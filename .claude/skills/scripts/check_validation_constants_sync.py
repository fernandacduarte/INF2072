#!/usr/bin/env python3
# designer: When your backend and frontend both enforce input limits, I
#   compare the two sides' validation constants and tell you which limits
#   disagree and which constants only one side knows about. This is how
#   a "max 255 characters" rule in your Python stays aligned with the
#   same rule in your TypeScript without anyone having to cross-check
#   by hand.
"""
check_validation_constants_sync.py — Detect drift between backend and frontend
validation constants.

Invocation: agent-invoked, hook-ci
Lifecycle: active

Checks performed
================
  1. Parse the backend constants file for all named integer constants.
  2. Parse the frontend constants.ts for the VALIDATION object entries.
  3. Auto-detect matching pairs by intersecting constant names.
  4. Report value mismatches and constants present on one side but not the other.

Configuration (via project/conventions.md)
------------------------------------------
  BACKEND_UTILS_DIR        — directory containing the backend constants file
  BACKEND_CONSTANTS_FILE   — filename (default: validation_constants.py)
  FRONTEND_UTILS_DIR       — directory containing the frontend constants file
  FRONTEND_CONSTANTS_FILE  — filename (default: constants.ts)

Usage
-----
    python .claude/skills/scripts/check_validation_constants_sync.py

CHECK_PLUGIN_MANIFEST:
  name: Validation Constants Sync
  stack:
    backend: [flask]
    frontend: [react]
  scope: validation
  critical: true
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from project_config import REPO_ROOT, get, get_path

_be_constants_file = get("BACKEND_CONSTANTS_FILE", "validation_constants.py")
_fe_constants_file = get("FRONTEND_CONSTANTS_FILE", "constants.ts")

BACKEND_CONSTANTS = (
    get_path("BACKEND_UTILS_DIR") or REPO_ROOT / "backend" / "app" / "utils"
) / _be_constants_file
FRONTEND_CONSTANTS = (
    get_path("FRONTEND_UTILS_DIR") or REPO_ROOT / "frontend" / "src" / "utils"
) / _fe_constants_file

# Regex to match  CONSTANT_NAME = <number>  in Python
_PY_CONST = re.compile(r"^([A-Z][A-Z0-9_]+)\s*=\s*(\d+)", re.MULTILINE)

# Regex to match  KEY: <number>,  inside the VALIDATION object in TS
_TS_CONST = re.compile(r"([A-Z][A-Z0-9_]+)\s*:\s*(\d+)")


def parse_backend() -> dict[str, int]:
    """Return {CONSTANT_NAME: value} from the backend constants file."""
    text = BACKEND_CONSTANTS.read_text(encoding="utf-8")
    return {m.group(1): int(m.group(2)) for m in _PY_CONST.finditer(text)}


def parse_frontend() -> dict[str, int]:
    """Return {KEY: value} from the frontend VALIDATION object."""
    text = FRONTEND_CONSTANTS.read_text(encoding="utf-8")
    # Find the VALIDATION block
    match = re.search(r"export\s+const\s+VALIDATION\s*=\s*Object\.freeze\(\{(.*?)\}\)", text, re.DOTALL)
    if not match:
        return {}
    block = match.group(1)
    return {m.group(1): int(m.group(2)) for m in _TS_CONST.finditer(block)}


def main() -> None:
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("# Validation Constants Sync Check\n")
    print(f"  Backend file:  {BACKEND_CONSTANTS}")
    print(f"  Frontend file: {FRONTEND_CONSTANTS}\n")

    if not BACKEND_CONSTANTS.exists():
        print(f"ERROR: Backend constants file not found: {BACKEND_CONSTANTS}")
        sys.exit(1)
    if not FRONTEND_CONSTANTS.exists():
        print(f"ERROR: Frontend constants file not found: {FRONTEND_CONSTANTS}")
        sys.exit(1)

    be = parse_backend()
    fe = parse_frontend()

    if not be:
        print("WARNING: No integer constants found in backend file")
    if not fe:
        print("WARNING: No entries found in frontend VALIDATION object")

    errors = []

    # Auto-detect pairs: constants with the same name on both sides
    shared_keys = sorted(set(be.keys()) & set(fe.keys()))
    be_only = sorted(set(be.keys()) - set(fe.keys()))
    fe_only = sorted(set(fe.keys()) - set(be.keys()))

    for key in shared_keys:
        if be[key] != fe[key]:
            errors.append(
                f"VALUE MISMATCH: {key}={be[key]} (backend) vs "
                f"VALIDATION.{key}={fe[key]} (frontend)"
            )
        else:
            print(f"  OK  {key} = {be[key]}")

    if be_only:
        print(f"\n  Backend-only constants (no frontend match): {', '.join(be_only)}")
    if fe_only:
        print(f"\n  Frontend-only constants (no backend match): {', '.join(fe_only)}")

    print()
    if not shared_keys:
        print("WARNING: No matching constant names found between backend and frontend.")
        print("Check that constant names match or that the correct files are configured.")
        sys.exit(1)
    elif errors:
        print(f"## Issues ({len(errors)})\n")
        for msg in errors:
            print(f"- X {msg}")
        print(f"\nFAIL: {len(errors)} issue(s) found")
        sys.exit(1)
    else:
        print(f"PASS: All {len(shared_keys)} validation constants are in sync")


if __name__ == "__main__":
    main()
