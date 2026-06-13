#!/usr/bin/env python3
# designer: When a skill produces a new artifact that was spawned by an earlier
#   artifact, I update the source artifact's `spawned:` field so the two are
#   linked without manual bookkeeping. Feed me the path to the new artifact;
#   I read its `source:` header, locate the source file in INDEX.md, and
#   append the new artifact's type-ID token to the source's `spawned:` line
#   (inserting the line if it doesn't exist yet).
"""
update_cross_refs.py -- Cross-reference updater for SEJA artifact headers.

Invocation: skill-invoked
Lifecycle: active

Reads an artifact file, extracts its `source: <type>-<id>` header, finds the
source file via _output/INDEX.md, and appends the new artifact's token to the
source file's `spawned:` line.  If `spawned:` is absent it inserts it after
the `source:` line, or after `tags:`, or after the title/header line.

Usage
-----
    python .claude/skills/scripts/update_cross_refs.py --artifact <path>
    python .claude/skills/scripts/update_cross_refs.py --artifact _output/plans/plan-000546-foo.md

Run from the repository root.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from pathlib import Path

from project_config import REPO_ROOT, get_path

OUTPUT_DIR = get_path("OUTPUT_DIR") or REPO_ROOT / "_output"
INDEX_FILE = OUTPUT_DIR / "INDEX.md"

# Matches `source: advisory-000058` or `source: research-000545 -- some note`
_SOURCE_RE = re.compile(
    r"^source:\s+([a-zA-Z][a-zA-Z0-9_-]*?)-(\d+)(?:\s|--|$)", re.IGNORECASE
)

# Matches the path column in INDEX.md table rows:
# | ... | [filename](relative/path.md) |
_INDEX_ROW_RE = re.compile(
    r"^\|\s*[^|]*\|\s*([^|]*?)\s*\|\s*(\d+)\s*\|[^|]*\|[^|]*\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|",
)


def _read_header_lines(artifact_path: Path, n: int = 10) -> list[str]:
    """Return up to n lines from the artifact file."""
    try:
        lines = artifact_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        print(f"WARNING: cannot read artifact {artifact_path}: {exc}", file=sys.stderr)
        return []
    return lines[:n]


def _extract_source(header_lines: list[str]) -> tuple[str, str] | None:
    """Return (source_type, source_id) from header lines, or None."""
    for line in header_lines:
        m = _SOURCE_RE.match(line)
        if m:
            return m.group(1).lower(), m.group(2)
    return None


def _artifact_token_from_path(artifact_path: Path) -> tuple[str, str] | None:
    """Derive (type, id) from filename e.g. plan-000546-foo.md -> ('plan', '000546')."""
    stem = artifact_path.stem  # e.g. plan-000546-foo
    parts = stem.split("-")
    # Expect at least <type>-<6-digit-id>[-slug...]
    if len(parts) < 2:
        return None
    artifact_type = parts[0].lower()
    candidate_id = parts[1]
    if not candidate_id.isdigit():
        return None
    return artifact_type, candidate_id


def _find_source_file(source_type: str, source_id: str) -> Path | None:
    """Locate the source artifact file via INDEX.md."""
    if not INDEX_FILE.is_file():
        print(f"WARNING: INDEX.md not found at {INDEX_FILE}", file=sys.stderr)
        return None

    index_text = INDEX_FILE.read_text(encoding="utf-8")
    # Normalize the ID to compare without leading zeros where safe
    padded_id = source_id.zfill(6)

    for line in index_text.splitlines():
        m = _INDEX_ROW_RE.match(line)
        if not m:
            continue
        row_type = m.group(1).strip().lower()
        row_id = m.group(2).strip().zfill(6)
        rel_path = m.group(4).strip()

        if row_id == padded_id and row_type == source_type:
            full_path = OUTPUT_DIR / rel_path
            if full_path.is_file():
                return full_path

    return None


def _update_spawned(source_path: Path, new_token: str) -> bool:
    """Append new_token to `spawned:` in source_path, inserting if absent.

    Returns True if the file was modified, False otherwise.
    """
    text = source_path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    spawned_idx: int | None = None
    source_idx: int | None = None
    tags_idx: int | None = None
    title_idx: int | None = None

    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("spawned:"):
            spawned_idx = i
        elif stripped.startswith("source:"):
            source_idx = i
        elif stripped.startswith("tags:"):
            tags_idx = i
        elif stripped.startswith("#") and title_idx is None:
            title_idx = i

    if spawned_idx is not None:
        # Append to existing spawned: line
        existing_stripped = lines[spawned_idx].rstrip()
        lines[spawned_idx] = existing_stripped + f", {new_token}\n"
    else:
        # Insert a new spawned: line
        insert_after = source_idx if source_idx is not None else (
            tags_idx if tags_idx is not None else title_idx
        )
        if insert_after is None:
            insert_after = 0  # fallback: after first line

        new_line = f"spawned: {new_token}\n"
        lines.insert(insert_after + 1, new_line)

    new_text = "".join(lines)
    if new_text == text:
        return False

    # Atomic write: write to a temp file in the same directory, then rename.
    dir_ = source_path.parent
    fd, tmp_name = tempfile.mkstemp(dir=str(dir_), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(new_text)
        os.replace(tmp_name, str(source_path))
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise

    return True


def run(artifact_path: Path) -> int:
    """Main logic. Returns exit code (0 = success/no-op)."""
    if not artifact_path.is_file():
        print(f"ERROR: artifact not found: {artifact_path}", file=sys.stderr)
        return 1

    header = _read_header_lines(artifact_path)
    source = _extract_source(header)

    if source is None:
        # No source: header -- silent no-op
        return 0

    source_type, source_id = source

    token_info = _artifact_token_from_path(artifact_path)
    if token_info is None:
        print(
            f"WARNING: cannot parse type/id from artifact filename: {artifact_path.name}",
            file=sys.stderr,
        )
        return 0

    new_type, new_id = token_info
    new_token = f"{new_type}-{new_id}"

    source_file = _find_source_file(source_type, source_id)
    if source_file is None:
        print(
            f"WARNING: source artifact {source_type}-{source_id} not found in INDEX.md "
            f"-- skipping spawned update",
            file=sys.stderr,
        )
        return 0

    modified = _update_spawned(source_file, new_token)
    if modified:
        print(
            f"Updated spawned: in {source_file.relative_to(REPO_ROOT)} "
            f"(added {new_token})"
        )
    else:
        print(
            f"No change needed in {source_file.relative_to(REPO_ROOT)} "
            f"({new_token} may already be present)"
        )

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Update the spawned: field in a source artifact when a new artifact "
            "declares it as its source."
        )
    )
    parser.add_argument(
        "--artifact",
        required=True,
        metavar="PATH",
        help="Path to the produced artifact (e.g., _output/plans/plan-000546-foo.md)",
    )
    args = parser.parse_args()

    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

    artifact_path = Path(args.artifact)
    if not artifact_path.is_absolute():
        artifact_path = Path.cwd() / artifact_path

    sys.exit(run(artifact_path))


if __name__ == "__main__":
    main()
