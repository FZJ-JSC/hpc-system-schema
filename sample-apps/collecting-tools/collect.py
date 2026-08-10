#!/usr/bin/env python3
"""
HPC System Description Collector

Main orchestrator that runs individual collectors and produces a JSON
fragment matching the system-definition schema (v0.5.0).

Usage:
    python3 collect.py                          # Run all available collectors
    python3 collect.py --tools lscpu,nvidia-smi # Run specific collectors
    python3 collect.py --merge desc.json        # Merge with existing description
    python3 collect.py --list                   # List available collectors
    python3 collect.py --review data.json       # Review collected data

Each collector produces a JSON fragment with keys matching the schema:
  cpus, memory, accelerators, network, on_node_storage, numa_topology,
  storage_system, further_metadata
"""

import argparse
import json
import sys
import os
from pathlib import Path

# Add parent dir for collect_lib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# Collector registry
# ---------------------------------------------------------------------------

COLLECTORS = {
    "lscpu": {
        "module": "collectors.lscpu",
        "description": "CPU model, cores, threads, sockets, cache, ISA",
        "requires": "lscpu (util-linux)",
        "sudo": False,
        "schema_fields": ["cpus"],
    },
    "lstopo": {
        "module": "collectors.lstopo",
        "description": "NUMA topology, cache hierarchy from hwloc",
        "requires": "lstopo (hwloc)",
        "sudo": False,
        "schema_fields": ["numa_topology"],
    },
    "dmidecode": {
        "module": "collectors.dmidecode",
        "description": "Memory DIMM config, board info",
        "requires": "dmidecode (root access)",
        "sudo": True,
        "schema_fields": ["memory", "further_metadata"],
    },
    "numactl": {
        "module": "collectors.numactl",
        "description": "NUMA domains, memory per domain, distance matrix",
        "requires": "numactl",
        "sudo": False,
        "schema_fields": ["numa_topology"],
    },
    "nvidia-smi": {
        "module": "collectors.nvidia_smi",
        "description": "GPU model, memory, cores, clock, power",
        "requires": "nvidia-smi (NVIDIA driver)",
        "sudo": False,
        "schema_fields": ["accelerators"],
    },
    "ibv_devinfo": {
        "module": "collectors.ibv_devinfo",
        "description": "InfiniBand adapter model, ports, speed",
        "requires": "ibv_devinfo (rdma-core)",
        "sudo": False,
        "schema_fields": ["network"],
    },
    "ethtool": {
        "module": "collectors.ethtool",
        "description": "Ethernet adapter speed, driver, features",
        "requires": "ethtool",
        "sudo": False,
        "schema_fields": ["network"],
    },
    "perftest": {
        "module": "collectors.perftest",
        "description": "InfiniBand latency and bandwidth benchmarks",
        "requires": "ib_write_bw, ib_read_lat (perftest)",
        "sudo": False,
        "schema_fields": ["further_metadata"],
    },
    "lsblk": {
        "module": "collectors.lsblk",
        "description": "Block devices: disk sizes, types, models",
        "requires": "lsblk (util-linux)",
        "sudo": False,
        "schema_fields": ["on_node_storage"],
    },
    "lustre": {
        "module": "collectors.lustre",
        "description": "Lustre filesystem: OSTs, MDTs, capacity",
        "requires": "lfs (Lustre client tools)",
        "sudo": False,
        "schema_fields": ["storage_system"],
    },
    "dd": {
        "module": "collectors.dd_benchmark",
        "description": "Disk I/O sequential read/write throughput",
        "requires": "dd (coreutils)",
        "sudo": False,
        "schema_fields": ["further_metadata"],
    },
    "ipmitool": {
        "module": "collectors.ipmitool",
        "description": "BMC info, power readings, thermal sensors",
        "requires": "ipmitool (root access)",
        "sudo": True,
        "schema_fields": ["further_metadata"],
    },
}


def load_collector(name: str):
    """Dynamically load a collector module."""
    info = COLLECTORS.get(name)
    if not info:
        return None
    try:
        import importlib
        mod = importlib.import_module(info["module"])
        return mod
    except ImportError as e:
        print(f"[error] failed to import {name}: {e}", file=sys.stderr)
        return None


