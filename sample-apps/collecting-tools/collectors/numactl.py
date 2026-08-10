#!/usr/bin/env python3
"""Collect NUMA topology from numactl.

Parses `numactl --hardware` to extract NUMA node count, per-node memory,
CPU assignment, and distance matrix.
"""

import re
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from collect_lib import run_cmd, make_numa_domain, warn_tool

TOOL_NAME = "numactl"


def collect() -> dict:
    """Collect NUMA info from numactl.

    Returns:
        Dict with 'numa_topology' key.
    """
    if not run_cmd("which numactl"):
        warn_tool("numactl", "NUMA topology details")
        return {}

    output = run_cmd("numactl --hardware")
    if not output:
        return {}

    # Parse available nodes
    num_nodes = 0
    m = re.search(r'available:\s*(\d+)\s*nodes', output)
    if m:
        num_nodes = int(m.group(1))

    if num_nodes == 0:
        return {}

    # Parse per-node info
    nodes = {}
    for nid in range(num_nodes):
        # CPU list
        cpus = []
        cpu_match = re.search(rf'node {nid} cpus:\s*(.*)', output)
        if cpu_match:
            cpu_str = cpu_match.group(1).strip()
            # Parse ranges like "0-23 48-71"
            for part in cpu_str.split():
                if "-" in part:
                    start, end = part.split("-", 1)
                    cpus.extend(range(int(start), int(end) + 1))
                elif part.isdigit():
                    cpus.append(int(part))

        # Memory size
        mem_gb = 0.0
        mem_match = re.search(rf'node {nid} size:\s*(\d+)\s*MB', output)
        if not mem_match:
            mem_match = re.search(rf'node {nid} size:\s*([\d.]+)\s*GB', output)
            if mem_match:
                mem_gb = float(mem_match.group(1))
        if mem_match and mem_gb == 0:
            mem_mb = float(mem_match.group(1))
            mem_gb = round(mem_mb / 1024, 1)

        nodes[nid] = {"cpus": cpus, "mem_gb": mem_gb}

    # Parse distance matrix
    distances = {}
    dist_section = re.search(r'node distances:\s*\n((?:\s+\d+.+\n)+)', output)
    if dist_section:
        lines = dist_section.group(1).strip().split("\n")
        if len(lines) >= 2:
            # First line is header
            header_ids = [int(x) for x in lines[0].split()[1:]]
            for i, line in enumerate(lines[1:], 0):
                parts = line.split()
                if len(parts) > 1:
                    from_id = int(parts[0])
                    dists = {str(header_ids[j]): parts[j + 1]
                             for j in range(min(len(header_ids), len(parts) - 1))}
                    distances[str(from_id)] = dists

    domains = []
    for nid in sorted(nodes.keys()):
        node = nodes[nid]
        domain = make_numa_domain(
            nid, node["mem_gb"], node["cpus"],
            comment=f"NUMA node {nid}: {node['mem_gb']} GB, {len(node['cpus'])} CPUs"
        )
        if str(nid) in distances:
            domain["distance_matrix"] = distances[str(nid)]
        domains.append(domain)

    if domains:
        return {"numa_topology": domains}
    return {}


if __name__ == "__main__":
    import json
    result = collect()
    print(json.dumps(result, indent=2))
