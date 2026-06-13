"""Integration smoke test for plan-000265 infrastructure.

Exercises the cross-script data flow (pending.py + check_human_markers_only.py)
without requiring agent interpretation of pre-skill or post-skill Markdown.

Tests use an in-process runner pattern (see _run_pending) that monkey-patches
project_config.REPO_ROOT to a temp directory, so tests never write to the real
_output/pending.jsonl. This mirrors the pattern used by test_pending.py.

Does NOT exercise agent-interpreted workflows; those are verified by the manual
acceptance gate in plan-000265 step 13.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
PENDING_SCRIPT = SCRIPTS_DIR / "pending.py"
VERIFIER_SCRIPT = SCRIPTS_DIR / "check_human_markers_only.py"
FIXTURE_PATH = SCRIPTS_DIR / "tests" / "fixtures" / "marker_fixture.md"

sys.path.insert(0, str(SCRIPTS_DIR))


MINIMAL_CONVENTIONS_WITH_TRIGGERS = """\
# Project Conventions

## Paths

| Variable | Value | Description |
|----------|-------|-------------|
| `OUTPUT_DIR` | `_output` | Output dir |

## Periodic Triggers

| Trigger | Interval (days) | Action type | Description |
|---------|-----------------|-------------|-------------|
| Periodic curation | 30 | periodic-curation | Review items ready to promote |
| Spec-drift check | 14 | spec-drift-check | Run /explain spec-drift |

