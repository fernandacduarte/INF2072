#!/usr/bin/env python3
# designer: Before you commit a change to a human-authored design
#   file, I look at what is actually changing. If anything other than
#   an allowed lifecycle marker has moved, I stop the commit. You
#   keep those files under your own hand and block the harness from
#   quietly rewriting your prose.
"""
check_human_markers_only.py -- Verify that diffs to Human (markers) files
contain ONLY allowed marker mutations.

Invocation: agent-invoked, hook-ci
Lifecycle: active

Runs as a preflight check (post-skill step 6c via run_preflight_fast.py).
Parses a git diff (staged by default), filters to files classified as
Human (markers), and rejects any added/removed non-blank line that does not
match an entry in ALLOWED_MARKERS.

Usage
-----
    python .claude/skills/scripts/check_human_markers_only.py --staged
    python .claude/skills/scripts/check_human_markers_only.py --range HEAD~1..HEAD
    # Testing only (requires SEJA_ALLOW_TEST_DIFF_INPUT=1):
    SEJA_ALLOW_TEST_DIFF_INPUT=1 python .claude/skills/scripts/check_human_markers_only.py \\
        --diff-from-file path/to/synthetic.diff

Exit codes: 0 pass (or no-op empty registry), 1 violation, 2 runtime error.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

from human_markers_registry import (
    ALLOWED_MARKERS,
    HUMAN_MARKERS_FILES,
    is_human_markers_file,
)


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]


_DIFF_FILE_RE = re.compile(r"^diff --git a/(\S+) b/(\S+)$")
_HUNK_RE = re.compile(r"^@@ .* @@")


def _get_diff(args: argparse.Namespace) -> str:
    """Return the unified diff text to parse."""
    if args.diff_from_file:
        if os.environ.get("SEJA_ALLOW_TEST_DIFF_INPUT") != "1":
            print(
                "ERROR: --diff-from-file requires SEJA_ALLOW_TEST_DIFF_INPUT=1 (testing only)",
                file=sys.stderr,
            )
            sys.exit(2)
        return Path(args.diff_from_file).read_text(encoding="utf-8")

    if args.range:
        cmd = ["git", "diff", args.range]
    else:
        cmd = ["git", "diff", "--cached"]
    try:
        # Explicit UTF-8 + errors='replace' is load-bearing on Windows: git diff
        # output of large staged changes can contain bytes that aren't valid in
        # the default cp1252 codec, causing a UnicodeDecodeError crash when
        # text=True is used without an explicit encoding.
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except FileNotFoundError:
        print("ERROR: git not found in PATH", file=sys.stderr)
        sys.exit(2)
    if result.returncode != 0:
        print(f"ERROR: git diff failed: {result.stderr}", file=sys.stderr)
        sys.exit(2)
    return result.stdout


def _line_is_allowed(line: str) -> bool:
    """Return True if a diff content line matches any allowed marker regex."""
    for spec in ALLOWED_MARKERS.values():
        if re.fullmatch(spec["line_regex"], line):
            return True
    return False


def _parse_and_check(diff_text: str, verbose: bool) -> tuple[int, int, list[dict]]:
    """Parse unified diff, return (marker_file_count, violation_count, violations)."""
    current_file: str | None = None
    current_hunk: str = ""
    marker_files: set[str] = set()
    violations: list[dict] = []

    in_tracked_file = False

    for raw_line in diff_text.splitlines():
        m = _DIFF_FILE_RE.match(raw_line)
        if m:
            # Normalize to forward slashes and check against registry
            new_path = m.group(2).replace("\\", "/")
            if is_human_markers_file(new_path):
                current_file = new_path
                marker_files.add(new_path)
                in_tracked_file = True
            else:
                current_file = None
                in_tracked_file = False
            current_hunk = ""
            continue

        if not in_tracked_file or current_file is None:
            continue

        if _HUNK_RE.match(raw_line):
            current_hunk = raw_line
            continue

        if not raw_line:
            continue

        # Skip diff metadata lines that start with +++ or ---
        if raw_line.startswith("+++") or raw_line.startswith("---"):
            continue

        if raw_line[0] not in "+-":
            continue

        content = raw_line[1:]
        if not content.strip():
            # Blank line additions/removals are allowed
            continue

        if not _line_is_allowed(content):
            violations.append({
                "file": current_file,
                "hunk": current_hunk,
                "line": content[:120],
                "sign": raw_line[0],
            })

    return len(marker_files), len(violations), violations


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify Human (markers) files only contain allowed marker mutations."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--staged", action="store_true", help="Check staged changes (default).")
    mode.add_argument("--range", help="Check a git ref range, e.g. HEAD~1..HEAD.")
    parser.add_argument(
        "--diff-from-file",
        help="Read a unified diff from a file (testing only; requires SEJA_ALLOW_TEST_DIFF_INPUT=1).",
    )
    parser.add_argument("--verbose", action="store_true", help="Print detailed info.")
    args = parser.parse_args()

    # Behavior 1: loud warn + no-op on empty registry
    if not HUMAN_MARKERS_FILES:
        print(
            "WARNING: no files in HUMAN_MARKERS_FILES; check_human_markers_only.py is a no-op",
            file=sys.stderr,
        )
        return 0

    diff_text = _get_diff(args)
    marker_file_count, violation_count, violations = _parse_and_check(diff_text, args.verbose)

    if violation_count == 0:
        print(
            f"PASS: no prose mutations detected in {marker_file_count} "
            f"Human (markers) file(s)"
        )
        return 0

    print(
        f"FAIL: {violation_count} prose mutation violation(s) in "
        f"{marker_file_count} Human (markers) file(s)",
        file=sys.stderr,
    )
    for v in violations:
        print(f"  file: {v['file']}", file=sys.stderr)
        print(f"  hunk: {v['hunk']}", file=sys.stderr)
        print(f"  {v['sign']}{v['line']}", file=sys.stderr)
        print("", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
