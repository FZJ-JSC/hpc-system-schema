#!/usr/bin/env python3
"""Collect CPU information from lscpu.

Parses `lscpu` to extract CPU model, cores, threads, sockets, architecture,
frequencies, and cache hierarchy. Produces a schema fragment for the CPU array.
"""

import re
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from collect_lib import run_cmd, make_cpu, make_cache_level, warn_tool

TOOL_NAME = "lscpu"


def _parse_cache_size(size_str: str) -> float:
    """Parse cache size string like '32K', '1M', '98304K' to KB."""
    size_str = size_str.strip().upper()
    m = re.match(r'([\d.]+)\s*([KMG])', size_str)
    if not m:
        return 0.0
    val = float(m.group(1))
    unit = m.group(2)
    if unit == "K":
        return val
    elif unit == "M":
        return val * 1024
    elif unit == "G":
        return val * 1024 * 1024
    return val


def _detect_manufacturer(model_name: str) -> str:
    """Guess CPU manufacturer from model name."""
    name_lower = model_name.lower()
    if any(x in name_lower for x in ("epyc", "ryzen", "threadripper", "athlon")):
        return "AMD"
    if any(x in name_lower for x in ("xeon", "core", "atom", "pentium", "celeron")):
        return "Intel"
    if any(x in name_lower for x in ("graviton", "arm", "neoverse")):
        return "ARM"
    if "a64fx" in name_lower:
        return "Fujitsu"
    if "power" in name_lower:
        return "IBM"
    return "Unknown"


def _detect_arch(model_name: str, arch_field: str) -> str:
    """Infer microarchitecture from model name."""
    name_lower = model_name.lower()
    arch_lower = arch_field.lower() if arch_field else ""

    # AMD
    if "epyc 9" in name_lower or "genoa" in name_lower:
        return "Zen 4"
    if "epyc 7" in name_lower or "milan" in name_lower:
        return "Zen 3"
    if "epyc 7" in name_lower and ("rome" in name_lower or "7xx2" in name_lower):
        return "Zen 2"

    # Intel
    if any(x in name_lower for x in ("sapphire rapids", "84", "xeon w9")):
        return "Sapphire Rapids"
    if any(x in name_lower for x in ("emerald rapids", "85")):
        return "Emerald Rapids"
    if any(x in name_lower for x in ("ice lake", "83")):
        return "Ice Lake"
    if any(x in name_lower for x in ("cooper lake", "62")):
        return "Cooper Lake"

    # ARM
    if "neoverse" in name_lower or "neoverse" in arch_lower:
        if "v2" in name_lower:
            return "Neoverse-V2"
        return "Neoverse"

    return arch_field or "Unknown"


def collect() -> dict:
    """Collect CPU information from lscpu.

    Returns:
        Dict with 'cpus' key containing CPU schema fragments.
    """
    if not run_cmd("which lscpu"):
        warn_tool("lscpu", "CPU information")
        return {}

    output = run_cmd("lscpu")
    if not output:
        return {}

    info = {}
    for line in output.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            info[key.strip()] = val.strip()

    # Extract basic fields
    model_name = info.get("Model name", info.get("CPU model", "Unknown"))
    manufacturer = _detect_manufacturer(model_name)
    arch_field = info.get("Architecture", "")
    isa = arch_field  # lscpu shows ISA in Architecture field

    # Cores and sockets
    cores_per_socket = int(info.get("Core(s) per socket", "1"))
    sockets = int(info.get("Socket(s)", "1"))
    threads_per_core = int(info.get("Thread(s) per core", "1"))
    total_cores = int(info.get("CPU(s)", str(cores_per_socket * sockets)))

    # If hyperthreading is off, threads_per_core from lscpu is 1
    # but if there's a difference between CPU(s) and Core(s)*Socket(s), it's HT
    if threads_per_core == 1 and total_cores > cores_per_socket * sockets:
        threads_per_core = total_cores // (cores_per_socket * sockets)

    # Frequencies
    from collect_lib import parse_speed_ghz
    base_freq = None
    max_freq = None

    for key in ("CPU MHz", "CPU max MHz", "CPU min MHz"):
        if key in info:
            ghz = parse_speed_ghz(info[key])
            if ghz:
                if "max" in key.lower():
                    max_freq = ghz
                elif "min" in key.lower() or "CPU MHz" == key:
                    base_freq = ghz

    # Cache hierarchy
    cache_levels = []
    cache_map = {}
    for key, val in info.items():
        key_lower = key.lower()
        if "cache" in key_lower:
            # Parse keys like "L1d cache", "L1i cache", "L2 cache", "L3 cache"
            m = re.match(r'L(\d)([di]?)\s+cache', key_lower)
            if m:
                level = int(m.group(1))
                sub = m.group(2)
                cache_type = "data" if sub == "d" else "instruction" if sub == "i" else "unified"
                cache_key = f"L{level}" + (f"{'d' if sub == 'd' else 'i' if sub == 'i' else ''}")
                if sub:
                    cache_key = f"L{level}{'d' if sub == 'd' else 'i'}"
                else:
                    cache_key = f"L{level}"

                # If unified exists for a level, don't add separate d/i
                if f"L{level}" in cache_map and not sub:
                    continue
                if sub and f"L{level}" in cache_map:
                    continue

                size_kb = _parse_cache_size(val)
                cache_levels.append(make_cache_level(
                    cache_key, cache_type, size_kb,
                    comment=f"{val.strip()} per core" if level <= 2 else f"{val.strip()} shared"
                ))
                cache_map[cache_key] = True

    # ISA detection
    if "x86" in isa.lower() or "amd64" in isa.lower():
        isa = "x86_64"
    elif "aarch64" in isa.lower() or "arm" in isa.lower():
        if any(x in model_name.lower() for x in ("grace", "v2")):
            isa = "ARMv9"
        else:
            isa = "ARMv8"

    # Build the fragment
    cpu_kwargs = {
        "id": "cpu-0",
        "architecture": _detect_arch(model_name, arch_field),
        "isa": isa,
        "number_of_sockets": sockets,
        "cores_per_cpu": cores_per_socket,
        "threads_per_core": threads_per_core,
    }
    if base_freq:
        cpu_kwargs["base_frequency"] = {"quantity": base_freq, "unit": "GHz"}
    if max_freq:
        cpu_kwargs["max_frequency"] = {"quantity": max_freq, "unit": "GHz"}
    if cache_levels:
        cpu_kwargs["cache_hierarchy"] = cache_levels

    cpu = make_cpu(manufacturer, model_name, **cpu_kwargs)

    # Add raw lscpu data to further_metadata for reference
    raw_fields = {}
    for k in ("Vendor ID", "Stepping", "CPU family", "Model",
              "BogoMIPS", "L1d cache", "L1i cache", "L2 cache", "L3 cache",
              "NUMA node(s)", "CPU online", "Flags"):
        if k in info:
            raw_fields[k.lower().replace(" ", "_")] = info[k]
    if raw_fields:
        cpu["further_metadata"] = raw_fields

    return {"cpus": [cpu]}


if __name__ == "__main__":
    import json
    result = collect()
    print(json.dumps(result, indent=2))
