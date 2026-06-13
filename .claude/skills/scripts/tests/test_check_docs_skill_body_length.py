"""Tests for the ``skill-body-length`` plugin in ``check_docs.py``.

Covers the six scenarios enumerated in plan-000458 step 2:

1. Clean pass -- ``light`` tier at 140 body lines.
2. Length warning -- ``light`` tier at 160 body lines.
3. Inlined-template warning -- ``standard`` tier at 280 body lines with one
   25-line code fence.
4. Rationale-citation warning -- ``heavy`` tier at 480 body lines with two
   ``See advisory-NNNNNN`` references in distinct numbered-step bodies.
5. Waiver respect -- ``standard`` tier at 320 body lines with a body-level
   ``<!-- skill-length-waiver: ... -->`` comment AND a 22-line inlined code
   fence; length WARN suppressed, inlined-template WARN still fires.
6. Same-as-Mode stubs -- any tier with 3 ``Same as Mode`` occurrences.

Each fixture builds a synthetic SKILL.md under ``tmp_path/.claude/skills/
<name>/SKILL.md``, invokes ``plugin_skill_body_length`` directly, and
asserts on the set of findings filtered down to the target SKILL.md.
"""
from __future__ import annotations

from pathlib import Path

import pytest

import check_docs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


# Post-plan-000466: Quick Guide narrative lives in a SKILL-quickguide.md
# sibling file. SKILL.md body starts with the pointer blockquote, then the
# Arguments table, then the agent-facing body.
FRONTMATTER_TEMPLATE = """\
---
name: {name}
description: "Synthetic fixture for skill-body-length plugin tests."
argument-hint: "[none]"
compatibility: "test"
metadata:
  context_budget: {tier}
  eager_references: []
  references: []
---

> Overview: see [./SKILL-quickguide.md](./SKILL-quickguide.md)

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| (none)   | No       | placeholder |

"""


def _write_skill(
    tmp_path: Path,
    name: str,
    tier: str,
    body_lines: list[str],
) -> Path:
    """Write a synthetic SKILL.md under ``tmp_path`` and return its path.

    ``body_lines`` are written verbatim after the Arguments blank-line
    terminator; the caller is responsible for ensuring the first line is a
    Markdown heading (``# ...``) so the body-start locator picks it up.
    """
    skill_dir = tmp_path / ".claude" / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_path = skill_dir / "SKILL.md"
    text = FRONTMATTER_TEMPLATE.format(name=name, tier=tier) + "\n".join(body_lines) + "\n"
    skill_path.write_text(text, encoding="utf-8")
    return skill_path


def _build_body(
    heading: str,
    filler_count: int,
    extras_before: list[str] | None = None,
    extras_after: list[str] | None = None,
) -> list[str]:
    """Build a body of exactly ``1 + len(extras_before) + filler_count +
    len(extras_after)`` lines. The first line is always ``heading``.
    """
    body = [heading]
    if extras_before:
        body.extend(extras_before)
    for i in range(filler_count):
        body.append(f"- item {i + 1}")
    if extras_after:
        body.extend(extras_after)
    return body


def _findings_for(findings: list[check_docs.Finding], skill_path: Path) -> list[check_docs.Finding]:
    """Return only findings whose path matches ``skill_path``."""
    target = str(skill_path)
    return [f for f in findings if f.path == target]


def _warnings(findings: list[check_docs.Finding]) -> list[check_docs.Finding]:
    return [f for f in findings if f.severity == "warning"]


def _run(tmp_path: Path) -> list[check_docs.Finding]:
    """Invoke the plugin against ``tmp_path`` and return all findings."""
    return check_docs.plugin_skill_body_length(tmp_path, verbose=False)


# ---------------------------------------------------------------------------
# Scenario 1 -- Clean pass at light tier with 140 body lines
# ---------------------------------------------------------------------------


