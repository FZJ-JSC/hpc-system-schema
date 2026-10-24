# System diff

Compares two system descriptions field by field and reports the differences
grouped by level: system, part, node type, component.

## Usage

```bash
# two different systems (aligned by position, since ids differ by construction)
python3 diff.py ../../descriptions/system-jupiter.json ../../descriptions/system-frontier-min.json

# two versions of one system (aligned by node type id)
python3 diff.py old.json new.json --align id

# only the fields both descriptions carry, as a Markdown table for a paper
python3 diff.py a.json b.json --exclude-identity --shared-only --format md --limit 20
```

`--exclude-identity` drops `name`, `id`, `location`, `website`, `provider` and
similar fields, so what remains is technical content. `--format summary|md|latex`
selects the output; `latex` emits bare table rows.

`summarize.py` prints axis overlap for a set of descriptions, one row per pair:

```bash
python3 summarize.py ../../descriptions/system-*.json
```

## Recorded results

- [`results/diff-summary.md`](results/diff-summary.md) — 15 pairs: fields per
  description, shared fields, differing fields, fields only one side has.
- [`results/diff-jupiter-frontier.md`](results/diff-jupiter-frontier.md),
  [`results/diff-aurora-elcapitan.md`](results/diff-aurora-elcapitan.md) — the
  differing shared fields for two pairs.

What the numbers say: two minimal descriptions of comparable exascale systems
(Aurora, El Capitan) carry 30 technical fields each, share 23 and differ on 16.
JUPITER carries 208 fields where LineShine carries 20, and the two share only 14.
Frontier against its minimal variant shares 30 fields and differs on 1 — the
version case, where `--align id` applies.

Regenerate all of the above with `./reproduce.sh`, which validates every
description against the schema first.

## Requirements

Python 3.9+, no third-party packages.
