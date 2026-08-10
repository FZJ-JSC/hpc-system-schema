#!/usr/bin/env python3
"""Collect BMC/IPMI information from ipmitool.

Parses `ipmitool` commands to extract BMC firmware, power consumption,
thermal sensors, and board information. Maps to SystemPart and FurtherMetadata.
"""

import re
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from collect_lib import run_cmd, warn_tool

TOOL_NAME = "ipmitool"


def _parse_sdr_power(output: str) -> dict:
    """Parse SDR power sensor readings."""
    result = {}
    for line in output.split("\n"):
        # Power sensors often have names like "System Level", "CPU1 Power"
        if "watt" in line.lower() or "power" in line.lower():
            # Extract the power value
            m = re.search(r'([\d.]+)\s*W', line)
            if m:
                power_w = float(m.group(1))
                if "System Level" in line or "Total" in line:
                    result["system_power_w"] = power_w
                elif "CPU" in line:
                    result.setdefault("cpu_power_w", 0)
                    result["cpu_power_w"] += power_w
                elif "GPU" in line or "Accelerator" in line:
                    result.setdefault("gpu_power_w", 0)
                    result["gpu_power_w"] += power_w
    return result


def _parse_fru(output: str) -> dict:
    """Parse FRU (Field Replaceable Unit) information."""
    info = {}
    for line in output.split("\n"):
        line = line.strip()
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        key_lower = key.lower()
        if "manufacturer" in key_lower and val and val not in ("NA", "N/A", "Unknown"):
            info["manufacturer"] = val
        elif "product" in key_lower and "name" in key_lower and val:
            info["product_name"] = val
        elif "board" in key_lower and "serial" in key_lower and val:
            info["serial_number"] = val
    return info


def collect() -> dict:
    """Collect BMC/IPMI information.

    Returns:
        Dict with power, cooling, and further_metadata fields.
    """
    if not run_cmd("which ipmitool"):
        warn_tool("ipmitool", "BMC/power/thermal information")
        return {}

    result = {}

    # Get FRU info for board details
    fru_output = run_cmd("ipmitool fru list", sudo=True)
    if fru_output:
        fru = _parse_fru(fru_output)
        if fru:
            result["further_metadata"] = {f"ipmi_{k}": v for k, v in fru.items()}

    # Get power readings
    sdr_output = run_cmd("ipmitool sdr list", sudo=True)
    if sdr_output:
        power = _parse_sdr_power(sdr_output)
        if power:
            fm = result.setdefault("further_metadata", {})
            if "system_power_w" in power:
                fm["ipmi_system_power_w"] = str(int(power["system_power_w"]))
            if "cpu_power_w" in power:
                fm["ipmi_cpu_power_w"] = str(int(power["cpu_power_w"]))
            if "gpu_power_w" in power:
                fm["ipmi_gpu_power_w"] = str(int(power["gpu_power_w"]))

    # Get BMC info
    mc_output = run_cmd("ipmitool mc info", sudo=True)
    if mc_output:
        fm = result.setdefault("further_metadata", {})
        for line in mc_output.split("\n"):
            if "Firmware Revision" in line:
                val = line.split(":", 1)[1].strip()
                fm["bmc_firmware"] = val
            elif "IPMI Version" in line:
                val = line.split(":", 1)[1].strip()
                fm["ipmi_version"] = val
            elif "Manufacturer" in line:
                val = line.split(":", 1)[1].strip()
                if val and val not in ("NA", "N/A"):
                    fm["bmc_manufacturer"] = val

    # Get thermal info (temperature sensors)
    temp_output = run_cmd("ipmitool sdr type Temperature", sudo=True)
    if temp_output:
        temps = []
        for line in temp_output.split("\n"):
            m = re.search(r'([\d.]+)\s*degrees', line)
            if m:
                temps.append(float(m.group(1)))
        if temps:
            fm = result.setdefault("further_metadata", {})
            fm["thermal_sensors"] = str(len(temps))
            fm["avg_temperature_c"] = str(round(sum(temps) / len(temps), 1))

    if result:
        return result
    return {}


if __name__ == "__main__":
    import json
    result = collect()
    print(json.dumps(result, indent=2))
