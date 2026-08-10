#!/usr/bin/env python3
"""Collect Lustre filesystem information.

Parses `lfs df` and related commands to extract Lustre OST/MDT counts,
filesystem sizes, and configuration. Maps to Storage schema fields.
"""

import re
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from collect_lib import run_cmd, make_storage, warn_tool

TOOL_NAME = "lustre"


def _parse_lfs_df(output: str) -> dict:
    """Parse lfs df output for filesystem statistics."""
    stats = {"total_kb": 0, "used_kb": 0, "available_kb": 0, "ost_count": 0}

    for line in output.split("\n"):
        line = line.strip()
        if not line or line.startswith("filesystem"):
            continue
        # Parse lines like:
        # OST0000         500G  350G  140G  71%  /lustre/OST0000
        # or
        # filesystem_summary: 20T  14T  5.6T  71%
        if "filesystem_summary" in line:
            parts = line.split()
            for i, p in enumerate(parts):
                if p.endswith("T"):
                    stats["total_kb"] = float(p[:-1]) * 1024 * 1024 * 1024
                elif p.endswith("G"):
                    stats["total_kb"] = float(p[:-1]) * 1024 * 1024

        if re.match(r'OST\d+', line):
            stats["ost_count"] += 1
            parts = line.split()
            for i, p in enumerate(parts):
                if p.endswith("G"):
                    val_kb = float(p[:-1]) * 1024 * 1024
                    if i == 1:
                        stats["total_kb"] += val_kb
                    elif i == 2:
                        stats["used_kb"] += val_kb

    return stats


def collect(mount_point: str = "/") -> dict:
    """Collect Lustre filesystem information.

    Args:
        mount_point: Lustre mount point to query. Default "/".

    Returns:
        Dict with 'storage_system' key for the storage system description.
    """
    if not run_cmd("which lfs"):
        warn_tool("lfs", "Lustre filesystem information")
        return {}

    # Get filesystem summary
    output = run_cmd(f"lfs df -h {mount_point}")
    if not output:
        # Try without mount point
        output = run_cmd("lfs df -h")
    if not output:
        return {}

    stats = _parse_lfs_df(output)

    # Get MDT info
    mdt_output = run_cmd("lfs df -h --mdt")
    mdt_count = 0
    if mdt_output:
        for line in mdt_output.split("\n"):
            if re.match(r'MDT\d+', line.strip()):
                mdt_count += 1

    # Get stripe info
    stripe_output = run_cmd("lfs getstripe -d /")
    stripe_info = {}
    if stripe_output:
        for line in stripe_output.split("\n"):
            if "stripe_size" in line.lower():
                m = re.search(r'([\d.]+)\s*([KMGTP])', line)
                if m:
                    stripe_info["stripe_size"] = f"{m.group(1)}{m.group(2)}"
            if "stripe_count" in line.lower():
                m = re.search(r'(\d+)', line)
                if m:
                    stripe_info["stripe_count"] = int(m.group(1))

    # Build storage system fragment
    total_gb = round(stats["total_kb"] / (1024 * 1024), 1)
    total_unit = "GB"
    if total_gb >= 1024:
        total_gb = round(total_gb / 1024, 1)
        total_unit = "TB"
    if total_gb >= 1024:
        total_gb = round(total_gb / 1024, 1)
        total_unit = "PB"

    comment_parts = []
    if stats["ost_count"] > 0:
        comment_parts.append(f"{stats['ost_count']} OSTs")
    if mdt_count > 0:
        comment_parts.append(f"{mdt_count} MDTs")
    if stripe_info.get("stripe_size"):
        comment_parts.append(f"stripe size {stripe_info['stripe_size']}")
    comment = ", ".join(comment_parts) if comment_parts else "Lustre filesystem"

    stor = make_storage(
        "Lustre Parallel Filesystem", "Lustre",
        id="stor-lustre-0",
        total_amount={"quantity": total_gb, "unit": total_unit},
        comment=comment,
    )

    # Add stripe info to further_metadata
    if stripe_info:
        stor["further_metadata"] = stripe_info

    return {"storage_system": stor}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Collect Lustre filesystem info")
    parser.add_argument("--mount", default="/", help="Lustre mount point")
    args = parser.parse_args()

    import json
    result = collect(mount_point=args.mount)
    print(json.dumps(result, indent=2))
