"""Tests for pending.py."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
SCRIPT_PATH = SCRIPTS_DIR / "pending.py"

sys.path.insert(0, str(SCRIPTS_DIR))


MINIMAL_CONVENTIONS = """\
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


CONVENTIONS_WITH_REFLECT = """\
# Project Conventions

## Paths

| Variable | Value | Description |
|----------|-------|-------------|
| `OUTPUT_DIR` | `_output` | Output dir |

## Periodic Triggers

| Trigger | Interval (days) | Action type | Description |
|---------|-----------------|-------------|-------------|
| Reflection on practice | 30 | reflect-on-practice | Review patterns from the last 30 days via /reflect |

## Source Directories
"""


def _run_pending(
    fake_repo: Path, *args: str, conventions: str | None = None
) -> subprocess.CompletedProcess:
    """Invoke pending.py in a fake repo with OUTPUT_DIR set to _output."""
    (fake_repo / ".claude").mkdir(exist_ok=True)
    output_dir = fake_repo / "_output"
    output_dir.mkdir(exist_ok=True)

    # Write minimal conventions.md in product-design/ if provided
    proj_dir = fake_repo / "product-design"
    proj_dir.mkdir(parents=True, exist_ok=True)
    if conventions is not None:
        (proj_dir / "conventions.md").write_text(conventions, encoding="utf-8")
    else:
        # Minimal conventions with OUTPUT_DIR
        (proj_dir / "conventions.md").write_text(
            "# Conv\n\n## Paths\n\n| Variable | Value | Description |\n"
            "|----------|-------|-------------|\n"
            "| `OUTPUT_DIR` | `_output` | Output dir |\n",
            encoding="utf-8",
        )

    runner = fake_repo / "_runner.py"
    runner.write_text(
        "import sys\n"
        "from pathlib import Path\n"
        f"sys.path.insert(0, {str(SCRIPTS_DIR)!r})\n"
        "import project_config\n"
        f"project_config.REPO_ROOT = Path({str(fake_repo)!r})\n"
        "project_config._config = None\n"  # force reparse
        "import pending\n"
        f"pending.REPO_ROOT = Path({str(fake_repo)!r})\n"
        f"sys.argv = [{str(SCRIPT_PATH)!r}] + {list(args)!r}\n"
        "sys.exit(pending.main())\n",
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


def _read_ledger(fake_repo: Path) -> list[dict]:
    ledger = fake_repo / "_output" / "pending.jsonl"
    if not ledger.is_file():
        return []
    return [json.loads(ln) for ln in ledger.read_text(encoding="utf-8").splitlines() if ln.strip()]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_add_creates_file(tmp_path):
    r = _run_pending(tmp_path, "add", "--type", "mark-implemented",
                     "--source", "plan-000001", "--description", "test1")
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "_output" / "pending.jsonl").is_file()
    assert r.stdout.strip() == "pa-000001"


def test_add_assigns_sequential_ids(tmp_path):
    _run_pending(tmp_path, "add", "--type", "t", "--source", "s1", "--description", "d1")
    r2 = _run_pending(tmp_path, "add", "--type", "t", "--source", "s2", "--description", "d2")
    assert r2.stdout.strip() == "pa-000002"


def test_list_empty(tmp_path):
    r = _run_pending(tmp_path, "list", "--json")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "[]"


def test_list_pending_after_add(tmp_path):
    _run_pending(tmp_path, "add", "--type", "t", "--source", "s", "--description", "d")
    r = _run_pending(tmp_path, "list", "--json")
    assert r.returncode == 0, r.stderr
    items = json.loads(r.stdout)
    assert len(items) == 1
    assert items[0]["status"] == "pending"


def test_done_transition(tmp_path):
    _run_pending(tmp_path, "add", "--type", "t", "--source", "s", "--description", "d")
    r = _run_pending(tmp_path, "done", "pa-000001")
    assert r.returncode == 0, r.stderr
    r2 = _run_pending(tmp_path, "list", "--status", "done", "--json")
    items = json.loads(r2.stdout)
    assert len(items) == 1
    assert items[0]["status"] == "done"


def test_snooze_transition(tmp_path):
    _run_pending(tmp_path, "add", "--type", "t", "--source", "s", "--description", "d")
    future = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")
    r = _run_pending(tmp_path, "snooze", "pa-000001", "--until", future)
    assert r.returncode == 0, r.stderr
    r2 = _run_pending(tmp_path, "list", "--status", "snoozed", "--json")
    items = json.loads(r2.stdout)
    assert len(items) == 1


def test_due_after_snooze_expires(tmp_path):
    _run_pending(tmp_path, "add", "--type", "t", "--source", "s", "--description", "d")
    past = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    _run_pending(tmp_path, "snooze", "pa-000001", "--until", past)
    r = _run_pending(tmp_path, "list", "--status", "pending", "--json")
    items = json.loads(r.stdout)
    # Snoozed items whose snooze_until has passed auto-expire to pending
    assert len(items) == 1


