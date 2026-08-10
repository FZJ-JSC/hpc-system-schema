"""
Feature definitions for HPC system comparison tables.

Each feature is a dict with:
  - key:      unique identifier for sorting / deduplication
  - label:    LaTeX-safe label for the left column
  - extract:  callable(data) -> str | None
             receives the parsed JSON, returns a LaTeX-ready string or None

To add a new feature, append to FEATURES.  The order in the list is the
order in the generated table.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _q(unit_obj: dict | None) -> str:
    """Format a QuantityWithUnit dict into a compact string with \num{}."""
    if not unit_obj:
        return "---"
    q = unit_obj.get("quantity", "?")
    u = unit_obj.get("unit", "")
    return f"\\num{{{q}}} {u}"


def _first_compute_part(data: dict) -> dict | None:
    """Return the first compute partition, or None."""
    for p in data.get("parts", []):
        if p.get("part_type") == "compute":
            return p
    return None


def _first_gpu_node_type(part: dict) -> dict | None:
    """Return the first node type that has accelerators."""
    for nt in part.get("node_types", []):
        if nt.get("accelerators"):
            return nt
    return None


# ---------------------------------------------------------------------------
# Feature registry  (append new features here)
# ---------------------------------------------------------------------------

FEATURES: list[dict] = [
    # ── 1. System name ──
    {
        "key": "system_name",
        "label": "System",
        "extract": lambda d: d.get("name", "---"),
    },

    # ── 2. Location ──
    {
        "key": "location",
        "label": "Location",
        "extract": lambda d: d.get("location", "---"),
    },

    # ── 3. Compute nodes ──
    {
        "key": "compute_nodes",
        "label": "Compute Nodes",
        "extract": lambda d: _fmt_int(
            (_first_compute_part(d) or {}).get("node_count")
        ),
    },

    # ── 4. CPU vendor + model ──
    {
        "key": "cpu",
        "label": "CPU",
        "extract": lambda d: _cpu_label(d),
    },

    # ── 5. CPU cores per node ──
    {
        "key": "cpu_cores",
        "label": "CPU Cores / Node",
        "extract": lambda d: _cpu_cores(d),
    },

    # ── 6. Accelerator vendor + model ──
    {
        "key": "accelerator",
        "label": "Accelerator",
        "extract": lambda d: _accel_label(d),
    },

    # ── 7. Accelerators per node ──
    {
        "key": "accel_count",
        "label": "Acc. / Node",
        "extract": lambda d: _accel_count(d),
    },

    # ── 8. Accelerator memory ──
    {
        "key": "accel_memory",
        "label": "Memory / Acc.",
        "extract": lambda d: _accel_memory(d),
    },

    # ── 9. Node memory ──
    {
        "key": "node_memory",
        "label": "CPU Memory / Node",
        "extract": lambda d: _node_memory(d),
    },

    # ── 10. Peak power ──
    {
        "key": "peak_power",
        "label": "Peak Power",
        "extract": lambda d: _q(
            (_first_compute_part(d) or {}).get("power_draw_peak")
        ),
    },

    # ── 11. TDP per node ──
    {
        "key": "tdp_per_node",
        "label": "TDP / Node",
        "extract": lambda d: _fmt_tdp(
            (_first_compute_part(d) or {}).get("power_details", {}).get("tdp_per_node_kw")
        ),
    },

    # ── 12. Cooling ──
    {
        "key": "cooling",
        "label": "Cooling",
        "extract": lambda d: (
            (_first_compute_part(d) or {})
            .get("cooling", {})
            .get("type", "---")
            .capitalize()
        ),
    },
]


# ---------------------------------------------------------------------------
# Extractors (kept separate for readability)
# ---------------------------------------------------------------------------

def _fmt_int(val) -> str:
    if val is None:
        return "---"
    return f"\\num{{{val:,}}}"


def _fmt_tdp(val) -> str:
    if val is None:
        return "---"
    return f"\\num{{{val}}} kW"


def _cpu_label(d: dict) -> str:
    part = _first_compute_part(d)
    if not part:
        return "---"
    for nt in part.get("node_types", []):
        for cpu in nt.get("cpus", []):
            mfr = cpu.get("manufacturer", "")
            name = cpu.get("name", "")
            if mfr or name:
                return f"{mfr} {name}".strip()
    return "---"


def _cpu_cores(d: dict) -> str:
    part = _first_compute_part(d)
    if not part:
        return "---"
    for nt in part.get("node_types", []):
        for cpu in nt.get("cpus", []):
            cores = cpu.get("cores_per_cpu")
            ncpus = cpu.get('number_of_sockets')
            if cores:
                return f"\\num{{{cores*ncpus}}}"
    return "---"


def _accel_label(d: dict) -> str:
    part = _first_compute_part(d)
    if not part:
        return "---"
    nt = _first_gpu_node_type(part)
    if not nt:
        return "None"
    for acc in nt.get("accelerators", []):
        mfr = acc.get("manufacturer", "")
        name = acc.get("name", "")
        if mfr or name:
            return f"{mfr} {name}".strip()
    return "None"


def _accel_count(d: dict) -> str:
    part = _first_compute_part(d)
    if not part:
        return "---"
    nt = _first_gpu_node_type(part)
    if not nt:
        return "0"
    for acc in nt.get("accelerators", []):
        c = acc.get("count_per_node")
        if c is not None:
            return f"\\num{{{c}}}"
    return "0"


def _accel_memory(d: dict) -> str:
    part = _first_compute_part(d)
    if not part:
        return "---"
    nt = _first_gpu_node_type(part)
    if not nt:
        return "---"
    for acc in nt.get("accelerators", []):
        mem = acc.get("memory")
        if mem:
            amt = mem.get("amount")
            if amt:
                q = amt.get("quantity", "?")
                u = amt.get("unit", "")
                return f"\\num{{{q}}} {u}"
    return "---"


def _node_memory(d: dict) -> str:
    part = _first_compute_part(d)
    if not part:
        return "---"
    for nt in part.get("node_types", []):
        mem_entries = []
        for mem in nt.get("memory", []):
            amt = mem.get("amount")
            mtype = mem.get("type", "")
            if amt:
                q = amt.get("quantity", "?")
                u = amt.get("unit", "")
                suffix = f" {mtype}" if mtype else ""
                mem_entries.append(f"\\num{{{q}}} {u}{suffix}")
        if mem_entries:
            return " + ".join(mem_entries)
    return "---"
