#!/usr/bin/env python3
"""Collect GPU information from nvidia-smi.

Parses `nvidia-smi --query-gpu=... --format=csv` to extract GPU model,
memory, core count, clock rate, TDP, and count per node.
"""

import re
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from collect_lib import run_cmd, make_accelerator, warn_tool

TOOL_NAME = "nvidia-smi"


def _gpu_model_to_arch(name: str) -> str:
    """Infer GPU architecture from model name."""
    name_lower = name.lower()
    if any(x in name_lower for x in ("h100", "h200")):
        return "Hopper"
    if any(x in name_lower for x in ("a100", "a30")):
        return "Ampere"
    if any(x in name_lower for x in ("hopper",)):
        return "Hopper"
    if any(x in name_lower for x in ("a10", "l4", "rtx 40", "rtx 30", "t4")):
        return "Ada Lovelace" if "l4" in name_lower or "40" in name_lower else "Ampere"
    if any(x in name_lower for x in ("v100",)):
        return "Volta"
    if any(x in name_lower for x in ("mi250", "mi300")):
        return "CDNA"
    if any(x in name_lower for x in ("p100",)):
        return "Pascal"
    if any(x in name_lower for x in ("k80", "k40")):
        return "Kepler"
    if any(x in name_lower for x in ("max 1550", "max 1100", "ponte vecchio")):
        return "Ponte Vecchio"
    return "Unknown"


def collect() -> dict:
    """Collect GPU information from nvidia-smi.

    Returns:
        Dict with 'accelerators' key.
    """
    if not run_cmd("which nvidia-smi"):
        warn_tool("nvidia-smi", "GPU information (NVIDIA driver required)")
        return {}

    query_fields = [
        "index", "name", "memory.total", "memory.used",
        "clocks.gr", "clocks.max.gr", "power.limit",
        "driver_version", "cuda_version",
        "compute_cap", "clocks.sm", "temperature.gpu",
        "utilization.gpu"
    ]
    cmd = f"nvidia-smi --query-gpu={','.join(query_fields)} --format=csv,noheader,nounits"
    output = run_cmd(cmd)
    if not output:
        return {}

    gpus = []
    for line in output.strip().split("\n"):
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 5:
            continue

        # Map fields
        data = {}
        for i, field in enumerate(query_fields):
            if i < len(parts):
                val = parts[i]
                if val == "[N/A]":
                    val = None
                data[field] = val

        name = data.get("name", "Unknown GPU")
        mem_mb = float(data.get("memory.total", "0") or "0")
        mem_gb = round(mem_mb / 1024, 1)
        clock_mhz = float(data.get("clocks.gr", "0") or "0")
        power_w = float(data.get("power.limit", "0") or "0")
        compute_cap = data.get("compute_cap", "")
        driver = data.get("driver_version", "")

        acc = make_accelerator(
            "NVIDIA", name,
            count=1,
            mem_gb=mem_gb,
            mem_type="HBM2e" if "hbm" in name.lower() else "GDDR6X" if "x" in name.lower() else "HBM3" if "h100" in name.lower() or "h200" in name.lower() else "HBM2e",
            architecture=_gpu_model_to_arch(name),
            isa="CUDA",
            id=f"gpu-{data.get('index', '0')}",
        )
        if clock_mhz > 0:
            acc["clock_rate"] = {"quantity": clock_mhz, "unit": "MHz"}
        if power_w > 0:
            acc["tdp"] = {"quantity": power_w, "unit": "W"}

        # Add compute capability and driver to further_metadata
        fm = {}
        if compute_cap:
            fm["compute_capability"] = compute_cap
        if driver:
            fm["driver_version"] = driver
        cuda_ver = data.get("cuda_version")
        if cuda_ver:
            fm["cuda_version"] = cuda_ver
        if fm:
            acc["further_metadata"] = fm

        gpus.append(acc)

    # Aggregate: all identical GPUs are one accelerator type
    if not gpus:
        return {}

    # Group by model name
    from collections import defaultdict
    groups = defaultdict(list)
    for gpu in gpus:
        groups[gpu["name"]].append(gpu)

    accelerators = []
    for model, gpu_list in groups.items():
        # Take the first GPU as the template
        agg = dict(gpu_list[0])
        agg["count_per_node"] = len(gpu_list)
        agg["id"] = f"gpu-{model.lower().replace(' ', '-')}"
        accelerators.append(agg)

    return {"accelerators": accelerators}


if __name__ == "__main__":
    import json
    result = collect()
    print(json.dumps(result, indent=2))
