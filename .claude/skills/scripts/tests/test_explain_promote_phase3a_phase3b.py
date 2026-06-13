"""Tests for the /explain spec-drift --promote Phase 3a/3b workflow.

The workflow itself is defined in .claude/skills/explain/SKILL.md (Step C) and
is executed by an agent orchestrating apply_marker.py + pending.py. These tests
exercise the load-bearing mechanics:

- Phase 3a: proposal-report generation, single-entry pending-action creation, dedup
- Phase 3b: heading-only grep (designer-voice preservation), STATUS marker flip
  via apply_marker.py, tolerant missing-entries handling, 2-branch lifecycle
  closure on the pending ledger (all-present AND all-flipped combined gate).

Amendments covered: A1 (legacy uppercase), A3 (partial completion + dedup +
lifecycle), A4 (heading-form enforcement + command syntax), A5 (extended test
matrix). plan-000470 R1 collapsed the Phase 3a entry pair to a single
`apply-promote-markers` entry with copy-prose instructions folded in.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
APPLY_MARKER = SCRIPTS_DIR / "apply_marker.py"
PENDING = SCRIPTS_DIR / "pending.py"

sys.path.insert(0, str(SCRIPTS_DIR))


# ---------------------------------------------------------------------------
# Fixtures -- fake repo layout with a product-design-as-intended.md registered as Human
# (markers), plus an OUTPUT_DIR so pending.py and the proposal writer have a
# place to land files.
# ---------------------------------------------------------------------------


DESIGN_INTENT_BASELINE = """\
# Project Design Intent

## 0. Planned Changes

Stub.

---

## 2. Entity Hierarchy

<!-- REQ-ENT-001 -->
### Task

A sample entity used by integration tests.

---

## Decisions

<!-- STATUS: proposed -->
### D-001: Use PostgreSQL as primary datastore

**Context**: We need a primary datastore for the task service.

**Decision**: Adopt PostgreSQL 15.

**Consequences**: Requires a migration framework; enables rich JSON querying.

---

## CHANGELOG

2026-04-10 | D-001 | added | - | initial entry for fixture
"""


DESIGN_INTENT_WITH_IMPLEMENTED = DESIGN_INTENT_BASELINE.replace(
    "<!-- STATUS: proposed -->\n### D-001:",
    "<!-- STATUS: implemented | plan-000268 | 2026-04-10 -->\n### D-001:",
)


DESIGN_INTENT_WITH_LEGACY_UPPERCASE = DESIGN_INTENT_BASELINE.replace(
    "<!-- STATUS: proposed -->\n### D-001:",
    "<!-- STATUS: IMPLEMENTED | plan-000260 | 2026-01-15 -->\n### D-001:",
)


DESIGN_INTENT_THREE_DECISIONS = """\
# Project Design Intent

## Decisions

<!-- STATUS: implemented | plan-000268 | 2026-04-10 -->
### D-001: Use PostgreSQL

**Context**: C.
**Decision**: D.
**Consequences**: Cs.

<!-- STATUS: implemented | plan-000268 | 2026-04-10 -->
### D-002: Use FastAPI

**Context**: C.
**Decision**: D.
**Consequences**: Cs.

<!-- STATUS: proposed -->
### D-003: (draft, not yet copied by designer)

Placeholder for the partial-completion test.

---

## CHANGELOG