def test_dismiss_transition(tmp_path):
    _run_pending(tmp_path, "add", "--type", "t", "--source", "s", "--description", "d")
    r = _run_pending(tmp_path, "dismiss", "pa-000001", "--reason", "not needed")
    assert r.returncode == 0, r.stderr
    r2 = _run_pending(tmp_path, "list", "--status", "dismissed", "--json")
    items = json.loads(r2.stdout)
    assert len(items) == 1
    assert items[0]["status"] == "dismissed"


def test_forbidden_transition_dismissed_to_done(tmp_path):
    _run_pending(tmp_path, "add", "--type", "t", "--source", "s", "--description", "d")
    _run_pending(tmp_path, "dismiss", "pa-000001", "--reason", "x")
    r = _run_pending(tmp_path, "done", "pa-000001")
    assert r.returncode == 1
    assert "forbidden transition" in r.stderr


def test_cleanup_auto_dismisses_old_items(tmp_path):
    # Add an item, then manually rewrite ledger with an old created_at
    _run_pending(tmp_path, "add", "--type", "t", "--source", "s", "--description", "d")
    ledger = tmp_path / "_output" / "pending.jsonl"
    records = _read_ledger(tmp_path)
    old_dt = datetime.now(timezone.utc) - timedelta(days=100)
    records[0]["created_at"] = old_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    ledger.write_text(
        "\n".join(json.dumps(r, sort_keys=True) for r in records) + "\n",
        encoding="utf-8",
    )
    r = _run_pending(tmp_path, "cleanup")
    assert r.returncode == 0, r.stderr
    r2 = _run_pending(tmp_path, "list", "--status", "dismissed", "--json")
    items = json.loads(r2.stdout)
    assert len(items) == 1
    assert items[0].get("reason", "").startswith("auto-dismissed")


# ---------------------------------------------------------------------------
# done --source/--type resolver (plan-000408 step 1)
# ---------------------------------------------------------------------------


def test_done_by_source_closes_single_open_entry(tmp_path):
    _run_pending(tmp_path, "add", "--type", "implement",
                 "--source", "plan-000042", "--description", "d")
    r = _run_pending(tmp_path, "done", "--source", "plan-000042",
                     "--type", "implement")
    assert r.returncode == 0, r.stderr
    assert "closed 1" in r.stderr
    items = json.loads(_run_pending(tmp_path, "list", "--status", "done", "--json").stdout)
    assert len(items) == 1


def test_done_by_source_closes_all_matching_open_entries(tmp_path):
    # Two open entries with the same (source, type) pair -- duplicate scenario
    _run_pending(tmp_path, "add", "--type", "implement",
                 "--source", "plan-000042", "--description", "first")
    _run_pending(tmp_path, "add", "--type", "implement",
                 "--source", "plan-000042", "--description", "second")
    r = _run_pending(tmp_path, "done", "--source", "plan-000042",
                     "--type", "implement")
    assert r.returncode == 0, r.stderr
    assert "closed 2" in r.stderr
    items = json.loads(_run_pending(tmp_path, "list", "--status", "done", "--json").stdout)
    assert len(items) == 2


def test_done_by_source_closes_snoozed_entry(tmp_path):
    _run_pending(tmp_path, "add", "--type", "implement",
                 "--source", "plan-000042", "--description", "d")
    future = (datetime.now(timezone.utc) + timedelta(days=5)).strftime("%Y-%m-%d")
    _run_pending(tmp_path, "snooze", "pa-000001", "--until", future)
    r = _run_pending(tmp_path, "done", "--source", "plan-000042",
                     "--type", "implement")
    assert r.returncode == 0, r.stderr
    items = json.loads(_run_pending(tmp_path, "list", "--status", "done", "--json").stdout)
    assert len(items) == 1


def test_done_by_source_ignores_done_and_dismissed_entries(tmp_path):
    _run_pending(tmp_path, "add", "--type", "implement",
                 "--source", "plan-000042", "--description", "d")
    _run_pending(tmp_path, "dismiss", "pa-000001")
    r = _run_pending(tmp_path, "done", "--source", "plan-000042",
                     "--type", "implement")
    assert r.returncode == 0, r.stderr
    # No "closed N" line — was already dismissed
    assert "closed" not in r.stderr


def test_done_by_source_no_match_is_noop(tmp_path):
    # Empty ledger; idempotent no-op
    r = _run_pending(tmp_path, "done", "--source", "plan-000042",
                     "--type", "implement")
    assert r.returncode == 0, r.stderr


def test_done_by_source_is_noop_when_already_done(tmp_path):
    _run_pending(tmp_path, "add", "--type", "implement",
                 "--source", "plan-000042", "--description", "d")
    r1 = _run_pending(tmp_path, "done", "--source", "plan-000042",
                      "--type", "implement")
    assert r1.returncode == 0, r1.stderr
    r2 = _run_pending(tmp_path, "done", "--source", "plan-000042",
                      "--type", "implement")
    # Second call finds no open entries -- exit 0, no "closed" line
    assert r2.returncode == 0, r2.stderr
    assert "closed" not in r2.stderr


