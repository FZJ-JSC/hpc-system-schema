#!/usr/bin/env python3
"""
Standalone merge utility for combining multiple collector output files.

Usage:
    python3 merge.py file1.json file2.json file3.json --output merged.json
    python3 merge.py cpu.json memory.json gpu.json --output node-type.json
    python3 merge.py *.json --output complete.json
"""

import argparse
import json
import sys
from pathlib import Path


def merge_fragments(*fragments: dict) -> dict:
    """Merge multiple JSON fragments into one."""
    result = {}
    for frag in fragments:
        if not frag:
            continue
        for key, val in frag.items():
            if key in result:
                existing = result[key]
                if isinstance(existing, list) and isinstance(val, list):
                    existing.extend(val)
                elif isinstance(existing, dict) and isinstance(val, dict):
                    existing.update(val)
                else:
                    result[key] = val
            else:
                result[key] = val
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Merge multiple collector output files into one"
    )
    parser.add_argument(
        "files", nargs="+",
        help="JSON files to merge (in order of priority)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file (default: stdout)"
    )
    parser.add_argument(
        "--pretty", action="store_true", default=True,
        help="Pretty-print output (default: True)"
    )

    args = parser.parse_args()

    fragments = []
    for path in args.files:
        try:
            with open(path) as f:
                data = json.load(f)
                fragments.append(data)
                print(f"[ok] loaded {path}", file=sys.stderr)
        except FileNotFoundError:
            print(f"[error] file not found: {path}", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"[error] invalid JSON in {path}: {e}", file=sys.stderr)
            sys.exit(1)

    merged = merge_fragments(*fragments)
    output_str = json.dumps(merged, indent=2 if args.pretty else None)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w") as f:
            f.write(output_str + "\n")
        print(f"[ok] written to {args.output}", file=sys.stderr)
    else:
        print(output_str)


if __name__ == "__main__":
    main()
