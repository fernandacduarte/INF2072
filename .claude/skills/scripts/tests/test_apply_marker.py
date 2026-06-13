"""Tests for apply_marker.py."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
SCRIPT_PATH = SCRIPTS_DIR / "apply_marker.py"
FIXTURE_SRC = SCRIPTS_DIR / "tests" / "fixtures" / "marker_fixture.md"

# Ensure imports work when patching
sys.path.insert(0, str(SCRIPTS_DIR))

import human_markers_registry  # noqa: E402
import project_config  # noqa: E402


@pytest.fixture
def marker_file(tmp_path, monkeypatch):
    """Copy the marker fixture into a tmp REPO_ROOT layout and register it."""
    # Build a fake repo root: tmp_path/<fake-subdir>/file
    rel = Path(".claude/skills/scripts/tests/fixtures/marker_fixture.md")
    target = tmp_path / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(FIXTURE_SRC, target)

    # Patch REPO_ROOT in both modules that reference it.
    monkeypatch.setattr(project_config, "REPO_ROOT", tmp_path)
    # apply_marker.py imports REPO_ROOT at import time; patch it there too if already imported
    import importlib
    if "apply_marker" in sys.modules:
        importlib.reload(sys.modules["apply_marker"])
    # Patch the registry
    monkeypatch.setattr(
        human_markers_registry,
        "HUMAN_MARKERS_FILES",
        [rel.as_posix()],
    )

    return target, tmp_path, rel.as_posix()


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Invoke the script as a subprocess with a clean PYTHONPATH."""
    env = {
        **_env_base(),
        "PYTHONPATH": str(SCRIPTS_DIR),
    }
    # Pass a runner that monkey-patches the registry + REPO_ROOT on the fly.
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        env=env,
    )


def _env_base() -> dict:
    import os
    return dict(os.environ)


# ---------------------------------------------------------------------------
# Helper: build a subprocess harness that patches registry/REPO_ROOT via a
# small inline runner script. Because the registry is module-level and
# REPO_ROOT is discovered via .claude walkup, we use a fake-repo layout and
# call the script from within that fake repo, using PYTHONPATH to find it.
# ---------------------------------------------------------------------------


def _run_in_fake_repo(
    tmp_path: Path, rel_file: str, *args: str
) -> subprocess.CompletedProcess:
    """Run apply_marker.py inside a fake repo layout at `tmp_path`.

    `tmp_path` must contain a `.claude` dir (for repo-root discovery) and the
    target marker file at `rel_file`. Registry patching happens via a small
    runner script written to tmp_path.
    """
    # Ensure .claude dir exists so REPO_ROOT discovery lands on tmp_path
    (tmp_path / ".claude").mkdir(exist_ok=True)

    runner = tmp_path / "_runner.py"
    runner.write_text(
        "import sys\n"
        "from pathlib import Path\n"
        f"sys.path.insert(0, {str(SCRIPTS_DIR)!r})\n"
        "import project_config\n"
        f"project_config.REPO_ROOT = Path({str(tmp_path)!r})\n"
        "import human_markers_registry\n"
        f"human_markers_registry.HUMAN_MARKERS_FILES = [{rel_file!r}]\n"
        "import apply_marker\n"
        f"apply_marker.REPO_ROOT = Path({str(tmp_path)!r})\n"
        f"sys.argv = [{str(SCRIPT_PATH)!r}] + {list(args)!r}\n"
        "sys.exit(apply_marker.main())\n",
        encoding="utf-8",
    )
    return subprocess.run(
        [sys.executable, str(runner)],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
    )


@pytest.fixture
def fake_repo(tmp_path):
    """Create a fake repo layout with .claude + a marker fixture copy."""
    (tmp_path / ".claude").mkdir()
    rel = ".claude/skills/scripts/tests/fixtures/marker_fixture.md"
    target = tmp_path / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(FIXTURE_SRC, target)
    return tmp_path, rel, target


def _read(target: Path) -> str:
    return target.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_status_proposed_to_implemented(fake_repo):
    tmp, rel, target = fake_repo
    result = _run_in_fake_repo(
        tmp, rel,
        "--file", str(target), "--id", "R-P-001",
        "--marker", "STATUS", "--value", "implemented",
        "--plan", "plan-000265",
    )
    assert result.returncode == 0, result.stderr
    content = _read(target)
    assert "<!-- STATUS: implemented | plan-000265" in content
    # The original proposed marker was replaced (not duplicated)
    assert content.count("STATUS: proposed -->") == 2  # R-P-002 and D-001 still proposed


