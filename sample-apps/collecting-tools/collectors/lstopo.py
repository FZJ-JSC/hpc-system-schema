#!/usr/bin/env python3
"""Collect NUMA topology from lstopo.

Parses `lstopo --of text` or `lstopo-no-graphics` to extract NUMA node
layout, cache hierarchy, and GPU placement.
"""

import re
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from collect_lib import run_cmd, make_numa_domain, make_cache_level, warn_tool

TOOL_NAME = "lstopo"


def _parse_numa_nodes(output: str) -> list:
    """Parse lstopo text output for NUMA nodes."""
    numa_nodes = []
    # Look for "NUMANode" lines like:
    #   NUMANode#0 (256MB)
    #   NUMANode#1 (256MB)
    for line in output.split("\n"):
        m = re.search(r'NUMANode#(\d+)\s*\((\d+)([KMGT]?B)\)', line)
        if m:
            domain_id = int(m.group(1))
            size = float(m.group(2))
            unit = m.group(3)
            # Convert to GB
            if unit == "TB":
                size *= 1024
            elif unit == "GB":
                pass
            elif unit == "MB":
                size /= 1024
            elif unit == "KB":
                size /= 1024 * 1024
            elif unit == "B":
                size /= 1024 ** 3
            numa_nodes.append({"domain_id": domain_id, "memory_gb": round(size, 1)})

    return numa_nodes


def _parse_cpu_assignment(output: str) -> dict:
    """Parse lstopo to find which CPUs are in which NUMA node."""
    assignments = {}
    # Look for patterns like "Core#0" and nearby "NUMANode#N"
    # This is a simplified heuristic from the text tree
    current_numa = None
    for line in output.split("\n"):
        stripped = line.strip()
        numa_match = re.search(r'NUMANode#(\d+)', stripped)
        if numa_match:
            current_numa = int(numa_match.group(1))
            if current_numa not in assignments:
                assignments[current_numa] = []

        # In some lstopo outputs, CPU ranges appear as "P#0" after NUMANode
        cpu_match = re.search(r'P#(\d+)', stripped)
        if cpu_match and current_numa is not None:
            cpu_id = int(cpu_match.group(1))
            if cpu_id not in assignments.get(current_numa, []):
                assignments.setdefault(current_numa, []).append(cpu_id)

    return assignments


def collect() -> dict:
    """Collect NUMA topology from lstopo.

    Returns:
        Dict with 'numa_topology' key.
    """
    if not run_cmd("which lstopo") and not run_cmd("which lstopo-no-graphics"):
        warn_tool("lstopo", "NUMA topology (install hwloc package)")
        return {}

    # Try lstopo with text output
    output = run_cmd("lstopo --of text 2>/dev/null")
    if not output:
        output = run_cmd("lstopo-no-graphics 2>/dev/null")
    if not output:
        output = run_cmd("lstopo 2>/dev/null")
    if not output:
        return {}

    numa_nodes = _parse_numa_nodes(output)
    cpu_assignments = _parse_cpu_assignment(output)

    if not numa_nodes:
        # Fallback: check /sys/devices/system/node/node*/meminfo
        import pathlib
        node_mem = []
        for p in sorted(pathlib.Path("/sys/devices/system/node").glob("node*")):
            if p.name.startswith("node"):
                try:
                    nid = int(p.name[4:])
                    meminfo = (p / "meminfo").read_text()
                    for line in meminfo.split("\n"):
                        if line.startswith("MemTotal:"):
                            kb = int(line.split()[1])
                            node_mem.append({"domain_id": nid, "memory_gb": round(kb / 1024 / 1024, 1)})
                            break
                except (ValueError, FileNotFoundError):
                    continue
        if node_mem:
            numa_nodes = node_mem

    domains = []
    for n in numa_nodes:
        nid = n["domain_id"]
        cpus = cpu_assignments.get(nid, [])
        domains.append(make_numa_domain(
            nid, n["memory_gb"], cpus,
            comment=f"NUMA node {nid}: {n['memory_gb']} GB"
        ))

    if domains:
        return {"numa_topology": domains}
    return {}


if __name__ == "__main__":
    import json
    result = collect()
    print(json.dumps(result, indent=2))
