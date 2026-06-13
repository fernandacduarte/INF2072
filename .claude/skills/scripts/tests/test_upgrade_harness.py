"""Tests for upgrade_harness.

Covers:
- _regenerate_reference_files (plan-000291)
- .seja-version read/write pin path (plan-000380)
"""
from __future__ import annotations

import stat
import sys
from pathlib import Path

import pytest

import upgrade_harness


def _make_scripts_dir(target: Path) -> Path:
    scripts_dir = target / ".claude" / "skills" / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    return scripts_dir


def _write_generator(scripts_dir: Path, name: str, body: str) -> Path:
    script = scripts_dir / name
    script.write_text(body, encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return script


def _sentinel_generator_body(sentinel_rel_path: str) -> str:
    return (
        "import sys\n"
        "from pathlib import Path\n"
        "sentinel = Path.cwd() / r'" + sentinel_rel_path + "'\n"
        "sentinel.parent.mkdir(parents=True, exist_ok=True)\n"
        "sentinel.write_text('generated', encoding='utf-8')\n"
        "sys.exit(0)\n"
    )


def test_regenerate_reference_files_invokes_present_generators(tmp_path, capsys):
    scripts_dir = _make_scripts_dir(tmp_path)
    _write_generator(scripts_dir, "generate_harness_reference.py",
                     _sentinel_generator_body("seja-public/docs/reference/harness-reference.md"))
    _write_generator(scripts_dir, "generate_skills_reference.py",
                     _sentinel_generator_body("seja-public/docs/reference/skills.md"))
    _write_generator(scripts_dir, "generate_perspectives_reference.py",
                     _sentinel_generator_body("seja-public/docs/reference/perspectives.md"))

    report: list[str] = []
    upgrade_harness._regenerate_reference_files(tmp_path, dry_run=False, report_updated=report)

    assert (tmp_path / "seja-public/docs/reference/harness-reference.md").is_file()
    assert (tmp_path / "seja-public/docs/reference/skills.md").is_file()
    assert (tmp_path / "seja-public/docs/reference/perspectives.md").is_file()
    assert len(report) == 3
    assert all("Regenerated" in line for line in report)


def test_regenerate_reference_files_skips_missing_generators(tmp_path, capsys):
    scripts_dir = _make_scripts_dir(tmp_path)
    _write_generator(scripts_dir, "generate_harness_reference.py",
                     _sentinel_generator_body("seja-public/docs/reference/harness-reference.md"))
    # skills + perspectives generators intentionally missing

    report: list[str] = []
    upgrade_harness._regenerate_reference_files(tmp_path, dry_run=False, report_updated=report)

    captured = capsys.readouterr()
    assert "Skipped skills reference" in captured.out
    assert "Skipped perspectives reference" in captured.out
    assert len(report) == 1
    assert "harness-reference" in report[0]


def test_regenerate_reference_files_dry_run_logs_without_executing(tmp_path, capsys):
    scripts_dir = _make_scripts_dir(tmp_path)
    _write_generator(scripts_dir, "generate_harness_reference.py",
                     _sentinel_generator_body("seja-public/docs/reference/harness-reference.md"))
    _write_generator(scripts_dir, "generate_skills_reference.py",
                     _sentinel_generator_body("seja-public/docs/reference/skills.md"))
    _write_generator(scripts_dir, "generate_perspectives_reference.py",
                     _sentinel_generator_body("seja-public/docs/reference/perspectives.md"))

    report: list[str] = []
    upgrade_harness._regenerate_reference_files(tmp_path, dry_run=True, report_updated=report)

    assert not (tmp_path / "seja-public/docs/reference/harness-reference.md").exists()
    assert not (tmp_path / "seja-public/docs/reference/skills.md").exists()
    assert not (tmp_path / "seja-public/docs/reference/perspectives.md").exists()
    assert report == []
    captured = capsys.readouterr()
    assert captured.out.count("Would regenerate") == 3


def test_regenerate_reference_files_continues_on_generator_failure(tmp_path, capsys):
    scripts_dir = _make_scripts_dir(tmp_path)
    # Generator exits non-zero
    _write_generator(scripts_dir, "generate_harness_reference.py",
                     "import sys\nsys.stderr.write('boom\\n')\nsys.exit(1)\n")
    _write_generator(scripts_dir, "generate_skills_reference.py",
                     _sentinel_generator_body("seja-public/docs/reference/skills.md"))
    _write_generator(scripts_dir, "generate_perspectives_reference.py",
                     _sentinel_generator_body("seja-public/docs/reference/perspectives.md"))

    report: list[str] = []
    upgrade_harness._regenerate_reference_files(tmp_path, dry_run=False, report_updated=report)

    captured = capsys.readouterr()
    assert "harness-reference regeneration failed" in captured.out
    # The other two generators still ran
    assert (tmp_path / "seja-public/docs/reference/skills.md").is_file()
    assert (tmp_path / "seja-public/docs/reference/perspectives.md").is_file()
    assert len(report) == 2
    assert not any("harness-reference" == line.replace("Regenerated ", "") for line in report)


def test_regenerate_reference_files_handles_timeout(tmp_path, capsys, monkeypatch):
    scripts_dir = _make_scripts_dir(tmp_path)
    # Generator sleeps longer than the monkeypatched timeout
    _write_generator(
        scripts_dir, "generate_harness_reference.py",
        "import time\ntime.sleep(5)\n",
    )

    # Monkeypatch subprocess.run to raise TimeoutExpired for the first call,
    # simulating a generator that exceeds the timeout without actually waiting.
    import subprocess as _subprocess
    real_run = _subprocess.run

    def fake_run(cmd, *args, **kwargs):
        if "generate_harness_reference.py" in " ".join(str(c) for c in cmd):
            raise _subprocess.TimeoutExpired(cmd=cmd, timeout=1)
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr(upgrade_harness.subprocess, "run", fake_run)

    report: list[str] = []
    upgrade_harness._regenerate_reference_files(tmp_path, dry_run=False, report_updated=report)

    captured = capsys.readouterr()
    assert "timed out" in captured.out
    # The helper did not raise and report remains empty for the timed-out generator
    assert not any("harness-reference" in line for line in report)


# ---------------------------------------------------------------------------
# .seja-version pin path (plan-000380)
# ---------------------------------------------------------------------------


def test_read_seja_version_missing(tmp_path):
    assert upgrade_harness.read_seja_version(tmp_path) is None


def test_read_seja_version_present(tmp_path):
    (tmp_path / ".seja-version").write_text("v0.1.0\n", encoding="utf-8")
    assert upgrade_harness.read_seja_version(tmp_path) == "v0.1.0"


def test_read_seja_version_empty_string_is_none(tmp_path):
    (tmp_path / ".seja-version").write_text("   \n", encoding="utf-8")
    assert upgrade_harness.read_seja_version(tmp_path) is None


def test_write_seja_version_creates_file(tmp_path):
    summary = upgrade_harness.write_seja_version(tmp_path, "v0.2.0", dry_run=False)
    assert "Pinned v0.2.0" in summary
    assert (tmp_path / ".seja-version").read_text(encoding="utf-8").strip() == "v0.2.0"


def test_write_seja_version_dry_run_does_not_touch_file(tmp_path):
    summary = upgrade_harness.write_seja_version(tmp_path, "v0.2.0", dry_run=True)
    assert "Would pin v0.2.0" in summary
    assert not (tmp_path / ".seja-version").exists()


def test_write_seja_version_overwrites_existing(tmp_path):
    (tmp_path / ".seja-version").write_text("v0.1.0\n", encoding="utf-8")
    upgrade_harness.write_seja_version(tmp_path, "v0.2.0", dry_run=False)
    assert (tmp_path / ".seja-version").read_text(encoding="utf-8").strip() == "v0.2.0"


def test_collect_source_files_includes_skill_siblings(tmp_path):
    """plan-000466 Step 6b: /seja-setup --upgrade must ship SKILL-*.md
    siblings alongside SKILL.md, otherwise upgraded consumers end up with
    dangling pointers.
    """
    skills_dir = tmp_path / ".claude" / "skills"
    demo = skills_dir / "demo"
    demo.mkdir(parents=True)
    (demo / "SKILL.md").write_text(
        "---\nname: demo\n---\n\n"
        "> Overview: see [./SKILL-quickguide.md](./SKILL-quickguide.md)\n\n"
        "# Demo\n",
        encoding="utf-8",
    )
    (demo / "SKILL-quickguide.md").write_text(
        "Quick guide body.\n", encoding="utf-8"
    )
    (demo / "SKILL-rationale.md").write_text(
        "Rationale body.\n", encoding="utf-8"
    )
    # A file that does NOT start with SKILL must be excluded.
    (demo / "NOTES.md").write_text("not a sibling", encoding="utf-8")

    files = upgrade_harness.collect_source_files(tmp_path)
    names = sorted(p.name for p in files if p.parent == demo)
    assert "SKILL.md" in names
    assert "SKILL-quickguide.md" in names
    assert "SKILL-rationale.md" in names
    assert "NOTES.md" not in names


def test_collect_source_files_rejects_nonsibling_skill_names(tmp_path):
    """The sibling glob must not match files that happen to start with SKILL
    but do not follow the SKILL.md / SKILL-<facet>.md shape.
    """
    skills_dir = tmp_path / ".claude" / "skills"
    demo = skills_dir / "only-skill"
    demo.mkdir(parents=True)
    (demo / "SKILL.md").write_text(
        "---\nname: only\n---\n# Only\n", encoding="utf-8"
    )
    # An ill-named file that would slip past a loose prefix filter.
    (demo / "SKILLS-plan.md").write_text("not a sibling", encoding="utf-8")

    files = upgrade_harness.collect_source_files(tmp_path)
    names = sorted(p.name for p in files if p.parent == demo)
    assert "SKILL.md" in names
    assert "SKILLS-plan.md" not in names


# ---------------------------------------------------------------------------
# _internal skills enumeration (plan-000553)
# ---------------------------------------------------------------------------


def test_collect_source_files_includes_internal_skills(tmp_path):
    """_internal skill directories (nested >1 level) must be discovered."""
    skills_dir = tmp_path / ".claude" / "skills"

    # Top-level skill (should still work)
    top = skills_dir / "check"
    top.mkdir(parents=True)
    (top / "SKILL.md").write_text("---\nname: check\n---\n# Check\n", encoding="utf-8")

    # Nested _internal skill
    internal = skills_dir / "_internal" / "plan" / "standard"
    internal.mkdir(parents=True)
    (internal / "SKILL.md").write_text(
        "---\nname: plan-standard\n---\n# Plan Standard\n", encoding="utf-8"
    )

    # Another nested _internal skill with SKILL-quickguide.md sibling
    internal2 = skills_dir / "_internal" / "design" / "interview"
    internal2.mkdir(parents=True)
    (internal2 / "SKILL.md").write_text(
        "---\nname: design-interview\n---\n# Design Interview\n", encoding="utf-8"
    )
    (internal2 / "SKILL-quickguide.md").write_text("Quick guide.\n", encoding="utf-8")

    files = upgrade_harness.collect_source_files(tmp_path)
    rel_paths = {f.relative_to(tmp_path).as_posix() for f in files}

    assert ".claude/skills/check/SKILL.md" in rel_paths
    assert ".claude/skills/_internal/plan/standard/SKILL.md" in rel_paths
    assert ".claude/skills/_internal/design/interview/SKILL.md" in rel_paths
    assert ".claude/skills/_internal/design/interview/SKILL-quickguide.md" in rel_paths


def test_collect_source_files_excludes_scripts_from_recursive_scan(tmp_path):
    """The scripts/ directory must not be treated as a skill directory."""
    skills_dir = tmp_path / ".claude" / "skills"
    scripts = skills_dir / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "upgrade_harness.py").write_text("# script\n", encoding="utf-8")

    # A real skill to ensure the function doesn't return empty
    demo = skills_dir / "demo"
    demo.mkdir(parents=True)
    (demo / "SKILL.md").write_text("---\nname: demo\n---\n# Demo\n", encoding="utf-8")

    files = upgrade_harness.collect_source_files(tmp_path)
    # scripts/*.py should be collected via the scripts enumeration, not skill enumeration
    skill_files = [f for f in files if "_internal" in str(f) or (f.parent.name != "scripts" and f.name.startswith("SKILL"))]
    # No SKILL*.md from scripts/
    assert not any(f.parent == scripts and f.name.startswith("SKILL") for f in files)


