# Schema Documentation

This directory contains the rendered HTML documentation of the HPC System
Description Schema and the tooling to regenerate it.

## Contents

- `index.html` — browsable documentation of the schema; open it directly in a browser.
- `schema_doc.css`, `schema_doc.min.js` — assets used by `index.html`.
- `generate-docs.json` — configuration for the documentation generator.
- `Makefile` — build script that regenerates the documentation.

## Regenerating

The documentation is generated with
[json-schema-for-humans](https://github.com/coveooss/json-schema-for-humans).
Requires `uv` / `uvx`.

```bash
make            # regenerate docs (only if schema or config changed)
make clean      # remove generated files (index.html, css, js)
```

`make` renders `../schema/system-description-0.5.0.json` to `index.html`,
using the options in `generate-docs.json` (table of contents, expandable
sections, markdown descriptions, links to reused `$ref`s).

`index.html` and its assets are generated artifacts — do not edit them by
hand; change the schema or the configuration and re-run `make` instead.
