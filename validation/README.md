# Validation / Verification

Initial tooling to

- Validate a description as per the schema (`validate-description.py`)
- Verify the schema itself (`verify-schema`)

Run like

```bash
uv run verify-schema.py
```

and `uv` will read the `dependencies` header to install the required dependencies on-the-fly.

Currently, description validation is match more extensive and proper than the schema verification.