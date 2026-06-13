# designer: When you suspect your project is carrying dead weight, I walk
#   your source tree and list the files that nothing else imports or
#   references -- likely abandoned modules, stale experiments, or files
#   that moved without being cleaned up. You can silence known false
#   positives through an explicit whitelist, so the check stays useful
#   as a standing hygiene signal.
"""Detect orphaned source files not imported or referenced anywhere.

Invocation: agent-invoked, hook-ci
Lifecycle: active

Purpose
- Find source files (Python, JS/TS) that are not imported by any other file.
- Helps identify dead code, abandoned modules, or misplaced files.

Usage:
  python .claude/skills/scripts/check_unused_files.py
  python .claude/skills/scripts/check_unused_files.py backend
  python .claude/skills/scripts/check_unused_files.py frontend
  python .claude/skills/scripts/check_unused_files.py --verbose

Customization needed:
- BACKEND_DIR, FRONTEND_DIR: source directory paths
- IGNORE_PATTERNS: files/dirs to skip (e.g., __init__.py, migrations)

Whitelist:
- Create `.claude/unused-whitelist.txt` to suppress known false positives.
- One glob pattern per line. Lines starting with # are comments. Empty lines are skipped.
- Invalid glob patterns are logged as warnings but do not abort the script.

CHECK_PLUGIN_MANIFEST:
  name: Unused Files
  stack:
    backend: [any]
    frontend: [any]
  scope: hygiene
  critical: false
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import sys
from pathlib import Path

from project_config import REPO_ROOT, get_path, get_list

# ── Configuration ──────────────────────────────────────────────────────────

BACKEND_DIR = get_path("BACKEND_APP_DIR", "backend/app") or REPO_ROOT / "backend/app"
FRONTEND_DIR = get_path("FRONTEND_SRC_DIR", "frontend/src") or REPO_ROOT / "frontend/src"

BACKEND_EXTENSIONS = {".py"}
FRONTEND_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx"}

IGNORE_PATTERNS = {
    "__init__.py",
    "__pycache__",
    "node_modules",
    "migrations",
    ".test.",
    ".spec.",
    "venv",
    ".venv",
    "dist",
    "build",
}

# Files that are entry points or config — never "unused"
_FRONTEND_ENTRY_DEFAULTS = [
    "main.tsx", "main.jsx", "main.ts", "main.js",
    "index.tsx", "index.jsx", "index.ts", "index.js",
    "App.tsx", "App.jsx", "App.ts", "App.js",
    "reportWebVitals.ts", "reportWebVitals.js",
    "setupTests.ts", "setupTests.js",
    "react-app-env.d.ts", "vite-env.d.ts",
]
ENTRY_POINTS = {
    "run.py",
    "wsgi.py",
    "conftest.py",
    "vite.config.ts",
    "vite.config.js",
    "vitest.config.js",
    "vitest.config.ts",
    "tailwind.config.js",
    "tailwind.config.ts",
    "postcss.config.js",
} | set(get_list("FRONTEND_ENTRY_POINTS", _FRONTEND_ENTRY_DEFAULTS))


WHITELIST_FILE = ".claude/unused-whitelist.txt"


def load_whitelist(root: Path) -> list[str]:
    """Load whitelist patterns from .claude/unused-whitelist.txt.

    The file is optional (no error if missing). Format:
    - One glob pattern per line
    - Lines starting with # are comments
    - Empty lines are skipped
    - Invalid glob patterns are logged as warnings but do not abort
    """
    whitelist_path = root / WHITELIST_FILE
    if not whitelist_path.exists():
        return []
    patterns = []
    for line_num, line in enumerate(whitelist_path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            # Validate the pattern by attempting a match
            fnmatch.fnmatch("test", line)
            patterns.append(line)
        except Exception as exc:
            print(f"  WARNING: Invalid glob pattern on line {line_num} of {WHITELIST_FILE}: {line!r} ({exc})")
    return patterns


def is_whitelisted(path: Path, root: Path, whitelist_patterns: list[str]) -> bool:
    """Check if a file matches any whitelist pattern."""
    try:
        rel_path = str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        rel_path = path.name
    for pattern in whitelist_patterns:
        if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(path.name, pattern):
            return True
    return False


def should_ignore(path: Path) -> bool:
    """Check if a file should be ignored."""
    path_str = str(path)
    name = path.name
    if name in ENTRY_POINTS:
        return True
    for pattern in IGNORE_PATTERNS:
        if pattern in path_str or pattern == name:
            return True
    return False


def collect_source_files(
    root: Path, src_dir: Path, extensions: set[str]
) -> tuple[list[Path], Path]:
    """Collect all source files in a directory.

    Returns the file list and the resolved base directory so callers can
    compute relative paths even when *base* lives outside *root* (workspace
    pattern).
    """
    base = src_dir if src_dir.is_absolute() else root / src_dir
    if not base.exists():
        return [], base
    files = []
    for path in base.rglob("*"):
        if path.is_file() and path.suffix in extensions and not should_ignore(path):
            files.append(path)
    return files, base


def get_module_name(path: Path, base: Path) -> str:
    """Extract the importable module name from a file path.

    *base* is the resolved source directory (e.g. ``root / src_dir``).
    Falls back to the bare filename when the path is outside *base*.
    """
    try:
        rel = path.relative_to(base)
    except ValueError:
        rel = Path(path.name)
    stem = str(rel).replace(os.sep, "/")
    for ext in (".tsx", ".ts", ".jsx", ".js", ".py"):
        if stem.endswith(ext):
            stem = stem[: -len(ext)]
            break
    return stem


def build_import_patterns(module_name: str, filename: str) -> list[str]:
    """Build regex patterns that would match imports of this module."""
    patterns = []
    # Python: from x.y.z import ... or import x.y.z
    py_module = module_name.replace("/", ".")
    patterns.append(re.escape(py_module))
    # Just the filename stem (common in relative imports)
    stem = Path(filename).stem
    patterns.append(r"\b" + re.escape(stem) + r"\b")
    # JS/TS: import ... from './path' or require('./path')
    # Use just the last few segments
    parts = module_name.split("/")
    if len(parts) >= 2:
        short = "/".join(parts[-2:])
        patterns.append(re.escape(short))
    return patterns


def check_references(
    source_file: Path, all_files: list[Path], base: Path
) -> list[Path]:
    """Find files that reference the given source file."""
    module_name = get_module_name(source_file, base)
    filename = source_file.name
    patterns = build_import_patterns(module_name, filename)
    compiled = [re.compile(p) for p in patterns]

    referencing = []
    for other in all_files:
        if other == source_file:
            continue
        try:
            content = other.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pat in compiled:
            if pat.search(content):
                referencing.append(other)
                break
    return referencing


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Detect orphaned source files not imported anywhere."
    )
    parser.add_argument(
        "scope",
        nargs="?",
        default="all",
        choices=["all", "backend", "frontend"],
        help="Scope to check (default: all)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show files that ARE referenced"
    )
    args = parser.parse_args()

    root = REPO_ROOT
    all_source_files: list[Path] = []
    check_files: list[Path] = []
    # Maps each source file to the base directory it was collected from,
    # so relative-path computations work even when base is outside root
    # (workspace pattern where codebase lives in a sibling directory).
    file_base: dict[Path, Path] = {}

    if args.scope in ("all", "backend"):
        backend_files, backend_base = collect_source_files(
            root, BACKEND_DIR, BACKEND_EXTENSIONS
        )
        all_source_files.extend(backend_files)
        check_files.extend(backend_files)
        for f in backend_files:
            file_base[f] = backend_base

    if args.scope in ("all", "frontend"):
        frontend_files, frontend_base = collect_source_files(
            root, FRONTEND_DIR, FRONTEND_EXTENSIONS
        )
        all_source_files.extend(frontend_files)
        check_files.extend(frontend_files)
        for f in frontend_files:
            file_base[f] = frontend_base

    if not check_files:
        print(f"No source files found in scope '{args.scope}'.")
        sys.exit(0)

    # Load whitelist for suppressing known false positives
    whitelist_patterns = load_whitelist(root)
    if whitelist_patterns:
        print(f"Loaded {len(whitelist_patterns)} whitelist pattern(s) from {WHITELIST_FILE}")

    print(f"Scanning {len(check_files)} source files for orphans...\n")

    orphans: list[Path] = []
    referenced: list[Path] = []
    whitelisted_count = 0

    def _display_rel(path: Path) -> Path:
        """Best-effort relative path for display."""
        try:
            return path.relative_to(root)
        except ValueError:
            return path.relative_to(file_base[path])

    for sf in check_files:
        # Skip whitelisted files
        if whitelist_patterns and is_whitelisted(sf, root, whitelist_patterns):
            whitelisted_count += 1
            if args.verbose:
                print(f"  SKIP {_display_rel(sf)}  (whitelisted)")
            continue
        refs = check_references(sf, all_source_files, file_base[sf])
        if refs:
            referenced.append(sf)
            if args.verbose:
                print(f"  OK  {_display_rel(sf)}  (referenced by {len(refs)} file(s))")
        else:
            orphans.append(sf)

    print(f"\n{'='*60}")
    print(f"Total files scanned: {len(check_files)}")
    print(f"Referenced: {len(referenced)}")
    print(f"Potentially orphaned: {len(orphans)}")
    print(f"{'='*60}\n")

    if orphans:
        print("POTENTIALLY ORPHANED FILES:")
        print("(Not imported or referenced by any other source file)\n")
        for o in sorted(orphans):
            print(f"  {_display_rel(o)}")
        print(
            "\nNote: Entry points, __init__.py, tests, and migrations are excluded."
        )
        print("Review these files manually — some may be dynamically loaded.")
        sys.exit(1)
    else:
        print("No orphaned files detected.")
        sys.exit(0)


if __name__ == "__main__":
    main()
