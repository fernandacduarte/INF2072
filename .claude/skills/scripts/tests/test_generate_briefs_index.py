"""Tests for generate_briefs_index.py — briefs index generator."""
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def fake_briefs(tmp_path):
    """Create a briefs.md with known entries."""
    briefs = tmp_path / "briefs.md"
    briefs.write_text(
        "DONE | 2026-03-28 10:00:00 UTC | STARTED | 2026-03-28 09:00:00 UTC | advise | First question\n"
        "\n"
        "DONE | 2026-03-28 12:00:00 UTC | STARTED | 2026-03-28 11:00:00 UTC | plan | Second task | PLAN | 0001\n"
        "\n"
        "STARTED | 2026-03-28 13:00:00 UTC | plan | Third task (orphaned)\n",
        encoding="utf-8",
    )
    return briefs


@pytest.fixture
def fake_repo_with_briefs(tmp_path, fake_briefs):
    """Create a minimal repo structure for generate_briefs_index.py."""
    (tmp_path / ".claude").mkdir()
    (tmp_path / "_references").mkdir()
    output_dir = tmp_path / "_output"
    output_dir.mkdir()
    # Move briefs into position
    target = output_dir / "briefs.md"
    target.write_text(fake_briefs.read_text(encoding="utf-8"), encoding="utf-8")
    # Create template/conventions.md so project_config can find it
    conv = tmp_path / "_references" / "template/conventions.md"
    conv.write_text(
        "| Variable | Value | Description |\n"
        "|----------|-------|-------------|\n"
        "| `OUTPUT_DIR` | `_output` | Root output |\n"
        "| `BRIEFS_FILE` | `${OUTPUT_DIR}/briefs.md` | Briefs file |\n"
        "| `BRIEFS_INDEX_FILE` | `${OUTPUT_DIR}/briefs-index.md` | Briefs index |\n",
        encoding="utf-8",
    )
    return tmp_path


def test_briefs_file_parsing(fake_briefs):
    """Verify the fixture briefs file has expected structure."""
    text = fake_briefs.read_text(encoding="utf-8")
    lines = [l for l in text.strip().splitlines() if l.strip()]
    assert len(lines) == 3
    assert "DONE" in lines[0]
    assert "STARTED" in lines[2]
    assert "PLAN | 0001" in lines[1]
