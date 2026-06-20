# designer: When you want a rough shape of how big your project is, I count
#   source files and lines across your frontend, backend, and the SEJA
#   harness layer, separating physical lines from code-only lines so
#   the comment-heavy directories do not inflate the number. You can
#   scope the count by path, by extension, or ask for JSON for further
#   analysis.
"""Local source line counter for this workspace.

Invocation: user-cli
Lifecycle: active

Purpose
- Count source files and line totals across frontend/backend.
- Count SEJA harness files (.claude/, .claude/references/).
- Exclude tests by directory and filename pattern.
- Report both:
  - physical lines (includes blank + comment-only)
  - code-only lines (excludes blank/comment-only)

Usage:
- Default project scan (backend + frontend):
  - `python .claude/skills/scripts/count_loc.py`
- Harness scan (SEJA harness files):
  - `python .claude/skills/scripts/count_loc.py --harness`
- JSON output (machine-readable):
  - `python .claude/skills/scripts/count_loc.py --json`
- Include per-file details:
  - `python .claude/skills/scripts/count_loc.py --list-files`
- Count only selected extensions:
  - `python .claude/skills/scripts/count_loc.py --ext .py .js .jsx .ts .tsx`
- Count a subset of paths:
  - `python .claude/skills/scripts/count_loc.py frontend`
  - `python .claude/skills/scripts/count_loc.py backend/app`

Notes / limitations
- Comment detection is heuristic (cloc-like, not parser-accurate).
- A line is counted as code if it contains any non-comment content.
- Inline comments on code lines are still counted as code.
- Python docstrings are treated as code (matching common LOC conventions).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

from project_config import REPO_ROOT, get


DEFAULT_SOURCE_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".html",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".mako",
    ".sql",
    ".sh",
}

HARNESS_SOURCE_EXTENSIONS = {
    ".md",
    ".py",
    ".sh",
    ".json",
    ".yaml",
    ".yml",
}

# Harness component directories scanned by --harness, relative to REPO_ROOT.
HARNESS_DIRS = [
    ".claude/skills",
    ".claude/agents",
    ".claude/rules",
    ".claude/references/general",
    ".claude/references/template",
]

# Directories skipped during recursive scans. Includes test locations and common generated folders.
EXCLUDED_DIR_NAMES = {
    "tests",
    "test",
    "__tests__",
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".venv",
    "venv",
    "__pycache__",
    ".git",
}

# Test-like filenames skipped even when outside excluded directories.
EXCLUDED_FILE_PATTERNS = [
    re.compile(r"\.(test|spec)\.[^.]+$", re.IGNORECASE),
]

# Single-line comment markers checked after block-comment stripping.
LINE_COMMENT_MARKERS = {
    ".py": ["#"],
    ".sh": ["#"],
    ".yaml": ["#"],
    ".yml": ["#"],
    ".js": ["//"],
    ".jsx": ["//"],
    ".ts": ["//"],
    ".tsx": ["//"],
    ".sql": ["--"],
    ".mako": ["##"],
}

# Block comment delimiters used by the heuristic "code-only" counter.
BLOCK_COMMENT_MARKERS = {
    ".js": [("/*", "*/")],
    ".jsx": [("/*", "*/")],
    ".ts": [("/*", "*/")],
    ".tsx": [("/*", "*/")],
    ".css": [("/*", "*/")],
    ".scss": [("/*", "*/")],
    ".sass": [("/*", "*/")],
    ".less": [("/*", "*/")],
    ".sql": [("/*", "*/")],
    ".md": [("<!--", "-->")],
    ".html": [("<!--", "-->")],
    ".mako": [("<%doc>", "</%doc>"), ("<!--", "-->")],
}


@dataclass
class FileCount:
    """Line counts for one file or an aggregate."""

    physical: int = 0
    blank: int = 0
    comment_only: int = 0
    code: int = 0

    def add(self, other: "FileCount") -> None:
        self.physical += other.physical
        self.blank += other.blank
        self.comment_only += other.comment_only
        self.code += other.code

    @property
    def nonblank(self) -> int:
        return self.physical - self.blank


@dataclass
class FileResult:
    """Per-file result used to build area/extension summaries."""

    path: str
    area: str
    ext: str
    counts: FileCount


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments and provide repo-specific defaults."""
    project_name = get("PROJECT_NAME", "project")
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description=(
            f"Count source files and lines in {project_name}, excluding tests. "
            "Reports physical lines and code-only lines (no blank/comment-only lines)."
        ),
        epilog=(
            "Examples:\n"
            "  py -3 .claude/skills/scripts/count_loc.py\n"
            "  py -3 .claude/skills/scripts/count_loc.py --harness\n"
            "  py -3 .claude/skills/scripts/count_loc.py --json\n"
            "  py -3 .claude/skills/scripts/count_loc.py --list-files\n"
            "  py -3 .claude/skills/scripts/count_loc.py frontend --ext .js .jsx .css\n"
        ),
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=None,
        help="Paths to scan (defaults to backend and frontend, or harness dirs with --harness).",
    )
    parser.add_argument(
        "--harness",
        action="store_true",
        help="Count SEJA harness files (skills, agents, rules, references) instead of project source.",
    )
    parser.add_argument(
        "--ext",
        nargs="*",
        default=None,
        help="Extensions to include (e.g. --ext .py .js .jsx).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON output.",
    )
    parser.add_argument(
        "--list-files",
        action="store_true",
        help="Include per-file counts in output (text and JSON).",
    )
    return parser.parse_args()