def test_done_positional_id_already_done_is_noop(tmp_path):
    _run_pending(tmp_path, "add", "--type", "t", "--source", "s", "--description", "d")
    _run_pending(tmp_path, "done", "pa-000001")
    r = _run_pending(tmp_path, "done", "pa-000001")
    # Idempotent: already-done is a no-op, not a forbidden transition.
    assert r.returncode == 0, r.stderr


# ---------------------------------------------------------------------------
# add --if-absent mode (plan-000408 step 1)
# ---------------------------------------------------------------------------


def test_add_if_absent_adds_when_no_open_entry(tmp_path):
    r = _run_pending(tmp_path, "add", "--if-absent", "--type", "implement",
                     "--source", "plan-000042", "--description", "first")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "pa-000001"


def test_add_if_absent_skips_when_open_entry_exists(tmp_path):
    _run_pending(tmp_path, "add", "--type", "implement",
                 "--source", "plan-000042", "--description", "first")
    r = _run_pending(tmp_path, "add", "--if-absent", "--type", "implement",
                     "--source", "plan-000042", "--description", "second")
    assert r.returncode == 0, r.stderr
    assert "existing open implement entry pa-000001" in r.stderr
    items = json.loads(_run_pending(tmp_path, "list", "--status", "all", "--json").stdout)
    assert len(items) == 1


def test_add_if_absent_adds_when_existing_entry_is_done(tmp_path):
    # Done entries should not block --if-absent from adding a fresh pending entry.
    _run_pending(tmp_path, "add", "--type", "implement",
                 "--source", "plan-000042", "--description", "first")
    _run_pending(tmp_path, "done", "pa-000001")
    r = _run_pending(tmp_path, "add", "--if-absent", "--type", "implement",
                     "--source", "plan-000042", "--description", "second")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "pa-000002"


# ---------------------------------------------------------------------------
# Orphan cleanup for implement (plan-000408 step 5)
# ---------------------------------------------------------------------------


def _prepare_cleanup_repo(tmp_path: Path, plan_files: list[str]) -> None:
    """Create tmp_path with a plans dir populated by the given plan filenames,
    and conventions pointing PLANS_DIR at that dir."""
    plans_dir = tmp_path / "_output" / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)
    for name in plan_files:
        (plans_dir / name).write_text("# placeholder\n", encoding="utf-8")


def _conventions_with_plans_dir() -> str:
    return (
        "# Conv\n\n## Paths\n\n| Variable | Value | Description |\n"
        "|----------|-------|-------------|\n"
        "| `OUTPUT_DIR` | `_output` | Output |\n"
        "| `PLANS_DIR` | `${OUTPUT_DIR}/plans` | Plans |\n"
    )


def test_cleanup_dismisses_implement_with_missing_file(tmp_path):
    _prepare_cleanup_repo(tmp_path, [])  # empty plans dir
    conv = _conventions_with_plans_dir()
    _run_pending(tmp_path, "add", "--type", "implement",
                 "--source", "plan-000042", "--description", "d",
                 conventions=conv)
    r = _run_pending(tmp_path, "cleanup", conventions=conv)
    assert r.returncode == 0, r.stderr
    items = json.loads(_run_pending(tmp_path, "list", "--status", "dismissed",
                                     "--json", conventions=conv).stdout)
    assert len(items) == 1
    assert items[0].get("reason") == "plan file deleted"


def test_cleanup_keeps_implement_with_existing_file(tmp_path):
    _prepare_cleanup_repo(tmp_path, ["plan-000042-some-title.md"])
    conv = _conventions_with_plans_dir()
    _run_pending(tmp_path, "add", "--type", "implement",
                 "--source", "plan-000042", "--description", "d",
                 conventions=conv)
    r = _run_pending(tmp_path, "cleanup", conventions=conv)
    assert r.returncode == 0, r.stderr
    items = json.loads(_run_pending(tmp_path, "list", "--status", "pending",
                                     "--json", conventions=conv).stdout)
    assert len(items) == 1


def test_cleanup_ignores_progress_and_qa_siblings(tmp_path):
    # Only progress + qa siblings present, main plan file deleted.
    _prepare_cleanup_repo(tmp_path, [
        "plan-000042-progress.md",
        "plan-000042-qa-some-title.md",
    ])
    conv = _conventions_with_plans_dir()
    _run_pending(tmp_path, "add", "--type", "implement",
                 "--source", "plan-000042", "--description", "d",
                 conventions=conv)
    r = _run_pending(tmp_path, "cleanup", conventions=conv)
    assert r.returncode == 0, r.stderr
    items = json.loads(_run_pending(tmp_path, "list", "--status", "dismissed",
                                     "--json", conventions=conv).stdout)
    assert len(items) == 1
    assert items[0].get("reason") == "plan file deleted"


def test_cleanup_detects_plan_as_present(tmp_path):
    _prepare_cleanup_repo(tmp_path, ["plan-000042-some-title.md"])
    conv = _conventions_with_plans_dir()
    _run_pending(tmp_path, "add", "--type", "implement",
                 "--source", "plan-000042", "--description", "d",
                 conventions=conv)
    r = _run_pending(tmp_path, "cleanup", conventions=conv)
    assert r.returncode == 0, r.stderr
    # Entry should still be pending -- plan file present regardless of # DONE header.
    items = json.loads(_run_pending(tmp_path, "list", "--status", "pending",
                                     "--json", conventions=conv).stdout)
    assert len(items) == 1


