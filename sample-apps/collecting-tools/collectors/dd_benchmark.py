#!/usr/bin/env python3
"""Disk I/O benchmark using dd.

Runs sequential read/write tests with dd to measure disk throughput.
Results are stored in further_metadata as performance data.
"""

import re
import sys
import os
import time
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from collect_lib import run_cmd, warn_tool

TOOL_NAME = "dd"


def _parse_dd_output(output: str) -> dict:
    """Parse dd stderr output for throughput."""
    result = {}
    # dd output like: "1024+0 records in\n1024+0 records out\n1073741824 bytes (1.1 GB, 1.0 GiB) copied, 1.23456 s, 869.4 MB/s"
    m = re.search(r'([\d.]+)\s*([MG]B)/s', output)
    if m:
        value = float(m.group(1))
        unit = m.group(2)
        result["throughput_mbps"] = round(value * 1000, 1) if unit == "GB" else round(value, 1)
    # Also parse time
    m_time = re.search(r'copied,\s*([\d.]+)\s*s', output)
    if m_time:
        result["duration_sec"] = float(m_time.group(1))
    # Parse bytes
    m_bytes = re.search(r'([\d]+)\s*bytes', output)
    if m_bytes:
        result["bytes"] = int(m_bytes.group(1))
    return result


def collect(test_file: str = None, test_size_mb: int = 256,
            block_size: str = "1M", directory: str = None) -> dict:
    """Run dd disk I/O benchmark.

    Args:
        test_file: Path to test file. If None, uses a temp file.
        test_size_mb: Size of test file in MB.
        block_size: Block size for dd (e.g., "1M", "4K").
        directory: Directory to test in. Uses system temp dir if None.

    Returns:
        Dict with performance data suitable for FurtherMetadata.
    """
    if directory is None:
        directory = tempfile.gettempdir()

    if test_file is None:
        test_file = os.path.join(directory, f"collect_bench_{os.getpid()}.dat")

    results = {}
    count = test_size_mb  # since block_size is in MB

    try:
        # Write test
        write_cmd = f"dd if=/dev/zero of={test_file} bs={block_size} count={count} oflag=direct 2>&1"
        write_output = run_cmd(write_cmd, timeout=120)
        if write_output:
            wr = _parse_dd_output(write_output)
            if wr.get("throughput_mbps"):
                results["sequential_write"] = {
                    "quantity": wr["throughput_mbps"],
                    "unit": "MB/s",
                    "comment": f"dd {block_size} blocks, {test_size_mb} MB file"
                }

        # Read test
        read_cmd = f"dd if={test_file} of=/dev/null bs={block_size} iflag=direct 2>&1"
        read_output = run_cmd(read_cmd, timeout=120)
        if read_output:
            rd = _parse_dd_output(read_output)
            if rd.get("throughput_mbps"):
                results["sequential_read"] = {
                    "quantity": rd["throughput_mbps"],
                    "unit": "MB/s",
                    "comment": f"dd {block_size} blocks, {test_size_mb} MB file"
                }

    finally:
        # Clean up
        try:
            if os.path.exists(test_file):
                os.unlink(test_file)
        except OSError:
            pass

    if results:
        return {"further_metadata": {"dd_benchmark": results}}
    return {}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run dd disk benchmark")
    parser.add_argument("--size", type=int, default=256, help="Test size in MB")
    parser.add_argument("--block", default="1M", help="Block size")
    parser.add_argument("--dir", default=None, help="Test directory")
    args = parser.parse_args()

    import json
    result = collect(test_size_mb=args.size, block_size=args.block, directory=args.dir)
    print(json.dumps(result, indent=2))
