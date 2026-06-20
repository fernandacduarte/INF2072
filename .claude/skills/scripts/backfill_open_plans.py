#!/usr/bin/env python3
# designer: When you turn on the pending ledger on an older project,
#   I look through every plan you have not yet marked done, queue the
#   recent ones for execution in /pending, and quietly dismiss the
#   stale ones so your inbox is not flooded. Re-running me later will
#   not undo any dismissals you have already chosen.
"""
backfill_open_plans.py -- One-shot backfill of implement pending entries.

Invocation: user-cli
Lifecycle: one-shot

Scans PLANS_DIR for plan files that lack the `# DONE | ...` header, filters out
progress/QA siblings, and files `implement` entries in the pending ledger
for each. Plans older than `--bulk-dismiss-older-than` days (default 30)
are filed as `dismissed` rather than `pending`, so the backfill does not
flood `/pending` with stale entries.

Idempotent: entries whose (source, type) pair already exists in the ledger
(in any state -- pending, snoozed, done, dismissed) are skipped. User
dismissals from a prior `/pending` session are NOT resurrected.

Usage
-----
    python .claude/skills/scripts/backfill_open_plans.py [--dry-run]
        [--bulk-dismiss-older-than N] [--reset]

Flags
-----
    --dry-run
        Print the planned actions without mutating the ledger.
    --bulk-dismiss-older-than N
        Plans older than N days are filed as dismissed (reason:
        `plan older than Nd at backfill`). Default: 30.
    --reset
        Remove all existing implement entries first. Hidden flag for
        dev re-runs; user dismissals will be lost.

Exit codes: 0 success, 2 runtime error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from project_config import get_path, get_pending_file


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]


_PLAN_FILE_RE = re.compile(
    r"^plan-(?P<id>\d{6})-(?P<rest>.+)\.md$"
)
_HEADER_DATE_RE = re.compile(
    r"^# Plan \d{6}\s*\|[^|]*\|\s*(?P<date>\d{4}-\d{2}-\d{2})\s+\d{2}:\d{2}\s+UTC"
)
_HEADER_TITLE_RE = re.compile(
    r"^# Plan \d{6}\s*\|[^|]*\|[^|]*\|\s*(?P<title>[^|]+?)(?:\s*\|.*)?\s*$"
)
_ID_RE = re.compile(r"pa-(\d{6})")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_sibling(rest: str) -> bool:
    """Return True when the suffix identifies a progress/QA sibling."""
    return (
        rest == "progress"
        or rest.startswith("qa-")
        or rest.startswith("qa-log-")
    )


def _parse_plan_header(path: Path) -> tuple[datetime | None, str | None]:
    """Return (plan_datetime_utc, short_title) from the plan header."""
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("# Plan "):
                    date_m = _HEADER_DATE_RE.match(line)
                    title_m = _HEADER_TITLE_RE.match(line)
                    dt = None
                    if date_m:
                        try:
                            dt = datetime.strptime(
                                date_m.group("date"), "%Y-%m-%d"
                            ).replace(tzinfo=timezone.utc)
                        except ValueError:
                            dt = None
                    title = None
                    if title_m:
                        t = title_m.group("title").strip()
                        # Strip trailing "| Review: ..." if present in the title group
                        if t.lower().startswith("review:"):
                            t = None
                        else:
                            title = t
                    return dt, title
    except OSError:
        pass
    return None, None


def _plan_age_days(path: Path) -> int:
    """Return the plan's age in days, from the header date or file mtime."""
    dt, _ = _parse_plan_header(path)
    if dt is None:
        try:
            dt = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        except OSError:
            return 0
    return max(0, (_utcnow() - dt).days)


