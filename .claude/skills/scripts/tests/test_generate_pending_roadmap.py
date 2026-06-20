"""Tests for generate_pending_roadmap.py."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
SCRIPT_PATH = SCRIPTS_DIR / "generate_pending_roadmap.py"

sys.path.insert(0, str(SCRIPTS_DIR))


MINIMAL_CONVENTIONS = """\
# Project Conventions

## Paths

| Variable | Value | Description |
|----------|-------|-------------|
| `OUTPUT_DIR` | `_output` | Output dir |
"""


def _setup_fake_repo(tmp_path: Path, conventions: str | None = None) -> Path:
    """Create the minimal directory skeleton for a fake SEJA repo."""
    (tmp_path / ".claude").mkdir(exist_ok=True)
    (tmp_path / "_output").mkdir(exist_ok=True)
    (tmp_path / "_output" / "plans").mkdir(parents=True, exist_ok=True)
    (tmp_path / "_output" / "roadmaps").mkdir(parents=True, exist_ok=True)
    proj_dir = tmp_path / "product-design"
    proj_dir.mkdir(parents=True, exist_ok=True)
    (proj_dir / "conventions.md").write_text(
        conventions or MINIMAL_CONVENTIONS, encoding="utf-8"
    )
    return tmp_path


def _write_pending_entries(fake_repo: Path, entries: list[dict]) -> None:
    """Write pending.jsonl with the given records."""
    ledger = fake_repo / "_output" / "pending.jsonl"
    lines = [json.dumps(e, sort_keys=True) for e in entries]
    ledger.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _make_pending_entry(
    entry_id: str,
    plan_id: str,
    *,
    entry_type: str = "implement",
    status: str = "pending",
    description: str = "Implement plan",
) -> dict:
    """Build a minimal pending ledger entry."""
    return {
        "id": entry_id,
        "type": entry_type,
        "created_at": "2026-04-30T12:00:00+00:00",
        "source": f"plan-{plan_id}",
        "description": description,
        "status": status,
        "snooze_until": None,
        "last_reminded_at": None,
    }


def _write_plan_file(
    fake_repo: Path,
    plan_id: str,
    title: str,
    files: list[str] | None = None,
    *,
    suffix: str = "feature",
) -> Path:
    """Write a minimal plan file with optional Files: metadata."""
    plans_dir = fake_repo / "_output" / "plans"
    plan_path = plans_dir / f"plan-{plan_id}-{suffix}.md"
    lines = [f"# Plan {plan_id} | New | implement | {title} |"]
    lines.append("")
    if files is not None:
        lines.append("## Files")
        lines.append("")
        for f in files:
            lines.append(f"- `{f}` (modify)")
        lines.append("")
    lines.append("## Steps")
    lines.append("")
    lines.append("### Step 1")
    lines.append("Do the thing.")
    plan_path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return plan_path


def _run_script(
    fake_repo: Path, *args: str
) -> subprocess.CompletedProcess:
    """Run generate_pending_roadmap.py in a fake repo via a runner script.

    The runner patches project_config.REPO_ROOT and the module's REPO_ROOT
    to point at the fake repo, and monkey-patches _query_pending_implements
    to read from the fake repo's pending.jsonl (bypassing the subprocess
    call to pending.py, which would discover the real repo root from its
    on-disk location).
    """
    runner = fake_repo / "_runner.py"
    runner.write_text(
        "import json, sys\n"
        "from pathlib import Path\n"
        f"sys.path.insert(0, {str(SCRIPTS_DIR)!r})\n"
        "import project_config\n"
        f"project_config.REPO_ROOT = Path({str(fake_repo)!r})\n"
        "project_config._config = None\n"  # force reparse
        "import generate_pending_roadmap as gpr\n"
        f"gpr.REPO_ROOT = Path({str(fake_repo)!r})\n"
        "gpr.get_path = project_config.get_path\n"
        "\n"
        "# Monkey-patch _query_pending_implements to read from fake ledger\n"
        "# and filter locally, avoiding a subprocess call to pending.py\n"
        "# that would find the real repo root.\n"
        "def _fake_query():\n"
        f"    ledger = Path({str(fake_repo)!r}) / '_output' / 'pending.jsonl'\n"
        "    if not ledger.is_file():\n"
        "        return []\n"
        "    text = ledger.read_text(encoding='utf-8').strip()\n"
        "    if not text:\n"
        "        return []\n"
        "    records = [json.loads(ln) for ln in text.splitlines() if ln.strip()]\n"
        "    # Replicate pending.py list --type implement --status pending\n"
        "    return [\n"
        "        r for r in records\n"
        "        if r.get('type') == 'implement' and r.get('status') == 'pending'\n"
        "    ]\n"
        "\n"
        "gpr._query_pending_implements = _fake_query\n"
        f"sys.argv = ['generate_pending_roadmap.py'] + {list(args)!r}\n"
        "sys.exit(gpr.main())\n",
        encoding="utf-8",
    )
    return subprocess.run(
        [sys.executable, str(runner)],
        cwd=str(fake_repo),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=dict(os.environ),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestHappyPathSingleWave:
    """Two non-overlapping plans should both land in Wave 0."""

    def test_two_disjoint_plans_single_wave(self, tmp_path):
        fake = _setup_fake_repo(tmp_path)

        _write_plan_file(
            fake, "000100", "Add auth module",
            ["src/auth.py", "src/auth_test.py"],
        )
        _write_plan_file(
            fake, "000101", "Add logging module",
            ["src/logging.py", "src/logging_test.py"],
        )
        _write_pending_entries(fake, [
            _make_pending_entry("pa-000001", "000100"),
            _make_pending_entry("pa-000002", "000101"),
        ])

        r = _run_script(fake, "--roadmap-id", "999999")
        assert r.returncode == 0, f"stderr: {r.stderr}"

        roadmap_file = fake / "_output" / "roadmaps" / "roadmap-999999-pending-plans.md"
        assert roadmap_file.is_file(), "Roadmap file not created"

        content = roadmap_file.read_text(encoding="utf-8")
        # Both plans should be in Wave 0
        assert "### Wave 0" in content
        assert "plan-000100" in content
        assert "plan-000101" in content
        # Both plan titles should appear
        assert "Add auth module" in content
        assert "Add logging module" in content
        # Should NOT have a Wave 1
        assert "### Wave 1" not in content
        # Stdout should contain the roadmap path
        assert "roadmap-999999" in r.stdout


class TestHappyPathTwoWaves:
    """Two overlapping plans should be split across Wave 0 and Wave 1."""

    def test_two_overlapping_plans_two_waves(self, tmp_path):
        fake = _setup_fake_repo(tmp_path)

        _write_plan_file(
            fake, "000200", "Refactor config",
            ["src/config.py", "src/shared.py"],
        )
        _write_plan_file(
            fake, "000201", "Update config tests",
            ["src/shared.py", "src/config_test.py"],  # overlaps on src/shared.py
        )
        _write_pending_entries(fake, [
            _make_pending_entry("pa-000010", "000200"),
            _make_pending_entry("pa-000011", "000201"),
        ])

        r = _run_script(fake, "--roadmap-id", "999998")
        assert r.returncode == 0, f"stderr: {r.stderr}"

        roadmap_file = fake / "_output" / "roadmaps" / "roadmap-999998-pending-plans.md"
        assert roadmap_file.is_file()

        content = roadmap_file.read_text(encoding="utf-8")
        # Should have two waves
        assert "### Wave 0" in content
        assert "### Wave 1" in content
        # First plan in Wave 0, second in Wave 1 (greedy order)
        assert "plan-000200" in content
        assert "plan-000201" in content
        # Wave 1 should mention dependency
        assert "pending-plan-1" in content  # Wave 1 depends on pending-plan-1


class TestNoPendingEntries:
    """Script should exit 1 when there are no pending implement entries."""

    def test_empty_ledger(self, tmp_path):
        fake = _setup_fake_repo(tmp_path)
        # Write an empty ledger
        (fake / "_output" / "pending.jsonl").write_text("", encoding="utf-8")

        r = _run_script(fake, "--roadmap-id", "999997")
        assert r.returncode == 1

    def test_no_implement_entries(self, tmp_path):
        fake = _setup_fake_repo(tmp_path)
        # Write entries that are not type=implement
        _write_pending_entries(fake, [
            _make_pending_entry(
                "pa-000020", "000300",
                entry_type="mark-implemented",
            ),
        ])

        r = _run_script(fake, "--roadmap-id", "999996")
        assert r.returncode == 1


class TestMissingPlanFile:
    """Missing plan files should be warned about and skipped."""

    def test_only_missing_plan_exits_1(self, tmp_path):
        fake = _setup_fake_repo(tmp_path)
        # Pending entry references a plan that doesn't exist on disk
        _write_pending_entries(fake, [
            _make_pending_entry("pa-000030", "000400"),
        ])

        r = _run_script(fake, "--roadmap-id", "999995")
        assert r.returncode == 1
        assert "WARNING" in r.stderr
        assert "plan-000400" in r.stderr

    def test_mixed_missing_and_present(self, tmp_path):
        fake = _setup_fake_repo(tmp_path)
        _write_plan_file(
            fake, "000401", "Valid plan",
            ["src/valid.py"],
        )
        # 000402 has no plan file on disk
        _write_pending_entries(fake, [
            _make_pending_entry("pa-000031", "000401"),
            _make_pending_entry("pa-000032", "000402"),
        ])

        r = _run_script(fake, "--roadmap-id", "999994")
        assert r.returncode == 0, f"stderr: {r.stderr}"
        assert "WARNING" in r.stderr
        assert "plan-000402" in r.stderr

        roadmap_file = fake / "_output" / "roadmaps" / "roadmap-999994-pending-plans.md"
        content = roadmap_file.read_text(encoding="utf-8")
        assert "plan-000401" in content
        assert "plan-000402" not in content


class TestPlanWithNoFilesMetadata:
    """Plans without Files: metadata should be treated as independent."""

    def test_no_files_metadata_no_overlap(self, tmp_path):
        fake = _setup_fake_repo(tmp_path)

        _write_plan_file(
            fake, "000500", "Plan with files",
            ["src/foo.py", "src/bar.py"],
        )
        # Plan without Files: section
        _write_plan_file(
            fake, "000501", "Plan without files",
            None,  # no Files: metadata
        )
        _write_pending_entries(fake, [
            _make_pending_entry("pa-000040", "000500"),
            _make_pending_entry("pa-000041", "000501"),
        ])

        r = _run_script(fake, "--roadmap-id", "999993")
        assert r.returncode == 0, f"stderr: {r.stderr}"

        roadmap_file = fake / "_output" / "roadmaps" / "roadmap-999993-pending-plans.md"
        content = roadmap_file.read_text(encoding="utf-8")
        # Both plans should be in Wave 0 (no overlap since one has empty set)
        assert "### Wave 0" in content
        assert "plan-000500" in content
        assert "plan-000501" in content
        assert "### Wave 1" not in content


class TestCustomOutputDir:
    """The --output-dir flag should override the default roadmap directory."""

    def test_custom_output_dir(self, tmp_path):
        fake = _setup_fake_repo(tmp_path)
        custom_dir = fake / "custom_output"
        custom_dir.mkdir()

        _write_plan_file(
            fake, "000600", "Custom dir plan",
            ["src/custom.py"],
        )
        _write_pending_entries(fake, [
            _make_pending_entry("pa-000050", "000600"),
        ])

        r = _run_script(
            fake, "--roadmap-id", "999992",
            "--output-dir", str(custom_dir),
        )
        assert r.returncode == 0, f"stderr: {r.stderr}"

        roadmap_file = custom_dir / "roadmap-999992-pending-plans.md"
        assert roadmap_file.is_file()
