#!/usr/bin/env python3
# designer: When you run /seja-setup --workspace, I am how a fresh SEJA workspace
#   comes into existence alongside your existing codebase without touching
#   the codebase itself. I copy the harness skeleton into the workspace
#   path you name and wire it to point at the target project, so your
#   design history and plans accumulate in a separate git repo while the
#   code being described stays untouched.
"""
create_workspace.py -- Create a project workspace from the foundational SEJA
harness, targeting an existing codebase without modifying it.

Invocation: user-cli
Lifecycle: active

Usage:
    python create_workspace.py --from <foundational_harness> --workspace <ws_path> --target <codebase_path> [--dry-run]

The --from source (foundational SEJA harness) can be a directory (repo or
harness source directory) or a .zip file.  The script copies harness files
into the workspace and configures absolute paths to the target codebase.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

# Ensure sibling scripts are importable
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from upgrade_harness import collect_source_files  # noqa: E402

# Standard _output subdirectories — keep in sync with template/conventions.md
# Directory Structure section (PLANS_DIR, ADVISORY_DIR, etc.)
_OUTPUT_SUBDIRS = [
    "plans",
    "advisory-logs",
    "research-logs",
    "generated-scripts",
    "inventories",
    "user-tests",
    "explained-behaviors",
    "explained-code",
    "explained-data-model",
    "explained-architecture",
    "behavior-evolution",
    "onboarding-plans",
    "communication",
    "roadmaps",
    "qa-logs",
    "check-logs",
    "tmp",
]

_GITIGNORE_CONTENT = """\
# OS files
.DS_Store
Thumbs.db
Desktop.ini

# Python
__pycache__/
*.pyc
*.pyo
*.egg-info/
.eggs/
dist/
build/

# IDE / Editor
.idea/
.vscode/
*.swp
*.swo
*~
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def resolve_source(source_path: Path) -> tuple[Path, str | None]:
    """Resolve source path, extracting zip if needed.

    Returns (source_root, temp_dir_or_None).
    """
    temp_dir: str | None = None

    if source_path.is_file() and source_path.suffix == ".zip":
        temp_dir = tempfile.mkdtemp(prefix="seja-workspace-")
        print(f"INFO: Extracting {source_path.name} to temporary directory...")
        with zipfile.ZipFile(source_path, "r") as zf:
            # Validate paths to prevent zip-slip (directory traversal)
            for member in zf.namelist():
                resolved = (Path(temp_dir) / member).resolve()
                if not str(resolved).startswith(str(Path(temp_dir).resolve())):
                    print(f"ERROR: Zip contains path traversal entry: {member}")
                    sys.exit(1)
            zf.extractall(temp_dir)
        source_root = Path(temp_dir)
        # Check if zip contents are nested in a subdirectory
        entries = list(source_root.iterdir())
        if len(entries) == 1 and entries[0].is_dir():
            source_root = entries[0]
        # If zip has .claude/ at root level, use that root
        if not (source_root / ".claude").is_dir():
            for child in source_root.iterdir():
                if child.is_dir() and (child / ".claude").is_dir():
                    source_root = child
                    break
    elif source_path.is_dir():
        source_root = source_path
        if not (source_root / ".claude").is_dir():
            for child in source_root.iterdir():
                if child.is_dir() and (child / ".claude").is_dir():
                    source_root = child
                    break
    else:
        print(f"ERROR: Source path does not exist or is not a directory/zip: {source_path}")
        sys.exit(1)

    return source_root, temp_dir


def validate_source(source_root: Path) -> None:
    """Validate that source contains .claude/ and .claude/references/."""
    if not (source_root / ".claude").is_dir():
        print(f"ERROR: Source does not contain a .claude/ directory: {source_root}")
        sys.exit(1)
    if not (source_root / ".claude" / "references").is_dir():
        print(f"ERROR: Source does not contain a .claude/references/ directory: {source_root}")
        sys.exit(1)


def _detect_project_dirs(target: Path) -> tuple[Path, Path]:
    """Detect backend and frontend directories in the target project."""
    backend_dir = target / "backend"
    if not backend_dir.is_dir():
        backend_dir = target
    frontend_dir = target / "frontend"
    if not frontend_dir.is_dir():
        frontend_dir = target
    return backend_dir, frontend_dir


