#!/usr/bin/env python3
# designer: When /seja-setup --upgrade pulls a newer SEJA release into your project, I'm
#   the engine that swaps the harness files (skills, rules, agents,
#   references, scripts) for the new version while leaving your project
#   directory, your conventions, your design intent, and your output history
#   untouched. You get a clean version bump, any pending migrations applied,
#   and the reference artifacts regenerated -- the same result you would get
#   from deleting and re-seeding, without losing your project-specific work.
"""
upgrade_harness.py — Upgrade a project using the SEJA-Claude harness to a
newer version by replacing harness files while preserving project-specific data.

Invocation: skill-invoked, user-cli
Lifecycle: active

Usage:
    python upgrade_harness.py --from <source_path> [--target <project_path>] [--dry-run]

Source can be a directory (harness source directory) or a .zip file.
The script is idempotent — safe to run multiple times.
"""

# Rationale for design choices and historical context: see upgrade_harness-rationale.md in this directory.

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from project_config import diff_conventions
from run_migrations import run_migrations as _run_pending_migrations

# Old-layout path for references (v1)
_OLD_REFS_REL = Path(".claude", "skills", "references")

# Legacy-layout path for references (v2 -- _references/ at repo root)
_REFERENCES_V2_REL = Path("_references")

# Current-layout path for references (v3 -- inside .claude/)
_REFERENCES_REL = Path(".claude", "references")

# Consumer-side public-release pin (A2). Records the public `seja` tag the
# project was last seeded or upgraded to. Legacy pre-A2 projects may lack this
# file or carry an internal harness version -- both are handled gracefully.
_SEJA_VERSION_FILE = ".seja-version"
_LEGACY_VERSION_SENTINEL = "unknown"

# Reference generators invoked by run_upgrade after migrations succeed.
# Each entry: (display-name, script-basename). Scripts live under the target
# repo's .claude/skills/scripts/ directory.
_REFERENCE_GENERATORS: list[tuple[str, str]] = [
    ("harness-reference", "generate_harness_reference.py"),
    ("skills reference", "generate_skills_reference.py"),
    ("perspectives reference", "generate_perspectives_reference.py"),
]


