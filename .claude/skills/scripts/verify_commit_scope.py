#!/usr/bin/env python3
# designer: When a post-skill commit is about to land, I check the staged
#   files against the files a given skill invocation is expected to touch.
#   I report what's expected, what's staged, what's unexpected, and what's
#   missing -- so the agent can decide whether the commit scope is right
#   before anything is recorded in git history.
"""
verify_commit_scope.py -- Check staged git files against expected post-skill patterns.

Invocation: agent-invoked
Lifecycle: active

Runs `git diff --cached --name-only` to get staged files and compares them
against the expected file set for a given skill type and artifact ID. Expected
files come from three sources:
  (a) the plan's ## Files section if --plan-id is given
  (b) the skill output directory resolved from conventions.md
  (c) the --always-include list

Files under _loom/ and .claude/ are always allowed (never unexpected).

Outputs JSON to stdout:
  {"expected": [...], "staged": [...], "unexpected": [...], "missing": [...], "pass": true|false}

Exit codes: 0 = pass (no unexpected files), 1 = unexpected files found, 2 = script error.

Usage
-----
    python .claude/skills/scripts/verify_commit_scope.py \\
        --skill-type research --artifact-id 000545 \\
        [--plan-id 000546] [--always-include briefs.md,INDEX.md] \\
        [--roadmap-id NNN] [--qa-log path/to/qa.md]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# project_config import
# ---------------------------------------------------------------------------

sys.path.insert(0, str(Path(__file__).resolve().parent))
from project_config import REPO_ROOT, get, get_path

# ---------------------------------------------------------------------------
# Skill-type -> conventions.md output directory variable
# ---------------------------------------------------------------------------

_SKILL_DIR_VARS: dict[str, str] = {
    "research": "RESEARCH_DIR",
    "advisory": "RESEARCH_DIR",   # legacy alias
    "plan": "PLANS_DIR",
    "implement": "PLANS_DIR",
    "check": "CHECK_LOGS_DIR",
    "document": "CHECK_LOGS_DIR",
    "explain": "EXPLAINED_BEHAVIORS_DIR",
    "communicate": "COMMUNICATION_DIR",
    "reflect": "REFLECTIONS_DIR",
    "onboard": "ONBOARDING_PLANS_DIR",
    "roadmap": "ROADMAP_DIR",
    "qa-log": "QA_LOGS_DIR",
}

# Prefixes git returns; always allowed (never unexpected)
_ALWAYS_ALLOWED_PREFIXES = ("_loom/", ".claude/")

# Regex for plan ## Files section: lines like `- \`path/to/file\` (action)`
_FILES_LINE_RE = re.compile(r"^-\s*`([^`]+)`", re.MULTILINE)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize(path: str) -> str:
    """Normalize a path to forward-slash form for cross-platform comparison."""
    return Path(path).as_posix()


def _get_staged_files() -> list[str]:
    """Return list of staged files (git diff --cached --name-only)."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(REPO_ROOT),
    )
    if result.returncode != 0:
        print(f"ERROR: git diff --cached failed: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(2)
    return [_normalize(line) for line in result.stdout.splitlines() if line.strip()]


def _parse_plan_files(plan_id: str) -> list[str]:
    """Parse the ## Files section from a plan file and return expected paths."""
    plans_dir = get_path("PLANS_DIR")
    if plans_dir is None:
        print("WARNING: PLANS_DIR not resolved; skipping plan file parsing", file=sys.stderr)
        return []

    # Find any plan file matching plan-<id>-*.md (skip progress and qa files)
    pattern = f"plan-{plan_id}-*.md"
    candidates = [
        p for p in plans_dir.glob(pattern)
        if "-progress" not in p.name and "-qa-" not in p.name
    ]
    if not candidates:
        print(f"WARNING: No plan file found for plan-{plan_id} in {plans_dir}", file=sys.stderr)
        return []

    plan_file = sorted(candidates)[0]
    text = plan_file.read_text(encoding="utf-8")

    # Find ## Files section
    files_section_match = re.search(r"^## Files\b", text, re.MULTILINE)
    if not files_section_match:
        return []

    # Extract content from ## Files until the next ## section
    section_start = files_section_match.end()
    next_section = re.search(r"^## ", text[section_start:], re.MULTILINE)
    section_text = text[section_start: section_start + next_section.start()] if next_section else text[section_start:]

    return [_normalize(m.group(1)) for m in _FILES_LINE_RE.finditer(section_text)]


def _resolve_skill_output_dir(skill_type: str, artifact_id: str) -> list[str]:
    """Resolve the expected output file pattern for a skill type + artifact ID."""
    var = _SKILL_DIR_VARS.get(skill_type.lower())
    if not var:
        return []
    output_dir = get_path(var)
    if output_dir is None:
        return []
    # Return the directory prefix so any file under it counts as expected
    rel = output_dir.relative_to(REPO_ROOT)
    return [_normalize(str(rel)) + "/"]


def _is_always_allowed(path: str) -> bool:
    """Return True if path is under _loom/ or .claude/."""
    return any(path.startswith(prefix) for prefix in _ALWAYS_ALLOWED_PREFIXES)


def _paths_match(staged: str, expected: str) -> bool:
    """Check if staged path satisfies expected (exact match or directory prefix)."""
    if expected.endswith("/"):
        return staged.startswith(expected)
    return staged == expected


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def build_expected(
    skill_type: str,
    artifact_id: str,
    plan_id: str | None,
    always_include: list[str],
    roadmap_id: str | None,
    qa_log: str | None,
) -> list[str]:
    """Collect all expected file paths/prefixes from all sources."""
    expected: list[str] = []

    # (a) Plan Files section
    if plan_id:
        expected.extend(_parse_plan_files(plan_id))

    # (b) Skill output directory prefix
    expected.extend(_resolve_skill_output_dir(skill_type, artifact_id))

    # Roadmap directory if --roadmap-id given
    if roadmap_id:
        roadmap_dir = get_path("ROADMAP_DIR")
        if roadmap_dir is not None:
            rel = roadmap_dir.relative_to(REPO_ROOT)
            expected.append(_normalize(str(rel)) + "/")

    # (c) Always-include list
    for p in always_include:
        norm = _normalize(p.strip())
        if norm:
            expected.append(norm)

    # QA log if provided
    if qa_log:
        expected.append(_normalize(qa_log))

    return expected


def check_scope(staged: list[str], expected: list[str]) -> dict:
    """Compare staged vs expected. Return result dict."""
    unexpected: list[str] = []
    matched: set[str] = set()

    for s in staged:
        if _is_always_allowed(s):
            continue  # always OK, not flagged
        if any(_paths_match(s, e) for e in expected):
            matched.add(s)
        else:
            unexpected.append(s)

    # Missing: expected exact paths not present in staged (skip directory prefixes)
    missing: list[str] = [
        e for e in expected
        if not e.endswith("/") and e not in staged
    ]

    return {
        "expected": expected,
        "staged": staged,
        "unexpected": unexpected,
        "missing": missing,
        "pass": len(unexpected) == 0,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="verify_commit_scope.py",
        description=(
            "Check staged git files against expected patterns for a post-skill commit. "
            "Outputs JSON to stdout. Exit 0 when pass=true, exit 1 when unexpected files found."
        ),
    )
    parser.add_argument(
        "--skill-type",
        required=True,
        metavar="NAME",
        help="Skill type: research, plan, implement, check, etc.",
    )
    parser.add_argument(
        "--artifact-id",
        required=True,
        metavar="NNN",
        help="Zero-padded 6-digit artifact ID (e.g. 000545).",
    )
    parser.add_argument(
        "--plan-id",
        default=None,
        metavar="NNN",
        help="Plan ID -- reads the plan's ## Files section for expected paths.",
    )
    parser.add_argument(
        "--always-include",
        default="",
        metavar="PATH,PATH,...",
        help="Comma-separated paths that are always expected (e.g. briefs.md,INDEX.md).",
    )
    parser.add_argument(
        "--roadmap-id",
        default=None,
        metavar="NNN",
        help="Roadmap ID -- adds the roadmap output directory to expected paths.",
    )
    parser.add_argument(
        "--qa-log",
        default=None,
        metavar="PATH",
        help="Path to the QA log file for this invocation (added to expected).",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    always_include = [p for p in args.always_include.split(",") if p.strip()]

    expected = build_expected(
        skill_type=args.skill_type,
        artifact_id=args.artifact_id,
        plan_id=args.plan_id,
        always_include=always_include,
        roadmap_id=args.roadmap_id,
        qa_log=args.qa_log,
    )

    staged = _get_staged_files()
    result = check_scope(staged, expected)

    print(json.dumps(result, indent=2))

    sys.exit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