def generate_conventions(
    template_path: Path,
    workspace: Path,
    target: Path,
) -> tuple[str, Path, Path]:
    """Read template/conventions.md and substitute path variables.

    Returns (generated content, backend_dir, frontend_dir).
    """
    content = template_path.read_text(encoding="utf-8")

    output_dir = (workspace / "_output").resolve().as_posix()

    backend_dir, frontend_dir = _detect_project_dirs(target)

    content = content.replace("| `OUTPUT_DIR` | `_output` |", f"| `OUTPUT_DIR` | `{output_dir}` |")
    content = content.replace("| `BACKEND_DIR` | `{{BACKEND_DIR}}` |", f"| `BACKEND_DIR` | `{backend_dir.resolve().as_posix()}` |")
    content = content.replace("| `FRONTEND_DIR` | `{{FRONTEND_DIR}}` |", f"| `FRONTEND_DIR` | `{frontend_dir.resolve().as_posix()}` |")

    return content, backend_dir, frontend_dir


# ---------------------------------------------------------------------------
# Main workspace creation logic
# ---------------------------------------------------------------------------


def run_create(
    source_root: Path,
    workspace: Path,
    target: Path,
    dry_run: bool,
) -> None:
    prefix = "[DRY-RUN] " if dry_run else ""

    # --- Report accumulators ---
    report_setup: list[str] = []
    report_copied: list[str] = []
    report_output: list[str] = []
    report_conventions: list[str] = []
    report_manual: list[str] = []

    # --- 1. Create workspace directory ---
    if not workspace.is_dir():
        if not dry_run:
            workspace.mkdir(parents=True, exist_ok=True)
        report_setup.append(f"Created workspace directory: {workspace}")
        print(f"OK: {prefix}{report_setup[-1]}")
    else:
        report_setup.append(f"Workspace directory already exists: {workspace}")
        print(f"INFO: {report_setup[-1]}")

    # --- 2. git init ---
    if not dry_run:
        result = subprocess.run(
            ["git", "init"],
            cwd=str(workspace),
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            report_setup.append("Initialized git repository")
            print(f"OK: {report_setup[-1]}")
        else:
            report_setup.append(f"WARN: git init failed: {result.stderr.strip()}")
            print(f"WARN: {report_setup[-1]}")
    else:
        report_setup.append("Would initialize git repository")
        print(f"INFO: {prefix}{report_setup[-1]}")

    # --- 3. Copy harness files ---
    source_files = collect_source_files(source_root)
    if not source_files:
        print("ERROR: No harness files found in source.")
        sys.exit(1)

    for src_file in source_files:
        rel = src_file.relative_to(source_root).as_posix()
        dest = workspace / rel
        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src_file), str(dest))
        report_copied.append(rel)
        print(f"OK: {prefix}Copied {rel}")

    # --- 4. Create _output directory tree ---
    output_dir = workspace / "_output"
    for subdir in _OUTPUT_SUBDIRS:
        subdir_path = output_dir / subdir
        if not dry_run:
            subdir_path.mkdir(parents=True, exist_ok=True)
        report_output.append(f"_output/{subdir}/")

    # Create empty briefs.md
    briefs_path = output_dir / "briefs.md"
    if not dry_run:
        briefs_path.touch()
    report_output.append("_output/briefs.md")

    # Create empty INDEX.md so the workspace has its own artifact counter
    index_path = output_dir / "INDEX.md"
    if not dry_run:
        index_path.write_text(
            "# Artifact Index\n"
            "\n"
            "> Auto-generated by `generate_macro_index.py`. 0 artifacts indexed.\n"
            "> Do not edit manually -- regenerate with:"
            " `python .claude/skills/scripts/generate_macro_index.py`\n"
            "\n"
            "| Date | Type | ID | Title | Status | File |\n"
            "|------|------|----|-------|--------|------|\n",
            encoding="utf-8",
        )
    report_output.append("_output/INDEX.md")

    print(f"OK: {prefix}Created _output/ with {len(_OUTPUT_SUBDIRS)} subdirectories, briefs.md, and INDEX.md")

    # --- 5. Generate project/conventions.md ---
    template_path = source_root / ".claude" / "references" / "template" / "conventions.md"
    conventions_dest = workspace / "product-design" / "conventions.md"

    if template_path.is_file():
        conventions_content, backend_dir, frontend_dir = generate_conventions(template_path, workspace, target)
        if not dry_run:
            conventions_dest.parent.mkdir(parents=True, exist_ok=True)
            conventions_dest.write_text(conventions_content, encoding="utf-8")
        report_conventions.append(f"Generated {conventions_dest.relative_to(workspace).as_posix()}")
        report_conventions.append(f"  OUTPUT_DIR  = {(workspace / '_output').resolve().as_posix()}")
        report_conventions.append(f"  BACKEND_DIR = {backend_dir.resolve().as_posix()}")
        report_conventions.append(f"  FRONTEND_DIR = {frontend_dir.resolve().as_posix()}")
        print(f"OK: {prefix}Generated project/conventions.md")
    else:
        report_conventions.append("WARN: template/conventions.md not found in source — skipped")
        print(f"WARN: {report_conventions[-1]}")

    # --- 6. Create .gitignore ---
    gitignore_path = workspace / ".gitignore"
    if not dry_run:
        gitignore_path.write_text(_GITIGNORE_CONTENT, encoding="utf-8")
    report_setup.append("Created .gitignore")
    print(f"OK: {prefix}Created .gitignore")

    # --- 7. Generate launcher scripts ---
    report_launchers: list[str] = []
    target_posix = target.resolve().as_posix()
    target_win = str(target.resolve()).replace("/", "\\")

    launch_sh_content = (
        '#!/usr/bin/env bash\n'
        '# Launch Claude Code with the target codebase as an additional directory.\n'
        '# Generated by create_workspace.py -- edit the --add-dir path if the codebase moves.\n'
        'cd "$(dirname "$0")"\n'
        f'claude --add-dir "{target_posix}"\n'
    )
    launch_bat_content = (
        '@echo off\r\n'
        'REM Launch Claude Code with the target codebase as an additional directory.\r\n'
        'REM Generated by create_workspace.py -- edit the --add-dir path if the codebase moves.\r\n'
        'cd /d "%~dp0"\r\n'
        f'claude --add-dir "{target_win}"\r\n'
    )

    launch_sh_path = workspace / "launch.sh"
    launch_bat_path = workspace / "launch.bat"

    if not dry_run:
        launch_sh_path.write_text(launch_sh_content, encoding="utf-8", newline="\n")
        launch_bat_path.write_bytes(launch_bat_content.encode("utf-8"))
    report_launchers.append(f"launch.sh  (target: {target_posix})")
    report_launchers.append(f"launch.bat (target: {target_win})")
    print(f"OK: {prefix}Generated launcher scripts")

    # --- Manual steps ---
    report_manual.append(
        "Start a session: ./launch.sh (Unix/Git Bash) or launch.bat (Windows)."
    )
    report_manual.append(
        "Review product-design/conventions.md and fill in remaining "
        "{{PLACEHOLDER}} values."
    )
    report_manual.append(
        "Create project-specific reference files (project/conceptual-design-*.md, "
        "project/metacomm-*.md) as needed."
    )

    # --- Summary report ---
    print()
    print("=" * 60)
    print(f"  WORKSPACE CREATION SUMMARY {'(DRY RUN)' if dry_run else ''}")
    print("=" * 60)

    def _section(title: str, items: list[str]) -> None:
        print(f"\n--- {title} ---")
        if items:
            for item in items:
                print(f"  {item}")
        else:
            print("  (none)")

    _section("Setup", report_setup)
    _section("Harness Files Copied", [f"{len(report_copied)} files copied"])
    _section("Output Structure", report_output)
    _section("Conventions", report_conventions)
    _section("Launcher Scripts", report_launchers)
    _section("Next Steps", report_manual)

    print()
    if dry_run:
        print("INFO: Dry run complete — no files were modified.")
    else:
        print(f"OK: Workspace created at {workspace}")
        print(f"    Targeting codebase at {target}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a project workspace from the foundational SEJA harness.",
        epilog=(
            "Example:\n"
            "  python create_workspace.py --from ../seja-priv --workspace ./my-ws --target ../my-project\n"
            "  python create_workspace.py --from ./kit.zip --workspace ./ws --target ./proj --dry-run"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--from",
        dest="source",
        required=True,
        help="Path to the foundational SEJA harness: a directory or .zip file",
    )
    parser.add_argument(
        "--workspace",
        required=True,
        help="Path for the new workspace directory",
    )
    parser.add_argument(
        "--target",
        required=True,
        help="Path to the target codebase (used for absolute paths in conventions)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without making changes",
    )

    args = parser.parse_args()

    # Resolve source
    source_path = Path(args.source).resolve()
    source_root, temp_dir = resolve_source(source_path)
    validate_source(source_root)

    # Resolve workspace and target
    workspace = Path(args.workspace).resolve()
    target = Path(args.target).resolve()

    if not target.is_dir():
        print(f"ERROR: Target codebase directory does not exist: {target}")
        sys.exit(1)

    print(f"INFO: Foundational harness: {source_root}")
    print(f"INFO: Workspace:              {workspace}")
    print(f"INFO: Target codebase:        {target}")
    print()

    try:
        run_create(source_root, workspace, target, args.dry_run)
    finally:
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
