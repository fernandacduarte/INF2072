#!/usr/bin/env python3
# designer: When you want to trust what the harness's telemetry is
#   recording about your sessions, I read every line of telemetry.jsonl
#   and confirm the required fields are present, the types are right,
#   and the enum values are ones the schema actually allows. Malformed
#   rows get called out with line numbers so you can fix the source.
"""
check_telemetry.py — Validate telemetry.jsonl schema and field constraints.

Invocation: agent-invoked, hook-ci
Lifecycle: active

Reads ${OUTPUT_DIR}/telemetry.jsonl and checks each JSON line for required fields,
valid types, and allowed enum values. Old records with only the 5 required fields
pass validation since all additional fields are optional.

Exit codes: 0 = all valid, 1 = errors found.

Usage
-----
    python .claude/skills/scripts/check_telemetry.py
    python .claude/skills/scripts/check_telemetry.py --verbose

CHECK_PLUGIN_MANIFEST:
  name: Telemetry
  stack:
    backend: [any]
    frontend: [any]
  scope: telemetry
  critical: false
"""

# Rationale for design choices and historical context: see check_telemetry-rationale.md in this directory.
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# Import from sibling module
sys.path.insert(0, str(Path(__file__).resolve().parent))
from project_config import REPO_ROOT, get

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = {"timestamp", "skill", "id", "duration_seconds", "outcome"}

VALID_OUTCOMES = {"success", "partial", "failed"}

VALID_ERROR_TYPES = {
    "git_conflict",
    "permission_error",
    "validation_failure",
    "timeout",
    "context_overflow",
    "user_cancelled",
    "unknown",
}

VALID_CONTEXT_BUDGETS = {"light", "standard", "heavy"}

VALID_QA_TYPES = {
    "single-prompt",
    "multi-turn",
    # TRANSITION plan-000468
    # advisory-follow-up is the dual-key legacy alias of research-follow-up.
    "advisory-follow-up",
    "research-follow-up",
    "decision-point-accept",
    "decision-point-revise",
    "decision-point-reject",
}

GIT_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")

# All recognized fields (required + optional)
# TRANSITION plan-000468
# advisory_decisions is the dual-key legacy alias of research_decisions.
ALL_FIELDS = REQUIRED_FIELDS | {
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
    "advisory_decisions",
    "research_decisions",
    "tokens_used",
}


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _check_string_or_null(record: dict, field: str) -> str | None:
    """Validate that a field is a string or null. Returns error or None."""
    value = record[field]
    if value is not None and not isinstance(value, str):
        return f"'{field}' must be string or null, got {type(value).__name__}"
    return None


