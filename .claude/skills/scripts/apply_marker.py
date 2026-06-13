#!/usr/bin/env python3
# designer: When you need to flip a lifecycle marker on a human-authored
#   design file -- status, established date, incorporated-by-plan, or a
#   changelog entry -- I am the only hand allowed to touch those files.
#   You tell me which entry and which marker; I rewrite the exact line
#   and leave every other word untouched.
"""
apply_marker.py -- Sole write path for Human (markers) files.

Invocation: skill-invoked, user-cli
Lifecycle: active

Applies lifecycle marker HTML comments (STATUS / ESTABLISHED / INCORPORATED) or
appends a CHANGELOG line to files classified as Human (markers). Agents that
need to update a marker MUST go through this script instead of using Edit or
Write on the file directly. The companion verifier
`check_human_markers_only.py` rejects any prose mutations that slip through.

Empty-allowlist behavior: if HUMAN_MARKERS_FILES is empty, every write attempt
fails the path check in behavior 1a. This is deliberate -- the script refuses
to write when no files are registered. Test suites patch HUMAN_MARKERS_FILES
to a tmp_path copy of marker_fixture.md via the conftest.py fixture.

Usage
-----
    python .claude/skills/scripts/apply_marker.py \\
        --file <path> --id <entry-id> --marker <kind> --value <value> \\
        [--plan <plan-id>] [--date <YYYY-MM-DD>] [--note <text>] [--dry-run]

Exit codes: 0 success, 1 validation failure, 2 runtime error.
"""

# Rationale for design choices and historical context: see apply_marker-rationale.md in this directory.
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from human_markers_registry import (
    ALLOWED_MARKERS,
    HUMAN_MARKERS_FILES,
    is_human_markers_file,
    normalize_path,
)
from project_config import REPO_ROOT


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]


# Accepts both the new lowercase state-machine values (proposed | implemented |
# established | superseded) and the legacy uppercase `IMPLEMENTED` one-shot
# marker from pre-2.8.3 files. This lets a Phase 3b flip REPLACE a
# legacy marker rather than stack a new one above it.
_STATUS_MARKER_RE = re.compile(r"^<!--\s*STATUS:\s*([A-Za-z]+)(?:\s*\|[^>]*)?\s*-->\s*$")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _find_entry_heading(lines: list[str], entry_id: str) -> int:
    """Return the 0-based index of the line matching `### <id>:` or `### <id>$`.

    Raises ValueError on not-found or ambiguous match.
    """
    pattern = re.compile(rf"^###\s+{re.escape(entry_id)}(?::|\s*$)")
    matches = [i for i, ln in enumerate(lines) if pattern.match(ln)]
    if not matches:
        raise ValueError(f"entry id {entry_id!r} not found")
    if len(matches) > 1:
        raise ValueError(f"entry id {entry_id!r} matches {len(matches)} headings (ambiguous)")
    return matches[0]


def _existing_status_value(lines: list[str], heading_idx: int) -> str | None:
    """If the line immediately preceding `heading_idx` is a STATUS marker, return its value."""
    if heading_idx == 0:
        return None
    prev = lines[heading_idx - 1]
    m = _STATUS_MARKER_RE.match(prev.rstrip())
    if not m:
        return None
    return m.group(1)


def _build_marker_line(kind: str, value: str, plan: str | None, date: str | None) -> str:
    """Construct the HTML comment line for STATUS/ESTABLISHED/INCORPORATED."""
    date = date or _today()
    if kind == "STATUS":
        parts = [f"STATUS: {value}"]
        if plan:
            parts.append(plan)
        parts.append(date)
        return f"<!-- {' | '.join(parts)} -->"
    if kind == "ESTABLISHED":
        if not plan:
            raise ValueError("ESTABLISHED marker requires --plan")
        return f"<!-- ESTABLISHED: {plan} | {date} -->"
    if kind == "INCORPORATED":
        if not plan:
            raise ValueError("INCORPORATED marker requires --plan")
        return f"<!-- INCORPORATED: {plan} | {date} -->"
    raise ValueError(f"unknown marker kind {kind!r}")


def _validate_regex(kind: str, line: str) -> None:
    spec = ALLOWED_MARKERS[kind]
    pattern = spec["line_regex"]
    if not re.fullmatch(pattern, line):
        raise ValueError(
            f"{kind} line does not match allowed regex: {line!r}"
        )