def normalize_extensions(exts: Iterable[str]) -> set[str]:
    """Normalize extensions so callers can pass `py` or `.py` interchangeably."""
    normalized: set[str] = set()
    for ext in exts:
        if not ext:
            continue
        normalized.add(ext if ext.startswith(".") else f".{ext}")
    return normalized


def should_skip_file(path: Path) -> bool:
    """Return True when filename matches a test-style exclusion pattern."""
    name = path.name
    for pattern in EXCLUDED_FILE_PATTERNS:
        if pattern.search(name):
            return True
    return False


def iter_source_files(paths: list[Path], allowed_exts: set[str]) -> Iterable[Path]:
    """Yield files under `paths` that match extension filters and exclusion rules."""
    for root in paths:
        if not root.exists():
            continue
        if root.is_file():
            if root.suffix.lower() in allowed_exts and not should_skip_file(root):
                yield root
            continue

        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIR_NAMES]
            current_dir = Path(dirpath)
            for filename in filenames:
                path = current_dir / filename
                if path.suffix.lower() not in allowed_exts:
                    continue
                if should_skip_file(path):
                    continue
                yield path


def strip_block_comments(
    text: str,
    block_rules: list[tuple[str, str]],
    block_state: tuple[str, str] | None,
) -> tuple[str, tuple[str, str] | None]:
    """Remove block comments heuristically, preserving non-comment text on the line."""
    result: list[str] = []
    i = 0
    active = block_state

    while i < len(text):
        if active is not None:
            _, end = active
            end_idx = text.find(end, i)
            if end_idx == -1:
                return "".join(result), active
            i = end_idx + len(end)
            active = None
            continue

        next_hit: tuple[int, str, str] | None = None
        for start, end in block_rules:
            idx = text.find(start, i)
            if idx != -1 and (next_hit is None or idx < next_hit[0]):
                next_hit = (idx, start, end)

        if next_hit is None:
            result.append(text[i:])
            break

        idx, start, end = next_hit
        result.append(text[i:idx])
        i = idx + len(start)
        end_idx = text.find(end, i)
        if end_idx == -1:
            active = (start, end)
            break
        i = end_idx + len(end)

    return "".join(result), active


def count_file(path: Path) -> FileCount:
    """Count physical/blank/comment-only/code lines for a single file.

    The code count is heuristic: it removes recognized block comments, skips blank lines,
    and treats lines starting with configured single-line comment markers as comment-only.
    """
    ext = path.suffix.lower()
    line_markers = LINE_COMMENT_MARKERS.get(ext, [])
    block_rules = BLOCK_COMMENT_MARKERS.get(ext, [])
    counts = FileCount()
    block_state: tuple[str, str] | None = None

    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for raw_line in f:
                counts.physical += 1
                line = raw_line.rstrip("\n\r")
                if not line.strip():
                    counts.blank += 1
                    continue

                processed = line
                if block_rules:
                    processed, block_state = strip_block_comments(processed, block_rules, block_state)

                stripped = processed.strip()

                if not stripped:
                    counts.comment_only += 1
                    continue

                if any(stripped.startswith(marker) for marker in line_markers):
                    counts.comment_only += 1
                    continue

                counts.code += 1
    except OSError as exc:
        print(f"Warning: failed to read {path}: {exc}", file=sys.stderr)

    return counts


def area_name(path: Path, requested_roots: list[Path]) -> str:
    """Label a file with the root bucket it came from (e.g. backend)."""
    for root in requested_roots:
        try:
            path.relative_to(root)
            return root.name or str(root)
        except ValueError:
            continue
    return path.parts[0] if path.parts else str(path)


