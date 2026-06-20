"""Tests for check_design_output.py -- design output validation scanners."""
from pathlib import Path
from unittest.mock import patch

import pytest

from check_design_output import (
    Finding,
    run_plugins,
    _PLUGINS,
    plugin_placeholder,
    plugin_phrasing_rule,
    plugin_cross_file_consistency,
    plugin_field_presence,
    plugin_value_propagation,
    _check_phrasing_line,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_project_dir(tmp_path):
    """Create the product-design/ and .claude/ dirs under tmp_path."""
    project_dir = tmp_path / "product-design"
    project_dir.mkdir(parents=True)
    (tmp_path / ".claude").mkdir(exist_ok=True)
    return project_dir


# ---------------------------------------------------------------------------
# 1. Placeholder scanner
# ---------------------------------------------------------------------------

class TestPlaceholderScanner:

    def test_finds_unsubstituted_placeholder(self, tmp_path):
        project_dir = _make_project_dir(tmp_path)
        (project_dir / "overview.md").write_text(
            "Welcome to {{FOO}} project.\n", encoding="utf-8"
        )
        findings = plugin_placeholder(tmp_path, verbose=False)
        assert len(findings) == 1
        assert findings[0].severity == "error"
        assert "{{FOO}}" in findings[0].message

    def test_clean_file_passes(self, tmp_path):
        project_dir = _make_project_dir(tmp_path)
        (project_dir / "overview.md").write_text(
            "Welcome to MyApp project.\n", encoding="utf-8"
        )
        findings = plugin_placeholder(tmp_path, verbose=False)
        assert findings == []

    def test_conventions_md_skipped(self, tmp_path):
        project_dir = _make_project_dir(tmp_path)
        (project_dir / "conventions.md").write_text(
            "| `PROJECT_NAME` | `{{PROJECT_NAME}}` | Name |\n", encoding="utf-8"
        )
        findings = plugin_placeholder(tmp_path, verbose=False)
        assert findings == []


# ---------------------------------------------------------------------------
# 2. Phrasing rule scanner
# ---------------------------------------------------------------------------

class TestPhrasingRuleScanner:

    def test_third_person_flagged(self):
        findings: list[Finding] = []
        _check_phrasing_line(findings, "the designer provides a toolbar", 1, "f.md")
        assert len(findings) >= 1
        assert any("Third-person" in f.message for f in findings)

    def test_first_person_passes(self):
        findings: list[Finding] = []
        _check_phrasing_line(findings, "I designed for you", 1, "f.md")
        assert findings == []

    def test_passive_voice_flagged(self):
        findings: list[Finding] = []
        _check_phrasing_line(findings, "A menu is provided for navigation", 1, "f.md")
        assert len(findings) >= 1
        assert any("Passive voice" in f.message for f in findings)

    def test_imperative_mood_flagged(self):
        findings: list[Finding] = []
        _check_phrasing_line(findings, "Enforce consistent spacing", 1, "f.md")
        assert len(findings) >= 1
        assert any("Imperative mood" in f.message for f in findings)

    def test_part_i_content_skipped(self, tmp_path):
        """Only Part II of product-design-as-intended.md is scanned."""
        project_dir = _make_project_dir(tmp_path)
        ditb = project_dir / "product-design-as-intended.md"
        ditb.write_text(
            "# Part I -- System Design\n"
            "The designer provides a grid layout.\n"
            "\n"
            "## 11. Metacommunication\n"
            "I offer you a sidebar.\n",
            encoding="utf-8",
        )
        findings = plugin_phrasing_rule(tmp_path, verbose=False)
        # Part I line with "the designer" should NOT be flagged;
        # Part II is clean ("I offer you") so no findings expected
        assert not any(
            "the designer" in f.message.lower() and f.line == 2
            for f in findings
        )


# ---------------------------------------------------------------------------
# 3. Cross-file consistency scanner
# ---------------------------------------------------------------------------

class TestCrossFileConsistencyScanner:

    @patch("check_design_output.sys")
    def test_consistent_name_passes(self, mock_sys, tmp_path):
        project_dir = _make_project_dir(tmp_path)
        (project_dir / "overview.md").write_text(
            "Welcome to MyApp.\n", encoding="utf-8"
        )
        with patch.dict("sys.modules", {"project_config": type("M", (), {"get": staticmethod(lambda k: "MyApp" if k == "PROJECT_NAME" else None)})}):
            findings = plugin_cross_file_consistency(tmp_path, verbose=False)
        assert findings == []

    @patch("check_design_output.sys")
    def test_literal_project_name_flagged(self, mock_sys, tmp_path):
        project_dir = _make_project_dir(tmp_path)
        (project_dir / "overview.md").write_text(
            "Welcome to PROJECT_NAME.\n", encoding="utf-8"
        )
        with patch.dict("sys.modules", {"project_config": type("M", (), {"get": staticmethod(lambda k: "MyApp" if k == "PROJECT_NAME" else None)})}):
            findings = plugin_cross_file_consistency(tmp_path, verbose=False)
        assert len(findings) >= 1
        assert findings[0].severity == "error"
        assert "PROJECT_NAME" in findings[0].message


# ---------------------------------------------------------------------------
# 4. Field presence scanner
# ---------------------------------------------------------------------------

class TestFieldPresenceScanner:

    def test_template_placeholder_warns(self, tmp_path):
        project_dir = _make_project_dir(tmp_path)
        (project_dir / "conventions.md").write_text(
            "| `PROJECT_NAME` | `{{PROJECT_NAME}}` | Name |\n"
            "| `PROJECT_DESCRIPTION` | `My project` | Desc |\n"
            "| `BACKEND_DIR` | `backend` | Dir |\n"
            "| `FRONTEND_DIR` | `frontend` | Dir |\n"
            "| `BACKEND_FRAMEWORK` | `Django` | FW |\n"
            "| `FRONTEND_FRAMEWORK` | `React` | FW |\n",
            encoding="utf-8",
        )
        findings = plugin_field_presence(tmp_path, verbose=False)
        assert len(findings) == 1
        assert findings[0].severity == "warning"
        assert "PROJECT_NAME" in findings[0].message

    def test_all_fields_filled_passes(self, tmp_path):
        project_dir = _make_project_dir(tmp_path)
        (project_dir / "conventions.md").write_text(
            "| `PROJECT_NAME` | `MyApp` | Name |\n"
            "| `PROJECT_DESCRIPTION` | `My project` | Desc |\n"
            "| `BACKEND_DIR` | `backend` | Dir |\n"
            "| `FRONTEND_DIR` | `frontend` | Dir |\n"
            "| `BACKEND_FRAMEWORK` | `Django` | FW |\n"
            "| `FRONTEND_FRAMEWORK` | `React` | FW |\n",
            encoding="utf-8",
        )
        findings = plugin_field_presence(tmp_path, verbose=False)
        assert findings == []


# ---------------------------------------------------------------------------
# 5. Value propagation scanner
# ---------------------------------------------------------------------------

class TestValuePropagationScanner:

    def test_matching_backend_framework_passes(self, tmp_path):
        """Unified standards.md: backend framework mentioned in Backend section passes."""
        project_dir = _make_project_dir(tmp_path)
        (project_dir / "conventions.md").write_text(
            "| `BACKEND_FRAMEWORK` | `Django` | FW |\n", encoding="utf-8"
        )
        (project_dir / "standards.md").write_text(
            "# Engineering Standards\n\n## Backend\n\nUse Django REST framework.\n\n## Frontend\n\nReact.\n",
            encoding="utf-8",
        )
        with patch.dict("sys.modules", {"project_config": type("M", (), {"get": staticmethod(lambda k: {"BACKEND_FRAMEWORK": "Django", "FRONTEND_FRAMEWORK": None}.get(k))})}):
            findings = plugin_value_propagation(tmp_path, verbose=False)
        assert findings == []

    def test_mismatching_backend_framework_warns(self, tmp_path):
        """Unified standards.md: backend framework missing from Backend section produces a warning."""
        project_dir = _make_project_dir(tmp_path)
        (project_dir / "conventions.md").write_text(
            "| `BACKEND_FRAMEWORK` | `Django` | FW |\n", encoding="utf-8"
        )
        (project_dir / "standards.md").write_text(
            "# Engineering Standards\n\n## Backend\n\nUse Flask for APIs.\n\n## Frontend\n\nReact.\n",
            encoding="utf-8",
        )
        with patch.dict("sys.modules", {"project_config": type("M", (), {"get": staticmethod(lambda k: {"BACKEND_FRAMEWORK": "Django", "FRONTEND_FRAMEWORK": None}.get(k))})}):
            findings = plugin_value_propagation(tmp_path, verbose=False)
        assert len(findings) == 1
        assert findings[0].severity == "warning"
        assert "Django" in findings[0].message

    def test_backend_framework_in_wrong_section_still_warns(self, tmp_path):
        """Cross-section contamination: Django mentioned only in Frontend section must still warn."""
        project_dir = _make_project_dir(tmp_path)
        (project_dir / "conventions.md").write_text(
            "| `BACKEND_FRAMEWORK` | `Django` | FW |\n", encoding="utf-8"
        )
        (project_dir / "standards.md").write_text(
            "# Engineering Standards\n\n## Backend\n\nNo framework named here.\n\n"
            "## Frontend\n\nDjango REST endpoints are consumed by React via fetch().\n",
            encoding="utf-8",
        )
        with patch.dict("sys.modules", {"project_config": type("M", (), {"get": staticmethod(lambda k: {"BACKEND_FRAMEWORK": "Django", "FRONTEND_FRAMEWORK": None}.get(k))})}):
            findings = plugin_value_propagation(tmp_path, verbose=False)
        assert len(findings) == 1, f"expected 1 warning, got {findings}"
        assert findings[0].severity == "warning"
        assert "Django" in findings[0].message
        assert "Backend" in findings[0].message

    def test_legacy_backend_standards_file_fallback(self, tmp_path):
        """When standards.md is absent, the scanner falls back to legacy backend-standards.md."""
        project_dir = _make_project_dir(tmp_path)
        (project_dir / "conventions.md").write_text(
            "| `BACKEND_FRAMEWORK` | `Django` | FW |\n", encoding="utf-8"
        )
        # Only legacy file present
        (project_dir / "backend-standards.md").write_text(
            "# Backend Standards\nUse Flask for APIs.\n", encoding="utf-8"
        )
        with patch.dict("sys.modules", {"project_config": type("M", (), {"get": staticmethod(lambda k: {"BACKEND_FRAMEWORK": "Django", "FRONTEND_FRAMEWORK": None}.get(k))})}):
            findings = plugin_value_propagation(tmp_path, verbose=False)
        assert len(findings) == 1
        assert findings[0].severity == "warning"
        assert "Django" in findings[0].message
        assert "backend-standards.md" in findings[0].message

    def test_neither_standards_file_present_skips_silently(self, tmp_path):
        """When neither standards.md nor backend-standards.md exists, non-verbose returns no findings."""
        project_dir = _make_project_dir(tmp_path)
        (project_dir / "conventions.md").write_text(
            "| `BACKEND_FRAMEWORK` | `Django` | FW |\n"
            "| `FRONTEND_FRAMEWORK` | `React` | FW |\n",
            encoding="utf-8",
        )
        # No standards files at all
        with patch.dict("sys.modules", {"project_config": type("M", (), {"get": staticmethod(lambda k: {"BACKEND_FRAMEWORK": "Django", "FRONTEND_FRAMEWORK": "React"}.get(k))})}):
            findings = plugin_value_propagation(tmp_path, verbose=False)
        assert findings == []
        # Verbose mode produces one info per framework
        with patch.dict("sys.modules", {"project_config": type("M", (), {"get": staticmethod(lambda k: {"BACKEND_FRAMEWORK": "Django", "FRONTEND_FRAMEWORK": "React"}.get(k))})}):
            findings = plugin_value_propagation(tmp_path, verbose=True)
        info_findings = [f for f in findings if f.severity == "info"]
        assert len(info_findings) >= 2
