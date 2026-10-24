#!/usr/bin/env python3
"""Compare two HPC system descriptions axis by axis.

A description is a document with a hierarchy (system, part, node type,
components). Comparing two systems means asking, per axis, what differs -- and
for an adopting site the useful answer is grouped by that hierarchy, not a flat
list of changed keys.

Arrays are matched by id where the objects carry one, so a node type in A is
compared with the node type of the same id in B rather than by position.

Usage:
    python3 diff.py A.json B.json [--format summary|md|latex] [--limit N]

Values of the form {"quantity": x, "unit": u} are rendered as "x u".
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

LEVELS = [
    ("parts[].node_types[].", "node type"),
    ("parts[]", "part"),
    ("", "system"),
]

COMPONENT_PREFIXES = ("cpus[", "memory[", "accelerators[", "network[", "storage")


def flatten(obj, path="", out=None, by_id=True):
    """Flatten to {dotted axis: scalar value}.

    by_id=True keys arrays of objects on their id (comparing two versions of the
    same system); by_id=False keys them by position (comparing two systems, whose
    ids differ by construction).
    """
    if out is None:
        out = {}
    if isinstance(obj, dict):
        if set(obj) == {"quantity", "unit"}:
            out[path] = f"{obj['quantity']} {obj['unit']}"
            return out
        for key, value in obj.items():
            if key == "comment":
                continue  # provenance prose, not a comparable axis
            flatten(value, f"{path}.{key}" if path else key, out, by_id)
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            if by_id and isinstance(value, dict) and "id" in value:
                token = f"[{value['id']}]"
            else:
                token = f"[{index}]"
            flatten(value, f"{path}{token}", out, by_id)
    else:
        out[path] = obj
    return out


def label(path: str) -> str:
    """Name a description by its own name field, else by its file name."""
    try:
        with open(path, encoding="utf-8") as handle:
            name = json.load(handle).get("name")
        if name:
            stem = pathlib.Path(path).stem
            if stem.endswith(("-min", "-minimal")):
                name += " (minimal)"
            return name
    except (OSError, json.JSONDecodeError):
        pass
    return pathlib.Path(path).stem.replace("system-", "")


def level_of(axis: str) -> str:
    if ".node_types[" in axis:
        if any(f".{prefix}" in axis for prefix in COMPONENT_PREFIXES):
            return "component"
        return "node type"
    if axis.startswith("parts["):
        return "part"
    return "system"


def short(axis: str) -> str:
    """Drop the array ids from the label, keep them where they identify the object."""
    return axis.replace("parts[", "part[").replace("node_types[", "node-type[")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("a")
    parser.add_argument("b")
    parser.add_argument("--format", default="summary", choices=("summary", "md", "latex"))
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--exclude-identity", action="store_true",
                        help="drop name/id/location/website/installed_at axes (paper tables)")
    parser.add_argument("--shared-only", action="store_true",
                        help="only axes present in both descriptions (the comparable ones)")
    parser.add_argument("--align", default="position", choices=("position", "id"),
                        help="position: compare two systems; id: compare two versions of one system")
    args = parser.parse_args()

    with open(args.a, encoding="utf-8") as handle:
        flat_a = flatten(json.load(handle), by_id=(args.align == "id"))
    with open(args.b, encoding="utf-8") as handle:
        flat_b = flatten(json.load(handle), by_id=(args.align == "id"))

    if args.exclude_identity:
        drop = ("name", "id", "location", "website", "installed_at", "accepted_at",
                "provider", "comment", "version", "changelog", "schema_version")
        flat_a = {k: v for k, v in flat_a.items() if not any(part in drop for part in k.split("."))}
        flat_b = {k: v for k, v in flat_b.items() if not any(part in drop for part in k.split("."))}

    changed = {k: (flat_a[k], flat_b[k]) for k in flat_a.keys() & flat_b.keys()
               if str(flat_a[k]) != str(flat_b[k])}
    only_a = {k: flat_a[k] for k in flat_a.keys() - flat_b.keys()}
    only_b = {k: flat_b[k] for k in flat_b.keys() - flat_a.keys()}

    def bucket(items):
        counts = {}
        for axis in items:
            counts[level_of(axis)] = counts.get(level_of(axis), 0) + 1
        return counts

    if args.format == "summary":
        name_a, name_b = label(args.a), label(args.b)
        print(f"{name_a}: {len(flat_a)} fields")
        print(f"{name_b}: {len(flat_b)} fields")
        print(f"{len(changed)} fields differ; "
              f"{len(only_a)} only in {name_a}, {len(only_b)} only in {name_b}")
        for title, items in ((f"differ", changed), (f"only in {name_a}", only_a),
                             (f"only in {name_b}", only_b)):
            if items:
                counts = bucket(items)
                detail = ", ".join(f"{k} {v}" for k, v in sorted(counts.items()))
                print(f"  {title}: {detail}")
        return 0

    rows = []
    for axis, (va, vb) in sorted(changed.items()):
        rows.append((level_of(axis), short(axis), va, vb))
    if not args.shared_only:
        for axis, va in sorted(only_a.items()):
            rows.append((level_of(axis), short(axis), va, "--"))
        for axis, vb in sorted(only_b.items()):
            rows.append((level_of(axis), short(axis), "--", vb))

    order = {"system": 0, "part": 1, "node type": 2, "component": 3}
    rows.sort(key=lambda r: (order[r[0]], r[1]))

    name_a, name_b = label(args.a), label(args.b)
    if args.format == "md":
        print(f"| Level | Field | {name_a} | {name_b} |")
        print("|---|---|---|---|")
        for level, axis, va, vb in rows[: args.limit]:
            print(f"| {level} | `{axis}` | {va} | {vb} |")
        print(f"\n{len(rows)} differing fields, {min(len(rows), args.limit)} shown")
    else:
        for level, axis, va, vb in rows[: args.limit]:
            axis_tex = axis.replace("_", r"\_")
            print(f"        {level} & \\texttt{{{axis_tex}}} & {va} & {vb} \\\\")
    return 0


if __name__ == "__main__":
    sys.exit(main())
