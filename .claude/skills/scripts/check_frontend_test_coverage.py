#!/usr/bin/env python3
# designer: When you want to know how well your frontend is tested, I
#   run the suite, measure coverage, and group the numbers by area --
#   components, pages, hooks, services, and so on. You get a single
#   table plus a list of source files that nothing tests at all and
#   files that do not even have a test next to them.
"""
check_frontend_test_coverage.py -- Analyse frontend test coverage.

Invocation: agent-invoked, hook-ci
Lifecycle: active

Generated : 2026-03-08T19:00:00 UTC
User brief: Check frontend test coverage
Interpretation: Run vitest with v8 coverage against frontend/src,
                then parse the JSON summary and display a per-module breakdown
                (api, components, context, features, hooks, pages, routes,
                services, utils, root) plus an overall total.
                Highlight uncovered source files and source files without
                a corresponding test file.

The script:
  1. Runs `npx vitest run --coverage` inside frontend/.
  2. Adds a temporary JSON reporter so the output can be parsed.
  3. Parses the JSON coverage report (coverage/coverage-final.json).
  4. Prints a table grouped by subpackage with stmts / miss / cover%.
  5. Lists source files with 0% coverage (completely untested).
  6. Lists source files without a corresponding test file.

Usage
-----
    python _loom/generated-scripts/check_frontend_test_coverage.py

Run from the repository root.
Optional flags:
    --fail-under N  Exit with code 2 if total coverage < N%
    --verbose       Show every file, not just the summary
    --skip-tests    Skip running tests; parse an existing coverage report

CHECK_PLUGIN_MANIFEST:
  name: Frontend Test Coverage
  stack:
    backend: []
    frontend: [react]
  scope: coverage
  critical: false
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from project_config import REPO_ROOT, get, get_list, get_path


# ---------------------------------------------------------------------------
# Resolve paths
# ---------------------------------------------------------------------------

FRONTEND  = get_path("FRONTEND_DIR") or REPO_ROOT / "frontend"
COV_DIR   = FRONTEND / "coverage"
COV_JSON  = COV_DIR / "coverage-final.json"

SUBPACKAGES = tuple(get_list("FRONTEND_SUBPACKAGES",
                             ["api", "components", "context", "features",
                              "hooks", "pages", "routes", "services",
                              "utils"]))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_vitest() -> int:
    """Run vitest with coverage inside the frontend directory.

    Returns the vitest exit code (0 = all passed, 1 = some failed, etc.).
    """
    cmd = ["npx", "vitest", "run", "--coverage"]

    env = os.environ.copy()
    env["NODE_ENV"] = "test"

    # shell=True is required on Windows for npx to resolve correctly.
    result = subprocess.run(
        cmd, cwd=str(FRONTEND), env=env,
        shell=(sys.platform == "win32"),
    )
    return result.returncode


def classify(filepath: str) -> str:
    """Return the subpackage bucket for a source path like 'src/api/auth.js'.

    The filepath is relative to frontend/ (after stripping the
    absolute prefix).
    """
    # Normalise to forward slashes and make relative to src/
    rel = filepath.replace("\\", "/")

    # Strip everything up to and including 'src/'
    idx = rel.find("src/")
    if idx >= 0:
        rel = rel[idx + 4:]  # after 'src/'

    parts = rel.split("/")
    if len(parts) >= 2 and parts[0] in SUBPACKAGES:
        return parts[0]
    return "root"  # App.jsx, main.jsx, etc.


def load_report() -> dict:
    """Load the Istanbul-format coverage-final.json."""
    with open(COV_JSON, encoding="utf-8") as f:
        return json.load(f)


def compute_file_stats(file_data: dict) -> tuple[int, int, float]:
    """Given Istanbul per-file data, return (stmts, missed, cover%).

    Istanbul format stores statement/branch/function maps with coverage
    counts.  We focus on statement coverage here.
    """
    stmt_map = file_data.get("statementMap", {})
    stmt_hits = file_data.get("s", {})
    total = len(stmt_map)
    if total == 0:
        return (0, 0, 100.0)
    missed = sum(1 for k in stmt_hits if stmt_hits[k] == 0)
    covered_pct = (total - missed) / total * 100
    return (total, missed, covered_pct)


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_table(rows: list[tuple[str, int, int, float]], title: str) -> None:
    """Print a markdown-style table of (label, stmts, miss, cover%)."""
    hdr = f"{'Module':<50} {'Stmts':>6} {'Miss':>6} {'Cover':>7}"
    sep = "-" * len(hdr)
    print(f"\n{title}")
    print(sep)
    print(hdr)
    print(sep)
    for label, stmts, miss, cover in rows:
        bar = _bar(cover)
        print(f"{label:<50} {stmts:>6} {miss:>6} {cover:>6.1f}% {bar}")
    print(sep)


def _bar(pct: float, width: int = 20) -> str:
    filled = round(pct / 100 * width)
    return "#" * filled + "." * (width - filled)


def analyse(report: dict, *, verbose: bool) -> float:
    """Print grouped coverage summary.  Returns total coverage %."""

    if not report:
        print("No coverage data found.")
        return 0.0

    # ---- per-file stats ----
    per_file: list[tuple[str, int, int, float]] = []
    for filepath, file_data in sorted(report.items()):
        stmts, miss, cover = compute_file_stats(file_data)
        # Make the path relative to the frontend dir for readability
        try:
            rel = str(Path(filepath).relative_to(FRONTEND))
        except ValueError:
            rel = filepath
        rel = rel.replace("\\", "/")
        per_file.append((rel, stmts, miss, cover))

    if verbose:
        print_table(per_file, "Per-file coverage")

    # ---- per-subpackage stats ----
    buckets: dict[str, list[tuple[str, int, int, float]]] = {s: [] for s in SUBPACKAGES}
    buckets["root"] = []

    for filepath, stmts, miss, cover in per_file:
        bucket = classify(filepath)
        buckets.setdefault(bucket, []).append((filepath, stmts, miss, cover))

    summary_rows: list[tuple[str, int, int, float]] = []
    for bucket in [*SUBPACKAGES, "root"]:
        items = buckets.get(bucket, [])
        if not items:
            continue
        total_stmts = sum(s for _, s, _, _ in items)
        total_miss  = sum(m for _, _, m, _ in items)
        pct = ((total_stmts - total_miss) / total_stmts * 100) if total_stmts else 0.0
        label = f"src/{bucket}" if bucket != "root" else "src/ (root files)"
        summary_rows.append((f"{label}  ({len(items)} files)", total_stmts, total_miss, pct))

    # overall
    total_stmts = sum(s for _, s, _, _ in per_file)
    total_miss  = sum(m for _, _, m, _ in per_file)
    total_pct   = ((total_stmts - total_miss) / total_stmts * 100) if total_stmts else 0.0
    summary_rows.append(("TOTAL", total_stmts, total_miss, total_pct))

    print_table(summary_rows, "Coverage by subpackage")

    # ---- zero-coverage files ----
    zero = [fp for fp, _, _, c in per_file if c == 0.0]
    if zero:
        print(f"\nFiles with 0% coverage ({len(zero)}):")
        for fp in zero:
            print(f"  - {fp}")

    # ---- source files without any test file ----
    _find_untested_files()

    return total_pct


def _find_untested_files() -> None:
    """List source files in src/ that have no corresponding .test.{js,jsx} file."""
    src_dir = FRONTEND / "src"
    if not src_dir.is_dir():
        return

    # Collect all test file stems (without .test.{js,jsx,ts,tsx} suffix)
    test_stems: set[str] = set()
    for ext in ("*.test.js", "*.test.jsx", "*.test.ts", "*.test.tsx"):
        for tf in src_dir.rglob(ext):
            # e.g., App.test.jsx → App
            stem = tf.stem  # "App.test" -- need to strip .test
            stem = stem.removesuffix(".test")
            test_stems.add(stem)

    # Collect source files (exclude test files, main/index files, CSS)
    source_files: list[Path] = []
    for ext in ("*.js", "*.jsx", "*.ts", "*.tsx"):
        for sf in src_dir.rglob(ext):
            if sf.name.endswith((".test.js", ".test.jsx", ".test.ts", ".test.tsx")):
                continue
            if sf.name in ("main.jsx", "main.tsx", "index.js", "index.jsx",
                           "index.ts", "index.tsx"):
                continue
            if sf.name.startswith("__"):
                continue
            source_files.append(sf)

    source_files.sort()

    untested: list[Path] = []
    for sf in source_files:
        stem = sf.stem  # e.g., "App", "apiFactories"
        if stem not in test_stems:
            untested.append(sf)

    if untested:
        print(f"\nSource files without a matching test file ({len(untested)}):")
        for sf in untested:
            rel = sf.relative_to(FRONTEND)
            print(f"  - {str(rel).replace(chr(92), '/')}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    _project = get("PROJECT_NAME", "project")
    parser = argparse.ArgumentParser(description=f"Check {_project} frontend test coverage")
    parser.add_argument("--fail-under", type=float, default=0.0,
                        help="Exit with code 2 if total coverage is below this %%")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show every file, not just the subpackage summary")
    parser.add_argument("--skip-tests", action="store_true",
                        help="Skip running tests; parse an existing coverage report")
    args = parser.parse_args()

    os.chdir(REPO_ROOT)

    if not args.skip_tests:
        print("=" * 60)
        print("Running frontend tests with coverage ...")
        print("=" * 60)

        rc = run_vitest()
        print()
    else:
        rc = 0
        print("Skipping test run -- using existing coverage report.\n")

    if not COV_JSON.exists():
        print(f"ERROR: coverage JSON not generated at {COV_JSON}", file=sys.stderr)
        print("Ensure vitest coverage generates coverage-final.json.", file=sys.stderr)
        print("You may need to add 'json' to the reporter list in vitest.config.js.", file=sys.stderr)
        sys.exit(1)

    report    = load_report()
    total_pct = analyse(report, verbose=args.verbose)

    print(f"\nOverall frontend coverage: {total_pct:.1f}%")

    if total_pct < args.fail_under:
        print(f"\nFAIL: coverage {total_pct:.1f}% < {args.fail_under}%")
        sys.exit(2)

    if rc != 0:
        print(f"\nNote: vitest exited with code {rc} (some tests may have failed).")
        sys.exit(rc)


if __name__ == "__main__":
    main()
