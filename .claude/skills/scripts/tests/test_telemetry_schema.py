"""Smoke tests for the 18-field post-skill telemetry record schema.

These tests parse hard-coded sample records to verify that the schema
documented in `.claude/skills/post-skill/SKILL.md` steps 1b and 8b is
internally consistent. They exercise the JSON shape and also import
`check_telemetry.validate_record` to verify the validator recognizes
the new fields (`qa_type`, `user_revised_output`, `decision_points`)
added in plan-000295 step 1.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Make .claude/skills/scripts importable so we can call validate_record directly.
_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from check_telemetry import validate_record  # noqa: E402

# The canonical 18 field names, in the order they appear in the SKILL.md
# step 8b example. Order is not semantically meaningful for JSON readers
# but this list is the single source of truth for these tests.
EXPECTED_FIELDS = [
    "timestamp",
    "skill",
    "id",
    "duration_seconds",
    "outcome",
    "brief",
    "prefix_scope",
    "plan_id",
    "error_type",
    "output_file",
    "context_budget",
    "git_commit_sha",
    "files_changed",
    "parent_skill",
    "qa_type",
    "user_revised_output",
    "decision_points",
    "tokens_used",
]

QA_TYPE_ALLOWED = {
    "single-prompt",
    "multi-turn",
    "advisory-follow-up",
    "decision-point-accept",
    "decision-point-revise",
    "decision-point-reject",
}


@pytest.fixture
def full_record() -> dict:
    """A realistic 18-field record matching the step 8b example."""
    raw = (
        '{"timestamp": "2026-03-29T14:00:00Z", "skill": "advise", '
        '"id": "000014", "duration_seconds": 1800, "outcome": "success", '
        '"brief": "What other attributes could be incorporated into telemetry?", '
        '"prefix_scope": "CHORE-O", "plan_id": null, "error_type": null, '
        '"output_file": "_output/advisory-logs/advisory-000014-telemetry-attributes-expansion.md", '
        '"context_budget": "standard", "git_commit_sha": "9709d91abc123", '
        '"files_changed": 6, "parent_skill": "advise", '
        '"qa_type": "advisory-follow-up", "user_revised_output": null, '
        '"decision_points": [{"prompt": "Apply markers now?", '
        '"chosen_option": "Defer for later review", '
        '"rationale_presented": true}], '
        '"tokens_used": null}'
    )
    return json.loads(raw)


@pytest.fixture
def degenerate_record() -> dict:
    """Backwards-compat degenerate case: null decision_points, single-prompt qa_type."""
    raw = (
        '{"timestamp": "2026-04-11T09:00:00Z", "skill": "check", '
        '"id": "000042", "duration_seconds": 12, "outcome": "success", '
        '"brief": "Run fast preflight", "prefix_scope": null, '
        '"plan_id": null, "error_type": null, "output_file": null, '
        '"context_budget": "light", "git_commit_sha": null, '
        '"files_changed": null, "parent_skill": "check", '
        '"qa_type": "single-prompt", "user_revised_output": null, '
        '"decision_points": null, '
        '"tokens_used": null}'
    )
    return json.loads(raw)


def test_full_record_has_all_18_fields(full_record: dict) -> None:
    assert len(EXPECTED_FIELDS) == 18
    for field in EXPECTED_FIELDS:
        assert field in full_record, f"missing field: {field}"
    assert set(full_record.keys()) == set(EXPECTED_FIELDS)


def test_qa_type_is_string_or_none(full_record: dict) -> None:
    value = full_record["qa_type"]
    assert value is None or isinstance(value, str)
    if isinstance(value, str):
        assert value in QA_TYPE_ALLOWED


def test_user_revised_output_is_bool_or_none(full_record: dict) -> None:
    value = full_record["user_revised_output"]
    assert value is None or isinstance(value, bool)
    # Post-skill always writes null; /reflect populates lazily.
    assert value is None


def test_decision_points_is_list_or_none(full_record: dict) -> None:
    value = full_record["decision_points"]
    assert value is None or isinstance(value, list)


def test_decision_point_entries_have_required_shape(full_record: dict) -> None:
    entries = full_record["decision_points"]
    assert isinstance(entries, list)
    for entry in entries:
        assert isinstance(entry, dict)
        assert "prompt" in entry and isinstance(entry["prompt"], str)
        assert "chosen_option" in entry and isinstance(entry["chosen_option"], str)
        assert "rationale_presented" in entry and isinstance(entry["rationale_presented"], bool)


def test_degenerate_record_parses(degenerate_record: dict) -> None:
    """Backwards-compat: null decision_points + 'single-prompt' qa_type must parse."""
    assert set(degenerate_record.keys()) == set(EXPECTED_FIELDS)
    assert degenerate_record["decision_points"] is None
    assert degenerate_record["qa_type"] == "single-prompt"
    assert degenerate_record["user_revised_output"] is None


def test_degenerate_record_types(degenerate_record: dict) -> None:
    value = degenerate_record["qa_type"]
    assert value is None or isinstance(value, str)
    assert degenerate_record["user_revised_output"] is None or isinstance(
        degenerate_record["user_revised_output"], bool
    )
    assert degenerate_record["decision_points"] is None or isinstance(
        degenerate_record["decision_points"], list
    )


def test_record_roundtrips_through_json(full_record: dict) -> None:
    """Serializing and re-parsing must preserve all 18 fields and their values."""
    serialized = json.dumps(full_record)
    reparsed = json.loads(serialized)
    assert reparsed == full_record
    assert set(reparsed.keys()) == set(EXPECTED_FIELDS)


# ---------------------------------------------------------------------------
# check_telemetry.validate_record integration tests
# ---------------------------------------------------------------------------
# These tests verify that the central validator accepts the 18-field schema
# and produces no unknown-field warnings for the 3 fields added by
# plan-000295 step 1. They also verify per-field type validation catches
# bad inputs (wrong enum, wrong type, wrong nested shape).


def test_validator_accepts_full_18_field_record(full_record: dict) -> None:
    """A full 18-field record must validate with no errors and no warnings."""
    errors, warnings = validate_record(full_record)
    assert errors == [], f"unexpected errors: {errors}"
    assert warnings == [], f"unexpected warnings: {warnings}"


def test_validator_accepts_legacy_14_field_record() -> None:
    """Backwards-compat: a 14-field record (pre plan-000295) must still validate."""
    legacy = {
        "timestamp": "2026-03-01T12:00:00Z",
        "skill": "plan",
        "id": "000001",
        "duration_seconds": 60,
        "outcome": "success",
        "brief": "Legacy record",
        "prefix_scope": "CHORE-O",
        "plan_id": None,
        "error_type": None,
        "output_file": None,
        "context_budget": "standard",
        "git_commit_sha": "abc1234",
        "files_changed": 1,
        "parent_skill": "plan",
    }
    errors, warnings = validate_record(legacy)
    assert errors == [], f"unexpected errors: {errors}"
    assert warnings == [], f"unexpected warnings: {warnings}"


def test_validator_accepts_degenerate_18_field_record(degenerate_record: dict) -> None:
    errors, warnings = validate_record(degenerate_record)
    assert errors == [], f"unexpected errors: {errors}"
    assert warnings == [], f"unexpected warnings: {warnings}"


def test_validator_flags_invalid_qa_type_enum(full_record: dict) -> None:
    full_record["qa_type"] = "invalid-enum"
    errors, _ = validate_record(full_record)
    assert any("qa_type" in e and "invalid-enum" in e for e in errors), errors


def test_validator_flags_non_string_qa_type(full_record: dict) -> None:
    full_record["qa_type"] = 42
    errors, _ = validate_record(full_record)
    assert any("qa_type" in e and "string or null" in e for e in errors), errors


def test_validator_allows_null_qa_type(full_record: dict) -> None:
    full_record["qa_type"] = None
    errors, _ = validate_record(full_record)
    assert not any("qa_type" in e for e in errors), errors


def test_validator_flags_non_bool_user_revised_output(full_record: dict) -> None:
    full_record["user_revised_output"] = "string"
    errors, _ = validate_record(full_record)
    assert any("user_revised_output" in e and "bool or null" in e for e in errors), errors


def test_validator_allows_bool_user_revised_output(full_record: dict) -> None:
    full_record["user_revised_output"] = True
    errors, _ = validate_record(full_record)
    assert not any("user_revised_output" in e for e in errors), errors


def test_validator_allows_null_user_revised_output(full_record: dict) -> None:
    full_record["user_revised_output"] = None
    errors, _ = validate_record(full_record)
    assert not any("user_revised_output" in e for e in errors), errors


def test_validator_flags_non_list_decision_points(full_record: dict) -> None:
    full_record["decision_points"] = "not-a-list"
    errors, _ = validate_record(full_record)
    assert any("decision_points" in e and "list or null" in e for e in errors), errors


def test_validator_allows_empty_decision_points_list(full_record: dict) -> None:
    full_record["decision_points"] = []
    errors, warnings = validate_record(full_record)
    assert errors == [], f"unexpected errors: {errors}"
    assert warnings == []


def test_validator_flags_decision_point_entry_wrong_shape(full_record: dict) -> None:
    full_record["decision_points"] = [{"bad": "shape"}]
    errors, _ = validate_record(full_record)
    # Missing prompt, chosen_option, rationale_presented.
    assert any("prompt" in e for e in errors), errors
    assert any("chosen_option" in e for e in errors), errors
    assert any("rationale_presented" in e for e in errors), errors


def test_validator_flags_decision_point_wrong_types(full_record: dict) -> None:
    full_record["decision_points"] = [
        {"prompt": 1, "chosen_option": 2, "rationale_presented": "yes"}
    ]
    errors, _ = validate_record(full_record)
    assert any("prompt" in e and "string" in e for e in errors), errors
    assert any("chosen_option" in e and "string" in e for e in errors), errors
    assert any("rationale_presented" in e and "bool" in e for e in errors), errors


def test_validator_flags_decision_point_non_dict_entry(full_record: dict) -> None:
    full_record["decision_points"] = ["not-a-dict"]
    errors, _ = validate_record(full_record)
    assert any("decision_points[0]" in e and "dict" in e for e in errors), errors


# ---------------------------------------------------------------------------
# tokens_used field validation
# ---------------------------------------------------------------------------


def test_tokens_used_null_is_valid(full_record: dict) -> None:
    full_record["tokens_used"] = None
    errors, _ = validate_record(full_record)
    assert not any("tokens_used" in e for e in errors), errors


def test_tokens_used_positive_int_is_valid(full_record: dict) -> None:
    full_record["tokens_used"] = 42000
    errors, _ = validate_record(full_record)
    assert not any("tokens_used" in e for e in errors), errors


def test_validator_flags_non_int_tokens_used(full_record: dict) -> None:
    full_record["tokens_used"] = "many"
    errors, _ = validate_record(full_record)
    assert any("tokens_used" in e and "int or null" in e for e in errors), errors


def test_validator_flags_negative_tokens_used(full_record: dict) -> None:
    full_record["tokens_used"] = -1
    errors, _ = validate_record(full_record)
    assert any("tokens_used" in e and ">= 0" in e for e in errors), errors
