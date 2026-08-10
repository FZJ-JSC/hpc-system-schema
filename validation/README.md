# Validation / Verification

Tooling to check HPC system descriptions against the schema and to verify the
schema itself. Both scripts are self-contained Python files with PEP 723
inline dependencies — run them with `uv run` and the required packages are
installed on the fly.

## validate-description.py

Validates a system description (JSON) against the schema (Draft-07). By
default it runs all checks; individual checks can be selected with repeatable
`--check` flags:

| Check | What it does |
|-------|--------------|
| `schema` | Structural validation via the `jsonschema` library: required fields, types, formats, enums, `$ref` resolution. |
| `inheritance` | Missing parent references and circular inheritance between parts / node types. |
| `tbd` | Reports `TBD` / placeholder values. |
| `unique` | Duplicate IDs and names across parts and node types. |
| `summary` | Prints a one-line overview of the document. |

```bash
# All checks (default)
uv run validate-description.py ../descriptions/system-jupiter.json

# Only specific checks, composably
uv run validate-description.py system.json --check schema --check inheritance

# Pick a different schema: --schema flag, SCHEMA_PATH env var, or the
# default ../schema/system-description-0.5.0.json (relative to this directory)
uv run validate-description.py system.json --schema /path/to/schema.json

# CI-friendly output (no ANSI colours)
uv run validate-description.py system.json --no-color
```

Exit codes: `0` all selected checks pass, `1` one or more checks fail,
`2` usage error or input file not found.

## verify-schema.py

Verifies the schema itself: validates it against the JSON Meta-Schema
(Draft-07) and runs structural checks — presence of `definitions`,
`properties`, and `required`, the `schema_version` enum, the `$id`, that all
`$ref` targets resolve, and that all `x-suggested` fields are well-formed.

```bash
uv run verify-schema.py
```

The schema path can be overridden with the `SCHEMA_PATH` environment
variable; by default it points at `../schema/system-description-0.5.0.json`.

Both tools exit non-zero on failure, so they can be used directly in CI
workflows and GitHub Actions.