def _apply_marker_stamp(
    lines: list[str],
    heading_idx: int,
    marker_line: str,
    replace_existing: bool,
) -> tuple[list[str], int]:
    """Insert or replace the marker line immediately before `heading_idx`.

    Returns (new_lines, line_number_1based) of the inserted/replaced marker.
    """
    new_lines = list(lines)
    if replace_existing and heading_idx > 0:
        # Replace the preceding STATUS marker line
        new_lines[heading_idx - 1] = marker_line
        return new_lines, heading_idx  # 1-based: heading_idx-1+1
    # Insert before the heading
    new_lines.insert(heading_idx, marker_line)
    return new_lines, heading_idx + 1


def _apply_status(
    lines: list[str],
    entry_id: str,
    value: str,
    plan: str | None,
    date: str | None,
) -> tuple[list[str], int, str]:
    spec = ALLOWED_MARKERS["STATUS"]
    if value not in spec["allowed_values"]:
        raise ValueError(
            f"STATUS value {value!r} not in allowed_values {spec['allowed_values']}"
        )
    heading_idx = _find_entry_heading(lines, entry_id)
    existing = _existing_status_value(lines, heading_idx)
    # Normalize the legacy uppercase `IMPLEMENTED` marker to the new lowercase
    # `implemented` value for transition lookup. This lets Phase 3b flip a
    # legacy STATUS: IMPLEMENTED marker to STATUS: established
    # by REPLACING the preceding line rather than stacking a new marker above it.
    effective_existing = "implemented" if existing == "IMPLEMENTED" else existing
    if effective_existing is not None:
        allowed_next = spec["allowed_transitions"].get(effective_existing, [])
        if value not in allowed_next:
            raise ValueError(
                f"STATUS transition {existing!r} -> {value!r} is not allowed "
                f"(allowed: {allowed_next})"
            )
    marker_line = _build_marker_line("STATUS", value, plan, date)
    _validate_regex("STATUS", marker_line)
    new_lines, lineno = _apply_marker_stamp(
        lines, heading_idx, marker_line, replace_existing=(existing is not None)
    )
    return new_lines, lineno, marker_line


def _apply_stamp(
    kind: str,
    lines: list[str],
    entry_id: str,
    plan: str | None,
    date: str | None,
) -> tuple[list[str], int, str]:
    heading_idx = _find_entry_heading(lines, entry_id)
    marker_line = _build_marker_line(kind, "", plan, date)
    _validate_regex(kind, marker_line)
    # Stamps never replace an existing line; they insert before the heading.
    new_lines, lineno = _apply_marker_stamp(
        lines, heading_idx, marker_line, replace_existing=False
    )
    return new_lines, lineno, marker_line


