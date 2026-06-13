"""Tests for check_human_markers_only.py."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
SCRIPT_PATH = SCRIPTS_DIR / "check_human_markers_only.py"

sys.path.insert(0, str(SCRIPTS_DIR))

import human_markers_registry  # noqa: E402


MARKER_REL = ".claude/skills/scripts/tests/fixtures/marker_fixture.md"


def _run_with_registry(
    tmp_path: Path,
    diff_file: Path | None,
    *args: str,
    registry: list[str] | None = None,
    allow_test_diff: bool = True,
) -> subprocess.CompletedProcess:
    """Invoke the script via a runner that patches the registry first."""
    (tmp_path / ".claude").mkdir(exist_ok=True)
    runner = tmp_path / "_runner.py"
    reg = registry if registry is not None else [MARKER_REL]
    runner_args = list(args)
    if diff_file is not None:
        runner_args = ["--diff-from-file", str(diff_file), *runner_args]
    runner.write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(SCRIPTS_DIR)!r})\n"
        "import human_markers_registry\n"
        f"human_markers_registry.HUMAN_MARKERS_FILES = {reg!r}\n"
        "import check_human_markers_only\n"
        f"sys.argv = [{str(SCRIPT_PATH)!r}] + {runner_args!r}\n"
        "sys.exit(check_human_markers_only.main())\n",
        encoding="utf-8",
    )
    env = dict(os.environ)
    if allow_test_diff:
        env["SEJA_ALLOW_TEST_DIFF_INPUT"] = "1"
    else:
        env.pop("SEJA_ALLOW_TEST_DIFF_INPUT", None)
    return subprocess.run(
        [sys.executable, str(runner)],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        env=env,
    )


def _write_diff(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "test.diff"
    p.write_text(body, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_empty_registry_warns_and_passes(tmp_path):
    diff = _write_diff(tmp_path, "")
    result = _run_with_registry(tmp_path, diff, registry=[])
    assert result.returncode == 0
    assert "no files in HUMAN_MARKERS_FILES" in result.stderr


def test_no_marker_files_in_diff(tmp_path):
    diff_body = (
        "diff --git a/other.md b/other.md\n"
        "index abc..def 100644\n"
        "--- a/other.md\n"
        "+++ b/other.md\n"
        "@@ -1,1 +1,1 @@\n"
        "-old text\n"
        "+new text\n"
    )
    diff = _write_diff(tmp_path, diff_body)
    result = _run_with_registry(tmp_path, diff)
    assert result.returncode == 0
    assert "PASS" in result.stdout


def test_marker_only_diff(tmp_path):
    diff_body = (
        f"diff --git a/{MARKER_REL} b/{MARKER_REL}\n"
        "index abc..def 100644\n"
        f"--- a/{MARKER_REL}\n"
        f"+++ b/{MARKER_REL}\n"
        "@@ -10,3 +10,3 @@\n"
        "-<!-- STATUS: proposed -->\n"
        "+<!-- STATUS: implemented | plan-000265 | 2026-04-10 -->\n"
        " ### R-P-001: Sample persona one\n"
    )
    diff = _write_diff(tmp_path, diff_body)
    result = _run_with_registry(tmp_path, diff)
    assert result.returncode == 0, result.stderr
    assert "PASS" in result.stdout


def test_prose_mutation_rejected(tmp_path):
    diff_body = (
        f"diff --git a/{MARKER_REL} b/{MARKER_REL}\n"
        f"--- a/{MARKER_REL}\n"
        f"+++ b/{MARKER_REL}\n"
        "@@ -14,1 +14,1 @@\n"
        "-A test persona used to exercise STATUS marker transitions.\n"
        "+A test persona REWRITTEN with prose changes.\n"
    )
    diff = _write_diff(tmp_path, diff_body)
    result = _run_with_registry(tmp_path, diff)
    assert result.returncode == 1
    assert "FAIL" in result.stderr or "violation" in result.stderr
    assert "REWRITTEN" in result.stderr


def test_mixed_diff_reports_prose_only(tmp_path):
    diff_body = (
        f"diff --git a/{MARKER_REL} b/{MARKER_REL}\n"
        f"--- a/{MARKER_REL}\n"
        f"+++ b/{MARKER_REL}\n"
        "@@ -10,4 +10,4 @@\n"
        "-<!-- STATUS: proposed -->\n"
        "+<!-- STATUS: implemented | plan-000265 | 2026-04-10 -->\n"
        "-A test persona used to exercise STATUS marker transitions.\n"
        "+A test persona with rewritten prose.\n"
    )
    diff = _write_diff(tmp_path, diff_body)
    result = _run_with_registry(tmp_path, diff)
    assert result.returncode == 1
    assert "rewritten prose" in result.stderr


def test_changelog_append_only(tmp_path):
    diff_body = (
        f"diff --git a/{MARKER_REL} b/{MARKER_REL}\n"
        f"--- a/{MARKER_REL}\n"
        f"+++ b/{MARKER_REL}\n"
        "@@ -29,2 +29,3 @@\n"
        " 2026-04-10 | R-P-001 | added | - | initial entry for fixture\n"
        " 2026-04-10 | R-P-002 | added | - | initial entry for fixture\n"
        "+2026-04-11 | R-P-001 | revised | plan-000265 | updated persona body\n"
    )
    diff = _write_diff(tmp_path, diff_body)
    result = _run_with_registry(tmp_path, diff)
    assert result.returncode == 0, result.stderr


def test_changelog_historical_line_modified(tmp_path):
    # Modifying an existing changelog line should be rejected (it's a '-' of a
    # line that matches the CHANGELOG regex, but a '+' of a different body is
    # also allowed; the real test is that prose mutation on a changelog line
    # that doesn't match the regex is rejected.
    diff_body = (
        f"diff --git a/{MARKER_REL} b/{MARKER_REL}\n"
        f"--- a/{MARKER_REL}\n"
        f"+++ b/{MARKER_REL}\n"
        "@@ -29,1 +29,1 @@\n"
        "-2026-04-10 | R-P-001 | added | - | initial entry for fixture\n"
        "+vandalized historical line with no structure\n"
    )
    diff = _write_diff(tmp_path, diff_body)
    result = _run_with_registry(tmp_path, diff)
    assert result.returncode == 1
    assert "vandalized" in result.stderr


def test_windows_path_normalization(tmp_path):
    # git diff emits forward slashes even on Windows, so just confirm
    # backslash paths in the diff are normalized.
    backslash_rel = MARKER_REL.replace("/", "\\")
    diff_body = (
        f"diff --git a/{backslash_rel} b/{backslash_rel}\n"
        f"--- a/{backslash_rel}\n"
        f"+++ b/{backslash_rel}\n"
        "@@ -10,1 +10,1 @@\n"
        "-<!-- STATUS: proposed -->\n"
        "+<!-- STATUS: implemented | plan-000265 | 2026-04-10 -->\n"
    )
    diff = _write_diff(tmp_path, diff_body)
    result = _run_with_registry(tmp_path, diff)
    assert result.returncode == 0, result.stderr


def test_diff_from_file_without_env_var_rejected(tmp_path):
    diff = _write_diff(tmp_path, "")
    result = _run_with_registry(tmp_path, diff, allow_test_diff=False)
    assert result.returncode == 2
    assert "SEJA_ALLOW_TEST_DIFF_INPUT" in result.stderr


def test_diff_from_file_with_env_var_allowed(tmp_path):
    diff = _write_diff(tmp_path, "")
    result = _run_with_registry(tmp_path, diff, allow_test_diff=True)
    assert result.returncode == 0