def test_light_tier_at_140_body_lines_passes(tmp_path: Path) -> None:
    """``light`` tier threshold is 150; 140 lines must not warn."""
    # 1 heading + 139 fillers = 140 body lines.
    body = _build_body("# Light Skill", filler_count=139)
    assert len(body) == 140
    skill_path = _write_skill(tmp_path, "light-clean", "light", body)

    findings = _findings_for(_run(tmp_path), skill_path)
    warnings = _warnings(findings)
    assert warnings == [], (
        f"expected no warnings for 140-line light-tier body; got "
        f"{[w.message for w in warnings]}"
    )


# ---------------------------------------------------------------------------
# Scenario 2 -- Length warning at light tier with 160 body lines
# ---------------------------------------------------------------------------


def test_light_tier_at_160_body_lines_warns(tmp_path: Path) -> None:
    """``light`` tier threshold is 150; 160 lines emits exactly one
    length warning referencing ``light tier threshold (150)``."""
    body = _build_body("# Light Skill", filler_count=159)
    assert len(body) == 160
    skill_path = _write_skill(tmp_path, "light-long", "light", body)

    findings = _findings_for(_run(tmp_path), skill_path)
    warnings = _warnings(findings)
    assert len(warnings) == 1, (
        f"expected exactly 1 warning; got {[w.message for w in warnings]}"
    )
    assert "light tier threshold (150)" in warnings[0].message


# ---------------------------------------------------------------------------
# Scenario 3 -- Inlined-template warning at standard tier with 25-line fence
# ---------------------------------------------------------------------------


def test_standard_tier_280_lines_with_25_line_fence_warns_inlined_only(tmp_path: Path) -> None:
    """``standard`` tier threshold is 300; 280 lines must not trigger the
    length check, but the 25-line code fence must emit an
    inlined-code-fenced-block warning."""
    # Layout: heading (1) + 127 fillers + fence-open (1) + 25 inside + fence-close (1)
    # + 125 fillers = 280 body lines. 25 lines strictly inside the fence.
    fence_interior = [f"code_line_{i}" for i in range(25)]
    fence_block = ["```python"] + fence_interior + ["```"]
    body = [
        "# Standard Skill",
    ]
    body.extend(f"- before {i}" for i in range(127))
    body.extend(fence_block)
    body.extend(f"- after {i}" for i in range(125))
    assert len(body) == 280, f"expected 280 body lines, got {len(body)}"
    skill_path = _write_skill(tmp_path, "standard-fence", "standard", body)

    findings = _findings_for(_run(tmp_path), skill_path)
    warnings = _warnings(findings)
    assert len(warnings) == 1, (
        f"expected exactly 1 warning; got {[w.message for w in warnings]}"
    )
    assert "inlined code-fenced block of 25 lines" in warnings[0].message
    assert "tier threshold" not in warnings[0].message


# ---------------------------------------------------------------------------
# Scenario 4 -- Two rationale citations in distinct numbered-step bodies
# ---------------------------------------------------------------------------


def test_heavy_tier_480_lines_with_two_citations_warns_twice(tmp_path: Path) -> None:
    """``heavy`` tier threshold is 500; 480 lines stays under length. Two
    ``See advisory-000001`` lines in distinct ``### Step`` bodies emit
    exactly two ``rationale citation in step body`` warnings."""
    body: list[str] = ["# Heavy Skill"]
    # Filler before step 1.
    body.extend(f"- intro {i}" for i in range(100))
    # Step 1 body with one citation.
    body.append("### Step 1: do the first thing")
    body.append("See advisory-000001 for rationale.")
    body.extend(f"- s1 detail {i}" for i in range(100))
    # Step 2 body with one citation.
    body.append("### Step 2: do the second thing")
    body.append("See advisory-000002 for rationale.")
    body.extend(f"- s2 detail {i}" for i in range(100))
    # Closing filler.
    body.extend(f"- outro {i}" for i in range(175))
    assert len(body) == 480, f"expected 480 body lines, got {len(body)}"
    skill_path = _write_skill(tmp_path, "heavy-citations", "heavy", body)

    findings = _findings_for(_run(tmp_path), skill_path)
    warnings = _warnings(findings)
    citation_warnings = [w for w in warnings if "rationale citation in step body" in w.message]
    assert len(citation_warnings) == 2, (
        f"expected exactly 2 rationale-citation warnings; got "
        f"{[w.message for w in warnings]}"
    )
    # No length warning at 480 body lines under the heavy ceiling (500).
    length_warnings = [w for w in warnings if "tier threshold" in w.message]
    assert length_warnings == [], (
        f"did not expect a length warning at 480 lines on heavy tier; got "
        f"{[w.message for w in length_warnings]}"
    )


