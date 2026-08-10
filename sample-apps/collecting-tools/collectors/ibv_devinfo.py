#!/usr/bin/env python3
"""Collect InfiniBand adapter information from ibv_devinfo.

Parses `ibv_devinfo` to extract adapter model, vendor, ports, link speed,
and port width. Maps to NetworkAdapter schema fields.
"""

import re
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from collect_lib import run_cmd, make_network_adapter, warn_tool

TOOL_NAME = "ibv_devinfo"


def _speed_to_type(speed_str: str, width_str: str) -> str:
    """Infer InfiniBand type from speed and width.

    Examples:
        "HDR": 200 Gb/s, "NDR": 400 Gb/s
        4x = standard width
    """
    speed_upper = speed_str.upper().strip()
    if "NDR" in speed_upper:
        return "InfiniBand NDR"
    if "HDR" in speed_upper:
        return "InfiniBand HDR"
    if "EDR" in speed_upper:
        return "InfiniBand EDR"
    if "FDR" in speed_upper:
        return "InfiniBand FDR"
    if "QDR" in speed_upper:
        return "InfiniBand QDR"
    if "SDR" in speed_upper:
        return "InfiniBand SDR"

    # Try numeric speed
    m = re.search(r'(\d+)', speed_upper)
    if m:
        rate = int(m.group(1))
        if rate >= 400:
            return "InfiniBand NDR400"
        if rate >= 200:
            return "InfiniBand NDR200"
        if rate >= 100:
            return "InfiniBand HDR"
        if rate >= 50:
            return "InfiniBand EDR"
        if rate >= 25:
            return "InfiniBand FDR"

    return f"InfiniBand ({speed_str})"


def _vendor_from_node_desc(node_desc: str) -> str:
    """Guess vendor from node description or device name."""
    desc_lower = node_desc.lower()
    if any(x in desc_lower for x in ("mlx", "mellanox", "connectx")):
        return "NVIDIA"
    if any(x in desc_lower for x in ("intel", "hfi")):
        return "Intel"
    return "Unknown"


def collect() -> dict:
    """Collect InfiniBand adapter information.

    Returns:
        Dict with 'network' key containing NetworkAdapter fragments.
    """
    if not run_cmd("which ibv_devinfo"):
        warn_tool("ibv_devinfo", "InfiniBand adapter info (install rdma-core)")
        return {}

    output = run_cmd("ibv_devinfo")
    if not output:
        return {}

    adapters = []
    current_adapter = None

    for line in output.split("\n"):
        line = line.strip()

        # Device header: "hca_id:\tmlx5_0"
        if line.startswith("hca_id:"):
            if current_adapter:
                adapters.append(current_adapter)
            dev_id = line.split(":", 1)[1].strip()
            current_adapter = {
                "device": dev_id,
                "vendor": "",
                "node_desc": "",
                "ports": [],
                "fw_ver": "",
                "hw_ver": "",
            }
            continue

        if not current_adapter:
            continue

        # Vendor
        if line.startswith("Vendor:"):
            current_adapter["vendor"] = line.split(":", 1)[1].strip()
        elif line.startswith("Node description:"):
            current_adapter["node_desc"] = line.split(":", 1)[1].strip()
        elif line.startswith("FW version:"):
            current_adapter["fw_ver"] = line.split(":", 1)[1].strip()
        elif line.startswith("Hardware version:"):
            current_adapter["hw_ver"] = line.split(":", 1)[1].strip()

        # Port info
        port_match = re.match(r'port:\s*(\d+)', line)
        if port_match:
            port_num = int(port_match.group(1))
            current_adapter["current_port"] = port_num
            current_adapter.setdefault("ports", []).append({"port": port_num})

        if "State:" in line and current_adapter.get("ports"):
            state = line.split(":", 1)[1].strip()
            current_adapter["ports"][-1]["state"] = state
        if "Physical state:" in line and current_adapter.get("ports"):
            pstate = line.split(":", 1)[1].strip()
            current_adapter["ports"][-1]["physical_state"] = pstate
        if "Rate:" in line and current_adapter.get("ports"):
            rate = line.split(":", 1)[1].strip()
            current_adapter["ports"][-1]["rate"] = rate
        if "Width:" in line and current_adapter.get("ports"):
            width = line.split(":", 1)[1].strip()
            current_adapter["ports"][-1]["width"] = width

    if current_adapter:
        adapters.append(current_adapter)

    if not adapters:
        return {}

    # Deduplicate (each ibv_devinfo entry is one adapter)
    # Count unique device names
    from collections import Counter
    dev_counts = Counter(a["device"] for a in adapters)
    unique_devices = {a["device"]: a for a in adapters}

    network = []
    for dev_id, adapter in unique_devices.items():
        # Determine type from port rate
        rate_str = ""
        width_str = ""
        for port in adapter.get("ports", []):
            if port.get("rate"):
                rate_str = port["rate"]
                break
        for port in adapter.get("ports", []):
            if port.get("width"):
                width_str = port["width"]
                break

        ib_type = _speed_to_type(rate_str, width_str)
        vendor = adapter.get("vendor", "") or _vendor_from_node_desc(adapter.get("node_desc", ""))

        net_kwargs = {
            "id": f"net-ib-{dev_id}",
            "manufacturer": vendor,
            "model": adapter.get("node_desc", dev_id),
            "adapters_per_node": dev_counts.get(dev_id, 1),
        }

        # Parse bandwidth
        m = re.search(r'([\d.]+)\s*(Gb/s|Gb)', rate_str, re.IGNORECASE)
        if m:
            net_kwargs["bandwidth"] = {"quantity": float(m.group(1)), "unit": "Gb/s"}

        # Add firmware/version to further_metadata
        fm = {}
        if adapter.get("fw_ver"):
            fm["firmware_version"] = adapter["fw_ver"]
        if adapter.get("hw_ver"):
            fm["hardware_version"] = adapter["hw_ver"]
        if fm:
            net_kwargs["further_metadata"] = fm

        network.append(make_network_adapter(ib_type, **net_kwargs))

    return {"network": network}


if __name__ == "__main__":
    import json
    result = collect()
    print(json.dumps(result, indent=2))
