"""Tests for check_harness_drift.

Covers:
- compute_drift() core logic
- CLI detect mode (text + JSON output, plan generation)
- CLI apply mode (plan parsing, selective application)
"""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

import check_harness_drift as chd


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_harness(root: Path, files: dict[str, str]) -> None:
    """Create a minimal harness tree under *root*.

    *files* maps relative paths (POSIX-style) to file content strings.
    Every entry must live under ``.claude/`` to be discoverable by
    ``collect_source_files()``.
    """
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _skill_file(name: str = "demo", body: str = "# Demo") -> dict[str, str]:
    """Return a single-skill file dict for ``_make_harness``."""
    return {
        f".claude/skills/{name}/SKILL.md": f"---\nname: {name}\n---\n{body}\n"
    }


def _script_file(name: str = "helper.py", body: str = "# helper") -> dict[str, str]:
    """Return a single scripts/ file dict for ``_make_harness``."""
    return {f".claude/skills/scripts/{name}": body}


# ---------------------------------------------------------------------------
# compute_drift — core logic
# ---------------------------------------------------------------------------


class TestComputeDriftSelfComparison:
    """Same directory as source and target should yield empty drift."""

    def test_self_comparison_returns_empty(self, tmp_path):
        _make_harness(tmp_path, {**_skill_file(), **_script_file()})
        report = chd.compute_drift(tmp_path, tmp_path)
        assert report.add == []
        assert report.remove == []
        assert report.revise == []


class TestComputeDriftAdd:
    """File present in source but absent in target -> ADD."""

    def test_file_in_source_not_in_target(self, tmp_path):
        source = tmp_path / "source"
        target = tmp_path / "target"
        _make_harness(source, {**_skill_file("plan"), **_skill_file("check")})
        _make_harness(target, _skill_file("plan"))

        report = chd.compute_drift(source, target)
        add_paths = [e.rel_path for e in report.add]
        assert ".claude/skills/check/SKILL.md" in add_paths

    def test_preserved_paths_excluded_from_add(self, tmp_path):
        """is_preserved() paths should never appear in ADD."""
        source = tmp_path / "source"
        target = tmp_path / "target"
        # Create a skill in both plus _output/ only in source
        _make_harness(source, {
            **_skill_file("plan"),
            "_output/something.md": "data",
        })
        _make_harness(target, _skill_file("plan"))

        report = chd.compute_drift(source, target)
        add_paths = [e.rel_path for e in report.add]
        assert not any("_output" in p for p in add_paths)


class TestComputeDriftRemove:
    """File present in target but absent in source -> REMOVE."""

    def test_file_in_target_not_in_source(self, tmp_path):
        source = tmp_path / "source"
        target = tmp_path / "target"
        _make_harness(source, _skill_file("plan"))
        _make_harness(target, {**_skill_file("plan"), **_skill_file("stale")})

        report = chd.compute_drift(source, target)
        remove_paths = [e.rel_path for e in report.remove]
        assert ".claude/skills/stale/SKILL.md" in remove_paths

    def test_preserved_paths_excluded_from_remove(self, tmp_path):
        """is_preserved() paths should never appear in REMOVE."""
        source = tmp_path / "source"
        target = tmp_path / "target"
        _make_harness(source, _skill_file("plan"))
        _make_harness(target, {
            **_skill_file("plan"),
            "product-design/conventions.md": "custom",
        })

        report = chd.compute_drift(source, target)
        remove_paths = [e.rel_path for e in report.remove]
        assert not any("product-design" in p for p in remove_paths)


class TestComputeDriftRevise:
    """Files present in both but with different content -> REVISE."""

    def test_different_content_detected(self, tmp_path):
        source = tmp_path / "source"
        target = tmp_path / "target"
        _make_harness(source, _skill_file("plan", body="# Plan v2"))
        _make_harness(target, _skill_file("plan", body="# Plan v1"))

        report = chd.compute_drift(source, target)
        revise_paths = [e.rel_path for e in report.revise]
        assert ".claude/skills/plan/SKILL.md" in revise_paths


# ---------------------------------------------------------------------------
# CLI — JSON output
# ---------------------------------------------------------------------------