# ---------------------------------------------------------------------------
# Scenario 5 -- Waiver suppresses length WARN but not inlined-template WARN
# ---------------------------------------------------------------------------


def test_waiver_suppresses_length_but_not_inlined_template(tmp_path: Path) -> None:
    """320 body lines on standard tier with a body-level waiver comment
    AND a 22-line code fence: the length warning is suppressed, the
    inlined-template warning still fires."""
    # Layout: heading (1) + waiver (1) + 145 fillers + fence-open (1)
    # + 22 inside + fence-close (1) + 149 fillers = 320 body lines.
    # 22 strictly inside the fence -> above the 20-line threshold.
    fence_interior = [f"code_line_{i}" for i in range(22)]
    fence_block = ["```"] + fence_interior + ["```"]
    body: list[str] = ["# Standard Skill"]
    body.append("<!-- skill-length-waiver: load-bearing telemetry spec -->")
    body.extend(f"- before {i}" for i in range(145))
    body.extend(fence_block)
    body.extend(f"- after {i}" for i in range(149))
    assert len(body) == 320, f"expected 320 body lines, got {len(body)}"
    skill_path = _write_skill(tmp_path, "standard-waived", "standard", body)

    findings = _findings_for(_run(tmp_path), skill_path)
    warnings = _warnings(findings)
    assert len(warnings) == 1, (
        f"expected exactly 1 warning (waiver suppresses length); got "
        f"{[w.message for w in warnings]}"
    )
    assert "inlined code-fenced block of 22 lines" in warnings[0].message
    assert "standard tier threshold" not in warnings[0].message


# ---------------------------------------------------------------------------
# Scenario 6 -- Three ``Same as Mode`` stubs emit one file-level warning
# ---------------------------------------------------------------------------


def test_three_same_as_mode_stubs_emit_one_file_level_warning(tmp_path: Path) -> None:
    """The ``Same as Mode`` detector emits a single summary warning when the
    count exceeds the tolerance (2). The warning reports the count (3) and
    names the drift signal, not one warning per line."""
    body: list[str] = ["# Stub Skill"]
    body.append("Intro line.")
    body.append("- Same as Mode 1, step 3")
    body.extend(f"- filler {i}" for i in range(5))
    body.append("- same as mode 2, step 4")
    body.extend(f"- filler {i}" for i in range(5))
    body.append("- Same as Mode 1, step 7")
    body.extend(f"- tail {i}" for i in range(5))
    skill_path = _write_skill(tmp_path, "stubs-skill", "standard", body)

    findings = _findings_for(_run(tmp_path), skill_path)
    warnings = _warnings(findings)
    stub_warnings = [w for w in warnings if "Same as Mode" in w.message]
    assert len(stub_warnings) == 1, (
        f"expected exactly one file-level Same-as-Mode warning; got "
        f"{[w.message for w in warnings]}"
    )
    assert "\"Same as Mode\" stubs detected" in stub_warnings[0].message
    assert "3" in stub_warnings[0].message


# ---------------------------------------------------------------------------
# Plugin registration sanity check (parity with other test_check_docs_* files)
# ---------------------------------------------------------------------------


def test_plugin_skill_body_length_is_registered() -> None:
    assert "skill-body-length" in check_docs._PLUGINS
    desc, func = check_docs._PLUGINS["skill-body-length"]
    assert callable(func)
    assert "skill" in desc.lower() or "body" in desc.lower()
