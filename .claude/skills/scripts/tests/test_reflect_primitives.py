"""Unit tests for the 5 V1 reflection analysis primitives.

Each primitive is exercised with at least three cases: a happy-path fixture, an
empty-window input, and a degenerate-field input. See plan-000295 step 5.
"""
from __future__ import annotations

from typing import Any

import pytest

import reflect_decision_reversals
import reflect_duration_anomalies
import reflect_revision_rate
import reflect_sequence_mining
import reflect_stuck_loops


# ---------------------------------------------------------------------------
# Shared record-builder helper
# ---------------------------------------------------------------------------


def _rec(
    *,
    ts: str,
    skill: str,
    id: str = "000000",
    duration: int | None = 60,
    brief: str = "sample brief",
    qa_type: str | None = "single-prompt",
    user_revised_output: bool | None = None,
    decision_points: list | None = None,
) -> dict[str, Any]:
    """Build a synthetic 17-field-ish telemetry record for tests."""
    return {
        "timestamp": ts,
        "skill": skill,
        "id": id,
        "duration_seconds": duration,
        "outcome": "success",
        "brief": brief,
        "prefix_scope": None,
        "plan_id": None,
        "error_type": None,
        "output_file": None,
        "context_budget": "standard",
        "git_commit_sha": None,
        "files_changed": None,
        "parent_skill": None,
        "qa_type": qa_type,
        "user_revised_output": user_revised_output,
        "decision_points": decision_points,
    }


# ---------------------------------------------------------------------------
# 1. reflect_sequence_mining
# ---------------------------------------------------------------------------


def test_sequence_mining_happy_path() -> None:
    window = [
        _rec(ts="2026-04-01T10:00:00Z", skill="advise"),
        _rec(ts="2026-04-01T10:10:00Z", skill="plan"),
        _rec(ts="2026-04-01T10:20:00Z", skill="implement"),
        _rec(ts="2026-04-01T11:00:00Z", skill="advise"),
        _rec(ts="2026-04-01T11:10:00Z", skill="plan"),
        _rec(ts="2026-04-01T11:20:00Z", skill="implement"),
        _rec(ts="2026-04-01T12:00:00Z", skill="advise"),
        _rec(ts="2026-04-01T12:10:00Z", skill="plan"),
    ]
    result = reflect_sequence_mining.analyze(window)
    assert result["degraded"] is False
    # top first-order should surface ("advise","plan") with count 3
    top_first = result["top_5_first_order"]
    assert len(top_first) >= 1
    assert top_first[0]["pattern"] == ["advise", "plan"]
    assert top_first[0]["count"] == 3
    # sequences list holds both orders with non-empty content
    assert any(s["order"] == 1 for s in result["sequences"])
    assert any(s["order"] == 2 for s in result["sequences"])
    # Observations should fire at count >= 3
    assert len(result["observations"]) >= 1
    assert "advise" in result["observations"][0]


def test_sequence_mining_empty_window() -> None:
    result = reflect_sequence_mining.analyze([])
    assert result["sequences"] == []
    assert result["top_5_first_order"] == []
    assert result["top_5_second_order"] == []
    assert result["observations"] == []
    assert result["degraded"] is True
    assert "insufficient" in result["reason"]


def test_sequence_mining_single_record_is_degraded() -> None:
    window = [_rec(ts="2026-04-01T10:00:00Z", skill="plan")]
    result = reflect_sequence_mining.analyze(window)
    assert result["degraded"] is True
    assert result["top_5_first_order"] == []


# ---------------------------------------------------------------------------
# 2. reflect_duration_anomalies
# ---------------------------------------------------------------------------


def test_duration_anomalies_happy_path() -> None:
    # 5 prior `plan` runs with median ~ 600s; one anomalous 1800s run.
    historical = [
        _rec(ts="2026-03-01T10:00:00Z", skill="plan", id="000001", duration=600),
        _rec(ts="2026-03-02T10:00:00Z", skill="plan", id="000002", duration=700),
        _rec(ts="2026-03-03T10:00:00Z", skill="plan", id="000003", duration=500),
        _rec(ts="2026-03-04T10:00:00Z", skill="plan", id="000004", duration=650),
        _rec(ts="2026-03-05T10:00:00Z", skill="plan", id="000005", duration=550),
    ]
    window = [
        _rec(ts="2026-04-01T10:00:00Z", skill="plan", id="000100", duration=1800),
    ]
    result = reflect_duration_anomalies.analyze(window, historical=historical)
    assert result["degraded"] is False
    assert len(result["anomalies"]) == 1
    anomaly = result["anomalies"][0]
    assert anomaly["skill"] == "plan"
    assert anomaly["id"] == "000100"
    assert anomaly["ratio"] >= 2.0
    assert anomaly["historical_sample_size"] == 5
    assert len(result["observations"]) == 1


def test_duration_anomalies_empty_window() -> None:
    result = reflect_duration_anomalies.analyze([])
    assert result["anomalies"] == []
    assert result["observations"] == []
    assert result["degraded"] is False


def test_duration_anomalies_all_null_durations_is_degraded() -> None:
    window = [
        _rec(ts="2026-04-01T10:00:00Z", skill="plan", duration=None),
        _rec(ts="2026-04-01T11:00:00Z", skill="advise", duration=None),
    ]
    result = reflect_duration_anomalies.analyze(window)
    assert result["degraded"] is True
    assert "no duration data" in result["reason"]
    assert result["anomalies"] == []


# ---------------------------------------------------------------------------
# 3. reflect_revision_rate
# ---------------------------------------------------------------------------


