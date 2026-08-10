# System Descriptions

Example system descriptions conforming to the HPC System Description Schema (v0.5.0).

| File | System | Notes |
|------|--------|-------|
| `system-jupiter.json` | JUPITER (JSC) | Complete reference example: Booster, login nodes, ExaSTORE and ExaFLASH storage |
| `system-frontier.json` | Frontier (OLCF) | More detailed description |
| `system-frontier-min.json` | Frontier (OLCF) | Minimal |
| `system-aurora-minimal.json` | Aurora (ALCF) | Minimal |
| `system-elcapitan-minimal.json` | El Capitan (LLNL) | Minimal |
| `system-lineshine-minimal.json` | LineShine (NSCS, Shenzhen) | Minimal |
| `system-marenostrum5-minimal.yaml` | MareNostrum 5 (BSC) | Minimal; YAML format |

Notes:

- The `*-minimal` files are stripped-down descriptions that serve as starting points; `system-jupiter.json` is the most complete and is used by the sample applications and the API.
- JSON is the canonical format. The MareNostrum 5 example demonstrates YAML as an editing convenience; the validation tooling currently expects JSON input.
- Values that are not publicly documented are marked `TBD` instead of guessed.

Validate a description with:

```bash
uv run ../validation/validate-description.py system-jupiter.json \
    --schema ../schema/system-description-0.5.0.json
```
