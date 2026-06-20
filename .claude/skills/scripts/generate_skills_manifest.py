#!/usr/bin/env python3
# designer: When any tool in the harness needs to know which skills exist
#   without reading every SKILL.md, I'm the manifest builder that reads each
#   skill's frontmatter and writes a compact JSON file -- name, description,
#   argument-hint, category -- so skill discovery stays a single fast lookup
#   instead of a filesystem walk.
"""
generate_skills_manifest.py -- Generate L1 metadata manifest from SKILL.md files.

Invocation: script-invoked, user-cli
Lifecycle: active

Parses YAML frontmatter from all SKILL.md files under .claude/skills/,
extracts lightweight metadata (name, description, argument-hint, category),
and outputs a JSON manifest for fast skill scanning.

Follows the progressive disclosure pattern (ADK L1/L2/L3): the manifest
provides ~100 tokens per skill at L1, avoiding the need to parse individual
SKILL.md files for skill discovery.

Usage
-----
    python .claude/skills/scripts/generate_skills_manifest.py
    python .claude/skills/scripts/generate_skills_manifest.py --check
    python .claude/skills/scripts/generate_skills_manifest.py --verbose

Flags:
    --check    Exit non-zero if the manifest is stale (any SKILL.md newer)
    --verbose  Show each skill being processed
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Repo root discovery (same pattern as other scripts)
SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parents[2]
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"
MANIFEST_PATH = SKILLS_DIR / "skills-manifest.json"

# Internal lifecycle hooks -- excluded from the manifest
INTERNAL_SKILLS = {"pre-skill", "post-skill"}

# YAML frontmatter extraction (simple regex, avoids PyYAML dependency)
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
_FIELD_RE = re.compile(r"^(\w[\w-]*):\s*(.+)$", re.MULTILINE)
_NESTED_FIELD_RE = re.compile(r"^\s{2}(\w[\w-]*):\s*(.+)$", re.MULTILINE)


def parse_frontmatter(skill_md: Path) -> dict[str, str] | None:
    """Extract key-value pairs from YAML frontmatter of a SKILL.md file."""
    try:
        text = skill_md.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    match = _FRONTMATTER_RE.match(text)
    if not match:
        return None

    fm_text = match.group(1)
    fields: dict[str, str] = {}

    for m in _FIELD_RE.finditer(fm_text):
        key = m.group(1)
        value = m.group(2).strip().strip('"').strip("'")
        fields[key] = value

    # Parse nested metadata fields
    in_metadata = False
    for line in fm_text.splitlines():
        if line.strip() == "metadata:":
            in_metadata = True
            continue
        if in_metadata:
            nested = _NESTED_FIELD_RE.match(line)
            if nested:
                fields[f"metadata.{nested.group(1)}"] = (
                    nested.group(2).strip().strip('"').strip("'")
                )
            elif not line.startswith(" "):
                in_metadata = False

    return fields


def collect_skills(verbose: bool = False) -> list[dict[str, str]]:
    """Walk SKILLS_DIR and collect L1 metadata from each SKILL.md."""
    skills = []

    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue

        skill_name = skill_dir.name
        if skill_name in INTERNAL_SKILLS:
            if verbose:
                print(f"  skip (internal): {skill_name}")
            continue

        # Skip non-skill directories (scripts, etc.)
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            if verbose:
                print(f"  skip (no SKILL.md): {skill_name}")
            continue

        fields = parse_frontmatter(skill_md)
        if not fields:
            print(f"  WARNING: could not parse frontmatter: {skill_md}",
                  file=sys.stderr)
            continue

        entry = {
            "name": fields.get("name", skill_name),
            "description": fields.get("description", ""),
            "argument_hint": fields.get("argument-hint", ""),
            "category": fields.get("metadata.category", ""),
            "version": fields.get("metadata.version", ""),
        }
        skills.append(entry)
        if verbose:
            print(f"  added: {entry['name']}")

    return skills


def is_stale() -> bool:
    """Check if the manifest content differs from what would be generated now.

    Compares the `skills` list by value (ignoring the `generated` timestamp),
    so the check is deterministic across fresh checkouts where file mtimes
    reflect write order rather than commit time.
    """
    if not MANIFEST_PATH.is_file():
        return True

    try:
        current = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return True

    expected_skills = collect_skills()
    return current.get("skills") != expected_skills


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate L1 skills manifest from SKILL.md frontmatter"
    )
    parser.add_argument("--check", action="store_true",
                        help="Exit non-zero if manifest is stale")
    parser.add_argument("--verbose", action="store_true",
                        help="Show each skill being processed")
    args = parser.parse_args()

    if args.check:
        if is_stale():
            print("FAIL: skills-manifest.json is stale or missing. "
                  "Run: python .claude/skills/scripts/generate_skills_manifest.py")
            return 1
        print("OK: skills-manifest.json is up to date.")
        return 0

    if args.verbose:
        print("Scanning SKILL.md files...")

    skills = collect_skills(verbose=args.verbose)

    manifest = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(skills),
        "skills": skills,
    }

    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Generated {MANIFEST_PATH.relative_to(REPO_ROOT)} "
          f"with {len(skills)} skills.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
