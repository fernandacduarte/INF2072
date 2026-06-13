#!/usr/bin/env python3
# designer: When your project has files where the prose belongs to you but
#   specific markers (STATUS, ESTABLISHED, CHANGELOG_APPEND, DECISION_APPEND)
#   may be agent-written, I'm the shared registry that names those files and
#   the marker patterns they allow -- the single list both the write path
#   (apply_marker.py) and the verifier (check_human_markers_only.py) consult
#   so nothing agent-authored slips into a prose-owned file by accident.
"""
human_markers_registry -- Shared registry for Human (markers) files and allowed marker patterns.

Invocation: library
Lifecycle: active

Imported by apply_marker.py (sole write path) and check_human_markers_only.py (post-skill
verifier). The split into a shared module avoids circular imports and keeps the allowlist
in one place.

All paths in HUMAN_MARKERS_FILES must use forward slashes (repo-relative POSIX paths)
because git diff output uses forward slashes on Windows too.

Empty-allowlist behavior: apply_marker.py refuses all writes when the registry is empty
(an intentional availability constraint -- no files classified means no files to write).
check_human_markers_only.py prints a loud warning and exits 0 when the registry is empty
(the verifier is a no-op with nothing to verify).
"""

# Rationale for design choices and historical context: see human_markers_registry-rationale.md in this directory.
from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Registry of files classified as Human (markers)
# ---------------------------------------------------------------------------

# Registry of files classified as Human (markers). Paths use forward slashes
# (repo-relative POSIX) so that git diff output matches on Windows too.
#
# Both the template/ and project/ paths are registered for each real file: the
# template path is what /design seeds (and what harness-level tests touch);
# the project path is what designer commits exercise via post-skill step 2e.
# apply_marker.py and check_human_markers_only.py perform exact-string matches
# against this list, so both forms must be present.
#
# ux-research-results.md and product-design-as-intended.md are both registered
# via the dual-path pattern (template + project). A future _paths_for(file_stem)
# helper could return both forms automatically; deferred.
HUMAN_MARKERS_FILES: list[str] = [
    ".claude/skills/scripts/tests/fixtures/marker_fixture.md",
    ".claude/references/template/ux-research-results.md",
    "product-design/ux-research-results.md",
    ".claude/references/template/product-design-as-intended.md",
    "product-design/product-design-as-intended.md",
]


# ---------------------------------------------------------------------------
# Allowed marker patterns
# ---------------------------------------------------------------------------

# Each entry defines:
#   line_regex: full-line pattern the marker must match
#   allowed_values: permitted values for the marker value field (None = any value)
#   allowed_transitions: {from_value: [to_values]} dict for state-machine validation
#                        (None = no transition validation)
#
# CHANGELOG_APPEND uses [^<>\n]{1,200} rather than .{1,200} to reject HTML comment
# smuggling: a --note value containing <!-- or --> could otherwise inject a new
# marker on the next line.

ALLOWED_MARKERS: dict[str, dict] = {
    "STATUS": {
        # Accepts both the new lowercase multi-value scheme (proposed | implemented |
        # established | superseded), AND the legacy
        # uppercase single-value scheme (IMPLEMENTED) from pre-2.8.0 for backward
        # compatibility with existing markers in design-intent files. Follow-up plans
        # that reclassify real files should use the new lowercase scheme.
        "line_regex": (
            r"<!-- STATUS: "
            r"(proposed|implemented|established|superseded|IMPLEMENTED)"
            r"(?: \| (?:plan-\d{6}|manual))?"
            r"(?: \| \d{4}-\d{2}-\d{2})?"
            r" -->"
        ),
        "allowed_values": [
            "proposed",
            "implemented",
            "established",
            "superseded",
            "IMPLEMENTED",
        ],
        "allowed_transitions": {
            "proposed": ["implemented", "superseded"],
            "implemented": ["established", "superseded"],
            "established": ["superseded"],
            "superseded": [],
            # Legacy uppercase scheme: no transitions defined (one-shot marker).
            "IMPLEMENTED": [],
        },
    },
    "ESTABLISHED": {
        # Legacy stamp, retained for migration from the current IMPLEMENTED/ESTABLISHED
        # scheme. Stamp is immutable once written; no value/transition validation.
        "line_regex": (
            r"<!-- ESTABLISHED: plan-\d{6} \| \d{4}-\d{2}-\d{2}"
            r"(?: \| v\d+\.\d+\.\d+)? -->"
        ),
        "allowed_values": None,
        "allowed_transitions": None,
    },
    "INCORPORATED": {
        "line_regex": r"<!-- INCORPORATED: plan-\d{6} \| \d{4}-\d{2}-\d{2} -->",
        "allowed_values": None,
        "allowed_transitions": None,
    },
    "CHANGELOG_APPEND": {
        "line_regex": (
            r"\d{4}-\d{2}-\d{2} \| [A-Z]+-[A-Z]+-\d{3,} \| "
            r"(added|revised|revoked|superseded) \| "
            r"(plan-\d{6}|-) \| "
            r"[^<>\n]{1,200}"
        ),
        "allowed_values": None,
        "allowed_transitions": None,
    },
    "DECISION_APPEND": {
        # Appends a new ### D-NNN: section to the ## Decisions heading.
        # The value field carries the full DRR-shaped entry text.
        # line_regex validates the heading line of the appended entry.
        "line_regex": r"### D-\d{3}: .{1,200}",
        "allowed_values": None,
        "allowed_transitions": None,
    },
}


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def normalize_path(path: str | Path) -> str:
    """Normalize a path to repo-relative forward-slash form.

    Does NOT resolve symlinks -- callers that need symlink resolution (apply_marker.py)
    must call Path.resolve() themselves before passing the result here.
    """
    return str(Path(path)).replace("\\", "/")


def is_human_markers_file(path: str | Path) -> bool:
    """Return True if the given path matches an entry in HUMAN_MARKERS_FILES.

    Path comparison is exact-string after normalization. Callers should resolve
    symlinks and make the path repo-relative before calling this.
    """
    canonical = normalize_path(path)
    return canonical in HUMAN_MARKERS_FILES
