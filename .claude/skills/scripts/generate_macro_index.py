#!/usr/bin/env python3
# designer: When you finish any skill run that writes an artifact, I'm the
#   indexer that refreshes `_output/INDEX.md` so you can find the new file
#   without scanning directories -- every plan, advisory, roadmap, proposal,
#   communication, onboarding, and reflection appears on one chronological
#   list, newest first, with any RESERVED rows preserved across regenerations.
"""
generate_macro_index.py -- Unified artifact index generator.

Invocation: skill-invoked, user-cli
Lifecycle: active

Recursively scans all .md files in the project's OUTPUT_DIR and subfolders,
extracts metadata (date, type, title) from each file's header, and generates
OUTPUT_DIR/INDEX.md with all artifacts sorted in descending chronological order
(newest first).

RESERVED rows (created by reserve_id.py) are preserved across regeneration:
the script reads any existing RESERVED rows from INDEX.md before scanning,
and merges them back into the output at their chronological position.

The output directory is read from project/conventions.md (the OUTPUT_DIR
variable), making this script portable across any SEJA-bootstrapped project.

Usage
-----
    python .claude/skills/scripts/generate_macro_index.py
    python .claude/skills/scripts/generate_macro_index.py --verbose
    python .claude/skills/scripts/generate_macro_index.py --finalize 000005 --status DONE

Run from the repository root.
"""

# Rationale for design choices and historical context: see generate_macro_index-rationale.md in this directory.
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from project_config import REPO_ROOT, get_path

OUTPUT_DIR = get_path("OUTPUT_DIR") or REPO_ROOT / "_output"
INDEX_FILE = OUTPUT_DIR / "INDEX.md"

# Files to exclude from indexing (basenames)
EXCLUDED_FILES = {
    "INDEX.md",
    "briefs.md",
    "briefs-index.md",
}


def truncate(text: str, max_len: int = 80) -> str:
    """Truncate text to max_len, appending ellipsis if needed."""
    text = text.strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "\u2026"


# ---------------------------------------------------------------------------
# Date extraction helpers
# ---------------------------------------------------------------------------
_DATETIME_RE = re.compile(r"(\d{4}-\d{2}-\d{2}[\s]+\d{2}:\d{2}(?::\d{2})?(?:\s*UTC)?)")
_DATE_ONLY_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
_FILENAME_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def _normalize_date(date_str: str) -> str:
    """Normalize a date string for consistent sorting."""
    date_str = date_str.strip()
    # Pad to full datetime if only date
    if len(date_str) == 10:  # YYYY-MM-DD
        return date_str + " 00:00:00 UTC"
    return date_str


# ---------------------------------------------------------------------------
# Extractors for known artifact types
# ---------------------------------------------------------------------------

# Plan (done): # DONE | datetime | Plan NNNN | PREFIX-SCOPE | datetime | title
_PLAN_DONE_RE = re.compile(
    r"^#\s+DONE\s*\|\s*([\d\-: UTC]+)\s*\|\s*Plan\s+(\d+)\s*\|\s*(\S+)\s*\|\s*([\d\-: UTC]+)\s*\|\s*([^|]+)",
    re.IGNORECASE,
)

# Plan (open): # Plan NNNN | PREFIX-SCOPE | datetime | title
_PLAN_OPEN_RE = re.compile(
    r"^#\s+Plan\s+(\d+)\s*\|\s*(\S+)\s*\|\s*([\d\-: UTC]+)\s*\|\s*([^|]+)",
    re.IGNORECASE,
)

# Plan (alt done): # Plan NNNN | DONE | PREFIX-SCOPE | datetime | title
_PLAN_ALT_DONE_RE = re.compile(
    r"^#\s+Plan\s+(\d+)\s*\|\s*DONE\s*\|\s*(\S+)\s*\|\s*([\d\-: UTC]+)\s*\|\s*([^|]+)",
    re.IGNORECASE,
)