# ---------------------------------------------------------------------------
# status JSON: implement overdue fields (plan-000408 step 6)
# ---------------------------------------------------------------------------


def _conventions_with_ep_threshold(threshold: int) -> str:
    return (
        "# Conv\n\n## Paths\n\n| Variable | Value | Description |\n"
        "|----------|-------|-------------|\n"
        "| `OUTPUT_DIR` | `_output` | Output |\n"
        "| `PLANS_DIR` | `${OUTPUT_DIR}/plans` | Plans |\n"
        "\n## Periodic Triggers\n\n"
        "| Trigger | Interval (days) | Action type | Description |\n"
        "|---------|-----------------|-------------|-------------|\n"
        f"| Pending plan age escalation | {threshold} | implement | threshold |\n"
    )


def test_status_reports_implement_overdue(tmp_path):
    conv = _conventions_with_ep_threshold(30)
    _prepare_cleanup_repo(tmp_path, ["plan-000042-some.md"])
    _run_pending(tmp_path, "add", "--type", "implement",
                 "--source", "plan-000042", "--description", "d",
                 conventions=conv)
    # Rewrite created_at to be 40 days old -> overdue with 30d threshold.
    ledger = tmp_path / "_output" / "pending.jsonl"
    old = (datetime.now(timezone.utc) - timedelta(days=40)).strftime("%Y-%m-%dT%H:%M:%SZ")
    recs = _read_ledger(tmp_path)
    recs[0]["created_at"] = old
    ledger.write_text("\n".join(json.dumps(r, sort_keys=True) for r in recs) + "\n",
                      encoding="utf-8")
    r = _run_pending(tmp_path, "status", "--json", conventions=conv)
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["implement_overdue_threshold_days"] == 30
    assert payload["implement_overdue_count"] == 1
    assert len(payload["implement_overdue"]) == 1
    assert payload["implement_overdue"][0]["source"] == "plan-000042"


def test_status_respects_custom_threshold(tmp_path):
    conv = _conventions_with_ep_threshold(7)
    _prepare_cleanup_repo(tmp_path, ["plan-000042-some.md"])
    _run_pending(tmp_path, "add", "--type", "implement",
                 "--source", "plan-000042", "--description", "d",
                 conventions=conv)
    ledger = tmp_path / "_output" / "pending.jsonl"
    old = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
    recs = _read_ledger(tmp_path)
    recs[0]["created_at"] = old
    ledger.write_text("\n".join(json.dumps(r, sort_keys=True) for r in recs) + "\n",
                      encoding="utf-8")
    r = _run_pending(tmp_path, "status", "--json", conventions=conv)
    payload = json.loads(r.stdout)
    assert payload["implement_overdue_threshold_days"] == 7
    assert payload["implement_overdue_count"] == 1


def test_status_threshold_default_when_conventions_missing_row(tmp_path):
    # Conventions has no Pending plan age escalation row -> falls back to 30.
    conv = (
        "# Conv\n\n## Paths\n\n| Variable | Value | Description |\n"
        "|----------|-------|-------------|\n"
        "| `OUTPUT_DIR` | `_output` | Output |\n"
        "| `PLANS_DIR` | `${OUTPUT_DIR}/plans` | Plans |\n"
    )
    _prepare_cleanup_repo(tmp_path, ["plan-000042-some.md"])
    _run_pending(tmp_path, "add", "--type", "implement",
                 "--source", "plan-000042", "--description", "d",
                 conventions=conv)
    r = _run_pending(tmp_path, "status", "--json", conventions=conv)
    payload = json.loads(r.stdout)
    assert payload["implement_overdue_threshold_days"] == 30
    # Fallback warning is present since implement has entries.
    assert any(
        "pending plan age escalation threshold not configured" in w
        for w in payload.get("warnings", [])
    )


def test_reducer_last_write_wins(tmp_path):
    _run_pending(tmp_path, "add", "--type", "t", "--source", "s", "--description", "orig")
    future = (datetime.now(timezone.utc) + timedelta(days=10)).strftime("%Y-%m-%d")
    _run_pending(tmp_path, "snooze", "pa-000001", "--until", future)
    r = _run_pending(tmp_path, "list", "--status", "all", "--json")
    items = json.loads(r.stdout)
    assert len(items) == 1
    assert items[0]["status"] == "snoozed"
    assert items[0]["snooze_until"] == future


def test_periodic_check_creates_entries_on_first_run(tmp_path):
    r = _run_pending(tmp_path, "periodic-check", conventions=MINIMAL_CONVENTIONS)
    assert r.returncode == 0, r.stderr
    r2 = _run_pending(tmp_path, "list", "--status", "all", "--json",
                      conventions=MINIMAL_CONVENTIONS)
    items = json.loads(r2.stdout)
    types = {i["type"] for i in items}
    assert "periodic-curation" in types
    assert "spec-drift-check" in types


