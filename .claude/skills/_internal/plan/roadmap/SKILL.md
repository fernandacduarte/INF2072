---
name: plan-roadmap-internal
description: "Inlined worker for /plan --roadmap mode (3 sub-modes: auto, from-spec, blank-spec). Not user-invocable."
compatibility: "Designed for Claude Code with the SEJA harness"
metadata:
  internal: true
  category: internal
  version: 1.0.0
---

> This is an inlined worker; execute these instructions as part of the caller's flow. The wrapper at .claude/skills/plan/SKILL.md has already run C1 (pre-skill) and the Design Guard; execute the steps below and invoke C6 (post-skill) at the end per the mode's own step 8.

> Used when `--roadmap` is present. Skip the standard workflow above.

## Overview

Generates a product roadmap by decomposing conceptual design and standards into independent work items, classifying each as technical or design, grouping into dependency-aware execution waves, and generating plans via the standard workflow (with optional `--framing metacomm` for design items). Three modes: auto-generate from project references, parse a pre-filled spec file, or generate a blank spec skeleton.

## Mode Selection

If no sub-mode flag is provided beyond `--roadmap`, use AskUserQuestion (or a numbered text list if AskUserQuestion is unavailable). Options phrased per C4:

- **1. Auto-generate** -- I read project reference files and decompose work into dependency-aware waves. Recommended when `/design` has populated project references. NOT recommended when references are stale or missing -- the roadmap inherits the gaps. When combined with `--only-unimplemented`, extraction scopes to open items only.
- **2. From spec file** -- I compile a pre-filled `roadmap-spec.md` into the roadmap. Recommended when you have a manual draft or the refs are not yet canonical. NOT recommended when no spec exists -- use option 3 first.
- **3. Generate blank spec** -- I create a `roadmap-spec` skeleton for offline editing; invoke option 2 later. Recommended when you want human-authored control before auto-decomposition. NOT recommended when project references are already authoritative -- option 1 is faster.

`--auto` -> Mode 1 directly. `--from-spec <path>` -> Mode 2 directly.

---

## Mode 1: Auto-generate from project references

> **Q&A tracking**: maintain `qa_engaged` (default `false`). Set `true` when the user (a) modifies the work item list (add/remove/reorder/reclassify/dep adjustments), (b) requests plan revision mid-stream, or (c) asks clarifying questions that change the roadmap or a plan. Simple accept/confirm answers do NOT constitute Q&A. Drives the finalization step.

Steps 1-11 below. Common-step reuse: step 1 = C1; step 8 = C2+C3 with `--type roadmap`; steps 9 and 10 = C4+C6; all other steps are Mode-1-unique.

1. Apply C1 (pre-skill).

2. **Read project references**. If `project/product-design-as-intended.md` is missing, abort and suggest `/design`. `project/product-design-as-coded.md` is required for brownfield, optional for greenfield. Others are optional (warn but continue):
   - `project/product-design-as-coded.md` (three H2 sections: Conceptual Design, Metacommunication, Journey Maps -- empty or absent for greenfield)
   - `project/product-design-as-intended.md` (target-state entities, hierarchy, permissions, UX patterns, metacommunication intentions)
   - `project/conventions.md` (directory structure, source paths)
   - `project/standards.md § Backend` (API patterns, service layer)
   - `project/standards.md § Frontend` (pages, components, routing)
   - `project/standards.md § i18n` (locales, translation scope)
   - `project/security-checklists.md` (validation, auth)

2b. **Requirements extraction pass**: if `product-design/product-design-as-intended.md` contains REQ markers (`<!-- REQ-*-NNN -->`), launch a `general-purpose` agent (Agent tool) with fresh context to extract a requirements index. The agent:
   1. Reads `product-design-as-intended.md` in full.
   2. For each REQ marker extracts: ID, section number, heading/title, classification (per type prefix in `general/shared-definitions.md` -- PERM/VAL -> security; UX/MC/JM -> ux; ENT/DELTA -> technical; I18N -> cross-cutting).
   3. Outputs a flat markdown table:
      ```
      | ID | Section | Title | Classification |
      |---|---|---|---|
      | REQ-ENT-001 | 2 | User entity | technical |
      | REQ-PERM-001 | 4 | Admin role | security |
      ```

   Use this index as the decomposition input (step 3) instead of re-reading full prose. Each work item notes which REQ IDs it covers.

   **`--only-unimplemented` filter**: when present, exclude REQs whose section/heading/row carries any of these STATUS markers:
   - `<!-- STATUS: implemented | plan-NNNNNN | YYYY-MM-DD -->` (current lowercase)
   - `<!-- STATUS: established | plan-NNNNNN | YYYY-MM-DD -->` (promoted)
   - `<!-- STATUS: IMPLEMENTED | plan-NNNNNN | YYYY-MM-DD -->` (legacy uppercase; see `general/shared-definitions.md` § STATUS state machine)

   Filter scopes input to open items only; classification and downstream behavior (step 3 Delta, step 4 Technical/Design, step 5 Waves) are unchanged. Disjoint from `/explain spec-drift --promote` Phase 3a.

   If no REQ markers, skip this step; step 3 reads the full prose. `--only-unimplemented` is a no-op in that branch.