# Advisory: # Advisory NNNN | PREFIX-SCOPE | datetime | title
_ADVISORY_RE = re.compile(
    r"^#\s+Advisory\s+(\d+)\s*\|\s*(\S+)\s*\|\s*([\d\-: UTC]+)\s*\|\s*(.+)",
    re.IGNORECASE,
)

# Research: # Research NNNN | PREFIX-SCOPE | datetime | title
_RESEARCH_RE = re.compile(
    r"^#\s+Research\s+(\d+)\s*\|\s*(\S+)\s*\|\s*([\d\-: UTC]+)\s*\|\s*(.+)",
    re.IGNORECASE,
)

# Proposal: # Proposal NNNN | PREFIX-SCOPE | datetime | title
_PROPOSAL_RE = re.compile(
    r"^#\s+Proposal\s+(\d+)\s*\|\s*(\S+)\s*\|\s*([\d\-: UTC]+)\s*\|\s*(.+)",
    re.IGNORECASE,
)

# Roadmap: # Roadmap NNNN | datetime | title
_ROADMAP_RE = re.compile(
    r"^#\s+Roadmap\s+(\d+)\s*\|\s*([\d\-: UTC]+)\s*\|\s*(.+)",
    re.IGNORECASE,
)

# QA Session: # QA Session - datetime  (em dash or hyphen)
_QA_SESSION_RE = re.compile(
    r"^#\s+QA\s+Session\s*[\u2014\-]+\s*([\d\-: UTC]+)",
    re.IGNORECASE,
)

# QA Log (dated): # QA Log | <parent-ref> | datetime | title
# New canonical format with datetime as the third pipe field
_QA_LOG_DATED_RE = re.compile(
    r"^#\s+QA\s+Log\s*\|\s*(.+?)\s*\|\s*(\d{4}-\d{2}-\d{2}[\s\d:]*(?:UTC)?)\s*\|\s*(.+)",
    re.IGNORECASE,
)

# QA Log (plan) with pipe: # QA Log | Plan NNNN | title  OR  # QA Log | implement NNNN, NNNN
_QA_LOG_PLAN_PIPE_RE = re.compile(
    r"^#\s+QA\s+Log\s*\|\s*(?:implement\s+)?(?:Plan\s+)?(\d[\d\-,\s]*)(?:\s*\|\s*(.+))?\s*$",
    re.IGNORECASE,
)

# QA Log (plan) with dash/em-dash: # QA Log — Plan NNNN — title
_QA_LOG_PLAN_DASH_RE = re.compile(
    r"^#\s+QA\s+Log\s*[\u2014\-]+\s*(?:Post-skill\s+for\s+)?(?:Plan[s]?\s+)?(\d[\d\-,\s]*)\s*[\u2014\-]+\s*(.+)",
    re.IGNORECASE,
)

# QA Log (skill): # QA Log | skill | brief
_QA_LOG_SKILL_RE = re.compile(
    r"^#\s+QA\s+Log\s*\|\s*(\S+)\s*\|\s*(.+)",
    re.IGNORECASE,
)

# QA Log generic (catch-all for variations like "Post-skill for Plans")
_QA_LOG_GENERIC_RE = re.compile(
    r"^#\s+QA\s+Log\s*[\u2014\-|:]+\s*(.+)",
    re.IGNORECASE,
)

# Metacomm: # Metacommunication Message — title  OR  # Metacommunication Message (subtitle)
_METACOMM_RE = re.compile(
    r"^#\s+Metacommunication\s+Message\s*(?:[\u2014\-]+\s*)?(.+)",
    re.IGNORECASE,
)

# Check log: # Check <id> | PREFIX-SCOPE | datetime | title
_CHECK_LOG_RE = re.compile(
    r"^#\s+Check\s+(\d+)\s*\|\s*(\S+)\s*\|\s*([\d\-: UTC]+)\s*\|\s*(.+)",
    re.IGNORECASE,
)

