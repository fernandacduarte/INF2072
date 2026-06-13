#!/usr/bin/env python3
# designer: When your project predates SEJA's global-ID convention and its
#   artifacts still carry per-type 4-digit or 6-digit IDs, I'm the one-shot
#   migration that sorts every `_output/` artifact chronologically, assigns
#   fresh 6-digit IDs from 000001 forward, renames the files, rewrites
#   headers and cross-references, updates the briefs and telemetry records,
#   and refreshes the index -- run `--dry-run` first to see the planned
#   renames before you let it rewrite history.
"""
migrate_to_global_ids.py -- One-time migration from mixed 4/6-digit per-type IDs
to globally unique 6-digit chronological IDs.

Invocation: user-cli
Lifecycle: one-shot

Scans all .md files in OUTPUT_DIR subdirectories, extracts datetime from headers,
sorts chronologically, assigns new 6-digit IDs starting from 000001, then:
  - Renames files
  - Updates header lines
  - Updates internal cross-references
  - Updates briefs.md plan IDs
  - Updates telemetry.jsonl IDs
  - Regenerates INDEX.md via generate_macro_index.py
  - Deletes per-folder INDEX.md files

Usage
-----
    python .claude/skills/scripts/migrate_to_global_ids.py --dry-run
    python .claude/skills/scripts/migrate_to_global_ids.py --verbose

Run from the repository root.
"""

# Rationale for design choices and historical context: see migrate_to_global_ids-rationale.md in this directory.
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

from project_config import REPO_ROOT, get_path

OUTPUT_DIR = get_path("OUTPUT_DIR") or REPO_ROOT / "_output"

# ---------------------------------------------------------------------------
# Files to skip entirely
# ---------------------------------------------------------------------------
SKIP_BASENAMES = {
    "INDEX.md",
    "briefs.md",
    "briefs-index.md",
    ".post-skill-checkpoint",
}

SKIP_EXTENSIONS = {".txt", ".jsonl", ".json"}

# Subdirectories to skip entirely
SKIP_DIRS = {"tmp", "old"}

# ---------------------------------------------------------------------------
# Header parsing regexes (reused from generate_macro_index.py)
# ---------------------------------------------------------------------------
_DATETIME_RE = re.compile(r"(\d{4}-\d{2}-\d{2}[\s]+\d{2}:\d{2}(?::\d{2})?(?:\s*UTC)?)")
_DATE_ONLY_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")

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

# SUPERSEDED plan: # SUPERSEDED | date | by Plan NNNN | Plan NNNN | PREFIX-SCOPE | datetime | title
_PLAN_SUPERSEDED_RE = re.compile(
    r"^#\s+SUPERSEDED\s*\|\s*([\d\-]+)\s*\|\s*by\s+Plan\s+(\d+)\s*\|\s*Plan\s+(\d+)\s*\|\s*(\S+)\s*\|\s*([\d\-: UTC]+)\s*\|\s*([^|]+)",
    re.IGNORECASE,
)

# Advisory: # Advisory NNNN | PREFIX-SCOPE | datetime | title
_ADVISORY_RE = re.compile(
    r"^#\s+Advisory\s+(\d+)\s*\|\s*(\S+)\s*\|\s*([\d\-: UTC]+)\s*\|\s*(.+)",
    re.IGNORECASE,
)

# Check log: # Check NNNN | PREFIX-SCOPE | datetime | title
_CHECK_LOG_RE = re.compile(
    r"^#\s+Check\s+(\d+)\s*\|\s*(\S+)\s*\|\s*([\d\-: UTC]+)\s*\|\s*(.+)",
    re.IGNORECASE,
)

# QA session (standalone): # QA NNNN | datetime | title
_QA_STANDALONE_RE = re.compile(
    r"^#\s+QA\s+(\d+)\s*\|\s*([\d\-: UTC]+)\s*\|\s*(.+)",
    re.IGNORECASE,
)

# QA Log (derived from parent): # QA Log | Advisory NNNN | title
_QA_LOG_ADVISORY_RE = re.compile(
    r"^#\s+QA\s+Log\s*\|\s*Advisory\s+(\d+)\s*\|\s*(.+)",
    re.IGNORECASE,
)

# QA Log (derived from parent): # QA Log | Check NNNN | title
_QA_LOG_CHECK_RE = re.compile(
    r"^#\s+QA\s+Log\s*\|\s*Check\s+(\d+)\s*\|\s*(.+)",
    re.IGNORECASE,
)

