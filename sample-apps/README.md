# Sample Applications

Example applications and tooling built on the HPC System Description Schema.
All of them read and/or produce schema-conformant system descriptions (v0.5.0),
such as the examples in [`../descriptions/`](../descriptions/).

| Directory | What it does |
|-----------|--------------|
| [`api/`](api/) | Read-only Flask REST API that serves a system description over HTTP: parts, node types, CPUs, memory, accelerators, statistics. |
| [`collecting-tools/`](collecting-tools/) | Collectors that gather hardware information from a running system (`lscpu`, `nvidia-smi`, `dmidecode`, …) and emit schema-conformant JSON, plus a merge tool. |
| [`gui-generator/`](gui-generator/) | Single-file, browser-based editor for creating and editing system descriptions, driven directly by the schema (including `x-suggested` value hints). |
| [`tex-table-compare/`](tex-table-compare/) | Generates LaTeX comparison tables from two or more system descriptions. |

## Quick start

```bash
# REST API — serve a system description
uv run api/main.py ../descriptions/system-jupiter.json

# Collecting tools — gather hardware info on a live node
cd collecting-tools && python3 collect.py --output system-hardware.json

# GUI editor — just open the HTML file in a browser
open gui-generator/index.html

# LaTeX comparison table — build .tex (default) or .pdf
cd tex-table-compare && make
```

Each application has its own README (or will get one) with more detailed
documentation, usage examples, and requirements.
