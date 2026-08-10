#!/usr/bin/env python3
"""
Build the GitHub Pages site for the HPC System Description Schema.

Assembles the deployable static site from repository sources (build
output goes to a gitignored directory, e.g. `site-preview/`):

    <output>/
    ├── index.html                  # from docs/index_landing.html (renamed here)
    ├── .nojekyll
    ├── docs/                       # schema documentation (regenerated via docs/Makefile)
    ├── gui-generator/              # browser editor + schema copy (for its relative fetch)
    ├── schema/
    │   └── system-description-0.5.0.json    # canonical schema (stable $id URL)
    └── descriptions/               # example system descriptions

Requirements: Python 3, uv (the docs regeneration runs `make -C docs`, which
uses `uvx --from json-schema-for-humans`).

Usage:
    python3 build-site.py                    # build into a fresh temp directory
    python3 build-site.py site-preview       # build into a named directory
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

SCHEMA_FILE = "system-description-0.5.0.json"
LANDING_PAGE = "index_landing.html"  # lives in docs/, deployed as index.html


def banner(msg: str) -> None:
    print(f"== {msg} ==")


def regenerate_docs() -> None:
    """Regenerate the HTML schema documentation from the source schema."""
    banner("Regenerating schema documentation (make -C docs)")
    try:
        subprocess.run(
            ["make", "-C", str(REPO_ROOT / "docs")],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        print("ERROR: `make` not found on PATH.", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"ERROR: docs generation failed:\n{e.stderr}", file=sys.stderr)
        sys.exit(1)


def copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"  {src.relative_to(REPO_ROOT)}  ->  {dst}")


def assemble(out: Path) -> None:
    banner("Assembling site")

    # Landing page: docs/index_landing.html is renamed to index.html here
    # (performed by GitHub Actions via this script in the deploy workflow).
    copy(REPO_ROOT / "docs" / LANDING_PAGE, out / "index.html")

    # Schema documentation, as generated above.
    docs_out = out / "docs"
    for name in ["index.html", "schema_doc.css", "schema_doc.min.js"]:
        copy(REPO_ROOT / "docs" / name, docs_out / name)

    # GUI generator: editor HTML plus a schema copy next to it, so the
    # page's relative schema fetch works unchanged on the deployed site.
    copy(REPO_ROOT / "sample-apps" / "gui-generator" / "index.html",
         out / "gui-generator" / "index.html")
    copy(REPO_ROOT / "schema" / SCHEMA_FILE,
         out / "gui-generator" / SCHEMA_FILE)

    # Canonical schema under ./schema/ (matches the schema's $id).
    copy(REPO_ROOT / "schema" / SCHEMA_FILE, out / "schema" / SCHEMA_FILE)

    # Examples — also used by the editor's "load example" button.
    desc_out = out / "descriptions"
    for src in sorted((REPO_ROOT / "descriptions").glob("system-*")):
        copy(src, desc_out / src.name)
    # Copy the index.html listing page
    copy(REPO_ROOT / "descriptions" / "index.html", desc_out / "index.html")

    # GitHub Pages marker (no Jekyll processing).
    (out / ".nojekyll").write_text("")


def main() -> None:
    if not (REPO_ROOT / "schema" / SCHEMA_FILE).is_file():
        print(f"ERROR: {SCHEMA_FILE} not found under schema/", file=sys.stderr)
        sys.exit(1)
    if not (REPO_ROOT / "docs" / LANDING_PAGE).is_file():
        print(f"ERROR: {LANDING_PAGE} not found under docs/", file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) > 1:
        out = Path(sys.argv[1]).resolve()
        if out == REPO_ROOT:
            # Only building into the repository root itself is refused —
            # named subdirectories (e.g. `site/` or `site-preview/`) are
            # allowed and are listed in .gitignore so the repo stays clean.
            print(f"ERROR: refusing to build into the repository root ({REPO_ROOT}).",
                  file=sys.stderr)
            print("Use a subdirectory, e.g.: python3 build-site.py site-preview",
                  file=sys.stderr)
            sys.exit(1)
        shutil.rmtree(out, ignore_errors=True)  # replace previous build
    else:
        out = Path(tempfile.mkdtemp(prefix="hpc-schema-site-"))

    regenerate_docs()
    assemble(out)
    banner("Done")
    print(f"Site ready in: {out}")
    print(f"Preview:       python3 -m http.server 8080 -d {out}")
    print("Deployed on push to main via .github/workflows/pages.yml")


if __name__ == "__main__":
    main()