2026-04-10 | D-001 | added | - | initial
2026-04-10 | D-002 | added | - | initial
2026-04-10 | D-003 | added | - | draft
"""


DESIGN_INTENT_NON_COLON_HEADING = DESIGN_INTENT_BASELINE.replace(
    "### D-001: Use PostgreSQL as primary datastore",
    "### D-001 - Use PostgreSQL as primary datastore",
)


@pytest.fixture
def fake_repo(tmp_path):
    """Build a fake repo layout at tmp_path with a product-design-as-intended.md fixture."""
    (tmp_path / ".claude").mkdir()
    rel = "_references/project/product-design-as-intended.md"
    target = tmp_path / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(DESIGN_INTENT_BASELINE, encoding="utf-8")

    # pending.py and the proposal writer both need an OUTPUT_DIR
    (tmp_path / "_output").mkdir()
    (tmp_path / "_output" / "promote-proposals").mkdir()

    return tmp_path, rel, target


def _write_design_intent(target: Path, content: str) -> None:
    target.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Subprocess harness -- a small runner that patches REPO_ROOT + registry +
# OUTPUT_DIR before calling the target script's main().
# ---------------------------------------------------------------------------


def _make_runner(
    tmp_path: Path,
    script_path: Path,
    rel_file: str,
    argv_tail: list[str],
    *,
    import_module: str,
) -> Path:
    runner = tmp_path / f"_runner_{import_module}.py"
    runner.write_text(
        "import sys\n"
        "from pathlib import Path\n"
        f"sys.path.insert(0, {str(SCRIPTS_DIR)!r})\n"
        "import project_config\n"
        f"project_config.REPO_ROOT = Path({str(tmp_path)!r})\n"
        "project_config._warned_missing = True\n"
        "project_config._config = {'OUTPUT_DIR': '_output'}\n"
        "import human_markers_registry\n"
        f"human_markers_registry.HUMAN_MARKERS_FILES = [{rel_file!r}]\n"
        f"import {import_module}\n"
        f"{import_module}.REPO_ROOT = Path({str(tmp_path)!r})\n"
        f"sys.argv = [{str(script_path)!r}] + {argv_tail!r}\n"
        f"sys.exit({import_module}.main())\n",
        encoding="utf-8",
    )
    return runner


def _run_apply_marker(
    tmp_path: Path, rel_file: str, *args: str
) -> subprocess.CompletedProcess:
    runner = _make_runner(
        tmp_path, APPLY_MARKER, rel_file, list(args), import_module="apply_marker"
    )
    return subprocess.run(
        [sys.executable, str(runner)],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
    )


def _run_pending(
    tmp_path: Path, rel_file: str, *args: str
) -> subprocess.CompletedProcess:
    runner = _make_runner(
        tmp_path, PENDING, rel_file, list(args), import_module="pending"
    )
    return subprocess.run(
        [sys.executable, str(runner)],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# Phase 3a / Phase 3b orchestration helpers
#
# These mirror the logic described in .claude/skills/explain/SKILL.md Step C.
# The agent performs this orchestration in production; here we reproduce it
# in Python so the load-bearing pieces (proposal writer, dedup, heading-only
# grep, lifecycle updates) can be tested deterministically.
# ---------------------------------------------------------------------------


_DECISION_HEADING_ONLY_RE = re.compile(r"^###\s+(D-\d+)(?::|\s*$)", re.MULTILINE)
_STATUS_IMPLEMENTED_RE = re.compile(
    r"<!--\s*STATUS:\s*(?:implemented|IMPLEMENTED)(?:\s*\|[^>]*)?\s*-->"
)


def phase3a_generate_proposal(
    tmp_path: Path,
    rel_file: str,
    plan_id: str,
    decisions: list[dict],
) -> Path:
    """Write a promote proposal report for the given plan."""
    proposal_dir = tmp_path / "_output" / "promote-proposals"
    proposal_dir.mkdir(parents=True, exist_ok=True)
    out = proposal_dir / f"promote-proposal-{plan_id}.md"
    lines = [
        f"# Promote proposal for {plan_id}",
        "",
        f"Source plan: {plan_id}",
        "",
        "Review, edit to your voice, copy accepted entries into "
        "`_references/project/product-design-as-intended.md § Decisions`, then run "
        f"`/explain spec-drift --promote --apply-markers {plan_id}`.",
        "",
    ]
    for d in decisions:
        lines.extend(
            [
                "```markdown",
                "<!-- STATUS: implemented | " + plan_id + " | 2026-04-10 -->",
                f"### {d['id']}: {d['title']}",
                "",
                f"**Context**: {d['context']}",
                "",
                f"**Decision**: {d['decision']}",
                "",
                f"**Consequences**: {d['consequences']}",
                "```",
                "",
            ]
        )
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def phase3a_pending_dedup_check(
    tmp_path: Path, rel_file: str, plan_id: str
) -> bool:
    """Return True if an `apply-promote-markers` entry with source=plan-id is
    already pending (dedup: do NOT add a duplicate entry in that case)."""
    result = _run_pending(
        tmp_path,
        rel_file,
        "list",
        "--status",
        "pending",
        "--type",
        "apply-promote-markers",
        "--source",
        plan_id,
        "--json",
    )
    if result.returncode != 0:
        return False
    try:
        records = json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        return False
    return len(records) > 0


def phase3a_add_pending_actions(
    tmp_path: Path, rel_file: str, plan_id: str, proposal_path: Path
) -> str | None:
    """Add the single pending action (`apply-promote-markers`) with copy-prose
    instructions folded into its description, deduped against any already-
    pending entry for the same plan-id. Returns markers_id or None if deduped."""
    if phase3a_pending_dedup_check(tmp_path, rel_file, plan_id):
        return None

    result = _run_pending(
        tmp_path,
        rel_file,
        "add",
        "--type",
        "apply-promote-markers",
        "--source",
        plan_id,
        "--description",
        f"Copy draft Decision entries from {proposal_path.name} into "
        "product-design-as-intended.md § Decisions, then run "
        f"/explain spec-drift --promote --apply-markers {plan_id} to flip "
        "STATUS markers (Phase 3b)",
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def phase3b_heading_only_grep(
    target: Path, proposed_ids: list[str]
) -> tuple[list[str], list[str]]:
    """Split proposed IDs into (present, missing) using a heading-only grep.

    Matches ONLY `### D-NNN:` and `### D-NNN` (EOL) — never prose or title
    text. This preserves the designer's voice per advisory-000264 Q4.
    """
    text = target.read_text(encoding="utf-8")
    found = set(m.group(1) for m in _DECISION_HEADING_ONLY_RE.finditer(text))
    present = [d for d in proposed_ids if d in found]
    missing = [d for d in proposed_ids if d not in found]
    return present, missing


def phase3b_flip_markers(
    tmp_path: Path,
    rel_file: str,
    target: Path,
    plan_id: str,
    present_ids: list[str],
) -> list[str]:
    """Invoke apply_marker.py on each present ID; return list of successful IDs."""
    ok: list[str] = []
    for did in present_ids:
        result = _run_apply_marker(
            tmp_path,
            rel_file,
            "--file",
            str(target),
            "--id",
            did,
            "--marker",
            "STATUS",
            "--value",
            "established",
            "--plan",
            plan_id,
            "--date",
            "2026-04-10",
        )
        if result.returncode == 0:
            ok.append(did)
    return ok


def phase3b_update_lifecycle(
    tmp_path: Path,
    rel_file: str,
    markers_id: str | None,
    proposed: list[str],
    present: list[str],
    flipped: list[str],
) -> None:
    """Close the `apply-promote-markers` ledger entry per the 2-branch gate
    (plan-000470 R1): all proposed D-NNNs present AND every present item
    flipped. Otherwise leave pending (the proposal file on disk is the
    partial-copy audit trail)."""
    missing = [p for p in proposed if p not in present]
    all_present = not missing
    all_flipped = set(present) == set(flipped)

    if markers_id and all_present and all_flipped:
        _run_pending(tmp_path, rel_file, "done", markers_id)


def _list_pending(
    tmp_path: Path, rel_file: str, *, type_filter: str | None = None
) -> list[dict]:
    args = ["list", "--status", "all", "--json"]
    if type_filter:
        args += ["--type", type_filter]
    result = _run_pending(tmp_path, rel_file, *args)
    if result.returncode != 0:
        return []
    try:
        return json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        return []


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def _sample_decisions() -> list[dict]:
    return [
        {
            "id": "D-010",
            "title": "Use PostgreSQL as primary datastore",
            "context": "We need a primary datastore.",
            "decision": "Adopt PostgreSQL 15.",
            "consequences": "Requires a migration framework.",
        }
    ]


def test_phase3a_generates_proposal_report(fake_repo):
    tmp, rel, target = fake_repo
    _write_design_intent(target, DESIGN_INTENT_WITH_IMPLEMENTED)

    proposal = phase3a_generate_proposal(tmp, rel, "plan-000268", _sample_decisions())

    assert proposal.exists()
    body = proposal.read_text(encoding="utf-8")
    assert "### D-010: Use PostgreSQL as primary datastore" in body
    assert "**Context**" in body
    assert "**Decision**" in body
    assert "**Consequences**" in body
    assert "plan-000268" in body


def test_phase3a_writes_single_pending_action(fake_repo):
    """plan-000470 R1: Phase 3a files ONE pending entry (apply-promote-markers)
    with copy-prose instructions folded into its description. The proposal file
    on disk is the Phase-3a audit trail (no separate ledger entry for it)."""
    tmp, rel, target = fake_repo
    _write_design_intent(target, DESIGN_INTENT_WITH_IMPLEMENTED)

    proposal = phase3a_generate_proposal(tmp, rel, "plan-000268", _sample_decisions())
    markers_id = phase3a_add_pending_actions(tmp, rel, "plan-000268", proposal)

    assert markers_id is not None

    records = _list_pending(tmp, rel)
    by_type = {r["type"]: r for r in records if r.get("source") == "plan-000268"}
    assert "apply-promote-markers" in by_type
    assert by_type["apply-promote-markers"]["status"] == "pending"
    # Description folds in copy-prose instructions + Phase-3b command hint
    description = by_type["apply-promote-markers"]["description"]
    assert "Copy draft Decision entries" in description
    assert "--apply-markers plan-000268" in description


def test_phase3b_verifies_decisions_present(fake_repo):
    tmp, rel, target = fake_repo
    # Baseline product-design-as-intended.md has D-001 only; proposal lists D-010 + D-011
    _write_design_intent(target, DESIGN_INTENT_BASELINE)

    present, missing = phase3b_heading_only_grep(target, ["D-010", "D-011"])

    assert present == []
    assert missing == ["D-010", "D-011"]


def test_phase3b_flips_markers_when_prose_applied(fake_repo):
    tmp, rel, target = fake_repo
    _write_design_intent(target, DESIGN_INTENT_WITH_IMPLEMENTED)

    present, missing = phase3b_heading_only_grep(target, ["D-001"])
    assert present == ["D-001"]
    assert missing == []

    flipped = phase3b_flip_markers(tmp, rel, target, "plan-000268", present)
    assert flipped == ["D-001"]

    content = target.read_text(encoding="utf-8")
    assert "STATUS: established" in content
    assert "plan-000268" in content
    # Exactly one STATUS marker above the heading (no stacking)
    status_markers = _STATUS_IMPLEMENTED_RE.findall(content)
    assert status_markers == [], (
        f"expected no implemented markers after flip, found: {status_markers}"
    )


def test_phase3b_partial_copy_leaves_markers_pending(fake_repo):
    """plan-000470 R1 Amendment 1: under the 2-branch closure (all-present AND
    all-flipped combined gate), partial copy leaves `apply-promote-markers`
    PENDING -- the proposal file on disk is the partial-copy audit trail;
    the ledger entry closes only when the cycle is fully complete. This
    inverts the old 4-branch behavior which closed markers once every
    *present* item was flipped."""
    tmp, rel, target = fake_repo
    # product-design-as-intended.md has D-001 and D-002 but NOT D-003 (designer hasn't
    # copied the third draft yet)
    _write_design_intent(target, DESIGN_INTENT_THREE_DECISIONS)

    proposal = phase3a_generate_proposal(
        tmp,
        rel,
        "plan-000268",
        [
            {"id": "D-001", "title": "PostgreSQL", "context": ".", "decision": ".",
             "consequences": "."},
            {"id": "D-002", "title": "FastAPI", "context": ".", "decision": ".",
             "consequences": "."},
            {"id": "D-003", "title": "Redis", "context": ".", "decision": ".",
             "consequences": "."},
        ],
    )
    markers_id = phase3a_add_pending_actions(tmp, rel, "plan-000268", proposal)
    assert markers_id

    proposed = ["D-001", "D-002", "D-003"]
    # Rewrite the file to drop D-003 entirely so the partial-copy case is
    # expressed as "heading for D-003 is absent from the intent file".
    stripped = DESIGN_INTENT_THREE_DECISIONS.replace(
        "<!-- STATUS: proposed -->\n### D-003: (draft, not yet copied by designer)\n\nPlaceholder for the partial-completion test.\n\n",
        "",
    )
    _write_design_intent(target, stripped)

    present, missing = phase3b_heading_only_grep(target, proposed)
    assert set(present) == {"D-001", "D-002"}
    assert missing == ["D-003"]

    flipped = phase3b_flip_markers(tmp, rel, target, "plan-000268", present)
    assert set(flipped) == {"D-001", "D-002"}

    phase3b_update_lifecycle(
        tmp, rel, markers_id, proposed, present, flipped
    )

    # markers stays PENDING because D-003 is missing from the intent file
    # (combined gate: all-present AND all-flipped).
    by_id = {r["id"]: r for r in _list_pending(tmp, rel)}
    assert by_id[markers_id]["status"] == "pending", (
        f"expected markers to stay pending due to missing D-003 "
        f"(2-branch gate requires all-present AND all-flipped), got "
        f"{by_id[markers_id]['status']}"
    )
    # Describe the expected user-facing message: it should enumerate the
    # missing D-NNN so the designer knows what to finish before re-running.
    assert "D-003" in missing


def test_phase3b_flips_legacy_uppercase_marker(fake_repo):
    tmp, rel, target = fake_repo
    _write_design_intent(target, DESIGN_INTENT_WITH_LEGACY_UPPERCASE)

    present, missing = phase3b_heading_only_grep(target, ["D-001"])
    assert present == ["D-001"]

    flipped = phase3b_flip_markers(tmp, rel, target, "plan-000260", present)
    assert flipped == ["D-001"]

    content = target.read_text(encoding="utf-8")
    # Legacy uppercase marker REPLACED (not stacked)
    assert "STATUS: IMPLEMENTED" not in content
    assert "STATUS: established" in content
    # Exactly one STATUS marker line immediately above the heading
    lines = content.splitlines()
    heading_idx = next(
        i for i, l in enumerate(lines)
        if l.startswith("### D-001:")
    )
    assert heading_idx > 0
    marker_count_above = 0
    j = heading_idx - 1
    while j >= 0 and lines[j].startswith("<!--"):
        marker_count_above += 1
        j -= 1
    assert marker_count_above == 1, (
        f"expected exactly one marker above heading, got {marker_count_above}"
    )


def test_phase3a_duplicate_invocation_is_idempotent(fake_repo):
    """plan-000470 R1: dedup on the single `apply-promote-markers` entry.
    Second invocation with the same plan-id returns None; exactly ONE record
    per plan ID for type `apply-promote-markers`."""
    tmp, rel, target = fake_repo
    _write_design_intent(target, DESIGN_INTENT_WITH_IMPLEMENTED)

    proposal = phase3a_generate_proposal(tmp, rel, "plan-000268", _sample_decisions())

    id1 = phase3a_add_pending_actions(tmp, rel, "plan-000268", proposal)
    assert id1

    # Second invocation with the same plan-id should dedup
    id2 = phase3a_add_pending_actions(tmp, rel, "plan-000268", proposal)
    assert id2 is None

    # Exactly one `apply-promote-markers` record for this plan
    records = _list_pending(tmp, rel)
    for_this_plan = [
        r
        for r in records
        if r.get("source") == "plan-000268"
        and r["type"] in {"apply-promote-markers"}
    ]
    assert len(for_this_plan) == 1, (
        f"expected exactly 1 record, got {len(for_this_plan)}: {for_this_plan}"
    )


def test_phase3b_rejects_non_colon_heading_form(fake_repo):
    tmp, rel, target = fake_repo
    _write_design_intent(target, DESIGN_INTENT_NON_COLON_HEADING)

    # apply_marker.py's `### D-001:` regex requires the colon form
    result = _run_apply_marker(
        tmp,
        rel,
        "--file",
        str(target),
        "--id",
        "D-001",
        "--marker",
        "STATUS",
        "--value",
        "implemented",
        "--plan",
        "plan-000268",
    )

    assert result.returncode != 0
    assert "D-001" in (result.stderr + result.stdout)
    assert "not found" in (result.stderr + result.stdout).lower()

    # File content is unchanged
    content = target.read_text(encoding="utf-8")
    assert "### D-001 - Use PostgreSQL" in content
    assert "STATUS: implemented" not in content