def test_status_implemented_to_established(fake_repo):
    tmp, rel, target = fake_repo
    # First transition to implemented
    r1 = _run_in_fake_repo(
        tmp, rel,
        "--file", str(target), "--id", "D-001",
        "--marker", "STATUS", "--value", "implemented",
        "--plan", "plan-000265",
    )
    assert r1.returncode == 0, r1.stderr
    # Then to established
    r2 = _run_in_fake_repo(
        tmp, rel,
        "--file", str(target), "--id", "D-001",
        "--marker", "STATUS", "--value", "established",
        "--plan", "plan-000266",
    )
    assert r2.returncode == 0, r2.stderr
    content = _read(target)
    assert "<!-- STATUS: established | plan-000266" in content


def test_status_regression_rejected(fake_repo):
    tmp, rel, target = fake_repo
    # Move D-001 all the way to established first
    _run_in_fake_repo(tmp, rel, "--file", str(target), "--id", "D-001",
                      "--marker", "STATUS", "--value", "implemented",
                      "--plan", "plan-000265")
    _run_in_fake_repo(tmp, rel, "--file", str(target), "--id", "D-001",
                      "--marker", "STATUS", "--value", "established",
                      "--plan", "plan-000266")
    # Try to regress
    result = _run_in_fake_repo(
        tmp, rel,
        "--file", str(target), "--id", "D-001",
        "--marker", "STATUS", "--value", "implemented",
        "--plan", "plan-000267",
    )
    assert result.returncode == 1
    assert "not allowed" in result.stderr


