"""Tests for check_skill_system.py — skill system integrity checker."""
from pathlib import Path
from unittest.mock import patch

import pytest

# Post plan-000466: Quick Guide narrative lives in a sibling
# SKILL-quickguide.md file. SKILL.md carries a mandatory pointer
# blockquote line to the sibling within the first 15 non-blank body
# lines.


@pytest.fixture
def valid_skill(tmp_path):
    """Create a minimal valid SKILL.md with its SKILL-quickguide.md sibling."""
    skill_dir = tmp_path / ".claude" / "skills" / "test-skill"
    skill_dir.mkdir(parents=True)
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        "---\n"
        "name: test-skill\n"
        "description: A test skill for validation.\n"
        "argument-hint: <arg>\n"
        "metadata:\n"
        "  last-updated: 2026-03-28 00:00 UTC\n"
        "  version: 1.0.0\n"
        "  category: utility\n"
        "  context_budget: light\n"
        "  references: []\n"
        "---\n"
        "\n"
        "> Overview: see [./SKILL-quickguide.md](./SKILL-quickguide.md)\n"
        "\n"
        "## Arguments\n"
        "\n"
        "| Argument | Required | Description |\n"
        "|----------|----------|-------------|\n"
        "| `<arg>` | Yes | The argument |\n"
        "\n"
        "# Test Skill\n"
        "\n"
        "Do the thing.\n",
        encoding="utf-8",
    )
    (skill_dir / "SKILL-quickguide.md").write_text(
        "**What it does**: Tests things.\n"
        "\n"
        "**Example**:\n"
        "> You: /test-skill foo\n"
        "> Agent: Does foo.\n"
        "\n"
        "**When to use**: When you need to test.\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def skill_missing_quickguide_pointer(tmp_path):
    """A SKILL.md with a sibling but no pointer -- should fail the invariant."""
    skill_dir = tmp_path / ".claude" / "skills" / "orphan-pointer"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        "name: orphan-pointer\n"
        "description: Skill whose SKILL.md forgot the sibling pointer.\n"
        "metadata:\n"
        "  version: 1.0.0\n"
        "---\n"
        "\n"
        "## Arguments\n"
        "\n"
        "No args.\n"
        "\n"
        "# Orphan\n",
        encoding="utf-8",
    )
    (skill_dir / "SKILL-quickguide.md").write_text(
        "**What it does**: still orphaned.\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def invalid_skill_missing_desc(tmp_path):
    """Create a SKILL.md missing the description field."""
    skill_dir = tmp_path / ".claude" / "skills" / "bad-skill"
    skill_dir.mkdir(parents=True)
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        "---\n"
        "name: bad-skill\n"
        "metadata:\n"
        "  version: 1.0.0\n"
        "---\n"
        "\n"
        "# Bad Skill\n",
        encoding="utf-8",
    )
    return tmp_path


def test_valid_skill_structure(valid_skill):
    """A well-formed SKILL.md carries the sibling pointer, and the Quick
    Guide body lives in the SKILL-quickguide.md sibling (plan-000466)."""
    skill_dir = valid_skill / ".claude" / "skills" / "test-skill"
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    assert "name:" in text
    assert "description:" in text
    # Pointer lives in SKILL.md; narrative does not.
    assert "SKILL-quickguide.md" in text
    assert "## Quick Guide" not in text
    assert "metadata:" in text
    sibling = (skill_dir / "SKILL-quickguide.md").read_text(encoding="utf-8")
    assert "What it does" in sibling


def test_invalid_skill_missing_description(invalid_skill_missing_desc):
    """A SKILL.md missing description should be detectable."""
    skill_md = invalid_skill_missing_desc / ".claude" / "skills" / "bad-skill" / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    assert "name:" in text
    assert "description:" not in text


def test_pointer_invariant_catches_missing_pointer(
    skill_missing_quickguide_pointer,
):
    """The quickguide-pointer-compliance plugin fires when a sibling
    exists but SKILL.md has no pointer line."""
    import sys
    scripts_dir = Path(__file__).resolve().parent.parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from check_docs import plugin_quickguide_pointer_compliance

    findings = plugin_quickguide_pointer_compliance(
        skill_missing_quickguide_pointer, verbose=False
    )
    assert any(
        "pointer" in f.message.lower() and f.severity == "error"
        for f in findings
    ), f"expected a pointer-compliance error; got {findings}"


def test_pointer_invariant_passes_on_valid_skill(valid_skill):
    """The quickguide-pointer-compliance plugin stays silent when the
    sibling exists and SKILL.md carries the pointer."""
    import sys
    scripts_dir = Path(__file__).resolve().parent.parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from check_docs import plugin_quickguide_pointer_compliance

    findings = plugin_quickguide_pointer_compliance(valid_skill, verbose=False)
    assert findings == [], f"expected no findings; got {findings}"
