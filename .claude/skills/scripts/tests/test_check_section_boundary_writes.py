"""Tests for check_section_boundary_writes.py.

Uses a git-based fixture: initializes a temp git repo, commits a baseline
file, then stages a modified version. The validator is invoked with --staged
and the `SECTION_BOUNDARY_FILES` registry is monkey-patched to point at the
temp file's repo-relative path.

Test matrix (plan-000269 Step 2 + Amendments C and E):

1. Empty registry warns and passes (no-op discipline).
2. Edit within a single H2 section passes.
3. Edit whose change run spans two H2 sections is rejected.
4. Two separate edits in different sections (separate hunks) pass.
5. New file in diff (no prior) is silently skipped.
6. File not in registry is ignored.
7. Append at EOF inside the last H2 section passes.
8. (Amendment C) Insertion within the preamble (before first H2) is allowed.
9. (Amendment C) Write crossing preamble → first section is rejected.
10. (Amendment E) Hunk with two disjoint change runs in one section passes.
11. (Amendment E) Hunk whose context crosses a boundary but whose edits stay
    in one section passes (the change-run-semantics test).
12. (Amendment E) Pure H2 header insertion is allowed.
13. (Amendment E) Rewrite that deletes an H2 boundary is rejected.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
# check_section_boundary_writes.py lives in the sibling post-skill/ skill directory.
POST_SKILL_DIR = SCRIPTS_DIR.parent / "post-skill"
SCRIPT_PATH = POST_SKILL_DIR / "check_section_boundary_writes.py"

sys.path.insert(0, str(SCRIPTS_DIR))


BASELINE_AS_CODED = """\
# TEMPLATE -- AS-CODED

<!-- maintained-by: Agent (post-skill) -->

> Preamble blockquote line one.
> Preamble blockquote line two.

---

## Conceptual Design

### 1. Platform Purpose

Stub body for platform purpose.

### 2. Entity Hierarchy

Stub body for entity hierarchy.

### 3. Domain Concepts

Stub body for domain concepts.

---

## Metacommunication

### 1. Global Summary

Stub body for global summary.

### 2. EMT

Stub body for EMT.

### 3. Solution Representations

Stub body for solutions.

---

## Journey Maps

### JM-TB-001: First Journey

Stub body for first journey.

### JM-TB-002: Second Journey

Stub body for second journey.

### Delta from As-Intended

