#!/usr/bin/env python3
"""Generate a procurement template from the HPC system description schema.

The point of the exercise: a tender asks for a system in words, and every vendor
answers in its own. If the questionnaire is derived from the schema instead of
written by hand, the answers come back in a form that already validates -- and
the required fields are exactly the ones a description needs anyway.

Output is Markdown: one section per level, required keys first, optional keys
after, and the schema's x-suggested values as candidate answers so a vendor
knows the expected vocabulary.

Usage:
    python3 generate.py [--schema PATH] [--level part|node|all] [--out FILE]
"""

from __future__ import annotations

import argparse
import json
import os
import sys

DEFAULT_SCHEMA = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "schema", "system-description-0.5.0.json",
))

# Levels in the order a questionnaire should ask them.
# (section, definition path, scope, cardinality line)
LEVELS = [
    ("System", None, None, "once"),
    ("Part", "hardware/system/SystemPart", None, "1..N -- repeat for every partition of the system"),
    ("Node type", "hardware/system/NodeDesign", None, "1..N -- repeat for every node type in a part"),
    ("CPU", "hardware/components/CPU", "node", "1..N -- repeat per socket; a node with two sockets answers twice"),
    ("Memory", "hardware/components/Memory", "node", "1..N -- repeat per memory tier (e.g. DDR and HBM)"),
    ("Accelerator", "hardware/components/Accelerator", "node", "0..N -- repeat per accelerator kind; omit if the system has none"),
    ("NUMA domain", "hardware/components/NumaDomain", "node", "0..N -- repeat per NUMA domain in a node"),
    ("Network adapter", "hardware/network/NetworkAdapter", "node", "0..N -- repeat per adapter kind in a node"),
    ("Link", "hardware/network/Link", "node", "0..N -- repeat per link kind"),
    ("Storage", "hardware/storage/Storage", "node", "0..N -- repeat per file system"),
    ("Global network", "hardware/network/GlobalNetwork", "part", "0..1 -- one per part"),
    ("Topology part", "hardware/network/TopologyPart", "part", "0..N -- repeat per topology segment"),
    ("Cooling", "hardware/Cooling", "part", "0..1 -- one per part"),
    ("Physical location", "hardware/PhysicalLocation", "part", "0..1 -- one per part"),
    ("Software stack", "software/stack/SoftwareStack", "part", "0..1 -- one per part"),
    ("Provider", "common/Provider", None, "once"),
]

SKIP = {"comment", "further_metadata"}


def resolve(definitions, dotted):
    node = definitions
    for part in dotted.split("/"):
        node = node[part]
    return node


def field_row(key, spec):
    kind = spec.get("type", "")
    ref = spec.get("$ref")
    if ref:
        kind = ref.rsplit("/", 1)[-1]
    elif isinstance(spec.get("items"), dict):
        ref = spec["items"].get("$ref")
        kind = f"{ref.rsplit('/', 1)[-1]}[]" if ref else f"{spec['items'].get('type', '')}[]"
    hints = spec.get("x-suggested") or []
    if isinstance(hints, dict):
        hints = [hints]          # quantities suggest a full {quantity, unit} pair
    rendered = []
    for h in hints[:4]:
        if isinstance(h, dict) and "quantity" in h:
            rendered.append(f"`{h['quantity']} {h.get('unit', '')}`".replace(" `", "`"))
        else:
            rendered.append(f"`{h}`")
    hint = ", ".join(rendered)
    if len(hints) > 4:
        hint += ", …"
    return kind, hint


def emit(name, node, required, out, cardinality):
    out.append(f"\n### {name}\n")
    out.append(f"*Occurrence:* {cardinality}.\n")
    props = node.get("properties", {}) or {}
    rows = []
    for key, spec in props.items():
        if key in SKIP:
            continue
        kind, hint = field_row(key, spec)
        rows.append((key not in required, key, kind, hint))
    rows.sort()
    out.append("| Field | Type | Answer (suggested values) |")
    out.append("|---|---|---|")
    for optional, key, kind, hint in rows:
        mark = "" if not optional else " *(optional)*"
        out.append(f"| `{key}`{mark} | {kind} | {hint} |")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", default=os.environ.get("SCHEMA_PATH", DEFAULT_SCHEMA))
    parser.add_argument("--level", default="all", choices=("all", "part", "node"),
                        help="restrict the questionnaire to one level of the hierarchy")
    parser.add_argument("--omit", default="",
                        help="comma-separated section names to leave out (e.g. 'Accelerator')")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    with open(args.schema, encoding="utf-8") as handle:
        schema = json.load(handle)
    definitions = schema["definitions"]

    out = ["# System description for tender",
           "",
           "Generated from the HPC system description schema "
           f"(version `{schema.get('x-schema-metadata', {}).get('schema_version', '?')}`).",
           "Fields marked *(optional)* may be left empty; all others are mandatory.",
           "Suggested values are examples from the schema, not an enumeration: a vendor",
           "may answer with any value of the given type.",
           "",
           "Blocks marked 1..N repeat, once per object they describe. Blocks marked 0..N are",
           "left empty when the system has none of that component -- a CPU-only procurement",
           "keeps the accelerator block and marks it not applicable, rather than deleting it,",
           "so that one questionnaire covers every system and no answer goes into free text.",
           ""]

    omitted = {o.strip().lower() for o in args.omit.split(",") if o.strip()}
    for name, path, scope, cardinality in LEVELS:
        if args.level != "all" and scope and scope != args.level:
            continue
        if name.lower() in omitted:
            continue
        if path is None:
            node, required = schema, set(schema.get("required", []) or [])
        else:
            node = resolve(definitions, path)
            required = set(node.get("required", []) or [])
        emit(name, node, required, out, cardinality)

    text = "\n".join(out) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text)
        fields = text.count("| `")
        print(f"wrote {args.out}: {fields} fields, {len(text.splitlines())} lines")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