# Reflection: # Reflection <id> | datetime | title
_REFLECTION_RE = re.compile(
    r"^#\s+Reflection\s+(\d+)\s*\|\s*([\d\-: UTC]+)\s*\|\s*(.+)",
    re.IGNORECASE,
)


def _find_date_in_text(text: str) -> str | None:
    """Try to find a date in the first 10 lines of text."""
    for line in text.split("\n")[:10]:
        m = _DATETIME_RE.search(line)
        if m:
            return m.group(1).strip()
    for line in text.split("\n")[:10]:
        m = _DATE_ONLY_RE.search(line)
        if m:
            return m.group(1).strip()
    return None


def _find_date_in_filename(filename: str) -> str | None:
    """Try to extract a date from filename."""
    m = _FILENAME_DATE_RE.search(filename)
    if m:
        return m.group(1).strip()
    return None


def _find_date_from_mtime(filepath: Path) -> str | None:
    """Last-resort: use file modification time as date."""
    try:
        mtime = os.path.getmtime(filepath)
        return datetime.fromtimestamp(mtime, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M UTC"
        )
    except OSError:
        return None


def extract_artifact(filepath: Path) -> dict | None:
    """Extract artifact metadata from a markdown file."""
    try:
        text = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    # Find the first heading line
    header_line = ""
    for line in text.split("\n")[:5]:
        stripped = line.strip()
        if stripped.startswith("#"):
            header_line = stripped
            break

    if not header_line:
        return None

    rel_path = filepath.relative_to(OUTPUT_DIR)

    # Try each known pattern

    # Plan (done)
    m = _PLAN_DONE_RE.match(header_line)
    if m:
        status = "DONE"
        plan_id = m.group(2).strip().zfill(6)
        is_qa = bool(re.match(r"^plan-\d{6}-qa-", filepath.name))
        return {
            "date": _normalize_date(m.group(4).strip()),
            "type": "Plan QA" if is_qa else "Plan",
            "id": plan_id,
            "title": truncate(m.group(5).strip().rstrip("|").strip()),
            "status": status,
            "file": str(rel_path),
        }

    # Plan (alt done): # Plan NNNN | DONE | PREFIX-SCOPE | datetime | title
    m = _PLAN_ALT_DONE_RE.match(header_line)
    if m:
        plan_id = m.group(1).strip().zfill(6)
        is_qa = bool(re.match(r"^plan-\d{6}-qa-", filepath.name))
        return {
            "date": _normalize_date(m.group(3).strip()),
            "type": "Plan QA" if is_qa else "Plan",
            "id": plan_id,
            "title": truncate(m.group(4).strip().rstrip("|").strip()),
            "status": "DONE",
            "file": str(rel_path),
        }

    # Plan (open)
    m = _PLAN_OPEN_RE.match(header_line)
    if m:
        plan_id = m.group(1).strip().zfill(6)
        is_qa = bool(re.match(r"^plan-\d{6}-qa-", filepath.name))
        return {
            "date": _normalize_date(m.group(3).strip()),
            "type": "Plan QA" if is_qa else "Plan",
            "id": plan_id,
            "title": truncate(m.group(4).strip().rstrip("|").strip()),
            "status": "OPEN",
            "file": str(rel_path),
        }

    # Advisory
    m = _ADVISORY_RE.match(header_line)
    if m:
        return {
            "date": _normalize_date(m.group(3).strip()),
            "type": "Advisory",
            "id": m.group(1).strip().zfill(6),
            "title": truncate(m.group(4).strip().rstrip("|").strip()),
            "status": "DONE",
            "file": str(rel_path),
        }

    # Research (forward-only advisory-to-research rename target)
    m = _RESEARCH_RE.match(header_line)
    if m:
        return {
            "date": _normalize_date(m.group(3).strip()),
            "type": "Research",
            "id": m.group(1).strip().zfill(6),
            "title": truncate(m.group(4).strip().rstrip("|").strip()),
            "status": "DONE",
            "file": str(rel_path),
        }

    # Proposal
    m = _PROPOSAL_RE.match(header_line)
    if m:
        return {
            "date": _normalize_date(m.group(3).strip()),
            "type": "Proposal",
            "id": m.group(1).strip().zfill(6),
            "title": truncate(m.group(4).strip().rstrip("|").strip()),
            "status": "OPEN",
            "file": str(rel_path),
        }

    # Roadmap
    m = _ROADMAP_RE.match(header_line)
    if m:
        return {
            "date": _normalize_date(m.group(2).strip()),
            "type": "Roadmap",
            "id": m.group(1).strip().zfill(6),
            "title": truncate(m.group(3).strip().rstrip("|").strip()),
            "status": "DONE",
            "file": str(rel_path),
        }

    # QA Session
    m = _QA_SESSION_RE.match(header_line)
    if m:
        return {
            "date": _normalize_date(m.group(1).strip()),
            "type": "QA Session",
            "id": "",
            "title": truncate(header_line.lstrip("# ").strip()),
            "status": "",
            "file": str(rel_path),
        }

    # QA Log (dated): # QA Log | <parent-ref> | datetime | title
    m = _QA_LOG_DATED_RE.match(header_line)
    if m:
        # Extract ID from parent ref (e.g., "Advisory 000058" -> "000058")
        parent_ref = m.group(1).strip()
        id_match = re.search(r"(\d{3,6})", parent_ref)
        qa_id = id_match.group(1).strip().zfill(6) if id_match else ""
        return {
            "date": _normalize_date(m.group(2).strip()),
            "type": "QA Log",
            "id": qa_id,
            "title": truncate(m.group(3).strip().rstrip("|").strip()),
            "status": "",
            "file": str(rel_path),
        }

    # QA Log (plan, pipe separator)
    m = _QA_LOG_PLAN_PIPE_RE.match(header_line)
    if m:
        date = _find_date_in_text(text) or _find_date_in_filename(filepath.name) or _find_date_from_mtime(filepath) or ""
        title_raw = m.group(2).strip().rstrip("|").strip() if m.group(2) else f"QA for plan {m.group(1).strip()}"
        return {
            "date": _normalize_date(date) if date else "",
            "type": "QA Log",
            "id": m.group(1).strip(),
            "title": truncate(title_raw),
            "status": "",
            "file": str(rel_path),
        }

    # QA Log (plan, dash/em-dash separator)
    m = _QA_LOG_PLAN_DASH_RE.match(header_line)
    if m:
        date = _find_date_in_text(text) or _find_date_in_filename(filepath.name) or _find_date_from_mtime(filepath) or ""
        return {
            "date": _normalize_date(date) if date else "",
            "type": "QA Log",
            "id": m.group(1).strip(),
            "title": truncate(m.group(2).strip().rstrip("|").strip()),
            "status": "",
            "file": str(rel_path),
        }

    # QA Log (skill)
    m = _QA_LOG_SKILL_RE.match(header_line)
    if m:
        date = _find_date_in_text(text) or _find_date_in_filename(filepath.name) or _find_date_from_mtime(filepath) or ""
        return {
            "date": _normalize_date(date) if date else "",
            "type": "QA Log",
            "id": "",
            "title": truncate(m.group(2).strip().rstrip("|").strip()),
            "status": "",
            "file": str(rel_path),
        }

    # QA Log (generic catch-all)
    m = _QA_LOG_GENERIC_RE.match(header_line)
    if m:
        date = _find_date_in_text(text) or _find_date_in_filename(filepath.name) or _find_date_from_mtime(filepath) or ""
        return {
            "date": _normalize_date(date) if date else "",
            "type": "QA Log",
            "id": "",
            "title": truncate(m.group(1).strip().rstrip("|").strip()),
            "status": "",
            "file": str(rel_path),
        }

    # Metacomm
    m = _METACOMM_RE.match(header_line)
    if m:
        date = _find_date_in_text(text) or _find_date_in_filename(filepath.name) or _find_date_from_mtime(filepath) or ""
        return {
            "date": _normalize_date(date) if date else "",
            "type": "Metacomm",
            "id": "",
            "title": truncate(m.group(1).strip()),
            "status": "",
            "file": str(rel_path),
        }

    # Check log
    m = _CHECK_LOG_RE.match(header_line)
    if m:
        return {
            "date": _normalize_date(m.group(3).strip()),
            "type": "Check",
            "id": m.group(1).strip().zfill(6),
            "title": truncate(m.group(4).strip().rstrip("|").strip()),
            "status": "DONE",
            "file": str(rel_path),
        }

    # Reflection
    m = _REFLECTION_RE.match(header_line)
    if m:
        return {
            "date": _normalize_date(m.group(2).strip()),
            "type": "Reflection",
            "id": m.group(1).strip().zfill(6),
            "title": truncate(m.group(3).strip().rstrip("|").strip()),
            "status": "",
            "file": str(rel_path),
        }

    # Fallback: try to extract date from text, filename, or mtime
    date = _find_date_in_text(text) or _find_date_in_filename(filepath.name) or _find_date_from_mtime(filepath)
    if date:
        title = header_line.lstrip("# ").strip()
        return {
            "date": _normalize_date(date),
            "type": "Other",
            "id": "",
            "title": truncate(title),
            "status": "",
            "file": str(rel_path),
        }

    return None


