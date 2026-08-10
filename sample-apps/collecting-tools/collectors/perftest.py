#!/usr/bin/env python3
"""Run InfiniBand perftest benchmarks and collect results.

Runs ib_write_bw, ib_read_lat (or reads from saved files) to collect
bandwidth and latency measurements. Results are stored in further_metadata.
"""

import re
import sys
import os
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from collect_lib import run_cmd, warn_tool

TOOL_NAME = "perftest"


def _parse_ib_write_bw(output: str) -> dict:
    """Parse ib_write_bw output for bandwidth results."""
    result = {}
    for line in output.split("\n"):
        # ib_write_bw output has lines like:
        # #bytes  #iterations   BW peak [Gb/s]   BW average [Gb/s]
        #  65536    1000         198.56           197.23
        parts = line.split()
        if len(parts) >= 4 and parts[0].isdigit():
            msg_size = int(parts[0])
            bw_avg = float(parts[-1])
            if msg_size >= 1048576:  # 1MB+ messages
                result[f"bandwidth_{msg_size // 1024}KB"] = {
                    "quantity": round(bw_avg, 2),
                    "unit": "Gb/s"
                }
    return result


def _parse_ib_read_lat(output: str) -> dict:
    """Parse ib_read_lat output for latency results."""
    result = {}
    for line in output.split("\n"):
        parts = line.split()
        if len(parts) >= 5 and parts[0].isdigit():
            msg_size = int(parts[0])
            # Average latency is typically in column 4 (0-indexed)
            try:
                lat_us = float(parts[-2])  # second to last is usually avg
                if lat_us > 0:
                    result[f"latency_{msg_size}B"] = {
                        "quantity": round(lat_us, 3),
                        "unit": "us"
                    }
            except (ValueError, IndexError):
                pass
    return result


def collect(server_ip: str = None, interface: str = None) -> dict:
    """Run IB perftest benchmarks.

    Args:
        server_ip: IP of the remote server for client-side tests.
                   If None, runs in server mode or skips.
        interface: IB device to test (e.g., mlx5_0).

    Returns:
        Dict with perftest data suitable for FurtherMetadata.
    """
    if not run_cmd("which ib_write_bw") and not run_cmd("which ib_read_lat"):
        warn_tool("ib_write_bw/ib_read_lat", "InfiniBand performance (install perftest)")
        return {}

    device_flag = f"-d {interface}" if interface else ""
    perf_data = {}

    # Bandwidth test
    if server_ip:
        # Client mode
        bw_output = run_cmd(f"ib_write_bw {device_flag} -s 1048576 --report_gbits {server_ip}", timeout=60)
    else:
        # Try to find if there's another node; otherwise skip
        bw_output = run_cmd(f"ib_write_bw {device_flag} -s 1048576 --report_gbits", timeout=10)

    if bw_output:
        perf_data["bandwidth"] = _parse_ib_write_bw(bw_output)

    # Latency test
    if server_ip:
        lat_output = run_cmd(f"ib_read_lat {device_flag} --report_gbits {server_ip}", timeout=60)
    else:
        lat_output = run_cmd(f"ib_read_lat {device_flag} --report_gbits", timeout=10)

    if lat_output:
        perf_data["latency"] = _parse_ib_read_lat(lat_output)

    if perf_data:
        return {"further_metadata": {"ib_perftest": perf_data}}
    return {}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Collect IB perftest data")
    parser.add_argument("--server", help="Remote server IP for client-side tests")
    parser.add_argument("--device", help="IB device (e.g., mlx5_0)")
    args = parser.parse_args()

    import json
    result = collect(server_ip=args.server, interface=args.device)
    print(json.dumps(result, indent=2))