def validate_record(record: dict) -> list[str]:
    """Validate a single telemetry record. Returns a list of error messages."""
    errors: list[str] = []

    # Check required fields are present
    for field in REQUIRED_FIELDS:
        if field not in record:
            errors.append(f"missing required field '{field}'")

    # Warn about unknown fields (collected separately, not an error)
    warnings: list[str] = []
    unknown = set(record.keys()) - ALL_FIELDS
    for field in sorted(unknown):
        warnings.append(f"unknown field '{field}'")

    # Validate 'timestamp' format
    if "timestamp" in record:
        ts = record["timestamp"]
        if not isinstance(ts, str):
            errors.append(f"'timestamp' must be a string, got {type(ts).__name__}")
        else:
            try:
                # Handle trailing Z for Python < 3.11 compatibility
                datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                errors.append(f"'timestamp' is not valid ISO 8601: {ts!r}")

    # Validate 'skill'
    if "skill" in record:
        if not isinstance(record["skill"], str) or not record["skill"]:
            errors.append("'skill' must be a non-empty string")

    # Validate 'id'
    if "id" in record:
        if not isinstance(record["id"], str) or not record["id"]:
            errors.append("'id' must be a non-empty string")

    # Validate 'outcome'
    if "outcome" in record:
        if record["outcome"] not in VALID_OUTCOMES:
            errors.append(
                f"'outcome' must be one of {sorted(VALID_OUTCOMES)}, got {record['outcome']!r}"
            )

    # Validate 'duration_seconds'
    if "duration_seconds" in record:
        val = record["duration_seconds"]
        if val is not None:
            if not isinstance(val, int) or isinstance(val, bool):
                errors.append(
                    f"'duration_seconds' must be int or null, got {type(val).__name__}"
                )
            elif val < 0:
                errors.append(f"'duration_seconds' must be >= 0, got {val}")

    # --- Optional fields (validated only when present) ---

    for field in ("brief", "prefix_scope", "plan_id", "output_file", "parent_skill"):
        if field in record:
            err = _check_string_or_null(record, field)
            if err:
                errors.append(err)

    if "error_type" in record:
        val = record["error_type"]
        if val is not None:
            if not isinstance(val, str):
                errors.append(
                    f"'error_type' must be string or null, got {type(val).__name__}"
                )
            elif val not in VALID_ERROR_TYPES:
                errors.append(
                    f"'error_type' must be one of {sorted(VALID_ERROR_TYPES)}, got {val!r}"
                )

    if "context_budget" in record:
        val = record["context_budget"]
        if not isinstance(val, str):
            errors.append(
                f"'context_budget' must be a string, got {type(val).__name__}"
            )
        elif val not in VALID_CONTEXT_BUDGETS:
            errors.append(
                f"'context_budget' must be one of {sorted(VALID_CONTEXT_BUDGETS)}, got {val!r}"
            )

    if "git_commit_sha" in record:
        val = record["git_commit_sha"]
        if val is not None:
            if not isinstance(val, str):
                errors.append(
                    f"'git_commit_sha' must be string or null, got {type(val).__name__}"
                )
            elif not GIT_SHA_RE.match(val):
                errors.append(
                    f"'git_commit_sha' must match ^[0-9a-f]{{7,40}}$, got {val!r}"
                )

    if "files_changed" in record:
        val = record["files_changed"]
        if val is not None:
            if not isinstance(val, int) or isinstance(val, bool):
                errors.append(
                    f"'files_changed' must be int or null, got {type(val).__name__}"
                )
            elif val < 0:
                errors.append(f"'files_changed' must be >= 0, got {val}")

    if "tokens_used" in record:
        val = record["tokens_used"]
        if val is not None:
            if not isinstance(val, int) or isinstance(val, bool):
                errors.append(
                    f"'tokens_used' must be int or null, got {type(val).__name__}"
                )
            elif val < 0:
                errors.append(f"'tokens_used' must be >= 0, got {val}")

    if "qa_type" in record:
        val = record["qa_type"]
        if val is not None:
            if not isinstance(val, str):
                errors.append(
                    f"'qa_type' must be string or null, got {type(val).__name__}"
                )
            elif val not in VALID_QA_TYPES:
                errors.append(
                    f"'qa_type' must be one of {sorted(VALID_QA_TYPES)}, got {val!r}"
                )

    if "user_revised_output" in record:
        val = record["user_revised_output"]
        if val is not None and not isinstance(val, bool):
            errors.append(
                f"'user_revised_output' must be bool or null, got {type(val).__name__}"
            )

    if "decision_points" in record:
        val = record["decision_points"]
        if val is not None:
            if not isinstance(val, list):
                errors.append(
                    f"'decision_points' must be list or null, got {type(val).__name__}"
                )
            else:
                for idx, entry in enumerate(val):
                    if not isinstance(entry, dict):
                        errors.append(
                            f"'decision_points[{idx}]' must be a dict, got {type(entry).__name__}"
                        )
                        continue
                    for key, expected_type, type_name in (
                        ("prompt", str, "string"),
                        ("chosen_option", str, "string"),
                        ("rationale_presented", bool, "bool"),
                    ):
                        if key not in entry:
                            errors.append(
                                f"'decision_points[{idx}]' missing required key '{key}'"
                            )
                        else:
                            entry_val = entry[key]
                            # isinstance(True, int) is True, so guard bool explicitly
                            if expected_type is bool:
                                if not isinstance(entry_val, bool):
                                    errors.append(
                                        f"'decision_points[{idx}].{key}' must be {type_name}, got {type(entry_val).__name__}"
                                    )
                            else:
                                if not isinstance(entry_val, expected_type) or isinstance(entry_val, bool):
                                    errors.append(
                                        f"'decision_points[{idx}].{key}' must be {type_name}, got {type(entry_val).__name__}"
                                    )

    return errors, warnings


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate telemetry.jsonl schema and field constraints"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show OK lines in addition to errors"
    )
    args = parser.parse_args()

    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    # Resolve telemetry file path
    output_dir = get("OUTPUT_DIR", "_output")
    telemetry_path = REPO_ROOT / output_dir / "telemetry.jsonl"

    if not telemetry_path.is_file():
        print("No telemetry file found")
        sys.exit(0)

    # Read and validate each line
    lines = telemetry_path.read_text(encoding="utf-8").splitlines()

    total = 0
    passed = 0
    failed = 0

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue

        total += 1

        # Parse JSON
        try:
            record = json.loads(stripped)
        except json.JSONDecodeError as exc:
            print(f"Line {i}: ERROR - invalid JSON: {exc}")
            failed += 1
            continue

        if not isinstance(record, dict):
            print(f"Line {i}: ERROR - expected JSON object, got {type(record).__name__}")
            failed += 1
            continue

        errors, warnings = validate_record(record)

        if errors:
            for err in errors:
                print(f"Line {i}: ERROR - {err}")
            failed += 1
        else:
            if args.verbose:
                print(f"Line {i}: OK")
            passed += 1

        # Always print warnings
        for warn in warnings:
            print(f"Line {i}: WARNING - {warn}")

    # Summary
    print(f"\nTelemetry validation: {total} records checked, {passed} passed, {failed} failed")

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
