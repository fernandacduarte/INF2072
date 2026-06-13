---
name: design-mode2-internal
description: "Inlined worker for /design Mode 2 (From Spec File). Not user-invocable."
compatibility: "Designed for Claude Code with the SEJA harness"
metadata:
  internal: true
  category: internal
  version: 1.0.0
---

> This is an inlined worker; execute these instructions as part of the caller's flow. The wrapper at `.claude/skills/design/SKILL.md` has already run the Detection Logic; execute the steps below.
>
> **Field Classification and Versioning**: Both sections are in the calling wrapper SKILL.md (`.claude/skills/design/SKILL.md`) -- they are loaded into context before this internal executes.

### Mode 2: From Spec File

1. **Locate spec file**: Use provided path, else look in `specs/`.
2. **Read and parse the spec file**: Same parsing rules as Mode 1.
3. **Version check**: Compare against `questionnaire_version`. If the spec file's version is less than 7, reject with: "Your spec file is version `<N>`; post-plan-447 /design uses v7 with split `stack-only` / `design-intent-only` sections. Run `/design --generate-spec` to regenerate, or provide a v7 spec. Abort." This prevents double-scaffolding (Section 1 already in `conventions.md` from `/seja-setup` + stack fields re-answered in the legacy spec).
4. **Validate all at once**: Report provided, missing required, missing-with-default, and ambiguous fields.
5. **Targeted Q&A**: Ask for missing required fields. Enforce mandatory conceptual design.
6. **Offer detailed sections**: Present Sections 2-11 (conceptual-design through security-checklists) as a numbered multi-select list.

7-10, 12. **Delegate to questionnaire internal**: Read `.claude/skills/_internal/design/questionnaire/SKILL.md` and execute steps 7 (Instantiate templates), 8 (Amend CLAUDE.md), 9 (Rules generation), 10 (Smoke-test infrastructure), and 12 (Secrets check) from that file, substituting the spec-file answers for questionnaire answers.

11. **Preserve spec**: Copy to `specs/project-spec-YYYY-MM-DD HH.MM UTC.md`.