# ---------------------------------------------------------------------------
# RESERVED row helpers
# ---------------------------------------------------------------------------

# Regex to parse a table row: | Date | Type | ID | Title | Status | File |
_TABLE_ROW_RE = re.compile(
    r"^\|\s*([^|]*)\|\s*([^|]*)\|\s*([^|]*)\|\s*([^|]*)\|\s*([^|]*)\|\s*([^|]*)\|"
)


def _extract_reserved_rows() -> list[dict]:
    """Read existing INDEX.md and return entries with status RESERVED."""
    if not INDEX_FILE.is_file():
        return []
    reserved: list[dict] = []
    try:
        text = INDEX_FILE.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    for line in text.split("\n"):
        m = _TABLE_ROW_RE.match(line)
        if not m:
            continue
        status = m.group(5).strip()
        if status != "RESERVED":
            continue
        # Reconstruct the entry dict from the row fields
        file_cell = m.group(6).strip()
        # Extract filename and link from markdown link: [name](path)
        link_m = re.match(r"\[([^\]]*)\]\(([^)]*)\)", file_cell)
        file_val = link_m.group(2) if link_m else ""
        reserved.append({
            "date": m.group(1).strip(),
            "type": m.group(2).strip(),
            "id": m.group(3).strip(),
            "title": m.group(4).strip(),
            "status": "RESERVED",
            "file": file_val,
        })
    return reserved