def _apply_decision_append(
    lines: list[str],
    value: str,
    plan: str | None,
    date: str | None,
    note: str | None,
) -> tuple[list[str], int, str]:
    """Append a new D-NNN decision entry to the ## Decisions section.

    The ``value`` parameter carries the full DRR-shaped entry text (everything
    after the ``### D-NNN: <title>`` heading). The ``--id`` argument is ignored
    at the caller level -- the next D-NNN ID is auto-assigned by scanning
    existing entries.

    Returns (new_lines, 1-based-line-number-of-heading, heading_line).
    """
    date = date or _today()

    # Locate the ## Decisions section
    decisions_idx: int | None = None
    for i, ln in enumerate(lines):
        if ln.strip() == "## Decisions":
            decisions_idx = i
            break
    if decisions_idx is None:
        raise ValueError("no '## Decisions' section found in file")

    # Determine next D-NNN ID by scanning ### D-NNN: headings within the
    # ## Decisions section only (not the entire file, which may have D-NNN
    # entries in other sections like ## Entries).
    existing_ids: list[int] = []
    d_heading_re = re.compile(r"^###\s+D-(\d{3}):")
    decisions_end = len(lines)
    for i in range(decisions_idx + 1, len(lines)):
        if lines[i].startswith("## ") and lines[i].strip() != "## Decisions":
            decisions_end = i
            break
    for ln in lines[decisions_idx + 1 : decisions_end]:
        m = d_heading_re.match(ln)
        if m:
            existing_ids.append(int(m.group(1)))
    next_id = max(existing_ids, default=0) + 1
    d_id = f"D-{next_id:03d}"

    # The value is the full entry text; the first line is the title.
    # Expected format: first line = title, rest = body (Context, Decision, etc.)
    value_lines = value.strip().splitlines()
    if not value_lines:
        raise ValueError("DECISION_APPEND --value must not be empty")
    title = value_lines[0].strip()
    body_lines = value_lines[1:] if len(value_lines) > 1 else []

    heading_line = f"### {d_id}: {title}"
    _validate_regex("DECISION_APPEND", heading_line)

    # Find insertion point: end of ## Decisions section (next ## heading or EOF)
    end_idx = len(lines)
    for i in range(decisions_idx + 1, len(lines)):
        if lines[i].startswith("## ") and lines[i].strip() != "## Decisions":
            end_idx = i
            break
    # Walk back to last non-empty line
    insert_at = end_idx
    for i in range(end_idx - 1, decisions_idx, -1):
        if lines[i].strip():
            insert_at = i + 1
            break

    # Build the entry block
    entry_lines = ["", heading_line, ""]
    entry_lines.extend(body_lines)
    if note:
        entry_lines.append("")
        entry_lines.append(f"*Source: {note} ({date})*")

    new_lines = list(lines)
    for offset, el in enumerate(entry_lines):
        new_lines.insert(insert_at + offset, el)

    return new_lines, insert_at + 2, heading_line  # +2 for blank + heading


def _apply_changelog(
    lines: list[str],
    entry_id: str,
    value: str,
    plan: str | None,
    date: str | None,
    note: str | None,
) -> tuple[list[str], int, str]:
    allowed_actions = {"added", "revised", "revoked", "superseded"}
    if value not in allowed_actions:
        raise ValueError(
            f"CHANGELOG_APPEND --value must be one of {sorted(allowed_actions)}"
        )
    if note is None:
        raise ValueError("CHANGELOG_APPEND requires --note")
    date = date or _today()
    plan_token = plan if plan else "-"
    new_line = f"{date} | {entry_id} | {value} | {plan_token} | {note}"
    _validate_regex("CHANGELOG_APPEND", new_line)

    # Locate the ## CHANGELOG section
    changelog_idx: int | None = None
    for i, ln in enumerate(lines):
        if ln.strip() == "## CHANGELOG":
            changelog_idx = i
            break
    if changelog_idx is None:
        raise ValueError("no '## CHANGELOG' section found in file")

    # Append after the last non-empty line in the changelog section.
    # Find the end of the section (either EOF or next '## ' header).
    end_idx = len(lines)
    for i in range(changelog_idx + 1, len(lines)):
        if lines[i].startswith("## ") and lines[i].strip() != "## CHANGELOG":
            end_idx = i
            break
    # Walk back from end_idx to find last non-empty line
    insert_at = end_idx
    for i in range(end_idx - 1, changelog_idx, -1):
        if lines[i].strip():
            insert_at = i + 1
            break

    new_lines = list(lines)
    new_lines.insert(insert_at, new_line)
    return new_lines, insert_at + 1, new_line


def _write_file(path: Path, lines: list[str]) -> None:
    # Preserve trailing newline if original had one.
    content = "\n".join(lines)
    if not content.endswith("\n"):
        content += "\n"
    path.write_text(content, encoding="utf-8", newline="\n")


