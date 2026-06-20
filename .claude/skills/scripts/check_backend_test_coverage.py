#!/usr/bin/env python3
# designer: When you want to know how well your backend is tested, I
#   run the suite, measure coverage, and group the numbers by area --
#   API, models, services, and so on. You get a single table plus a
#   list of files that nothing tests at all and files that do not even
#   have a test next to them.
"""
check_backend_test_coverage.py — Analyse backend test coverage.

Invocation: agent-invoked, hook-ci
Lifecycle: active

Generated : 2026-03-08T12:00:00 UTC
User brief: Check backend test coverage
Interpretation: Run pytest with coverage against backend/app,
                then display a per-module summary (api, models, services,
                middleware, schemas, utils, root) plus an overall total.
                Highlight uncovered source files.

The script:
  1. Installs pytest-cov if missing (user site, no pip prompt).
  2. Runs `pytest --cov=app --cov-report=json` inside backend/.
  3. Parses the JSON coverage report.
  4. Prints a table grouped by subpackage with stmts / miss / cover%.
  5. Lists source files with 0% coverage (completely untested).
  6. Lists source files without a corresponding test file.

Usage
-----
    python _loom/generated-scripts/check_backend_test_coverage.py

Run from the repository root.
Optional flags:
    --html          Also generate an HTML report in backend/htmlcov/
    --fail-under N  Exit with code 2 if total coverage < N%
    --verbose       Show every file, not just the summary

CHECK_PLUGIN_MANIFEST:
  name: Backend Test Coverage
  stack:
    backend: [flask]
    frontend: []
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

BACKEND   = get_path("BACKEND_DIR") or REPO_ROOT / "backend"
COV_JSON  = BACKEND / "coverage.json"

SUBPACKAGES = tuple(get_list("BACKEND_SUBPACKAGES",
                             ["api", "models", "services", "middleware",
                              "schemas", "utils"]))

# Locate the backend virtual-environment Python so that all backend
# dependencies (Flask, SQLAlchemy, flask_limiter, …) are available.
_VENV_CANDIDATES = ("venv", ".venv", "env")

def _find_venv_python() -> str:
    """Return the path to the backend venv python, or fall back to sys.executable."""
    for name in _VENV_CANDIDATES:
        venv_dir = BACKEND / name
        for rel in ("Scripts/python.exe", "bin/python"):   # Windows / Unix
            candidate = venv_dir / rel
            if candidate.exists():
                return str(candidate)
    return sys.executable

VENV_PYTHON = _find_venv_python()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ensure_pytest_cov() -> None:
    """Install pytest-cov into the backend venv if it is not already available."""
    rc = subprocess.run(
        [VENV_PYTHON, "-c", "import pytest_cov"],
        capture_output=True,
    ).returncode
    if rc != 0:
        print("pytest-cov not found — installing into backend venv …")
        subprocess.check_call(
            [VENV_PYTHON, "-m", "pip", "install", "pytest-cov", "--quiet"],
        )


def run_pytest(html: bool) -> int:
    """Run pytest with coverage inside the backend directory.

    Returns the pytest exit code (0 = all passed, 1 = some failed, etc.).
    """
    cmd = [
        VENV_PYTHON, "-m", "pytest",
        "--cov=app",
        "--cov-report", f"json:{COV_JSON}",
        "--cov-report", "term-missing:skip-covered",
        "-q",
    ]
    if html:
        cmd += ["--cov-report", f"html:{BACKEND / 'htmlcov'}"]

    result = subprocess.run(cmd, cwd=str(BACKEND))
    return result.returncode


def classify(filepath: str) -> str:
    """Return the subpackage bucket for a source path like 'app/api/auth.py'."""
    parts = Path(filepath).parts
    if len(parts) >= 2 and parts[0] == "app":
        sub = parts[1]
        if sub in SUBPACKAGES:
            return sub
    return "root"                           # app/__init__.py, app/config.py, …


def load_report() -> dict:
    with open(COV_JSON, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_table(rows: list[tuple[str, int, int, float]], title: str) -> None:
    """Print a markdown-style table of (label, stmts, miss, cover%)."""
    hdr = f"{'Module':<40} {'Stmts':>6} {'Miss':>6} {'Cover':>7}"
    sep = "-" * len(hdr)
    print(f"\n{title}")
    print(sep)
    print(hdr)
    print(sep)
    for label, stmts, miss, cover in rows:
        bar = _bar(cover)
        print(f"{label:<40} {stmts:>6} {miss:>6} {cover:>6.1f}% {bar}")
    print(sep)


def _bar(pct: float, width: int = 20) -> str:
    filled = round(pct / 100 * width)
    return "#" * filled + "-" * (width - filled)


def analyse(report: dict, *, verbose: bool) -> float:
    """Print grouped coverage summary. Returns total coverage %."""

    files_data = report.get("files", {})
    if not files_data:
        print("No coverage data found.")
        return 0.0

    # ---- per-file stats ----
    per_file: list[tuple[str, int, int, float]] = []
    for filepath, info in sorted(files_data.items()):
        summary = info["summary"]
        stmts   = summary["num_statements"]
        miss    = summary["missing_lines"]
        cover   = summary["percent_covered"]
        per_file.append((filepath, stmts, miss, cover))

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
        label = f"app/{bucket}" if bucket != "root" else "app/ (root files)"
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
    tested_modules: set[str] = set()
    tests_dir = BACKEND / "tests"
    if tests_dir.is_dir():
        for tf in tests_dir.glob("test_*.py"):
            # test_auth_endpoints.py  →  auth_endpoints
            tested_modules.add(tf.stem.removeprefix("test_"))

    source_files = sorted(
        p.relative_to(BACKEND)
        for p in (BACKEND / "app").rglob("*.py")
        if p.name != "__init__.py" and not p.name.startswith("test_")
    )
    untested: list[Path] = []
    for sf in source_files:
        stem = sf.stem                              # e.g. "auth"
        parent = sf.parent.name                     # e.g. "api"
        # Check common naming conventions for test files
        candidates = {stem, f"{parent}_{stem}", f"{stem}_{parent}",
                      f"{parent}", f"{stem}_service", f"{stem}_api"}
        if not candidates & tested_modules:
            untested.append(sf)

    if untested:
        print(f"\nSource files without a matching test file ({len(untested)}):")
        for sf in untested:
            print(f"  - {sf}")

    return total_pct


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    _project = get("PROJECT_NAME", "project")
    parser = argparse.ArgumentParser(description=f"Check {_project} backend test coverage")
    parser.add_argument("--html", action="store_true",
                        help="Also produce an HTML report in backend/htmlcov/")
    parser.add_argument("--fail-under", type=float, default=0.0,
                        help="Exit with code 2 if total coverage is below this %%")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show every file, not just the subpackage summary")
    args = parser.parse_args()

    os.chdir(REPO_ROOT)
    ensure_pytest_cov()

    print("=" * 60)
    print("Running backend tests with coverage …")
    print("=" * 60)

    rc = run_pytest(html=args.html)
    print()

    if not COV_JSON.exists():
        print(f"ERROR: coverage JSON not generated at {COV_JSON}", file=sys.stderr)
        sys.exit(1)

    report   = load_report()
    total_pct = analyse(report, verbose=args.verbose)

    print(f"\nOverall backend coverage: {total_pct:.1f}%")

    if args.html:
        print(f"HTML report: {BACKEND / 'htmlcov' / 'index.html'}")

    # Cleanup the JSON artefact
    COV_JSON.unlink(missing_ok=True)

    if total_pct < args.fail_under:
        print(f"\nFAIL: coverage {total_pct:.1f}% < {args.fail_under}%")
        sys.exit(2)

    if rc != 0:
        print(f"\nNote: pytest exited with code {rc} (some tests may have failed).")
        sys.exit(rc)


if __name__ == "__main__":
    main()