# ---------------------------------------------------------------------------
# Co-located skill scripts (plan-000553)
# ---------------------------------------------------------------------------


def test_collect_source_files_includes_colocated_py_scripts(tmp_path):
    """Co-located .py files in skill directories must be collected."""
    skills_dir = tmp_path / ".claude" / "skills"

    check_dir = skills_dir / "check"
    check_dir.mkdir(parents=True)
    (check_dir / "SKILL.md").write_text("---\nname: check\n---\n# Check\n", encoding="utf-8")
    (check_dir / "check_docs.py").write_text("# check docs\n", encoding="utf-8")
    (check_dir / "check_git_freshness.py").write_text("# git freshness\n", encoding="utf-8")

    setup_dir = skills_dir / "seja-setup"
    setup_dir.mkdir(parents=True)
    (setup_dir / "SKILL.md").write_text("---\nname: seja-setup\n---\n# Setup\n", encoding="utf-8")
    (setup_dir / "resolve_seja_version.py").write_text("# resolve\n", encoding="utf-8")

    files = upgrade_harness.collect_source_files(tmp_path)
    rel_paths = {f.relative_to(tmp_path).as_posix() for f in files}

    assert ".claude/skills/check/check_docs.py" in rel_paths
    assert ".claude/skills/check/check_git_freshness.py" in rel_paths
    assert ".claude/skills/seja-setup/resolve_seja_version.py" in rel_paths


def test_collect_source_files_excludes_non_py_colocated_files(tmp_path):
    """Only .py files (and SKILL*.md) should be collected from skill dirs."""
    skills_dir = tmp_path / ".claude" / "skills"
    demo = skills_dir / "demo"
    demo.mkdir(parents=True)
    (demo / "SKILL.md").write_text("---\nname: demo\n---\n# Demo\n", encoding="utf-8")
    (demo / "helper.py").write_text("# helper\n", encoding="utf-8")
    (demo / "NOTES.md").write_text("random notes", encoding="utf-8")
    (demo / "data.json").write_text("{}", encoding="utf-8")

    files = upgrade_harness.collect_source_files(tmp_path)
    names = {f.name for f in files if f.parent == demo}

    assert "SKILL.md" in names
    assert "helper.py" in names
    assert "NOTES.md" not in names
    assert "data.json" not in names