# QA Log (plan, pipe): # QA Log | Plan NNNN | title
_QA_LOG_PLAN_PIPE_RE = re.compile(
    r"^#\s+QA\s+Log\s*\|\s*(?:implement\s+)?(?:Plan\s+)?(\d[\d\-,\s]*)(?:\s*\|\s*(.+))?\s*$",
    re.IGNORECASE,
)

# QA Log (plan, dash): # QA Log -- Plan NNNN -- title  or  # QA Log -- Plan NNNN | title
_QA_LOG_PLAN_DASH_RE = re.compile(
    r"^#\s+QA\s+Log\s*[\u2014\-]+\s*(?:Post-skill\s+for\s+)?(?:Plan[s]?\s+)?(\d[\d\-,\s]*)\s*[\u2014\-|]+\s*(.+)",
    re.IGNORECASE,
)

# Roadmap: # Roadmap NNNN | datetime | title
_ROADMAP_RE = re.compile(
    r"^#\s+Roadmap\s+(\d+)\s*\|\s*([\d\-: UTC]+)\s*\|\s*(.+)",
    re.IGNORECASE,
)


def _normalize_date(date_str: str) -> str:
    date_str = date_str.strip()
    if len(date_str) == 10:
        return date_str + " 00:00:00 UTC"
    return date_str


def _find_date_in_text(text: str) -> str | None:
    for line in text.split("\n")[:10]:
        m = _DATETIME_RE.search(line)
        if m:
            return m.group(1).strip()
    for line in text.split("\n")[:10]:
        m = _DATE_ONLY_RE.search(line)
        if m:
            return m.group(1).strip()
    return None


def _get_header_line(text: str) -> str:
    for line in text.split("\n")[:5]:
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped
    return ""


# ---------------------------------------------------------------------------
# Artifact classification
# ---------------------------------------------------------------------------

class Artifact:
    """Represents a single artifact file with its metadata."""

    def __init__(
        self,
        filepath: Path,
        art_type: str,
        old_id: str,
        date: str,
        is_derived: bool = False,
        parent_type: str | None = None,
        parent_old_id: str | None = None,
        is_progress: bool = False,
    ):
        self.filepath = filepath
        self.art_type = art_type          # "advisory", "plan", "check", "qa", "roadmap"
        self.old_id = old_id              # original numeric ID (e.g., "0001", "000019")
        self.date = date                  # normalized datetime string for sorting
        self.is_derived = is_derived      # True for qa logs derived from parent
        self.parent_type = parent_type    # "advisory", "plan", "check" for derived QA
        self.parent_old_id = parent_old_id
        self.is_progress = is_progress    # True for plan-NNNN-progress.md files
        self.new_id: str | None = None    # assigned during migration


