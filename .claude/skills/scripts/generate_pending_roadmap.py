#!/usr/bin/env python3
# designer: When you have multiple open plans piling up in the pending ledger,
#   I'm the script that reads them all, figures out which ones touch the same
#   files, and generates a lightweight roadmap that groups independent plans
#   into parallel waves and overlapping ones into sequential waves -- so
#   /implement --pending can hand off to the existing roadmap pathway.
"""
generate_pending_roadmap.py -- Generate a roadmap from pending implement entries.

Invocation: skill-invoked
Lifecycle: active

Queries the pending ledger for open implement entries, reads each plan's
Files: metadata, computes file overlaps between plans, assigns plans to
waves (non-overlapping plans can run in parallel, overlapping ones are
sequenced), and writes a roadmap file in the standard format.

Usage
-----
    python .claude/skills/scripts/generate_pending_roadmap.py --roadmap-id 000999
    python .claude/skills/scripts/generate_pending_roadmap.py --roadmap-id 000999 --output-dir /custom/path
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from project_config import REPO_ROOT, get_path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PLAN_ID_RE = re.compile(r"plan-(\d{6})")
_BACKTICK_PATH_RE = re.compile(r"`([^`]+)`")
# A plausible file path: starts with a dot or letter, contains a slash or
# extension, no spaces (angle-bracket placeholders are excluded).
_PLAUSIBLE_PATH_RE = re.compile(
    r"^[a-zA-Z._][\w./\\-]*\.[a-zA-Z0-9]+$"
)
_PLAN_HEADER_RE = re.compile(
    r"^#\s+(?:DONE\s*\|[^|]*\|\s*)?Plan\s+\d{6}\s*\|\s*([^|]*?)\s*\|[^|]*\|\s*(.+?)\s*\|"
)
_PLAN_HEADER_FALLBACK_RE = re.compile(
    r"^#\s+(?:DONE\s*\|[^|]*\|\s*)?Plan\s+\d{6}\s*\|\s*([^|]*?)\s*\|[^|]*\|\s*(.+?)\s*$"
)
_SCOPE_MAP = {
    "-B": "backend", "-F": "frontend", "-X": "cross-cutting", "-O": "other",
}


# ---------------------------------------------------------------------------
# Pending ledger query
# ---------------------------------------------------------------------------


def _query_pending_implements() -> list[dict]:
    """Run pending.py to get open implement entries."""
    scripts_dir = Path(__file__).resolve().parent
    pending_script = scripts_dir / "pending.py"
    result = subprocess.run(
        [
            sys.executable,
            str(pending_script),
            "list",
            "--type", "implement",
            "--status", "pending",
            "--json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        print(
            f"ERROR: pending.py exited with code {result.returncode}: "
            f"{result.stderr.strip()}",
            file=sys.stderr,
        )
        return []
    stdout = result.stdout.strip()
    if not stdout:
        return []
    return json.loads(stdout)


# ---------------------------------------------------------------------------
# Plan file parsing
# ---------------------------------------------------------------------------


def _find_plan_file(plans_dir: Path, plan_id: str) -> Path | None:
    """Find the main plan file for a given 6-digit plan ID."""
    prefix = f"plan-{plan_id}-"
    for p in plans_dir.glob(f"{prefix}*.md"):
        name = p.name
        # Skip progress, QA, and QA-log siblings
        if name.endswith("-progress.md"):
            continue
        rest = name[len(prefix):-3]
        if rest.startswith("qa-") or rest.startswith("qa-log-"):
            continue
        return p
    return None


def _parse_plan_header(text: str) -> tuple[str, str]:
    """Extract the title and scope from the plan's first-line header.

    Returns (title, scope) where scope is one of: backend, frontend,
    cross-cutting, other.
    """
    first_line = text.split("\n", 1)[0]
    m = _PLAN_HEADER_RE.match(first_line)
    if m:
        prefix_scope = m.group(1).strip()
        title = m.group(2).strip().rstrip("|").strip()
        scope_suffix = prefix_scope.rsplit("-", 1)[-1] if "-" in prefix_scope else ""
        scope = _SCOPE_MAP.get(f"-{scope_suffix}", "other")
        return title, scope
    m = _PLAN_HEADER_FALLBACK_RE.match(first_line)
    if m:
        prefix_scope = m.group(1).strip()
        title = m.group(2).strip()
        scope_suffix = prefix_scope.rsplit("-", 1)[-1] if "-" in prefix_scope else ""
        scope = _SCOPE_MAP.get(f"-{scope_suffix}", "other")
        return title, scope
    return "(untitled)", "other"


def _is_plausible_path(s: str) -> bool:
    """Return True if the string looks like a file path (not a CLI flag, code, etc.)."""
    if not s:
        return False
    # Reject CLI flags, angle-bracket placeholders, parenthesised annotations
    if s.startswith("-") or s.startswith("(") or "<" in s:
        return False
    # Reject strings with spaces (commands, function signatures)
    if " " in s:
        return False
    return bool(_PLAUSIBLE_PATH_RE.match(s))


def _parse_files_metadata(text: str) -> set[str]:
    """Extract all file paths from Files: metadata in a plan.

    Parses two forms:
    1. Top-level ## Files section with lines like:
       - `.claude/skills/implement/SKILL.md` (modify)
    2. Step-level **Files**: lines like:
       - **Files**: `.claude/skills/scripts/foo.py` (create), `.claude/skills/scripts/bar.py` (read)
    """
    files: set[str] = set()

    in_files_section = False
    in_code_block = False
    for line in text.splitlines():
        stripped = line.strip()

        # Track fenced code blocks to avoid parsing their contents
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        # Detect top-level ## Files section (exact match, not "## Files to Add")
        if re.match(r"^## Files\s*$", stripped):
            in_files_section = True
            continue

        # End of ## Files section at next H2
        if in_files_section and stripped.startswith("## "):
            in_files_section = False
            continue

        # Parse lines within ## Files section
        if in_files_section and stripped.startswith("- "):
            for m in _BACKTICK_PATH_RE.finditer(stripped):
                path = m.group(1).strip()
                if _is_plausible_path(path):
                    files.add(path)
            continue

        # Parse step-level **Files**: lines
        if "**Files**:" in stripped:
            # Everything after **Files**:
            after = stripped.split("**Files**:", 1)[1]
            for m in _BACKTICK_PATH_RE.finditer(after):
                path = m.group(1).strip()
                if _is_plausible_path(path):
                    files.add(path)

    return files


# ---------------------------------------------------------------------------
# Wave assignment
# ---------------------------------------------------------------------------


def _compute_overlaps(
    plan_files: dict[str, set[str]],
) -> dict[str, set[str]]:
    """Build an overlap graph: plan_id -> set of plan_ids it overlaps with."""
    plan_ids = list(plan_files.keys())
    overlaps: dict[str, set[str]] = {pid: set() for pid in plan_ids}
    for i, pid_a in enumerate(plan_ids):
        for pid_b in plan_ids[i + 1:]:
            if plan_files[pid_a] & plan_files[pid_b]:
                overlaps[pid_a].add(pid_b)
                overlaps[pid_b].add(pid_a)
    return overlaps


def _assign_waves(
    plan_ids: list[str],
    overlaps: dict[str, set[str]],
) -> list[list[str]]:
    """Assign plans to waves using greedy non-overlap grouping.

    Wave 0 gets the first set of non-overlapping plans.
    Remaining plans go to Wave 1+, grouped by non-overlap within each wave.
    """
    remaining = set(plan_ids)
    waves: list[list[str]] = []

    while remaining:
        wave: list[str] = []
        plans_in_wave: set[str] = set()

        # Greedy: iterate in original order for determinism
        for pid in plan_ids:
            if pid not in remaining:
                continue
            # Check if pid overlaps with any plan already in this wave
            if overlaps[pid] & plans_in_wave:
                continue
            wave.append(pid)
            plans_in_wave.add(pid)

        for pid in wave:
            remaining.discard(pid)

        if wave:
            waves.append(wave)
        else:
            # Safety: if no progress, dump remaining into one wave
            waves.append(sorted(remaining))
            break

    return waves


# ---------------------------------------------------------------------------
# Roadmap generation
# ---------------------------------------------------------------------------


def _utcnow_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _generate_roadmap(
    roadmap_id: str,
    waves: list[list[str]],
    plan_titles: dict[str, str],
    plan_scopes: dict[str, str],
    wave_depends: dict[str, list[str]],
) -> str:
    """Generate the roadmap markdown content."""
    lines: list[str] = []
    now = _utcnow_str()

    lines.append(f"# Roadmap {roadmap_id} | {now} | Pending plans auto-roadmap")
    lines.append("")
    lines.append("## Source")
    lines.append("- pending.jsonl (read)")
    for wave in waves:
        for pid in wave:
            lines.append(f"- plan-{pid}-*.md (read)")
    lines.append("")
    lines.append("## Wave Summary")

    global_counter = 0
    pending_plan_ids: dict[str, str] = {}  # plan_id -> pending-plan-N label

    for wave_idx, wave in enumerate(waves):
        wave_label = "Sequential" if wave_idx == 0 else "Parallel"
        lines.append("")
        lines.append(f"### Wave {wave_idx} -- {wave_label}")
        lines.append(
            "| # | ID | Title | Scope | Type | Plan | Depends on | Status |"
        )
        lines.append(
            "|---|-----|-------|-------|------|------|-----------|--------|"
        )

        for pid in wave:
            global_counter += 1
            pp_label = f"pending-plan-{global_counter}"
            pending_plan_ids[pid] = pp_label
            title = plan_titles.get(pid, "(untitled)")
            scope = plan_scopes.get(pid, "other")

            deps = wave_depends.get(pid, [])
            dep_labels = [
                pending_plan_ids[d] for d in deps if d in pending_plan_ids
            ]
            dep_str = ", ".join(dep_labels) if dep_labels else "none"
            lines.append(
                f"| {global_counter} | {pp_label} | {title} "
                f"| {scope} | technical | plan-{pid} | {dep_str} | pending |"
            )

    lines.append("")
    lines.append("## Execution Instructions")

    for wave_idx, wave in enumerate(waves):
        lines.append("")
        if wave_idx == 0:
            lines.append(f"### Wave {wave_idx} (sequential)")
            lines.append("Execute these plans one at a time, in order:")
            for i, pid in enumerate(wave, 1):
                pp_label = pending_plan_ids[pid]
                title = plan_titles.get(pid, "(untitled)")
                lines.append(f"{i}. /implement {pid} ({pp_label})")
        else:
            count = len(wave)
            lines.append(
                f"### Wave {wave_idx} (parallel -- {count} plan"
                f"{'s' if count != 1 else ''})"
            )
            lines.append(
                f"Depends on Wave {wave_idx - 1}. Execute after "
                f"Wave {wave_idx - 1} completes."
            )
            if count > 1:
                lines.append("Execute in parallel via:")
                lines.append("- Multiple Claude Code sessions, or")
                lines.append(
                    "- Worktree-isolated agents from a single session"
                )
            for pid in wave:
                pp_label = pending_plan_ids[pid]
                lines.append(f"- /implement {pid} ({pp_label})")

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a roadmap from pending implement entries.",
    )
    parser.add_argument(
        "--roadmap-id",
        required=True,
        help="6-digit roadmap ID (pre-reserved via reserve_id.py)",
    )
    parser.add_argument(
        "--output-dir",
        help="Output directory (defaults to ROADMAP_DIR from project_config)",
    )
    args = parser.parse_args()

    roadmap_id = args.roadmap_id

    # Resolve output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = get_path("ROADMAP_DIR") or REPO_ROOT / "_output" / "roadmaps"

    # Query pending implement entries
    entries = _query_pending_implements()
    if not entries:
        print("No pending implement entries found.", file=sys.stderr)
        return 1

    # Resolve plans directory
    plans_dir = get_path("PLANS_DIR") or REPO_ROOT / "_output" / "plans"

    # Extract plan info
    plan_titles: dict[str, str] = {}
    plan_scopes: dict[str, str] = {}
    plan_files_map: dict[str, set[str]] = {}
    plan_order: list[str] = []  # preserve order from pending ledger

    for entry in entries:
        source = entry.get("source", "")
        m = _PLAN_ID_RE.search(source)
        if not m:
            print(
                f"WARNING: cannot extract plan ID from source '{source}', "
                f"skipping entry {entry.get('id', '?')}",
                file=sys.stderr,
            )
            continue
        plan_id = m.group(1)

        if plan_id in plan_files_map:
            continue

        plan_file = _find_plan_file(plans_dir, plan_id)
        if plan_file is None:
            print(
                f"WARNING: plan file not found for plan-{plan_id}, "
                f"skipping entry {entry.get('id', '?')}",
                file=sys.stderr,
            )
            continue

        text = plan_file.read_text(encoding="utf-8")
        title, scope = _parse_plan_header(text)
        files = _parse_files_metadata(text)

        plan_titles[plan_id] = title
        plan_scopes[plan_id] = scope
        plan_files_map[plan_id] = files
        plan_order.append(plan_id)

    if not plan_order:
        print(
            "No valid plan files found for pending entries.",
            file=sys.stderr,
        )
        return 1

    # Compute overlaps and assign waves
    overlaps = _compute_overlaps(plan_files_map)
    waves = _assign_waves(plan_order, overlaps)

    # Compute per-plan dependencies for non-Wave-0 plans
    wave_depends: dict[str, list[str]] = {}
    earlier_plans: set[str] = set()
    for wave_idx, wave in enumerate(waves):
        if wave_idx > 0:
            for pid in wave:
                deps = [
                    d for d in earlier_plans
                    if d in overlaps.get(pid, set())
                ]
                wave_depends[pid] = deps
        earlier_plans.update(wave)

    # Generate roadmap content
    content = _generate_roadmap(
        roadmap_id=roadmap_id,
        waves=waves,
        plan_titles=plan_titles,
        plan_scopes=plan_scopes,
        wave_depends=wave_depends,
    )

    # Write roadmap file
    output_dir.mkdir(parents=True, exist_ok=True)
    roadmap_file = output_dir / f"roadmap-{roadmap_id}-pending-plans.md"
    roadmap_file.write_text(content, encoding="utf-8", newline="\n")

    # Print the path to stdout (for callers to capture)
    print(str(roadmap_file))
    return 0


if __name__ == "__main__":
    sys.exit(main())
