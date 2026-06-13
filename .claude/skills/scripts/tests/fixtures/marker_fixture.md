# Test Fixture -- Human (markers)

<!-- This file exists only for the test suite of apply_marker.py and check_human_markers_only.py.
     It is classified Human (markers) via .claude/skills/scripts/human_markers_registry.py so the
     scripts have a non-empty allowlist to exercise against. Do not modify by hand during normal
     harness work -- tests will rewrite it in a tmp_path copy per test.
-->

## Entries

<!-- STATUS: proposed -->
### R-P-001: Sample persona one

A test persona used to exercise STATUS marker transitions in test_apply_marker.py.

<!-- STATUS: proposed -->
### R-P-002: Sample persona two

A second test persona used for ambiguous-id and multi-entry tests.

<!-- STATUS: proposed -->
### D-001: Sample decision one

A test decision entry used to exercise ESTABLISHED stamp insertion and STATUS transitions
in the proposed -> implemented -> established -> superseded chain.

## Decisions

### D-002: Use markdown for design documents

**Context**: Needed a format for design documents.
**Decision**: Use markdown. Widely supported, version-control friendly.
**Consequences**: All design documents are markdown files.
**Rejected Alternatives**: AsciiDoc, reStructuredText.

## CHANGELOG

2026-04-10 | R-P-001 | added | - | initial entry for fixture
2026-04-10 | R-P-002 | added | - | initial entry for fixture