def classify_file(filepath: Path) -> Artifact | None:
    """Classify a markdown file and extract its metadata."""
    name = filepath.name

    # Skip non-artifact files
    if name in SKIP_BASENAMES:
        return None
    if filepath.suffix in SKIP_EXTENSIONS:
        return None

    # Skip files in excluded directories
    rel = filepath.relative_to(OUTPUT_DIR)
    parts = rel.parts
    if any(p in SKIP_DIRS for p in parts):
        return None

    try:
        text = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    header = _get_header_line(text)
    if not header:
        return None

    # --- Progress files (plan-NNNN-progress.md) ---
    progress_m = re.match(r"^plan-(\d+)-progress\.md$", name)
    if progress_m:
        old_id = progress_m.group(1)
        date = _find_date_in_text(text) or ""
        return Artifact(filepath, "plan", old_id, _normalize_date(date) if date else "",
                        is_progress=True)

    # --- Derived QA: advisory-NNNN-qa-*, plan-NNNN-qa-*, check-NNNN-qa-* ---
    # Filename takes priority: even if the header looks like a primary artifact,
    # these files are QA-derived and follow their parent's ID.
    derived_m = re.match(r"^(advisory|plan|check)-(\d+)-qa-(.+)\.md$", name)
    if derived_m:
        parent_type = derived_m.group(1)
        parent_old_id = derived_m.group(2)
        date = _find_date_in_text(text) or ""
        return Artifact(filepath, "qa-derived", parent_old_id, _normalize_date(date) if date else "",
                        is_derived=True, parent_type=parent_type, parent_old_id=parent_old_id)

    # --- Primary artifacts ---

    # Plan (done): # DONE | datetime | Plan NNNN | ...
    m = _PLAN_DONE_RE.match(header)
    if m:
        return Artifact(filepath, "plan", m.group(2).strip(),
                        _normalize_date(m.group(4).strip()))

    # Plan (alt done): # Plan NNNN | DONE | ...
    m = _PLAN_ALT_DONE_RE.match(header)
    if m:
        return Artifact(filepath, "plan", m.group(1).strip(),
                        _normalize_date(m.group(3).strip()))

    # Plan SUPERSEDED: # SUPERSEDED | date | by Plan X | Plan NNNN | ...
    m = _PLAN_SUPERSEDED_RE.match(header)
    if m:
        return Artifact(filepath, "plan", m.group(3).strip(),
                        _normalize_date(m.group(5).strip()))

    # Plan (open): # Plan NNNN | PREFIX-SCOPE | datetime | title
    m = _PLAN_OPEN_RE.match(header)
    if m:
        return Artifact(filepath, "plan", m.group(1).strip(),
                        _normalize_date(m.group(3).strip()))

    # Advisory: # Advisory NNNN | ...
    m = _ADVISORY_RE.match(header)
    if m:
        return Artifact(filepath, "advisory", m.group(1).strip(),
                        _normalize_date(m.group(3).strip()))

    # Check: # Check NNNN | ...
    m = _CHECK_LOG_RE.match(header)
    if m:
        return Artifact(filepath, "check", m.group(1).strip(),
                        _normalize_date(m.group(3).strip()))

    # Roadmap: # Roadmap NNNN | ...
    m = _ROADMAP_RE.match(header)
    if m:
        return Artifact(filepath, "roadmap", m.group(1).strip(),
                        _normalize_date(m.group(2).strip()))

    # Standalone QA: # QA NNNN | datetime | title
    m = _QA_STANDALONE_RE.match(header)
    if m:
        return Artifact(filepath, "qa", m.group(1).strip(),
                        _normalize_date(m.group(2).strip()))

    return None


# ---------------------------------------------------------------------------
# Migration logic
# ---------------------------------------------------------------------------

def _extract_slug(filepath: Path) -> str:
    """Extract the slug portion of a filename (after type-id prefix)."""
    name = filepath.stem  # without .md
    # Remove prefix like "advisory-0014-qa-" or "plan-0001-done-" etc.
    m = re.match(r"^(?:advisory|plan|check|qa|roadmap)-\d+(?:-qa)?-(.+)$", name)
    return m.group(1) if m else name


