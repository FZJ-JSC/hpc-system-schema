"""
Shared library for HPC system description collectors.

Provides utilities for:
- Running system commands safely (with sudo fallback)
- Parsing command output
- Building schema-compliant JSON fragments
- Merging fragments into a complete node type description
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional, Any


# ---------------------------------------------------------------------------
# Command execution
# ---------------------------------------------------------------------------

def run_cmd(cmd: str, timeout: int = 30, sudo: bool = False) -> Optional[str]:
    """Run a shell command and return stdout, or None on failure.

    Args:
        cmd: The command string to execute.
        timeout: Timeout in seconds.
        sudo: If True, prefix with sudo (useful for dmidecode, ipmitool).

    Returns:
        stdout string or None if command not found / failed.
    """
    if sudo:
        cmd = f"sudo {cmd}"
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
        return None
    except FileNotFoundError:
        return None
    except subprocess.TimeoutExpired:
        print(f"[warn] timeout running: {cmd}", file=sys.stderr)
        return None
    except PermissionError:
        print(f"[warn] permission denied: {cmd} (try sudo)", file=sys.stderr)
        return None


def check_tool(name: str) -> bool:
    """Check if a command-line tool is available."""
    try:
        result = subprocess.run(
            ["which", name], capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def warn_tool(name: str, purpose: str = ""):
    """Print a warning that a tool is not available."""
    msg = f"[warn] '{name}' not found"
    if purpose:
        msg += f" — needed for {purpose}"
    msg += ". Install it or skip this collector."
    print(msg, file=sys.stderr)


# ---------------------------------------------------------------------------
# Schema fragment builders
# ---------------------------------------------------------------------------

def make_cpu(manufacturer: str, name: str, **kwargs) -> dict:
    """Build a CPU schema fragment."""
    cpu = {
        "id": kwargs.pop("id", "cpu-0"),
        "manufacturer": manufacturer,
        "name": name,
        "cores_per_cpu": kwargs.pop("cores_per_cpu", 1),
        "threads_per_core": kwargs.pop("threads_per_core", 1),
    }
    # Optional fields
    for key in ("sku", "architecture", "isa", "number_of_sockets",
                "base_frequency", "max_frequency", "tdp",
                "cache_hierarchy", "comment", "further_metadata"):
        if key in kwargs and kwargs[key] is not None:
            cpu[key] = kwargs[key]
    return cpu


def make_memory(amount_gb: float, mem_type: str, **kwargs) -> dict:
    """Build a Memory schema fragment."""
    mem = {
        "id": kwargs.pop("id", "mem-0"),
        "amount": {"quantity": amount_gb, "unit": "GB"},
        "type": mem_type,
    }
    for key in ("bandwidth", "memory_pieces", "memory_channels",
                "numa_domains", "comment", "further_metadata"):
        if key in kwargs and kwargs[key] is not None:
            mem[key] = kwargs[key]
    return mem


def make_accelerator(manufacturer: str, name: str, count: int,
                     mem_gb: float, mem_type: str, **kwargs) -> dict:
    """Build an Accelerator schema fragment."""
    acc = {
        "id": kwargs.pop("id", "gpu-0"),
        "kind": kwargs.pop("kind", "GPU"),
        "manufacturer": manufacturer,
        "name": name,
        "count_per_node": count,
        "memory": {
            "id": f"mem-{name.lower().replace(' ', '-')}-0",
            "amount": {"quantity": mem_gb, "unit": "GB"},
            "type": mem_type,
        },
    }
    for key in ("sku", "architecture", "isa", "cores", "clock_rate",
                "tdp", "cpu_to_accelerator_link",
                "accelerator_to_accelerator_link",
                "cache_hierarchy", "comment", "further_metadata"):
        if key in kwargs and kwargs[key] is not None:
            acc[key] = kwargs[key]
    return acc


def make_network_adapter(adapter_type: str, **kwargs) -> dict:
    """Build a NetworkAdapter schema fragment."""
    net = {
        "id": kwargs.pop("id", "net-0"),
        "type": adapter_type,
    }
    for key in ("manufacturer", "model", "adapters_per_node",
                "bandwidth", "adapter_to_switch_link",
                "cpu_to_network_link", "comment", "further_metadata"):
        if key in kwargs and kwargs[key] is not None:
            net[key] = kwargs[key]
    return net


def make_storage(name: str, stype: str, **kwargs) -> dict:
    """Build a Storage schema fragment."""
    stor = {
        "id": kwargs.pop("id", "stor-0"),
        "name": name,
        "type": stype,
    }
    for key in ("manufacturer", "product_name", "amount_per_node",
                "total_amount", "bandwidth", "iops", "storage_role",
                "blocksize", "cpu_to_storage_link",
                "comment", "further_metadata"):
        if key in kwargs and kwargs[key] is not None:
            stor[key] = kwargs[key]
    return stor


def make_numa_domain(domain_id: int, mem_gb: float, cpus: list, **kwargs) -> dict:
    """Build a NumaDomain schema fragment."""
    numa = {
        "id": f"numa-{domain_id}",
        "domain_id": domain_id,
        "memory_size": {"quantity": mem_gb, "unit": "GB"},
        "associated_cpus": cpus,
    }
    for key in ("distance_matrix", "associated_accelerators",
                "comment", "further_metadata"):
        if key in kwargs and kwargs[key] is not None:
            numa[key] = kwargs[key]
    return numa


def make_cache_level(name: str, cache_type: str, size_kb: float, **kwargs) -> dict:
    """Build a CacheLevel schema fragment."""
    cache = {
        "id": f"cache-{name.lower()}",
        "level_name": name,
        "cache_type": cache_type,
    }
    if size_kb >= 1024:
        cache["size"] = {"quantity": size_kb / 1024, "unit": "MB"}
    else:
        cache["size"] = {"quantity": size_kb, "unit": "KB"}
    for key in ("associativity", "line_size", "instances_per_cpu",
                "comment", "further_metadata"):
        if key in kwargs and kwargs[key] is not None:
            cache[key] = kwargs[key]
    return cache


def make_link(link_type: str, bandwidth_gbps: float, **kwargs) -> dict:
    """Build a Link schema fragment."""
    link = {
        "id": kwargs.pop("id", "link-0"),
        "type": link_type,
        "bandwidth": {"quantity": bandwidth_gbps, "unit": "Gb/s"},
    }
    for key in ("comment", "further_metadata"):
        if key in kwargs and kwargs[key] is not None:
            link[key] = kwargs[key]
    return link


# ---------------------------------------------------------------------------
# Unit helpers
# ---------------------------------------------------------------------------

def parse_size_to_gb(size_str: str) -> float:
    """Convert a human-readable size string to GB.

    Examples:
        '256Gi' -> 256.0
        '1.5Ti' -> 1536.0
        '512Mi' -> 0.5
        '4096MB' -> 4.096
        '32kB' -> 0.000030517578125
    """
    size_str = size_str.strip()
    multipliers = {
        "Ki": 1 / (1024 * 1024),   # to GB
        "Mi": 1 / 1024,
        "Gi": 1.0,
        "Ti": 1024.0,
        "Pi": 1024 * 1024.0,
        "KB": 1e-6,
        "MB": 1e-3,
        "GB": 1.0,
        "TB": 1000.0,
        "PB": 1000000.0,
    }
    for suffix, mult in sorted(multipliers.items(), key=lambda x: -len(x[0])):
        if size_str.endswith(suffix):
            num = float(size_str[:-len(suffix)])
            return num * mult
    # Try plain number (assume GB)
    try:
        return float(size_str)
    except ValueError:
        return 0.0


def parse_speed_ghz(speed_str: str) -> Optional[float]:
    """Parse CPU frequency string to GHz float.

    Examples:
        '2400 MHz' -> 2.4
        '3.70 GHz' -> 3.7
        '2400.000 MHz' -> 2.4
    """
    speed_str = speed_str.strip().replace(",", ".")
    m = re.search(r'([\d.]+)\s*GHz', speed_str, re.IGNORECASE)
    if m:
        return float(m.group(1))
    m = re.search(r'([\d.]+)\s*MHz', speed_str, re.IGNORECASE)
    if m:
        return float(m.group(1)) / 1000.0
    return None


# ---------------------------------------------------------------------------
# Merge helpers
# ---------------------------------------------------------------------------

def merge_into_node_type(base: dict, *fragments: dict) -> dict:
    """Merge collector fragments into a node type description.

    Each fragment is a dict that may contain keys like 'cpus', 'memory',
    'accelerators', 'network', 'on_node_storage', 'numa_topology', etc.
    Lists are appended; dicts are merged at top level only.

    Args:
        base: The base node type dict (may be empty).
        *fragments: One or more fragment dicts to merge in.

    Returns:
        Merged node type dict.
    """
    result = dict(base)
    for frag in fragments:
        for key, val in frag.items():
            if key in result and isinstance(result[key], list) and isinstance(val, list):
                result[key].extend(val)
            else:
                result[key] = val
    return result


def collect_and_merge(collectors: list, tool_names: Optional[list] = None) -> dict:
    """Run selected collectors and merge their outputs.

    Args:
        collectors: List of collector modules (each must have a collect() function).
        tool_names: Optional filter — only run collectors whose tool_name is in this list.

    Returns:
        Merged node type dict.
    """
    fragments = []
    for collector in collectors:
        if tool_names and getattr(collector, "TOOL_NAME", "") not in tool_names:
            continue
        try:
            frag = collector.collect()
            if frag:
                fragments.append(frag)
        except Exception as e:
            print(f"[error] {collector.TOOL_NAME}: {e}", file=sys.stderr)
    return merge_into_node_type({}, *fragments)


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def write_json(data: Any, path: str):
    """Write JSON data to a file with pretty printing."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"[ok] written to {path}")


def print_json(data: Any):
    """Print JSON data to stdout."""
    print(json.dumps(data, indent=2))
