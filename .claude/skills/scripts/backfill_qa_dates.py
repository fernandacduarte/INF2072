#!/usr/bin/env python3
# designer: When you look at an old Q&A log and cannot tell when the
#   conversation happened, I walk every Q&A file in your workspace,
#   work out the most plausible date from the body or the git history,
#   and write it into the header. Safe to re-run: I never overwrite a
#   date that is already there.
"""
backfill_qa_dates.py -- One-time script to add dates to existing QA log headers.

Invocation: user-cli
Lifecycle: one-shot

Scans all QA log files (*-qa-*.md and qa-*.md) in OUTPUT_DIR, checks if the
header already contains a datetime, and if not, inserts one derived from:
  1. A **Session date:** or **Date:** line in the file body
  2. The git commit date when the file was first added
  3. The file modification time (last resort)

Idempotent: safe to run multiple times. Files already containing a datetime
in the header are skipped.

Usage
-----
    python .claude/skills/scripts/backfill_qa_dates.py
    python .claude/skills/scripts/backfill_qa_dates.py --dry-run
    python .claude/skills/scripts/backfill_qa_dates.py --verbose

Run from the repository root.
"""

# Rationale for design choices and historical context: see backfill_qa_dates-rationale.md in this directory.
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from project_config import REPO_ROOT, get_path

OUTPUT_DIR = get_path("OUTPUT_DIR") or REPO_ROOT / "_output"

# Match a datetime pattern in a string
_DATETIME_RE = re.compile(r"\d{4}-\d{2}-\d{2}[\s]+\d{2}:\d{2}(?::\d{2})?(?:\s*UTC)?")
_DATE_ONLY_RE = re.compile(r"\d{4}-\d{2}-\d{2}")

# Match **Session date:** or **Date:** lines
_SESSION_DATE_RE = re.compile(
    r"\*\*(?:Session\s+)?[Dd]ate\*?\*?\s*:\s*(.+)", re.IGNORECASE
)

# QA Log header with pipe separators
_QA_HEADER_RE = re.compile(r"^(#\s+QA\s+Log\s*\|.*?)$", re.MULTILINE)


def _header_has_date(header: str) -> bool:
    """Check if a QA Log header already contains a datetime."""
    # Count pipe-separated fields; if >=4 fields, likely has a date
    parts = [p.strip() for p in header.split("|")]
    for part in parts:
        if _DATETIME_RE.search(part):
            return True
    return False


def _find_date_in_body(text: str) -> str | None:
    """Look for **Session date:** or **Date:** in the file body."""
    for line in text.split("\n"):
        m = _SESSION_DATE_RE.search(line)
        if m:
            date_str = m.group(1).strip()
            dm = _DATETIME_RE.search(date_str)
            if dm:
                return dm.group(0).strip()
            dm = _DATE_ONLY_RE.search(date_str)
            if dm:
                return dm.group(0).strip() + " 00:00:00 UTC"
    return None


def _find_date_from_git(filepath: Path) -> str | None:
    """Get the commit date when the file was first added."""
    try:
        result = subprocess.run(
            ["git", "log", "--format=%aI", "--diff-filter=A", "--follow", "--", str(filepath)],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            # Take the last line (earliest commit)
            iso_date = result.stdout.strip().split("\n")[-1].strip()
            if iso_date:
                dt = datetime.fromisoformat(iso_date)
                return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except (subprocess.TimeoutExpired, ValueError, OSError):
        pass
    return None


def _find_date_from_mtime(filepath: Path) -> str | None:
    """Last resort: file modification time."""
    try:
        mtime = os.path.getmtime(filepath)
        return datetime.fromtimestamp(mtime, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M UTC"
        )
    except OSError:
        return None


def _insert_date_in_header(header: str, date: str) -> str:
    """Insert a date field into a QA Log header.

    Transforms:
      # QA Log | Advisory 000011 | Skills Critical Appraisal
    into:
      # QA Log | Advisory 000011 | 2026-03-28 12:00:00 UTC | Skills Critical Appraisal
    """
    parts = [p.strip() for p in header.split("|")]
    if len(parts) >= 3:
        # Insert date as the third field (between parent ref and title)
        new_parts = parts[:2] + [date] + parts[2:]
        return " | ".join(new_parts)
    elif len(parts) == 2:
        # Only has "# QA Log" and one other field
        return " | ".join(parts + [date])
    return header


def backfill(dry_run: bool = False, verbose: bool = False) -> tuple[int, int]:
    """Backfill dates in QA log headers. Returns (modified, skipped) counts."""
    if not OUTPUT_DIR.is_dir():
        print(f"ERROR: Output directory not found: {OUTPUT_DIR}")
        return 0, 0

    # Find all QA log files (prefixed with qa- or containing -qa- as a QA variant)
    # Exclude files where -qa- appears only in the slug portion.
    qa_files: list[Path] = []
    for fp in OUTPUT_DIR.rglob("*.md"):
        name = fp.name
        if name.startswith("qa-"):
            qa_files.append(fp)
        elif re.match(r"^[a-z]+-\d{6}-qa-", name):
            # Matches artifact QA companion files such as <type>-NNNNNN-qa-...
            qa_files.append(fp)

    qa_files.sort()
    modified = 0
    skipped = 0

    for fp in qa_files:
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            print(f"  ERROR reading {fp}: {e}")
            continue

        # Find the header line
        header_match = _QA_HEADER_RE.search(text)
        if not header_match:
            if verbose:
                print(f"  Skip (no QA Log header): {fp.relative_to(OUTPUT_DIR)}")
            skipped += 1
            continue

        header = header_match.group(1)

        if _header_has_date(header):
            if verbose:
                print(f"  Skip (already has date): {fp.relative_to(OUTPUT_DIR)}")
            skipped += 1
            continue

        # Find the best date
        date = (
            _find_date_in_body(text)
            or _find_date_from_git(fp)
            or _find_date_from_mtime(fp)
        )

        if not date:
            print(f"  WARNING: No date found for {fp.relative_to(OUTPUT_DIR)}")
            skipped += 1
            continue

        new_header = _insert_date_in_header(header, date)
        new_text = text.replace(header, new_header, 1)

        if dry_run:
            print(f"  Would update: {fp.relative_to(OUTPUT_DIR)}")
            print(f"    Before: {header}")
            print(f"    After:  {new_header}")
        else:
            fp.write_text(new_text, encoding="utf-8")
            if verbose:
                print(f"  Updated: {fp.relative_to(OUTPUT_DIR)} ({date})")

        modified += 1

    return modified, skipped


def main():
    parser = argparse.ArgumentParser(
        description="Backfill dates in QA log headers"
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show each file processed")
    args = parser.parse_args()

    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    modified, skipped = backfill(dry_run=args.dry_run, verbose=args.verbose)
    action = "Would modify" if args.dry_run else "Modified"
    print(f"\n{action}: {modified} files, Skipped: {skipped} files")


if __name__ == "__main__":
    main()
