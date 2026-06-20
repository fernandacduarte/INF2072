---
name: plan-standard-internal
description: "Inlined worker for /plan standard single-plan mode. Not user-invocable."
compatibility: "Designed for Claude Code with the SEJA harness"
metadata:
  internal: true
  category: internal
  version: 1.0.0
---

> This is an inlined worker; execute these instructions as part of the caller's flow. The wrapper at .claude/skills/plan/SKILL.md has already run C1 (pre-skill) and the Design Guard; execute the steps below and invoke C6 (post-skill) at the end per the mode's own step 8. Note: when this internal is invoked inline from `_internal/plan/roadmap/SKILL.md` (Mode 1 step 9 or Mode 2 step 8), the caller instructs per-item execution to skip steps 7 and 8 -- the roadmap run owns the user prompt and the commit.

This mode is the reference prose -- other modes delta off of its shape. Steps 1, 3 (reserve-ID + header), 5 (Review Depth), 7 (decision-point phrasing), and 8 (post-skill) reuse C1, C2+C3, C5, C4, and C6 respectively; the local prose below adds only the single-plan-specific content.

1. Apply C1 (pre-skill).

2. **Load references on demand** as needed:

   | When | Load |
   |---|---|
   | `--framing metacomm` | `project/product-design-as-intended.md` |
   | Plan touches backend/frontend/testing/i18n files | `project/standards.md` |
   | Plan involves auth, validation, or sensitive data | `project/security-checklists.md` |
   | Plan involves UX flows or visual design | `project/design-standards.md` |
   | Before Phase 1 review | `general/review-perspectives.md` |
   | Before writing the review log | `general/review-log-template.md` |

3. Create a structured, self-contained plan with these sections (header per C3; `<depth>` set in step 5):
   - If default framing: *user brief*, *agent interpretation*, *files* -- per `general/report-conventions.md`.
   - If metacomm framing: *designer's metacommunication message* (the brief verbatim), *agent interpretation*, *files*.
   - *agent interpretation* covers three elements (four when `source:` is present):
     1. **Problem**: one sentence describing what problem this plan solves.
     2. **Approach**: the chosen approach and why it was selected.
     3. **Alternatives rejected** (Standard/Deep only; omit for Light): key alternatives considered and rejected.
     4. **Selection rationale** (Standard/Deep only; omit for Light; omit when no `source: <type>-<id>` header): bullet list of source recommendations with disposition. For each recommendation in the source artifact: `Included: R<n> -- <one-line reason>` or `Excluded: R<n> -- <one-line reason for deferral or rejection>`. When the source has no numbered recommendations, summarize the selection as a prose sentence.
   - If prefix is FIX (brief describes an error or bug), also include: *error log* (optional; if extensive, summarize and prepend "summarized error log:", and replace the inline log in the user brief with "<error log> (see summary below)"); *root cause*: diagnostics of the problem.
   - *best practices*: used in the plan.
   - *design decisions* (Standard/Deep only; omit for Light):
     - **User-visible impact**: what changes from the user's perspective (one paragraph).
     - **Trade-offs accepted**: what was gained, what was given up.
     - **Metacommunication impact** (when the plan modifies user-facing communication -- error messages, help, UI copy, CLI output, docs): what the system will now communicate differently. Use I/you phrasing per `shared-definitions.md`. Include regardless of `--framing metacomm`.
   - *steps*: structured step list -- step format and decomposition guidelines: see `.claude/references/template/plan-step.md`.
   - *review log*: if applicable.
   - *outcomes*: expected outcomes.
   - *smoke*: `true` if any step creates or modifies API route files or frontend page/component files; `false` otherwise. Consumed by `/implement` to decide whether to run `/check smoke api`.
   - *reflection* (optional, appended post-execution): a `## Reflection` section of dated bullets appended by post-skill's reflection loop (step 11b). Absent by default; the section may be created on first use.

4. Save the plan. If not overwriting, proceed without asking for authorization.

4b. **Coverage check (advisory)**: if `product-design/product-design-as-intended.md` contains REQ markers (`<!-- REQ-*-NNN -->`), run `python .claude/skills/design/check_plan_coverage.py --mode advisory` and include the coverage summary in the plan after the steps. Skip silently if no REQ markers exist.

