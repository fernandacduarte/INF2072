#!/usr/bin/env python3
# designer: When /seja-setup --upgrade moves your project from one SEJA version to a newer
#   one, I'm the step that runs the numbered migration scripts that sit
#   between those versions, in order, so the harness bits your project
#   carries stay in step with the new release. You see which migrations ran
#   and can dry-run first to preview the changes before committing to them.
"""
run_migrations.py -- Run pending SEJA harness migrations.

Invocation: script-invoked, user-cli
Lifecycle: active

Reads .seja-version from the target project, scans .claude/migrations/ for
NNNN_*.py migration files, filters those whose from_version matches the
current version range, sorts by sequence number, and executes them in order.

Usage:
    python run_migrations.py [--target <project_path>] [--dry-run]
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Version helpers
# ---------------------------------------------------------------------------


def _parse_version(v: str) -> tuple[int, ...]:
    """Parse a dotted version string into a tuple of ints."""
    parts: list[int] = []
    for segment in v.strip().split("."):
        try:
            parts.append(int(segment))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def read_seja_version(project_root: Path) -> str:
    """Read .seja-version from *project_root*. Returns '0.0.0' if missing."""
    version_file = project_root / ".seja-version"
    if not version_file.is_file():
        return "0.0.0"
    text = version_file.read_text(encoding="utf-8").strip()
    return text if text else "0.0.0"


def write_seja_version(project_root: Path, version: str) -> None:
    """Write *version* to .seja-version (no trailing newline beyond the string)."""
    version_file = project_root / ".seja-version"
    version_file.write_text(version, encoding="utf-8")


# ---------------------------------------------------------------------------
# Migration discovery
# ---------------------------------------------------------------------------


def _find_migrations_dir() -> Path:
    """Return the .claude/migrations/ directory relative to this script."""
    # This script lives in .claude/skills/scripts/; migrations is at .claude/migrations/
    return Path(__file__).resolve().parent.parent.parent / "migrations"


def discover_migrations(migrations_dir: Path) -> list[dict]:
    """Scan *migrations_dir* for NNNN_*.py files and load their metadata.

    Each migration module must export:
        from_version: str
        to_version: str
        upgrade(root: Path) -> None
        downgrade(root: Path) -> None   (optional)

    Returns a sorted list of dicts with keys:
        sequence, name, path, from_version, to_version, module
    """
    if not migrations_dir.is_dir():
        return []

    migrations: list[dict] = []
    for f in sorted(migrations_dir.iterdir()):
        if not f.is_file() or f.suffix != ".py":
            continue
        name = f.stem
        # Expect NNNN_ prefix
        parts = name.split("_", 1)
        if len(parts) < 2 or not parts[0].isdigit():
            continue

        sequence = int(parts[0])

        # Import the module
        spec = importlib.util.spec_from_file_location(f"migration_{name}", str(f))
        if spec is None or spec.loader is None:
            print(f"WARN: Could not load migration {f.name} -- skipping")
            continue
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as exc:
            print(f"WARN: Error loading migration {f.name}: {exc} -- skipping")
            continue

        from_ver = getattr(module, "from_version", None)
        to_ver = getattr(module, "to_version", None)
        upgrade_fn = getattr(module, "upgrade", None)

        if from_ver is None or to_ver is None or upgrade_fn is None:
            print(
                f"WARN: Migration {f.name} missing required exports "
                f"(from_version, to_version, upgrade) -- skipping"
            )
            continue

        migrations.append(
            {
                "sequence": sequence,
                "name": name,
                "path": f,
                "from_version": from_ver,
                "to_version": to_ver,
                "module": module,
            }
        )

    migrations.sort(key=lambda m: m["sequence"])
    return migrations


# ---------------------------------------------------------------------------
# Migration execution
# ---------------------------------------------------------------------------


def run_migrations(
    project_root: Path,
    dry_run: bool = False,
) -> None:
    """Run all pending migrations against *project_root*."""
    current_version = read_seja_version(project_root)
    current_tuple = _parse_version(current_version)

    prefix = "[DRY-RUN] " if dry_run else ""
    print(f"INFO: {prefix}Current .seja-version: {current_version}")

    migrations_dir = _find_migrations_dir()
    all_migrations = discover_migrations(migrations_dir)

    if not all_migrations:
        print(f"INFO: {prefix}No migration files found in {migrations_dir}")
        return

    # Filter: only migrations whose from_version <= current_version
    # and to_version > current_version
    pending = [
        m
        for m in all_migrations
        if _parse_version(m["from_version"]) <= current_tuple
        and _parse_version(m["to_version"]) > current_tuple
    ]

    if not pending:
        print(f"INFO: {prefix}No pending migrations (already at {current_version})")
        return

    print(f"INFO: {prefix}Found {len(pending)} pending migration(s)")

    final_version = current_version
    for m in pending:
        label = f"{m['name']} ({m['from_version']} -> {m['to_version']})"
        if dry_run:
            print(f"INFO: [DRY-RUN] Would run migration: {label}")
        else:
            print(f"INFO: Running migration: {label}")
            try:
                m["module"].upgrade(project_root)
                print(f"OK: Migration {m['name']} completed")
            except Exception as exc:
                print(f"ERROR: Migration {m['name']} failed: {exc}")
                print(f"ERROR: Stopping migration chain at version {final_version}")
                write_seja_version(project_root, final_version)
                sys.exit(1)
        final_version = m["to_version"]

    if not dry_run:
        write_seja_version(project_root, final_version)
        print(f"OK: Updated .seja-version to {final_version}")
    else:
        print(f"INFO: [DRY-RUN] Would update .seja-version to {final_version}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def find_project_root() -> Path:
    """Walk up from CWD to find the directory containing .claude/."""
    current = Path.cwd().resolve()
    while current != current.parent:
        if (current / ".claude").is_dir():
            return current
        current = current.parent
    return Path.cwd().resolve()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run pending SEJA harness migrations.",
    )
    parser.add_argument(
        "--target",
        default=None,
        help="Project directory to migrate (default: auto-detect repo root)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without making changes",
    )
    args = parser.parse_args()

    if args.target:
        project_root = Path(args.target).resolve()
    else:
        project_root = find_project_root()

    if not (project_root / ".claude").is_dir():
        print(f"ERROR: Target does not contain a .claude/ directory: {project_root}")
        sys.exit(1)

    run_migrations(project_root, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
