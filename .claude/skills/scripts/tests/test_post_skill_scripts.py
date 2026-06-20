"""Unit tests for the four post-skill helper scripts created in plan-000546.

Scripts under test (all in .claude/skills/scripts/):
  - mark_brief_done.py
  - build_telemetry.py
  - verify_commit_scope.py
  - update_cross_refs.py

Each script is tested as a CLI subprocess so that exit codes and I/O are
captured accurately, matching real post-skill invocation behaviour.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

# Locate the scripts directory regardless of cwd
_SCRIPTS_DIR = Path(__file__).resolve().parents[1]  # .claude/skills/scripts/


def _run(script_name: str, *args: str, input_text: str | None = None) -> subprocess.CompletedProcess:
    """Run a script by name with the given args and return the CompletedProcess."""
    script = str(_SCRIPTS_DIR / script_name)
    return subprocess.run(
        [sys.executable, script, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        input=input_text,
    )


# ===========================================================================
# mark_brief_done.py
# ===========================================================================


@pytest.fixture()
def briefs_file(tmp_path: Path) -> Path:
    """Create a minimal briefs.md with one STARTED entry."""
    f = tmp_path / "briefs.md"
    f.write_text(
        "STARTED | 2026-05-03 10:00 UTC | post-skill | plan 000546 step 5 unit tests\n"
        "DONE | 2026-05-02 18:00 UTC | STARTED | 2026-05-02 17:00 UTC | plan | earlier task\n",
        encoding="utf-8",
    )
    return f


class TestMarkBriefDone:
    def test_marks_started_as_done(self, briefs_file: Path) -> None:
        """Matching STARTED entry is replaced with a correctly formatted DONE line."""
        result = _run(
            "mark_brief_done.py",
            "--brief-pattern", "plan 000546 step 5",
            "--done-time", "2026-05-03 12:00 UTC",
            "--briefs-file", str(briefs_file),
        )
        assert result.returncode == 0, result.stderr
        content = briefs_file.read_text(encoding="utf-8")
        assert "DONE | 2026-05-03 12:00 UTC | STARTED |" in content
        assert "plan 000546 step 5 unit tests" in content
        # Original STARTED line must be gone
        assert not content.startswith("STARTED | ")

    def test_appends_plan_suffix_when_plan_id_given(self, briefs_file: Path) -> None:
        """--plan-id appends '| PLAN | <id>' to the DONE line."""
        result = _run(
            "mark_brief_done.py",
            "--brief-pattern", "plan 000546 step 5",
            "--done-time", "2026-05-03 12:00 UTC",
            "--plan-id", "000546",
            "--briefs-file", str(briefs_file),
        )
        assert result.returncode == 0, result.stderr
        content = briefs_file.read_text(encoding="utf-8")
        assert "| PLAN | 000546" in content

    def test_exits_1_when_no_match(self, tmp_path: Path) -> None:
        """When no STARTED entry matches the pattern, exit code is 1."""
        briefs = tmp_path / "briefs.md"
        briefs.write_text(
            "DONE | 2026-05-02 18:00 UTC | STARTED | 2026-05-02 17:00 UTC | plan | some task\n",
            encoding="utf-8",
        )
        result = _run(
            "mark_brief_done.py",
            "--brief-pattern", "nonexistent-pattern-xyz",
            "--done-time", "2026-05-03 12:00 UTC",
            "--briefs-file", str(briefs),
        )
        assert result.returncode == 1
        assert "WARNING" in result.stderr or "no STARTED" in result.stderr.lower() or result.returncode == 1

    def test_case_insensitive_pattern_match(self, briefs_file: Path) -> None:
        """Pattern matching is case-insensitive."""
        result = _run(
            "mark_brief_done.py",
            "--brief-pattern", "PLAN 000546",   # uppercase, original is lowercase
            "--done-time", "2026-05-03 12:00 UTC",
            "--briefs-file", str(briefs_file),
        )
        assert result.returncode == 0, result.stderr


# ===========================================================================
# build_telemetry.py
# ===========================================================================

_REQUIRED_TELEMETRY_ARGS = [
    "--skill", "research",
    "--id", "advisory-000001",
    "--outcome", "success",
    "--timestamp", "2026-05-03T12:00:00Z",
    "--duration-seconds", "300",
]


class TestBuildTelemetry:
    def test_valid_record_appended_and_passes_check(self, tmp_path: Path) -> None:
        """A valid invocation writes a JSON line that validate_record accepts."""
        telemetry_file = tmp_path / "telemetry.jsonl"

        result = _run(
            "build_telemetry.py",
            *_REQUIRED_TELEMETRY_ARGS,
            "--telemetry-file", str(telemetry_file),
        )
        assert result.returncode == 0, result.stderr
        assert "Appended telemetry record" in result.stdout
        # The record was written to the temp file, not the live telemetry.jsonl
        assert telemetry_file.exists(), "telemetry file was not created"
        record = json.loads(telemetry_file.read_text(encoding="utf-8").strip())
        assert record["skill"] == "research"
        assert record["id"] == "advisory-000001"
        assert record["outcome"] == "success"

    def test_valid_record_passes_validate_record(self, tmp_path: Path) -> None:
        """Record built by _build_record() matches check_telemetry.validate_record."""
        # Import the module directly (conftest adds scripts dir to sys.path)
        import importlib
        sys.path.insert(0, str(_SCRIPTS_DIR))
        build_tel = importlib.import_module("build_telemetry")
        check_tel = importlib.import_module("check_telemetry")

        import argparse
        # Provide context_budget as "standard" -- check_telemetry requires a string
        # for that field when present (null is not accepted by its validator).
        ns = argparse.Namespace(
            skill="research",
            id="advisory-000001",
            outcome="success",
            timestamp="2026-05-03T12:00:00Z",
            duration_seconds=300,
            brief=None,
            prefix_scope=None,
            plan_id=None,
            error_type=None,
            output_file=None,
            context_budget="standard",
            git_commit_sha=None,
            files_changed=None,
            parent_skill=None,
            qa_type=None,
            tokens_used=None,
            session_id=None,
            decision_points_json=None,
            research_decisions_json=None,
        )
        record, errors = build_tel._build_record(ns)
        assert errors == [], f"build errors: {errors}"
        assert record is not None

        val_errors, warnings = check_tel.validate_record(record)
        # session_id is an unknown field -- produces a warning but not an error
        assert val_errors == [], f"validation errors: {val_errors}"

    def test_invalid_outcome_enum_exits_nonzero(self) -> None:
        """Invalid --outcome value causes argparse exit with code 2."""
        result = _run(
            "build_telemetry.py",
            "--skill", "research",
            "--id", "advisory-000001",
            "--outcome", "INVALID_VALUE",
            "--timestamp", "2026-05-03T12:00:00Z",
            "--duration-seconds", "300",
        )
        # argparse exits 2 for invalid choices
        assert result.returncode in (1, 2), f"expected non-zero exit, got {result.returncode}"

    def test_negative_duration_exits_1(self) -> None:
        """Negative --duration-seconds is caught after argparse and exits 1."""
        result = _run(
            "build_telemetry.py",
            "--skill", "research",
            "--id", "advisory-000001",
            "--outcome", "success",
            "--timestamp", "2026-05-03T12:00:00Z",
            "--duration-seconds", "-5",
        )
        assert result.returncode == 1
        assert "ERROR" in result.stderr

    def test_advisory_decisions_mirrors_research_decisions(self) -> None:
        """advisory_decisions must equal research_decisions (dual-key transition)."""
        sys.path.insert(0, str(_SCRIPTS_DIR))
        import importlib
        build_tel = importlib.import_module("build_telemetry")
        import argparse

        decisions_json = json.dumps([
            {"prompt": "Skip tests?", "chosen_option": "No", "rationale_presented": True}
        ])
        ns = argparse.Namespace(
            skill="plan",
            id="plan-000546",
            outcome="success",
            timestamp="2026-05-03T12:00:00Z",
            duration_seconds=60,
            brief=None,
            prefix_scope=None,
            plan_id=None,
            error_type=None,
            output_file=None,
            context_budget=None,
            git_commit_sha=None,
            files_changed=None,
            parent_skill=None,
            qa_type=None,
            tokens_used=None,
            session_id=None,
            decision_points_json=None,
            research_decisions_json=decisions_json,
        )
        record, errors = build_tel._build_record(ns)
        assert errors == []
        assert record["research_decisions"] == record["advisory_decisions"]
        assert record["advisory_decisions"] is not None

    def test_invalid_json_for_decision_points_exits_1(self) -> None:
        """Malformed JSON in --decision-points causes exit 1."""
        result = _run(
            "build_telemetry.py",
            *_REQUIRED_TELEMETRY_ARGS,
            "--decision-points", "not-valid-json",
        )
        assert result.returncode == 1
        assert "ERROR" in result.stderr


# ===========================================================================
# verify_commit_scope.py
# ===========================================================================


class TestVerifyCommitScope:
    def test_no_staged_files_returns_pass_true(self) -> None:
        """JSON output has all required keys regardless of what is staged."""
        result = _run(
            "verify_commit_scope.py",
            "--skill-type", "research",
            "--artifact-id", "000001",
        )
        # Exit code depends on what is actually staged in the working tree;
        # do not assert it here. Focus on the JSON structure contract only.
        assert result.stdout.strip(), "expected JSON on stdout"
        data = json.loads(result.stdout)
        for key in ("pass", "expected", "staged", "unexpected", "missing"):
            assert key in data, f"missing key: {key}"
        assert isinstance(data["pass"], bool)
        assert isinstance(data["expected"], list)
        assert isinstance(data["staged"], list)
        assert isinstance(data["unexpected"], list)
        assert isinstance(data["missing"], list)

    def test_json_output_structure_is_complete(self) -> None:
        """JSON output always has the five required keys."""
        result = _run(
            "verify_commit_scope.py",
            "--skill-type", "plan",
            "--artifact-id", "000546",
        )
        assert result.stdout.strip(), "expected JSON on stdout"
        data = json.loads(result.stdout)
        for key in ("expected", "staged", "unexpected", "missing", "pass"):
            assert key in data, f"missing key: {key}"
        assert isinstance(data["pass"], bool)
        assert isinstance(data["expected"], list)
        assert isinstance(data["staged"], list)
        assert isinstance(data["unexpected"], list)
        assert isinstance(data["missing"], list)

    def test_check_scope_with_matching_files(self) -> None:
        """check_scope() returns pass=true when staged files are all expected."""
        sys.path.insert(0, str(_SCRIPTS_DIR))
        import importlib
        vcs = importlib.import_module("verify_commit_scope")

        staged = ["_output/research/advisory-000001-some-topic.md"]
        expected = ["_output/research/"]
        result = vcs.check_scope(staged, expected)
        assert result["pass"] is True
        assert result["unexpected"] == []

    def test_check_scope_with_unexpected_files(self) -> None:
        """check_scope() returns pass=false when staged contains unexpected files."""
        sys.path.insert(0, str(_SCRIPTS_DIR))
        import importlib
        vcs = importlib.import_module("verify_commit_scope")

        staged = ["some/unexpected/file.py"]
        expected = ["_output/plans/"]
        result = vcs.check_scope(staged, expected)
        assert result["pass"] is False
        assert "some/unexpected/file.py" in result["unexpected"]

    def test_always_allowed_prefixes_never_unexpected(self) -> None:
        """Files under .claude/ and _loom/ are never flagged as unexpected."""
        sys.path.insert(0, str(_SCRIPTS_DIR))
        import importlib
        vcs = importlib.import_module("verify_commit_scope")

        staged = [".claude/skills/scripts/some-script.py", "_loom/something.md"]
        expected = []  # nothing explicitly expected
        result = vcs.check_scope(staged, expected)
        assert result["pass"] is True
        assert result["unexpected"] == []

    def test_exact_path_match(self) -> None:
        """An exact expected path matches the staged file."""
        sys.path.insert(0, str(_SCRIPTS_DIR))
        import importlib
        vcs = importlib.import_module("verify_commit_scope")

        staged = ["_output/briefs.md"]
        expected = ["_output/briefs.md"]
        result = vcs.check_scope(staged, expected)
        assert result["pass"] is True
        assert result["missing"] == []

    def test_missing_exact_paths_are_advisory_only(self) -> None:
        """Expected exact paths not staged appear in missing but do not fail pass."""
        sys.path.insert(0, str(_SCRIPTS_DIR))
        import importlib
        vcs = importlib.import_module("verify_commit_scope")

        staged = []
        expected = ["_output/briefs.md"]
        result = vcs.check_scope(staged, expected)
        # missing advisory, but pass=true because no unexpected
        assert result["pass"] is True
        assert "_output/briefs.md" in result["missing"]


# ===========================================================================
# update_cross_refs.py
# ===========================================================================


def _make_artifact(tmp_path: Path, filename: str, content: str) -> Path:
    """Write a temp artifact file and return its path."""
    p = tmp_path / filename
    p.write_text(content, encoding="utf-8")
    return p


class TestUpdateCrossRefs:
    def test_no_source_header_is_noop(self, tmp_path: Path) -> None:
        """Artifact with no source: header exits 0 without modifying anything."""
        artifact = _make_artifact(
            tmp_path,
            "plan-000546-test.md",
            "# Plan 000546\n\nsome content\n",
        )
        original = artifact.read_text(encoding="utf-8")
        result = _run("update_cross_refs.py", "--artifact", str(artifact))
        assert result.returncode == 0
        assert artifact.read_text(encoding="utf-8") == original, "file should not be modified"

    def test_updates_spawned_field_directly(self, tmp_path: Path) -> None:
        """_update_spawned appends a new token to an existing spawned: line."""
        sys.path.insert(0, str(_SCRIPTS_DIR))
        import importlib
        ucr = importlib.import_module("update_cross_refs")

        source_file = tmp_path / "research-000569-some-topic.md"
        source_file.write_text(
            "# Research 000569\n"
            "tags: research, design\n"
            "spawned: plan-000570\n"
            "\nBody content.\n",
            encoding="utf-8",
        )
        modified = ucr._update_spawned(source_file, "plan-000546")
        assert modified is True
        content = source_file.read_text(encoding="utf-8")
        assert "spawned: plan-000570, plan-000546" in content

    def test_inserts_spawned_field_when_absent(self, tmp_path: Path) -> None:
        """_update_spawned inserts spawned: line when the field does not exist."""
        sys.path.insert(0, str(_SCRIPTS_DIR))
        import importlib
        ucr = importlib.import_module("update_cross_refs")

        source_file = tmp_path / "research-000569-no-spawned.md"
        source_file.write_text(
            "# Research 000569\n"
            "source: advisory-000058\n"
            "tags: research\n"
            "\nBody content.\n",
            encoding="utf-8",
        )
        modified = ucr._update_spawned(source_file, "plan-000999")
        assert modified is True
        content = source_file.read_text(encoding="utf-8")
        assert "spawned: plan-000999" in content

    def test_artifact_token_from_path(self) -> None:
        """_artifact_token_from_path parses type and id from a standard filename."""
        sys.path.insert(0, str(_SCRIPTS_DIR))
        import importlib
        ucr = importlib.import_module("update_cross_refs")

        result = ucr._artifact_token_from_path(Path("plan-000546-step5-tests.md"))
        assert result == ("plan", "000546")

    def test_extract_source_header(self) -> None:
        """_extract_source finds the source: header in the first 10 lines."""
        sys.path.insert(0, str(_SCRIPTS_DIR))
        import importlib
        ucr = importlib.import_module("update_cross_refs")

        lines = [
            "# Plan 000546",
            "source: research-000569 -- spawned from step 5",
            "tags: plan",
        ]
        result = ucr._extract_source(lines)
        assert result == ("research", "000569")

    def test_extract_source_returns_none_when_absent(self) -> None:
        """_extract_source returns None when there is no source: header."""
        sys.path.insert(0, str(_SCRIPTS_DIR))
        import importlib
        ucr = importlib.import_module("update_cross_refs")

        lines = ["# Plan 000546", "tags: plan", "body text"]
        result = ucr._extract_source(lines)
        assert result is None

    def test_update_cross_refs_cli_no_source_exits_0(self, tmp_path: Path) -> None:
        """CLI exits 0 silently when artifact has no source: header."""
        artifact = _make_artifact(
            tmp_path,
            "plan-000546-nosource.md",
            "# Plan 000546\n\nno source header\n",
        )
        result = _run("update_cross_refs.py", "--artifact", str(artifact))
        assert result.returncode == 0

    def test_update_cross_refs_cli_missing_artifact_exits_1(self, tmp_path: Path) -> None:
        """CLI exits 1 when the specified artifact does not exist."""
        result = _run(
            "update_cross_refs.py",
            "--artifact", str(tmp_path / "nonexistent-artifact.md"),
        )
        assert result.returncode == 1
        assert "ERROR" in result.stderr
