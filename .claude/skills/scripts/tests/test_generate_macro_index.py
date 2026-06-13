"""Tests for generate_macro_index.py -- unified artifact index generator."""
from __future__ import annotations

from pathlib import Path

import pytest

import generate_macro_index as gen


FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "generate_macro_index"


# ---------------------------------------------------------------------------
# Reflection header extraction
# ---------------------------------------------------------------------------


def test_extract_reflection_header(tmp_path, monkeypatch):
    """A reflection file with the canonical header is recognized as type 'Reflection'."""
    output_dir = tmp_path / "_output"
    reflections_dir = output_dir / "reflections"
    reflections_dir.mkdir(parents=True)

    stub = reflections_dir / "reflection-999999-smoke-stub.md"
    stub.write_text(
        "# Reflection 999999 | 2026-04-11 22:45 UTC | Smoke stub\n"
        "\n"
        "Stub body for test fixture.\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(gen, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(gen, "INDEX_FILE", output_dir / "INDEX.md")

    entry = gen.extract_artifact(stub)
    assert entry is not None, "extract_artifact returned None for reflection file"
    assert entry["type"] == "Reflection"
    assert entry["id"] == "999999"
    assert entry["title"] == "Smoke stub"
    assert entry["date"] == "2026-04-11 22:45 UTC"
    assert entry["status"] == ""
    assert entry["file"].replace("\\", "/") == "reflections/reflection-999999-smoke-stub.md"


def test_generate_index_includes_reflection(tmp_path, monkeypatch):
    """Running generate_index over a tmp OUTPUT_DIR with a reflection produces an INDEX row."""
    output_dir = tmp_path / "_output"
    reflections_dir = output_dir / "reflections"
    reflections_dir.mkdir(parents=True)

    stub = reflections_dir / "reflection-999999-smoke-stub.md"
    stub.write_text(
        "# Reflection 999999 | 2026-04-11 22:45 UTC | Smoke stub\n",
        encoding="utf-8",
    )

    index_file = output_dir / "INDEX.md"
    monkeypatch.setattr(gen, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(gen, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(gen, "INDEX_FILE", index_file)

    count = gen.generate_index(verbose=False)
    assert count >= 1

    content = index_file.read_text(encoding="utf-8")
    assert "| Reflection |" in content, "Reflection type row missing from INDEX"
    assert "999999" in content
    assert "Smoke stub" in content
    assert "reflections/reflection-999999-smoke-stub.md" in content.replace("\\", "/")


def test_generate_index_skips_missing_reflections_dir(tmp_path, monkeypatch):
    """If OUTPUT_DIR has no reflections/ subdir, the generator still runs cleanly."""
    output_dir = tmp_path / "_output"
    output_dir.mkdir()
    # intentionally: no reflections/ subdir

    index_file = output_dir / "INDEX.md"
    monkeypatch.setattr(gen, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(gen, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(gen, "INDEX_FILE", index_file)

    count = gen.generate_index(verbose=False)
    # Count may be 0 (no artifacts at all); the point is no exception was raised.
    assert count == 0
    content = index_file.read_text(encoding="utf-8")
    assert "# Artifact Index" in content
