#!/usr/bin/env python3
# designer: When you want to confirm no orphaned git worktrees are
#   lingering from parallel wave execution, I run `git worktree list`
#   and flag any worktrees beyond the main one. Clean repos pass; stale
#   worktrees get listed with their paths so you can remove them.
"""
check_worktree_health.py -- Detect orphaned git worktrees.

Invocation: agent-invoked, hook-ci
Lifecycle: active

Runs `git worktree list` and flags any worktrees beyond the main working
tree. Orphaned worktrees from parallel wave execution can lock files on
Windows and waste disk space.

Exit codes: 0 = clean (only main worktree), 1 = orphaned worktrees found.

Usage
-----
    python .claude/skills/scripts/check_worktree_health.py

CHECK_PLUGIN_MANIFEST:
  name: Worktree Health
  stack:
    backend: [any]
    frontend: [any]
  scope: worktree
  critical: false
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from project_config import REPO_ROOT


def main() -> int:
    result = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"FAIL: git worktree list failed: {result.stderr.strip()}")
        return 1

    worktrees: list[str] = []
    current_path = ""
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            current_path = line[len("worktree "):]
        elif line == "bare" or line.startswith("branch "):
            pass
        elif line == "":
            if current_path and Path(current_path).resolve() != Path(REPO_ROOT).resolve():
                worktrees.append(current_path)
            current_path = ""

    if current_path and Path(current_path).resolve() != Path(REPO_ROOT).resolve():
        worktrees.append(current_path)

    if not worktrees:
        print("PASS: no orphaned worktrees")
        return 0

    print(f"FAIL: {len(worktrees)} orphaned worktree(s) found:")
    for wt in worktrees:
        print(f"  - {wt}")
    print("Remove with: git worktree remove <path> && git worktree prune")
    return 1


if __name__ == "__main__":
    sys.exit(main())
