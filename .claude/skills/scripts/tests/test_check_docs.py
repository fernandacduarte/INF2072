"""Tests for check_docs.py plugins added in plan-000283.

Covers ``harness-reference-coverage`` and ``lifecycle-fact-uniqueness``
plugins plus their module-level helpers. Fixtures live under
``tests/fixtures/check_docs/``. The generator module is stubbed via
``monkeypatch.setitem(sys.modules, ...)`` so tests do not depend on the real
``generate_harness_reference`` behavior.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

import check_docs

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "check_docs"
CLEAN = FIXTURES / "clean_harness"
DRIFT = FIXTURES / "drift_harness"
MISSING = FIXTURES / "missing_reference"
SHORT = FIXTURES / "short_paragraph_fixture"


def _make_generator_stub(render_output: str) -> types.ModuleType:
    """Build a fake ``generate_harness_reference`` module.

    ``discover_all`` returns an empty list and ``render_harness_reference``
    returns ``render_output`` verbatim so the drift check can be controlled.
    """
    mod = types.ModuleType("generate_harness_reference")

    def discover_all(root: Path):  # noqa: ARG001 - signature match
        return []

    def render_harness_reference(artifacts, public_docs_root, generated_at):  # noqa: ARG001
        return render_output

    mod.discover_all = discover_all
    mod.render_harness_reference = render_harness_reference
    return mod


def _stub_generator_matching(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    """Stub the generator so its output matches the fixture's reference file.

    Used to force the regen-drift sub-check to report "in sync" for the clean
    fixture regardless of what the real generator would produce.
    """
    reference = root / "seja-public" / "docs" / "reference" / "harness-reference.md"
    text = reference.read_text(encoding="utf-8")
    stub = _make_generator_stub(text)
    monkeypatch.setitem(sys.modules, "generate_harness_reference", stub)


def _stub_generator_diverging(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub the generator so its output never matches (always drift)."""
    stub = _make_generator_stub("intentionally different text")
    monkeypatch.setitem(sys.modules, "generate_harness_reference", stub)


# ---------------------------------------------------------------------------
# plugin_harness_reference_coverage
# ---------------------------------------------------------------------------


