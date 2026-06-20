#!/usr/bin/env python3
# designer: When you want your project's whole test surface exercised in one
#   go, I'm the runner that sweeps through backend, frontend, and end-to-end
#   suites sequentially and saves a clean, ANSI-free transcript of each run
#   to a timestamped file. You end up with a reviewable record of which
#   suites passed, which failed, and where to look, without having to
#   remember each stack's invocation.
"""
run_all_tests.py — Run backend, frontend and Playwright tests, saving results.

Invocation: agent-invoked
Lifecycle: active

Generated : 2026-03-13T00:00:00 UTC
User brief: Comprehensively test backend and frontend, also with playwright,
            and save results to (frontend|backend)-tests-<YYYY-MM-DD HH.SS>.txt
            in UTF-8 files without ANSI codes. | DONE
Interpretation: Run pytest (backend), vitest (frontend) and playwright (e2e)
                sequentially, strip ANSI escape codes from all output, and
                write each result set to a timestamped UTF-8 text file inside
                the _loom/generated-scripts/out/ directory.

The script:
  1. Determines a shared timestamp for all output files.
  2. Runs pytest in backend/ and saves to backend-tests-<ts>.txt.
  3. Runs vitest in frontend/ and saves to frontend-tests-<ts>.txt.
  4. Runs playwright in e2e/ and saves to e2e-tests-<ts>.txt.
  5. All ANSI escape sequences are stripped from the captured output.
  6. Prints a summary with pass/fail status and output file paths.

Usage
-----
    python _loom/generated-scripts/run_all_tests.py

Run from the repository root (dialogos/).
Optional flags:
    --backend-only   Run only backend tests
    --frontend-only  Run only frontend tests
    --e2e-only       Run only Playwright tests
    --out-dir DIR    Override the output directory (default: _output/test-results)
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from project_config import REPO_ROOT, get, get_path  # get used for PROJECT_NAME

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]|\x1b\].*?\x07|\x1b\[[\d;]*m")

_BACKEND_DIR = get_path("BACKEND_DIR", "backend") or REPO_ROOT / "backend"
_FRONTEND_DIR = get_path("FRONTEND_DIR", "frontend") or REPO_ROOT / "frontend"
_E2E_DIR = get_path("E2E_DIR", "e2e") or REPO_ROOT / "e2e"
_OUTPUT_DIR = get_path("OUTPUT_DIR", "_output") or REPO_ROOT / "_output"
_PROJECT_NAME = get("PROJECT_NAME", "project")


def _find_venv_python() -> str:
    """Return the venv Python if we're inside one, else sys.executable."""
    venv = os.environ.get("VIRTUAL_ENV")
    if venv:
        candidate = Path(venv) / "Scripts" / "python.exe"  # Windows
        if candidate.exists():
            return str(candidate)
        candidate = Path(venv) / "bin" / "python"  # Unix
        if candidate.exists():
            return str(candidate)
    # Fallback: check common venv locations
    for venv_name in (".venv", "venv"):
        for base in (REPO_ROOT, REPO_ROOT / "backend"):
            for rel in ("Scripts/python.exe", "bin/python"):
                candidate = base / venv_name / rel
                if candidate.exists():
                    return str(candidate)
    return sys.executable


def _find_npx() -> str:
    """Resolve the full path to npx so subprocess can find it."""
    npx = shutil.which("npx")
    if npx:
        return npx
    # Common Windows locations via nvm4w
    for candidate in [
        Path("e:/apps/nvm4w/nodejs/npx.cmd"),
        Path(os.environ.get("NVM_SYMLINK", ""), "npx.cmd"),
    ]:
        if candidate.exists():
            return str(candidate)
    return "npx"  # last resort — let OS try


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from *text*."""
    return ANSI_RE.sub("", text)


def run_suite(
    label: str,
    cmd: list[str],
    cwd: Path,
    out_path: Path,
) -> bool:
    """Run *cmd* in *cwd*, write cleaned output to *out_path*. Return True on success."""
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(f"  command : {' '.join(cmd)}")
    print(f"  cwd     : {cwd}")
    print(f"  output  : {out_path}\n")

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env={**os.environ, "NO_COLOR": "1", "FORCE_COLOR": ""},
        )
    except FileNotFoundError:
        msg = f"[ERROR] Command not found: {cmd[0]}"
        print(msg)
        out_path.write_text(msg + "\n", encoding="utf-8")
        return False

    lines: list[str] = []
    assert proc.stdout is not None
    for raw_line in proc.stdout:
        clean_line = strip_ansi(raw_line)
        lines.append(clean_line)
        sys.stdout.write(clean_line)
        sys.stdout.flush()
    proc.wait(timeout=600)

    out_path.write_text("".join(lines), encoding="utf-8")

    ok = proc.returncode == 0
    status = "PASSED" if ok else f"FAILED (exit {proc.returncode})"
    print(f"\n  -> {status}")
    return ok


def main() -> None:
    parser = argparse.ArgumentParser(description=f"Run all {_PROJECT_NAME} test suites.")
    parser.add_argument("--backend-only", action="store_true")
    parser.add_argument("--frontend-only", action="store_true")
    parser.add_argument("--e2e-only", action="store_true")
    parser.add_argument("--out-dir", type=str, default=None)
    args = parser.parse_args()

    run_all = not (args.backend_only or args.frontend_only or args.e2e_only)

    venv_python = _find_venv_python()
    npx = _find_npx()

    ts = datetime.now().strftime("%Y-%m-%d %H.%M")

    out_dir = Path(args.out_dir) if args.out_dir else _OUTPUT_DIR / "test-results"
    out_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, bool | None] = {
        "backend": None,
        "frontend": None,
        "e2e": None,
    }

    # --- Backend (pytest) ---------------------------------------------------
    if run_all or args.backend_only:
        results["backend"] = run_suite(
            label="Backend tests (pytest)",
            cmd=[venv_python, "-m", "pytest", "-v", "--tb=short", "--no-header"],
            cwd=_BACKEND_DIR,
            out_path=out_dir / f"backend-tests-{ts}.txt",
        )

    # --- Frontend (vitest) ---------------------------------------------------
    if run_all or args.frontend_only:
        results["frontend"] = run_suite(
            label="Frontend tests (vitest)",
            cmd=[npx, "vitest", "run", "--reporter=verbose"],
            cwd=_FRONTEND_DIR,
            out_path=out_dir / f"frontend-tests-{ts}.txt",
        )

    # --- E2E (playwright) ----------------------------------------------------
    if run_all or args.e2e_only:
        results["e2e"] = run_suite(
            label="E2E tests (Playwright)",
            cmd=[npx, "playwright", "test", "--reporter=list"],
            cwd=_E2E_DIR,
            out_path=out_dir / f"e2e-tests-{ts}.txt",
        )

    # --- Summary -------------------------------------------------------------
    print(f"\n{'='*60}")
    print("  Summary")
    print(f"{'='*60}")
    for suite, ok in results.items():
        if ok is None:
            continue
        tag = "PASS" if ok else "FAIL"
        fname = f"{suite}-tests-{ts}.txt"
        print(f"  [{tag}]  {suite:<10}  ->  {out_dir / fname}")
    print()

    if any(v is False for v in results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
