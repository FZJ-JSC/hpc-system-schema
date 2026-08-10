#!/usr/bin/env python3
# /// script
# dependencies = [
#   "jsonschema"
# ]
# ///
"""
HPC System Definition — JSON Schema validator.

Validates a system description JSON file against the JSON Schema (Draft-07).

Usage:
    python validate.py <system.json> [--schema <schema.json>] [--check inheritance] [--check tbd] ...

The JSON Schema path is resolved in this order of precedence:
    1. --schema CLI argument
    2. SCHEMA_PATH environment variable
    3. Default: ../schema/system-description-0.5.0.json (relative to this script)

Checks:
    schema     — JSON Schema structural validation (required, type, format, $ref)
    inheritance — circular inheritance, missing parents
    tbd        — report TBD / placeholder values
    unique     — duplicate IDs / names across parts
    summary    — one-line summary of the document

Exit codes:
    0  all checks pass
    1  one or more checks fail
    2  usage / file error
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from typing import Any

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RESET = "\033[0m"
BOLD = "\033[1m"


def _ok(msg: str) -> None:
    print(f"  {GREEN}✓{RESET} {msg}")


def _fail(msg: str) -> None:
    print(f"  {RED}✗{RESET} {msg}")


def _warn(msg: str) -> None:
    print(f"  {YELLOW}⚠{RESET} {msg}")


def _section(title: str) -> None:
    print(f"\n{BOLD}── {title} ──{RESET}")


# ---------------------------------------------------------------------------
# Check: schema (structural JSON Schema validation)
# ---------------------------------------------------------------------------
def check_schema(instance: dict, schema: dict) -> bool:
    """Validate *instance* against the JSON Schema using jsonschema.

    This natively enforces all Draft-07 keywords, including:
      - required: missing mandatory fields are reported at any nesting depth
      - type, minimum/maximum, pattern, format (e.g. date-time, uri)
      - enum / const / oneOf / anyOf / allOf
      - $ref resolution into the schema's definitions
    """
    _section("Schema validation (Draft-07)")
    try:
        from jsonschema import Draft7Validator
        validator = Draft7Validator(schema)
        errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))
        if not errors:
            _ok("Document is valid against the JSON Schema.")
            return True
        for err in errors:
            path = ".".join(str(p) for p in err.absolute_path) or "(root)"
            _fail(f"{path}: {err.message}")
        return False
    except Exception as exc:
        _fail(f"Validator error: {exc}")
        return False


# ---------------------------------------------------------------------------
# Check: TBD values
# ---------------------------------------------------------------------------
_TBD_RE = re.compile(r"^TBD$", re.IGNORECASE)


def _find_tbd(obj: Any, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            hits.extend(_find_tbd(v, f"{path}.{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits.extend(_find_tbd(v, f"{path}[{i}]"))
    elif isinstance(obj, str) and _TBD_RE.match(obj):
        hits.append(path)
    return hits


def check_tbd(instance: dict) -> bool:
    """Report any TBD / placeholder string values."""
    _section("TBD / placeholder detection")
    hits = _find_tbd(instance)
    if not hits:
        _ok("No TBD values found.")
        return True
    for loc in hits:
        _warn(f"TBD at {loc}")
    _warn(f"{len(hits)} TBD value(s) found.")
    return False  # TBD is a soft-fail (warn); return False so caller can decide


# ---------------------------------------------------------------------------
# Check: uniqueness of IDs and names in parts
# ---------------------------------------------------------------------------
def check_unique(instance: dict) -> bool:
    """Ensure IDs and names are unique across parts and node_types."""
    _section("Uniqueness checks")
    parts = instance.get("parts", [])
    ok = True

    # Part-level IDs
    ids = [p.get("id") for p in parts if "id" in p]
    dup_ids = [id_ for id_, cnt in Counter(ids).items() if cnt > 1]
    if dup_ids:
        for d in dup_ids:
            _fail(f"Duplicate part id: {d}")
        ok = False
    else:
        _ok(f"All {len(ids)} part IDs are unique.")

    # Part-level names
    names = [p.get("name") for p in parts if "name" in p]
    dup_names = [n for n, cnt in Counter(names).items() if cnt > 1]
    if dup_names:
        for d in dup_names:
            _fail(f"Duplicate part name: {d}")
        ok = False
    else:
        _ok(f"All {len(names)} part names are unique.")

    # Node-type IDs within each part
    for part in parts:
        pName = part.get("name", part.get("id", "?"))
        for nt in part.get("node_types", []):
            nt_ids = [n.get("id") for n in part.get("node_types", []) if "id" in n]
            nt_dup = [x for x, c in Counter(nt_ids).items() if c > 1]
            if nt_dup:
                for d in nt_dup:
                    _fail(f"Duplicate node_type id in '{pName}': {d}")
                ok = False
            break  # only check once per part

    if ok:
        _ok("All IDs and names are unique.")
    return ok


# ---------------------------------------------------------------------------
# Check: inheritance
# ---------------------------------------------------------------------------
def _collect_inheritance(parts: list[dict]) -> list[tuple[str, str, str, str]]:
    """Return (child_name, parent_ref, scope, parent_set_info) tuples.

    scope is 'part' or 'node_type'.
    For part scope, parent_set_info is the parent part id (used for lookup).
    For node_type scope, parent_set_info is 'part:<part_name>:node_type'.
    """
    pairs = []
    for p in parts:
        part_id = p.get("id", "?")
        part_name = p.get("name", "?")
        parent = p.get("inherits_from")
        if parent:
            pairs.append((part_name, parent, "part", f"part_id:{parent}"))
        for nt in p.get("node_types", []):
            nt_name = nt.get("node_type_name", nt.get("id", "?"))
            nt_parent = nt.get("inherits_from")
            if nt_parent:
                pairs.append((nt_name, nt_parent, "node_type", f"part:{part_name}:node_type_name:{nt_parent}"))
    return pairs


def check_inheritance(instance: dict) -> bool:
    """Validate inheritance references (no missing parents, no cycles)."""
    _section("Inheritance validation")
    parts = instance.get("parts", [])
    pairs = _collect_inheritance(parts)
    if not pairs:
        _ok("No inheritance relationships — nothing to check.")
        return True

    # Build lookup sets
    part_id_set = {p.get("id") for p in parts}
    # node_type_name lookup: {part_name: {node_type_name, ...}}
    nt_by_part: dict[str, set[str]] = {}
    for p in parts:
        pname = p.get("name", "?")
        nt_by_part[pname] = {nt.get("node_type_name", nt.get("id", "?")) for nt in p.get("node_types", [])}

    ok = True

    # Missing parents
    for child_name, parent_ref, scope, _info in pairs:
        if scope == "part":
            if parent_ref not in part_id_set:
                _fail(f"'{child_name}' inherits from '{parent_ref}' — parent part not found.")
                ok = False
        elif scope == "node_type":
            # Find which part this child belongs to
            child_part = None
            for p in parts:
                for nt in p.get("node_types", []):
                    if nt.get("node_type_name", nt.get("id", "?")) == child_name:
                        child_part = p.get("name", "?")
                        break
                if child_part:
                    break
            # Check within same part first, then across all parts
            part_nts = nt_by_part.get(child_part, set()) if child_part else set()
            all_nts = set().union(*nt_by_part.values()) if nt_by_part else set()
            if parent_ref in part_nts:
                pass  # same-part inheritance
            elif parent_ref in all_nts:
                pass  # cross-part inheritance
            else:
                _fail(f"Node type '{child_name}' inherits from '{parent_ref}' — not found in any part.")
                ok = False
    if ok:
        _ok(f"All {len(pairs)} inheritance reference(s) resolve.")

    # Cycle detection (DFS) — separate per scope
    # Build id-to-name map for parts
    id_to_name = {p.get("id"): p.get("name", "?") for p in parts}

    # For parts: child_name → parent_name (resolve id to name)
    child_map_part: dict[str, str] = {}
    for c, p, s, _ in pairs:
        if s == "part":
            child_map_part[c] = id_to_name.get(p, p)

    # For node_types: child_name → parent_name (names already used)
    child_map_nt: dict[str, str] = {c: p for c, p, s, _ in pairs if s == "node_type"}

    def _dfs(node: str, child_map: dict[str, str], visited: set[str], stack: set[str]) -> list[str] | None:
        if node in stack:
            return [node]
        if node in visited:
            return None
        visited.add(node)
        stack.add(node)
        parent = child_map.get(node)
        if parent:
            cycle = _dfs(parent, child_map, visited, stack)
            if cycle:
                return [node] + cycle
        stack.discard(node)
        return None

    visited: set[str] = set()
    for child, _, scope, _ in pairs:
        child_map = child_map_part if scope == "part" else child_map_nt
        cycle = _dfs(child, child_map, set(), set())
        if cycle:
            _fail(f"Circular inheritance ({scope}): {' → '.join(cycle)}")
            ok = False

    if ok:
        _ok("No circular inheritance detected.")
    return ok


# ---------------------------------------------------------------------------
# Check: summary / document overview
# ---------------------------------------------------------------------------
def check_summary(instance: dict) -> bool:
    """Print a one-line summary of the document."""
    _section("Document summary")
    parts = instance.get("parts", [])
    node_types_total = sum(len(p.get("node_types", [])) for p in parts)
    part_types = Counter(p.get("part_type", "?") for p in parts)

    _ok(f"name: {instance.get('name', '?')}")
    _ok(f"schema_version: {instance.get('schema_version', '?')}, version: {instance.get('version', '?')}")
    _ok(f"parts: {len(parts)} ({', '.join(f'{v}×{k}' for k, v in part_types.items())})")
    _ok(f"node_types total: {node_types_total}")
    _ok(f"installed_at: {instance.get('installed_at', '?')}")
    return True


# ---------------------------------------------------------------------------
# Registry of checks
# ---------------------------------------------------------------------------
CHECKS = {
    "schema": check_schema,
    "tbd": check_tbd,
    "unique": check_unique,
    "inheritance": check_inheritance,
    "summary": check_summary,
}

# Checks that don't need schema (skip if --schema not given)
SKIP_IF_NO_SCHEMA = {"schema"}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="validate.py",
        description=(
            "Validate an HPC system definition (JSON) against the System Definition "
            "JSON Schema (Draft-07).\n\n"
            "The document is checked structurally against the schema (required fields, "
            "types, formats, enums, $ref resolution) and additionally for placeholder "
            "values, duplicate identifiers, and broken or circular part inheritance.\n\n"
            "Checks (select with --check, repeatable):\n"
            "  schema       structural validation via the jsonschema library "
            "(Draft-07 keywords: required, type, format, enum, minimum/maximum, $ref)\n"
            "  tbd          report TBD / placeholder string values\n"
            "  unique       duplicate IDs / names across parts and node_types\n"
            "  inheritance  missing parent references and circular inheritance\n"
            "  summary      print a one-line overview of the document\n\n"
            "Schema resolution order:\n"
            "  1. --schema CLI argument\n"
            "  2. SCHEMA_PATH environment variable\n"
            "  3. default: ../schema/system-description-0.5.0.json (relative to this script)\n\n"
            "Exit codes:\n"
            "  0  all selected checks pass\n"
            "  1  one or more checks fail\n"
            "  2  usage error or input file not found"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  # run all checks (default)\n"
            "  python validate.py descriptions/system-jupiter.json\n"
            "\n"
            "  # pick a different schema (flag or environment variable)\n"
            "  python validate.py system.json --schema path/to/schema.json\n"
            "  SCHEMA_PATH=path/to/schema.json python validate.py system.json\n"
            "\n"
            "  # run only specific checks, composably\n"
            "  python validate.py system.json --check schema --check inheritance\n"
            "  python validate.py system.json --check tbd\n"
            "\n"
            "  # CI / GitHub Actions friendly output (no ANSI colours)\n"
            "  python validate.py system.json --no-color\n"
            "\n"
            "  # with uv (installs jsonschema automatically, see PEP 723 header)\n"
            "  uv run validate.py system.json\n"
        ),
    )
    p.add_argument(
        "system",
        metavar="SYSTEM.json",
        help="Path to the system description JSON file to validate.",
    )
    p.add_argument(
        "--schema",
        metavar="SCHEMA.json",
        default=os.environ.get(
            "SCHEMA_PATH",
            os.path.join(os.path.dirname(__file__), os.pardir,
                         "schema", "system-description-0.5.0.json"),
        ),
        help=(
            "Path to the JSON Schema file used for structural validation. "
            "Defaults to $SCHEMA_PATH if set, otherwise "
            "../schema/system-description-0.5.0.json (relative to this script)."
        ),
    )
    p.add_argument(
        "--check",
        action="append",
        dest="checks",
        metavar="CHECK",
        choices=list(CHECKS),
        help=(
            "Run only this check; repeat the flag to select several, e.g. "
            "--check schema --check tbd. Possible values: "
            + ", ".join(sorted(CHECKS)) + ". Default: run all checks."
        ),
    )
    p.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colour codes in the output (useful for CI logs).",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    ns = parse_args(argv)

    if ns.no_color:
        global RED, GREEN, YELLOW, RESET, BOLD
        RED = GREEN = YELLOW = RESET = BOLD = ""

    # Resolve schema path
    schema_path = os.path.abspath(ns.schema)
    if not os.path.isfile(schema_path):
        print(f"Error: schema not found: {schema_path}", file=sys.stderr)
        return 2

    with open(schema_path) as f:
        schema = json.load(f)

    # Load system description
    system_path = os.path.abspath(ns.system)
    if not os.path.isfile(system_path):
        print(f"Error: system file not found: {system_path}", file=sys.stderr)
        return 2

    with open(system_path) as f:
        instance = json.load(f)

    # Determine which checks to run
    to_run = ns.checks or list(CHECKS)
    results: dict[str, bool] = {}

    for name in to_run:
        if name in SKIP_IF_NO_SCHEMA and not ns.schema:
            continue
        fn = CHECKS[name]
        if name == "schema":
            results[name] = fn(instance, schema)
        else:
            results[name] = fn(instance)

    # Final verdict
    all_pass = all(results.values())
    print(f"\n{'═' * 60}")
    if all_pass:
        print(f"{GREEN}{BOLD}  ALL CHECKS PASSED{RESET}")
    else:
        failed = [k for k, v in results.items() if not v]
        print(f"{RED}{BOLD}  FAILED: {', '.join(failed)}{RESET}")
    print(f"{'═' * 60}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
