#!/usr/bin/env python3
"""Collect Ethernet adapter information from ethtool.

Parses `ethtool <interface>` to extract link speed, driver, and features.
Maps to NetworkAdapter schema fields.
"""

import re
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from collect_lib import run_cmd, make_network_adapter, warn_tool

TOOL_NAME = "ethtool"


def _discover_interfaces() -> list:
    """Discover network interfaces from /sys/class/net/."""
    interfaces = []
    try:
        import pathlib
        for iface_path in sorted(pathlib.Path("/sys/class/net").iterdir()):
            name = iface_path.name
            # Skip loopback and virtual interfaces
            if name in ("lo", "dummy0"):
                continue
            # Check if it's a physical device
            if (iface_path / "device").exists():
                interfaces.append(name)
    except FileNotFoundError:
        pass
    return interfaces


def _speed_to_type(speed_mbps: int) -> str:
    """Convert link speed in Mbps to an Ethernet type string."""
    if speed_mbps >= 400000:
        return "Ethernet 400GbE"
    if speed_mbps >= 200000:
        return "Ethernet 200GbE"
    if speed_mbps >= 100000:
        return "Ethernet 100GbE"
    if speed_mbps >= 40000:
        return "Ethernet 40GbE"
    if speed_mbps >= 25000:
        return "Ethernet 25GbE"
    if speed_mbps >= 10000:
        return "Ethernet 10GbE"
    if speed_mbps >= 1000:
        return "Ethernet 1GbE"
    return f"Ethernet ({speed_mbps} Mb/s)"


def collect() -> dict:
    """Collect Ethernet adapter information.

    Returns:
        Dict with 'network' key containing NetworkAdapter fragments.
    """
    if not run_cmd("which ethtool"):
        warn_tool("ethtool", "Ethernet adapter info")
        return {}

    interfaces = _discover_interfaces()
    if not interfaces:
        return {}

    adapters = []
    for iface in interfaces:
        output = run_cmd(f"ethtool {iface}")
        if not output:
            continue

        info = {}
        for line in output.split("\n"):
            line = line.strip()
            if ":" in line:
                key, _, val = line.partition(":")
                info[key.strip()] = val.strip()

        # Link speed
        speed_mbps = 0
        speed_str = info.get("Speed", "")
        m = re.search(r'(\d+)\s*Mb/s', speed_str)
        if m:
            speed_mbps = int(m.group(1))

        # If speed not reported, try reading from sysfs
        if speed_mbps == 0:
            try:
                speed_file = f"/sys/class/net/{iface}/speed"
                if os.path.exists(speed_file):
                    speed_mbps = int(open(speed_file).read().strip())
            except (ValueError, FileNotFoundError):
                pass

        if speed_mbps == 0:
            continue

        eth_type = _speed_to_type(speed_mbps)

        net_kwargs = {
            "id": f"net-eth-{iface}",
            "model": iface,
        }

        # Parse bandwidth
        if speed_mbps >= 1000:
            net_kwargs["bandwidth"] = {
                "quantity": speed_mbps / 1000,
                "unit": "Gb/s"
            }

        # Driver info from further_metadata
        fm = {}
        driver = info.get("Driver")
        if driver:
            fm["driver"] = driver
        version = info.get("Version")
        if version:
            fm["driver_version"] = version
        firmware = info.get("Firmware-version")
        if firmware:
            fm["firmware_version"] = firmware
        bus = info.get("Bus-info")
        if bus:
            fm["bus_info"] = bus
        duplex = info.get("Duplex")
        if duplex:
            fm["duplex"] = duplex

        if fm:
            net_kwargs["further_metadata"] = fm

        adapters.append(make_network_adapter(eth_type, **net_kwargs))

    if adapters:
        return {"network": adapters}
    return {}


if __name__ == "__main__":
    import json
    result = collect()
    print(json.dumps(result, indent=2))
