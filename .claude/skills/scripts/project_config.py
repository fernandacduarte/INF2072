#!/usr/bin/env python3
# designer: When any SEJA helper script needs to know where your backend lives,
#   where tests go, or any other path that varies by project, I'm the central
#   config reader that parses your project's conventions file and hands back a
#   consistent answer. Scripts call into me instead of hard-coding paths, so
#   the same tooling works across projects with different layouts without the
#   scripts themselves ever seeing your specific choices.
"""
project_config — Central configuration for SEJA helper scripts.

Invocation: library
Lifecycle: active

Parses project/conventions.md and exposes all variables via get/get_path/get_list.
Falls back to template/conventions.md when project/conventions.md is absent.

Usage from sibling scripts:
    from project_config import REPO_ROOT, get, get_path, get_list

    backend_dir = get_path("BACKEND_DIR")
    subpackages = get_list("BACKEND_SUBPACKAGES", ["api", "models", "services"])
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Repo root discovery
# ---------------------------------------------------------------------------

_CONVENTIONS_REL = Path("product-design", "conventions.md")
_CONVENTIONS_REL_LEGACY = Path("project-design", "conventions.md")  # pre-migration-0003 name
_TEMPLATE_REL = Path(".claude", "references", "template", "conventions.md")
_ROW_RE = re.compile(
    r"^\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|", re.MULTILINE
)
_VAR_REF_RE = re.compile(r"\$\{([^}]+)\}")
_MAX_RESOLVE_PASSES = 10
_SHELL_INJECTION_RE = re.compile(r"`|\$\(|\$\(\(")
_UNRESOLVED_VAR_RE = re.compile(r"\$\{[^}]+\}")


def _find_repo_root() -> Path:
    """Walk up from the script's location until we find a .claude/ directory."""
    candidate = Path(__file__).resolve().parent
    while candidate != candidate.parent:
        if (candidate / ".claude").is_dir():
            return candidate
        candidate = candidate.parent
    return Path.cwd()


REPO_ROOT = _find_repo_root()
GENERAL_REFS_DIR = REPO_ROOT / ".claude" / "references" / "general"
TEMPLATE_REFS_DIR = REPO_ROOT / ".claude" / "references" / "template"
_pd_new = REPO_ROOT / "product-design"
_pd_legacy = REPO_ROOT / "project-design"
PROJECT_REFS_DIR = _pd_new if _pd_new.is_dir() else _pd_legacy

# ---------------------------------------------------------------------------
# Config parsing (lazy, cached at module level)
# ---------------------------------------------------------------------------

_config: dict[str, str] | None = None
_warned_missing = False


def _parse_config() -> dict[str, str]:
    """Read project/conventions.md, extract variable rows, resolve refs."""
    global _warned_missing

    conventions = REPO_ROOT / _CONVENTIONS_REL
    if not conventions.is_file():
        # Fall back to pre-migration-0003 directory name.
        legacy = REPO_ROOT / _CONVENTIONS_REL_LEGACY
        if legacy.is_file():
            conventions = legacy
    if not conventions.is_file():
        template = REPO_ROOT / _TEMPLATE_REL
        if template.is_file():
            if not _warned_missing:
                print(
                    f"INFO: project/conventions.md not found; using template/conventions.md as fallback",
                    file=sys.stderr,
                )
                _warned_missing = True
            conventions = template
        else:
            if not _warned_missing:
                print(
                    f"WARNING: neither project/conventions.md nor template/conventions.md found",
                    file=sys.stderr,
                )
                _warned_missing = True
            return {}

    text = conventions.read_text(encoding="utf-8", errors="replace")
    raw: dict[str, str] = {}
    for m in _ROW_RE.finditer(text):
        raw[m.group(1)] = m.group(2)

    # Reject values containing shell injection patterns
    tainted = [k for k, v in raw.items() if _SHELL_INJECTION_RE.search(v)]
    for key in tainted:
        print(
            f"WARNING: conventions variable {key} contains shell metacharacters "
            f"and was dropped: {raw[key]!r}",
            file=sys.stderr,
        )
        del raw[key]

    # Resolve ${VAR} references iteratively
    resolved = dict(raw)
    for _ in range(_MAX_RESOLVE_PASSES):
        changed = False
        for key, value in resolved.items():
            new_value = _VAR_REF_RE.sub(
                lambda m: resolved.get(m.group(1), m.group(0)), value
            )
            if new_value != value:
                resolved[key] = new_value
                changed = True
        if not changed:
            break

    # Warn about unresolved variable references (circular or missing)
    for key, value in resolved.items():
        if _UNRESOLVED_VAR_RE.search(value):
            print(
                f"WARNING: conventions variable {key} has unresolved reference "
                f"after {_MAX_RESOLVE_PASSES} passes: {value!r}",
                file=sys.stderr,
            )

    return resolved