def build_mapping(artifacts: list[Artifact], verbose: bool = False) -> dict[tuple[str, str], str]:
    """Build old-id -> new-id mapping. Returns dict of (type, old_id) -> new_id.

    Only primary (non-derived, non-progress) artifacts get new IDs.
    Derived and progress files follow their parent's new ID.

    When duplicate (type, old_id) pairs exist (legacy collisions), the mapping
    stores the LAST assigned new_id, but derived files use slug matching
    to find the best parent.
    """
    # Separate primary vs derived/progress
    primaries = [a for a in artifacts if not a.is_derived and not a.is_progress]
    derived = [a for a in artifacts if a.is_derived]
    progress = [a for a in artifacts if a.is_progress]

    # Sort primaries chronologically
    primaries.sort(key=lambda a: a.date if a.date else "9999-99-99")

    # Assign sequential IDs
    # mapping: last-wins for cross-reference replacement (imperfect but OK for body text)
    mapping: dict[tuple[str, str], str] = {}
    # multi_map: all primaries grouped by (type, old_id) for slug-based lookup
    multi_map: dict[tuple[str, str], list[Artifact]] = defaultdict(list)

    counter = 1
    for art in primaries:
        new_id = str(counter).zfill(6)
        art.new_id = new_id
        mapping[(art.art_type, art.old_id)] = new_id
        multi_map[(art.art_type, art.old_id)].append(art)
        if verbose:
            print(f"  {art.art_type:10s} {art.old_id:>6s} -> {new_id}  ({art.date[:19]})  {art.filepath.name}")
        counter += 1

    # Assign derived QA files: they inherit parent's new ID
    for art in derived:
        key = (art.parent_type, art.parent_old_id)
        candidates = multi_map.get(key, [])
        if len(candidates) == 1:
            art.new_id = candidates[0].new_id
        elif len(candidates) > 1:
            # Multiple parents with same (type, old_id) -- use slug similarity
            derived_slug = _extract_slug(art.filepath)
            best = None
            best_score = -1
            for cand in candidates:
                cand_slug = _extract_slug(cand.filepath)
                # Simple: check if derived slug starts with or contains parent slug
                score = 0
                if derived_slug in cand_slug or cand_slug in derived_slug:
                    score = len(cand_slug)
                # Also check common prefix length
                common = 0
                for a, b in zip(derived_slug, cand_slug):
                    if a == b:
                        common += 1
                    else:
                        break
                score = max(score, common)
                if score > best_score:
                    best_score = score
                    best = cand
            art.new_id = best.new_id if best else candidates[-1].new_id
            if verbose:
                print(f"  Derived {art.filepath.name} -> parent {best.filepath.name if best else '?'} "
                      f"(slug match, score={best_score})")
        else:
            # Parent not found -- try to find any type with that old_id
            for (t, oid), nid in mapping.items():
                if oid == art.parent_old_id:
                    art.new_id = nid
                    break
            if art.new_id is None:
                print(f"  WARNING: no parent for derived QA {art.filepath.name} "
                      f"(parent: {art.parent_type}-{art.parent_old_id})")
                art.new_id = art.parent_old_id.zfill(6)

    # Assign progress files: they inherit parent plan's new ID
    for art in progress:
        key = ("plan", art.old_id)
        candidates = multi_map.get(key, [])
        if candidates:
            # For plan-0007 duplicates, progress goes with last (most recent)
            art.new_id = candidates[-1].new_id
        else:
            print(f"  WARNING: no parent plan for progress {art.filepath.name} "
                  f"(plan {art.old_id})")
            art.new_id = art.old_id.zfill(6)

    return mapping


def _new_filename(art: Artifact) -> str:
    """Compute the new filename for an artifact."""
    name = art.filepath.name
    new_id = art.new_id

    if art.is_progress:
        # plan-NNNN-progress.md -> plan-NNNNNN-progress.md
        return re.sub(r"^plan-\d+-progress\.md$", f"plan-{new_id}-progress.md", name)

    if art.is_derived:
        # advisory-NNNNNN-qa-slug.md -> advisory-NNNNNN-qa-slug.md (new pattern)
        # plan-NNNNNN-qa-slug.md -> plan-NNNNNN-qa-slug.md
        # check-NNNNNN-qa-slug.md -> check-NNNNNN-qa-slug.md
        return re.sub(
            r"^(advisory|plan|check)-\d+-qa-",
            rf"\1-{new_id}-qa-",
            name,
        )

    # Primary artifacts
    # advisory-NNNN-slug.md -> advisory-NNNNNN-slug.md
    # plan-NNNN-done-slug.md -> plan-NNNNNN-done-slug.md
    # check-NNNNNN-slug.md -> check-NNNNNN-slug.md (already 6-digit, but new value)
    # qa-NNNN-slug.md -> qa-NNNNNN-slug.md
    # roadmap-NNNN-slug.md -> roadmap-NNNNNN-slug.md
    patterns = [
        (r"^advisory-\d+-", f"advisory-{new_id}-"),
        (r"^plan-\d+-", f"plan-{new_id}-"),
        (r"^check-\d+-", f"check-{new_id}-"),
        (r"^qa-\d+-", f"qa-{new_id}-"),
        (r"^roadmap-\d+-", f"roadmap-{new_id}-"),
    ]
    for pat, repl in patterns:
        new_name = re.sub(pat, repl, name)
        if new_name != name:
            return new_name

    return name


