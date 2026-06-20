---
name: design-mode1-internal
description: "Inlined worker for /design Mode 1 (Interactive Questionnaire). Not user-invocable."
compatibility: "Designed for Claude Code with the SEJA harness"
metadata:
  internal: true
  category: internal
  version: 1.0.0
---

> This is an inlined worker; execute these instructions as part of the caller's flow. The wrapper at `.claude/skills/design/SKILL.md` has already run the Detection Logic; execute the steps below.
>
> **Stable-contract steps**: Steps 7-15 are stable-contract steps. Mode 2 executes steps 7, 8, 9, 10, and 12 by step number reference. Mode 5 Phase D resumes from step 7 by step number reference. Renumbering these steps requires updating `_internal/design/from-spec/SKILL.md` and `_internal/design/interview/SKILL.md` simultaneously.
>
> **Callers**: Mode 2 delegates steps 7 (Instantiate templates), 8 (Amend CLAUDE.md), 9 (Rules generation), 10 (Smoke-test infrastructure), and 12 (Secrets check) here. Mode 5 Phase D resumes from step 7 (Instantiate templates) onward. In both cases, those callers read this file and execute only the specified step range, not the full body.
>
> **Field Classification**: The Field Classification section is in the calling wrapper SKILL.md (`.claude/skills/design/SKILL.md ## Field Classification`) -- it is loaded into context before this internal executes.

### Mode 1: Interactive Questionnaire

1. **Check for in-progress design**: If `specs/design-in-progress.md` exists, ask "Resume previous design session or start fresh?"

2. **Run the questionnaire**: Read `template/questionnaire.md` and walk the user through it. Two entry paths:
   - **Partial-design entry** (the common post-`/seja-setup` case): when Mode 1 is entered from the partial-design state (see Detection Logic), load the questionnaire with `section-include: "design-intent-only"` (shortcut defined in `template/questionnaire.md § Parser directives`: `0, 2.*, 3.*, 4.*, 5+`). Section 1 basic-definitions is already populated in `conventions.md` by `/seja-setup` step 4b; do NOT re-prompt for stack values. Start with Section 0 (metacomm; optional, skip if reused from invocation) and continue with Sections 2-5+ (conceptual-design, UX/visual design, standards, docs). Skip the "After Section 1" continuation prompt -- the flow jumps straight from Section 0 to Section 2.
   - **Legacy fully-empty entry** (no `conventions.md` at all): load the questionnaire with the default all-sections behavior. Start with Section 0 (optional; skip if reused) then Section 1 -- 10 minimum questions for a working skeleton. After Section 1, ask whether to continue remaining sections or use defaults.
   - **Invocation-supplied metacomm** (applies to both entry paths): If the user already supplied a metacommunication message at invocation (initial prompt, preceding `/seja-setup` brief, or explicit "metacomm: ..." line), treat Section 0.1 as already answered verbatim and skip both Section 0.1 and the Final Step re-prompt. Confirm reuse: "Using metacomm message you provided at invocation." Extraction hints still apply.
   - **Metacomm hint reuse** (applies to both entry paths): If Section 0.1 is answered (via prompt or reuse), parse it and extract project name hint, description, target user type, primary use case. At questions 2.1, 2.10 (partial-design entry) or 1.1, 1.2, 2.1, 2.10 (legacy fully-empty entry) present: "From your metacomm message, I suggest: [value]. Accept or override?"
   - For each question presented, offer options with pros/cons and a recommendation. Record answers.

3. **Interruptibility**: At any point, if the user stops, save answers to `specs/design-in-progress.md` and print "Progress saved. Run `/design` again to resume."

4. **Skip to defaults**: On "use defaults for everything else", fill remaining fields from the Field Classification defaults table and proceed to template instantiation. For brownfield: defaults = detected values (step 5b) for stack fields + template defaults for design fields.

