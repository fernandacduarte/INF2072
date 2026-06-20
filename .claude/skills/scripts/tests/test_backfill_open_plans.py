"""Tests for backfill_open_plans.py."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
SCRIPT_PATH = SCRIPTS_DIR / "backfill_open_plans.py"

sys.path.insert(0, str(SCRIPTS_DIR))


CONVENTIONS = (
    "# Conv\n\n## Paths\n\n| Variable | Value | Description |\n"
    "|----------|-------|-------------|\n"
    "| `OUTPUT_DIR` | `_output` | Output |\n"
    "| `PLANS_DIR` | `${OUTPUT_DIR}/plans` | Plans |\n"
)


def _run(fake_repo: Path, *args: str) -> subprocess.CompletedProcess:
    """Invoke backfill_open_plans.py in a fake repo."""
    output_dir = fake_repo / "_output"
    output_dir.mkdir(exist_ok=True)
    plans_dir = output_dir / "plans"
    plans_dir.mkdir(exist_ok=True)
    proj_dir = fake_repo / "product-design"
    proj_dir.mkdir(parents=True, exist_ok=True)
    (proj_dir / "conventions.md").write_text(CONVENTIONS, encoding="utf-8")

    runner = fake_repo / "_runner.py"
    runner.write_text(
        "import sys\n"
        "from pathlib import Path\n"
        f"sys.path.insert(0, {str(SCRIPTS_DIR)!r})\n"
        "import project_config\n"
        f"project_config.REPO_ROOT = Path({str(fake_repo)!r})\n"
        "project_config._config = None\n"
        "import backfill_open_plans\n"
        f"sys.argv = [{str(SCRIPT_PATH)!r}] + {list(args)!r}\n"
        "sys.exit(backfill_open_plans.main())\n",
        encoding="utf-8",
    )
    return subprocess.run(
        [sys.executable, str(runner)],
        cwd=str(fake_repo),
        capture_output=True,
        text=True,
        env=dict(os.environ),
    )


def _write_plan(fake_repo: Path, plan_id: str, slug: str, date_str: str) -> Path:
    plans_dir = fake_repo / "_output" / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)
    path = plans_dir / f"plan-{plan_id}-{slug}.md"
    content = (
        f"# Plan {plan_id} | FEATURE-O | {date_str} 10:00 UTC | "
        f"{slug.replace('-', ' ')} | Review: Standard\n"
        "plan_format_version: 1\n"
    )
    path.write_text(content, encoding="utf-8")
    return path


def _read_ledger(fake_repo: Path) -> list[dict]:
    ledger = fake_repo / "_output" / "pending.jsonl"
    if not ledger.is_file():
        return []
    return [
        json.loads(ln)
        for ln in ledger.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]


def test_backfill_files_pending_for_recent_plans(tmp_path):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    _write_plan(tmp_path, "000042", "recent-plan", today)
    r = _run(tmp_path)
    assert r.returncode == 0, r.stderr
    ledger = _read_ledger(tmp_path)
    # One create record for the pending entry.
    assert len(ledger) == 1
    assert ledger[0]["type"] == "implement"
    assert ledger[0]["source"] == "plan-000042"
    assert ledger[0]["status"] == "pending"


def test_backfill_dismisses_old_plans(tmp_path):
    old_date = (datetime.now(timezone.utc) - __import__("datetime").timedelta(days=60))\
        .strftime("%Y-%m-%d")
    _write_plan(tmp_path, "000042", "old-plan", old_date)
    r = _run(tmp_path)
    assert r.returncode == 0, r.stderr
    ledger = _read_ledger(tmp_path)
    # Create + dismiss transition records.
    assert len(ledger) == 2
    assert ledger[0]["status"] == "pending"
    assert ledger[1]["status"] == "dismissed"
    assert "plan older than 30d" in ledger[1].get("reason", "")


def test_backfill_is_idempotent(tmp_path):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    _write_plan(tmp_path, "000042", "recent-plan", today)
    _run(tmp_path)
    before = _read_ledger(tmp_path)
    r = _run(tmp_path)
    after = _read_ledger(tmp_path)
    assert r.returncode == 0, r.stderr
    # Second run should skip — same ledger size.
    assert len(after) == len(before)
    assert "skipped as already tracked" in r.stdout


def test_backfill_dry_run_does_not_mutate(tmp_path):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    _write_plan(tmp_path, "000042", "recent-plan", today)
    r = _run(tmp_path, "--dry-run")
    assert r.returncode == 0, r.stderr
    assert "DRY-RUN" in r.stdout
    # Ledger file should not have been created.
    assert _read_ledger(tmp_path) == []


def test_backfill_respects_existing_dismissed_entries(tmp_path):
    # Simulate a prior session where the user dismissed the entry.
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    _write_plan(tmp_path, "000042", "recent-plan", today)
    # Seed the ledger directly with a dismissed implement entry.
    ledger = tmp_path / "_output" / "pending.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    create = {
        "id": "pa-000001",
        "type": "implement",
        "created_at": "2026-01-01T10:00:00Z",
        "source": "plan-000042",
        "description": "Execute plan-000042 recent plan",
        "status": "pending",
    }
    dismiss = {
        "id": "pa-000001",
        "status": "dismissed",
        "closed_at": "2026-01-05T10:00:00Z",
        "reason": "user decision",
    }
    ledger.write_text(
        json.dumps(create, sort_keys=True) + "\n"
        + json.dumps(dismiss, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    r = _run(tmp_path)
    assert r.returncode == 0, r.stderr
    # Re-running backfill must NOT resurrect the dismissed entry.
    records = _read_ledger(tmp_path)
    assert len(records) == 2  # no new records added
    assert "skipped as already tracked" in r.stdout


def test_backfill_ignores_progress_and_qa_siblings(tmp_path):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    # Main plan file is absent; only progress + qa siblings exist.
    plans_dir = tmp_path / "_output" / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)
    (plans_dir / "plan-000042-progress.md").write_text("# progress\n", encoding="utf-8")
    (plans_dir / "plan-000042-qa-some-title.md").write_text("# qa\n", encoding="utf-8")
    r = _run(tmp_path)
    assert r.returncode == 0, r.stderr
    # No candidates should have been found -- progress + qa are not plans.
    # Actually the backfill regex only matches plan-NNNNNN-*.md, and these do match
    # but _is_sibling() should filter them out. Let me check via ledger:
    assert _read_ledger(tmp_path) == []


def test_backfill_ignores_done_header_plans(tmp_path):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    plans_dir = tmp_path / "_output" / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)
    (plans_dir / "plan-000042-some-title.md").write_text(
        f"# DONE | {today} 11:00 UTC | Plan 000042 | FEATURE-O | {today} 10:00 UTC | some title | Review: Light\n"
        "plan_format_version: 1\n",
        encoding="utf-8",
    )
    r = _run(tmp_path)
    assert r.returncode == 0, r.stderr
    # Done plans should not be filed.
    assert _read_ledger(tmp_path) == []
