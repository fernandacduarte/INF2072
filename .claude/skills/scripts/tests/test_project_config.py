"""Tests for project_config.py — central configuration module."""
import importlib
from pathlib import Path

import pytest


@pytest.fixture
def fake_repo(tmp_path):
    """Create a minimal repo structure with .claude/ and template/conventions.md."""
    (tmp_path / ".claude").mkdir()
    (tmp_path / "_references" / "template").mkdir(parents=True)
    conventions = tmp_path / "_references" / "template" / "conventions.md"
    conventions.write_text(
        "# TEMPLATE - PROJECT CONVENTIONS\n\n"
        "| Variable | Value | Description |\n"
        "|----------|-------|-------------|\n"
        "| `OUTPUT_DIR` | `_output` | Root output |\n"
        "| `PLANS_DIR` | `${OUTPUT_DIR}/plans` | Plans folder |\n"
        "| `SCRIPTS_DIR` | `${OUTPUT_DIR}/generated-scripts` | Scripts folder |\n",
        encoding="utf-8",
    )
    return tmp_path


def test_parse_config_extracts_variables(fake_repo):
    """project_config._parse_config should extract and resolve variables."""
    import project_config

    # Monkeypatch REPO_ROOT and reset cache
    original_root = project_config.REPO_ROOT
    original_config = project_config._config
    try:
        project_config.REPO_ROOT = fake_repo
        project_config._config = None
        project_config._warned_missing = False

        config = project_config._parse_config()
        assert "OUTPUT_DIR" in config
        assert config["OUTPUT_DIR"] == "_output"
        assert config["PLANS_DIR"] == "_output/plans"
        assert config["SCRIPTS_DIR"] == "_output/generated-scripts"
    finally:
        project_config.REPO_ROOT = original_root
        project_config._config = original_config


def test_get_returns_value(fake_repo):
    """get() should return the resolved value for a known key."""
    import project_config

    original_root = project_config.REPO_ROOT
    original_config = project_config._config
    try:
        project_config.REPO_ROOT = fake_repo
        project_config._config = None
        project_config._warned_missing = False

        assert project_config.get("OUTPUT_DIR") == "_output"
        assert project_config.get("NONEXISTENT") is None
        assert project_config.get("NONEXISTENT", "fallback") == "fallback"
    finally:
        project_config.REPO_ROOT = original_root
        project_config._config = original_config


def test_get_path_returns_absolute(fake_repo):
    """get_path() should return a Path relative to REPO_ROOT."""
    import project_config

    original_root = project_config.REPO_ROOT
    original_config = project_config._config
    try:
        project_config.REPO_ROOT = fake_repo
        project_config._config = None
        project_config._warned_missing = False

        result = project_config.get_path("OUTPUT_DIR")
        assert result == fake_repo / "_output"
    finally:
        project_config.REPO_ROOT = original_root
        project_config._config = original_config


def test_missing_conventions_returns_empty(tmp_path):
    """When neither conventions file exists, config should be empty."""
    import project_config

    original_root = project_config.REPO_ROOT
    original_config = project_config._config
    try:
        project_config.REPO_ROOT = tmp_path
        project_config._config = None
        project_config._warned_missing = False

        config = project_config._parse_config()
        assert config == {}
    finally:
        project_config.REPO_ROOT = original_root
        project_config._config = original_config


def test_diff_conventions(tmp_path):
    """diff_conventions should detect differences between two files."""
    import project_config

    project = tmp_path / "project.md"
    template = tmp_path / "template.md"

    project.write_text(
        "| `VAR_A` | `value1` | desc |\n"
        "| `VAR_B` | `changed` | desc |\n",
        encoding="utf-8",
    )
    template.write_text(
        "| `VAR_A` | `value1` | desc |\n"
        "| `VAR_B` | `original` | desc |\n"
        "| `VAR_C` | `new` | desc |\n",
        encoding="utf-8",
    )

    diff = project_config.diff_conventions(project, template)
    assert "VAR_C" in diff["missing_in_project"]
    assert len(diff["extra_in_project"]) == 0
    assert len(diff["value_differences"]) == 1
    assert diff["value_differences"][0]["key"] == "VAR_B"