def build_summary(results: list[FileResult]) -> dict:
    """Aggregate per-file results into totals, by-area, and by-extension summaries."""
    total = FileCount()
    by_area: dict[str, FileCount] = defaultdict(FileCount)
    by_ext: dict[str, FileCount] = defaultdict(FileCount)
    file_counts_by_area = Counter()
    file_counts_by_ext = Counter()

    for result in results:
        total.add(result.counts)
        by_area[result.area].add(result.counts)
        by_ext[result.ext].add(result.counts)
        file_counts_by_area[result.area] += 1
        file_counts_by_ext[result.ext] += 1

    return {
        "files": len(results),
        "totals": {
            "physical": total.physical,
            "blank": total.blank,
            "comment_only": total.comment_only,
            "nonblank": total.nonblank,
            "code": total.code,
        },
        "by_area": {
            area: {
                "files": file_counts_by_area[area],
                "physical": counts.physical,
                "blank": counts.blank,
                "comment_only": counts.comment_only,
                "nonblank": counts.nonblank,
                "code": counts.code,
            }
            for area, counts in sorted(by_area.items())
        },
        "by_extension": {
            ext: {
                "files": file_counts_by_ext[ext],
                "physical": counts.physical,
                "blank": counts.blank,
                "comment_only": counts.comment_only,
                "nonblank": counts.nonblank,
                "code": counts.code,
            }
            for ext, counts in sorted(by_ext.items())
        },
    }


def print_text(summary: dict, results: list[FileResult], list_files: bool, *, harness: bool = False) -> None:
    """Render markdown-formatted output."""
    totals = summary["totals"]
    heading = "# SEJA harness count" if harness else "# Source count (tests excluded)"
    print(f"{heading}\n")
    print("| Metric | Count |")
    print("| --- | ---: |")
    print(f"| Files | {summary['files']} |")
    print(f"| Physical | {totals['physical']} |")
    print(f"| Code only | {totals['code']} |")
    print(f"| Blank | {totals['blank']} |")
    print(f"| Comment-only | {totals['comment_only']} |")
    print()

    print("## By area\n")
    print("| Area | Files | Physical | Code | Blank | Comment-only |")
    print("| --- | ---: | ---: | ---: | ---: | ---: |")
    for area, data in summary["by_area"].items():
        print(
            f"| {area} | {data['files']} | {data['physical']} "
            f"| {data['code']} | {data['blank']} | {data['comment_only']} |"
        )
    print()

    print("## By extension\n")
    print("| Extension | Files | Physical | Code | Blank | Comment-only |")
    print("| --- | ---: | ---: | ---: | ---: | ---: |")
    for ext, data in summary["by_extension"].items():
        print(
            f"| {ext} | {data['files']} | {data['physical']} "
            f"| {data['code']} | {data['blank']} | {data['comment_only']} |"
        )

    if list_files:
        print()
        print("## Per file\n")
        print("| File | Physical | Code | Blank | Comment-only |")
        print("| --- | ---: | ---: | ---: | ---: |")
        for r in sorted(results, key=lambda x: x.path.lower()):
            c = r.counts
            print(
                f"| {r.path} | {c.physical} | {c.code} "
                f"| {c.blank} | {c.comment_only} |"
            )


def resolve_defaults(args: argparse.Namespace) -> tuple[list[Path], set[str]]:
    """Apply harness-aware defaults for paths and extensions."""
    if args.harness:
        paths = args.paths or [str(REPO_ROOT / d) for d in HARNESS_DIRS]
        exts = args.ext or sorted(HARNESS_SOURCE_EXTENSIONS)
    else:
        backend_dir = get("BACKEND_DIR", "backend")
        frontend_dir = get("FRONTEND_DIR", "frontend")
        paths = args.paths or [str(REPO_ROOT / backend_dir), str(REPO_ROOT / frontend_dir)]
        exts = args.ext or sorted(DEFAULT_SOURCE_EXTENSIONS)
    return [Path(p).resolve() for p in paths], normalize_extensions(exts)


def main() -> int:
    """CLI entrypoint."""
    args = parse_args()
    roots, allowed_exts = resolve_defaults(args)

    results: list[FileResult] = []
    for path in iter_source_files(roots, allowed_exts):
        counts = count_file(path)
        results.append(
            FileResult(
                path=str(path),
                area=area_name(path, roots),
                ext=path.suffix.lower(),
                counts=counts,
            )
        )

    summary = build_summary(results)

    if args.json:
        payload = {
            "mode": "harness" if args.harness else "project",
            **summary,
            "roots": [str(p) for p in roots],
            "extensions": sorted(allowed_exts),
        }
        if args.list_files:
            payload["files_detail"] = [
                {
                    "path": r.path,
                    "area": r.area,
                    "extension": r.ext,
                    **asdict(r.counts),
                    "nonblank": r.counts.nonblank,
                }
                for r in sorted(results, key=lambda x: x.path.lower())
            ]
        print(json.dumps(payload, indent=2))
    else:
        print_text(summary, results, args.list_files, harness=args.harness)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

