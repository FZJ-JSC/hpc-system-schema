# HPC System Description Schema

> [!TIP]
> [🌐 **GitHub Pages site**](https://fzj-jsc.github.io/hpc-system-schema/) — browse the schema, use the browser-based editor, and view example system descriptions.

A vendor-neutral [JSON Schema](https://json-schema.org/) (Draft-07) for describing HPC systems in a structured, machine-readable way. A system description covers the full machine: partitions, node types, CPUs, accelerators, memory, on-node and parallel storage, network interconnect, power and cooling, and the software stack.

The current schema version is **0.5.0**; the canonical definition is [`schema/system-description-0.5.0.json`](schema/system-description-0.5.0.json), which carries a stable `$id`. Real systems described with it include the JUPITER exascale system (see [`descriptions/`](descriptions/)).

## Schema highlights

- Hierarchical, namespaced definitions (`hardware/`, `software/`, `common/`) covering system parts, node designs and their components.
- Inheritance between parts and node types (`inherits_from`) to avoid repetition.
- Suggested values (`x-suggested`) embedded in the schema to guide editors and tooling.
- Free-form extension points (`further_metadata`, `comment`) at every level.
- Quantities as `{quantity, unit}` pairs; timestamps in RFC3339 format.
- Two version numbers per document: the schema version and the description's own semantic version.

## Repository layout

| Directory | Contents |
|-----------|----------|
| [`schema/`](schema/) | The core schema: `system-description-0.5.0.json` (JSON Schema Draft-07) and `system_description_0.5.0.py` (equivalent Marshmallow schema; experimental). |
| [`descriptions/`](descriptions/) | Example system descriptions: JUPITER (complete), plus minimal examples for Frontier, Aurora, El Capitan, MareNostrum 5 (YAML), and LineShine. |
| [`validation/`](validation/) | Tooling to validate descriptions against the schema and to verify the schema itself. |
| [`docs/`](docs/) | Generated schema documentation (HTML). |
| [`sample-apps/`](sample-apps/) | Example applications built on the schema: REST API, hardware collecting tools, browser-based editor, LaTeX comparison tables. |

## Validation/Verification Quick start

Requires [uv](https://docs.astral.sh/uv/), which installs the needed dependencies on the fly.

```bash
# Validate a system description against the schema
uv run validation/validate-description.py descriptions/system-jupiter.json \
    --schema schema/system-description-0.5.0.json

# Verify the schema itself against the JSON Schema meta-schema
SCHEMA_PATH=schema/system-description-0.5.0.json \
    uv run validation/verify-schema.py
```

## Schema documentation

An HTML rendering of the schema is available at [`docs/index.html`](docs/index.html). It is generated with [json-schema-for-humans](https://github.com/coveooss/json-schema-for-humans); see [`docs/README.md`](docs/README.md) for details.

## Website

The repository is published as a GitHub Pages site with the schema, its
documentation, the browser-based editor, and example descriptions. The landing
page source is [`docs/index_landing.html`](docs/index_landing.html);
[`build-site.py`](build-site.py) assembles the deployable site from the
repository sources (renaming the landing page to `index.html` during the
build):

```bash
python3 build-site.py                    # build into a fresh temp directory
python3 build-site.py site-preview       # build into a named directory
python3 -m http.server 8080 -d site-preview   # preview locally
```

Nothing is generated into the repository itself — the site is assembled in
the runner workspace and deployed to GitHub Pages on every push to `main` via
[`.github/workflows/pages.yml`](.github/workflows/pages.yml).

## Sample applications

- [`sample-apps/gui-generator/`](sample-apps/gui-generator/) — single-file browser-based editor for system descriptions.
- [`sample-apps/tex-table-compare/`](sample-apps/tex-table-compare/) — generate LaTeX comparison tables from several system descriptions.
- [`sample-apps/api/`](sample-apps/api/) — read-only Flask REST API for browsing a system description.
- [`sample-apps/collecting-tools/`](sample-apps/collecting-tools/) — collectors that gather hardware information from a running system (`lscpu`, `nvidia-smi`, `dmidecode`, …) and emit schema-conformant JSON.


## License

MIT — see [LICENSE](LICENSE).
