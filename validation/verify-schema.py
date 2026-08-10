#!/usr/bin/env python3
# /// script
# dependencies = [
#   "jsonschema"
# ]
# ///
"""
Verify that the HPC System Definition JSON schema itself is structurally valid.

Checks the schema file against the JSON Meta-Schema (Draft-07).
This does NOT validate any sample data — it only validates the schema definition.
"""
import json
import os
import sys

try:
    from jsonschema import Draft7Validator
except ImportError:
    print("ERROR: jsonschema not installed.  pip install jsonschema")
    sys.exit(2)

SCHEMA_PATH = os.environ.get(
    "SCHEMA_PATH",
    os.path.join(os.path.dirname(__file__), os.pardir, "schemas", "system-definition-v1.json"),
)

if "--help" in sys.argv or "-h" in sys.argv:
    print(__doc__)
    print(f"Default schema: {SCHEMA_PATH}")
    print("Set SCHEMA_PATH env var to override.")
    sys.exit(0)


def main():
    # --- Load schema under test ---
    try:
        with open(SCHEMA_PATH) as f:
            schema = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: schema not found: {SCHEMA_PATH}")
        sys.exit(2)
    except json.JSONDecodeError as e:
        print(f"ERROR: invalid JSON in schema: {e}")
        sys.exit(1)

    # --- Load JSON Meta-Schema (Draft-07) ---
    meta_schema = Draft7Validator.META_SCHEMA

    # --- Validate schema against meta-schema ---
    meta_validator = Draft7Validator(meta_schema)
    errors = sorted(meta_validator.iter_errors(schema), key=lambda e: list(e.absolute_path))

    ok = 0
    if errors:
        for err in errors:
            path = ".".join(str(p) for p in err.absolute_path) or "(root)"
            print(f"  [FAIL] {path}: {err.message}")
    else:
        print("  [PASS] Schema validates against JSON Meta-Schema (Draft-07)")
        ok += 1

    # --- Structural checks ---
    # 1. Has definitions
    defs = schema.get("definitions", {})
    if defs:
        print(f"  [PASS] Has definitions ({len(defs)} groups)")
        ok += 1
    else:
        print("  [FAIL] Missing 'definitions'")

    # 2. Has properties
    props = schema.get("properties", {})
    if props:
        print(f"  [PASS] Has properties ({len(props)} root fields)")
        ok += 1
    else:
        print("  [FAIL] Missing root 'properties'")

    # 3. Has required
    req = schema.get("required", [])
    if req:
        print(f"  [PASS] Has required ({len(req)}: {', '.join(req)})")
        ok += 1
    else:
        print("  [FAIL] Missing root 'required'")

    # 4. Schema version
    ver = schema.get("properties", {}).get("schema_version", {}).get("enum", [])
    if ver:
        print(f"  [PASS] schema_version enum: {ver}")
        ok += 1
    else:
        print("  [FAIL] schema_version has no enum")

    # 5. $id present
    sid = schema.get("$id", "")
    if sid:
        print(f"  [PASS] $id: {sid}")
        ok += 1
    else:
        print("  [FAIL] Missing $id")

    # 6. Check all $ref targets exist
    def find_refs(obj, path="$"):
        refs = []
        if isinstance(obj, dict):
            if "$ref" in obj:
                refs.append((path, obj["$ref"]))
            for k, v in obj.items():
                refs.extend(find_refs(v, f"{path}.{k}"))
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                refs.extend(find_refs(v, f"{path}[{i}]"))
        return refs

    all_refs = find_refs(schema)
    broken = []
    for ref_path, ref_val in all_refs:
        if not ref_val.startswith("#/"):
            continue  # external refs — skip
        parts = ref_val.lstrip("#/").split("/")
        target = schema
        for p in parts:
            if isinstance(target, dict) and p in target:
                target = target[p]
            else:
                broken.append((ref_path, ref_val))
                break

    if broken:
        for ref_path, ref_val in broken:
            print(f"  [FAIL] Broken $ref at {ref_path}: {ref_val}")
    else:
        print(f"  [PASS] All {len(all_refs)} $ref targets resolve")
        ok += 1

    # --- x-suggested checks ---
    def check_x_suggested(obj, path="$"):
        """Validate x-suggested arrays/objects in the schema."""
        issues = []
        if isinstance(obj, dict):
            if "x-suggested" in obj:
                val = obj["x-suggested"]
                if isinstance(val, list):
                    if len(val) == 0:
                        issues.append(f"{path}.x-suggested: empty array")
                    for i, item in enumerate(val):
                        if isinstance(item, list):
                            issues.append(f"{path}.x-suggested[{i}]: nested array (not allowed)")
                elif isinstance(val, dict):
                    pass  # Single object — acceptable
                else:
                    issues.append(f"{path}.x-suggested: unexpected type {type(val).__name__}")
            for k, v in obj.items():
                issues.extend(check_x_suggested(v, f"{path}.{k}"))
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                issues.extend(check_x_suggested(v, f"{path}[{i}]"))
        return issues

    xs_issues = check_x_suggested(schema)
    if xs_issues:
        for issue in xs_issues:
            print(f"  [FAIL] {issue}")
    else:
        # Count x-suggested fields
        def count_x_suggested(obj):
            c = 0
            if isinstance(obj, dict):
                if 'x-suggested' in obj:
                    c += 1
                for v in obj.values():
                    c += count_x_suggested(v)
            elif isinstance(obj, list):
                for v in obj:
                    c += count_x_suggested(v)
            return c
        xs_count = count_x_suggested(schema)
        print(f"  [PASS] All x-suggested fields valid ({xs_count} found)")
        ok += 1

    # Summary
    total_fails = len(errors) + len(broken) + len(xs_issues)
    print(f"\n{'ALL CHECKS PASSED' if ok >= 7 and total_fails == 0 else 'SOME CHECKS FAILED'}: "
          f"{ok} passed, {total_fails} failed")
    sys.exit(1 if total_fails else 0)


if __name__ == "__main__":
    main()