class TestJsonOutput:
    """--json flag produces valid JSON with expected structure."""

    def test_json_flag_outputs_valid_json(self, tmp_path, capsys):
        source = tmp_path / "source"
        target = tmp_path / "target"
        _make_harness(source, {**_skill_file("plan"), **_skill_file("new")})
        _make_harness(target, {**_skill_file("plan"), **_skill_file("stale")})

        # Invoke via main with --json
        exit_code = chd.run_detect(source, target, json_output=True, plan_output=None)
        captured = capsys.readouterr()
        data = json.loads(captured.out)

        assert "add" in data
        assert "remove" in data
        assert "revise" in data
        assert exit_code == 1  # drift found


# ---------------------------------------------------------------------------
# CLI — plan output
# ---------------------------------------------------------------------------


class TestPlanOutput:
    """--plan-output generates a markdown remediation plan."""

    def test_plan_file_generated(self, tmp_path):
        source = tmp_path / "source"
        target = tmp_path / "target"
        plan_path = tmp_path / "drift-plan.md"

        _make_harness(source, {
            **_skill_file("plan", body="# Plan v2"),
            **_skill_file("new"),
        })
        _make_harness(target, {
            **_skill_file("plan", body="# Plan v1"),
            **_skill_file("stale"),
        })

        chd.run_detect(source, target, json_output=False, plan_output=plan_path)
        assert plan_path.is_file()
        content = plan_path.read_text(encoding="utf-8")

        # Check structure
        assert "# Drift Remediation Plan" in content
        assert "## Files to Add" in content
        assert "## Files to Remove" in content
        assert "## Files to Revise" in content

    def test_plan_has_remove_checklist(self, tmp_path):
        source = tmp_path / "source"
        target = tmp_path / "target"
        plan_path = tmp_path / "drift-plan.md"

        _make_harness(source, _skill_file("plan"))
        _make_harness(target, {**_skill_file("plan"), **_skill_file("stale")})

        chd.run_detect(source, target, json_output=False, plan_output=plan_path)
        content = plan_path.read_text(encoding="utf-8")

        assert "- [ ] .claude/skills/stale/SKILL.md" in content

    def test_plan_has_revise_with_diff(self, tmp_path):
        source = tmp_path / "source"
        target = tmp_path / "target"
        plan_path = tmp_path / "drift-plan.md"

        _make_harness(source, _skill_file("plan", body="# Plan v2"))
        _make_harness(target, _skill_file("plan", body="# Plan v1"))

        chd.run_detect(source, target, json_output=False, plan_output=plan_path)
        content = plan_path.read_text(encoding="utf-8")

        assert "- [ ] .claude/skills/plan/SKILL.md" in content
        assert "Changes:" in content

    def test_plan_has_add_informational(self, tmp_path):
        source = tmp_path / "source"
        target = tmp_path / "target"
        plan_path = tmp_path / "drift-plan.md"

        _make_harness(source, {**_skill_file("plan"), **_skill_file("new")})
        _make_harness(target, _skill_file("plan"))

        chd.run_detect(source, target, json_output=False, plan_output=plan_path)
        content = plan_path.read_text(encoding="utf-8")

        assert "## Files to Add" in content
        assert ".claude/skills/new/SKILL.md" in content


# ---------------------------------------------------------------------------
# CLI — apply mode
# ---------------------------------------------------------------------------