def test_status_flip_replaces_legacy_uppercase_marker(fake_repo):
    """Legacy `STATUS: IMPLEMENTED` is detected and REPLACED (not stacked) on flip.

    Regression test for plan-000268 Amendment A1: apply_marker.py
    `_STATUS_MARKER_RE` was lowercase-only and would silently stack a new marker
    above a legacy uppercase one. The widened regex + `effective_existing`
    normalization in `_apply_status` must now detect and replace the legacy
    marker cleanly.
    """
    tmp, rel, target = fake_repo

    # Seed the fixture: insert a legacy uppercase marker above R-P-001.
    content = target.read_text(encoding="utf-8")
    legacy = "<!-- STATUS: IMPLEMENTED | plan-000260 | 2026-01-15 -->"
    content = content.replace(
        "<!-- STATUS: proposed -->\n### R-P-001:",
        f"{legacy}\n### R-P-001:",
    )
    target.write_text(content, encoding="utf-8")

    # Verify the seed took effect (sanity check before the actual test logic).
    assert legacy in target.read_text(encoding="utf-8")

    # Flip from legacy IMPLEMENTED -> established via apply_marker.
    result = _run_in_fake_repo(
        tmp, rel,
        "--file", str(target), "--id", "R-P-001",
        "--marker", "STATUS", "--value", "established",
        "--plan", "plan-000268",
    )
    assert result.returncode == 0, (
        f"expected legacy flip to succeed, got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )

    # Assert exactly one STATUS marker remains above R-P-001, and it is the
    # new lowercase form. The legacy marker must be REPLACED, not stacked.
    new_content = target.read_text(encoding="utf-8")
    assert legacy not in new_content, "legacy uppercase marker should have been replaced"
    assert "STATUS: established" in new_content, "new lowercase marker should be present"
    # Count STATUS lines immediately above the R-P-001 heading.
    lines = new_content.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("### R-P-001"):
            prev = lines[i - 1] if i > 0 else ""
            prev_prev = lines[i - 2] if i > 1 else ""
            assert prev.startswith("<!-- STATUS: established"), (
                f"expected lowercase marker on line above heading, got {prev!r}"
            )
            # Two STATUS markers stacked would mean prev_prev also starts with STATUS
            assert not prev_prev.startswith("<!-- STATUS:"), (
                f"STATUS markers stacked (not replaced): prev_prev={prev_prev!r}"
            )
            break
    else:
        pytest.fail("R-P-001 heading not found in modified file")


def test_established_stamp(fake_repo):
    tmp, rel, target = fake_repo
    result = _run_in_fake_repo(
        tmp, rel,
        "--file", str(target), "--id", "R-P-001",
        "--marker", "ESTABLISHED", "--value", "-",
        "--plan", "plan-000265",
    )
    assert result.returncode == 0, result.stderr
    content = _read(target)
    assert "<!-- ESTABLISHED: plan-000265" in content


def test_incorporated_stamp(fake_repo):
    tmp, rel, target = fake_repo
    result = _run_in_fake_repo(
        tmp, rel,
        "--file", str(target), "--id", "D-001",
        "--marker", "INCORPORATED", "--value", "-",
        "--plan", "plan-000265",
    )
    assert result.returncode == 0, result.stderr
    content = _read(target)
    assert "<!-- INCORPORATED: plan-000265" in content


def test_changelog_append(fake_repo):
    tmp, rel, target = fake_repo
    original = _read(target)
    # Count existing changelog lines
    original_lines = original.count("| added | -")
    result = _run_in_fake_repo(
        tmp, rel,
        "--file", str(target), "--id", "R-P-001",
        "--marker", "CHANGELOG_APPEND", "--value", "revised",
        "--plan", "plan-000265", "--note", "updated persona body",
    )
    assert result.returncode == 0, result.stderr
    content = _read(target)
    assert "| revised | plan-000265 | updated persona body" in content
    # Existing lines preserved
    assert content.count("| added | -") == original_lines


def test_file_not_in_registry(fake_repo):
    tmp, rel, target = fake_repo
    # Create a second file NOT in the registry
    other = tmp / "not_registered.md"
    other.write_text("# not registered\n\n### X-001:\n", encoding="utf-8")
    result = _run_in_fake_repo(
        tmp, rel,
        "--file", str(other), "--id", "X-001",
        "--marker", "STATUS", "--value", "implemented",
        "--plan", "plan-000265",
    )
    assert result.returncode == 1
    assert "not classified as Human (markers)" in result.stderr


def test_unknown_marker_kind(fake_repo):
    tmp, rel, target = fake_repo
    result = _run_in_fake_repo(
        tmp, rel,
        "--file", str(target), "--id", "R-P-001",
        "--marker", "WHATEVER", "--value", "x",
    )
    # argparse choices will fail
    assert result.returncode != 0
    assert "WHATEVER" in (result.stderr + result.stdout)


def test_value_not_allowed(fake_repo):
    tmp, rel, target = fake_repo
    result = _run_in_fake_repo(
        tmp, rel,
        "--file", str(target), "--id", "R-P-001",
        "--marker", "STATUS", "--value", "not-a-real-status",
        "--plan", "plan-000265",
    )
    assert result.returncode == 1
    assert "not in allowed_values" in result.stderr


def test_entry_id_not_found(fake_repo):
    tmp, rel, target = fake_repo
    result = _run_in_fake_repo(
        tmp, rel,
        "--file", str(target), "--id", "ZZZ-999",
        "--marker", "STATUS", "--value", "implemented",
        "--plan", "plan-000265",
    )
    assert result.returncode == 1
    assert "not found" in result.stderr


def test_entry_id_ambiguous(fake_repo):
    tmp, rel, target = fake_repo
    # Inject a duplicate heading
    content = target.read_text(encoding="utf-8")
    content += "\n<!-- STATUS: proposed -->\n### R-P-001: Duplicate\n\nBody.\n"
    target.write_text(content, encoding="utf-8")
    result = _run_in_fake_repo(
        tmp, rel,
        "--file", str(target), "--id", "R-P-001",
        "--marker", "STATUS", "--value", "implemented",
        "--plan", "plan-000265",
    )
    assert result.returncode == 1
    assert "ambiguous" in result.stderr


def test_dry_run_no_mutation(fake_repo):
    tmp, rel, target = fake_repo
    before = _read(target)
    result = _run_in_fake_repo(
        tmp, rel,
        "--file", str(target), "--id", "R-P-001",
        "--marker", "STATUS", "--value", "implemented",
        "--plan", "plan-000265", "--dry-run",
    )
    assert result.returncode == 0, result.stderr
    after = _read(target)
    assert before == after
    # Diff was printed
    assert "+<!-- STATUS: implemented" in result.stdout


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="symlink creation requires admin on Windows",
)
def test_symlink_to_marker_file_rejected(fake_repo):
    tmp, rel, target = fake_repo
    link = tmp / "link_to_marker.md"
    link.symlink_to(target)
    result = _run_in_fake_repo(
        tmp, rel,
        "--file", str(link), "--id", "R-P-001",
        "--marker", "STATUS", "--value", "implemented",
        "--plan", "plan-000265",
    )
    # The resolved path of the symlink matches the registered file, so the
    # resolve()+relative_to() dance should accept it. To actually test
    # rejection of non-registered canonical paths via symlinks, point the
    # symlink at a file outside the registry.
    # Instead: create a non-registered file and symlink it
    other = tmp / "other.md"
    other.write_text("# other\n\n<!-- STATUS: proposed -->\n### R-P-001:\n", encoding="utf-8")
    link2 = tmp / "link2.md"
    link2.unlink(missing_ok=True) if hasattr(link2, "unlink") else None
    link2.symlink_to(other)
    result2 = _run_in_fake_repo(
        tmp, rel,
        "--file", str(link2), "--id", "R-P-001",
        "--marker", "STATUS", "--value", "implemented",
        "--plan", "plan-000265",
    )
    assert result2.returncode == 1
    assert "not classified" in result2.stderr


