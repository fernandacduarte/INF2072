#!/usr/bin/env python3
# designer: When your briefs ledger grows large, I distill it into a compact
#   index -- one line per entry, newest first -- so pre-skill can scan
#   your recent session history quickly without loading the full briefs
#   file into context. You get faster skill startup and a readable
#   timeline you can eyeball yourself.
"""
generate_briefs_index.py — Generate a lightweight briefs index for fast scanning.

Invocation: skill-invoked, user-cli
Lifecycle: active

Parses OUTPUT_DIR/briefs.md and produces OUTPUT_DIR/briefs-index.md with one-line
summaries per entry, sorted newest first (descending chronological order).
This enables pre-skill to load a compact index instead of the full briefs file.

Usage
-----
    python .claude/skills/scripts/generate_briefs_index.py

Run from the repository root.
Optional flags:
    --verbose  Show each entry being processed
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from project_config import REPO_ROOT, get_path

BRIEFS_FILE = get_path("BRIEFS_FILE") or REPO_ROOT / "_output" / "briefs.md"
INDEX_FILE = BRIEFS_FILE.parent / "briefs-index.md"

# Match optional trailing metadata suffixes at the end of a brief line.
# Order of extraction (from the end): GENERATED, then SHA, then PLAN.
_GENERATED_SUFFIX_RE = re.compile(
    r"\s*\|\s*GENERATED\s*\|\s*([a-z][a-z0-9,\- ]*)\s*$", re.IGNORECASE
)
_SHA_SUFFIX_RE = re.compile(r"\s*\|\s*SHA\s*\|\s*([0-9a-f]{7,40})\s*$", re.IGNORECASE)
_PLAN_SUFFIX_RE = re.compile(r"\s*\|\s*PLAN\s*\|\s*(\S+)\s*$")


def truncate(text: str, max_len: int = 80) -> str:
    """Truncate text to max_len, appending ellipsis if needed."""
    text = text.strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "\u2026"


def _split_fields(line: str) -> list[str]:
    """Split a briefs line on ' | ' delimiters, returning stripped fields."""
    return [f.strip() for f in line.split(" | ")]


def _extract_skill(raw_skill: str) -> str:
    """Extract just the skill name from a field that may contain flags.

    E.g., 'research --deep' -> 'research', 'plan' -> 'plan'.
    """
    return raw_skill.split()[0] if raw_skill else raw_skill


def _extract_trailing_metadata(text: str) -> tuple[str, str, str, str]:
    """Strip optional trailing metadata suffixes from the end of a brief line.

    Extraction order (from the end): GENERATED, SHA, PLAN.

    Returns (brief_text, plan_id, head_sha, generated).
    Missing fields return ''.
    """
    remaining = text
    generated = ""
    head_sha = ""
    plan_id = ""

    m = _GENERATED_SUFFIX_RE.search(remaining)
    if m:
        generated = m.group(1).strip()
        remaining = remaining[: m.start()].strip()

    m = _SHA_SUFFIX_RE.search(remaining)
    if m:
        head_sha = m.group(1).strip()
        remaining = remaining[: m.start()].strip()

    m = _PLAN_SUFFIX_RE.search(remaining)
    if m:
        plan_id = m.group(1).strip()
        remaining = remaining[: m.start()].strip()

    return remaining, plan_id, head_sha, generated


def _parse_done_line(fields: list[str]) -> dict | None:
    """Parse a DONE entry from split fields.

    Expected structure (minimum 6 fields):
      DONE | done_datetime | STARTED | start_datetime | skill [flags] | brief... [| PLAN | id]

    The brief may contain ' | ' so we rejoin fields[5:] and then strip the
    optional PLAN suffix from the end.
    """
    if len(fields) < 6:
        return None
    if fields[2] != "STARTED":
        return None

    raw_brief = " | ".join(fields[5:])
    brief, plan_id, head_sha, generated = _extract_trailing_metadata(raw_brief)

    return {
        "date": fields[3],
        "skill": _extract_skill(fields[4]),
        "brief": brief,
        "status": "DONE",
        "plan_id": plan_id,
        "head_sha": head_sha,
        "generated": generated,
    }


def _parse_started_line(fields: list[str]) -> dict | None:
    """Parse a STARTED entry from split fields.

    Expected structure (minimum 4 fields):
      STARTED | datetime | skill [flags] | brief...

    The brief may contain ' | ' so we rejoin fields[3:].
    """
    if len(fields) < 4:
        return None

    raw_brief = " | ".join(fields[3:])

    brief, _, head_sha, generated = _extract_trailing_metadata(raw_brief)

    return {
        "date": fields[1],
        "skill": _extract_skill(fields[2]),
        "brief": brief,
        "status": "STARTED",
        "plan_id": "",
        "head_sha": head_sha,
        "generated": generated,
    }


def parse_briefs(verbose: bool = False) -> list[dict]:
    """Parse briefs.md and return a list of entry dicts."""
    if not BRIEFS_FILE.is_file():
        print(f"ERROR: Briefs file not found: {BRIEFS_FILE}")
        return []

    text = BRIEFS_FILE.read_text(encoding="utf-8", errors="replace")
    entries = []
    unparsed_count = 0

    for line_num, line in enumerate(text.split("\n"), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        fields = _split_fields(line)

        entry = None
        if fields[0] == "DONE":
            entry = _parse_done_line(fields)
        elif fields[0] == "STARTED":
            entry = _parse_started_line(fields)

        if entry:
            entries.append(entry)
            if verbose:
                print(f"  {entry['status']}: {entry['skill']} — {truncate(entry['brief'], 50)}")
        else:
            unparsed_count += 1
            print(f"WARNING: Unparseable line {line_num}: {line[:80]}")

    if unparsed_count > 0:
        print(f"{unparsed_count} unparseable line(s) found")

    return entries


def generate_index(verbose: bool = False) -> int:
    """Generate briefs-index.md. Returns count of indexed entries."""
    entries = parse_briefs(verbose=verbose)
    if not entries:
        print("No entries found in briefs.md")
        return 0

    lines = [
        "# Briefs Index",
        "",
        f"> Auto-generated by `generate_briefs_index.py`. {len(entries)} entries indexed (newest first).",
        "> Do not edit manually -- regenerate with: `python .claude/skills/scripts/generate_briefs_index.py`",
        "",
        "| Date | Skill | Brief | Status | Plan | Head SHA | Generated |",
        "|------|-------|-------|--------|------|----------|-----------|",
    ]

    for e in entries:
        brief_truncated = truncate(e["brief"])
        head_sha = e.get("head_sha", "")
        generated = e.get("generated", "")
        lines.append(
            f"| {e['date']} | {e['skill']} | {brief_truncated} | {e['status']}"
            f" | {e['plan_id']} | {head_sha} | {generated} |"
        )

    lines.append("")
    INDEX_FILE.write_text("\n".join(lines), encoding="utf-8")

    print(f"Generated {INDEX_FILE.relative_to(REPO_ROOT)} with {len(entries)} entries.")
    return len(entries)


def main():
    parser = argparse.ArgumentParser(
        description="Generate a lightweight briefs index for fast scanning"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show each entry being processed"
    )
    args = parser.parse_args()

    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    count = generate_index(verbose=args.verbose)
    if count == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
