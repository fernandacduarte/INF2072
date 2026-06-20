#!/usr/bin/env python3
# designer: When a skill finishes and needs to record its completion in the
#   briefs ledger, I find the STARTED entry whose brief text matches what you
#   give me and flip it to DONE -- prepending the done timestamp and optionally
#   tagging the plan ID. I keep the ledger accurate without forcing you to
#   hand-edit the file or worry about line offsets.
"""
mark_brief_done.py — Mark a STARTED brief entry as DONE in briefs.md.

Invocation: skill-invoked, agent-invoked
Lifecycle: active

Finds the most recent STARTED line whose brief text contains the given pattern
(substring match) and rewrites it as a DONE entry.

Output format:
  DONE | <done-time> | STARTED | <start-time> | <skill> | <brief> [| PLAN | <id>]

The file is written back atomically (temp-file swap). Briefs are newest-first,
so "most recent" means the first matching STARTED line encountered top-to-bottom.

Usage
-----
    python .claude/skills/scripts/mark_brief_done.py \\
        --brief-pattern <text> \\
        --done-time "2026-05-03 18:00 UTC" \\
        [--plan-id 000546]

Exit codes: 0 = success, 1 = no matching STARTED entry found.
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

# Resolve project_config from sibling directory regardless of cwd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from project_config import REPO_ROOT, get_path

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

# BRIEFS_FILE comes from conventions.md; fall back to the conventional default.
_DEFAULT_BRIEFS = REPO_ROOT / "_output" / "briefs.md"
BRIEFS_FILE: Path = get_path("BRIEFS_FILE") or _DEFAULT_BRIEFS

_PLAN_SUFFIX_MARKER = " | PLAN | "


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def _line_is_started(line: str) -> bool:
    """Return True if this is a STARTED entry (not already DONE)."""
    return line.startswith("STARTED | ")


def _line_contains_pattern(line: str, pattern: str) -> bool:
    """Return True if the brief text portion of the line contains the pattern."""
    # The brief text starts after "STARTED | <datetime> | <skill> | ".
    # A simple substring match across the whole line is safe because the
    # pattern is unlikely to match the fixed prefix fields.
    return pattern.lower() in line.lower()


def _already_has_plan(line: str) -> bool:
    """Return True if the line already carries a PLAN suffix."""
    return _PLAN_SUFFIX_MARKER in line


def _build_done_line(started_line: str, done_time: str, plan_id: str | None) -> str:
    """Construct the DONE replacement for a STARTED line.

    Prepends 'DONE | <done-time> | ' to the original STARTED line.
    Appends ' | PLAN | <id>' when plan_id is given and not already present.
    """
    base = f"DONE | {done_time} | {started_line}"

    if plan_id and not _already_has_plan(started_line):
        base = base.rstrip() + f"{_PLAN_SUFFIX_MARKER}{plan_id}"

    return base


def find_and_mark(
    briefs_path: Path,
    pattern: str,
    done_time: str,
    plan_id: str | None,
) -> bool:
    """Find the most recent STARTED line matching pattern and mark it DONE.

    Reads the file, rewrites it atomically. Returns True on success, False
    if no matching entry was found (caller handles exit code).

    Briefs are newest-first, so the first match encountered is the most recent.
    """
    text = briefs_path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    matched_index: int | None = None
    for i, line in enumerate(lines):
        stripped = line.rstrip("\r\n")
        if _line_is_started(stripped) and _line_contains_pattern(stripped, pattern):
            matched_index = i
            break  # first match = most recent, stop here

    if matched_index is None:
        return False

    original = lines[matched_index].rstrip("\r\n")
    replacement = _build_done_line(original, done_time, plan_id)

    # Preserve the original line ending
    ending = lines[matched_index][len(lines[matched_index].rstrip("\r\n")):]
    lines[matched_index] = replacement + ending

    _write_atomic(briefs_path, "".join(lines))
    return True


def _write_atomic(path: Path, content: str) -> None:
    """Write content to path via a temp file to avoid partial writes."""
    dir_ = path.parent
    # NamedTemporaryFile with delete=False so we can rename on Windows too
    fd, tmp_path = tempfile.mkstemp(dir=str(dir_), prefix=".briefs_tmp_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        # On Windows, os.replace is atomic within the same filesystem
        os.replace(tmp_path, str(path))
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mark_brief_done.py",
        description=(
            "Mark the most recent STARTED brief entry whose text contains "
            "--brief-pattern as DONE."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python .claude/skills/scripts/mark_brief_done.py \\\n"
            '      --brief-pattern "plan 000546" \\\n'
            '      --done-time "2026-05-03 18:00 UTC" \\\n'
            "      --plan-id 000546\n"
        ),
    )
    parser.add_argument(
        "--brief-pattern",
        required=True,
        metavar="TEXT",
        help="Substring to match against STARTED brief entries (case-insensitive).",
    )
    parser.add_argument(
        "--done-time",
        required=True,
        metavar="DATETIME",
        help='UTC datetime string, e.g. "2026-05-03 18:00 UTC".',
    )
    parser.add_argument(
        "--plan-id",
        default=None,
        metavar="NNN",
        help=(
            "Plan ID to append as '| PLAN | NNN' suffix, "
            "unless the entry already carries one."
        ),
    )
    parser.add_argument(
        "--briefs-file",
        default=None,
        metavar="PATH",
        help=(
            "Override the briefs file path (default: resolved from conventions.md "
            f"or {_DEFAULT_BRIEFS.relative_to(REPO_ROOT)})."
        ),
    )
    return parser


def main() -> None:
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = _build_parser()
    args = parser.parse_args()

    briefs_path = Path(args.briefs_file) if args.briefs_file else BRIEFS_FILE

    if not briefs_path.is_file():
        print(
            f"ERROR: briefs file not found: {briefs_path}",
            file=sys.stderr,
        )
        sys.exit(1)

    success = find_and_mark(
        briefs_path=briefs_path,
        pattern=args.brief_pattern,
        done_time=args.done_time,
        plan_id=args.plan_id,
    )

    if not success:
        print(
            f"WARNING: no STARTED entry matching pattern {args.brief_pattern!r} found in {briefs_path}",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"OK: marked DONE in {briefs_path}")
    sys.exit(0)


if __name__ == "__main__":
    main()