3. **Decompose into work items**: compare as-coded vs as-intended to derive work items from the **delta**.

   | Condition | Work item type |
   |---|---|
   | In as-intended but not as-coded | **new** |
   | In as-coded but removed in as-intended | **deprecation** (remove migration, API sunset, UI removal) |
   | In both but differing | **modification** (alter migration, API update, UI update) |
   | Greenfield (identical or as-coded empty) | all as-intended entities treated as new |

   **Layer decomposition** applied to the delta:

   | Layer | Parallelism | Work item granularity | Depends on |
   |---|---|---|---|
   | Foundation | Sequential (migration chain) | One per entity cluster (shared FKs): model + migration + basic service + unit tests | -- |
   | Service + API | Parallel per resource | One per API resource (CRUD endpoints, validation, permissions) | Foundation for those entities |
   | Frontend | Parallel per page/feature | One per page or major feature | API for those endpoints |
   | Cross-cutting | Limited | i18n setup, auth integration, contextual help, error patterns | Shared files |

4. **Classify each work item**:
   - **Technical** -- infrastructure, models, services, APIs, migrations, tests. Planned via standard workflow.
   - **Design** -- UX flows, page layouts, hierarchy, empty states, onboarding, discoverability. Planned with `--framing metacomm`.

   Heuristic: primary value in *what the user sees and experiences* -> design. Primary value in *what the system does internally* -> technical.

5. **Group into execution waves**:
   - **Wave 0 (sequential)**: Foundation models + migrations (strict order).
   - **Wave 1 (parallel)**: Service + API layer (depends on Wave 0).
   - **Wave 2 (parallel)**: Frontend pages + features (depends on Wave 1).
   - **Wave 3 (limited parallel)**: Cross-cutting (i18n, auth, help, error handling).
   - **Wave 4 (parallel)**: Testing and polish (E2E, a11y, docs).

6. **Present draft roadmap for review**: numbered list grouped by wave; per item show ID (slug), Title, Scope (backend/frontend/fullstack), Size (S/M/L), Classification, Dependencies.

7. Ask the user to review, add, remove, or reorder items.

8. **Save roadmap summary** (apply C2 with `--type roadmap`; header per C3) to `${ROADMAP_DIR}/roadmap-<id>-<slug>.md`. Shape: see `.claude/references/template/roadmap-summary.md`.

9. **Plan generation decision point**: present AskUserQuestion with three options (phrased per C4):

   - **Create all plans now** -- generates plans for every item, waves sequential (Wave 0, then Wave 1, etc.). Each plan invokes the standard workflow inline.
     - Recommended when: <=5 work items and you want to proceed immediately.
     - NOT recommended when: 6+ items -- context budget may degrade later waves.
   - **Create plans for Wave 0 only** -- generates only foundational wave plans.
     - Recommended when: 6+ items, or you want to review foundation plans before committing to the full roadmap.
     - NOT recommended when: the full scope is known-correct and you want batch generation.
   - **Don't create plans now** -- keep roadmap with `plan-TBD` entries; create plans manually later.
     - Recommended when: you want cross-session review, sharing, or aren't ready to implement.
     - NOT recommended when: you have clear scope and want to start immediately.

   **Context budget guardrail**: if >5 items and user selects "Create all plans now", emit: "This roadmap has N work items. Generating all plans in a single session may impact quality for later waves. Consider 'Wave 0 only' if quality is a concern." Do not block.

   **Conditional plan generation** based on choice:
   - **Technical**: invoke the standard workflow inline (read `.claude/skills/_internal/plan/standard/SKILL.md` via the Read tool per work item; execute steps 1-6 inline; skip steps 7 and 8 per the clarification below) with item description.
   - **Design**: invoke the standard workflow inline (read `.claude/skills/_internal/plan/standard/SKILL.md` via the Read tool per work item; execute steps 1-6 inline; skip steps 7 and 8 per the clarification below) with `--framing metacomm` and item description phrased as I/you (e.g., "When you open the home page, I want you to see...").
   - After each plan is generated, update the roadmap file's Plan column from `plan-TBD` to the actual ID.
   - If "Don't create plans now", skip generation.
   - **Inline-invocation clarification**: when invoking the standard workflow inline for a work item, skip that workflow's step 7 (AskUserQuestion next-step prompt) and step 8 (per-plan /post-skill). Per C6, the roadmap's finalization step owns the commit decision for the whole run; per-plan finalization would produce N prompts and N commits, defeating the unified-artifact contract.

   **Anti-pattern -- do not pre-reserve plan IDs.** `/plan` reserves its own ID when invoked (C2 applies per plan); never call `reserve_id.py --type plan` up front for downstream items. The Plan column starts as `plan-TBD` and is filled with the real ID after `/plan` completes. See `SKILL-rationale.md` for the failure-mode reasoning.