def test_revision_rate_happy_path() -> None:
    window: list[dict] = []
    # 10 `plan` runs where user_revised_output is True for 9 of them.
    for i in range(10):
        window.append(
            _rec(
                ts=f"2026-04-01T{10+i:02d}:00:00Z",
                skill="plan",
                id=f"00010{i}",
                user_revised_output=(i < 9),
            )
        )
    # 5 `advise` runs, 1 revised.
    for i in range(5):
        window.append(
            _rec(
                ts=f"2026-04-02T{10+i:02d}:00:00Z",
                skill="advise",
                id=f"00020{i}",
                user_revised_output=(i == 0),
            )
        )
    result = reflect_revision_rate.analyze(window)
    assert result["degraded"] is False
    # per_skill contains both skills
    skills = {entry["skill"]: entry for entry in result["per_skill"]}
    assert "plan" in skills
    assert "advise" in skills
    assert skills["plan"]["total"] == 10
    assert skills["plan"]["revised"] == 9
    assert skills["plan"]["rate"] == 0.9
    # high_revision_skills only contains plan
    highs = {entry["skill"] for entry in result["high_revision_skills"]}
    assert "plan" in highs
    assert "advise" not in highs
    assert len(result["observations"]) == 1


def test_revision_rate_empty_window() -> None:
    result = reflect_revision_rate.analyze([])
    assert result["per_skill"] == []
    assert result["high_revision_skills"] == []
    assert result["observations"] == []
    assert result["degraded"] is False


def test_revision_rate_all_null_is_degraded() -> None:
    window = [
        _rec(ts="2026-04-01T10:00:00Z", skill="plan", user_revised_output=None),
        _rec(ts="2026-04-01T11:00:00Z", skill="plan", user_revised_output=None),
    ]
    result = reflect_revision_rate.analyze(window)
    assert result["degraded"] is True
    assert "lazily" in result["reason"]
    assert result["per_skill"] == []


# ---------------------------------------------------------------------------
# 4. reflect_stuck_loops
# ---------------------------------------------------------------------------


def test_stuck_loops_happy_path() -> None:
    window = [
        _rec(
            ts="2026-04-01T14:00:00Z",
            skill="implement",
            id="000301",
            brief="fix the login bug in the auth module now",
        ),
        _rec(
            ts="2026-04-01T14:05:00Z",
            skill="implement",
            id="000302",
            brief="fix the login bug in the auth module again",
        ),
        _rec(
            ts="2026-04-01T14:10:00Z",
            skill="implement",
            id="000303",
            brief="fix the login bug in the auth module once more",
        ),
        _rec(
            ts="2026-04-01T14:12:00Z",
            skill="implement",
            id="000304",
            brief="fix the login bug in the auth module finally",
        ),
    ]
    result = reflect_stuck_loops.analyze(window)
    assert result["degraded"] is False
    assert len(result["stuck_loops"]) == 1
    loop = result["stuck_loops"][0]
    assert loop["skill"] == "implement"
    assert loop["count"] == 4
    assert loop["min_similarity"] >= 0.6
    assert len(loop["briefs"]) == 4
    assert len(result["observations"]) == 1


def test_stuck_loops_empty_window() -> None:
    result = reflect_stuck_loops.analyze([])
    assert result["stuck_loops"] == []
    assert result["observations"] == []
    assert result["degraded"] is False


def test_stuck_loops_missing_briefs_is_degraded() -> None:
    # All briefs empty; no briefs_map provided.
    window = [
        _rec(ts="2026-04-01T14:00:00Z", skill="implement", id="a", brief=""),
        _rec(ts="2026-04-01T14:05:00Z", skill="implement", id="b", brief=""),
        _rec(ts="2026-04-01T14:10:00Z", skill="implement", id="c", brief=""),
    ]
    result = reflect_stuck_loops.analyze(window, briefs_map={})
    assert result["degraded"] is True
    assert "briefs" in result["reason"]


# ---------------------------------------------------------------------------
# 5. reflect_decision_reversals
# ---------------------------------------------------------------------------


def test_decision_reversals_happy_path() -> None:
    window = [
        _rec(
            ts="2026-04-01T10:00:00Z",
            skill="plan",
            id="000271",
            qa_type="decision-point-accept",
            decision_points=[
                {
                    "prompt": "Apply markers now?",
                    "chosen_option": "Apply markers now",
                    "rationale_presented": True,
                }
            ],
        ),
        _rec(
            ts="2026-04-02T15:30:00Z",
            skill="explain",
            id="000280",
            qa_type="decision-point-revise",
            decision_points=[
                {
                    "prompt": "Should we keep 'Apply markers now'?",
                    "chosen_option": "Revert marker application",
                    "rationale_presented": True,
                }
            ],
        ),
    ]
    result = reflect_decision_reversals.analyze(window)
    assert result["degraded"] is False
    assert len(result["reversals"]) == 1
    rev = result["reversals"][0]
    assert rev["decision"] == "Apply markers now"
    assert rev["accepted_in"] == "plan-000271"
    assert rev["reversed_in"] == "explain-000280"
    assert len(result["observations"]) == 1


def test_decision_reversals_empty_window() -> None:
    result = reflect_decision_reversals.analyze([])
    assert result["reversals"] == []
    assert result["observations"] == []
    assert result["degraded"] is False


def test_decision_reversals_all_null_dp_is_degraded() -> None:
    window = [
        _rec(ts="2026-04-01T10:00:00Z", skill="plan", decision_points=None),
        _rec(ts="2026-04-02T10:00:00Z", skill="plan", decision_points=[]),
    ]
    result = reflect_decision_reversals.analyze(window)
    assert result["degraded"] is True
    assert "decision_points" in result["reason"]
    assert result["reversals"] == []