def test_periodic_check_respects_interval(tmp_path):
    _run_pending(tmp_path, "periodic-check", conventions=MINIMAL_CONVENTIONS)
    _run_pending(tmp_path, "periodic-check", conventions=MINIMAL_CONVENTIONS)
    r = _run_pending(tmp_path, "list", "--status", "all", "--json",
                     conventions=MINIMAL_CONVENTIONS)
    items = json.loads(r.stdout)
    # Should still be exactly 2 (one per trigger) -- second run should skip
    assert len(items) == 2


def test_periodic_check_recreates_after_interval_elapses(tmp_path):
    _run_pending(tmp_path, "periodic-check", conventions=MINIMAL_CONVENTIONS)
    # Mark both as done with old closed_at
    _run_pending(tmp_path, "done", "pa-000001", conventions=MINIMAL_CONVENTIONS)
    _run_pending(tmp_path, "done", "pa-000002", conventions=MINIMAL_CONVENTIONS)
    # Rewrite ledger to set closed_at to 40 days ago
    ledger = tmp_path / "_output" / "pending.jsonl"
    old_iso = (datetime.now(timezone.utc) - timedelta(days=40)).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = ledger.read_text(encoding="utf-8").splitlines()
    new_lines = []
    for ln in lines:
        if not ln.strip():
            continue
        rec = json.loads(ln)
        if rec.get("status") == "done":
            rec["closed_at"] = old_iso
        new_lines.append(json.dumps(rec, sort_keys=True))
    ledger.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    _run_pending(tmp_path, "periodic-check", conventions=MINIMAL_CONVENTIONS)
    r = _run_pending(tmp_path, "list", "--status", "pending", "--json",
                     conventions=MINIMAL_CONVENTIONS)
    items = json.loads(r.stdout)
    # After recreating, should have 2 new pending items (one per trigger whose
    # last closure is older than interval)
    types = {i["type"] for i in items}
    # Spec-drift-check interval is 14 days, and periodic-curation is 30 days;
    # both <40 days ago, so both recreate.
    assert "spec-drift-check" in types
    assert "periodic-curation" in types


def test_cold_repo_silent(tmp_path):
    # No periodic triggers section present
    r = _run_pending(tmp_path, "periodic-check", conventions="# No triggers here\n")
    assert r.returncode == 0
    r2 = _run_pending(tmp_path, "list", "--json", conventions="# No triggers here\n")
    assert r2.returncode == 0
    assert r2.stdout.strip() == "[]"


def test_status_subcommand_happy_path(tmp_path):
    _run_pending(tmp_path, "add", "--type", "t1", "--source", "plan-1", "--description", "one")
    _run_pending(tmp_path, "add", "--type", "t2", "--source", "plan-2", "--description", "two")
    r = _run_pending(tmp_path, "status", "--json", "--overdue-days", "14")
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["count"] == 2
    assert payload["overdue_count"] == 0
    assert len(payload["top_3"]) == 2
    assert payload["top_3"][0]["source"] == "plan-1"


# ---------------------------------------------------------------------------
# reflect-on-practice periodic trigger (stamp-based dispatch)
# ---------------------------------------------------------------------------


def _reflect_stamp(fake_repo: Path) -> Path:
    return fake_repo / "_output" / ".reflect-on-practice-stamp"


def test_reflect_on_practice_first_run_creates_action_and_stamp(tmp_path):
    r = _run_pending(
        tmp_path, "periodic-check", "--json", conventions=CONVENTIONS_WITH_REFLECT
    )
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["warnings"] == []
    created_types = {item["type"] for item in payload["created"]}
    assert "reflect-on-practice" in created_types
    # Stamp file should exist after a clean run
    assert _reflect_stamp(tmp_path).is_file()
    # Ledger should contain the new pending action
    ledger = _read_ledger(tmp_path)
    reflect_items = [r for r in ledger if r.get("type") == "reflect-on-practice"]
    assert len(reflect_items) == 1
    assert reflect_items[0]["source"] == "periodic-trigger"
    assert reflect_items[0]["status"] == "pending"
    assert "/reflect" in reflect_items[0]["description"]


def test_reflect_on_practice_inside_interval_skips(tmp_path):
    # Prime the stamp by running once
    _run_pending(
        tmp_path, "periodic-check", "--json", conventions=CONVENTIONS_WITH_REFLECT
    )
    # Set stamp to 5 days ago (inside the 30-day interval)
    stamp = _reflect_stamp(tmp_path)
    assert stamp.is_file()
    five_days_ago = (datetime.now() - timedelta(days=5)).timestamp()
    os.utime(stamp, (five_days_ago, five_days_ago))
    # Dismiss the first item so the no-duplicate-open-pending guard doesn't
    # mask the interval logic we're testing.
    _run_pending(tmp_path, "dismiss", "pa-000001", "--reason", "t",
                 conventions=CONVENTIONS_WITH_REFLECT)
    # Run again
    r = _run_pending(
        tmp_path, "periodic-check", "--json", conventions=CONVENTIONS_WITH_REFLECT
    )
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    created_types = {item["type"] for item in payload["created"]}
    assert "reflect-on-practice" not in created_types
    # Ledger should still contain only the one original action
    ledger = _read_ledger(tmp_path)
    reflect_items = [r for r in ledger if r.get("type") == "reflect-on-practice"]
    # One creation + one dismissal event, but only one unique id
    ids = {r.get("id") for r in reflect_items}
    assert ids == {"pa-000001"}


