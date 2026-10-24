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
| [`system-diff/`](system-diff/) | Compares two descriptions field by field, grouped by level (system, part, node type, component); aligns by position across systems or by id across versions. |
| [`procurement-template/`](procurement-template/) | Generates a tender questionnaire from the schema: per level, required fields first, `x-suggested` values as candidate answers. |

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

# System diff — what differs between two descriptions
python3 system-diff/diff.py ../descriptions/system-jupiter.json ../descriptions/system-frontier-min.json

# Procurement questionnaire — a tender template from the schema
python3 procurement-template/generate.py --out tender.md

# Each tool regenerates its own recorded output
cd system-diff && ./reproduce.sh
cd procurement-template && ./reproduce.sh
```

Each application has its own README (or will get one) with more detailed
documentation, usage examples, and requirements. `system-diff/` and
`procurement-template/` also ship a `reproduce.sh` that regenerates the recorded
output in their `results/` directory.
