#!/usr/bin/env python3
# designer: Before you deploy a database change, I walk your
#   migration history end to end and call out anything that would
#   block the deploy: two branches competing for head, an orphan
#   revision, a cycle. You see the shape of the chain and the
#   problems in one place instead of finding them at boot time.
"""
check_migration_chain.py — Validate Alembic migration revision chain in dialogos.

Invocation: agent-invoked, hook-ci
Lifecycle: active

Checks performed
================
  1. Parse all migration files for revision / down_revision
  2. Build the revision DAG and detect:
     - Multiple heads (unmerged branches)
     - Orphan revisions (down_revision pointing to non-existent revision)
     - Cycles in the revision graph
  3. Optionally check for idempotency patterns in create_table / add_column

Usage
-----
    python .claude/skills/scripts/check_migration_chain.py

Run from the repository root (dialogos/).
Optional flags:
    --verbose           Show the full revision chain
    --check-idempotency Warn about create_table/add_column without guards

CHECK_PLUGIN_MANIFEST:
  name: Migration Chain
  stack:
    backend: [flask]
    frontend: []
  scope: database
  critical: true
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from project_config import REPO_ROOT, get_path

VERSIONS_DIR = get_path("MIGRATIONS_DIR") or REPO_ROOT / "backend" / "migrations" / "versions"

# Regex to match revision = '...' and down_revision = '...'
_REVISION_RE = re.compile(r"^revision\s*=\s*['\"]([^'\"]+)['\"]", re.MULTILINE)
_DOWN_REV_RE = re.compile(r"^down_revision\s*=\s*['\"]([^'\"]*)['\"]", re.MULTILINE)
_DOWN_REV_NONE_RE = re.compile(r"^down_revision\s*=\s*None", re.MULTILINE)

# Patterns for idempotency checks
_CREATE_TABLE_RE = re.compile(r"op\.create_table\(\s*['\"](\w+)['\"]")
_ADD_COLUMN_RE = re.compile(r"op\.add_column\(\s*['\"](\w+)['\"]")
_IF_NOT_EXISTS_RE = re.compile(r"if\s+not\s+.*(?:has_table|has_column|exists)")


def parse_migration(fpath: Path) -> dict | None:
    """Parse a migration file and return its metadata."""
    text = fpath.read_text(encoding="utf-8")

    rev_match = _REVISION_RE.search(text)
    if not rev_match:
        return None

    revision = rev_match.group(1)

    down_match = _DOWN_REV_RE.search(text)
    down_none = _DOWN_REV_NONE_RE.search(text)

    if down_match:
        down_revision = down_match.group(1) or None
    elif down_none:
        down_revision = None
    else:
        down_revision = None

    # Idempotency check
    create_tables = _CREATE_TABLE_RE.findall(text)
    add_columns = _ADD_COLUMN_RE.findall(text)
    has_guards = bool(_IF_NOT_EXISTS_RE.search(text))

    return {
        "file": fpath.name,
        "revision": revision,
        "down_revision": down_revision,
        "create_tables": create_tables,
        "add_columns": add_columns,
        "has_guards": has_guards,
    }


def detect_cycles(graph: dict[str, str | None]) -> list[str]:
    """Detect cycles in the revision graph. Returns list of cycle descriptions."""
    cycles = []
    visited = set()
    in_stack = set()

    def dfs(node, path):
        if node in in_stack:
            cycle_start = path.index(node)
            cycle = path[cycle_start:] + [node]
            cycles.append(" -> ".join(cycle))
            return
        if node in visited:
            return
        visited.add(node)
        in_stack.add(node)
        path.append(node)
        # Find children (nodes whose down_revision is this node)
        for child, parent in graph.items():
            if parent == node:
                dfs(child, path[:])
        in_stack.discard(node)

    # Start from roots (down_revision is None)
    roots = [rev for rev, down in graph.items() if down is None]
    for root in roots:
        dfs(root, [])

    # Also check nodes not reachable from roots
    for node in graph:
        if node not in visited:
            dfs(node, [])

    return cycles


def main():
    parser = argparse.ArgumentParser(description="Check Alembic migration revision chain")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show the full revision chain")
    parser.add_argument("--check-idempotency", action="store_true",
                        help="Warn about create_table/add_column without guards")
    args = parser.parse_args()

    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("# Alembic Migration Chain Check\n")

    if not VERSIONS_DIR.is_dir():
        print(f"ERROR: Migrations directory not found: {VERSIONS_DIR}")
        sys.exit(1)

    migrations = []
    for fpath in sorted(VERSIONS_DIR.glob("*.py")):
        if fpath.name.startswith("__"):
            continue
        meta = parse_migration(fpath)
        if meta:
            migrations.append(meta)

    print(f"Migration files found: {len(migrations)}\n")

    if not migrations:
        print("No migrations to check.")
        return

    # Build graph: revision -> down_revision
    graph = {}
    rev_to_file = {}
    for m in migrations:
        graph[m["revision"]] = m["down_revision"]
        rev_to_file[m["revision"]] = m["file"]

    all_revisions = set(graph.keys())
    errors = []
    warnings = []

    # 1. Check for orphan references
    for rev, down in graph.items():
        if down is not None and down not in all_revisions:
            errors.append(
                f"Orphan reference: {rev_to_file[rev]} (revision={rev}) "
                f"references down_revision={down} which does not exist"
            )

    # 2. Check for multiple heads
    # A head is a revision that no other revision points to as down_revision
    children = set()
    for down in graph.values():
        if down is not None:
            children.add(down)
    heads = [rev for rev in all_revisions if rev not in children]
    if len(heads) > 1:
        head_files = [f"{rev_to_file[h]} ({h})" for h in sorted(heads)]
        warnings.append(f"Multiple heads detected ({len(heads)}): {', '.join(head_files)}")

    # 3. Check for multiple children of same parent (branches)
    parent_count: dict[str, list[str]] = {}
    for rev, down in graph.items():
        if down is not None:
            parent_count.setdefault(down, []).append(rev)
    for parent, kids in parent_count.items():
        if len(kids) > 1:
            kid_files = [f"{rev_to_file[k]} ({k})" for k in sorted(kids)]
            warnings.append(
                f"Branch detected at {parent}: {len(kids)} children: "
                f"{', '.join(kid_files)}"
            )

    # 4. Cycle detection
    cycles = detect_cycles(graph)
    for cycle in cycles:
        errors.append(f"Cycle detected: {cycle}")

    # 5. Idempotency check (optional)
    if args.check_idempotency:
        for m in migrations:
            if (m["create_tables"] or m["add_columns"]) and not m["has_guards"]:
                ops = []
                if m["create_tables"]:
                    ops.append(f"create_table({', '.join(m['create_tables'])})")
                if m["add_columns"]:
                    ops.append(f"add_column({', '.join(m['add_columns'])})")
                warnings.append(
                    f"{m['file']}: {'; '.join(ops)} without idempotency guards"
                )

    # Verbose output
    if args.verbose:
        print("## Revision Chain\n")
        # Build and display the chain from roots
        roots = [rev for rev, down in graph.items() if down is None]
        for root in sorted(roots):
            print(f"  ROOT: {rev_to_file[root]} ({root})")
            _print_chain(root, graph, rev_to_file, indent=2)
        print()
        if heads:
            print(f"## Heads: {', '.join(sorted(heads))}\n")

    # Report
    if errors:
        print(f"## Errors ({len(errors)})\n")
        for msg in errors:
            print(f"- X {msg}")
        print()

    if warnings:
        print(f"## Warnings ({len(warnings)})\n")
        for msg in warnings:
            print(f"- ! {msg}")
        print()

    if not errors and not warnings:
        print(f"PASS: Migration chain is valid ({len(migrations)} migrations, {len(heads)} head(s))")
    elif errors:
        print(f"FAIL: {len(errors)} error(s), {len(warnings)} warning(s)")
        sys.exit(1)
    else:
        print(f"WARN: {len(warnings)} warning(s), 0 errors")


def _print_chain(parent_rev, graph, rev_to_file, indent=0):
    """Recursively print children of a revision."""
    children = [rev for rev, down in graph.items() if down == parent_rev]
    for child in sorted(children):
        prefix = "  " * indent
        print(f"{prefix}-> {rev_to_file[child]} ({child})")
        _print_chain(child, graph, rev_to_file, indent + 1)


if __name__ == "__main__":
    main()