def _read_ledger(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _append(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    if existing and not existing.endswith("\n"):
        existing += "\n"
    existing += json.dumps(record, sort_keys=True) + "\n"
    path.write_text(existing, encoding="utf-8", newline="\n")


def _reduce(records: list[dict]) -> dict[str, dict]:
    """Last-write-wins reducer (tolerant)."""
    state: dict[str, dict] = {}
    for rec in records:
        rid = rec.get("id")
        if not rid:
            continue
        if rid not in state:
            state[rid] = dict(rec)
        else:
            merged = dict(state[rid])
            merged.update(rec)
            state[rid] = merged
    return state


def _next_id(records: list[dict]) -> str:
    max_n = 0
    for r in records:
        m = _ID_RE.fullmatch(r.get("id", ""))
        if m:
            n = int(m.group(1))
            if n > max_n:
                max_n = n
    return f"pa-{max_n + 1:06d}"


def _existing_sources(state: dict[str, dict]) -> set[str]:
    """Return sources already represented by an implement entry (any state)."""
    out: set[str] = set()
    for r in state.values():
        if r.get("type") == "implement":
            src = r.get("source")
            if src:
                out.add(src)
    return out


def _discover_open_plans(plans_dir: Path) -> list[tuple[str, Path]]:
    """Return (plan_id, path) for open plan files (no # DONE header, not siblings)."""
    out: list[tuple[str, Path]] = []
    for p in sorted(plans_dir.glob("plan-*.md")):
        m = _PLAN_FILE_RE.match(p.name)
        if not m:
            continue
        rest = m.group("rest")
        if _is_sibling(rest):
            continue
        # Determine open/done from file header, not filename
        try:
            with p.open(encoding="utf-8") as f:
                first_line = f.readline().strip()
            if re.match(r"^#\s+DONE\b", first_line, re.IGNORECASE):
                continue
        except OSError:
            continue
        out.append((f"plan-{m.group('id')}", p))
    return out


def _reset_implement_entries(path: Path) -> int:
    """Drop every record whose type is implement. Returns count removed."""
    if not path.is_file():
        return 0
    removed = 0
    keep: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            keep.append(line)
            continue
        # Drop records that are about implement entries (initial add or transition).
        # We identify by the initial record's type; transition records only carry id.
        # To be safe, build a set of ids to drop in two passes.
        keep.append(line)
    # Two-pass: identify implement ids, then keep only lines whose id is not in the set.
    ids_to_drop: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("type") == "implement":
            rid = rec.get("id")
            if rid:
                ids_to_drop.add(rid)
    new_lines: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            new_lines.append(line)
            continue
        if rec.get("id") in ids_to_drop:
            removed += 1
            continue
        new_lines.append(line)
    path.write_text("\n".join(new_lines) + ("\n" if new_lines else ""), encoding="utf-8", newline="\n")
    # removed here counts transition lines too; cap at ids-count for reporting clarity
    return len(ids_to_drop)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1] if __doc__ else "")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned actions without mutating the ledger.",
    )
    parser.add_argument(
        "--bulk-dismiss-older-than",
        type=int,
        default=30,
        dest="bulk_dismiss_older_than",
        help="Plans older than N days are filed as dismissed. Default: 30.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Remove existing implement entries first (dev only).",
    )
    args = parser.parse_args()

    plans_dir = get_path("PLANS_DIR")
    if plans_dir is None or not plans_dir.is_dir():
        print("ERROR: PLANS_DIR not found", file=sys.stderr)
        return 2

    ledger_path = get_pending_file()
    if ledger_path is None:
        print("ERROR: OUTPUT_DIR not configured", file=sys.stderr)
        return 2

    if args.reset and not args.dry_run:
        removed = _reset_implement_entries(ledger_path)
        print(f"Reset: removed {removed} implement entries from the ledger.")

    candidates = _discover_open_plans(plans_dir)
    records = _read_ledger(ledger_path)
    state = _reduce(records)
    tracked_sources = _existing_sources(state) if not args.reset else set()

    filed_pending = 0
    filed_dismissed = 0
    skipped_tracked = 0
    now = _utcnow()
    now_iso_s = _iso(now)

    for plan_id, path in candidates:
        if plan_id in tracked_sources:
            skipped_tracked += 1
            continue

        age_days = _plan_age_days(path)
        _, title = _parse_plan_header(path)
        if not title:
            # Fall back to the filename's slug portion.
            m = _PLAN_FILE_RE.match(path.name)
            title = m.group("rest") if m else plan_id

        description = f"Execute {plan_id} {title}"
        should_dismiss = age_days >= args.bulk_dismiss_older_than

        if args.dry_run:
            action = "DISMISS" if should_dismiss else "PENDING"
            print(f"  [{action}] {plan_id} (age {age_days}d) -- {title}")
            if should_dismiss:
                filed_dismissed += 1
            else:
                filed_pending += 1
            continue

        # Real run: append records.
        records = _read_ledger(ledger_path)  # re-read for fresh id
        new_id = _next_id(records)
        create_rec = {
            "id": new_id,
            "type": "implement",
            "created_at": now_iso_s,
            "source": plan_id,
            "description": description,
            "status": "pending",
            "snooze_until": None,
            "last_reminded_at": None,
        }
        _append(ledger_path, create_rec)
        if should_dismiss:
            _append(ledger_path, {
                "id": new_id,
                "status": "dismissed",
                "closed_at": now_iso_s,
                "reason": f"plan older than {args.bulk_dismiss_older_than}d at backfill",
            })
            filed_dismissed += 1
        else:
            filed_pending += 1

    total = len(candidates)
    prefix = "DRY-RUN: " if args.dry_run else ""
    print(
        f"{prefix}Filed {filed_pending} pending + {filed_dismissed} dismissed "
        f"from {total} candidate plan files ({skipped_tracked} skipped as already tracked)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