def test_clean_harness_has_no_findings(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_generator_matching(monkeypatch, CLEAN)
    findings = check_docs.plugin_harness_reference_coverage(CLEAN, verbose=False)
    warnings = [f for f in findings if f.severity == "warning"]
    errors = [f for f in findings if f.severity == "error"]
    assert not warnings, f"unexpected warnings: {[f.message for f in warnings]}"
    assert not errors, f"unexpected errors: {[f.message for f in errors]}"


def test_coverage_flags_missing_file(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_generator_diverging(monkeypatch)
    findings = check_docs.plugin_harness_reference_coverage(DRIFT, verbose=False)
    coverage_hits = [
        f for f in findings
        if f.severity == "warning"
        and "ghost-agent.md" in f.message
        and "not mentioned" in f.message
    ]
    assert len(coverage_hits) == 1, (
        f"expected exactly one coverage warning for ghost-agent.md; got "
        f"{[f.message for f in findings]}"
    )


def test_nonexistent_target_is_flagged(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_generator_diverging(monkeypatch)
    findings = check_docs.plugin_harness_reference_coverage(DRIFT, verbose=False)
    hits = [
        f for f in findings
        if f.severity == "warning"
        and "deleted-rule.md" in f.message
        and "nonexistent file" in f.message
    ]
    assert len(hits) == 1, (
        f"expected one nonexistent-target warning for deleted-rule.md; got "
        f"{[f.message for f in findings]}"
    )


def test_cross_ref_missing_public_doc_is_flagged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_generator_diverging(monkeypatch)
    findings = check_docs.plugin_harness_reference_coverage(DRIFT, verbose=False)
    hits = [
        f for f in findings
        if f.severity == "warning"
        and "missing.md" in f.message
        and "nonexistent public doc" in f.message
    ]
    assert len(hits) == 1, (
        f"expected one cross-ref warning for missing.md; got "
        f"{[f.message for f in findings]}"
    )


def test_missing_reference_file_degrades_gracefully(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_generator_diverging(monkeypatch)
    findings = check_docs.plugin_harness_reference_coverage(MISSING, verbose=False)
    assert len(findings) == 1
    assert findings[0].severity == "info"
    assert "not found" in findings[0].message


def test_plugin_harness_reference_coverage_is_registered() -> None:
    assert "harness-reference-coverage" in check_docs._PLUGINS
    desc, func = check_docs._PLUGINS["harness-reference-coverage"]
    assert callable(func)
    assert "harness-reference" in desc.lower()


# ---------------------------------------------------------------------------
# plugin_lifecycle_fact_uniqueness
# ---------------------------------------------------------------------------


def test_clean_how_tos_have_no_findings() -> None:
    findings = check_docs.plugin_lifecycle_fact_uniqueness(CLEAN, verbose=False)
    warnings = [f for f in findings if f.severity == "warning"]
    assert not warnings, (
        f"clean how-tos should not trigger warnings; got "
        f"{[f.message for f in warnings]}"
    )


def test_duplicated_paragraphs_trigger_warning() -> None:
    findings = check_docs.plugin_lifecycle_fact_uniqueness(DRIFT, verbose=False)
    warnings = [f for f in findings if f.severity == "warning"]
    assert warnings, "drift fixture should trigger at least one warning"
    matches = [
        f for f in warnings
        if ("one.md" in f.path and "two.md" in f.message)
        or ("two.md" in f.path and "one.md" in f.message)
        or ("one.md" in f.message and "two.md" in f.message)
    ]
    assert matches, (
        f"expected a warning naming both one.md and two.md; got "
        f"{[(f.path, f.message) for f in warnings]}"
    )


def test_short_paragraphs_below_token_minimum_are_ignored() -> None:
    findings = check_docs.plugin_lifecycle_fact_uniqueness(SHORT, verbose=False)
    warnings = [f for f in findings if f.severity == "warning"]
    assert not warnings, (
        f"short paragraphs below the 8-token minimum should not be flagged; "
        f"got {[f.message for f in warnings]}"
    )


def test_missing_how_to_directory_degrades_gracefully() -> None:
    findings = check_docs.plugin_lifecycle_fact_uniqueness(MISSING, verbose=False)
    assert len(findings) == 1
    assert findings[0].severity == "info"
    assert "how-to" in findings[0].message


def test_plugin_lifecycle_fact_uniqueness_is_registered() -> None:
    assert "lifecycle-fact-uniqueness" in check_docs._PLUGINS
    desc, func = check_docs._PLUGINS["lifecycle-fact-uniqueness"]
    assert callable(func)
    assert "lifecycle" in desc.lower()


def test_before_you_start_paragraphs_excluded() -> None:
    """Paragraphs under 'Before you start' are prerequisite pointers, not
    duplicated facts. The plugin should exclude them from comparison even
    when they are identical across files (advisory-000359 R1)."""
    findings = check_docs.plugin_lifecycle_fact_uniqueness(DRIFT, verbose=False)
    warnings = [f for f in findings if f.severity == "warning"]
    before_warnings = [
        f for f in warnings if "Before you start" in f.message
    ]
    assert not before_warnings, (
        f"'Before you start' paragraphs should be excluded; got "
        f"{[f.message for f in before_warnings]}"
    )


def test_moderate_overlap_below_threshold_not_flagged(tmp_path: Path) -> None:
    """Paragraphs with 60-69% Jaccard overlap should not be flagged after
    the threshold was raised from 0.60 to 0.70 (advisory-000359 R2)."""
    how_to = tmp_path / "seja-public" / "docs" / "how-to"
    how_to.mkdir(parents=True)
    # Two paragraphs sharing ~65% tokens but not identical.
    (how_to / "alpha.md").write_text(
        "# Alpha\n\n## Step 1: Do the thing\n\n"
        "**Harness:** the harness records applied markers, flips status "
        "fields, propagates established dates, and writes journey lifecycle "
        "rotation events into the changelog ledger deterministically.\n",
        encoding="utf-8",
    )
    (how_to / "beta.md").write_text(
        "# Beta\n\n## Step 1: Do the thing\n\n"
        "**Harness:** the harness records applied markers, flips status "
        "fields, propagates validation timestamps, and writes entity "
        "permission updates into the audit trail deterministically.\n",
        encoding="utf-8",
    )
    findings = check_docs.plugin_lifecycle_fact_uniqueness(tmp_path, verbose=False)
    warnings = [f for f in findings if f.severity == "warning"]
    assert not warnings, (
        f"moderate overlap (~65%) should not trigger at 0.70 threshold; got "
        f"{[f.message for f in warnings]}"
    )


# ---------------------------------------------------------------------------
# plugin_docs_frontmatter
# ---------------------------------------------------------------------------


def _write_public_doc(root: Path, rel_path: str, body: str) -> Path:
    """Write ``body`` to ``root/seja-public/docs/<rel_path>`` and return the path."""
    target = root / "seja-public" / "docs" / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    return target


def test_plugin_docs_frontmatter_is_registered() -> None:
    assert "docs-frontmatter" in check_docs._PLUGINS
    desc, func = check_docs._PLUGINS["docs-frontmatter"]
    assert callable(func)
    assert "frontmatter" in desc.lower()


def test_well_formed_frontmatter_has_no_findings(tmp_path: Path) -> None:
    _write_public_doc(
        tmp_path, "ok.md",
        "---\n"
        "diataxis: how-to\n"
        "freshness: release-bound\n"
        "last-reviewed: 2026-04-18\n"
        "---\n\n# OK\n",
    )
    findings = check_docs.plugin_docs_frontmatter(tmp_path, verbose=False)
    warnings = [f for f in findings if f.severity == "warning"]
    assert not warnings, f"unexpected warnings: {[f.message for f in warnings]}"


def test_missing_frontmatter_is_flagged(tmp_path: Path) -> None:
    _write_public_doc(tmp_path, "bare.md", "# No frontmatter\n\nJust prose.\n")
    findings = check_docs.plugin_docs_frontmatter(tmp_path, verbose=False)
    warnings = [f for f in findings if f.severity == "warning"]
    assert len(warnings) == 1
    assert "missing or malformed YAML frontmatter" in warnings[0].message


def test_missing_diataxis_field_is_flagged(tmp_path: Path) -> None:
    _write_public_doc(
        tmp_path, "nodx.md",
        "---\n"
        "freshness: release-bound\n"
        "last-reviewed: 2026-04-18\n"
        "---\n\n# X\n",
    )
    findings = check_docs.plugin_docs_frontmatter(tmp_path, verbose=False)
    hits = [f for f in findings if "'diataxis'" in f.message]
    assert len(hits) == 1, (
        f"expected one diataxis finding; got {[f.message for f in findings]}"
    )


def test_bad_diataxis_value_is_flagged(tmp_path: Path) -> None:
    _write_public_doc(
        tmp_path, "baddx.md",
        "---\n"
        "diataxis: faq\n"
        "freshness: release-bound\n"
        "last-reviewed: 2026-04-18\n"
        "---\n\n# X\n",
    )
    findings = check_docs.plugin_docs_frontmatter(tmp_path, verbose=False)
    hits = [f for f in findings if "diataxis: faq" in f.message]
    assert len(hits) == 1


def test_missing_freshness_field_is_flagged(tmp_path: Path) -> None:
    _write_public_doc(
        tmp_path, "nofr.md",
        "---\n"
        "diataxis: how-to\n"
        "last-reviewed: 2026-04-18\n"
        "---\n\n# X\n",
    )
    findings = check_docs.plugin_docs_frontmatter(tmp_path, verbose=False)
    hits = [f for f in findings if "'freshness'" in f.message]
    assert len(hits) == 1


def test_bad_freshness_value_is_flagged(tmp_path: Path) -> None:
    _write_public_doc(
        tmp_path, "badfr.md",
        "---\n"
        "diataxis: how-to\n"
        "freshness: evergreen\n"
        "last-reviewed: 2026-04-18\n"
        "---\n\n# X\n",
    )
    findings = check_docs.plugin_docs_frontmatter(tmp_path, verbose=False)
    hits = [f for f in findings if "freshness: evergreen" in f.message]
    assert len(hits) == 1


def test_non_frozen_missing_last_reviewed_is_flagged(tmp_path: Path) -> None:
    _write_public_doc(
        tmp_path, "nolr.md",
        "---\n"
        "diataxis: how-to\n"
        "freshness: release-bound\n"
        "---\n\n# X\n",
    )
    findings = check_docs.plugin_docs_frontmatter(tmp_path, verbose=False)
    hits = [f for f in findings if "last-reviewed" in f.message and "required" in f.message]
    assert len(hits) == 1


def test_bad_last_reviewed_date_is_flagged(tmp_path: Path) -> None:
    _write_public_doc(
        tmp_path, "baddate.md",
        "---\n"
        "diataxis: how-to\n"
        "freshness: release-bound\n"
        "last-reviewed: April 18 2026\n"
        "---\n\n# X\n",
    )
    findings = check_docs.plugin_docs_frontmatter(tmp_path, verbose=False)
    hits = [f for f in findings if "ISO date" in f.message and "last-reviewed" in f.message]
    assert len(hits) == 1


def test_event_frozen_with_last_reviewed_is_flagged(tmp_path: Path) -> None:
    _write_public_doc(
        tmp_path, "frozen.md",
        "---\n"
        "diataxis: explanation\n"
        "freshness: event-frozen\n"
        "last-reviewed: 2026-04-18\n"
        "---\n\n# Frozen\n",
    )
    findings = check_docs.plugin_docs_frontmatter(tmp_path, verbose=False)
    hits = [
        f for f in findings
        if "event-frozen" in f.message and "must be absent" in f.message
    ]
    assert len(hits) == 1


def test_event_frozen_without_last_reviewed_passes(tmp_path: Path) -> None:
    _write_public_doc(
        tmp_path, "frozen.md",
        "---\n"
        "diataxis: explanation\n"
        "freshness: event-frozen\n"
        "---\n\n# Frozen\n",
    )
    findings = check_docs.plugin_docs_frontmatter(tmp_path, verbose=False)
    warnings = [f for f in findings if f.severity == "warning"]
    assert not warnings


def test_bad_review_by_date_is_flagged(tmp_path: Path) -> None:
    _write_public_doc(
        tmp_path, "badrb.md",
        "---\n"
        "diataxis: how-to\n"
        "freshness: release-bound\n"
        "last-reviewed: 2026-04-18\n"
        "review-by: next quarter\n"
        "---\n\n# X\n",
    )
    findings = check_docs.plugin_docs_frontmatter(tmp_path, verbose=False)
    hits = [f for f in findings if "review-by" in f.message and "ISO date" in f.message]
    assert len(hits) == 1


def test_unknown_fields_are_allowed(tmp_path: Path) -> None:
    """Forward-compat: unrecognized keys must not trigger findings."""
    _write_public_doc(
        tmp_path, "extra.md",
        "---\n"
        "diataxis: how-to\n"
        "freshness: release-bound\n"
        "last-reviewed: 2026-04-18\n"
        "description: \"Some extra key\"\n"
        "recommended: true\n"
        "---\n\n# X\n",
    )
    findings = check_docs.plugin_docs_frontmatter(tmp_path, verbose=False)
    warnings = [f for f in findings if f.severity == "warning"]
    assert not warnings, f"unexpected warnings: {[f.message for f in warnings]}"


def test_missing_public_docs_degrades_gracefully(tmp_path: Path) -> None:
    findings = check_docs.plugin_docs_frontmatter(tmp_path, verbose=False)
    assert len(findings) == 1
    assert findings[0].severity == "info"
    assert "not found" in findings[0].message


def test_walks_subdirectories(tmp_path: Path) -> None:
    """Nested .md files (e.g., how-to/, reference/, concepts/) must be checked."""
    _write_public_doc(
        tmp_path, "how-to/nested.md",
        "# Missing frontmatter\n",
    )
    findings = check_docs.plugin_docs_frontmatter(tmp_path, verbose=False)
    warnings = [f for f in findings if f.severity == "warning"]
    assert len(warnings) == 1
    assert "nested.md" in warnings[0].path


# ---------------------------------------------------------------------------
# plugin_script_citation_drift
# ---------------------------------------------------------------------------


def _write_script(root: Path, rel_path: str, body: str) -> Path:
    target = root / ".claude" / "skills" / "scripts" / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    return target


def test_plugin_script_citation_drift_is_registered() -> None:
    assert "script-citation-drift" in check_docs._PLUGINS
    desc, func = check_docs._PLUGINS["script-citation-drift"]
    assert callable(func)
    assert "script" in desc.lower()


def test_script_citation_without_sibling_warns(tmp_path: Path) -> None:
    script = _write_script(
        tmp_path,
        "sample.py",
        '"""sample"""\n# See plan-000123 for rationale.\n',
    )
    findings = check_docs.plugin_script_citation_drift(tmp_path, verbose=False)
    warnings = [f for f in findings if f.severity == "warning"]
    assert len(warnings) == 1
    assert warnings[0].path == str(script)
    assert "sample-rationale.md" in warnings[0].message


def test_script_citation_with_sibling_and_pointer_passes(tmp_path: Path) -> None:
    _write_script(
        tmp_path,
        "sample.py",
        '"""sample"""\n\n'
        "# Rationale for design choices and historical context: see "
        "sample-rationale.md in this directory.\n"
        "# See plan-000123 for rationale.\n",
    )
    (tmp_path / ".claude" / "skills" / "scripts" / "sample-rationale.md").write_text(
        "# sample rationale\n\n- **plan-000123**: Summary.\n",
        encoding="utf-8",
    )
    findings = check_docs.plugin_script_citation_drift(tmp_path, verbose=False)
    warnings = [f for f in findings if f.severity == "warning"]
    assert not warnings


def test_script_citation_sibling_without_pointer_warns(tmp_path: Path) -> None:
    script = _write_script(
        tmp_path,
        "sample.py",
        '"""sample"""\n# See plan-000123 for rationale.\n',
    )
    script.with_name("sample-rationale.md").write_text(
        "# sample rationale\n\n- **plan-000123**: Summary.\n",
        encoding="utf-8",
    )
    findings = check_docs.plugin_script_citation_drift(tmp_path, verbose=False)
    warnings = [f for f in findings if f.severity == "warning"]
    assert len(warnings) == 1
    assert "missing the standard module-level pointer" in warnings[0].message


def test_script_citation_transition_anchor_is_exempt(tmp_path: Path) -> None:
    _write_script(
        tmp_path,
        "sample.py",
        '"""sample"""\n# TRANSITION plan-000123\nVALUE = "x"\n',
    )
    findings = check_docs.plugin_script_citation_drift(tmp_path, verbose=False)
    warnings = [f for f in findings if f.severity == "warning"]
    assert not warnings


def test_script_citation_skips_tests_and_priv(tmp_path: Path) -> None:
    _write_script(tmp_path, "tests/test_sample.py", "# See plan-000123\n")
    _write_script(tmp_path, "priv/migration.py", "# See plan-000123\n")
    _write_script(tmp_path, "test_root_helper.py", "# See plan-000123\n")
    findings = check_docs.plugin_script_citation_drift(tmp_path, verbose=False)
    warnings = [f for f in findings if f.severity == "warning"]
    assert not warnings


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


def test_cli_dispatch_runs_both_plugins_by_name(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    """Invoke check_docs.main() with --plugins listing both new plugins.

    The clean fixture must exit 0 (after the generator stub aligns the
    regen-drift sub-check) and the drift fixture must exit 1.
    """
    # Clean fixture: stub so drift check reports "in sync".
    _stub_generator_matching(monkeypatch, CLEAN)
    monkeypatch.setattr(
        sys, "argv",
        [
            "check_docs.py",
            "--root", str(CLEAN),
            "--plugins", "harness-reference-coverage,lifecycle-fact-uniqueness",
        ],
    )
    rc_clean = check_docs.main()
    capsys.readouterr()
    assert rc_clean == 0, f"clean fixture expected exit 0, got {rc_clean}"

    # Drift fixture: force divergence so all drift classes fire.
    _stub_generator_diverging(monkeypatch)
    monkeypatch.setattr(
        sys, "argv",
        [
            "check_docs.py",
            "--root", str(DRIFT),
            "--plugins", "harness-reference-coverage,lifecycle-fact-uniqueness",
        ],
    )
    rc_drift = check_docs.main()
    capsys.readouterr()
    assert rc_drift == 1, f"drift fixture expected exit 1, got {rc_drift}"
