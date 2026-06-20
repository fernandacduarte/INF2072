#!/usr/bin/env python3
# designer: When a consumer (pre-skill help stage, /help Layer 2,
#   generate_call_graph.py, check_docs.py) needs the designer-facing
#   narrative for a skill, I'm the single code path that reads the
#   SKILL-quickguide.md sibling file and returns its body with
#   YAML frontmatter stripped -- so the file location lives in exactly
#   one place and future layout moves are a one-site change.
"""
load_quickguide.py -- Shared loader for SKILL-quickguide.md sibling files.

Invocation: library
Lifecycle: active

Canonical loader for the designer-facing Quick Guide narrative carried by
each user-invocable skill. The sibling file pattern documented in
.claude/references/general/harness-governance.md `Sibling SKILL-quickguide.md pattern`
keeps the Quick Guide out of the agent-executional SKILL.md body; this
helper is the single file-path source of truth for read consumers.

Usage
-----
    from pathlib import Path
    from load_quickguide import load_quickguide

    body = load_quickguide(Path(".claude/skills/research"))
    if body is None:
        # sibling missing -- caller decides fallback
        ...
"""

# Rationale for design choices and historical context: see load_quickguide-rationale.md in this directory.
from __future__ import annotations

from pathlib import Path

_QUICKGUIDE_FILENAME = "SKILL-quickguide.md"


def load_quickguide(skill_dir: Path) -> str | None:
    """Return the Quick Guide body for the given skill directory.

    Reads ``<skill_dir>/SKILL-quickguide.md`` when present. Returns the
    file contents with YAML frontmatter stripped, or ``None`` when the
    sibling is missing (or the directory does not exist). Never falls
    back to SKILL.md -- siblings are the single source.

    Emits no warnings; missing-sibling handling is the caller's
    responsibility.
    """
    sibling = skill_dir / _QUICKGUIDE_FILENAME
    try:
        text = sibling.read_text(encoding="utf-8-sig", errors="replace")
    except (OSError, FileNotFoundError):
        return None

    return _strip_frontmatter(text).strip("\n")


def _strip_frontmatter(text: str) -> str:
    """Strip a leading ``---\\n...\\n---\\n`` YAML frontmatter block, if any.

    Returns the text unchanged when no frontmatter delimiter pair is found
    at the start. Handles both LF and CRLF line endings.
    """
    if not text.startswith("---"):
        return text
    # Find the closing delimiter. Accept LF or CRLF after the opener.
    # Skip the opening '---' then look for a line that is exactly '---'.
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return text
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            return "".join(lines[idx + 1 :])
    # Unterminated frontmatter -- return unchanged rather than silently
    # eating the whole file.
    return text