def _update_header(text: str, art: Artifact, full_mapping: dict[tuple[str, str], str]) -> str:
    """Update the header line with the new ID and update cross-references."""
    lines = text.split("\n")
    new_id = art.new_id

    # Find and update header line
    for i, line in enumerate(lines[:5]):
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue

        new_line = stripped

        if art.is_derived:
            # Derived QA: update the parent reference ID in header
            # e.g., "# QA Log | Advisory 0001 |" -> "# QA Log | Advisory 000042 |"
            # e.g., "# QA Log -- Plan 0002 |" -> "# QA Log -- Plan 000042 |"
            new_line = re.sub(
                r"(Advisory|Plan|Check)\s+0*" + re.escape(art.parent_old_id.lstrip("0") or "0"),
                lambda m: f"{m.group(1)} {new_id}",
                new_line,
            )
        elif art.art_type == "plan":
            # Plan headers: update "Plan NNNN" to "Plan NNNNNN"
            new_line = re.sub(
                r"Plan\s+" + re.escape(art.old_id),
                f"Plan {new_id}",
                new_line,
            )
            # Also update "by Plan NNNN" in SUPERSEDED headers
            for (t, oid), nid in full_mapping.items():
                if t == "plan" and oid != art.old_id:
                    new_line = re.sub(
                        r"by\s+Plan\s+" + re.escape(oid),
                        f"by Plan {nid}",
                        new_line,
                    )
        elif art.art_type == "advisory":
            new_line = re.sub(
                r"Advisory\s+" + re.escape(art.old_id),
                f"Advisory {new_id}",
                new_line,
            )
        elif art.art_type == "check":
            new_line = re.sub(
                r"Check\s+" + re.escape(art.old_id),
                f"Check {new_id}",
                new_line,
            )
        elif art.art_type == "qa":
            new_line = re.sub(
                r"QA\s+" + re.escape(art.old_id),
                f"QA {new_id}",
                new_line,
            )
        elif art.art_type == "roadmap":
            new_line = re.sub(
                r"Roadmap\s+" + re.escape(art.old_id),
                f"Roadmap {new_id}",
                new_line,
            )

        lines[i] = new_line
        break

    return "\n".join(lines)


def _update_cross_references(text: str, full_mapping: dict[tuple[str, str], str]) -> str:
    """Update cross-references throughout the body text.

    Handles patterns like:
      Plan NNNN, Advisory NNNN, Check NNNNNN, QA NNNN, Roadmap NNNN
      plan-NNNN, advisory-NNNN, check-NNNNNN
      source: advisory-NNNN, spawned: plan-NNNN
    """
    # Build a combined lookup: (type_prefix, old_id_stripped) -> new_id
    # where type_prefix is lowercase (plan, advisory, check, qa, roadmap)
    lookup: dict[tuple[str, str], str] = {}
    for (art_type, old_id), new_id in full_mapping.items():
        lookup[(art_type, old_id)] = new_id
        # Also store with stripped leading zeros for flexible matching
        stripped = old_id.lstrip("0") or "0"
        lookup[(art_type, stripped)] = new_id

    type_names = {
        "plan": "Plan",
        "advisory": "Advisory",
        "check": "Check",
        "qa": "QA",
        "roadmap": "Roadmap",
    }

    # Replace "Plan 0011" style references
    for art_type, display_name in type_names.items():
        # "Plan 0011" or "plan 0011" (case-insensitive for the type word)
        text = re.sub(
            rf"(?i)({re.escape(display_name)})\s+(\d{{4,6}})",
            lambda m, _type=art_type: _replace_type_ref(m, _type, lookup),
            text,
        )
        # "plan-0011" or "advisory-0014" in filenames/references
        text = re.sub(
            rf"(?<![a-zA-Z]){art_type}-(\d{{4,6}})(?=[^0-9]|$)",
            lambda m, _type=art_type: _replace_dash_ref(m, _type, lookup),
            text,
        )

    return text


def _replace_type_ref(m: re.Match, art_type: str, lookup: dict) -> str:
    """Replace 'Plan 0011' style reference."""
    display = m.group(1)
    old_id = m.group(2)
    stripped = old_id.lstrip("0") or "0"
    for key in [(art_type, old_id), (art_type, stripped)]:
        if key in lookup:
            return f"{display} {lookup[key]}"
    return m.group(0)


def _replace_dash_ref(m: re.Match, art_type: str, lookup: dict) -> str:
    """Replace 'plan-0011' style reference."""
    old_id = m.group(1)
    stripped = old_id.lstrip("0") or "0"
    for key in [(art_type, old_id), (art_type, stripped)]:
        if key in lookup:
            return f"{art_type}-{lookup[key]}"
    return m.group(0)


