#!/usr/bin/env python3
# designer: When you adopt the decision digest on an existing project,
#   I sweep every advisory log you have already written, pull out the
#   high and medium recommendations, and seed the digest so your past
#   decisions show up alongside new ones. Safe to re-run: I skip
#   anything I have already recorded.
"""
backfill_decision_digest.py -- One-time backfill of decision-digest.jsonl from existing advisory logs.

Invocation: user-cli
Lifecycle: one-shot

Scans all advisory logs in ADVISORY_DIR for HIGH/MEDIUM recommendations
and appends them as JSONL records to the decision digest. Idempotent:
skips records whose source_id + recommendation index already exist.

Usage
-----
    python .claude/skills/scripts/backfill_decision_digest.py
    python .claude/skills/scripts/backfill_decision_digest.py --dry-run

Run from the repository root.
"""

# Rationale for design choices and historical context: see backfill_decision_digest-rationale.md in this directory.
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from project_config import REPO_ROOT, get_path

OUTPUT_DIR = get_path("OUTPUT_DIR") or REPO_ROOT / "_output"
ADVISORY_DIR = get_path("ADVISORY_DIR") or OUTPUT_DIR / "advisory-logs"
RESEARCH_DIR = get_path("RESEARCH_DIR") or OUTPUT_DIR / "research-logs"
DIGEST_FILE = OUTPUT_DIR / "decision-digest.jsonl"

# Advisory header pattern
_ADVISORY_HEADER_RE = re.compile(
    r"^#\s+Advisory\s+(\d+)\s*\|.*?\|\s*(\d{4}-\d{2}-\d{2})\s+\d{2}:\d{2}\s+UTC\s*\|\s*(.+)$",
    re.MULTILINE,
)

# Research header pattern for the forward-only advisory-to-research rename.
_RESEARCH_HEADER_RE = re.compile(
    r"^#\s+Research\s+(\d+)\s*\|.*?\|\s*(\d{4}-\d{2}-\d{2})\s+\d{2}:\d{2}\s+UTC\s*\|\s*(.+)$",
    re.MULTILINE,
)

# Recommendation line pattern
_REC_LINE_RE = re.compile(
    r"^\d+\.\s+\*\*\[(\w+)\]\*\*\s+(.+)$", re.MULTILINE
)

# Tags line pattern
_TAGS_RE = re.compile(r"^tags:\s*(.+)$", re.MULTILINE)


def _slugify_tags(title: str) -> list[str]:
    """Derive tags from a title slug."""
    words = re.split(r"[-_\s|]+", title.lower().strip())
    stop = {"the", "a", "an", "and", "or", "for", "to", "in", "of", "on", "is", "with"}
    return [w for w in words if w and w not in stop and len(w) > 2][:5]


def _load_existing_keys() -> set[str]:
    """Load existing record keys from the digest file for dedup.

    Uses a composite key of source_id + decision_statement prefix to detect
    semantic duplicates regardless of ID format (adv-* vs backfill-*).
    """
    if not DIGEST_FILE.is_file():
        return set()
    keys = set()
    for line in DIGEST_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
            key = f"{record.get('source_id', '')}|{record.get('decision_statement', '')[:80]}"
            keys.add(key)
        except json.JSONDecodeError:
            continue
    return keys


def backfill(dry_run: bool = False) -> int:
    """Scan advisory and research logs and append new records to the digest. Returns count of new records."""
    advisory_files: list[Path] = []
    if ADVISORY_DIR.is_dir():
        advisory_files += sorted(ADVISORY_DIR.glob("advisory-*.md"))
    else:
        print(f"WARNING: Advisory directory not found: {ADVISORY_DIR}")
    if RESEARCH_DIR.is_dir():
        advisory_files += sorted(RESEARCH_DIR.glob("research-*.md"))
    if not advisory_files:
        print("ERROR: No advisory or research logs found.")
        return 0

    existing_keys = _load_existing_keys()
    new_records = []

    for fpath in advisory_files:
        text = fpath.read_text(encoding="utf-8", errors="replace")

        header_match = _ADVISORY_HEADER_RE.search(text) or _RESEARCH_HEADER_RE.search(text)
        if not header_match:
            continue

        adv_id = header_match.group(1)
        adv_date = header_match.group(2)
        adv_title = header_match.group(3).strip()

        # Parse tags
        tags_match = _TAGS_RE.search(text)
        if tags_match:
            tags = [t.strip() for t in tags_match.group(1).split(",")]
        else:
            tags = _slugify_tags(adv_title)

        # Find recommendations section
        rec_section = None
        for heading in ["## Recommendations Summary", "### Recommendations"]:
            idx = text.find(heading)
            if idx != -1:
                rec_section = text[idx:]
                next_h2 = re.search(r"\n## ", rec_section[len(heading):])
                if next_h2:
                    rec_section = rec_section[: len(heading) + next_h2.start()]
                break

        if not rec_section:
            continue

        rec_idx = 0
        for m in _REC_LINE_RE.finditer(rec_section):
            priority_raw = m.group(1).lower()
            if priority_raw not in ("high", "medium"):
                continue

            rec_text = m.group(2).strip()
            rec_idx += 1

            record_id = f"backfill-{adv_id}-{rec_idx}"
            dedup_key = f"advisory-{adv_id}|{rec_text[:80]}"
            if dedup_key in existing_keys:
                continue

            record = {
                "id": record_id,
                "source_type": "advisory",
                "source_id": f"advisory-{adv_id}",
                "decision_statement": rec_text[:200],
                "rationale_summary": None,
                "tags": tags,
                "date": adv_date,
                "d_nnn_id": None,
                "priority": priority_raw,
            }
            new_records.append(record)

    if not new_records:
        print("No new records to backfill.")
        return 0

    if dry_run:
        print(f"DRY RUN: Would append {len(new_records)} records to {DIGEST_FILE.relative_to(REPO_ROOT)}:")
        for r in new_records:
            print(f"  [{r['priority']}] {r['source_id']}: {r['decision_statement'][:80]}")
        return len(new_records)

    DIGEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    with DIGEST_FILE.open("a", encoding="utf-8") as f:
        for record in new_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Appended {len(new_records)} records to {DIGEST_FILE.relative_to(REPO_ROOT)}.")
    return len(new_records)


def main():
    parser = argparse.ArgumentParser(
        description="Backfill decision-digest.jsonl from existing advisory logs"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print extracted records without writing to the digest"
    )
    args = parser.parse_args()

    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    backfill(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
