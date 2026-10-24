# Procurement template

Generates a tender questionnaire from the schema, so that a vendor's answers come
back in a form a description can be filled from.

```bash
python3 generate.py --out tender.md
python3 generate.py --level node          # only node-level sections
python3 generate.py --omit "Accelerator,NUMA domain" --out tender-cpu-only.md
```

One section per level, required fields first, optional ones marked, and the
schema's `x-suggested` values as candidate answers so a vendor writes in the
expected vocabulary.

Each section states its cardinality, because most of them repeat: a part block
repeats per partition, a node type per node type, a CPU per socket (a two-socket
node answers twice), an accelerator per accelerator kind. Sections marked `0..N`
are to be answered "not applicable" rather than deleted, so one questionnaire
covers every system; `--omit` produces a trimmed document for a site that wants
one anyway.

## Recorded output

- [`results/tender-template.md`](results/tender-template.md) — 16 sections, 246
  fields.
- [`results/tender-cpu-only.md`](results/tender-cpu-only.md) — with the
  accelerator and NUMA blocks omitted: 14 sections, 205 fields.

Regenerate with `./reproduce.sh`.

## Requirements

Python 3.9+, no third-party packages.
