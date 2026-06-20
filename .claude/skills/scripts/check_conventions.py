#!/usr/bin/env python3
# designer: When a skill or reference file mentions a convention
#   variable like your backend directory or test layout, I make sure
#   you have actually defined that variable in your project
#   conventions. You find out about a missing or mistyped setting
#   before a skill tries to use it and fails.
"""
check_conventions.py — Validate conventions variables against skill and reference files.

Invocation: agent-invoked, hook-ci
Lifecycle: active

Checks that every ${VARIABLE_NAME} reference used in SKILL.md and .claude/references/**/*.md
files is defined in project/conventions.md (or template/conventions.md as fallback).

Exit codes: 0 = pass (all referenced variables are defined), 1 = errors found.

Usage
-----
    python .claude/skills/scripts/check_conventions.py
    python .claude/skills/scripts/check_conventions.py --verbose

CHECK_PLUGIN_MANIFEST:
  name: Conventions
  stack:
    backend: [any]
    frontend: [any]
  scope: conventions
  critical: false
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Import from sibling module
sys.path.insert(0, str(Path(__file__).resolve().parent))
from project_config import REPO_ROOT

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

CLAUDE_DIR = REPO_ROOT / ".claude"
SKILLS_DIR = CLAUDE_DIR / "skills"
REFERENCES_DIR = REPO_ROOT / ".claude" / "references"

_CONVENTIONS_REL = REPO_ROOT / "product-design" / "conventions.md"
_TEMPLATE_REL = REFERENCES_DIR / "template" / "conventions.md"

# Regex to extract variable definitions from markdown table rows:
#   | `VAR_NAME` | `value` | description |
_DEF_RE = re.compile(r"^\|\s*`([A-Z][A-Z0-9_]*)`\s*\|", re.MULTILINE)

# Regex to find ${VARIABLE_NAME} references in file content
_REF_RE = re.compile(r"\$\{([A-Z][A-Z0-9_]*)\}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def find_conventions_file() -> Path | None:
    """Locate the conventions file, preferring project/ over template/."""
    if _CONVENTIONS_REL.is_file():
        return _CONVENTIONS_REL
    if _TEMPLATE_REL.is_file():
        print(
            "INFO: project/conventions.md not found; using template/conventions.md as fallback",
            file=sys.stderr,
        )
        return _TEMPLATE_REL
    return None


def extract_defined_variables(conventions_path: Path) -> set[str]:
    """Parse the conventions file and return all defined variable names."""
    text = conventions_path.read_text(encoding="utf-8", errors="replace")
    return set(_DEF_RE.findall(text))


def scan_references(file_path: Path) -> dict[str, list[int]]:
    """Scan a file for ${VAR} references. Returns {var_name: [line_numbers]}."""
    refs: dict[str, list[int]] = {}
    text = file_path.read_text(encoding="utf-8", errors="replace")
    for i, line in enumerate(text.splitlines(), start=1):
        for match in _REF_RE.finditer(line):
            var_name = match.group(1)
            refs.setdefault(var_name, []).append(i)
    return refs


def collect_scan_files() -> list[Path]:
    """Collect all files to scan for variable references."""
    files: list[Path] = []

    # SKILL.md files
    if SKILLS_DIR.is_dir():
        for skill_dir in sorted(SKILLS_DIR.iterdir()):
            if skill_dir.is_dir():
                skill_file = skill_dir / "SKILL.md"
                if skill_file.is_file():
                    files.append(skill_file)

    # .claude/references/**/*.md files
    if REFERENCES_DIR.is_dir():
        for md_file in sorted(REFERENCES_DIR.glob("**/*.md")):
            files.append(md_file)

    return files


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate conventions variables against skill and reference files"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show per-file reference details"
    )
    args = parser.parse_args()

    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("# Conventions Variable Check\n")

    # Locate conventions file
    conventions_path = find_conventions_file()
    if conventions_path is None:
        print("ERROR: neither project/conventions.md nor template/conventions.md found")
        sys.exit(1)

    conventions_name = conventions_path.name
    print(f"Source: {conventions_name}\n")

    # Extract defined variables
    defined_vars = extract_defined_variables(conventions_path)
    print(f"Defined variables: {len(defined_vars)}\n")

    # Scan all target files for references
    scan_files = collect_scan_files()
    print(f"Files scanned: {len(scan_files)}\n")

    # Collect all references: {var_name: [(file_path, line_numbers), ...]}
    all_refs: dict[str, list[tuple[Path, list[int]]]] = {}

    for file_path in scan_files:
        # Skip the conventions file itself — self-references are expected
        if file_path.resolve() == conventions_path.resolve():
            continue

        refs = scan_references(file_path)
        if refs:
            if args.verbose:
                rel = file_path.relative_to(REPO_ROOT)
                print(f"  {rel}: {', '.join(sorted(refs.keys()))}")
            for var_name, lines in refs.items():
                all_refs.setdefault(var_name, []).append((file_path, lines))

    if args.verbose:
        print()

    # Compute sets
    referenced_vars = set(all_refs.keys())
    undefined_refs = referenced_vars - defined_vars
    unreferenced_defs = defined_vars - referenced_vars

    errors: list[str] = []
    warnings: list[str] = []

    # Errors: referenced but not defined
    for var in sorted(undefined_refs):
        locations = all_refs[var]
        loc_strs = []
        for file_path, lines in locations:
            rel = file_path.relative_to(REPO_ROOT)
            loc_strs.append(f"{rel} (lines {', '.join(str(l) for l in lines)})")
        errors.append(f"  ERROR: ${{{var}}} referenced but not defined in {conventions_name}")
        for loc in loc_strs:
            errors.append(f"         -> {loc}")

    # Warnings: defined but never referenced
    for var in sorted(unreferenced_defs):
        warnings.append(f"  WARNING: `{var}` defined in {conventions_name} but never referenced")

    # Report
    print("---\n")
    print("## Summary\n")
    print(f"  Defined variables:    {len(defined_vars)}")
    print(f"  Referenced variables:  {len(referenced_vars)}")
    print(f"  Errors (undefined):   {len(undefined_refs)}")
    print(f"  Warnings (unused):    {len(unreferenced_defs)}")
    print()

    if errors:
        print("## Errors\n")
        for msg in errors:
            print(msg)
        print()

    if warnings:
        print("## Warnings\n")
        for msg in warnings:
            print(msg)
        print()

    if not errors and not warnings:
        print("PASS: All referenced variables are defined; no unused definitions.")
    elif errors:
        print(f"FAIL: {len(undefined_refs)} undefined variable(s) referenced")
        sys.exit(1)
    else:
        print(f"WARN: {len(unreferenced_defs)} unused definition(s), 0 errors")


if __name__ == "__main__":
    main()
