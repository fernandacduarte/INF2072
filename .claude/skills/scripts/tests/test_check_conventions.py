"""Tests for check_conventions.py — conventions variable validator."""
from pathlib import Path

import pytest

import check_conventions


@pytest.fixture
def fake_conventions(tmp_path):
    """Create a conventions file with known variables."""
    conv = tmp_path / "conventions.md"
    conv.write_text(
        "| Variable | Value | Description |\n"
        "|----------|-------|-------------|\n"
        "| `OUTPUT_DIR` | `_output` | Root output |\n"
        "| `PLANS_DIR` | `${OUTPUT_DIR}/plans` | Plans folder |\n"
        "| `UNUSED_VAR` | `something` | Never referenced |\n",
        encoding="utf-8",
    )
    return conv


@pytest.fixture
def fake_skill(tmp_path):
    """Create a SKILL.md that references some variables."""
    skill_dir = tmp_path / ".claude" / "skills" / "test-skill"
    skill_dir.mkdir(parents=True)
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        "Output folder: `${OUTPUT_DIR}` (see conventions)\n"
        "Plans go to `${PLANS_DIR}`\n"
        "Also references `${MISSING_VAR}` which is undefined\n",
        encoding="utf-8",
    )
    return skill_md


def test_extract_defined_variables(fake_conventions):
    """Should extract variable names from the conventions file."""
    defined = check_conventions.extract_defined_variables(fake_conventions)
    assert "OUTPUT_DIR" in defined
    assert "PLANS_DIR" in defined
    assert "UNUSED_VAR" in defined
    assert len(defined) == 3


def test_scan_references(fake_skill):
    """Should find ${VAR} references with line numbers."""
    refs = check_conventions.scan_references(fake_skill)
    assert "OUTPUT_DIR" in refs
    assert "PLANS_DIR" in refs
    assert "MISSING_VAR" in refs
    assert refs["OUTPUT_DIR"] == [1]
    assert refs["PLANS_DIR"] == [2]
    assert refs["MISSING_VAR"] == [3]


def test_scan_references_empty(tmp_path):
    """File with no references should return empty dict."""
    f = tmp_path / "empty.md"
    f.write_text("No variables here.\n", encoding="utf-8")
    refs = check_conventions.scan_references(f)
    assert refs == {}
