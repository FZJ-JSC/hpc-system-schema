#!/bin/sh
# Regenerate every recorded questionnaire of this tool. Run from anywhere; paths
# resolve relative to this script.
set -e

cd "$(dirname "$0")"
S=../../schema/system-description-0.5.0.json

echo "== schema =="
python3 - "$S" <<'PY'
import json, sys

def count(node):
    total = 0
    for value in node.values():
        if isinstance(value, dict):
            total += 1 if "properties" in value else 0
            total += count(value)
    return total

schema = json.load(open(sys.argv[1]))
meta = schema.get("x-schema-metadata", {})
print(f"  {sys.argv[1]}: version {meta.get('schema_version', '?')}, "
      f"{count(schema['definitions'])} object definitions")
PY

echo "== questionnaires =="
python3 generate.py --schema "$S" --out results/tender-template.md
python3 generate.py --schema "$S" --omit "Accelerator,NUMA domain" \
    --out results/tender-cpu-only.md

echo "results regenerated in results/"