def test_reflect_on_practice_after_interval_creates(tmp_path):
    _run_pending(
        tmp_path, "periodic-check", "--json", conventions=CONVENTIONS_WITH_REFLECT
    )
    # Dismiss the first item so the no-duplicate guard allows a new creation
    _run_pending(tmp_path, "dismiss", "pa-000001", "--reason", "t",
                 conventions=CONVENTIONS_WITH_REFLECT)
    # Set stamp to 35 days ago (beyond the 30-day interval)
    stamp = _reflect_stamp(tmp_path)
    thirty_five_days_ago = (datetime.now() - timedelta(days=35)).timestamp()
    os.utime(stamp, (thirty_five_days_ago, thirty_five_days_ago))
    r = _run_pending(
        tmp_path, "periodic-check", "--json", conventions=CONVENTIONS_WITH_REFLECT
    )
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    created_types = {item["type"] for item in payload["created"]}
    assert "reflect-on-practice" in created_types
    # Stamp should be refreshed (mtime newer than 35 days ago)
    new_mtime = stamp.stat().st_mtime
    assert new_mtime > thirty_five_days_ago + 60  # updated well past the old value


def test_reflect_on_practice_stamp_write_failure_degrades_gracefully(tmp_path):
    # Simulate stamp-write failure by replacing the stamp path with a
    # read-only directory so write_text raises OSError.
    output_dir = tmp_path / "_output"
    output_dir.mkdir(exist_ok=True)
    stamp_path = output_dir / ".reflect-on-practice-stamp"
    # Create the stamp path as a directory -- writing to it as a file will fail
    stamp_path.mkdir()
    r = _run_pending(
        tmp_path, "periodic-check", "--json", conventions=CONVENTIONS_WITH_REFLECT
    )
    # Exit 0 even though stamp write failed
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    # Warning about stamp write failure
    warnings_text = " ".join(payload["warnings"])
    assert "reflect-on-practice" in warnings_text
    # Pending action should still have been created (stamp failure is non-fatal)
    ledger = _read_ledger(tmp_path)
    reflect_items = [r for r in ledger if r.get("type") == "reflect-on-practice"]
    assert len(reflect_items) == 1


def test_status_subcommand_stamp_throttling(tmp_path):
    # First call creates stamps
    _run_pending(tmp_path, "add", "--type", "t", "--source", "s", "--description", "d")
    _run_pending(tmp_path, "status", "--json")
    cleanup_stamp = tmp_path / "_output" / ".pending-cleanup-stamp"
    assert cleanup_stamp.is_file()
    # Set stamp mtime to 1 hour ago -- cleanup should NOT run (24h throttle)
    one_hour_ago = (datetime.now() - timedelta(hours=1)).timestamp()
    os.utime(cleanup_stamp, (one_hour_ago, one_hour_ago))
    mtime_before = cleanup_stamp.stat().st_mtime
    _run_pending(tmp_path, "status", "--json")
    mtime_after = cleanup_stamp.stat().st_mtime
    assert abs(mtime_after - mtime_before) < 1.0  # unchanged

    # Set stamp to 25 hours ago -- cleanup SHOULD run
    twenty_five_hours_ago = (datetime.now() - timedelta(hours=25)).timestamp()
    os.utime(cleanup_stamp, (twenty_five_hours_ago, twenty_five_hours_ago))
    _run_pending(tmp_path, "status", "--json")
    mtime_after2 = cleanup_stamp.stat().st_mtime
    assert mtime_after2 > twenty_five_hours_ago + 10  # updated


# ---------------------------------------------------------------------------
# --formatted output mode (plan-000534)
# ---------------------------------------------------------------------------


def _make_old_ledger(tmp_path: Path, entries: list[dict], age_days: int = 0) -> None:
    """Write entries to the pending ledger with created_at set to age_days ago."""
    ledger = tmp_path / "_output" / "pending.jsonl"
    (tmp_path / "_output").mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    lines = []
    for i, entry in enumerate(entries, start=1):
        rec = {
            "id": f"pa-{i:06d}",
            "type": entry.get("type", "generic"),
            "created_at": (now - timedelta(days=entry.get("age_days", age_days))).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "source": entry.get("source", f"src-{i}"),
            "description": entry.get("description", f"desc {i}"),
            "status": "pending",
            "snooze_until": None,
            "last_reminded_at": None,
        }
        lines.append(json.dumps(rec, sort_keys=True))
    ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _minimal_conv_no_triggers() -> str:
    return (
        "# Conv\n\n## Paths\n\n| Variable | Value | Description |\n"
        "|----------|-------|-------------|\n"
        "| `OUTPUT_DIR` | `_output` | Output dir |\n"
    )