def generate_index(verbose: bool = False) -> int:
    """Generate INDEX.md from all artifact files. Returns count of indexed entries."""
    if not OUTPUT_DIR.is_dir():
        print(f"ERROR: Output directory not found: {OUTPUT_DIR}")
        return 0

    # Extract RESERVED rows before regenerating (they have no .md file on disk)
    reserved_entries = _extract_reserved_rows()
    if verbose and reserved_entries:
        for r in reserved_entries:
            print(f"  Preserved RESERVED: [{r['type']}] {r['id']} -- {r['title']}")

    # Collect all .md files recursively, excluding specific files
    md_files = sorted(
        f
        for f in OUTPUT_DIR.rglob("*.md")
        if f.is_file()
        and f.name not in EXCLUDED_FILES
    )

    entries = []
    scanned_ids: set[str] = set()
    for fp in md_files:
        entry = extract_artifact(fp)
        if entry:
            entries.append(entry)
            if entry["id"]:
                scanned_ids.add(entry["id"])
            if verbose:
                print(f"  Indexed: [{entry['type']}] {entry.get('id', '')} -- {entry['title']}")
        elif verbose:
            print(f"  Skipped (no match): {fp.relative_to(OUTPUT_DIR)}")

    # Merge back RESERVED entries whose ID was NOT found among scanned artifacts
    for r in reserved_entries:
        if r["id"] and r["id"] in scanned_ids:
            if verbose:
                print(f"  RESERVED {r['id']} superseded by scanned artifact, dropping")
            continue
        entries.append(r)

    # Sort by date descending (newest first), entries without dates go last
    entries.sort(key=lambda e: e["date"] if e["date"] else "", reverse=True)

    # Write INDEX.md
    lines = [
        "# Artifact Index",
        "",
        f"> Auto-generated by `generate_macro_index.py`. {len(entries)} artifacts indexed (newest first).",
        "> Do not edit manually -- regenerate with: `python .claude/skills/scripts/generate_macro_index.py`",
        "",
        "| Date | Type | ID | Title | Status | File |",
        "|------|------|----|-------|--------|------|",
    ]

    for e in entries:
        file_link = e["file"].replace("\\", "/")
        if file_link:
            file_cell = f"[{Path(e['file']).name}]({file_link})"
        else:
            file_cell = ""
        lines.append(
            f"| {e['date']} | {e['type']} | {e['id']} | {e['title']} | {e['status']} | {file_cell} |"
        )

    lines.append("")
    INDEX_FILE.write_text("\n".join(lines), encoding="utf-8")

    print(f"Generated {INDEX_FILE.relative_to(REPO_ROOT)} with {len(entries)} entries.")
    return len(entries)