class TestApplyMode:
    """--apply mode parses the plan and applies only entries still present."""

    def _make_plan(self, plan_path: Path, add: list[str], remove: list[str],
                   revise: list[str]) -> None:
        """Write a minimal remediation plan file."""
        lines = ["# Drift Remediation Plan", "Source: /source", "Target: /target",
                 "Generated: 2026-05-01T00:00:00Z", "",
                 "## Files to Add (informational -- no review needed)"]
        for a in add:
            lines.append(f"- {a}")
        lines.append("")
        lines.append("## Files to Remove")
        lines.append("Delete these files from the target. Remove an entry to exclude it.")
        for r in remove:
            lines.append(f"- [ ] {r}")
        lines.append("")
        lines.append("## Files to Revise")
        lines.append("Overwrite these target files with the source version. Remove an entry to exclude it.")
        for v in revise:
            lines.append(f"- [ ] {v}")
            lines.append("  Changes: (diff)")
        plan_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def test_apply_respects_deleted_entries(self, tmp_path):
        """User deleted one REMOVE and one REVISE entry -- those files stay untouched."""
        source = tmp_path / "source"
        target = tmp_path / "target"

        _make_harness(source, {
            **_skill_file("plan", body="# Plan v2"),
            **_skill_file("check", body="# Check v2"),
            **_skill_file("new"),
        })
        _make_harness(target, {
            **_skill_file("plan", body="# Plan v1"),
            **_skill_file("check", body="# Check v1"),
            **_skill_file("stale-a"),
            **_skill_file("stale-b"),
        })

        plan_path = tmp_path / "plan.md"
        # Write plan with stale-a and stale-b in REMOVE, plan and check in REVISE
        # Then "delete" stale-b and check from the plan (user decision)
        self._make_plan(
            plan_path,
            add=[".claude/skills/new/SKILL.md"],
            remove=[".claude/skills/stale-a/SKILL.md"],  # stale-b intentionally absent
            revise=[".claude/skills/plan/SKILL.md"],  # check intentionally absent
        )

        exit_code = chd.run_apply(plan_path, source, target)
        assert exit_code == 0

        # stale-a should be deleted (was in plan)
        assert not (target / ".claude/skills/stale-a/SKILL.md").is_file()

        # stale-b should still exist (user removed from plan)
        assert (target / ".claude/skills/stale-b/SKILL.md").is_file()

        # plan should be overwritten with source version
        plan_content = (target / ".claude/skills/plan/SKILL.md").read_text(encoding="utf-8")
        assert "Plan v2" in plan_content

        # check should be untouched (user removed from plan)
        check_content = (target / ".claude/skills/check/SKILL.md").read_text(encoding="utf-8")
        assert "Check v1" in check_content

        # new should be copied (ADD is unconditional)
        assert (target / ".claude/skills/new/SKILL.md").is_file()

    def test_apply_copies_add_files_unconditionally(self, tmp_path):
        """ADD entries in the informational section are always applied."""
        source = tmp_path / "source"
        target = tmp_path / "target"

        _make_harness(source, {**_skill_file("plan"), **_skill_file("alpha"), **_skill_file("beta")})
        _make_harness(target, _skill_file("plan"))

        plan_path = tmp_path / "plan.md"
        self._make_plan(
            plan_path,
            add=[".claude/skills/alpha/SKILL.md", ".claude/skills/beta/SKILL.md"],
            remove=[],
            revise=[],
        )

        exit_code = chd.run_apply(plan_path, source, target)
        assert exit_code == 0
        assert (target / ".claude/skills/alpha/SKILL.md").is_file()
        assert (target / ".claude/skills/beta/SKILL.md").is_file()

    def test_apply_rejects_path_traversal(self, tmp_path):
        """Plan entries with ../../ paths are rejected and the file is not touched."""
        source = tmp_path / "source"
        target = tmp_path / "target"

        _make_harness(source, _skill_file("plan"))
        _make_harness(target, _skill_file("plan"))

        secret = tmp_path / "secret.txt"
        secret.write_text("do not delete", encoding="utf-8")

        plan_path = tmp_path / "plan.md"
        self._make_plan(
            plan_path,
            add=[],
            remove=["../../secret.txt"],
            revise=[],
        )

        exit_code = chd.run_apply(plan_path, source, target)
        assert exit_code == 0
        assert secret.read_text(encoding="utf-8") == "do not delete"


# ---------------------------------------------------------------------------
# Exit codes
# ---------------------------------------------------------------------------


class TestExitCodes:
    """Exit code semantics: 0=no drift, 1=drift found, 2=error."""

    def test_exit_0_no_drift(self, tmp_path):
        _make_harness(tmp_path, {**_skill_file(), **_script_file()})
        code = chd.run_detect(tmp_path, tmp_path, json_output=False, plan_output=None)
        assert code == 0

    def test_exit_1_drift_found(self, tmp_path):
        source = tmp_path / "source"
        target = tmp_path / "target"
        _make_harness(source, {**_skill_file("plan"), **_skill_file("new")})
        _make_harness(target, _skill_file("plan"))
        code = chd.run_detect(source, target, json_output=False, plan_output=None)
        assert code == 1