def test_status_formatted_empty(tmp_path):
    """No pending items: --formatted outputs empty string (silent)."""
    r = _run_pending(tmp_path, "status", "--formatted",
                     conventions=_minimal_conv_no_triggers())
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == ""


def test_status_formatted_publish_banner(tmp_path):
    """Publish items: verify overdue and non-overdue lines with correct emoji and phrasing."""
    conv = _minimal_conv_no_triggers()
    # One overdue publish (age > 3 days) and one non-overdue publish (age 1 day).
    _make_old_ledger(tmp_path, [
        {"type": "generic", "source": "plan-001", "description": "PUBLISH: v1.0.0 tag",
         "age_days": 5},
        {"type": "generic", "source": "plan-002", "description": "PUBLISH: v0.9.0 tag",
         "age_days": 1},
    ])
    r = _run_pending(tmp_path, "status", "--formatted", conventions=conv)
    assert r.returncode == 0, r.stderr
    output = r.stdout
    # Overdue line
    assert "⚠️ OVERDUE publish" in output
    assert "v1.0.0 tag" in output
    assert "5 days ago" in output
    assert "sync-runbook.md" in output
    # Non-overdue line
    assert "⏳ Pending publish" in output
    assert "v0.9.0 tag" in output
    assert "1 days ago" in output


def test_status_formatted_implement_banner(tmp_path):
    """Implement items: verify overdue/non-overdue lines, cap at 5, overflow line."""
    conv = _conventions_with_ep_threshold(30)
    _prepare_cleanup_repo(tmp_path, [
        f"plan-{n:06d}-some.md" for n in range(1, 8)
    ])
    # 2 overdue (age 40 days) + 5 non-overdue (age 1 day) = 7 implement items.
    entries = []
    for n in range(1, 3):
        entries.append({
            "type": "implement",
            "source": f"plan-{n:06d}",
            "description": f"overdue plan {n}",
            "age_days": 40,
        })
    for n in range(3, 8):
        entries.append({
            "type": "implement",
            "source": f"plan-{n:06d}",
            "description": f"pending plan {n}",
            "age_days": 1,
        })
    _make_old_ledger(tmp_path, entries)
    r = _run_pending(tmp_path, "status", "--formatted", conventions=conv)
    assert r.returncode == 0, r.stderr
    output = r.stdout
    # Overdue lines present
    assert "⚠️ OVERDUE plan" in output
    assert "overdue plan 1" in output
    # Non-overdue lines present (cap means at most 5 total lines emitted)
    assert "⏳ Pending plan" in output
    # Overflow line present (7 total, capped at 5 -> 2 remaining)
    assert "… and 2 more" in output
    assert "/pending" in output


def test_status_formatted_generic_notice(tmp_path):
    """Generic notice: one-line notice (1-5, no overdue) and warning block (>5 or overdue)."""
    conv = _minimal_conv_no_triggers()

    # Case 1: count=3, no overdue -> one-line notice.
    _make_old_ledger(tmp_path, [
        {"type": "t", "source": f"s{i}", "description": f"desc {i}", "age_days": 1}
        for i in range(3)
    ])
    r = _run_pending(tmp_path, "status", "--formatted", "--overdue-days", "30",
                     conventions=conv)
    assert r.returncode == 0, r.stderr
    assert "You have 3 pending actions (run /pending to view)." in r.stdout
    # Should NOT contain "Top 3 by age" for this case
    assert "Top 3 by age" not in r.stdout

    # Case 2: count=6, no overdue -> warning block with top-3.
    _make_old_ledger(tmp_path, [
        {"type": "t", "source": f"s{i}", "description": f"desc {i}", "age_days": 1}
        for i in range(6)
    ])
    r2 = _run_pending(tmp_path, "status", "--formatted", "--overdue-days", "30",
                      conventions=conv)
    assert r2.returncode == 0, r2.stderr
    output2 = r2.stdout
    assert "You have 6 pending actions" in output2
    assert "Top 3 by age" in output2
    # Three bullet items
    assert output2.count("  - [") >= 3

    # Case 3: count=2 with 1 overdue -> warning block.
    _make_old_ledger(tmp_path, [
        {"type": "t", "source": "s0", "description": "overdue one", "age_days": 40},
        {"type": "t", "source": "s1", "description": "fresh one", "age_days": 1},
    ])
    r3 = _run_pending(tmp_path, "status", "--formatted", "--overdue-days", "30",
                      conventions=conv)
    assert r3.returncode == 0, r3.stderr
    assert "2 pending actions (1 overdue)" in r3.stdout
    assert "Top 3 by age" in r3.stdout