def list_collectors():
    """Print available collectors."""
    print("Available collectors:")
    print("-" * 60)
    for name, info in sorted(COLLECTORS.items()):
        fields = ", ".join(info["schema_fields"])
        sudo_note = " [sudo]" if info["sudo"] else ""
        print(f"  {name:15s} {info['description']}{sudo_note}")
        print(f"  {'':15s} requires: {info['requires']}")
        print(f"  {'':15s} schema fields: {fields}")
        print()


def merge_fragments(*fragments: dict) -> dict:
    """Merge multiple collector fragments into a single node type description.

    Lists are merged (appended); dicts are merged at top level;
    scalar values are overwritten by later fragments.
    """
    result = {}
    for frag in fragments:
        if not frag:
            continue
        for key, val in frag.items():
            if key in result:
                existing = result[key]
                if isinstance(existing, list) and isinstance(val, list):
                    existing.extend(val)
                elif isinstance(existing, dict) and isinstance(val, dict):
                    existing.update(val)
                else:
                    result[key] = val
            else:
                result[key] = val
    return result


def merge_with_existing(existing_path: str, new_data: dict) -> dict:
    """Merge collected data into an existing system description.

    For arrays (cpus, memory, accelerators, network, on_node_storage,
    numa_topology): appends to existing arrays.
    For storage_system: overwrites.
    For further_metadata: merges keys.
    """
    with open(existing_path) as f:
        existing = json.load(f)

    # Find the first compute part to merge into
    parts = existing.get("parts", [])
    if not parts:
        print("[warn] no parts in existing description, adding new part", file=sys.stderr)
        parts.append({"id": "part-0", "name": "Compute", "part_type": "compute", "node_types": []})
        existing["parts"] = parts

    # Get or create first compute node type
    compute_part = None
    for p in parts:
        if p.get("part_type") == "compute":
            compute_part = p
            break
    if not compute_part:
        compute_part = parts[0]

    node_types = compute_part.get("node_types", [])
    if not node_types:
        node_types.append({"id": "node-0", "node_type_name": "Default", "cpus": [], "memory": []})
        compute_part["node_types"] = node_types

    nt = node_types[0]

    # Merge arrays
    for key in ("cpus", "memory", "accelerators", "network",
                "on_node_storage", "numa_topology"):
        if key in new_data:
            existing_arr = nt.get(key, [])
            if isinstance(existing_arr, list):
                existing_arr.extend(new_data[key])
            else:
                nt[key] = new_data[key]

    # Merge storage_system (overwrite)
    if "storage_system" in new_data:
        compute_part["storage_system"] = new_data["storage_system"]

    # Merge further_metadata
    if "further_metadata" in new_data:
        fm = existing.get("further_metadata", {})
        fm.update(new_data["further_metadata"])
        existing["further_metadata"] = fm

    return existing


def review_data(data_path: str):
    """Review collected data and show what was found."""
    with open(data_path) as f:
        data = json.load(f)

    print("=" * 60)
    print("Review of collected data")
    print("=" * 60)

    for key, val in data.items():
        if isinstance(val, list):
            print(f"\n{key}: {len(val)} item(s)")
            for i, item in enumerate(val):
                name = item.get("name", item.get("id", f"item-{i}"))
                extra = ""
                if key == "cpus":
                    extra = f" ({item.get('cores_per_cpu', '?')} cores, {item.get('number_of_sockets', '?')} sockets)"
                elif key == "memory":
                    amt = item.get("amount", {})
                    extra = f" ({amt.get('quantity', '?')} {amt.get('unit', '?')})"
                elif key == "accelerators":
                    extra = f" (count={item.get('count_per_node', '?')})"
                print(f"  [{i}] {name}{extra}")
        elif isinstance(val, dict):
            print(f"\n{key}: (dict with {len(val)} keys)")
            for k, v in val.items():
                if isinstance(v, str) and len(v) > 60:
                    print(f"  {k}: {v[:60]}...")
                else:
                    print(f"  {k}: {v}")
        else:
            print(f"\n{key}: {val}")

    # Show schema coverage
    schema_keys = {"cpus", "memory", "accelerators", "network",
                   "on_node_storage", "numa_topology", "storage_system",
                   "further_metadata"}
    filled = schema_keys & set(data.keys())
    empty = schema_keys - filled

    print("\n" + "=" * 60)
    print("Schema coverage:")
    print(f"  Filled: {', '.join(sorted(filled)) or '(none)'}")
    print(f"  Empty:  {', '.join(sorted(empty)) or '(none)'}")


