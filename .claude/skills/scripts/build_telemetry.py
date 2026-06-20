#!/usr/bin/env python3
# designer: When a skill finishes and wants to record what happened, I take
#   all eighteen telemetry fields as CLI arguments, validate every enum against
#   the schema defined in check_telemetry.py, and append one JSON line to
#   telemetry.jsonl. I am the single write path for telemetry so that every
#   record the harness produces is guaranteed to pass check_telemetry validation
#   before it ever hits disk.
"""
build_telemetry.py -- Construct and append a validated telemetry record.

Invocation: skill-invoked
Lifecycle: active

Accepts all 18 telemetry fields as CLI arguments, validates enum fields against
constants imported from check_telemetry.py, and appends one JSON line to
${OUTPUT_DIR}/telemetry.jsonl.

Required args: --skill, --id, --outcome, --timestamp, --duration-seconds
Optional args default to null unless supplied. Complex fields (decision_points,
research_decisions) are passed as JSON strings.

Exit codes: 0 success, 1 validation error.

Usage
-----
    python .claude/skills/scripts/build_telemetry.py \\
        --skill research --id advisory-000123 \\
        --outcome success --timestamp 2026-05-03T12:00:00Z \\
        --duration-seconds 300
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_telemetry import (
    VALID_CONTEXT_BUDGETS,
    VALID_ERROR_TYPES,
    VALID_OUTCOMES,
    VALID_QA_TYPES,
)
from project_config import REPO_ROOT, get

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Construct and append a validated telemetry record to telemetry.jsonl"
    )

    # Required fields
    p.add_argument("--skill", required=True, help="Skill name (non-empty string)")
    p.add_argument("--id", required=True, dest="id", help="Record ID (non-empty string)")
    p.add_argument(
        "--outcome",
        required=True,
        choices=sorted(VALID_OUTCOMES),
        help="Skill outcome",
    )
    p.add_argument(
        "--timestamp",
        required=True,
        help="ISO 8601 timestamp (e.g. 2026-05-03T12:00:00Z)",
    )
    p.add_argument(
        "--duration-seconds",
        required=True,
        type=int,
        dest="duration_seconds",
        help="Duration in whole seconds (>= 0)",
    )

    # Optional string fields
    p.add_argument("--brief", default=None, help="Short human-readable summary")
    p.add_argument("--prefix-scope", default=None, dest="prefix_scope", help="Prefix scope")
    p.add_argument("--plan-id", default=None, dest="plan_id", help="Associated plan ID")
    p.add_argument(
        "--error-type",
        default=None,
        dest="error_type",
        choices=sorted(VALID_ERROR_TYPES),
        help="Error type (when outcome is failed or partial)",
    )
    p.add_argument("--output-file", default=None, dest="output_file", help="Primary output file")
    p.add_argument(
        "--context-budget",
        default=None,
        dest="context_budget",
        choices=sorted(VALID_CONTEXT_BUDGETS),
        help="Context budget tier",
    )
    p.add_argument("--git-sha", default=None, dest="git_commit_sha", help="Git commit SHA (7-40 hex chars)")
    p.add_argument(
        "--files-changed",
        default=None,
        type=int,
        dest="files_changed",
        help="Number of files changed (>= 0)",
    )
    p.add_argument("--parent-skill", default=None, dest="parent_skill", help="Invoking parent skill")
    p.add_argument(
        "--qa-type",
        default=None,
        dest="qa_type",
        choices=sorted(VALID_QA_TYPES),
        help="Q&A interaction type",
    )
    p.add_argument(
        "--tokens-used",
        default=None,
        type=int,
        dest="tokens_used",
        help="Tokens consumed (>= 0)",
    )
    p.add_argument("--session-id", default=None, dest="session_id", help="Session identifier")
    p.add_argument(
        "--telemetry-file",
        default=None,
        dest="telemetry_file",
        help="Override output path (default: ${OUTPUT_DIR}/telemetry.jsonl). Use in tests to avoid writing to live file.",
    )

    # Complex fields passed as JSON strings
    p.add_argument(
        "--decision-points",
        default=None,
        dest="decision_points_json",
        help="JSON array of decision point objects",
    )
    p.add_argument(
        "--research-decisions",
        default=None,
        dest="research_decisions_json",
        help="JSON array of research decision objects (also written to advisory_decisions)",
    )

    return p


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_enum(value: str | None, valid_set: set[str], field: str) -> str | None:
    """Return error string if value is non-null and not in valid_set."""
    if value is not None and value not in valid_set:
        return f"'{field}' must be one of {sorted(valid_set)}, got {value!r}"
    return None


def _validate_non_negative_int(value: int | None, field: str) -> str | None:
    """Return error string if value is non-null and negative."""
    if value is not None and value < 0:
        return f"'{field}' must be >= 0, got {value}"
    return None


def _parse_json_field(raw: str | None, field: str) -> tuple[list | None, str | None]:
    """Parse a JSON string arg into a Python object. Returns (parsed, error)."""
    if raw is None:
        return None, None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, f"'{field}' is not valid JSON: {exc}"
    if not isinstance(parsed, list):
        return None, f"'{field}' must be a JSON array"
    return parsed, None


# ---------------------------------------------------------------------------
# Record construction and write
# ---------------------------------------------------------------------------


def _build_record(args: argparse.Namespace) -> tuple[dict | None, list[str]]:
    """Validate args and build the telemetry record. Returns (record, errors)."""
    errors: list[str] = []

    # Validate non-negative ints
    err = _validate_non_negative_int(args.duration_seconds, "duration_seconds")
    if err:
        errors.append(err)
    err = _validate_non_negative_int(args.files_changed, "files_changed")
    if err:
        errors.append(err)
    err = _validate_non_negative_int(args.tokens_used, "tokens_used")
    if err:
        errors.append(err)

    # Parse complex JSON fields
    decision_points, err = _parse_json_field(args.decision_points_json, "decision_points")
    if err:
        errors.append(err)
    research_decisions, err = _parse_json_field(args.research_decisions_json, "research_decisions")
    if err:
        errors.append(err)

    if errors:
        return None, errors

    record: dict = {
        "timestamp": args.timestamp,
        "skill": args.skill,
        "id": args.id,
        "duration_seconds": args.duration_seconds,
        "outcome": args.outcome,
        "brief": args.brief,
        "prefix_scope": args.prefix_scope,
        "plan_id": args.plan_id,
        "error_type": args.error_type,
        "output_file": args.output_file,
        "context_budget": args.context_budget,
        "git_commit_sha": args.git_commit_sha,
        "files_changed": args.files_changed,
        "parent_skill": args.parent_skill,
        "qa_type": args.qa_type,
        "tokens_used": args.tokens_used,
        "session_id": args.session_id,
        "user_revised_output": None,
        "decision_points": decision_points,
        "research_decisions": research_decisions,
        "advisory_decisions": research_decisions,  # dual-key transition alias
    }

    return record, []


def _append_record(record: dict, telemetry_path: Path) -> None:
    """Append one JSON line to the telemetry file."""
    telemetry_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False)
    with telemetry_path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    record, errors = _build_record(args)
    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        sys.exit(1)

    if args.telemetry_file:
        telemetry_path = Path(args.telemetry_file)
    else:
        output_dir_str = get("OUTPUT_DIR", "_output")
        telemetry_path = REPO_ROOT / output_dir_str / "telemetry.jsonl"

    _append_record(record, telemetry_path)
    print(f"Appended telemetry record to {telemetry_path}")


if __name__ == "__main__":
    main()