def _ensure_config() -> dict[str, str]:
    """Return cached config, parsing on first call."""
    global _config
    if _config is None:
        _config = _parse_config()
    return _config


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get(key: str, default: str | None = None) -> str | None:
    """Get a resolved string value by variable name."""
    return _ensure_config().get(key, default)


def get_path(key: str, default: str | None = None) -> Path | None:
    """Get a resolved value as a Path relative to REPO_ROOT.

    Returns None (with a warning) if the resolved path escapes REPO_ROOT.
    """
    value = get(key, default)
    if value is None:
        return None
    candidate = (REPO_ROOT / value).resolve()
    try:
        candidate.relative_to(REPO_ROOT.resolve())
    except ValueError:
        print(
            f"WARNING: path for {key} resolves outside REPO_ROOT and was "
            f"rejected: {value!r}",
            file=sys.stderr,
        )
        return None
    return candidate


def get_list(key: str, default: list[str] | None = None) -> list[str]:
    """Split a comma-separated value into a list of stripped strings."""
    value = get(key)
    if value is None:
        return default if default is not None else []
    return [item.strip() for item in value.split(",")]


def diff_conventions(project_path: str | Path, template_path: str | Path) -> dict:
    """Compare a project/conventions file against a template/conventions file.

    Parses both files using _ROW_RE and returns a dict with:
      - missing_in_project: variable names in template but not in project
      - extra_in_project: variable names in project but not in template
      - value_differences: list of dicts with key, project_value, template_value
    """
    project_path = Path(project_path)
    template_path = Path(template_path)

    def _parse_rows(path: Path) -> dict[str, str]:
        if not path.is_file():
            return {}
        text = path.read_text(encoding="utf-8", errors="replace")
        return {m.group(1): m.group(2) for m in _ROW_RE.finditer(text)}

    project_vars = _parse_rows(project_path)
    template_vars = _parse_rows(template_path)

    project_keys = set(project_vars)
    template_keys = set(template_vars)

    value_differences = [
        {
            "key": key,
            "project_value": project_vars[key],
            "template_value": template_vars[key],
        }
        for key in sorted(project_keys & template_keys)
        if project_vars[key] != template_vars[key]
    ]

    return {
        "missing_in_project": sorted(template_keys - project_keys),
        "extra_in_project": sorted(project_keys - template_keys),
        "value_differences": value_differences,
    }


def get_pending_file() -> Path | None:
    """Return the pending ledger path, or None if OUTPUT_DIR is unresolvable.

    Lazy evaluation (not a module-level constant) because get_path() may return
    None on a misconfigured repo, and a None at import time would break every
    script that imports project_config. Callers should handle None explicitly.
    """
    output_dir = get_path("OUTPUT_DIR")
    return (output_dir / "pending.jsonl") if output_dir is not None else None


# ---------------------------------------------------------------------------
# Standalone mode
# ---------------------------------------------------------------------------


def _main() -> None:
    """Print all resolved config variables."""
    config = _ensure_config()
    if not config:
        print("No configuration loaded (project/conventions.md missing or empty).")
        return

    print(f"REPO_ROOT: {REPO_ROOT}\n")
    max_key_len = max(len(k) for k in config)
    for key in sorted(config):
        print(f"  {key:<{max_key_len}}  =  {config[key]}")


if __name__ == "__main__":
    _main()
