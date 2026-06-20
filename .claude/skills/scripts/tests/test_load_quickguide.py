"""Tests for load_quickguide.py -- shared SKILL-quickguide.md loader.

Covers plan-000466 Step 7 unit cases:

(a) sibling present, returns body
(b) sibling missing, returns None
(c) sibling with YAML frontmatter, frontmatter stripped
(d) sibling empty, returns empty string
(e) skill directory does not exist, returns None
"""
from __future__ import annotations

from pathlib import Path

import pytest

from load_quickguide import load_quickguide


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="")


def test_sibling_present_returns_body(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skills" / "demo"
    _write(
        skill_dir / "SKILL-quickguide.md",
        "**What it does**: demo narrative.\n",
    )
    result = load_quickguide(skill_dir)
    assert result is not None
    assert "What it does" in result
    assert "demo narrative" in result


def test_sibling_missing_returns_none(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skills" / "empty-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("body only", encoding="utf-8")
    assert load_quickguide(skill_dir) is None


def test_frontmatter_stripped(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skills" / "with-frontmatter"
    _write(
        skill_dir / "SKILL-quickguide.md",
        "---\n"
        "title: Demo Quick Guide\n"
        "---\n"
        "\n"
        "**What it does**: after-the-frontmatter content.\n",
    )
    result = load_quickguide(skill_dir)
    assert result is not None
    assert "title: Demo Quick Guide" not in result
    assert "after-the-frontmatter content" in result


def test_empty_sibling_returns_empty_string(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skills" / "empty"
    _write(skill_dir / "SKILL-quickguide.md", "")
    result = load_quickguide(skill_dir)
    assert result == ""


def test_missing_directory_returns_none(tmp_path: Path) -> None:
    # Directory never existed.
    nonexistent = tmp_path / "does-not-exist" / "skill"
    assert load_quickguide(nonexistent) is None


def test_crlf_frontmatter_stripped(tmp_path: Path) -> None:
    # CRLF-terminated frontmatter (matches constraints.md line ending).
    skill_dir = tmp_path / "skills" / "crlf"
    (skill_dir).mkdir(parents=True)
    (skill_dir / "SKILL-quickguide.md").write_bytes(
        b"---\r\nkey: value\r\n---\r\n\r\nbody line\r\n"
    )
    result = load_quickguide(skill_dir)
    assert result is not None
    assert "key: value" not in result
    assert "body line" in result


def test_unterminated_frontmatter_returns_file_unchanged(
    tmp_path: Path,
) -> None:
    # A leading --- with no closing delimiter: return content as-is rather
    # than silently swallow the whole file.
    skill_dir = tmp_path / "skills" / "malformed"
    _write(
        skill_dir / "SKILL-quickguide.md",
        "---\nkey: value\nno closing delimiter ever\n",
    )
    result = load_quickguide(skill_dir)
    assert result is not None
    assert "no closing delimiter" in result
