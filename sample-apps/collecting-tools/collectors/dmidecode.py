#!/usr/bin/env python3
"""Collect memory and board information from dmidecode.

Parses `dmidecode` to extract DIMM configuration (type, size, speed, count),
board manufacturer, and BIOS information.

NOTE: dmidecode typically requires root/sudo access.
"""

import re
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from collect_lib import run_cmd, make_memory, warn_tool

TOOL_NAME = "dmidecode"


def _parse_memory_devices(output: str) -> dict:
    """Parse Memory Device sections from dmidecode output."""
    # Split into sections
    sections = output.split("\n\n")
    dimms = []
    mem_types = set()
    speeds_mhz = []
    total_size_gb = 0

    for section in sections:
        if "Memory Device" not in section:
            continue
        lines = section.strip().split("\n")

        dimm = {}
        for line in lines:
            line = line.strip()
            if ":" not in line:
                continue
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()

            if key == "Type":
                if val and val not in ("Unknown", "Other", "Empty"):
                    dimm["type"] = val
                    mem_types.add(val)
            elif key == "Size":
                if val and val not in ("Unknown", "No Module Installed"):
                    # Parse like "32 GB" or "65536 MB"
                    m = re.match(r'([\d.]+)\s*(GB|MB|TB|KiB|MiB|GiB)', val)
                    if m:
                        size = float(m.group(1))
                        unit = m.group(2)
                        if unit in ("MB", "MiB"):
                            size /= 1024
                        elif unit in ("TB",):
                            size *= 1024
                        elif unit in ("KiB",):
                            size /= 1024 * 1024
                        dimm["size_gb"] = round(size, 2)
                        total_size_gb += size
            elif key == "Speed":
                if val and val not in ("Unknown",):
                    m = re.match(r'([\d.]+)\s*MT/s', val)
                    if m:
                        speeds_mhz.append(float(m.group(1)))
                    else:
                        # Try to extract MHz
                        m2 = re.search(r'([\d.]+)\s*MHz', val)
                        if m2:
                            speeds_mhz.append(float(m2.group(1)))
            elif key == "Locator":
                dimm["locator"] = val
            elif key == "Bank Locator":
                dimm["bank"] = val
            elif key == "Manufacturer":
                dimm["manufacturer"] = val

        if dimm.get("type") and dimm.get("size_gb", 0) > 0:
            dimms.append(dimm)

    # Summarize
    num_dimms = len(dimms)
    avg_speed = round(sum(speeds_mhz) / len(speeds_mhz), 0) if speeds_mhz else 0

    # Determine memory type string
    # Filter out non-memory types
    real_types = mem_types - {"Unknown", "Other", "Empty"}
    if real_types:
        mem_type = sorted(real_types)[0]  # most common
    else:
        mem_type = "Unknown"

    # Try to get speed suffix
    if avg_speed > 0:
        speed_int = int(avg_speed)
        if mem_type in ("DDR4",):
            mem_type = f"DDR4-{speed_int}"
        elif mem_type in ("DDR5",):
            mem_type = f"DDR5-{speed_int}"
        elif mem_type in ("LPDDR5", "LPDDR5X"):
            mem_type = mem_type

    return {
        "total_gb": round(total_size_gb, 1),
        "mem_type": mem_type,
        "num_dimms": num_dimms,
        "speed_mhz": avg_speed,
    }


def _parse_board(output: str) -> dict:
    """Parse baseboard/system info from dmidecode."""
    info = {}
    sections = output.split("\n\n")
    for section in sections:
        for line in section.split("\n"):
            line = line.strip()
            if ":" not in line:
                continue
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            if key == "Manufacturer" and val not in ("Unknown", "To Be Filled"):
                info["manufacturer"] = val
            elif key == "Product Name" and val not in ("Unknown",):
                info["product_name"] = val
            elif key == "Version" and "BIOS" in section:
                info["bios_version"] = val
            elif key == "Release Date" and "BIOS" in section:
                info["bios_date"] = val
    return info


def collect() -> dict:
    """Collect memory and board info from dmidecode.

    Returns:
        Dict with 'memory' key and optionally 'further_metadata'.
    """
    if not run_cmd("which dmidecode"):
        warn_tool("dmidecode", "memory configuration (install dmidecode)")
        return {}

    output = run_cmd("dmidecode", sudo=True)
    if not output:
        warn_tool("dmidecode", "memory info — root access required")
        return {}

    result = {}

    # Parse memory devices
    mem_info = _parse_memory_devices(output)
    if mem_info["total_gb"] > 0:
        mem_kwargs = {"id": "mem-0"}
        if mem_info["num_dimms"] > 0:
            mem_kwargs["memory_pieces"] = mem_info["num_dimms"]
        if mem_info["speed_mhz"] > 0:
            # Estimate bandwidth: DDR4-3200 ~ 25.6 GB/s per channel, 8 channels = 204.8 GB/s
            # DDR5-4800 ~ 38.4 GB/s per channel, 8 channels = 307.2 GB/s
            # This is a rough estimate
            pass
        mem_kwargs["comment"] = f"{mem_info['num_dimms']} DIMMs, {mem_info['mem_type']}"
        result["memory"] = [make_memory(mem_info["total_gb"], mem_info["mem_type"], **mem_kwargs)]

    # Parse board info
    board = _parse_board(output)
    if board:
        fm = {}
        for k, v in board.items():
            fm[k] = v
        if fm:
            result["further_metadata"] = fm

    return result


if __name__ == "__main__":
    import json
    result = collect()
    print(json.dumps(result, indent=2))
