#!/usr/bin/env python3
# /// script
# dependencies = [
#   "jinja2>=3.1,<4"
# ]
# ///
"""
compare.py — Generate a LaTeX comparison table from HPC system descriptions.

Usage:
    python compare.py sys1.json sys2.json [sys3.json ...]
    python compare.py sys1.json sys2.json -o comparison.tex
    python compare.py sys1.json sys2.json --features system_name,accelerator

The harness:
  1. Loads N system description JSON files
  2. Extracts a configurable set of features (from features.py)
  3. Renders a LaTeX table via Jinja2

To add a new comparison metric, add an entry to FEATURES in features.py.
"""
import argparse
import json
import pathlib
import sys

from typing import Optional

from jinja2 import Environment, FileSystemLoader

# ── Feature registry (import from features.py) ──
from features import FEATURES

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent


def load_system(path: pathlib.Path) -> dict:
    """Load and return a parsed system description."""
    return json.loads(path.read_text())


def extract_row(features: list[dict], data: dict) -> list[str]:
    """Extract all feature values for one system. Returns a list of strings."""
    out = []
    for feat in features:
        try:
            val = feat["extract"](data)
        except Exception as exc:
            val = f"\\textit{{error: {exc}}}"
        out.append(str(val) if val is not None else "---")
    return out


def render(
    systems: list[dict],
    features: list[dict],
    template_path: Optional[pathlib.Path] = None,
) -> str:
    """Render the LaTeX comparison document."""
    if template_path is None:
        template_path = SCRIPT_DIR / "template.tex.j2"

    env = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        keep_trailing_newline=True,
    )
    template = env.get_template(template_path.name)

    # Build row data
    rows = []
    for feat in features:
        rows.append({
            "label": feat["label"],
            "vals": [val for val in (feat["extract"](s) for s in systems)],
        })

    # System names for header
    sys_headers = [{"name": s.get("name", "???")} for s in systems]

    return template.render(systems=sys_headers, features=rows)


def main():
    parser = argparse.ArgumentParser(
        description="Generate a LaTeX comparison table from HPC system descriptions.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "systems",
        nargs="+",
        help="JSON files to compare (2+ systems).",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output .tex file. Default: stdout.",
    )
    parser.add_argument(
        "--features",
        default=None,
        help="Comma-separated feature keys to include (default: all). "
             "Available: " + ", ".join(f["key"] for f in FEATURES),
    )
    parser.add_argument(
        "--template",
        default=None,
        help="Path to a custom Jinja2 template.",
    )
    args = parser.parse_args()

    # Load systems
    systems = []
    for p in args.systems:
        path = pathlib.Path(p)
        if not path.exists():
            print(f"ERROR: File not found: {path}", file=sys.stderr)
            sys.exit(1)
        systems.append(load_system(path))

    if len(systems) < 2:
        print("ERROR: Need at least 2 system descriptions.", file=sys.stderr)
        sys.exit(1)

    # Filter features if requested
    features = FEATURES
    if args.features:
        keys = [k.strip() for k in args.features.split(",")]
        features = [f for f in FEATURES if f["key"] in keys]
        missing = set(keys) - {f["key"] for f in features}
        if missing:
            print(f"WARNING: Unknown feature keys: {missing}", file=sys.stderr)

    # Render
    template_path = pathlib.Path(args.template) if args.template else None
    latex = render(systems, features, template_path)

    # Output
    if args.output:
        out = pathlib.Path(args.output)
        out.write_text(latex)
        print(f"Written to {out}", file=sys.stderr)
    else:
        print(latex)


if __name__ == "__main__":
    main()
