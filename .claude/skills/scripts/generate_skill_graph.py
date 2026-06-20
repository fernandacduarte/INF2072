#!/usr/bin/env python3
# designer: When the harness's lifecycle orchestration needs a machine-
#   readable view of which skill suggests which next -- the After / Suggest /
#   Reason triples that power post-skill's hand-off prompts -- I'm the parser
#   that reads `skill-graph.md` and writes `skill-graph.json` so lookups are
#   fast and the human-authored table stays the single source of truth.
"""
generate_skill_graph.py -- Generate skill-graph.json from skill-graph.md.

Invocation: user-cli
Lifecycle: active

Parses the Markdown table in .claude/references/general/skill-graph.md and produces
.claude/references/general/skill-graph.json with structured edge data for fast
programmatic lookup by /post-skill.

Usage
-----
    python .claude/skills/scripts/generate_skill_graph.py
    python .claude/skills/scripts/generate_skill_graph.py --check
    python .claude/skills/scripts/generate_skill_graph.py --verbose

Flags:
    --check    Compare existing JSON with what would be generated.
               Exit 0 if up-to-date, exit 1 if stale.
    --verbose  Show each edge being processed
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Repo root discovery (same pattern as generate_skills_manifest.py)
SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parents[2]
SOURCE_MD = REPO_ROOT / ".claude" / "references" / "general" / "skill-graph.md"
OUTPUT_JSON = REPO_ROOT / ".claude" / "references" / "general" / "skill-graph.json"

# Category slug mapping: section header -> slug
_CATEGORY_SLUGS = {
    "Planning & Execution": "planning-execution",
    "Analysis & Review": "analysis-review",
    "Code & Tests": "code-tests",
    "Utilities": "utilities",
}

# Match Markdown table rows (skip header and separator rows)
_TABLE_ROW_RE = re.compile(
    r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|$"
)


def slugify_category(header: str) -> str:
    """Convert a section header to a category slug."""
    slug = _CATEGORY_SLUGS.get(header)
    if slug:
        return slug
    # Fallback: lowercase, replace & with empty, collapse spaces to hyphens
    return re.sub(r"\s+", "-", header.lower().replace("&", "").strip()).strip("-")


def parse_skill_graph(verbose: bool = False) -> list[dict[str, str]]:
    """Parse skill-graph.md and return a flat list of edge dicts."""
    if not SOURCE_MD.is_file():
        print(f"ERROR: Source file not found: {SOURCE_MD}", file=sys.stderr)
        return []

    text = SOURCE_MD.read_text(encoding="utf-8")
    edges: list[dict[str, str]] = []
    current_category = ""
    in_relationships = False

    for line in text.splitlines():
        stripped = line.strip()

        # Detect ## Relationships section
        if stripped == "## Relationships":
            in_relationships = True
            continue

        # Detect end of Relationships section (next ## heading)
        if in_relationships and stripped.startswith("## ") and stripped != "## Relationships":
            in_relationships = False
            continue

        if not in_relationships:
            continue

        # Detect ### category headers
        if stripped.startswith("### "):
            header = stripped[4:].strip()
            current_category = slugify_category(header)
            if verbose:
                print(f"  category: {header} -> {current_category}")
            continue

        # Skip non-table lines, header rows, and separator rows
        if not stripped.startswith("|"):
            continue

        m = _TABLE_ROW_RE.match(stripped)
        if not m:
            continue

        after_val = m.group(1).strip().strip("`")
        suggest_val = m.group(2).strip()
        reason_val = m.group(3).strip()

        # Skip header rows
        if after_val.lower() == "after" or after_val.startswith("---"):
            continue

        # Comma-separated Suggest values become separate edges
        suggests = [s.strip().strip("`") for s in suggest_val.split(",")]

        for suggest in suggests:
            edge = {
                "after": after_val,
                "suggest": suggest,
                "reason": reason_val,
                "category": current_category,
            }
            edges.append(edge)
            if verbose:
                print(f"  edge: {after_val} -> {suggest}")

    return edges


def build_manifest(edges: list[dict[str, str]]) -> dict:
    """Build the full JSON structure from edges."""
    # Collect categories in order of first appearance
    seen: set[str] = set()
    categories: list[str] = []
    for edge in edges:
        cat = edge["category"]
        if cat not in seen:
            seen.add(cat)
            categories.append(cat)

    return {
        "version": "1.0",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "categories": categories,
        "edges": edges,
    }


def edges_match(existing_json: dict, new_edges: list[dict[str, str]]) -> bool:
    """Compare existing JSON edges with newly parsed edges (ignoring generated timestamp)."""
    existing_edges = existing_json.get("edges", [])
    if len(existing_edges) != len(new_edges):
        return False

    for old, new in zip(existing_edges, new_edges):
        if (old.get("after") != new["after"]
                or old.get("suggest") != new["suggest"]
                or old.get("reason") != new["reason"]
                or old.get("category") != new["category"]):
            return False

    # Also check categories list and version
    new_manifest = build_manifest(new_edges)
    if existing_json.get("version") != new_manifest["version"]:
        return False
    if existing_json.get("categories") != new_manifest["categories"]:
        return False

    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate skill-graph.json from skill-graph.md"
    )
    parser.add_argument("--check", action="store_true",
                        help="Exit non-zero if JSON is stale or missing")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show each edge being processed")
    args = parser.parse_args()

    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    edges = parse_skill_graph(verbose=args.verbose)
    if not edges:
        print("ERROR: No edges parsed from skill-graph.md", file=sys.stderr)
        return 1

    if args.check:
        if not OUTPUT_JSON.is_file():
            print(f"FAIL: {OUTPUT_JSON.relative_to(REPO_ROOT)} does not exist. "
                  "Run: python .claude/skills/scripts/generate_skill_graph.py")
            return 1

        existing = json.loads(OUTPUT_JSON.read_text(encoding="utf-8"))
        if edges_match(existing, edges):
            print(f"OK: {OUTPUT_JSON.relative_to(REPO_ROOT)} is up to date "
                  f"({len(edges)} edges).")
            return 0
        else:
            print(f"FAIL: {OUTPUT_JSON.relative_to(REPO_ROOT)} is stale. "
                  "Run: python .claude/skills/scripts/generate_skill_graph.py")
            return 1

    manifest = build_manifest(edges)

    OUTPUT_JSON.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Generated {OUTPUT_JSON.relative_to(REPO_ROOT)} "
          f"with {len(edges)} edges across {len(manifest['categories'])} categories.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