5. **Mandatory conceptual design**: Core Section 2 questions are required; defaults cannot substitute. Minimum required for all projects:
   - Entity hierarchy (2.3), Permission levels (2.6), Greenfield/evolving status (2.9)
   - Metacommunication message (handled in Final Step; skipped if Section 0.1 already answered -- verbatim rule applies to the final confirmed answer)

   Brownfield additionally requires existing tech stack (2.12) and migration constraints (2.13).

5b. **Brownfield stack auto-detection** (moved to `/seja-setup`):

    Brownfield stack auto-detection has moved to `/seja-setup` step 4b (sub-step 4b.i). Run `/seja-setup --upgrade` or `/seja-setup <target>` for stack re-detection; `/design` no longer performs stack-level codebase scanning.

    **Legacy pre-scaffolding fallback (Amendment A4)**: when `/design` enters the partial-design state (see step 8 below) and `product-design/conventions.md` exists with no populated `BACKEND_FRAMEWORK` row (regardless of `PROJECT_MODE` -- legacy greenfield and legacy brownfield both route here), re-run the detection inline as a compatibility fallback. Emit the one-line note:

    > Legacy pre-scaffolding project detected (PROJECT_MODE=`<value>`); running Section 1 inline. Future upgrades will carry `.seja-version` for a cleaner path.

    The inline re-run uses the same detection logic that now lives in `/seja-setup` step 4b.i: scan `${CODEBASE_DIR}` for `package.json`, `requirements.txt`, `pyproject.toml`, etc.; map to `BACKEND_FRAMEWORK`, `FRONTEND_FRAMEWORK`, `DATABASE`, `BACKEND_TEST`/`FRONTEND_TEST`, directory vars; present confirmation prompts; fall back to manual entry on ambiguous detection. After the inline re-run, continue with steps 5c-5e and the rest of the questionnaire as normal.

5c. **As-Coded Pre-population** (brownfield; runs after 5b when `MODELS_DIR` or schema files detected):

    Extract domain knowledge from step 5b scan to pre-populate `## Conceptual Design` in `product-design-as-coded.md` in place of the empty template.

    1. **Entity extraction** -- scan models per detected ORM:

       | ORM | Scan location | Entity signal |
       |---|---|---|
       | SQLAlchemy | `${MODELS_DIR}` or `models/*.py` | classes inheriting `db.Model` or `Base` |
       | Django | `*/models.py` | classes inheriting `models.Model` |
       | Prisma | `prisma/schema.prisma` | `model` blocks |
       | TypeORM | `entities/` or `src/entities/` | `@Entity()` classes |
       | Sequelize | `models/` | `sequelize.define()` / `Model.init()` |
       | ActiveRecord | `app/models/` | classes inheriting `ApplicationRecord` |

       Per model, extract: entity name + mapped table; field names + types; relationships (FKs, M2M, O2M); visibility/access rules (visibility fields, is_public, scoped queries); soft-delete indicators (`deleted_at`, `paranoid`, `acts_as_paranoid`). Build an entity tree for `### 2. Entity Hierarchy`: parent = target of FK; root = entity with no inbound ownership FK.

    2. **Permission extraction** -- scan routes/controllers for decorators and middleware:

       | Stack | Signals |
       |---|---|
       | Flask | `@login_required`, `@roles_required`, `@jwt_required`, `@permission_required` |
       | Django | `@login_required`, `@permission_required`, `@user_passes_test`, `permission_classes` |
       | FastAPI | `Depends()` auth functions, `Security()` scopes |
       | Express | middleware: `isAuthenticated`, `authorize()`, `requireRole()` |
       | Rails | `before_action :authenticate_user!`, `authorize`, Pundit, CanCanCan |

       Build Section 4: distinct roles -> System-Level Roles table; resource-scoped guards -> Resource-Level Access table.

    3. **Validation extraction** -- scan schemas for field constraints:

       | Library | Signals |
       |---|---|
       | Marshmallow | `Schema` subclasses, `fields.String(validate=Length(...))`, `Required` |
       | Pydantic | `BaseModel`, `Field(min_length=..., max_length=...)`, `constr()`, `conint()` |
       | Zod | `z.string().min().max()`, `z.number().int().positive()` |
       | Django Forms/Serializers | `max_length`, `min_length`, `validators=[...]` |
       | Joi | `Joi.string().min().max()`, `Joi.number().integer()` |

       Map to Section 10 (Validation Constants) as field name | min/max | source file.

    4. **Present extracted as-coded model**: Before writing, display a structured summary (Entities, Permissions, Validation Constants, and "Sections with no data detected -- will retain placeholder text"). Ask "Confirm, edit, or add details before I save it to `product-design-as-coded.md § Conceptual Design`."

    5. **Populate**: After confirmation, write `## Conceptual Design` in `project/product-design-as-coded.md` with confirmed content in subsections 2, 4, 10 (and any others with data). Other H3 subsections keep template placeholder text. Preserve the `maintained-by: Agent (post-skill)` header. `## Metacommunication` and `## Journey Maps` H2s remain placeholders (post-skill populates on first plan execution).