def _format_diff(old_lines: list[str], new_lines: list[str]) -> str:
    """Return a simple unified diff for --dry-run output."""
    import difflib

    diff = difflib.unified_diff(
        old_lines, new_lines, fromfile="a", tofile="b", lineterm=""
    )
    return "\n".join(diff)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply a lifecycle marker to a Human (markers) file."
    )
    parser.add_argument("--file", required=True, help="Target file (repo-relative).")
    parser.add_argument("--id", dest="entry_id", required=True, help="Entry id, e.g. R-P-001.")
    parser.add_argument(
        "--marker", required=True,
        choices=sorted(ALLOWED_MARKERS.keys()),
        help="Marker kind.",
    )
    parser.add_argument(
        "--value",
        required=False,
        default=None,
        help=(
            "Marker value (e.g. 'implemented' or 'added'). Required for STATUS "
            "and CHANGELOG_APPEND markers; ignored by ESTABLISHED and "
            "INCORPORATED (which are stamp-kind markers)."
        ),
    )
    parser.add_argument(
        "--plan",
        help=(
            "Plan id. Accepts either the fully-qualified form 'plan-NNNNNN' "
            "(e.g., plan-NNNNNN) or a bare 6-digit id (e.g., NNNNNN) which "
            "will be auto-prefixed with 'plan-'."
        ),
    )
    parser.add_argument("--date", help="Override date (YYYY-MM-DD).")
    parser.add_argument("--note", help="CHANGELOG note text.")
    parser.add_argument("--dry-run", action="store_true", help="Print diff without writing.")
    args = parser.parse_args()

    # Post-parse validation 1: --value required for STATUS, CHANGELOG_APPEND,
    # and DECISION_APPEND. Stamp-kind markers (ESTABLISHED, INCORPORATED)
    # ignore the value field.
    if args.marker in ("STATUS", "CHANGELOG_APPEND", "DECISION_APPEND") and args.value is None:
        print(
            f"ERROR: {args.marker} requires --value "
            f"(stamp markers ESTABLISHED and INCORPORATED do not)",
            file=sys.stderr,
        )
        return 1

    # Post-parse validation 2: --plan normalizer. Accepts bare 6-digit id
    # and auto-prefixes 'plan-'. Accepts the fully-qualified form unchanged.
    # Rejects any other form with a clear error.
    if args.plan is not None:
        if re.fullmatch(r"\d{6}", args.plan):
            args.plan = f"plan-{args.plan}"
        elif args.plan == "manual":
            pass  # literal 'manual' is a valid plan token (human-initiated)
        elif not re.fullmatch(r"plan-\d{6}", args.plan):
            print(
                "ERROR: --plan must be 'plan-NNNNNN', a bare 6-digit ID, or "
                f"'manual' (got {args.plan!r})",
                file=sys.stderr,
            )
            return 1

    # Behavior 1a: resolve and validate against allowlist (FIRST CHECK).
    try:
        resolved = Path(args.file).resolve(strict=True)
        rel = resolved.relative_to(REPO_ROOT)
    except (FileNotFoundError, ValueError):
        print(
            f"ERROR: file {args.file} is not a repo-relative existing file",
            file=sys.stderr,
        )
        return 1
    canonical = rel.as_posix()
    if canonical not in HUMAN_MARKERS_FILES:
        print(
            f"ERROR: file {args.file} is not classified as Human (markers); refusing to write.",
            file=sys.stderr,
        )
        return 1

    target_path = REPO_ROOT / canonical

    if args.marker not in ALLOWED_MARKERS:
        print(f"ERROR: unknown marker kind {args.marker!r}", file=sys.stderr)
        return 1

    # Read file
    try:
        raw = target_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: cannot read {target_path}: {exc}", file=sys.stderr)
        return 2

    lines = raw.splitlines()

    try:
        if args.marker == "STATUS":
            new_lines, lineno, _ = _apply_status(
                lines, args.entry_id, args.value, args.plan, args.date
            )
        elif args.marker in ("ESTABLISHED", "INCORPORATED"):
            new_lines, lineno, _ = _apply_stamp(
                args.marker, lines, args.entry_id, args.plan, args.date
            )
        elif args.marker == "CHANGELOG_APPEND":
            new_lines, lineno, _ = _apply_changelog(
                lines, args.entry_id, args.value, args.plan, args.date, args.note
            )
        elif args.marker == "DECISION_APPEND":
            new_lines, lineno, _ = _apply_decision_append(
                lines, args.value, args.plan, args.date, args.note
            )
        else:
            print(f"ERROR: marker kind {args.marker!r} not implemented", file=sys.stderr)
            return 1
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(_format_diff(lines, new_lines))
        return 0

    try:
        _write_file(target_path, new_lines)
    except OSError as exc:
        print(f"ERROR: cannot write {target_path}: {exc}", file=sys.stderr)
        return 2

    if args.value is not None:
        print(f"applied {args.marker}={args.value} to {canonical}:{lineno}")
    else:
        print(f"applied {args.marker} to {canonical}:{lineno}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