## Source Directories
"""


def _setup_fake_repo(tmp_path: Path, with_triggers: bool = True) -> Path:
    """Create a minimal fake SEJA repo layout under tmp_path."""
    (tmp_path / ".claude").mkdir(exist_ok=True)
    (tmp_path / "_output").mkdir(exist_ok=True)
    proj_dir = tmp_path / "_references" / "project"
    proj_dir.mkdir(parents=True, exist_ok=True)
    if with_triggers:
        (proj_dir / "conventions.md").write_text(MINIMAL_CONVENTIONS_WITH_TRIGGERS, encoding="utf-8")
    else:
        (proj_dir / "conventions.md").write_text(
            "# Conv\n\n## Paths\n\n| Variable | Value | Description |\n"
            "|----------|-------|-------------|\n"
            "| `OUTPUT_DIR` | `_output` | Output dir |\n",
            encoding="utf-8",
        )
    return tmp_path


def _run_pending(fake_repo: Path, *args: str) -> subprocess.CompletedProcess:
    """Invoke pending.py in a fake repo via a runner that patches REPO_ROOT."""
    runner = fake_repo / "_runner.py"
    runner.write_text(
        "import sys\n"
        "from pathlib import Path\n"
        f"sys.path.insert(0, {str(SCRIPTS_DIR)!r})\n"
        "import project_config\n"
        f"project_config.REPO_ROOT = Path({str(fake_repo)!r})\n"
        "project_config._config = None\n"
        "import pending\n"
        f"pending.REPO_ROOT = Path({str(fake_repo)!r})\n"
        f"sys.argv = [{str(PENDING_SCRIPT)!r}] + {list(args)!r}\n"
        "sys.exit(pending.main())\n",
        encoding="utf-8",
    )
    return subprocess.run(
        [sys.executable, str(runner)],
        cwd=str(fake_repo),
        capture_output=True,
        text=True,
        env=dict(os.environ),
    )


def test_pending_full_lifecycle(tmp_path: Path) -> None:
    """add -> list pending -> done -> list pending empty -> list all shows done."""
    fake_repo = _setup_fake_repo(tmp_path, with_triggers=False)

    result = _run_pending(
        fake_repo,
        "add",
        "--type",
        "user-defined",
        "--source",
        "manual",
        "--description",
        "integration test item",
    )
    assert result.returncode == 0, f"add failed: {result.stderr}"

    result = _run_pending(fake_repo, "list", "--status", "pending", "--json")
    assert result.returncode == 0
    items = json.loads(result.stdout)
    assert len(items) == 1
    assert items[0]["id"] == "pa-000001"
    assert items[0]["type"] == "user-defined"
    assert items[0]["status"] == "pending"

    result = _run_pending(fake_repo, "done", "pa-000001")
    assert result.returncode == 0

    result = _run_pending(fake_repo, "list", "--status", "pending", "--json")
    assert result.returncode == 0
    assert json.loads(result.stdout) == []

    result = _run_pending(fake_repo, "list", "--status", "all", "--json")
    assert result.returncode == 0
    items = json.loads(result.stdout)
    assert len(items) == 1
    assert items[0]["status"] == "done"


def test_periodic_check_idempotent(tmp_path: Path) -> None:
    """Two back-to-back periodic-check runs should not duplicate entries."""
    fake_repo = _setup_fake_repo(tmp_path, with_triggers=True)

    result = _run_pending(fake_repo, "periodic-check")
    assert result.returncode == 0, f"first periodic-check failed: {result.stderr}"

    result = _run_pending(fake_repo, "list", "--status", "pending", "--json")
    assert result.returncode == 0
    items_first = json.loads(result.stdout)
    assert len(items_first) == 2
    types_first = {item["type"] for item in items_first}
    assert types_first == {"periodic-curation", "spec-drift-check"}

    result = _run_pending(fake_repo, "periodic-check")
    assert result.returncode == 0

    result = _run_pending(fake_repo, "list", "--status", "pending", "--json")
    assert result.returncode == 0
    items_second = json.loads(result.stdout)
    assert len(items_second) == 2


def test_verify_as_coded_branch_creates_pending(tmp_path: Path) -> None:
    """Simulate post-skill sub-step g.i: >= 5 files creates a verify-as-coded pending entry."""
    fake_repo = _setup_fake_repo(tmp_path, with_triggers=False)

    result = _run_pending(
        fake_repo,
        "add",
        "--type",
        "verify-as-coded",
        "--source",
        "plan-000999",
        "--description",
        "Review product-design-as-coded.md against plan-000999 (7 files modified)",
    )
    assert result.returncode == 0

    result = _run_pending(
        fake_repo, "list", "--status", "pending", "--type", "verify-as-coded", "--json"
    )
    assert result.returncode == 0
    items = json.loads(result.stdout)
    assert len(items) == 1
    assert items[0]["source"] == "plan-000999"
    assert "7 files modified" in items[0]["description"]


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_marker_happy_path_staged_diff(tmp_path: Path) -> None:
    """Stage a STATUS marker flip on the fixture and verify check_human_markers_only passes."""
    fake_repo = tmp_path / "repo"
    fake_repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=fake_repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@test"], cwd=fake_repo, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=fake_repo, check=True)

    fixture_dir = fake_repo / ".claude" / "skills" / "scripts" / "tests" / "fixtures"
    fixture_dir.mkdir(parents=True)
    fixture_copy = fixture_dir / "marker_fixture.md"
    shutil.copy(FIXTURE_PATH, fixture_copy)
    (fake_repo / ".claude" / ".keep").touch()

    subprocess.run(["git", "add", "."], cwd=fake_repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "baseline"], cwd=fake_repo, check=True)

    content = fixture_copy.read_text(encoding="utf-8")
    new_content = content.replace(
        "<!-- STATUS: proposed -->\n### R-P-001:",
        "<!-- STATUS: implemented | plan-000265 | 2026-04-10 -->\n### R-P-001:",
        1,
    )
    fixture_copy.write_text(new_content, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=fake_repo, check=True)

    result = subprocess.run(
        [sys.executable, str(VERIFIER_SCRIPT), "--staged"],
        cwd=str(fake_repo),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, (
        f"expected pass, got {result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_marker_prose_mutation_rejected(tmp_path: Path) -> None:
    """Stage a prose mutation in the fixture; verifier should exit 1."""
    fake_repo = tmp_path / "repo"
    fake_repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=fake_repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@test"], cwd=fake_repo, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=fake_repo, check=True)

    fixture_dir = fake_repo / ".claude" / "skills" / "scripts" / "tests" / "fixtures"
    fixture_dir.mkdir(parents=True)
    fixture_copy = fixture_dir / "marker_fixture.md"
    shutil.copy(FIXTURE_PATH, fixture_copy)
    (fake_repo / ".claude" / ".keep").touch()

    subprocess.run(["git", "add", "."], cwd=fake_repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "baseline"], cwd=fake_repo, check=True)

    content = fixture_copy.read_text(encoding="utf-8")
    bad_content = content.replace(
        "A test persona used to exercise STATUS marker transitions in test_apply_marker.py.",
        "A test persona used to exercise STATUS marker transitions in test_apply_marker.py.\n\nMALICIOUS NEW PARAGRAPH inserted by the test.",
        1,
    )
    fixture_copy.write_text(bad_content, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=fake_repo, check=True)

    result = subprocess.run(
        [sys.executable, str(VERIFIER_SCRIPT), "--staged"],
        cwd=str(fake_repo),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 1, (
        f"expected rejection, got {result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    combined = (result.stdout + result.stderr).lower()
    assert any(token in combined for token in ("malicious", "violat", "prose", "@@"))