def finalize_reserved(artifact_id: str, status: str, verbose: bool = False) -> bool:
    """Replace a RESERVED row with actual artifact metadata for the given ID.

    Re-scans artifact files to find the one matching *artifact_id*, then
    regenerates INDEX.md with the RESERVED row replaced by real metadata.
    """
    padded_id = artifact_id.strip().zfill(6)

    # First check there IS a reserved row for this ID
    reserved = _extract_reserved_rows()
    matching = [r for r in reserved if r["id"] == padded_id]
    if not matching:
        print(f"ERROR: No RESERVED row found for ID {padded_id}")
        return False

    # Scan all artifact files to find one with this ID
    found_entry: dict | None = None
    for fp in OUTPUT_DIR.rglob("*.md"):
        if not fp.is_file() or fp.name in EXCLUDED_FILES:
            continue
        entry = extract_artifact(fp)
        if entry and entry["id"] == padded_id:
            # Override status with the requested one
            entry["status"] = status
            found_entry = entry
            break

    if not found_entry:
        print(f"ERROR: No artifact file found with ID {padded_id} to finalize")
        return False

    if verbose:
        print(f"  Finalized: [{found_entry['type']}] {padded_id} -- {found_entry['title']} ({status})")

    # Regenerate the full index; the scanned artifact will supersede the RESERVED row
    count = generate_index(verbose=verbose)
    return count > 0


def main():
    parser = argparse.ArgumentParser(
        description="Unified artifact index generator for OUTPUT_DIR"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show each file being processed",
    )
    parser.add_argument(
        "--finalize", metavar="ID",
        help="Replace the RESERVED row for ID with actual artifact metadata",
    )
    parser.add_argument(
        "--status", choices=["DONE", "OPEN"], default="DONE",
        help="Status to assign when finalizing (default: DONE)",
    )
    args = parser.parse_args()

    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

    if args.finalize:
        ok = finalize_reserved(args.finalize, args.status, verbose=args.verbose)
        if not ok:
            sys.exit(1)
    else:
        count = generate_index(verbose=args.verbose)
        if count == 0:
            sys.exit(1)


if __name__ == "__main__":
    main()