5. **Review the plan** using a complexity-gated, two-phase process. Use `general/review-log-template.md` for the review log format.

   **Step metadata validation (before perspective review):**
   - Every step has all required fields (Files, References, Interface, Verify, Tests, checkbox). Optional fields (Depends on, Docs, Traces) may be omitted entirely -- absent Depends on = no dependencies; absent Docs/Traces = not applicable. `Interface:` is required but may be `N/A` -- omitting it entirely is a validation error; populate for dependency-producing steps.
   - Docs and Traces are present-when-relevant. When present, validate: Docs describes specific documentation to update; Traces lists valid REQ-xxx IDs.
   - For non-N/A `Tests:` entries: the description must express an observable behavior ('when X is called with Y, returns Z') rather than a structural assertion ('module exports class Z') or bare test name. Auto mode uses this to write a meaningful failing test before implementation.
   - `Tests: N/A` is appropriate for database migrations, configuration-only steps, pure refactors with pre-existing coverage, and framework/tooling-only steps that produce no business logic.
   - File paths for existing files verified on disk.
   - Dependencies flow forward (no circular, no backwards references).
   - No step touches >5 files (split if so).
   - Each step description is self-contained.

   Fix any issues before proceeding.

   **Complexity gate -- determine review depth:**
   - **Light**: <=6 action steps AND touches <=4 files. Phase 1 only.
   - **Standard**: 7-12 action steps OR touches 5-8 files. Phase 1; Phase 2 eligible.
   - **Deep**: >12 action steps OR touches >8 files OR involves migrations/auth/X-scope. Phase 1 + Phase 2 for all Deferred concerns.

   **Depth resolution:** apply Common Step C5 (Review Depth Override).

   **Phase 1 -- Perspective triage and scan (inline, no subagents):**
   Use the two-stage loading protocol (`general/review-perspectives.md` section "Two-Stage Loading"):
   1. Load `general/review-perspectives-index.md` to see all 16 perspectives.
   2. Identify the default shortlist of 3-6 perspectives using the Perspective Shortcuts by Plan Prefix table in `general/review-perspectives.md`.
   3. Optionally add up to 2 more with a one-line justification (e.g., "Added PERF: Step 3 introduces a bulk query not typical for CHORE-O scope").
   4. Load only the selected `review-perspectives/<tag>.md` files.
   Mark perspectives not in the shortlist as N/A in the review log. Scan and record Adopted/Deferred with a one-line concern. If Light, stop here.

   **Phase 2 -- Targeted deep-dives:**
   Trigger only for Deferred perspectives whose concern could cause regression, production incident, or standards violation. For Deep, also trigger for additive-improvement Deferred concerns. Never trigger for cosmetic or out-of-scope concerns.

   **Execution strategy by review depth:**
   - **Standard**: launch the `plan-reviewer` agent (Agent tool, subagent_type=`plan-reviewer`) with plan text, plan file path, depth=`standard`. Agent returns review log + amendments; append to the plan file.
   - **Deep**: launch `plan-reviewer` with depth=`deep`. Agent performs all deep-dives, conflict checks, and iterations autonomously; append output to the plan file.

   **Conflict check:** after each iteration producing Phase 2 recommendations, check for contradictions between perspectives. Resolve per `general/review-perspectives.md` section Resolving Perspective Conflicts. Log in the review log.

   **Iteration and convergence:** if Phase 2 changes the plan:
   1. Append a `### Plan Amendment (iteration N)` section with change + rationale (additive; do not modify existing text).
   2. Update the Steps section in place (only section allowed to change, since it is a living checklist).
   3. Re-evaluate perspectives whose steps were modified, plus any still Deferred.
   4. If all Phase 2 findings are "no change needed," terminate the loop immediately.
   5. Otherwise repeat until all Adopted or Deferred-with-rationale, or 3 iterations reached, or deep-dive budget (6) exhausted.

   **Execution metrics (mandatory):** append the Execution Metrics table (see `general/review-log-template.md`) at the end of the review log.

   Append review results to the plan file. Do not rewrite -- only add review log and amendment sections.

6. Output the plan id.

7. Ask the user via AskUserQuestion what to do next (options phrased per C4):
   - **Implement now** -- commit the plan and run `/implement <id>`. Recommended when the plan has been reviewed and you are ready to proceed in this session. NOT recommended when you want to review offline or share it first.
   - **Commit plan** -- commit as-is; implement later via `/implement <id>`. Recommended when you want to review further, implement in a separate session, or share. NOT recommended when the plan is trivially correct and delay adds no value.
   - **Revise plan** -- stop; the plan is not committed. Recommended when you spotted an issue or want to adjust before committing. NOT recommended when the plan is satisfactory and the revision impulse is perfectionism rather than substance.

8. Based on the user's choice (C6 applies for the /post-skill call):
   - **Implement now**: run /post-skill <id>, then run /implement <id>.
   - **Commit plan**: run /post-skill <id>.
   - **Revise plan**: do not run /post-skill. Wait for instructions.
