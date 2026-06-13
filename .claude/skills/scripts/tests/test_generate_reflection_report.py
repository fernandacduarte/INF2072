"""Unit tests for the reflection-report orchestrator.

Covers the compose/load/compute surface exposed by
``generate_reflection_report`` so Step 4's ``/reflect`` skill has a stable CLI
contract and Step 9's live run has a known-good composition path. See
plan-000295 Step 6.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

import generate_reflection_report as grr


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_H1_REGEX = re.compile(
    r"^#\s+Reflection\s+(\d+)\s*\|\s*([\d\-: UTC]+)\s*\|\s*(.+)",
    re.IGNORECASE,
)

_FORBIDDEN_SUBSTRINGS = (
    "you should",
    "consider ",
    "we recommend",
    "ought to",
    "must ",
)

_ALLOWED_HANDOFF_PARAGRAPH_ANCHOR = "These are descriptive observations and questions"


def _fixed_times() -> tuple[datetime, datetime]:
    since = datetime(2026, 3, 12, 0, 0, 0, tzinfo=timezone.utc)
    now = datetime(2026, 4, 11, 13, 30, 0, tzinfo=timezone.utc)
    return since, now


def _empty_results() -> dict[str, dict]:
    return {
        "sequence_mining": {
            "sequences": [],
            "top_5_first_order": [],
            "top_5_second_order": [],
            "observations": [],
            "degraded": False,
        },
        "duration_anomalies": {
            "anomalies": [],
            "observations": [],
            "degraded": False,
        },
        "revision_rate": {
            "per_skill": [],
            "high_revision_skills": [],
            "observations": [],
            "degraded": False,
        },
        "stuck_loops": {
            "stuck_loops": [],
            "observations": [],
            "degraded": False,
        },
        "decision_reversals": {
            "reversals": [],
            "observations": [],
            "degraded": False,
        },
    }


def _assert_no_prescriptive_phrasing(report: str) -> None:
    """Forbidden substrings must not appear outside the static hand-off paragraph.

    The hand-off paragraph uses "run `/research`" which is allowed because it
    is a static, non-prescriptive hand-off signal (not first-person advice).
    """
    lower = report.lower()
    handoff_idx = lower.find(_ALLOWED_HANDOFF_PARAGRAPH_ANCHOR.lower())
    if handoff_idx == -1:
        before = lower
        after = ""
    else:
        # The hand-off paragraph ends at the next blank line (== "\n\n").
        end = lower.find("\n\n", handoff_idx)
        if end == -1:
            end = len(lower)
        before = lower[:handoff_idx]
        after = lower[end:]

    for needle in _FORBIDDEN_SUBSTRINGS:
        assert needle not in before, (
            f"Forbidden prescriptive phrase {needle!r} found before hand-off"
        )
        assert needle not in after, (
            f"Forbidden prescriptive phrase {needle!r} found after hand-off"
        )


# ---------------------------------------------------------------------------
# 1. Empty window
# ---------------------------------------------------------------------------


def test_compose_report_empty_window_shows_fallbacks():
    since, now = _fixed_times()
    report = grr.compose_report(
        reflection_id="000123",
        title="Empty window check",
        since=since,
        now=now,
        window=[],
        git_range=("", ""),
        results=_empty_results(),
    )

    # H1 matches the macro-index regex.
    first_line = report.splitlines()[0]
    match = _H1_REGEX.match(first_line)
    assert match is not None, f"H1 does not match regex: {first_line!r}"
    assert match.group(1) == "000123"

    # Every section shows its fallback phrasing.
    assert "No notable sequences this window." in report
    assert "No notable duration anomalies this window." in report
    assert "No notable revision patterns this window." in report
    assert "No stuck loops this window." in report
    assert (
        "No decision reversals this window (or decision_points field not yet "
        "populated)." in report
    )

    # Questions section falls back to None this window.
    assert "None this window." in report

    # Signature lists the 5 primitives.
    assert (
        "Primitives run: sequence_mining, duration_anomalies, "
        "revision_rate, stuck_loops, decision_reversals" in report
    )

    # No prescriptive words anywhere outside the hand-off paragraph.
    _assert_no_prescriptive_phrasing(report)


# ---------------------------------------------------------------------------
# 2. Full window
# ---------------------------------------------------------------------------


def test_compose_report_full_window_embeds_every_observation():
    since, now = _fixed_times()
    results = _empty_results()
    results["sequence_mining"]["observations"] = [
        "I notice that after `plan`, you most often invoke `plan` (3 of 10 "
        "times). Here is a question I am holding for you: why two plans in a row?"
    ]
    results["duration_anomalies"]["observations"] = [
        "I notice that `advise` (id `000016`) took 1800 seconds, about 6.0x "
        "your historical median of 300 seconds. Here is a question I am "
        "holding for you: what was different about that session?"
    ]
    results["revision_rate"]["observations"] = [
        "I notice that you revised the output of `plan` in 4 of your last 6 "
        "invocations (67%). Here is a question I am holding for you: what "
        "might I be missing in how I draft for this skill?"
    ]
    results["stuck_loops"]["observations"] = [
        "I notice that you invoked `plan` 3 times in about 12.0 minutes on "
        "very similar briefs. Here is a question I am holding for you: what "
        "did you learn between the first and the last invocation?"
    ]
    results["decision_reversals"]["observations"] = [
        "I notice that you accepted `Plan A` on 2026-03-20, and then "
        "`revert to draft` on 2026-04-01 undid it. Here is a question I am "
        "holding for you: what changed between those two moments?"
    ]

    report = grr.compose_report(
        reflection_id="000456",
        title="Full window check",
        since=since,
        now=now,
        window=[{"skill": "plan"}] * 7,
        git_range=("abcdef1", "9876543"),
        results=results,
    )

    # Every observation appears verbatim in the report.
    for key in grr._SECTION_ORDER:
        for obs in results[key]["observations"]:
            assert obs in report, f"Missing observation in {key}: {obs!r}"

    # Every question fragment shows up in the aggregated section.
    expected_questions = [
        "why two plans in a row?",
        "what was different about that session?",
        "what might I be missing in how I draft for this skill?",
        "what did you learn between the first and the last invocation?",
        "what changed between those two moments?",
    ]
    q_section_start = report.index("## Questions I am holding for you")
    q_section_end = report.index("## What to do with this", q_section_start)
    q_section = report[q_section_start:q_section_end]
    for q in expected_questions:
        assert q in q_section, f"Missing question in aggregated section: {q!r}"

    # Records count and git range render correctly.
    assert "- Records: 7" in report
    assert "- Git range: abcdef1..9876543" in report

    _assert_no_prescriptive_phrasing(report)


# ---------------------------------------------------------------------------
# 3. Some primitives degraded
# ---------------------------------------------------------------------------


def test_compose_report_degraded_primitives_surface_reason():
    since, now = _fixed_times()
    results = _empty_results()
    results["revision_rate"]["degraded"] = True
    results["revision_rate"]["reason"] = (
        "user_revised_output not yet computed for this window; "
        "/reflect computes it lazily"
    )
    results["decision_reversals"]["degraded"] = True
    results["decision_reversals"]["reason"] = (
        "decision_points field not populated; requires Plan B rationale "
        "payloads to be captured first"
    )

    report = grr.compose_report(
        reflection_id="000789",
        title="Degraded check",
        since=since,
        now=now,
        window=[],
        git_range=("", ""),
        results=results,
    )

    assert (
        "(Degraded: user_revised_output not yet computed for this window; "
        "/reflect computes it lazily)"
    ) in report
    assert (
        "(Degraded: decision_points field not populated; requires Plan B "
        "rationale payloads to be captured first)"
    ) in report

    # The non-degraded sections still fall back cleanly.
    assert "No notable sequences this window." in report
    assert "No notable duration anomalies this window." in report
    assert "No stuck loops this window." in report

    _assert_no_prescriptive_phrasing(report)


# ---------------------------------------------------------------------------
# 4. H1 regex check
# ---------------------------------------------------------------------------


def test_compose_report_h1_matches_macro_index_regex():
    since, now = _fixed_times()
    report = grr.compose_report(
        reflection_id="042000",
        title="Regex check title",
        since=since,
        now=now,
        window=[],
        git_range=("", ""),
        results=_empty_results(),
    )
    first_line = report.splitlines()[0]
    match = _H1_REGEX.match(first_line)
    assert match is not None
    assert match.group(1) == "042000"
    # Datetime chunk must end with " UTC" and contain no Z / +00:00 markers.
    dt_chunk = match.group(2)
    assert dt_chunk.strip().endswith("UTC")
    assert "Z" not in dt_chunk
    assert "+00:00" not in dt_chunk
    # Title round-trips.
    assert match.group(3).strip() == "Regex check title"


# ---------------------------------------------------------------------------
# 5. Non-prescriptive global scan
# ---------------------------------------------------------------------------


def test_compose_report_no_forbidden_substrings_across_configurations():
    since, now = _fixed_times()
    # Run the scan against three distinct configurations.
    configs: list[dict[str, dict]] = [_empty_results()]

    full = _empty_results()
    full["sequence_mining"]["observations"] = [
        "I notice that after `plan`, you most often invoke `plan`. "
        "Here is a question I am holding for you: is this a healthy rhythm?"
    ]
    configs.append(full)

    degraded = _empty_results()
    degraded["stuck_loops"]["degraded"] = True
    degraded["stuck_loops"]["reason"] = "briefs not loaded or missing"
    configs.append(degraded)

    for idx, cfg in enumerate(configs):
        report = grr.compose_report(
            reflection_id=f"0000{idx:02d}",
            title=f"Config {idx}",
            since=since,
            now=now,
            window=[],
            git_range=("", ""),
            results=cfg,
        )
        _assert_no_prescriptive_phrasing(report)


# ---------------------------------------------------------------------------
# 6. load_window filtering
# ---------------------------------------------------------------------------


def test_load_window_filters_by_since_and_skill(tmp_path: Path):
    telemetry = tmp_path / "telemetry.jsonl"
    records = [
        {"timestamp": "2026-02-01T00:00:00Z", "skill": "plan", "id": "000001"},
        {"timestamp": "2026-03-20T12:00:00Z", "skill": "plan", "id": "000002"},
        {"timestamp": "2026-03-25T08:00:00Z", "skill": "advise", "id": "000003"},
        {"timestamp": "2026-04-01T10:00:00Z", "skill": "plan", "id": "000004"},
        # Malformed line -- should be skipped gracefully.
        {"skill": "plan", "id": "000005"},
    ]
    lines = [json.dumps(r) for r in records]
    lines.insert(2, "not-json-at-all")
    telemetry.write_text("\n".join(lines) + "\n", encoding="utf-8")

    since = datetime(2026, 3, 1, 0, 0, 0, tzinfo=timezone.utc)

    window = grr.load_window(telemetry, since, skill_filter=None)
    # Drops pre-since (1) and the timestamp-less record (1) and the
    # non-json line (1) => 3 records retained.
    assert [r["id"] for r in window] == ["000002", "000003", "000004"]

    filtered = grr.load_window(telemetry, since, skill_filter="plan")
    assert [r["id"] for r in filtered] == ["000002", "000004"]

    advise_only = grr.load_window(telemetry, since, skill_filter="advise")
    assert [r["id"] for r in advise_only] == ["000003"]


# ---------------------------------------------------------------------------
# 7. compute_git_range
# ---------------------------------------------------------------------------


def test_compute_git_range_returns_first_and_last_shas():
    window = [
        {"timestamp": "2026-03-12T00:00:00Z", "skill": "plan", "git_commit_sha": "aaa1111"},
        {"timestamp": "2026-03-13T00:00:00Z", "skill": "plan", "git_commit_sha": None},
        {"timestamp": "2026-03-14T00:00:00Z", "skill": "plan", "git_commit_sha": "bbb2222"},
        {"timestamp": "2026-03-15T00:00:00Z", "skill": "plan", "git_commit_sha": "ccc3333"},
    ]
    assert grr.compute_git_range(window) == ("aaa1111", "ccc3333")

    assert grr.compute_git_range([]) == ("", "")
    assert grr.compute_git_range(
        [{"skill": "plan", "git_commit_sha": None}]
    ) == ("", "")