def update_briefs(mapping: dict[tuple[str, str], str], dry_run: bool, verbose: bool) -> None:
    """Update _output/briefs.md: replace old plan IDs in | PLAN | <old-id> lines."""
    briefs_path = OUTPUT_DIR / "briefs.md"
    if not briefs_path.is_file():
        return

    text = briefs_path.read_text(encoding="utf-8", errors="replace")
    original = text

    # Replace "| PLAN | 0002" -> "| PLAN | 000042"
    def _repl_plan_brief(m: re.Match) -> str:
        old_id = m.group(1)
        stripped = old_id.lstrip("0") or "0"
        for key in [("plan", old_id), ("plan", stripped)]:
            if key in mapping:
                return f"| PLAN | {mapping[key]}"
        return m.group(0)

    text = re.sub(r"\|\s*PLAN\s*\|\s*(\d{4,6})", _repl_plan_brief, text)

    # Also update inline cross-references like "plan 0002", "advisory 0014"
    text = _update_cross_references(text, mapping)

    if text != original:
        if dry_run:
            print(f"  [dry-run] Would update briefs.md")
        else:
            briefs_path.write_text(text, encoding="utf-8")
            if verbose:
                print(f"  Updated briefs.md")


def update_telemetry(mapping: dict[tuple[str, str], str], dry_run: bool, verbose: bool) -> None:
    """Update _output/telemetry.jsonl: replace old IDs in 'id' and 'plan_id' fields.

    Uses the 'skill' field to infer artifact type for disambiguation:
      plan / implement -> plan
      advise -> advisory
      check -> advisory (old checks used advisory IDs) or check (6-digit IDs)
    """
    telem_path = OUTPUT_DIR / "telemetry.jsonl"
    if not telem_path.is_file():
        return

    lines = telem_path.read_text(encoding="utf-8", errors="replace").split("\n")
    new_lines = []
    changed = False

    # KEEP: advise->advisory is the historical artifact-ID prefix mapping; the skill is now /research but produces advisory-NNN artifacts.
    skill_to_type = {
        "plan": "plan",
        "implement": "plan",
        "advise": "advisory",
        "check": "advisory",
    }

    def _lookup_id(art_type: str, old_id: str) -> str | None:
        stripped = old_id.lstrip("0") or "0"
        for key in [(art_type, old_id), (art_type, stripped)]:
            if key in mapping:
                return mapping[key]
        return None

    def _update_output_path(path: str) -> str:
        if not path:
            return path
        parts = path.rsplit("/", 1)
        dirpart = parts[0] if len(parts) == 2 else ""
        filename = parts[-1]
        for (t, oid), nid in mapping.items():
            old_prefix = f"{t}-{oid}-"
            if filename.startswith(old_prefix):
                filename = f"{t}-{nid}-" + filename[len(old_prefix):]
                break
        return f"{dirpart}/{filename}" if dirpart else filename

    for line in lines:
        line = line.strip()
        if not line:
            new_lines.append("")
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            new_lines.append(line)
            continue

        modified = False
        skill = obj.get("skill", "")
        old_id = str(obj.get("id", ""))

        # Map 'id' field using skill-aware type inference
        if skill == "check" and len(old_id) >= 6:
            art_type = "check"
        else:
            art_type = skill_to_type.get(skill, "advisory")
        new_id = _lookup_id(art_type, old_id)
        if new_id:
            obj["id"] = new_id
            modified = True

        # Map 'plan_id' field (always plan type)
        old_pid = obj.get("plan_id")
        if old_pid is not None:
            new_pid = _lookup_id("plan", str(old_pid))
            if new_pid:
                obj["plan_id"] = new_pid
                modified = True

        # Update output_file path (prefix only, not slug)
        output_file = obj.get("output_file", "")
        if output_file:
            new_output = _update_output_path(output_file)
            if new_output != output_file:
                obj["output_file"] = new_output
                modified = True

        if modified:
            changed = True
        new_lines.append(json.dumps(obj, ensure_ascii=False))

    if changed:
        if dry_run:
            print(f"  [dry-run] Would update telemetry.jsonl")
        else:
            telem_path.write_text("\n".join(new_lines), encoding="utf-8")
            if verbose:
                print(f"  Updated telemetry.jsonl")