def test_changelog_note_rejects_html_comment(fake_repo):
    tmp, rel, target = fake_repo
    result = _run_in_fake_repo(
        tmp, rel,
        "--file", str(target), "--id", "R-P-001",
        "--marker", "CHANGELOG_APPEND", "--value", "revised",
        "--plan", "plan-000265", "--note", "<!-- malicious -->",
    )
    assert result.returncode == 1
    assert "does not match allowed regex" in result.stderr


# ---------------------------------------------------------------------------
# proposal-000270 -- UX polish: --value optional for stamp kinds, --plan
# auto-prefix for bare 6-digit ids, clear errors on the remaining error paths.
# ---------------------------------------------------------------------------


def test_incorporated_marker_without_value_arg_succeeds(fake_repo):
    """INCORPORATED is a stamp-kind marker; --value is ignored and must not
    be required at the argparse layer. Before proposal-000270 this failed with
    `error: the following arguments are required: --value`.
    """
    tmp, rel, target = fake_repo
    result = _run_in_fake_repo(
        tmp, rel,
        "--file", str(target), "--id", "D-001",
        "--marker", "INCORPORATED",
        "--plan", "plan-000265",
    )
    assert result.returncode == 0, (
        f"expected success, got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    content = _read(target)
    assert "<!-- INCORPORATED: plan-000265" in content


def test_established_stamp_without_value_arg_succeeds(fake_repo):
    """ESTABLISHED is a stamp-kind marker; --value is ignored and must not
    be required at the argparse layer.
    """
    tmp, rel, target = fake_repo
    result = _run_in_fake_repo(
        tmp, rel,
        "--file", str(target), "--id", "R-P-001",
        "--marker", "ESTABLISHED",
        "--plan", "plan-000265",
    )
    assert result.returncode == 0, (
        f"expected success, got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    content = _read(target)
    assert "<!-- ESTABLISHED: plan-000265" in content


def test_status_without_value_arg_raises_clear_error(fake_repo):
    """STATUS requires --value. Without it, the post-parse validation must
    emit a clear error message referencing STATUS + --value, not an opaque
    argparse error or a NoneType crash downstream.
    """
    tmp, rel, target = fake_repo
    result = _run_in_fake_repo(
        tmp, rel,
        "--file", str(target), "--id", "R-P-001",
        "--marker", "STATUS",
        "--plan", "plan-000265",
    )
    assert result.returncode == 1, (
        f"expected exit 1, got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "STATUS requires --value" in result.stderr


def test_plan_bare_six_digit_id_is_prefixed(fake_repo):
    """--plan 000265 must be auto-prefixed to plan-000265 before the marker
    regex validation runs. Previously this failed with an opaque
    `INCORPORATED line does not match allowed regex` error.
    """
    tmp, rel, target = fake_repo
    result = _run_in_fake_repo(
        tmp, rel,
        "--file", str(target), "--id", "D-001",
        "--marker", "INCORPORATED",
        "--plan", "000265",
    )
    assert result.returncode == 0, (
        f"expected success, got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    content = _read(target)
    assert "<!-- INCORPORATED: plan-000265" in content


def test_plan_already_prefixed_passes_through(fake_repo):
    """--plan plan-000265 must pass through the normalizer unchanged. This
    is the backward-compatibility path for existing invocations.
    """
    tmp, rel, target = fake_repo
    result = _run_in_fake_repo(
        tmp, rel,
        "--file", str(target), "--id", "D-001",
        "--marker", "INCORPORATED",
        "--plan", "plan-000265",
    )
    assert result.returncode == 0, (
        f"expected success, got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    content = _read(target)
    assert "<!-- INCORPORATED: plan-000265" in content


# ---------------------------------------------------------------------------
# DECISION_APPEND tests (plan-000322)
# ---------------------------------------------------------------------------


def test_decision_append_creates_next_id(fake_repo):
    """DECISION_APPEND auto-assigns the next D-NNN ID after existing entries."""
    tmp, rel, target = fake_repo
    value = "Adopt event sourcing\n\n**Context**: Need audit trail.\n**Decision**: Use event sourcing."
    result = _run_in_fake_repo(
        tmp, rel,
        "--file", str(target), "--id", "D-NEXT",
        "--marker", "DECISION_APPEND", "--value", value,
        "--plan", "manual", "--note", "from advisory-000311",
    )
    assert result.returncode == 0, (
        f"expected success, got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    content = _read(target)
    # Fixture has D-001 (Entries) and D-002 (Decisions), so next should be D-003
    assert "### D-003: Adopt event sourcing" in content
    assert "**Context**: Need audit trail." in content
    assert "from advisory-000311" in content
    # Original D-001 is still present
    assert "### D-001:" in content


def test_decision_append_first_entry(fake_repo):
    """DECISION_APPEND assigns D-001 when no existing decisions exist."""
    tmp, rel, target = fake_repo
    # Remove the existing D-001 entry from the fixture
    content = target.read_text(encoding="utf-8")
    # Remove everything between ## Decisions and ## CHANGELOG, keeping both headings
    import re as _re
    content = _re.sub(
        r"(## Decisions)\n.*?(## CHANGELOG)",
        r"\1\n\n\2",
        content,
        flags=_re.DOTALL,
    )
    target.write_text(content, encoding="utf-8")

    value = "First decision\n\n**Context**: Starting fresh."
    result = _run_in_fake_repo(
        tmp, rel,
        "--file", str(target), "--id", "D-NEXT",
        "--marker", "DECISION_APPEND", "--value", value,
        "--plan", "manual",
    )
    assert result.returncode == 0, result.stderr
    content = _read(target)
    assert "### D-001: First decision" in content


def test_decision_append_no_decisions_section_fails(fake_repo):
    """DECISION_APPEND fails when the file has no ## Decisions section."""
    tmp, rel, target = fake_repo
    # Remove the ## Decisions section entirely
    content = target.read_text(encoding="utf-8")
    content = content.replace("## Decisions", "## Other")
    target.write_text(content, encoding="utf-8")

    result = _run_in_fake_repo(
        tmp, rel,
        "--file", str(target), "--id", "D-NEXT",
        "--marker", "DECISION_APPEND", "--value", "Title\n\nBody",
        "--plan", "manual",
    )
    assert result.returncode == 1
    assert "no '## Decisions' section" in result.stderr


def test_decision_append_empty_value_fails(fake_repo):
    """DECISION_APPEND with empty --value fails with a clear error."""
    tmp, rel, target = fake_repo
    result = _run_in_fake_repo(
        tmp, rel,
        "--file", str(target), "--id", "D-NEXT",
        "--marker", "DECISION_APPEND", "--value", "  ",
        "--plan", "manual",
    )
    assert result.returncode == 1
    assert "must not be empty" in result.stderr


def test_decision_append_dry_run(fake_repo):
    """DECISION_APPEND with --dry-run prints diff without writing."""
    tmp, rel, target = fake_repo
    before = _read(target)
    value = "Dry run decision\n\n**Context**: Testing."
    result = _run_in_fake_repo(
        tmp, rel,
        "--file", str(target), "--id", "D-NEXT",
        "--marker", "DECISION_APPEND", "--value", value,
        "--plan", "manual", "--dry-run",
    )
    assert result.returncode == 0, result.stderr
    after = _read(target)
    assert before == after
    assert "+### D-003: Dry run decision" in result.stdout


def test_plan_invalid_form_raises_clear_error(fake_repo):
    """Any --plan value that is neither 'plan-NNNNNN' nor a bare 6-digit
    id must raise a clear error referencing the accepted forms, not an
    opaque regex mismatch.
    """
    tmp, rel, target = fake_repo
    result = _run_in_fake_repo(
        tmp, rel,
        "--file", str(target), "--id", "D-001",
        "--marker", "INCORPORATED",
        "--plan", "invalid",
    )
    assert result.returncode == 1, (
        f"expected exit 1, got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "--plan must be 'plan-NNNNNN'" in result.stderr