def _regenerate_reference_files(
    target: Path,
    dry_run: bool,
    report_updated: list[str],
) -> None:
    """Invoke the three reference generators against the target repo.

    Best-effort: if a generator is missing (older target), log a warning and
    continue. If a generator exits non-zero, log a warning and continue. The
    upgrade itself must not fail because of a generator issue.
    """
    scripts_dir = target / ".claude" / "skills" / "scripts"
    for display_name, script_name in _REFERENCE_GENERATORS:
        script = scripts_dir / script_name
        if not script.is_file():
            script = scripts_dir / "priv" / script_name
        if not script.is_file():
            print(f"WARN: Skipped {display_name} regeneration: {script_name} not found")
            continue
        if dry_run:
            print(f"OK: Would regenerate {display_name} (dry run)")
            continue
        try:
            result = subprocess.run(
                [sys.executable, str(script)],
                cwd=str(target),
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                report_updated.append(f"Regenerated {display_name}")
                print(f"OK: Regenerated {display_name}")
            else:
                print(f"WARN: {display_name} regeneration failed (exit {result.returncode})")
                if result.stderr:
                    print(result.stderr.rstrip(), file=sys.stderr)
        except subprocess.TimeoutExpired:
            print(f"WARN: {display_name} regeneration timed out (60s)")
        except Exception as exc:
            print(f"WARN: {display_name} regeneration error: {exc}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def find_project_root() -> Path:
    """Walk up from CWD to find the directory containing .claude/."""
    current = Path.cwd().resolve()
    while current != current.parent:
        if (current / ".claude").is_dir():
            return current
        current = current.parent
    return Path.cwd().resolve()


def read_version(root: Path) -> str | None:
    """Parse version string from a VERSION file under .claude/skills/."""
    version_file = root / ".claude" / "skills" / "VERSION"
    if not version_file.is_file():
        return None
    text = version_file.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        if line.startswith("version:"):
            return line.split(":", 1)[1].strip()
    return None


def read_seja_version(root: Path) -> str | None:
    """Read the consumer's pinned public-seja release tag from .seja-version."""
    path = root / _SEJA_VERSION_FILE
    if not path.is_file():
        return None
    value = path.read_text(encoding="utf-8", errors="replace").strip()
    return value or None


def write_seja_version(root: Path, tag: str, dry_run: bool) -> str:
    """Write the resolved public-seja release tag to .seja-version.

    Returns a human-readable summary string for the upgrade report.
    """
    path = root / _SEJA_VERSION_FILE
    if dry_run:
        return f"Would pin {tag} in {_SEJA_VERSION_FILE}"
    path.write_text(tag + "\n", encoding="utf-8")
    return f"Pinned {tag} in {_SEJA_VERSION_FILE}"


def detect_layout(target: Path) -> str:
    """Detect harness layout in target codebase or workspace.

    Returns: 'new' (v3: .claude/references/), 'legacy' (v2: _references/),
             'old' (v1: .claude/skills/references/), or 'fresh'
    """
    if (target / _REFERENCES_REL).is_dir():
        # Check it actually has files (v3 layout)
        ar_dir = target / _REFERENCES_REL
        if any(ar_dir.iterdir()):
            return "new"
    if (target / _REFERENCES_V2_REL).is_dir():
        # v2 layout: _references/ at repo root
        ar_dir = target / _REFERENCES_V2_REL
        if any(ar_dir.iterdir()):
            return "legacy"
    old_refs = target / _OLD_REFS_REL
    if old_refs.is_dir() and any(old_refs.iterdir()):
        return "old"
    return "fresh"


def collect_source_files(source: Path) -> list[Path]:
    """Collect all harness files from source directory."""
    files: list[Path] = []
    claude_dir = source / ".claude"
    ar_dir = source / _REFERENCES_REL  # .claude/references/ (v3 layout)

    # Skills -- recursively discover all directories containing SKILL.md
    # or SKILL-<facet>.md files (e.g., SKILL-quickguide.md, SKILL-rationale.md).
    # This handles both top-level skills (skills/plan/) and nested internals
    # (skills/_internal/plan/standard/).  The scripts/ subtree is excluded
    # because it is enumerated separately below.
    skills_dir = claude_dir / "skills"
    if skills_dir.is_dir():
        # Collect unique skill directories that contain SKILL*.md files
        skill_dirs: set[Path] = set()
        for skill_md in skills_dir.rglob("SKILL.md"):
            if "scripts" not in skill_md.relative_to(skills_dir).parts:
                skill_dirs.add(skill_md.parent)
        for skill_facet in skills_dir.rglob("SKILL-*.md"):
            if "scripts" not in skill_facet.relative_to(skills_dir).parts:
                skill_dirs.add(skill_facet.parent)

        for skill_dir in sorted(skill_dirs):
            # Collect SKILL.md and SKILL-<facet>.md files
            for sibling in sorted(skill_dir.glob("SKILL*.md")):
                name = sibling.name
                if name == "SKILL.md" or name.startswith("SKILL-"):
                    if sibling.is_file():
                        files.append(sibling)
            # Collect co-located .py scripts (skill-owned scripts that live
            # next to SKILL.md, e.g. check/check_docs.py, design/check_plan_coverage.py)
            for py_file in sorted(skill_dir.glob("*.py")):
                if py_file.is_file():
                    files.append(py_file)

    # Scripts (skip priv/ subdirectory -- harness-exclusive scripts)
    scripts_dir = claude_dir / "skills" / "scripts"
    if scripts_dir.is_dir():
        for f in sorted(scripts_dir.iterdir()):
            if f.is_file() and f.suffix == ".py":
                files.append(f)
        # Explicitly skip scripts_dir/priv/ -- those are harness-exclusive

    # Agents
    agents_dir = claude_dir / "agents"
    if agents_dir.is_dir():
        for f in sorted(agents_dir.iterdir()):
            if f.is_file() and f.suffix == ".md":
                files.append(f)

    # Rules
    rules_dir = claude_dir / "rules"
    if rules_dir.is_dir():
        for f in sorted(rules_dir.iterdir()):
            if f.is_file() and f.suffix == ".md":
                files.append(f)

    # References — .claude/references/general/ and .claude/references/template/
    # (project/ subdir is excluded — that is consumer-specific data)
    if ar_dir.is_dir():
        for subdir_name in ("general", "template"):
            subdir = ar_dir / subdir_name
            if subdir.is_dir():
                for sub in sorted(subdir.rglob("*")):
                    if sub.is_file() and sub.suffix in (".md", ".json"):
                        files.append(sub)

    # Metadata
    for meta_name in ("skills/VERSION", "CHEATSHEET.md", "CHANGELOG.md"):
        meta_file = claude_dir / meta_name
        if meta_file.is_file():
            files.append(meta_file)

    return files


def is_preserved(rel_path: str) -> bool:
    """Check if a relative path should be preserved (never overwritten)."""
    parts = Path(rel_path).parts
    filename = parts[-1] if parts else ""

    # product-design/ directory (v4 layout: renamed from project-design in v0.3.0)
    # Also guard the old name during the upgrade window before migration 0003 runs.
    if parts and parts[0] in ("product-design", "project-design"):
        return True
    # project/ subdirectory in _references/ (v2 legacy layout)
    if len(parts) >= 2 and parts[0] == "_references" and parts[1] == "project":
        return True
    # settings files
    if filename in ("settings.json", "settings.local.json"):
        return True
    # _output directory
    if parts and parts[0] == "_output":
        return True
    # CLAUDE.md at root
    if rel_path == "CLAUDE.md":
        return True

    return False


def scan_old_path_references(target: Path) -> list[tuple[str, int, str]]:
    """Scan product-design/*.md and CLAUDE.md for v2 layout path references (_references/).

    Called after a v2→v3 migration to surface remaining _references/ strings
    in consumer-owned files that need manual updating.

    Returns list of (file_rel_path, line_number, line_text) tuples.
    """
    old_path = "_references/"
    hits: list[tuple[str, int, str]] = []
    files_to_scan: list[Path] = []

    # product-design/*.md (v3 consumer-specific design files)
    project_dir = target / "product-design"
    if project_dir.is_dir():
        for f in sorted(project_dir.iterdir()):
            if f.is_file() and f.name.endswith(".md"):
                files_to_scan.append(f)

    # CLAUDE.md at root
    claude_md = target / "CLAUDE.md"
    if claude_md.is_file():
        files_to_scan.append(claude_md)

    for fpath in files_to_scan:
        try:
            lines = fpath.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        rel = fpath.relative_to(target).as_posix()
        for i, line in enumerate(lines, 1):
            if old_path in line:
                hits.append((rel, i, line.strip()))

    return hits


# ---------------------------------------------------------------------------
# Consumer project migration: v2 (_references/) → v3 (.claude/references/ + product-design/)
# ---------------------------------------------------------------------------


def migrate_references_split(target: Path, dry_run: bool) -> list[str]:
    """Migrate a consumer project from v2 (_references/) layout to v3.

    v3 layout:
      _references/general/   → .claude/references/general/
      _references/template/  → .claude/references/template/
      _references/project/   → product-design/

    Migration is per-subdir guarded (Amendment D1): each subdir is only moved
    if it exists.  The function is idempotent -- safe to call on a v3 project.

    Git-aware (Amendment D2): attempts ``git mv`` first.  Falls back to
    ``shutil.move()`` when the target is not a git repo or ``git mv`` exits
    non-zero (e.g., dry-run mode, files not staged, etc.).

    Pre-existing ``product-design/`` guard (Amendment D3): if
    ``product-design/`` already exists and is non-empty, the function aborts
    rather than clobbering existing design work.

    Returns a list of human-readable action strings (empty list when nothing
    to migrate).
    """
    refs_v2 = target / "_references"
    if not refs_v2.is_dir():
        # Nothing to migrate -- already v3 (or no references at all).
        return []

    actions: list[str] = []
    prefix = "[DRY-RUN] " if dry_run else ""

    def _git_mv(src: Path, dst: Path) -> bool:
        """Attempt git mv src dst.  Returns True on success."""
        git_dir = target / ".git"
        if not git_dir.exists():
            return False
        result = subprocess.run(
            ["git", "-C", str(target), "mv", str(src.relative_to(target)), str(dst.relative_to(target))],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0

    def _move(src: Path, dst: Path) -> None:
        """Move src to dst, trying git mv first then falling back to shutil.move."""
        if dry_run:
            print(f"INFO: {prefix}Would move {src.relative_to(target)} → {dst.relative_to(target)}")
            return
        used_git = _git_mv(src, dst)
        if used_git:
            print(f"OK: Moved (git mv) {src.relative_to(target)} → {dst.relative_to(target)}")
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            print(f"OK: Moved (shutil) {src.relative_to(target)} → {dst.relative_to(target)}")

    # Ensure .claude/references/ destination exists (v3 harness refs root).
    refs_v3 = target / ".claude" / "references"
    if not dry_run:
        refs_v3.mkdir(parents=True, exist_ok=True)

    # --- general/ ---
    src_general = refs_v2 / "general"
    if src_general.is_dir():
        dst_general = refs_v3 / "general"
        _move(src_general, dst_general)
        actions.append(f"{prefix}Moved _references/general/ → .claude/references/general/")

    # --- template/ ---
    src_template = refs_v2 / "template"
    if src_template.is_dir():
        dst_template = refs_v3 / "template"
        _move(src_template, dst_template)
        actions.append(f"{prefix}Moved _references/template/ → .claude/references/template/")

    # --- project/ → product-design/ (Amendment D3: guard pre-existing non-empty target) ---
    src_project = refs_v2 / "project"
    if src_project.is_dir():
        dst_project = target / "product-design"
        if dst_project.is_dir() and any(dst_project.iterdir()):
            msg = (
                f"ERROR: Cannot migrate _references/project/ → product-design/ because "
                f"product-design/ already exists and is non-empty. "
                f"Resolve the conflict manually before upgrading."
            )
            print(msg, file=sys.stderr)
            if dry_run:
                actions.append(f"[DRY-RUN] Would abort: {msg}")
                return actions
            raise SystemExit(1)
        _move(src_project, dst_project)
        actions.append(f"{prefix}Moved _references/project/ → product-design/")

    # --- Remove _references/ if now empty ---
    if not dry_run:
        try:
            refs_v2.rmdir()
            actions.append("Removed empty _references/")
            print("OK: Removed empty _references/")
        except OSError:
            # Not empty -- may contain unknown subdirs; leave in place.
            actions.append("WARN: _references/ not empty after migration -- left in place")
            print("WARN: _references/ not empty after migration -- left in place")
    else:
        actions.append(f"{prefix}Would remove _references/ (if empty after moves)")

    return actions


# ---------------------------------------------------------------------------
# Main upgrade logic
# ---------------------------------------------------------------------------


def run_upgrade(
    source_root: Path,
    target: Path,
    dry_run: bool,
    new_version: str | None = None,
) -> None:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    # --- Report accumulators ---
    report_backup: list[str] = []
    report_version: list[str] = []
    report_migration: list[str] = []
    report_updated: list[str] = []
    report_preserved: list[str] = []
    report_convention_gaps: list[str] = []
    report_manual: list[str] = []

    prefix = "[DRY-RUN] " if dry_run else ""

    # --- Layout detection ---
    layout = detect_layout(target)
    print(f"INFO: {prefix}Detected layout: {layout}")

    # --- Public-release pin banner (A2) ---
    target_seja_version = read_seja_version(target)
    if new_version:
        if target_seja_version:
            report_version.append(
                f"Upgrading public pin from {target_seja_version} to {new_version}"
            )
        else:
            report_version.append(
                f"No {_SEJA_VERSION_FILE} found — treating as {_LEGACY_VERSION_SENTINEL}. "
                f"Upgrading public pin to {new_version}"
            )
        print(f"INFO: {report_version[-1]}")

    # --- Internal VERSION reading ---
    source_version = read_version(source_root) or "unknown"
    target_version = read_version(target)
    if target_version:
        report_version.append(f"Upgrading from {target_version} to {source_version}")
    else:
        report_version.append(
            f"No VERSION found in target — treating as v1.0.0. Upgrading to {source_version}"
        )
    print(f"INFO: {report_version[-1]}")

    # --- Backup ---
    claude_backup = target / f".claude-backup-{timestamp}"
    if not dry_run:
        shutil.copytree(target / ".claude", claude_backup)
        report_backup.append(f"Backed up .claude/ → {claude_backup.name}/")
        print(f"OK: {report_backup[-1]}")
    else:
        report_backup.append(f"Would back up .claude/ → .claude-backup-{timestamp}/")
        print(f"INFO: {prefix}{report_backup[-1]}")

    if layout == "legacy":
        # Back up _references/ (v2) before migration — .claude/ backup already covers v3
        ar_backup = target / f"_references-backup-{timestamp}"
        if not dry_run:
            shutil.copytree(target / _REFERENCES_V2_REL, ar_backup)
            report_backup.append(f"Backed up _references/ → {ar_backup.name}/")
            print(f"OK: {report_backup[-1]}")
        else:
            report_backup.append(
                f"Would back up _references/ → _references-backup-{timestamp}/"
            )
            print(f"INFO: {prefix}{report_backup[-1]}")

    # --- v2 → v3 path layout migration (run before collect_source_files) ---
    pre_migration_layout = layout  # preserve for scan_old_path_references gate below
    migration_actions = migrate_references_split(target, dry_run)
    for action in migration_actions:
        report_migration.append(action)
    if migration_actions:
        # Re-detect layout after migration so the rest of the upgrade uses v3 paths.
        layout = detect_layout(target)
        print(f"INFO: {prefix}Layout after migration: {layout}")

    # --- Layout migration ---
    if layout == "old":
        # v1 → v2: move from .claude/skills/references/ to _references/
        old_refs_dir = target / _OLD_REFS_REL
        ar_dir = target / _REFERENCES_V2_REL

        if not dry_run:
            ar_dir.mkdir(parents=True, exist_ok=True)

        # Move files from old refs to _references/
        if old_refs_dir.is_dir():
            for entry in sorted(old_refs_dir.iterdir()):
                if entry.is_file() and (entry.suffix == ".md" or entry.suffix == ".json"):
                    dest = ar_dir / entry.name
                    if not dry_run:
                        shutil.move(str(entry), str(dest))
                    report_migration.append(
                        f"Moved {_OLD_REFS_REL.as_posix()}/{entry.name} → "
                        f"{_REFERENCES_V2_REL.as_posix()}/{entry.name}"
                    )
                    print(f"OK: {prefix}{report_migration[-1]}")
                elif entry.is_dir():
                    # Subdirectories (e.g., general/review-perspectives/)
                    dest_dir = ar_dir / entry.name
                    if not dry_run:
                        if dest_dir.exists():
                            shutil.rmtree(dest_dir)
                        shutil.move(str(entry), str(dest_dir))
                    report_migration.append(
                        f"Moved {_OLD_REFS_REL.as_posix()}/{entry.name}/ → "
                        f"{_REFERENCES_V2_REL.as_posix()}/{entry.name}/"
                    )
                    print(f"OK: {prefix}{report_migration[-1]}")

            # Remove old refs directory if empty
            if not dry_run:
                try:
                    old_refs_dir.rmdir()
                    report_migration.append(
                        f"Removed empty {_OLD_REFS_REL.as_posix()}/"
                    )
                    print(f"OK: {report_migration[-1]}")
                except OSError:
                    report_migration.append(
                        f"WARN: {_OLD_REFS_REL.as_posix()}/ not empty after migration"
                    )
                    print(f"WARN: {report_migration[-1]}")
            else:
                report_migration.append(
                    f"Would remove {_OLD_REFS_REL.as_posix()}/ (if empty)"
                )
                print(f"INFO: {prefix}{report_migration[-1]}")

    elif layout == "fresh":
        # Ensure .claude/references/ exists for fresh v3 projects
        ar_dir = target / _REFERENCES_REL
        if not dry_run:
            ar_dir.mkdir(parents=True, exist_ok=True)
        report_migration.append(f"Fresh project — created {_REFERENCES_REL.as_posix()}/")
        print(f"INFO: {prefix}{report_migration[-1]}")

    # --- Overwrite harness files from source ---
    source_files = collect_source_files(source_root)
    if not source_files:
        print("ERROR: No harness files found in source.")
        sys.exit(1)

    for src_file in source_files:
        rel = src_file.relative_to(source_root).as_posix()

        if is_preserved(rel):
            report_preserved.append(rel)
            print(f"SKIP: {prefix}{rel} (preserved)")
            continue

        dest = target / rel
        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src_file), str(dest))

        report_updated.append(rel)
        print(f"OK: {prefix}Updated {rel}")

    # --- Remove retired skills from target ---
    _RETIRED_SKILLS = ["quickstart", "seed"]
    for skill_name in _RETIRED_SKILLS:
        for harness_dir in (".claude",):
            retired_dir = target / harness_dir / "skills" / skill_name
            if retired_dir.is_dir():
                if not dry_run:
                    shutil.rmtree(retired_dir)
                report_updated.append(
                    f"Removed retired skill {harness_dir}/skills/{skill_name}/"
                )
                print(f"OK: {prefix}Removed retired skill {harness_dir}/skills/{skill_name}/")

    # --- Run pending migrations ---
    print()
    print(f"INFO: {prefix}Running pending migrations...")
    try:
        _run_pending_migrations(target, dry_run=dry_run)
        report_migration.append("Ran pending migrations successfully")
    except SystemExit:
        report_migration.append("WARN: Migration runner exited with an error")
    except Exception as exc:
        report_migration.append(f"WARN: Migration runner error: {exc}")

    # --- Regenerate reference files ---
    print()
    print(f"INFO: {prefix}Regenerating harness reference files...")
    _regenerate_reference_files(target, dry_run=dry_run, report_updated=report_updated)

    # --- Pin public-release tag (A2) ---
    if new_version:
        summary = write_seja_version(target, new_version, dry_run=dry_run)
        report_version.append(summary)
        print(f"OK: {prefix}{summary}")

    # --- Preserved files summary ---
    # Check for settings files and CLAUDE.md
    for check_rel in (".claude/settings.json", ".claude/settings.local.json", "CLAUDE.md"):
        check_path = target / check_rel
        if check_path.is_file() and check_rel not in report_preserved:
            report_preserved.append(check_rel)

    # _output directory
    if (target / "_output").is_dir():
        if "_output/" not in report_preserved:
            report_preserved.append("_output/ (entire directory)")

    # product-design/*.md files (v4 layout: renamed from project-design in v0.3.0)
    # Fall back to project-design/ for installations where migration 0003 has not yet run.
    for _pd_name in ("product-design", "project-design"):
        project_design_dir = target / _pd_name
        if project_design_dir.is_dir():
            for f in sorted(project_design_dir.rglob("*.md")):
                rel = f.relative_to(target).as_posix()
                if rel not in report_preserved:
                    report_preserved.append(rel)
            break

    # project/*.md files in _references/ (v2 legacy layout)
    project_dir = target / _REFERENCES_V2_REL / "project"
    if project_dir.is_dir():
        for f in sorted(project_dir.rglob("*.md")):
            rel = f.relative_to(target).as_posix()
            if rel not in report_preserved:
                report_preserved.append(rel)

    # --- Convention schema diff ---
    # Try v4 layout (product-design/) first, fall back to v3 (project-design/), then v2.
    project_conv_v4 = target / "product-design" / "conventions.md"
    project_conv_v3 = target / "project-design" / "conventions.md"
    project_conv_v2 = target / _REFERENCES_V2_REL / "project" / "conventions.md"
    project_conv = (
        project_conv_v4 if project_conv_v4.is_file()
        else project_conv_v3 if project_conv_v3.is_file()
        else project_conv_v2
    )
    template_conv = target / _REFERENCES_REL / "template" / "conventions.md"

    if project_conv.is_file() and template_conv.is_file():
        diff = diff_conventions(project_conv, template_conv)

        if diff["missing_in_project"]:
            report_convention_gaps.append(
                f"Variables in template missing from project/conventions.md: "
                f"{', '.join(diff['missing_in_project'])}"
            )
        if diff["extra_in_project"]:
            report_convention_gaps.append(
                f"Variables in project/conventions.md not in template: "
                f"{', '.join(diff['extra_in_project'])}"
            )
        if not diff["missing_in_project"] and not diff["extra_in_project"]:
            report_convention_gaps.append("Convention variables are in sync.")
    elif project_conv.is_file():
        report_convention_gaps.append(
            "WARN: template/conventions.md not found — cannot compare."
        )
    else:
        report_convention_gaps.append(
            "INFO: No project/conventions.md found — diff skipped."
        )

    # --- Path reference scan (migration layouts only) ---
    if pre_migration_layout in ("old", "legacy"):
        old_refs = scan_old_path_references(target)
        if old_refs:
            report_manual.append(
                "Old path references found (need manual update to new layout):"
            )
            for fpath, lineno, line_text in old_refs:
                report_manual.append(f"  {fpath}:{lineno}: {line_text}")
        else:
            report_manual.append("No old path references found — migration clean.")

    # CLAUDE.md always flagged for review
    if (target / "CLAUDE.md").is_file():
        report_manual.append(
            "Review CLAUDE.md — root project instructions may need updates to "
            "reflect new harness version."
        )

    # --- Summary report ---
    print()
    print("=" * 60)
    print(f"  UPGRADE SUMMARY {'(DRY RUN)' if dry_run else ''}")
    print("=" * 60)

    def _section(title: str, items: list[str]) -> None:
        print(f"\n--- {title} ---")
        if items:
            for item in items:
                print(f"  {item}")
        else:
            print("  (none)")

    _section("Backup", report_backup)
    _section("Version", report_version)
    _section("Migration", report_migration)
    _section("Files Updated", report_updated)
    _section("Files Preserved", report_preserved)
    _section("Convention Gaps", report_convention_gaps)
    _section("Manual Steps Needed", report_manual)

    print()
    if dry_run:
        print("INFO: Dry run complete — no files were modified.")
    else:
        print(f"OK: Upgrade complete. Backup stored in {claude_backup.name}/")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upgrade a SEJA-Claude harness project to a newer version.",
        epilog=(
            "Example:\n"
            "  python upgrade_harness.py --from ../seja-public/\n"
            "  python upgrade_harness.py --from ./kit/ --target ./my-project --dry-run"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--from",
        dest="source",
        required=True,
        help="Source of new harness files: a directory or .zip file",
    )
    parser.add_argument(
        "--target",
        default=None,
        help="Project directory to upgrade (default: auto-detect repo root)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without making changes",
    )
    parser.add_argument(
        "--new-version",
        default=None,
        help=(
            "Public release tag being upgraded to (e.g. v0.1.0). When set, "
            "records the value in the target's .seja-version file."
        ),
    )

    args = parser.parse_args()

    # Resolve source
    source_path = Path(args.source).resolve()
    temp_dir = None

    if source_path.is_file() and source_path.suffix == ".zip":
        # Extract zip to temporary directory
        temp_dir = tempfile.mkdtemp(prefix="seja-upgrade-")
        print(f"INFO: Extracting {source_path.name} to temporary directory...")
        with zipfile.ZipFile(source_path, "r") as zf:
            zf.extractall(temp_dir)
        source_root = Path(temp_dir)
        # Check if zip contents are nested in a subdirectory
        entries = list(source_root.iterdir())
        if len(entries) == 1 and entries[0].is_dir():
            source_root = entries[0]
        # If zip has .claude/ at root level, use that root
        if not (source_root / ".claude").is_dir():
            # Try one level deeper
            for child in source_root.iterdir():
                if child.is_dir() and (child / ".claude").is_dir():
                    source_root = child
                    break
    elif source_path.is_dir():
        source_root = source_path
        # Navigate to root with .claude/ if needed
        if not (source_root / ".claude").is_dir():
            for child in source_root.iterdir():
                if child.is_dir() and (child / ".claude").is_dir():
                    source_root = child
                    break
    else:
        print(f"ERROR: Source path does not exist or is not a directory/zip: {source_path}")
        sys.exit(1)

    if not (source_root / ".claude").is_dir():
        print(f"ERROR: Source does not contain a .claude/ directory: {source_root}")
        sys.exit(1)

    # Resolve target
    if args.target:
        target = Path(args.target).resolve()
    else:
        target = find_project_root()

    if not (target / ".claude").is_dir():
        print(f"ERROR: Target does not contain a .claude/ directory: {target}")
        sys.exit(1)

    print(f"INFO: Source: {source_root}")
    print(f"INFO: Target: {target}")
    print()

    try:
        run_upgrade(source_root, target, args.dry_run, new_version=args.new_version)
    finally:
        # Clean up temp directory if we created one
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