5d. **Brownfield Questionnaire Flow** (brownfield/evolving; three phases):

    - **Phase 1 -- Automated scan**: when entering from partial-design (the common post-`/seja-setup` case), Phase 1 is a **no-op** -- the stack-level scan already ran in `/seja-setup` step 4b.i, and `conventions.md` carries the confirmed stack/directory values. Run only 5c (as-coded pre-population) to extract domain knowledge from the code; re-using 5b's scan is redundant. Legacy fully-empty entry still runs 5b (via the A4 legacy-fallback branch) and 5c. Present detected values before proceeding.
    - **Phase 2 -- Confirm detected values**: skipped when entering from partial-design (Q1.4, Q1.5, Q1.6, Q1.9 already confirmed in `/seja-setup` step 4b.i; Q2.12 is design-intent and remains in Phase 3). Legacy fully-empty entry still presents confirmation prompts pre-filled with detected values. Format: "I detected **[value]** as your [field] [from source]. Correct? (yes / override: ___)". Undetected fields fall back to standard manual entry.
    - **Phase 3 -- Intent-only questions** (cannot be inferred from code; runs in both entry paths): Metacomm (0.1), Design philosophy (2.2), Entity hierarchy refinement (2.3 -- present detected entities then ask whether to refine), Permission refinement (2.6), Existing tech stack summary (2.12 -- design-intent view, not stack values), Migration constraints (2.13), Pain points (2.15), Design system (2.16), all UX/graphic design sections (3.x, 4.x).

5e. **Validation Cross-check** (brownfield; runs after 5d, before template instantiation):

    Current-state vs target-state routing:
    - `conventions.md` variables = current state (detected) so plans execute against existing code
    - `product-design-as-intended.md` = target state (questionnaire answers)
    - `product-design-as-coded.md § Conceptual Design` = current state (populated by 5c)

    **Discrepancy detection**: For each field with both detected and answered values, if they differ prompt: *"You specified **[answer]** but I detected **[detected]**. Which is correct -- current state (**[detected]**) for conventions.md, or target state (**[answer]**) for product-design-as-intended.md? Or are they the same?"*

    Cross-check fields (match 5b targets): `BACKEND_FRAMEWORK`, `FRONTEND_FRAMEWORK`, `DATABASE`, `BACKEND_DIR`, `FRONTEND_DIR`, `MODELS_DIR`, `MIGRATIONS_DIR`, plus any other variables both detected and answered.

    **Dual population** when states differ (e.g., Flask -> FastAPI): `conventions.md` = current value; `product-design-as-intended.md § Section 0 "Planned Changes"` = migration intent; `product-design-as-coded.md § Conceptual Design` already reflects current state from 5c. If all answers match detected values, skip the cross-check silently.

