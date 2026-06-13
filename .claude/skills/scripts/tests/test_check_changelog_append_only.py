"""Tests for check_changelog_append_only.py.

Uses a git-based fixture: initializes a temp git repo, commits a baseline file,
then stages a modified version. The validator is invoked with --staged and the
`APPEND_ONLY_SECTIONS` registry is monkey-patched to point at the temp file's
repo-relative path.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
# check_changelog_append_only.py lives in the sibling explain/ skill directory.
EXPLAIN_DIR = SCRIPTS_DIR.parent / "explain"
SCRIPT_PATH = EXPLAIN_DIR / "check_changelog_append_only.py"

sys.path.insert(0, str(SCRIPTS_DIR))


BASELINE_UX_RESEARCH = """\
# TEMPLATE -- UX RESEARCH

> preamble line

---

## 1. Personas

Stub persona section.

---

## 5. Discovered User Journeys

### JM-E-001: First journey

Prose body for first journey.

### JM-E-002: Second journey

Prose body for second journey.

### JM-E-003: Third journey

Prose body for third journey.

---

## CHANGELOG

2026-04-01 | JM-E-001 | added | - | initial entry
2026-04-02 | JM-E-002 | added | - | initial entry
2026-04-03 | JM-E-003 | added | - | initial entry
"""


def _init_git_repo(repo_root: Path) -> None:
    """Initialize a temp git repo with the SEJA .claude marker."""
    (repo_root / ".claude").mkdir(exist_ok=True)
    (repo_root / ".claude" / ".keep").touch()
    subprocess.run(["git", "init", "-q"], cwd=repo_root, check=True)
    subprocess.run(["git", "config", "user.email", "test@test"], cwd=repo_root, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=repo_root, check=True)


def _commit_baseline(repo_root: Path, rel_path: str, content: str) -> None:
    """Write a file, add it, and commit as the baseline."""
    full_path = repo_root / rel_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo_root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "baseline"], cwd=repo_root, check=True)


def _stage_modification(repo_root: Path, rel_path: str, new_content: str) -> None:
    """Overwrite the file and stage it."""
    (repo_root / rel_path).write_text(new_content, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo_root, check=True)


def _run_validator(
    repo_root: Path, registry_path: str
) -> subprocess.CompletedProcess:
    """Invoke check_changelog_append_only.py via a runner that patches the registry."""
    runner = repo_root / "_runner.py"
    runner.write_text(
        "import sys\n"
        "from pathlib import Path\n"
        f"sys.path.insert(0, {str(SCRIPTS_DIR)!r})\n"
        f"sys.path.insert(0, {str(EXPLAIN_DIR)!r})\n"
        "import check_changelog_append_only as mod\n"
        f"mod.REPO_ROOT = Path({str(repo_root)!r})\n"
        f"mod.APPEND_ONLY_SECTIONS = {{{registry_path!r}: ['5. Discovered User Journeys', 'CHANGELOG']}}\n"
        f"sys.argv = [{str(SCRIPT_PATH)!r}, '--staged']\n"
        "sys.exit(mod.main())\n",
        encoding="utf-8",
    )
    return subprocess.run(
        [sys.executable, str(runner)],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        env=dict(os.environ),
    )


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_empty_registry_warns_and_passes(tmp_path: Path) -> None:
    """With APPEND_ONLY_SECTIONS empty, the validator exits 0 with a loud warning."""
    _init_git_repo(tmp_path)
    _commit_baseline(tmp_path, ".claude/references/template/ux-research-results.md", BASELINE_UX_RESEARCH)

    runner = tmp_path / "_runner.py"
    runner.write_text(
        "import sys\n"
        "from pathlib import Path\n"
        f"sys.path.insert(0, {str(SCRIPTS_DIR)!r})\n"
        f"sys.path.insert(0, {str(EXPLAIN_DIR)!r})\n"
        "import check_changelog_append_only as mod\n"
        "mod.APPEND_ONLY_SECTIONS = {}\n"
        f"sys.argv = [{str(SCRIPT_PATH)!r}, '--staged']\n"
        "sys.exit(mod.main())\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(runner)],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        env=dict(os.environ),
    )
    assert result.returncode == 0, result.stderr
    assert "WARNING" in result.stderr
    assert "no-op" in result.stderr.lower()


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_append_only_happy_path(tmp_path: Path) -> None:
    """Appending a new line to CHANGELOG passes the strict rule."""
    rel = ".claude/references/template/ux-research-results.md"
    _init_git_repo(tmp_path)
    _commit_baseline(tmp_path, rel, BASELINE_UX_RESEARCH)

    new_content = BASELINE_UX_RESEARCH + "2026-04-04 | JM-E-004 | added | plan-000267 | new entry\n"
    _stage_modification(tmp_path, rel, new_content)

    result = _run_validator(tmp_path, rel)
    assert result.returncode == 0, (
        f"expected pass, got {result.returncode}\nstderr: {result.stderr}"
    )
    assert "PASS" in result.stdout


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_historical_changelog_line_modified_rejected(tmp_path: Path) -> None:
    """Modifying a pre-existing CHANGELOG line fails the strict rule."""
    rel = ".claude/references/template/ux-research-results.md"
    _init_git_repo(tmp_path)
    _commit_baseline(tmp_path, rel, BASELINE_UX_RESEARCH)

    new_content = BASELINE_UX_RESEARCH.replace(
        "2026-04-01 | JM-E-001 | added | - | initial entry",
        "2026-04-01 | JM-E-001 | added | - | TAMPERED entry",
    )
    _stage_modification(tmp_path, rel, new_content)

    result = _run_validator(tmp_path, rel)
    assert result.returncode == 1, (
        f"expected fail, got {result.returncode}\nstderr: {result.stderr}\nstdout: {result.stdout}"
    )
    assert "FAIL" in result.stderr
    assert "CHANGELOG" in result.stderr


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_historical_changelog_line_removed_rejected(tmp_path: Path) -> None:
    """Removing a pre-existing CHANGELOG line fails the strict rule."""
    rel = ".claude/references/template/ux-research-results.md"
    _init_git_repo(tmp_path)
    _commit_baseline(tmp_path, rel, BASELINE_UX_RESEARCH)

    new_content = BASELINE_UX_RESEARCH.replace(
        "2026-04-02 | JM-E-002 | added | - | initial entry\n", ""
    )
    _stage_modification(tmp_path, rel, new_content)

    result = _run_validator(tmp_path, rel)
    assert result.returncode == 1
    assert "FAIL" in result.stderr
    assert "removed" in result.stderr or "missing" in result.stderr


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_changelog_insertion_in_middle_rejected(tmp_path: Path) -> None:
    """Inserting a new CHANGELOG line in the middle fails the strict rule."""
    rel = ".claude/references/template/ux-research-results.md"
    _init_git_repo(tmp_path)
    _commit_baseline(tmp_path, rel, BASELINE_UX_RESEARCH)

    new_content = BASELINE_UX_RESEARCH.replace(
        "2026-04-02 | JM-E-002 | added | - | initial entry",
        "2026-04-02 | JM-E-002 | added | - | initial entry\n2026-04-99 | R-P-999 | added | plan-000266 | SNEAKY middle insertion",
    )
    _stage_modification(tmp_path, rel, new_content)

    result = _run_validator(tmp_path, rel)
    assert result.returncode == 1
    assert "FAIL" in result.stderr


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_file_new_in_diff_silently_passes(tmp_path: Path) -> None:
    """A brand-new file (no prior commit) is skipped silently."""
    rel = ".claude/references/template/ux-research-results.md"
    _init_git_repo(tmp_path)
    # Commit an UNRELATED file so the repo has HEAD
    (tmp_path / "other.txt").write_text("placeholder", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=tmp_path, check=True)

    # Now stage the ux-research-results.md for the first time
    full = tmp_path / rel
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(BASELINE_UX_RESEARCH, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)

    result = _run_validator(tmp_path, rel)
    assert result.returncode == 0, (
        f"expected silent pass, got {result.returncode}\nstderr: {result.stderr}"
    )
    assert "PASS" in result.stdout


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_marker_line_inserted_mid_section_passes(tmp_path: Path) -> None:
    """Inserting an INCORPORATED marker above an existing JM-E-NNN heading
    inside §5 passes the prose-only rule (marker lines are filtered out before
    the prefix-preserving check)."""
    rel = ".claude/references/template/ux-research-results.md"
    _init_git_repo(tmp_path)
    _commit_baseline(tmp_path, rel, BASELINE_UX_RESEARCH)

    # Insert a marker on the line above JM-E-002 (middle of the section)
    new_content = BASELINE_UX_RESEARCH.replace(
        "### JM-E-002: Second journey",
        "<!-- INCORPORATED: plan-000267 | 2026-04-10 -->\n### JM-E-002: Second journey",
    )
    _stage_modification(tmp_path, rel, new_content)

    result = _run_validator(tmp_path, rel)
    assert result.returncode == 0, (
        f"expected pass, got {result.returncode}\n"
        f"stderr: {result.stderr}\nstdout: {result.stdout}"
    )
    assert "PASS" in result.stdout


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_prose_line_inserted_mid_section_5_rejected(tmp_path: Path) -> None:
    """Inserting a non-marker prose line in the middle of §5 fails the prose-only rule."""
    rel = ".claude/references/template/ux-research-results.md"
    _init_git_repo(tmp_path)
    _commit_baseline(tmp_path, rel, BASELINE_UX_RESEARCH)

    # Insert a regular prose line (not a marker) in the middle of §5
    new_content = BASELINE_UX_RESEARCH.replace(
        "### JM-E-002: Second journey",
        "A sneaky paragraph inserted above the middle entry.\n\n### JM-E-002: Second journey",
    )
    _stage_modification(tmp_path, rel, new_content)

    result = _run_validator(tmp_path, rel)
    assert result.returncode == 1, (
        f"expected fail, got {result.returncode}\n"
        f"stderr: {result.stderr}\nstdout: {result.stdout}"
    )
    assert "FAIL" in result.stderr
    assert "Discovered User Journeys" in result.stderr or "prose-only" in result.stderr
