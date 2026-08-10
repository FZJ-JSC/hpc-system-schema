#!/usr/bin/env python3
"""Collect block device information from lsblk.

Parses `lsblk -J` (JSON output) to extract disk sizes, types, models,
and filesystem info. Maps to on_node_storage schema fields.
"""

import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from collect_lib import run_cmd, make_storage, warn_tool

TOOL_NAME = "lsblk"


def _determine_role(device: dict, mount: str) -> str:
    """Infer the storage role from mount point and device type."""
    if mount in ("/", "/boot", "/boot/efi"):
        return "boot"
    if "swap" in mount or mount == "[SWAP]":
        return "swap"
    if mount.startswith("/scratch") or mount.startswith("/tmp"):
        return "scratch"
    if mount.startswith("/home"):
        return "home"
    if any(x in mount for x in ("/data", "/lustre", "/gpfs", "/beegfs")):
        return "data"
    fstype = device.get("fstype", "") or ""
    if fstype in ("ext4", "xfs", "btrfs"):
        return "system"
    return "other"


def collect() -> dict:
    """Collect block device information.

    Returns:
        Dict with 'on_node_storage' key.
    """
    if not run_cmd("which lsblk"):
        warn_tool("lsblk", "block device information")
        return {}

    # Get JSON output
    output = run_cmd("lsblk -J -b -o NAME,SIZE,TYPE,MODEL,VENDOR,SERIAL,FSTYPE,MOUNTPOINT,ROTA,TRAN")
    if not output:
        return {}

    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return {}

    devices = []
    for dev in data.get("blockdevices", []):
        # Skip partitions, only want disks
        dev_type = dev.get("type", "")
        if dev_type != "disk":
            continue

        # Size in bytes
        size_bytes = int(dev.get("size", 0) or 0)
        if size_bytes == 0:
            continue

        # Convert to GB or TB
        if size_bytes >= 1024 ** 4:
            amount = round(size_bytes / (1024 ** 4), 1)
            unit = "TB"
        else:
            amount = round(size_bytes / (1024 ** 3), 1)
            unit = "GB"

        # Determine storage type
        model = (dev.get("model") or "").strip()
        vendor = (dev.get("vendor") or "").strip()
        tran = (dev.get("tran") or "").strip()
        rotational = dev.get("rota", True)

        if tran == "nvme" or "nvme" in model.lower():
            stype = "NVMe"
        elif tran == "sata" or "ssd" in model.lower() or not rotational:
            stype = "SATA SSD"
        elif tran == "sas":
            stype = "SAS SSD" if not rotational else "SAS HDD"
        elif not rotational:
            stype = "SSD"
        else:
            stype = "HDD"

        # Find mount point from children
        mount = ""
        for child in dev.get("children", []):
            mp = child.get("mountpoint", "") or ""
            if mp and mp not in ("[SWAP]",):
                mount = mp
                break
            elif child.get("fstype") == "swap":
                mount = "[SWAP]"

        role = _determine_role(dev, mount)
        name_str = model or f"{vendor} {dev.get('name', '')}".strip()

        stor_kwargs = {
            "id": f"stor-{dev.get('name', 'disk')}",
            "amount_per_node": {"quantity": amount, "unit": unit},
            "storage_role": role,
            "comment": f"{stype}: {name_str}, {amount} {unit}"
        }
        if model:
            stor_kwargs["manufacturer"] = vendor or "Unknown"
            stor_kwargs["product_name"] = model

        fstype = dev.get("fstype")
        if fstype:
            stor_kwargs["further_metadata"] = {"filesystem": fstype}

        devices.append(make_storage(name_str or dev.get("name", "disk"), stype, **stor_kwargs))

    if devices:
        return {"on_node_storage": devices}
    return {}


if __name__ == "__main__":
    result = collect()
    print(json.dumps(result, indent=2))