9b. **Coverage check (advisory)**: if any plans were generated and REQ markers exist, run `python .claude/skills/design/check_plan_coverage.py --mode advisory` and include the coverage summary in the roadmap file.

10. **Finalize the roadmap run** (C6 applies for the /post-skill call):
    - `qa_engaged == false`: auto-commit the roadmap summary + generated plan files in a single commit via /post-skill with the roadmap ID. Commit message: `roadmap-<id>: <N> plans generated across <M> waves` (adjust per wave generation scope). Print: `Committed roadmap <id> and <N> generated plans.`
    - `qa_engaged == true`: use AskUserQuestion. Options phrased per C4:
      - **Commit all now** -- runs /post-skill as above. Recommended when Q&A produced a coherent, shippable set. NOT recommended when review is pending or some plans are known wrong.
      - **Keep uncommitted for review** -- no commit; files on disk. Recommended when you want to read offline or share before committing. NOT recommended when delay risks losing Q&A context.
      - **Revise further** -- stop; not committed. Recommended when the current state is not shippable. NOT recommended when remaining revisions are cosmetic and don't affect commit-readiness.

    After the commit decision (both auto-commit and "Commit all now" branches), file a pending entry for cross-session recall. Skip when all Plan column entries are `plan-TBD` (user chose "Don't create plans now" -- no actionable plans to implement).

    ```
    python .claude/skills/scripts/pending.py add --if-absent \
      --type implement \
      --source roadmap-<id> \
      --description "Execute roadmap-<id>: <N> plans across <M> waves — see <roadmap-file-path>"
    ```

    Silent on success (script prints pa-NNNNNN or `INFO: existing open ... skipping`). Non-zero -> `Warning: could not file roadmap pending entry for roadmap-<id>: <reason>`. Do not block.

11. **Output execution instructions**, adapted to which plans were generated:
    - All plans generated: show `/implement <plan-id>` commands with real IDs per wave.
    - Wave 0 only: show `/implement <plan-id>` for Wave 0 and `/plan <description>` for remaining waves.
    - None generated: show `/plan <description>` for all waves.
    - Include the recommended execution method (multiple Claude Code sessions or worktree-isolated agents) for parallel waves.

---

## Mode 2: From spec file

> **Q&A tracking**: maintain `qa_engaged` (default `false`). Set `true` when the user adjusts parsed items at step 4/5/6 or requests plan revision mid-stream. Simple accept/confirm answers do NOT constitute Q&A.

Steps 1-10. Common-step reuse: step 1 = C1; step 7 = C2+C3 with `--type roadmap` (behaves like Mode 1 step 8); step 8 reuses the Mode 1 step 9 prose (decision point + inline-invocation clarification); step 9 reuses Mode 1 step 10 (finalization); step 10 reuses Mode 1 step 11 (execution instructions). Steps 2-6 are Mode-2-unique.

1. Apply C1 (pre-skill).

2. **Locate spec file**: use `--from-spec` path, or ask the user.

3. **Parse the roadmap-spec.md**: extract themes, work items, constraints, wave groupings. Rules:
   - `- key: value` lines are key-value pairs (value = everything after first colon, trimmed).
   - `## ` or `### ` lines are section/subsection headers.
   - `<!-- ... -->` lines are HTML comments (ignored).
   - Empty values mean "not provided" (defaults or ask).
   - `description:` uses YAML-style `>` for multi-line text.

4. **Validate**: missing required fields (id, title, scope, description per item); circular dependencies; items with `depends_on` referencing non-existent IDs. Present a validation report.

5. **Classify items**: apply the Mode 1 technical/design heuristic. Users can override via optional `type: technical | design` per item.

6. **Present validation report** with parsed items, classifications, dependency graph. Ask user to confirm or adjust.

Steps 7-10: follow Mode 1 steps 8 -> 9 -> 10 -> 11 prose. Mode 1 is the single source of truth if shared behavior changes.

---

## Mode 3: Generate blank spec

Steps 1-4. Mode 3 skips every Common Step (no pre-skill, no ID reserve, no post-skill -- the spec file is a local artifact the user fills in offline).

1. **Determine target directory**: current working directory, or ask the user.

2. **Create `<target>/specs/`** if missing.

3. **Generate the spec file**: copy `.claude/references/template/roadmap-spec.md` to `<target>/specs/roadmap-spec-YYYY-MM-DD HH.MM UTC.md`; substitute `{datetime}` with current UTC datetime.

4. **Output next steps**:
   > Spec file created at `<path>`.
   >
   > Fill in your choices -- inline comments explain options. Required per item: id, title, scope, description. Everything else is optional.
   >
   > When ready, run `/plan --roadmap --from-spec <path>`.

---

## Roadmap Summary File Format

See `.claude/references/template/roadmap-summary.md` for the header shape, ## Source list, ## Wave Summary tables, and ## Execution Instructions block.
