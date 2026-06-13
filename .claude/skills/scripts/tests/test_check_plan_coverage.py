"""Tests for check_plan_coverage.py -- plan coverage verification."""
from pathlib import Path

import pytest

from check_plan_coverage import (
    Finding,
    Requirement,
    CLASSIFICATION_MAP,
    SECURITY_CLASSIFICATIONS,
    extract_requirements,
    extract_traces,
    compute_coverage,
    _extract_title,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_project_structure(tmp_path):
    """Create the _references/project/, _output/plans/, and .claude/ dirs."""
    project_dir = tmp_path / "_references" / "project"
    project_dir.mkdir(parents=True)
    plans_dir = tmp_path / "_output" / "plans"
    plans_dir.mkdir(parents=True)
    (tmp_path / ".claude").mkdir(exist_ok=True)
    return project_dir, plans_dir


SAMPLE_SPEC = """\
# Design Intent To-Be

## 1. Platform Purpose

A sample platform.

## 2. Entity Hierarchy

<!-- REQ-ENT-001 -->
### User

The primary entity.

<!-- REQ-ENT-002 -->
### Group

A container for users.

## 4. Permission Model

<!-- REQ-PERM-001 -->
| Role | Level | Capabilities |
|------|-------|-------------|
| Admin | 100 | Full access |

<!-- REQ-PERM-002 -->
| Role | Level | Capabilities |
|------|-------|-------------|
| Viewer | 10 | Read-only access |

## 8. User Experience Patterns (Domain-Driven)

<!-- REQ-UX-001 -->
### Drag-and-drop reorder

Users can reorder items.

## 10. Validation Constants (Domain)

<!-- REQ-VAL-001 -->
| Constant | Value | Domain Rationale |
|----------|-------|-----------------|
| Username length | 3--50 chars | Common name range |

## 7. User Community & Localization

<!-- REQ-I18N-001 -->
### pt-BR locale support

Primary locale.
"""

SAMPLE_PLAN_FULL_COVERAGE = """\
# Plan 000100 | FEATURE-B | 2026-04-06 | User entity

## Steps

### Step 1: Create User model
- **Files**: backend/app/models/user.py (create)
- **Traces**: REQ-ENT-001, REQ-PERM-001
- [ ] Done

### Step 2: Create Group model
- **Files**: backend/app/models/group.py (create)
- **Traces**: REQ-ENT-002, REQ-PERM-002
- [ ] Done

### Step 3: Add UX pattern
- **Files**: frontend/src/components/dnd.tsx (create)
- **Traces**: REQ-UX-001
- [ ] Done

### Step 4: Add validation
- **Files**: backend/app/utils/validation.py (create)
- **Traces**: REQ-VAL-001
- [ ] Done

### Step 5: Add i18n
- **Files**: frontend/src/i18n/pt-BR.json (create)
- **Traces**: REQ-I18N-001
- [ ] Done
"""

SAMPLE_PLAN_PARTIAL_COVERAGE = """\
# Plan 000101 | FEATURE-B | 2026-04-06 | Partial coverage

## Steps

### Step 1: Create User model
- **Files**: backend/app/models/user.py (create)
- **Traces**: REQ-ENT-001
- [ ] Done
"""


# ---------------------------------------------------------------------------
# 1. Requirement extraction
# ---------------------------------------------------------------------------

class TestRequirementExtraction:

    def test_extracts_all_markers(self, tmp_path):
        project_dir, _ = _make_project_structure(tmp_path)
        spec_file = project_dir / "product-design-as-intended.md"
        spec_file.write_text(SAMPLE_SPEC, encoding="utf-8")

        reqs = extract_requirements(spec_file)
        assert len(reqs) == 7

        ids = [r.id for r in reqs]
        assert "REQ-ENT-001" in ids
        assert "REQ-ENT-002" in ids
        assert "REQ-PERM-001" in ids
        assert "REQ-PERM-002" in ids
        assert "REQ-UX-001" in ids
        assert "REQ-VAL-001" in ids
        assert "REQ-I18N-001" in ids

    def test_extracts_correct_sections(self, tmp_path):
        project_dir, _ = _make_project_structure(tmp_path)
        spec_file = project_dir / "product-design-as-intended.md"
        spec_file.write_text(SAMPLE_SPEC, encoding="utf-8")

        reqs = extract_requirements(spec_file)
        by_id = {r.id: r for r in reqs}

        assert "2." in by_id["REQ-ENT-001"].section
        assert "4." in by_id["REQ-PERM-001"].section
        assert "8." in by_id["REQ-UX-001"].section

    def test_extracts_titles(self, tmp_path):
        project_dir, _ = _make_project_structure(tmp_path)
        spec_file = project_dir / "product-design-as-intended.md"
        spec_file.write_text(SAMPLE_SPEC, encoding="utf-8")

        reqs = extract_requirements(spec_file)
        by_id = {r.id: r for r in reqs}

        assert "User" in by_id["REQ-ENT-001"].title
        assert "Group" in by_id["REQ-ENT-002"].title

    def test_empty_file_returns_empty(self, tmp_path):
        project_dir, _ = _make_project_structure(tmp_path)
        spec_file = project_dir / "product-design-as-intended.md"
        spec_file.write_text("# Empty spec\n", encoding="utf-8")

        reqs = extract_requirements(spec_file)
        assert reqs == []

    def test_missing_file_returns_empty(self, tmp_path):
        nonexistent = tmp_path / "nonexistent.md"
        reqs = extract_requirements(nonexistent)
        assert reqs == []

    def test_extract_requirements_ignores_d_nnn_headings(self, tmp_path):
        """REQ-TYPE-NNN and D-NNN are orthogonal ID conventions.

        plan-000268 Amendment A2 regression guard: the REQ extraction regex
        must NOT accidentally match D-NNN Decision entries. The merged
        product-design-as-intended.md file carries both (REQ markers on sections and
        D-NNN headings on Decision entries in `## Decisions`).
        """
        project_dir, _ = _make_project_structure(tmp_path)
        spec_file = project_dir / "product-design-as-intended.md"
        spec_file.write_text(
            "# Design Intent\n\n"
            "## 2. Entity Hierarchy\n\n"
            "<!-- REQ-ENT-001 -->\n"
            "### User\n\n"
            "The primary entity.\n\n"
            "## Decisions\n\n"
            "<!-- STATUS: proposed -->\n"
            "### D-001: Use Postgres\n\n"
            "**Context**: The codebase needs a transactional database.\n"
            "**Decision**: Use Postgres 16.\n"
            "**Consequences**: We gain MVCC and mature tooling.\n",
            encoding="utf-8",
        )

        reqs = extract_requirements(spec_file)
        ids = [r.id for r in reqs]

        assert "REQ-ENT-001" in ids, "REQ marker should be extracted"
        assert len(reqs) == 1, (
            f"expected exactly 1 requirement, got {len(reqs)}: {ids}"
        )
        # D-001 must NOT appear in the extracted REQ list.
        assert not any("D-001" in r.id for r in reqs), (
            "D-NNN Decision heading was mistakenly extracted as a requirement"
        )


# ---------------------------------------------------------------------------
# 2. Trace extraction
# ---------------------------------------------------------------------------

class TestTraceExtraction:

    def test_extracts_traces_from_plan(self, tmp_path):
        _, plans_dir = _make_project_structure(tmp_path)
        plan_file = plans_dir / "plan-000100-user-entity.md"
        plan_file.write_text(SAMPLE_PLAN_FULL_COVERAGE, encoding="utf-8")

        traces = extract_traces(plans_dir)
        assert "REQ-ENT-001" in traces
        assert "REQ-PERM-001" in traces
        assert "000100" in traces["REQ-ENT-001"]

    def test_multiple_traces_per_step(self, tmp_path):
        _, plans_dir = _make_project_structure(tmp_path)
        plan_file = plans_dir / "plan-000100-user-entity.md"
        plan_file.write_text(SAMPLE_PLAN_FULL_COVERAGE, encoding="utf-8")

        traces = extract_traces(plans_dir)
        # Step 1 traces both REQ-ENT-001 and REQ-PERM-001
        assert "REQ-ENT-001" in traces
        assert "REQ-PERM-001" in traces

    def test_no_plans_dir_returns_empty(self, tmp_path):
        traces = extract_traces(tmp_path / "nonexistent")
        assert traces == {}

    def test_plan_without_traces_ignored(self, tmp_path):
        _, plans_dir = _make_project_structure(tmp_path)
        plan_file = plans_dir / "plan-000102-no-traces.md"
        plan_file.write_text(
            "# Plan 000102\n\n### Step 1\n- **Files**: foo.py\n- [ ] Done\n",
            encoding="utf-8",
        )

        traces = extract_traces(plans_dir)
        assert traces == {}


# ---------------------------------------------------------------------------
# 3. Coverage computation
# ---------------------------------------------------------------------------

class TestCoverageComputation:

    def test_full_coverage_no_gaps(self, tmp_path):
        project_dir, plans_dir = _make_project_structure(tmp_path)
        spec_file = project_dir / "product-design-as-intended.md"
        spec_file.write_text(SAMPLE_SPEC, encoding="utf-8")
        plan_file = plans_dir / "plan-000100-user-entity.md"
        plan_file.write_text(SAMPLE_PLAN_FULL_COVERAGE, encoding="utf-8")

        findings = compute_coverage(tmp_path, verbose=True)

        # Should have info summary + "all covered" message
        errors = [f for f in findings if f.severity == "error"]
        warnings = [f for f in findings if f.severity == "warning"]
        assert len(errors) == 0
        assert len(warnings) == 0

    def test_partial_coverage_reports_gaps(self, tmp_path):
        project_dir, plans_dir = _make_project_structure(tmp_path)
        spec_file = project_dir / "product-design-as-intended.md"
        spec_file.write_text(SAMPLE_SPEC, encoding="utf-8")
        plan_file = plans_dir / "plan-000101-partial.md"
        plan_file.write_text(SAMPLE_PLAN_PARTIAL_COVERAGE, encoding="utf-8")

        findings = compute_coverage(tmp_path, verbose=False)

        # Should report gaps for uncovered requirements
        errors = [f for f in findings if f.severity == "error"]
        warnings = [f for f in findings if f.severity == "warning"]
        # PERM-001, PERM-002, VAL-001 are security -> errors
        assert len(errors) == 3
        # ENT-002, UX-001, I18N-001 are non-security -> warnings
        assert len(warnings) == 3

    def test_no_requirements_passes(self, tmp_path):
        project_dir, _ = _make_project_structure(tmp_path)
        spec_file = project_dir / "product-design-as-intended.md"
        spec_file.write_text("# Empty spec\nNo REQ markers.\n", encoding="utf-8")

        findings = compute_coverage(tmp_path, verbose=True)
        errors = [f for f in findings if f.severity == "error"]
        assert len(errors) == 0

    def test_no_spec_file_passes(self, tmp_path):
        _make_project_structure(tmp_path)
        findings = compute_coverage(tmp_path, verbose=True)
        errors = [f for f in findings if f.severity == "error"]
        assert len(errors) == 0


# ---------------------------------------------------------------------------
# 4. Classification derivation
# ---------------------------------------------------------------------------

class TestClassification:

    def test_perm_is_security(self):
        assert CLASSIFICATION_MAP["PERM"] == "security"

    def test_val_is_security(self):
        assert CLASSIFICATION_MAP["VAL"] == "security"

    def test_ux_is_ux(self):
        assert CLASSIFICATION_MAP["UX"] == "ux"

    def test_mc_is_ux(self):
        assert CLASSIFICATION_MAP["MC"] == "ux"

    def test_jm_is_ux(self):
        assert CLASSIFICATION_MAP["JM"] == "ux"

    def test_ent_is_technical(self):
        assert CLASSIFICATION_MAP["ENT"] == "technical"

    def test_delta_is_technical(self):
        assert CLASSIFICATION_MAP["DELTA"] == "technical"

    def test_i18n_is_cross_cutting(self):
        assert CLASSIFICATION_MAP["I18N"] == "cross-cutting"


# ---------------------------------------------------------------------------
# 5. Security gap escalation
# ---------------------------------------------------------------------------

class TestSecurityEscalation:

    def test_security_gaps_are_errors(self, tmp_path):
        project_dir, plans_dir = _make_project_structure(tmp_path)
        spec_file = project_dir / "product-design-as-intended.md"
        spec_file.write_text(
            "## 4. Permission Model\n<!-- REQ-PERM-001 -->\n### Admin role\n",
            encoding="utf-8",
        )

        findings = compute_coverage(tmp_path, verbose=False)
        gap_findings = [f for f in findings if "Untraced" in f.message]
        assert len(gap_findings) == 1
        assert gap_findings[0].severity == "error"

    def test_non_security_gaps_are_warnings(self, tmp_path):
        project_dir, plans_dir = _make_project_structure(tmp_path)
        spec_file = project_dir / "product-design-as-intended.md"
        spec_file.write_text(
            "## 2. Entity Hierarchy\n<!-- REQ-ENT-001 -->\n### User\n",
            encoding="utf-8",
        )

        findings = compute_coverage(tmp_path, verbose=False)
        gap_findings = [f for f in findings if "Untraced" in f.message]
        assert len(gap_findings) == 1
        assert gap_findings[0].severity == "warning"


# ---------------------------------------------------------------------------
# 6. Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_malformed_req_id_ignored(self, tmp_path):
        project_dir, _ = _make_project_structure(tmp_path)
        spec_file = project_dir / "product-design-as-intended.md"
        spec_file.write_text(
            "## 2. Entity\n<!-- REQ-INVALID -->\n### Bad marker\n"
            "<!-- REQ- -->\n### Also bad\n",
            encoding="utf-8",
        )

        reqs = extract_requirements(spec_file)
        assert reqs == []

    def test_extract_title_from_heading(self):
        lines = ["### User Entity", "Description here"]
        title = _extract_title(lines, 0)
        assert "User Entity" in title

    def test_extract_title_from_table_row(self):
        lines = ["| Admin | 100 | Full access |"]
        title = _extract_title(lines, 0)
        assert "Admin" in title

    def test_extract_title_skips_empty_lines(self):
        lines = ["", "", "### Actual Title"]
        title = _extract_title(lines, 0)
        assert "Actual Title" in title