def run_migration(dry_run: bool = False, verbose: bool = False) -> None:
    """Execute the full migration."""
    if not OUTPUT_DIR.is_dir():
        print(f"ERROR: Output directory not found: {OUTPUT_DIR}")
        sys.exit(1)

    # -----------------------------------------------------------------------
    # PASS 1: Scan and classify all artifacts
    # -----------------------------------------------------------------------
    print(f"Scanning {OUTPUT_DIR} for artifacts...")
    artifacts: list[Artifact] = []
    for fp in sorted(OUTPUT_DIR.rglob("*.md")):
        if not fp.is_file():
            continue
        art = classify_file(fp)
        if art:
            artifacts.append(art)
        elif verbose:
            rel = fp.relative_to(OUTPUT_DIR)
            print(f"  Skipped: {rel}")

    print(f"Found {len(artifacts)} artifacts "
          f"({sum(1 for a in artifacts if not a.is_derived and not a.is_progress)} primary, "
          f"{sum(1 for a in artifacts if a.is_derived)} derived, "
          f"{sum(1 for a in artifacts if a.is_progress)} progress)")

    # -----------------------------------------------------------------------
    # PASS 2: Build ID mapping
    # -----------------------------------------------------------------------
    print("\nBuilding ID mapping...")
    mapping = build_mapping(artifacts, verbose=verbose)

    # Print mapping table
    print(f"\n{'Old Type':12s} {'Old ID':>8s}  ->  {'New ID':>8s}")
    print("-" * 40)
    primaries = [a for a in artifacts if not a.is_derived and not a.is_progress]
    primaries.sort(key=lambda a: a.date if a.date else "9999-99-99")
    for art in primaries:
        print(f"{art.art_type:12s} {art.old_id:>8s}  ->  {art.new_id:>8s}")

    if dry_run:
        print(f"\n[dry-run] No changes made. Re-run without --dry-run to apply.")

        # Also show derived mappings
        derived = [a for a in artifacts if a.is_derived or a.is_progress]
        if derived:
            print(f"\nDerived/progress files ({len(derived)}):")
            for art in derived:
                new_name = _new_filename(art)
                print(f"  {art.filepath.name}  ->  {new_name}")

        update_briefs(mapping, dry_run=True, verbose=verbose)
        update_telemetry(mapping, dry_run=True, verbose=verbose)
        return

    # -----------------------------------------------------------------------
    # PASS 3: Apply changes
    # -----------------------------------------------------------------------
    print("\nApplying migration...")

    # 3a. Update file contents (headers + cross-references) BEFORE renaming
    for art in artifacts:
        text = art.filepath.read_text(encoding="utf-8", errors="replace")
        new_text = _update_header(text, art, mapping)
        new_text = _update_cross_references(new_text, mapping)
        if new_text != text:
            art.filepath.write_text(new_text, encoding="utf-8")
            if verbose:
                print(f"  Updated content: {art.filepath.name}")

    # 3b. Rename files (must happen after content updates since we use filepath)
    rename_count = 0
    for art in artifacts:
        new_name = _new_filename(art)
        if new_name != art.filepath.name:
            new_path = art.filepath.parent / new_name
            art.filepath.rename(new_path)
            art.filepath = new_path
            rename_count += 1
            if verbose:
                print(f"  Renamed: {art.filepath.parent.name}/{new_name}")

    print(f"Renamed {rename_count} files")

    # 3c. Update briefs.md
    update_briefs(mapping, dry_run=False, verbose=verbose)

    # 3d. Update telemetry.jsonl
    update_telemetry(mapping, dry_run=False, verbose=verbose)

    # 3e. Delete per-folder INDEX.md files
    for subdir in ["advisory-logs", "plans", "qa-logs", "check-logs"]:
        idx = OUTPUT_DIR / subdir / "INDEX.md"
        if idx.is_file():
            idx.unlink()
            print(f"Deleted {idx.relative_to(REPO_ROOT)}")

    # 3f. Regenerate global INDEX.md via generate_macro_index.py
    print("\nRegenerating INDEX.md...")
    script = REPO_ROOT / ".claude" / "skills" / "scripts" / "generate_macro_index.py"
    cmd = [sys.executable, str(script)]
    if verbose:
        cmd.append("--verbose")
    subprocess.run(cmd, cwd=str(REPO_ROOT), check=True)

    print("\nMigration complete.")


def main():
    parser = argparse.ArgumentParser(
        description="One-time migration from mixed 4/6-digit IDs to global 6-digit IDs"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print ID mapping without making changes",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show detailed output",
    )
    args = parser.parse_args()

    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

    run_migration(dry_run=args.dry_run, verbose=args.verbose)


if __name__ == "__main__":
    main()