Stub delta body.
"""


def _init_git_repo(repo_root: Path) -> None:
    (repo_root / ".claude").mkdir(exist_ok=True)
    (repo_root / ".claude" / ".keep").touch()
    subprocess.run(["git", "init", "-q"], cwd=repo_root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test"], cwd=repo_root, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "test"], cwd=repo_root, check=True
    )


def _commit_baseline(repo_root: Path, rel_path: str, content: str) -> None:
    full_path = repo_root / rel_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo_root, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "baseline"], cwd=repo_root, check=True
    )


def _stage_modification(repo_root: Path, rel_path: str, new_content: str) -> None:
    (repo_root / rel_path).write_text(new_content, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo_root, check=True)


def _stage_new_file(repo_root: Path, rel_path: str, content: str) -> None:
    full_path = repo_root / rel_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo_root, check=True)


def _run_validator(
    repo_root: Path, registry_path: str | None
) -> subprocess.CompletedProcess:
    """Invoke the validator via a runner that monkey-patches the registry.

    If `registry_path` is None, the registry is emptied to exercise the
    no-op branch.
    """
    runner = repo_root / "_runner.py"
    if registry_path is None:
        registry_literal = "{}"
    else:
        registry_literal = "{" + f"{registry_path!r}: None" + "}"
    runner.write_text(
        "import sys\n"
        "from pathlib import Path\n"
        f"sys.path.insert(0, {str(SCRIPTS_DIR)!r})\n"
        f"sys.path.insert(0, {str(POST_SKILL_DIR)!r})\n"
        "import check_section_boundary_writes as mod\n"
        f"mod.REPO_ROOT = Path({str(repo_root)!r})\n"
        f"mod.SECTION_BOUNDARY_FILES = {registry_literal}\n"
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


# ---- Test 1: empty registry -------------------------------------------------


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_empty_registry_warns_and_passes(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    _commit_baseline(tmp_path, "_references/template/product-design-as-coded.md", BASELINE_AS_CODED)

    result = _run_validator(tmp_path, None)
    assert result.returncode == 0, result.stderr
    assert "WARNING" in result.stderr
    assert "no-op" in result.stderr.lower()


# ---- Test 2: edit within single section passes ------------------------------


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_edit_within_single_section_passes(tmp_path: Path) -> None:
    rel = "_references/template/product-design-as-coded.md"
    _init_git_repo(tmp_path)
    _commit_baseline(tmp_path, rel, BASELINE_AS_CODED)

    new_content = BASELINE_AS_CODED.replace(
        "Stub body for platform purpose.",
        "Updated body for platform purpose with more content.",
    )
    _stage_modification(tmp_path, rel, new_content)

    result = _run_validator(tmp_path, rel)
    assert result.returncode == 0, (
        f"expected pass, got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "PASS" in result.stdout


# ---- Test 3: edit crossing two sections rejected ----------------------------


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_edit_crossing_two_sections_rejected(tmp_path: Path) -> None:
    """A contiguous change run that spans Conceptual Design → Metacommunication
    must be rejected.
    """
    rel = "_references/template/product-design-as-coded.md"
    _init_git_repo(tmp_path)
    _commit_baseline(tmp_path, rel, BASELINE_AS_CODED)

    # Replace a contiguous block spanning Conceptual Design → Metacommunication.
    # Every line in the block is modified (including the H2 heading, which is
    # renamed so git cannot reuse it as context), forcing git to emit one
    # large change run that crosses the boundary.
    old_block = (
        "Stub body for domain concepts.\n"
        "\n"
        "---\n"
        "\n"
        "## Metacommunication\n"
        "\n"
        "### 1. Global Summary\n"
        "\n"
        "Stub body for global summary."
    )
    new_block = (
        "Tampered domain concepts content.\n"
        "Extra line in conceptual design.\n"
        "Another extra line that crosses.\n"
        "## Metacommunication RENAMED\n"
        "### 1. Global Summary RENAMED\n"
        "Tampered global summary content."
    )
    assert old_block in BASELINE_AS_CODED
    new_content = BASELINE_AS_CODED.replace(old_block, new_block)
    _stage_modification(tmp_path, rel, new_content)

    result = _run_validator(tmp_path, rel)
    assert result.returncode == 1, (
        f"expected fail, got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "FAIL" in result.stderr
    assert "section-boundary" in result.stderr.lower()


# ---- Test 4: two separate edits in different sections pass ------------------


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_two_separate_edits_in_different_sections_pass(tmp_path: Path) -> None:
    rel = "_references/template/product-design-as-coded.md"
    _init_git_repo(tmp_path)
    _commit_baseline(tmp_path, rel, BASELINE_AS_CODED)

    new_content = BASELINE_AS_CODED.replace(
        "Stub body for platform purpose.",
        "Edited platform purpose.",
    ).replace(
        "Stub body for global summary.",
        "Edited global summary.",
    )
    _stage_modification(tmp_path, rel, new_content)

    result = _run_validator(tmp_path, rel)
    assert result.returncode == 0, (
        f"expected pass, got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "PASS" in result.stdout


# ---- Test 5: new file in diff silently passes -------------------------------


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_new_file_in_diff_silently_passes(tmp_path: Path) -> None:
    rel = "_references/template/product-design-as-coded.md"
    _init_git_repo(tmp_path)
    # Commit a baseline that does NOT include the target file
    (tmp_path / "placeholder.txt").write_text("placeholder\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "placeholder"], cwd=tmp_path, check=True
    )

    # Stage the target file as new
    _stage_new_file(tmp_path, rel, BASELINE_AS_CODED)

    result = _run_validator(tmp_path, rel)
    assert result.returncode == 0, (
        f"expected silent pass, got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "PASS" in result.stdout


# ---- Test 6: file not in registry ignored -----------------------------------


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_file_not_in_registry_ignored(tmp_path: Path) -> None:
    """A registered path is set, but the staged change touches a DIFFERENT file."""
    registered = "_references/template/product-design-as-coded.md"
    touched = "_references/template/other.md"
    _init_git_repo(tmp_path)
    _commit_baseline(tmp_path, touched, "# other\n\n## A\n\ncontent\n\n## B\n\ncontent\n")

    new_content = "# other\n\n## A\n\nupdated\n\n## B\n\nother update\n"
    _stage_modification(tmp_path, touched, new_content)

    result = _run_validator(tmp_path, registered)
    assert result.returncode == 0, (
        f"expected pass (unregistered file ignored), got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


# ---- Test 7: append at EOF inside last section passes -----------------------


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_append_to_last_section_passes(tmp_path: Path) -> None:
    rel = "_references/template/product-design-as-coded.md"
    _init_git_repo(tmp_path)
    _commit_baseline(tmp_path, rel, BASELINE_AS_CODED)

    new_content = BASELINE_AS_CODED + "\nExtra appended line inside Journey Maps delta.\n"
    _stage_modification(tmp_path, rel, new_content)

    result = _run_validator(tmp_path, rel)
    assert result.returncode == 0, (
        f"expected pass, got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


# ---- Test 8 (Amendment C): insertion within preamble allowed ----------------


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_insertion_within_preamble_allowed(tmp_path: Path) -> None:
    rel = "_references/template/product-design-as-coded.md"
    _init_git_repo(tmp_path)
    _commit_baseline(tmp_path, rel, BASELINE_AS_CODED)

    # Update the maintained-by comment line -- all preamble.
    new_content = BASELINE_AS_CODED.replace(
        "<!-- maintained-by: Agent (post-skill) -->",
        "<!-- maintained-by: Agent (post-skill); since SEJA 2.8.4 -->",
    )
    _stage_modification(tmp_path, rel, new_content)

    result = _run_validator(tmp_path, rel)
    assert result.returncode == 0, (
        f"expected pass, got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


# ---- Test 9 (Amendment C): preamble → first section crossing rejected -------


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_write_crossing_preamble_to_first_section_rejected(tmp_path: Path) -> None:
    rel = "_references/template/product-design-as-coded.md"
    _init_git_repo(tmp_path)
    _commit_baseline(tmp_path, rel, BASELINE_AS_CODED)

    # Build a single contiguous change run that spans from preamble lines
    # into the first H2 section body. Every line in the block is modified
    # (including the H2 and H3 headings, which are renamed so git cannot
    # reuse them as context).
    old_block = (
        "> Preamble blockquote line one.\n"
        "> Preamble blockquote line two.\n"
        "\n"
        "---\n"
        "\n"
        "## Conceptual Design\n"
        "\n"
        "### 1. Platform Purpose\n"
        "\n"
        "Stub body for platform purpose."
    )
    new_block = (
        "> Edited preamble line one.\n"
        "> Edited preamble line two.\n"
        "> Extra preamble line three.\n"
        "## Conceptual Design RENAMED\n"
        "### 1. Platform Purpose RENAMED\n"
        "Edited body for platform purpose."
    )
    assert old_block in BASELINE_AS_CODED
    new_content = BASELINE_AS_CODED.replace(old_block, new_block)
    _stage_modification(tmp_path, rel, new_content)

    result = _run_validator(tmp_path, rel)
    assert result.returncode == 1, (
        f"expected fail, got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "FAIL" in result.stderr


# ---- Test 10 (Amendment E): hunk with two disjoint change runs in same section


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_hunk_with_disjoint_change_runs_in_same_section_passes(
    tmp_path: Path,
) -> None:
    """Two edits in one H2 section, close enough that git folds them into one
    hunk (separated by context lines). Both runs stay inside Conceptual Design.
    """
    rel = "_references/template/product-design-as-coded.md"
    _init_git_repo(tmp_path)
    _commit_baseline(tmp_path, rel, BASELINE_AS_CODED)

    new_content = BASELINE_AS_CODED.replace(
        "Stub body for platform purpose.",
        "Edited platform purpose body.",
    ).replace(
        "Stub body for entity hierarchy.",
        "Edited entity hierarchy body.",
    )
    _stage_modification(tmp_path, rel, new_content)

    result = _run_validator(tmp_path, rel)
    assert result.returncode == 0, (
        f"expected pass, got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


# ---- Test 11 (Amendment E): hunk with context crossing boundary but edits
#      in one section ---------------------------------------------------------


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_hunk_with_context_crossing_boundary_but_edits_in_one_section_passes(
    tmp_path: Path,
) -> None:
    """Two edits that git may pack into a single hunk whose full span (including
    context) reaches across the Conceptual Design / Metacommunication boundary.
    Each change run is confined to one section, so the validator must accept
    the hunk (Amendment A change-run semantics).
    """
    rel = "_references/template/product-design-as-coded.md"
    _init_git_repo(tmp_path)
    _commit_baseline(tmp_path, rel, BASELINE_AS_CODED)

    new_content = BASELINE_AS_CODED.replace(
        "Stub body for domain concepts.",
        "Edited domain concepts body.",
    ).replace(
        "Stub body for global summary.",
        "Edited global summary body.",
    )
    _stage_modification(tmp_path, rel, new_content)

    # Confirm for debugging that both changes are within their respective
    # sections (no boundary crossing in any change run).
    result = _run_validator(tmp_path, rel)
    assert result.returncode == 0, (
        f"expected pass (change-run semantics), got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


# ---- Test 12 (Amendment E): pure H2 header insertion allowed ----------------


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_h2_header_insertion_allowed(tmp_path: Path) -> None:
    """Inserting a fresh `## New Section` heading line is allowed."""
    rel = "_references/template/product-design-as-coded.md"
    _init_git_repo(tmp_path)
    _commit_baseline(tmp_path, rel, BASELINE_AS_CODED)

    # Insert a brand-new H2 at the very end of the file.
    new_content = BASELINE_AS_CODED + "\n## CHANGELOG\n"
    _stage_modification(tmp_path, rel, new_content)

    result = _run_validator(tmp_path, rel)
    assert result.returncode == 0, (
        f"expected pass, got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


# ---- Test 13 (Amendment E): rewrite deleting H2 boundary rejected -----------


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_rewrite_deleting_h2_boundary_rejected(tmp_path: Path) -> None:
    """Removing a `## Metacommunication` heading is a cross-section rewrite
    via H2 deletion — must be rejected.
    """
    rel = "_references/template/product-design-as-coded.md"
    _init_git_repo(tmp_path)
    _commit_baseline(tmp_path, rel, BASELINE_AS_CODED)

    # Delete the Metacommunication H2 heading line and merge the section
    # into the preceding content.
    new_content = BASELINE_AS_CODED.replace(
        "## Metacommunication\n\n### 1. Global Summary\n",
        "### 1. Global Summary\n",
    )
    assert new_content != BASELINE_AS_CODED
    _stage_modification(tmp_path, rel, new_content)

    result = _run_validator(tmp_path, rel)
    assert result.returncode == 1, (
        f"expected fail, got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "FAIL" in result.stderr