6. **Codebase scaffolding question**: After stack decisions are made, ask:
   > "Should I create the initial project structure (directories, config files, entry points) for your chosen stack?"
   - If yes, run the project scaffolding tasks (see Project Scaffolding section)
   - If no, skip

7. **Instantiate templates**: Copy `template/*` -> `project/*` substituting questionnaire answers. `conventions.md` is NOT instantiated here -- it was scaffolded by `/seja-setup` step 4b (Section 1 questionnaire + conditional-stack population). `/design` only amends `conventions.md` in-place to set `PROJECT_MODE` from Q2.9 (greenfield -> `greenfield`, evolving -> `brownfield`) when Q2.9 is answered in this Mode 1 run. Legacy fully-empty entry (no `conventions.md` at all): instantiate `template/conventions.md` with Section 1 answers inline as a compatibility fallback. Core file set (excludes `conventions.md`):

   | Source | Destination | Notes |
   |---|---|---|
   | `template/constitution.md` | `project/constitution.md` | Required; always generated. Content may be customized but not skipped. |
   | `template/product-design-as-intended.md` | `project/product-design-as-intended.md` | `Human (markers)`. Prose human-authored; agents write `STATUS`/`DECISION_APPEND` (`### D-NNN:`) via `apply_marker.py` after AskUserQuestion. Includes `## Decisions` + `## CHANGELOG`. Apply I/you phrasing rule for Part II metacomm sections. |
   | `template/product-design-as-coded.md` | `project/product-design-as-coded.md` | **Brownfield only.** If step 5c produced pre-populated `## Conceptual Design`, use that in place of the empty section. Greenfield: do NOT instantiate (post-skill creates it on first plan execution). |
   | `template/product-design-changelog.md` | `project/product-design-changelog.md` | Brownfield only. Kept separate from `product-design-as-coded.md`. |
   | `template/standards.md` | `project/standards.md` | Backend, Frontend, Testing, i18n sections. |
   | `template/design-standards.md` | `project/design-standards.md` | UX patterns + Graphic/visual design. |
   | `template/security-checklists.md` | `project/security-checklists.md` | -- |
   | `template/ux-research-results.md` | `project/ux-research-results.md` | `Human (markers)`. Pre-populate personas/user community from Q2.10 if provided. Agents write `INCORPORATED` + CHANGELOG appends via `apply_marker.py`. |
   | `template/agent/{constraints,entities,permissions,spec-checks}.yaml` | `project/agent/*` | Agent YAML specs. |
   | `template/docs/*.md` | `project/docs/*.md` | Per Section 5 answer: "defaults" -> 3 recommended (readme, contextual-help, drr); "skip" -> none; else selected subset. |
   | `template/settings.json` | `.claude/settings.json` | Substitute actual paths. |

   > **Registry note:** For each row in the As-Intended / As-Coded Registry (see conventions.md), ensure the as-intended template is copied during project setup; as-coded templates are copied for brownfield projects per the branch above. When new rows are added in future harness versions, add their template copies here.

8. **Amend CLAUDE.md** with design-intent references. `CLAUDE.md` was scaffolded by `/seja-setup` step 7c (anchor: `Scaffold-CLAUDE.md`) and already carries project name, stack summary, build/run commands, conditional architecture summaries, and `@`-references to `.claude/rules/` + `product-design/conventions.md`. Do NOT regenerate from scratch; append a new `## Project design` section to the existing file containing `@`-references to the design-intent artifacts produced by this Mode 1 run:

   - `@product-design/product-design-as-intended.md`
   - `@product-design/ux-research-results.md`
   - `@product-design/standards.md`
   - `@product-design/design-standards.md`
   - `@product-design/security-checklists.md`
   - `@product-design/constitution.md`
   - plus any project-specific conventions Section 6 (T2) declared (e.g., additional rule files or per-domain references).

   If CLAUDE.md is missing (legacy project that predates the scaffolding move), fall through to the legacy-regenerate path: apply the `Scaffold-CLAUDE.md` anchor body from `/seja-setup` step 7c first to produce a baseline, then append the `## Project design` section.

