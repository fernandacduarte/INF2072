"""Tests for migrate_qa_logs_to_parent_dirs.classify()."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from migrate_qa_logs_to_parent_dirs import classify


def test_standalone_6digit():
    action, _ = classify("qa-000350-priv-public-separation-full-session.md")
    assert action == "standalone"


def test_standalone_4digit_txt():
    action, _ = classify("qa-0001-codex-creating-codex-codebase.txt")
    assert action == "standalone"


def test_plan_prefix():
    action, dest = classify("plan-000278-qa-concepts-sign-system-lifecycle.md")
    assert action == "move"
    assert dest is not None
    assert dest.name == "plans"


def test_implement_prefix():
    action, dest = classify("implement-000187-qa-revise-framework-documentation.md")
    assert action == "move"
    assert dest is not None
    assert dest.name == "plans"


def test_advisory_prefix():
    action, dest = classify("advisory-000366-qa-document-auto-detect.md")
    assert action == "move"
    assert dest is not None
    assert dest.name == "advisory-logs"


def test_check_prefix():
    action, dest = classify("check-000179-qa-preflight-results.md")
    assert action == "move"
    assert dest is not None
    assert dest.name == "check-logs"


def test_roadmap_prefix():
    action, dest = classify("roadmap-000276-qa-roadmap-review.md")
    assert action == "move"
    assert dest is not None
    assert dest.name == "roadmaps"


def test_noid_document_qa():
    action, _ = classify("document-qa-framework-changelog-2-10-0.md")
    assert action == "leave"


def test_unknown_prefix():
    action, _ = classify("foobar-000999-qa-something.md")
    assert action == "unknown-prefix"


def test_unrecognized_shape():
    action, _ = classify("random-file.md")
    assert action == "unknown"


def test_standalone_with_space():
    action, _ = classify("qa-0003-claude-review README.md.txt")
    assert action == "standalone"