def test_status_formatted_warnings(tmp_path):
    """Cleanup/periodic warning lines are appended with 'Warning: ' prefix."""
    # Provide no conventions so periodic-check fails to find triggers, but
    # use a convention that still has OUTPUT_DIR. Also pre-add an implement
    # entry without the escalation threshold row so the threshold-default
    # warning fires.
    conv = (
        "# Conv\n\n## Paths\n\n| Variable | Value | Description |\n"
        "|----------|-------|-------------|\n"
        "| `OUTPUT_DIR` | `_output` | Output |\n"
        "| `PLANS_DIR` | `${OUTPUT_DIR}/plans` | Plans |\n"
    )
    _prepare_cleanup_repo(tmp_path, ["plan-000001-some.md"])
    _make_old_ledger(tmp_path, [
        {"type": "implement", "source": "plan-000001",
         "description": "implement something", "age_days": 1},
    ])
    r = _run_pending(tmp_path, "status", "--formatted", conventions=conv)
    assert r.returncode == 0, r.stderr
    # The implement entry has no threshold row -> default warning fires.
    assert "Warning: pending plan age escalation threshold not configured" in r.stdout


def test_status_formatted_beats_json(tmp_path):
    """When both --formatted and --json are passed, output is not JSON."""
    _make_old_ledger(tmp_path, [
        {"type": "t", "source": "s", "description": "desc", "age_days": 1}
    ])
    r = _run_pending(tmp_path, "status", "--formatted", "--json",
                     conventions=_minimal_conv_no_triggers())
    assert r.returncode == 0, r.stderr
    # Output should NOT be a JSON object (--formatted wins)
    try:
        json.loads(r.stdout)
        is_json = True
    except (json.JSONDecodeError, ValueError):
        is_json = False
    assert not is_json, "expected non-JSON output when --formatted is passed alongside --json"


# ---------------------------------------------------------------------------
# --format banner output mode (plan-000541)
# ---------------------------------------------------------------------------


def test_format_banner_empty(tmp_path):
    """No pending items: --format banner outputs empty string (silent)."""
    r = _run_pending(tmp_path, "status", "--format", "banner",
                     conventions=_minimal_conv_no_triggers())
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == ""


def test_format_banner_publish(tmp_path):
    """Publish items via --format banner produce same output as --formatted."""
    conv = _minimal_conv_no_triggers()
    _make_old_ledger(tmp_path, [
        {"type": "generic", "source": "plan-001", "description": "PUBLISH: v1.0.0 tag",
         "age_days": 5},
    ])
    r = _run_pending(tmp_path, "status", "--format", "banner", conventions=conv)
    assert r.returncode == 0, r.stderr
    assert "OVERDUE publish" in r.stdout
    assert "v1.0.0 tag" in r.stdout


def test_format_banner_implement(tmp_path):
    """Implement items via --format banner with cap and overflow."""
    conv = _conventions_with_ep_threshold(30)
    _prepare_cleanup_repo(tmp_path, [
        f"plan-{n:06d}-some.md" for n in range(1, 4)
    ])
    _make_old_ledger(tmp_path, [
        {"type": "implement", "source": f"plan-{n:06d}",
         "description": f"plan {n}", "age_days": 1}
        for n in range(1, 4)
    ])
    r = _run_pending(tmp_path, "status", "--format", "banner", conventions=conv)
    assert r.returncode == 0, r.stderr
    assert "Pending plan" in r.stdout


def test_format_banner_generic_low_count(tmp_path):
    """--format banner with 1-5 items and no overdue produces one-line notice."""
    conv = _minimal_conv_no_triggers()
    _make_old_ledger(tmp_path, [
        {"type": "t", "source": f"s{i}", "description": f"desc {i}", "age_days": 1}
        for i in range(2)
    ])
    r = _run_pending(tmp_path, "status", "--format", "banner", "--overdue-days", "30",
                     conventions=conv)
    assert r.returncode == 0, r.stderr
    assert "You have 2 pending actions (run /pending to view)." in r.stdout


def test_format_banner_overdue(tmp_path):
    """--format banner with overdue items produces warning block."""
    conv = _minimal_conv_no_triggers()
    _make_old_ledger(tmp_path, [
        {"type": "t", "source": "s0", "description": "old one", "age_days": 40},
        {"type": "t", "source": "s1", "description": "new one", "age_days": 1},
    ])
    r = _run_pending(tmp_path, "status", "--format", "banner", "--overdue-days", "30",
                     conventions=conv)
    assert r.returncode == 0, r.stderr
    assert "2 pending actions (1 overdue)" in r.stdout
    assert "Top 3 by age" in r.stdout


def test_format_json_explicit(tmp_path):
    """--format json produces JSON output."""
    conv = _minimal_conv_no_triggers()
    _make_old_ledger(tmp_path, [
        {"type": "t", "source": "s", "description": "desc", "age_days": 1}
    ])
    r = _run_pending(tmp_path, "status", "--format", "json", conventions=conv)
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["count"] == 1


def test_format_banner_overrides_json_flag(tmp_path):
    """--format banner overrides --json flag."""
    conv = _minimal_conv_no_triggers()
    _make_old_ledger(tmp_path, [
        {"type": "t", "source": "s", "description": "desc", "age_days": 1}
    ])
    r = _run_pending(tmp_path, "status", "--format", "banner", "--json",
                     conventions=conv)
    assert r.returncode == 0, r.stderr
    try:
        json.loads(r.stdout)
        is_json = True
    except (json.JSONDecodeError, ValueError):
        is_json = False
    assert not is_json, "--format banner should override --json"
