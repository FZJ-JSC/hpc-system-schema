#!/usr/bin/env python3
"""Summarize axis overlap for a set of system-description pairs.

Prints one Markdown row per pair: how many axes each description carries, how
many exist on both sides, how many of those differ, and how many exist on one
side only. Identity axes (name, id, location, website, ...) are excluded, so
the numbers describe technical content.

Usage:
    python3 summarize.py ../../GitHub/descriptions/system-*.json
"""

from __future__ import annotations

import glob
import importlib.util
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("diff", HERE / "diff.py")
diff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diff)

IDENTITY = ("name", "id", "location", "website", "installed_at", "accepted_at",
            "provider", "comment", "version", "changelog", "schema_version")


def flat(path):
    with open(path, encoding="utf-8") as handle:
        axes = diff.flatten(json.load(handle), by_id=False)
    return {k: v for k, v in axes.items() if not any(p in IDENTITY for p in k.split("."))}


def row(a, b):
    fa, fb = flat(a), flat(b)
    shared = fa.keys() & fb.keys()
    differing = sum(1 for k in shared if str(fa[k]) != str(fb[k]))
    return (diff.label(a), diff.label(b),
            len(fa), len(fb), len(shared), differing,
            len(fa.keys() - fb.keys()), len(fb.keys() - fa.keys()))


def main() -> int:
    paths = sorted(sys.argv[1:])
    if len(paths) < 2:
        print("need at least two descriptions", file=sys.stderr)
        return 1
    pairs = [(paths[i], paths[j]) for i in range(len(paths)) for j in range(i + 1, len(paths))]
    print("| System | Compared with | Fields here | Fields there | Shared | Differing | Only here | Only there |")
    print("|---|---|---|---|---|---|---|---|")
    for a, b in pairs:
        print("| " + " | ".join(str(x) for x in row(a, b)) + " |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
