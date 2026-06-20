#!/usr/bin/env python3
# designer: When you add or touch a skill, I check its SKILL.md frontmatter
#   against the agentskills.io universal spec -- name shape, description
#   length, metadata shape -- and tell you exactly which line the skill
#   viewer ecosystem would reject. This is the gate that keeps your skills
#   portable beyond SEJA.
"""
check_skill_spec.py — Validate SKILL.md files against the agentskills.io spec.

Invocation: agent-invoked, hook-ci
Lifecycle: active

Exit codes: 0 = pass, 1 = failures found, 2 = script error.

Checks performed
================
  1. name: required, 1-64 chars, lowercase alphanumeric + hyphens,
     no consecutive hyphens, no leading/trailing hyphens, must match parent dir
  2. description: required, 1-1024 chars, non-empty
  3. compatibility: optional, max 500 chars if present
  4. metadata: optional, must be a mapping if present

Usage
-----
    python .claude/skills/scripts/check_skill_spec.py
    python .claude/skills/scripts/check_skill_spec.py --verbose

CHECK_PLUGIN_MANIFEST:
  name: Skill Spec
  stack:
    backend: [any]
    frontend: [any]
  scope: harness
  critical: false
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"

# agentskills.io name rules
NAME_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")
CONSECUTIVE_HYPHENS_RE = re.compile(r"--")

# Simple YAML frontmatter parser (between --- delimiters)
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


def parse_frontmatter(text: str) -> dict:
    """Parse YAML-like frontmatter from a markdown file."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}

    result = {}
    current_key = None
    current_list = None
    in_metadata = False
    metadata = {}

    for line in match.group(1).split("\n"):
        stripped = line.strip()
        if not stripped:
            continue

        if not line.startswith(" ") and not line.startswith("\t"):
            if current_list is not None and current_key:
                if in_metadata:
                    metadata[current_key] = current_list
                else:
                    result[current_key] = current_list
                current_list = None
            in_metadata = False

            if ":" in stripped:
                key, _, value = stripped.partition(":")
                key = key.strip()
                value = value.strip().strip("\"'")
                if key == "metadata":
                    in_metadata = True
                    current_key = None
                else:
                    result[key] = value if value else ""
                    current_key = key
            continue

        if in_metadata:
            if stripped.startswith("- "):
                if current_list is None:
                    current_list = []
                current_list.append(stripped[2:].strip())
            elif ":" in stripped:
                if current_list is not None and current_key:
                    metadata[current_key] = current_list
                    current_list = None
                key, _, value = stripped.partition(":")
                key = key.strip()
                value = value.strip().strip("\"'")
                current_key = key
                if value:
                    if value == "[]":
                        metadata[key] = []
                    else:
                        metadata[key] = value
        elif stripped.startswith("- "):
            if current_list is None:
                current_list = []
            current_list.append(stripped[2:].strip())

    if current_list is not None and current_key:
        if in_metadata:
            metadata[current_key] = current_list
        else:
            result[current_key] = current_list

    if metadata:
        result["metadata"] = metadata

    return result


def validate_name(name: str, dir_name: str) -> list[str]:
    """Validate the name field against agentskills.io rules."""
    errors = []
    if not name:
        errors.append("missing 'name' field")
        return errors
    if len(name) > 64:
        errors.append(f"name exceeds 64 chars ({len(name)})")
    if not NAME_RE.match(name):
        errors.append(f"name '{name}' does not match pattern [a-z0-9]([a-z0-9-]*[a-z0-9])?")
    if CONSECUTIVE_HYPHENS_RE.search(name):
        errors.append(f"name '{name}' contains consecutive hyphens")
    if name != dir_name:
        errors.append(f"name '{name}' does not match parent directory '{dir_name}'")
    return errors


def validate_description(desc: str) -> list[str]:
    """Validate the description field."""
    errors = []
    if not desc:
        errors.append("missing 'description' field")
        return errors
    if len(desc) > 1024:
        errors.append(f"description exceeds 1024 chars ({len(desc)})")
    return errors


def validate_compatibility(compat: str | None) -> list[str]:
    """Validate the optional compatibility field."""
    if compat is None:
        return []
    if len(compat) > 500:
        return [f"compatibility exceeds 500 chars ({len(compat)})"]
    return []


def validate_metadata(metadata) -> list[str]:
    """Validate the optional metadata field."""
    if metadata is None:
        return []
    if not isinstance(metadata, dict):
        return [f"metadata must be a mapping, got {type(metadata).__name__}"]
    return []


def check_all(verbose: bool = False) -> tuple[list[str], int]:
    """Check all SKILL.md files. Returns (errors, total_count)."""
    all_errors = []

    skill_dirs = sorted(
        d for d in SKILLS_DIR.iterdir()
        if d.is_dir() and (d / "SKILL.md").exists()
    )

    for skill_dir in skill_dirs:
        skill_file = skill_dir / "SKILL.md"
        text = skill_file.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        dir_name = skill_dir.name
        skill_errors = []

        # Validate name
        skill_errors.extend(validate_name(fm.get("name", ""), dir_name))

        # Validate description
        skill_errors.extend(validate_description(fm.get("description", "")))

        # Validate compatibility (optional)
        skill_errors.extend(validate_compatibility(fm.get("compatibility")))

        # Validate metadata (optional)
        skill_errors.extend(validate_metadata(fm.get("metadata")))

        if skill_errors:
            for err in skill_errors:
                all_errors.append(f"  - {dir_name}/SKILL.md: {err}")
        elif verbose:
            print(f"  OK: {dir_name}")

    return all_errors, len(skill_dirs)


def main():
    parser = argparse.ArgumentParser(
        description="Validate SKILL.md files against the agentskills.io specification"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show details for passing checks too"
    )
    args = parser.parse_args()

    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if not SKILLS_DIR.is_dir():
        print("ERROR: .claude/skills directory not found")
        sys.exit(2)

    print("# agentskills.io Spec Validation\n")

    errors, total = check_all(verbose=args.verbose)

    if errors:
        print(f"## Violations ({len(errors)})\n")
        for msg in errors:
            print(msg)
        print()
        print(f"FAIL: {len(errors)} violation(s) in {total} skills")
        sys.exit(1)
    else:
        print(f"PASS: All {total} skills comply with agentskills.io spec")


if __name__ == "__main__":
    main()