def main():
    parser = argparse.ArgumentParser(
        description="Collect HPC system hardware information for system descriptions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--tools", "-t",
        default=None,
        help="Comma-separated list of tools to run (default: all available)"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output JSON file (default: stdout)"
    )
    parser.add_argument(
        "--merge", "-m",
        default=None,
        help="Merge with an existing system description JSON"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available collectors and exit"
    )
    parser.add_argument(
        "--review", "-r",
        default=None,
        help="Review a previously collected JSON file"
    )
    parser.add_argument(
        "--node-id",
        default="node-0",
        help="ID for the collected node type (default: node-0)"
    )
    parser.add_argument(
        "--node-name",
        default="Collected Node",
        help="Name for the collected node type (default: 'Collected Node')"
    )

    # Per-tool arguments
    parser.add_argument("--ib-server", default=None, help="IB perftest remote server IP")
    parser.add_argument("--ib-device", default=None, help="IB device for perftest")
    parser.add_argument("--dd-size", type=int, default=256, help="DD test size in MB")
    parser.add_argument("--lustre-mount", default="/", help="Lustre mount point")

    args = parser.parse_args()

    if args.list:
        list_collectors()
        return

    if args.review:
        review_data(args.review)
        return

    # Determine which tools to run
    tool_names = None
    if args.tools:
        tool_names = [t.strip() for t in args.tools.split(",")]
        # Validate
        for t in tool_names:
            if t not in COLLECTORS:
                print(f"[error] unknown tool: {t}", file=sys.stderr)
                print(f"Available: {', '.join(sorted(COLLECTORS.keys()))}", file=sys.stderr)
                sys.exit(1)

    # Run collectors
    fragments = []
    for name, info in sorted(COLLECTORS.items()):
        if tool_names and name not in tool_names:
            continue

        mod = load_collector(name)
        if not mod:
            continue

        try:
            # Special arguments for certain collectors
            if name == "perftest":
                frag = mod.collect(server_ip=args.ib_server, interface=args.ib_device)
            elif name == "dd":
                frag = mod.collect(test_size_mb=args.dd_size)
            elif name == "lustre":
                frag = mod.collect(mount_point=args.lustre_mount)
            else:
                frag = mod.collect()

            if frag:
                fragments.append(frag)
                # Show what was collected
                keys = list(frag.keys())
                print(f"[ok] {name}: {', '.join(keys)}", file=sys.stderr)
            else:
                print(f"[skip] {name}: no data collected", file=sys.stderr)
        except Exception as e:
            print(f"[error] {name}: {e}", file=sys.stderr)

    if not fragments:
        print("[warn] no data collected from any tool", file=sys.stderr)
        sys.exit(1)

    # Merge fragments
    merged = merge_fragments(*fragments)

    # Add node metadata
    merged["id"] = args.node_id
    merged["node_type_name"] = args.node_name

    # Merge with existing description if requested
    if args.merge:
        if os.path.exists(args.merge):
            result = merge_with_existing(args.merge, merged)
            print(f"\n[ok] merged with {args.merge}", file=sys.stderr)
        else:
            print(f"[error] file not found: {args.merge}", file=sys.stderr)
            sys.exit(1)
    else:
        result = merged

    # Output
    output_str = json.dumps(result, indent=2)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w") as f:
            f.write(output_str)
            f.write("\n")
        print(f"[ok] written to {args.output}", file=sys.stderr)
    else:
        print(output_str)

    # Summary
    schema_keys = {"cpus", "memory", "accelerators", "network",
                   "on_node_storage", "numa_topology", "storage_system"}
    if args.merge:
        schema_keys |= {"parts"}
    filled = schema_keys & set(result.keys()) if args.merge else schema_keys & set(merged.keys())
    print(f"\n[summary] collected data for: {', '.join(sorted(filled))}", file=sys.stderr)


if __name__ == "__main__":
    main()
