---
designer_description: "When you want every script in the harness to declare who invokes it and where it sits in its lifecycle, I'm the reference that pins down the two-line docstring header, the enum values, and the extraction grammar so the harness reference table can group scripts by role without guesswork."
---

# GENERAL - SCRIPT HEADER CONVENTION

Every Python script in the SEJA harness carries a two-line docstring header declaring its invocation role and lifecycle status. `generate_harness_reference.py` parses these headers and renders them into the harness-reference table, grouping scripts by role. Motivation (research-000455): role and lifecycle were previously implicit, obscuring which scripts are user CLIs vs. skill helpers vs. libraries, and which are active vs. one-shot vs. deprecated.

## The two mandatory fields

After the first-line purpose and a blank line, every module docstring must contain:

- `Invocation:` -- comma-separated roles (enum below). Declares who calls the script.
- `Lifecycle:` -- single value (enum below). Declares lifecycle status.

Field names are case-sensitive. Unknown values fail the generator's `--check`, which fails `run_preflight_fast.py`.

## Invocation enum (comma-separated, one or more)

| Value | Meaning |
|-------|---------|
| `user-cli` | Invoked directly by the human operator on the command line. |
| `skill-invoked` | Called by a skill (`.claude/skills/*/SKILL.md`) as part of its workflow. |
| `agent-invoked` | Called by a subagent prompt (`.claude/agents/*.md`). |
| `hook-ci` | Run by a lifecycle hook (pre-skill, post-skill, pre-commit) or a CI workflow. |
| `library` | Imported as a Python module by other scripts; not executable as a standalone entry point. |
| `test` | A test file, typically under `_tests/` or next to the code it exercises. |

A script may carry more than one role (e.g., `apply_marker.py` is used by both humans and skills); values are comma-separated.

## Lifecycle enum (single value)

| Value | Meaning |
|-------|---------|
| `active` | In current use; expected to keep working and be maintained. |
| `one-shot` | A migration or backfill script that ran once; kept for reproducibility but not expected to run again. |
| `deprecated` | Superseded; scheduled for removal. Still works but new code must not call it. |

## Extraction grammar

The generator runs `ast.get_docstring(module)` and scans for both fields.

- Regex (per field, case-sensitive, anywhere after the first line): `^(Invocation|Lifecycle):\s*(.+)$`
- First match per field wins; values stripped of whitespace.
- `Invocation:` is split on `,`; each token stripped and lowercased before enum validation.
- `Lifecycle:` is stripped and lowercased before enum validation.

Missing field or off-enum value -> `--check` exits non-zero and names the offender.

## Examples

Single-role (`count_loc.py`):

```python
"""Count lines of code in the harness.

Invocation: user-cli
Lifecycle: active
"""
```
Multi-role (`apply_marker.py`):

```python
"""Append structured markers to Human(markers) files.

Invocation: user-cli, skill-invoked
Lifecycle: active
"""
```

## Upgrade-compatibility note

Consumer-side scripts under `.claude/skills/scripts/` outside harness core must carry this header after upgrading past the release that introduced the preflight gate. If `run_preflight_fast.py` fails with `harness-reference` errors, annotate offenders (two lines per script) or pin to the pre-tightening tag while backfilling. The generator names each offender, so the touch list is auto-discoverable.