9. **Rules generation (moved to `/seja-setup`)**: Rule generation is now handled by `/seja-setup` step 7d (`Scaffold-Rules` anchor). `/design` may propose rule amendments when a Section 2 entity cluster warrants scoped guidance, but the initial set is scaffolded by `/seja-setup`.

10. **Smoke-test infrastructure (moved to `/seja-setup`)**: Smoke-test infrastructure is now scaffolded by `/seja-setup` step 7e (`Scaffold-SmokeTestInfra` anchor). `/design` no longer emits these files.

11. **Verification pass** (always runs after template instantiation). Print "Verifying design output...".

    1. Read the spec input (questionnaire answers) and 3 critical generated files: `project/product-design-as-intended.md` (Part II, sections 11-15), `project/constitution.md`, `project/security-checklists.md`.

    2. Evaluate semantic fidelity per file:
       - **design-intent Part II**: metacomm message -> generated §11 Global Vision match; §12 EMT guiding questions populated from spec (not placeholders); §14 per-feature intentions cover all spec features.
       - **constitution**: all immutable principles from the spec present and not contradicted.
       - **security-checklists**: all security constraints (validation constants, auth requirements) present.

    3. If gaps found: fix by updating the file, log "Verification: added missing [field] to [file]", re-run evaluation once (1 retry bound). If gaps persist, log "Verification: [N] semantic gaps remain in [file] after 1 retry. Please review manually."

    4. Print "Design output verified. [N] files checked, [M] gaps found and fixed."

    5. **Requirement ID assignment**: For each enumerable requirement in `project/product-design-as-intended.md`, emit an HTML-comment marker `<!-- REQ-TYPE-NNN -->` on the line immediately before the heading/row/bullet. Counters are per-TYPE, zero-padded, starting at 001. TYPE mapping: §2 -> ENT, §4 -> PERM, §7 -> I18N, §8 -> UX, §10 -> VAL, §14 -> MC, §15 -> JM, §16-17 -> DELTA. Enables `check_plan_coverage.py` traceability.

12. **Secrets check**: Run `python .claude/skills/design/check_secrets.py` to verify no secrets are staged.

13. **Clean up**: Remove `specs/design-in-progress.md` if it exists.

14. **Summary**: Output a checklist of everything created and any manual steps needed.

15. **Review & next steps**: Present generated files with their Controls and Questionnaire-source:

    | File | Controls | Sourced from (questionnaire) |
    |---|---|---|
    | `project/conventions.md` | Directory paths, variable definitions | Stack choices (T2) |
    | `project/constitution.md` | Immutable principles, security invariants | Immutable principles (T2) |
    | `project/product-design-as-intended.md` | Unified working intent (§1-§17), `## Decisions` (DRR shape), CHANGELOG. `Human (markers)`. | Q2.3 (entities), Q2.6 (permissions), Final Step metacomm -> §15 |
    | `project/ux-research-results.md` | Personas, problem scenarios, cross-ref map, processing status, JM-E-NNN journeys, CHANGELOG. `Human (markers)`. | Q2.1, Q2.10 |
    | `project/standards.md` | Backend, Frontend, Testing, i18n sections | Backend/Frontend/Testing/i18n patterns (T3) |
    | `project/design-standards.md` | UX patterns + Graphic/visual design | UX patterns (T1), Visual design (T1) |
    | `project/security-checklists.md` | Security checklists, validation constants | Security constraints (T3) |
    | `project/docs/*.md` | Documentation structure templates | Section 5 (docs-templates) |

    Then offer: 1) Review specs now, 2) Generate roadmap (`/plan --roadmap`), 3) Done for now.

---

## Project Scaffolding

When the user opts in, offer the following task catalog based on stack choices:

**Tasks**: source dirs, Python venv, backend requirements, Node.js init, frontend scaffold, Tailwind config, .env files, migration tool init, E2E test dir, .gitignore.
