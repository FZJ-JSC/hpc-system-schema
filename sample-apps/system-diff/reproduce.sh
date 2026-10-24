#!/bin/sh
# Validate the example descriptions, then regenerate every recorded result of
# this tool. Run from anywhere; paths resolve relative to this script.
set -e

cd "$(dirname "$0")"
D=../../descriptions

echo "== validating descriptions against the schema =="
python3 - "$D" <<'PY'
import glob, json, sys
try:
    import jsonschema
except ImportError:
    sys.exit("install jsonschema: uv pip install jsonschema")

schema = json.load(open("../../schema/system-description-0.5.0.json"))
validator = jsonschema.Draft7Validator(
    schema, format_checker=jsonschema.Draft7Validator.FORMAT_CHECKER)
failed = 0
for path in sorted(glob.glob(f"{sys.argv[1]}/*.json")):
    errors = list(validator.iter_errors(json.load(open(path))))
    print(f"  {'ok ' if not errors else 'FAIL'} {path}")
    for error in errors[:3]:
        print(f"       {'/'.join(str(p) for p in error.path)}: {error.message}")
    failed += bool(errors)
sys.exit(f"{failed} description(s) invalid" if failed else 0)
PY

echo "== axis overlap across all pairs =="
python3 summarize.py "$D"/system-*.json > results/diff-summary.md

echo "== per-pair field listings =="
python3 diff.py "$D/system-jupiter.json" "$D/system-frontier-min.json" \
    --exclude-identity --shared-only --format md --limit 30 > results/diff-jupiter-frontier.md
python3 diff.py "$D/system-aurora-minimal.json" "$D/system-elcapitan-minimal.json" \
    --exclude-identity --shared-only --format md --limit 30 > results/diff-aurora-elcapitan.md

echo "results regenerated in results/"
