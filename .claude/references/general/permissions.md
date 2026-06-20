---
designer_description: "When you want to know which actions SEJA takes without asking and which ones still need your confirmation -- reading files, running git status or tests, writing into the output directory, but never editing marker-managed human files directly -- I'm the reference that codifies those defaults, so skills stay productive without crossing into changes that should involve you."
---

# FRAMEWORK - PERMISSIONS

- Don't ask for confirmation before reading any folder or file in the project codebase.
- Don't ask for confirmation before executing git status, git log, git diff commands.
- Don't ask for confirmation before changing the directory within the project structure.
- Don't ask for confirmation before creating new source files.
- Don't ask for confirmation before appending content to any file in `${OUTPUT_DIR}/**` (see project/conventions.md), including briefs.md.
- Don't ask for confirmation before creating non-executable temporary files.
- Don't ask for confirmation before running backend or frontend tests.
- Don't ask for confirmation before creating, reading, or writing the session scratchpad file (`${SESSION_NOTES_FILE}`).
- Do not use `Edit` or `Write` on files classified as `Human (markers)` in the File Maintainer Classification table (see `.claude/references/general/shared-definitions.md`). Use `python .claude/skills/scripts/apply_marker.py` instead. The `check_human_markers_only.py` verifier will reject non-marker hunks during post-skill commit.
- Ask for clarifications whenever necessary.
