---
name: seja-setup-install-internal
description: "Inlined worker for /seja-setup Standard Install Flow. Not user-invocable."
compatibility: "Designed for Claude Code with the SEJA harness"
metadata:
  internal: true
  category: internal
  version: 1.0.0
---

> This is an inlined worker; execute these instructions as part of the caller's flow. The wrapper at `.claude/skills/seja-setup/SKILL.md` has already run the Entry-Point Routing dispatch; execute the steps below as part of the `/seja-setup` skill's flow. Demo mode (`--demo`) instructs this internal to be read and executed for steps 1-7 only, before continuing with the demo-specific steps.

## Standard Install Flow

> **Scaffolding note**: this flow now populates `product-design/conventions.md` inline via the Section 1 basic-definitions questionnaire (step 4b below), scaffolds `CLAUDE.md` (step 7c), scaffolds stack-flavored `.claude/rules/` (step 7d), and scaffolds smoke-test infrastructure when a backend is present (step 7e) so the project boots with a stack-scaffolded skeleton in one invocation. `/design` is invoked afterwards to populate design-intent files (metacomm, personas, entities, permissions, standards, constitution) and amend `CLAUDE.md` with design-intent references.

**Mode Detection**: `--here` -> `## --here Flag`. `--upgrade` -> `## Upgrade Flow`. Otherwise follow steps below. `--workspace` and `--demo` are handled within these steps and in their dedicated sections.

1. **Accept target directory**: if not provided as argument and not collected via no-arg flow, ask the user.

2. **Detect scenario**:

   | Scenario | Detection | Action |
   |----------|-----------|--------|
   | Greenfield | Target does not exist | Create directory (do NOT `git init` yet -- workspace routing in 2b decides) |
   | Empty project | Target exists, git repo, no source code | Proceed to copy |
   | Existing codebase | Target exists, git repo, has source code | If `--workspace`, go to 2b. If `.claude/` exists, see the `.claude/`-exists menu below. Otherwise ask "Embed SEJA in this codebase or create a separate workspace?" (Embed, Companion workspace). Companion -> 2b; Embed -> copy. |
   | Not a git repo | Target exists, not a git repo | Offer `git init`, or abort |

   **`.claude/` exists menu** (target already has a SEJA install):
   - **Overwrite harness only** (recommended for upgrades) -- overwrite skills, `general/` refs, `template/` refs, scripts, agents, rules. **Never touch** `project/` refs, `settings.json`, `settings.local.json`, output dir, or `CLAUDE.md`.
   - **Overwrite everything** -- full re-setup (destructive, requires confirmation).
   - **Create companion workspace** -- treat this dir as codebase; create workspace alongside (codebase not modified). Proceed to 2b (brownfield).
   - **Abort**.

2b. **Workspace routing** (if `--workspace` or user chose workspace):
   - **Greenfield**: ask workspace + codebase dir names -> create both subdirs -> `git init` each -> redirect harness files to workspace dir.
   - **Brownfield**: ask workspace dir path -> detect embedded harness files in codebase -> offer to migrate SEJA files to workspace -> create + `git init` workspace dir.
   - **No separation**: `git init` target if not already a repo -> continue with in-place setup.
   - Always generate launcher scripts (`launch.sh` / `launch.bat`) that invoke `claude --add-dir <codebase-dir>`.

3. **Create directory structure** in target (or workspace): `.claude/references/{general,template}/` and `product-design/`, `.claude/{skills/scripts,rules,agents}/`.

4. **Copy harness files** from source to target:
   - `.claude/references/general/` (all, as-is).
   - `.claude/references/template/` (all; consumed by `/design`), including `template/constitution.md` (immutable principles template) and `template/agent/*.yaml` (agent-facing structured specs).
   - `template/settings.json`.
   - All skill `SKILL.md` files (project-independent).
   - `.claude/agents/*.md`, `.claude/rules/*.md`, `.claude/skills/scripts/*.py`.
   - `.claude/CHANGELOG.md`, `.claude/CHEATSHEET.md`, `.claude/skills/VERSION`.

4b. **Scaffolding questionnaire** (populate `conventions.md`): run `.claude/references/template/questionnaire.md` with `section-include: "stack-only"` (the shortcut defined in the Parser directives section, which expands to Q 0.1 metacomm-message + all of Section 1 basic-definitions). Skip entirely when `--demo` is active -- demo mode uses the pre-filled `.claude/references/template/demo/conventions.md` and the subsequent `--demo` step 9 copies it into place. Output: populated `product-design/conventions.md` instantiated from `.claude/references/template/conventions.md`. The optional Q 0.1 metacomm answer (if provided) is stored for `/design` to consume when it runs; at setup time we do not yet produce `product-design-as-intended.md`.

   **4b.i -- Brownfield stack auto-detection (pre-fill).** Before presenting the Section 1 questions, check whether the target path contains an existing codebase (source files under `${CODEBASE_DIR}`). If so, scan dependency files and directory structure to pre-fill the questionnaire with detected values; each affected question is presented as a confirmation prompt ("I detected **flask**; correct?") rather than an open-ended entry. If no source or ambiguous detection, fall back to standard manual entry.

    1. **Detect stack from dependency files**: Read whichever exist in `${CODEBASE_DIR}`: `package.json`, `requirements.txt`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `Gemfile`, `pom.xml`, `build.gradle`. Map detected dependencies to `conventions.md` variables:

       | Variable | Source signals |
       |---|---|
       | `BACKEND_FRAMEWORK` | `flask`, `fastapi`, `django`, `express`, `nestjs`, `spring-boot`, `rails`, `actix-web`, `gin` |
       | `FRONTEND_FRAMEWORK` | `react`, `vue`, `angular`, `svelte`, `next`, `nuxt` |
       | `ORM` | `sqlalchemy`, `prisma`, `django-orm`, `typeorm` |
       | `VALIDATION` | `marshmallow`, `pydantic`, `zod` |
       | `AUTH` | `flask-jwt-extended`, `passport`, `django-allauth` |
       | `CSS` / `BUILD_TOOL` / `STATE` | `tailwindcss`/`bootstrap`; `vite`/`webpack`/`esbuild`; `redux`/`zustand`/`pinia` |
       | `DATA_FETCHING` / `HTTP_CLIENT` / `ROUTER` | `tanstack-query`/`swr`/`apollo`; `axios`/`ky`; `react-router`/`vue-router` |
       | `BACKEND_TEST` / `FRONTEND_TEST` | `pytest`/`jest`/`mocha`; `vitest`/`jest`/`testing-library` |
       | `DATABASE` | ORM config, `docker-compose.yml` services, `.env` `DATABASE_URL`, migration dir (`alembic/`, `prisma/migrations/`, Django migrations) |

    2. **Detect directory structure**: Find `BACKEND_DIR`/`FRONTEND_DIR` via entry points (`app.py`, `manage.py`, `main.py`, `server.ts`, `index.ts`, `App.tsx`, nested `package.json`). Detect `MIGRATIONS_DIR` (e.g., `alembic/versions/`, `prisma/migrations/`, `<app>/migrations/`) and `MODELS_DIR` (e.g., `models/`, `app/models/`, `src/entities/`) from ORM conventions.

    3. **Present detected values**: Display a summary table (columns: Variable | Detected Value | Source) and ask "Accept, override, or correct each value:".

    4. **Pre-fill questionnaire**: Convert these from open-ended to confirmation prompts using confirmed detected values: Q1.4 (<- `BACKEND_FRAMEWORK`), Q1.5 (<- `FRONTEND_FRAMEWORK`), Q1.6 (<- `DATABASE`), Q1.9 (<- `BACKEND_TEST`/`FRONTEND_TEST`).

    5. **Fallback**: No dependency files or ambiguous detection -> standard manual entry for that field. Only pre-fill high-confidence values.

4c. **Conditional-stack population**: resolve template placeholders in `conventions.md` using the questionnaire answers, applying stack-presence conditionality. The four modes this step handles are: **full-stack** (backend + frontend both present), **API-only** (backend present, `FRONTEND_FRAMEWORK == none`), **frontend-only** (frontend present, `BACKEND_FRAMEWORK == none`), and **CLI / library** (both `none`).

   1. If the user answered `framework: none` for backend, omit every `BACKEND_*` row from the generated `conventions.md` -- including the backend-parented i18n variable `I18N_BACKEND_CATALOGS` -- and note internally that smoke-test infrastructure (added by a later step in this flow) and backend rules (likewise) will be skipped. (Covers API-absent cases: frontend-only and CLI / library.)
   2. If the user answered `framework: none` for frontend, omit every `FRONTEND_*` row, the `FRONTEND_I18N_DIR` row, and the `I18N_FRONTEND_FILES` variable; frontend rules emission (likewise) will be skipped. (Covers frontend-absent cases: API-only and CLI / library.)
   3. If both are `none` (pure CLI or library project), emit a minimal valid `conventions.md` containing only `PROJECT_NAME`, `PROJECT_DESCRIPTION`, `PROJECT_MODE`, `CODEBASE_DIR`, `OUTPUT_DIR`, and the `Directory Structure` variables. Both i18n catalog variables (`I18N_FRONTEND_FILES`, `I18N_BACKEND_CATALOGS`) are absent in this mode.
   4. Never emit template placeholders in the final file: every `{{VAR}}` must either be resolved from the questionnaire answers or its row omitted. A leftover placeholder is a bug, not a valid state.

   **i18n prompt gating (Section 1 questionnaire, step 4b).** `I18N_FRONTEND_FILES` is prompted only when frontend is present; `I18N_BACKEND_CATALOGS` is prompted only when backend is present. An API-only project with backend-translated emails still gets asked about `I18N_BACKEND_CATALOGS`. A frontend-only project with localized UI still gets asked about `I18N_FRONTEND_FILES`. A CLI / library project is asked about neither. The agent implements this gating while presenting Section 1 -- skip the prompt when its parent stack was answered `framework: none`.

   The `<!-- CONDITIONAL: ... -->` comments in `.claude/references/template/conventions.md` (added by a later step in this plan) are the machine-readable markers that drive the row-omission logic. Until those comments land, apply the conditionality by matching variable-name prefixes (`BACKEND_`, `FRONTEND_`, `I18N_FRONTEND_`, `I18N_BACKEND_`).

5. **Create output directory** (default: `_output/`) with subdirs `plans/`, `advisory-logs/`, `qa-logs/`, `check-logs/` and `briefs.md` header `# Briefs\n\nExecution log of all skill invocations.\n\n---\n`.

6. **Create settings.json**: copy `template/settings.json` to `.claude/settings.json` with default path values.

7. **Summary**: report file count by category copied.

7a. **Pin public-release tag**: resolve `--version` (see Version Pinning) and write to `<target>/.seja-version` (one line, no trailing whitespace). Workspace mode writes it in the workspace dir (where `.claude/` lives), not the codebase dir.

7c. **Scaffold CLAUDE.md** (anchor: `Scaffold-CLAUDE.md`). Generate a `CLAUDE.md` in the codebase root (embedded mode) or in the workspace root (workspace mode) carrying ONLY stack-dependent content at setup time:

   - **Project name** (from `PROJECT_NAME`) + one-line **project description** (from `PROJECT_DESCRIPTION`).
   - **Stack summary**: the answered frameworks as bullets (e.g. `Backend: flask`, `Frontend: react`, `Database: postgresql`); omit the row for any stack the user answered `framework: none`.
   - **Build/run commands** derived from the chosen frameworks (e.g. `flask run` / `npm run dev` / `pytest` / `npm test`). Use the framework slug's canonical entry points; do not invent commands for stacks that are not present.
   - **Architecture overview**, emitted conditionally per stack presence:
     - `## Backend Architecture Summary` -- emit only when `BACKEND_FRAMEWORK != none`. One paragraph describing backend layout (directory, ORM, validation, auth) sourced from `conventions.md`.
     - `## Frontend Architecture Summary` -- emit only when `FRONTEND_FRAMEWORK != none`. One paragraph describing frontend layout (directory, build tool, state, router, data fetching) sourced from `conventions.md`.
     - **i18n block** -- emit only when at least one i18n catalog applies (`I18N_FRONTEND_FILES` present when frontend exists, or `I18N_BACKEND_CATALOGS` present when backend exists); otherwise omit entirely.
     - **Pure CLI fallback** -- when both `BACKEND_FRAMEWORK == none` AND `FRONTEND_FRAMEWORK == none`, emit a short `## Project Shape` paragraph acknowledging the project is not a web app (CLI / library / toolkit) and pointing the reader to `product-design/conventions.md` for directory layout.
   - **`@`-references** (stack-time only): `@.claude/rules/` (directory reference surfaces scoped rules) and `@product-design/conventions.md`.
   - **EXPLICITLY OMIT** design-intent `@`-references at setup time: do NOT emit `@product-design/product-design-as-intended.md`, `@product-design/ux-research-results.md`, `@product-design/standards.md`, `@product-design/design-standards.md`, `@product-design/security-checklists.md`, or `@product-design/constitution.md`. Those are amended later by `/design` (Mode 1 step 8 "Amend CLAUDE.md").

   Anchor name: `Scaffold-CLAUDE.md`. Referenced by `/design` Update when the stack flips.

7d. **Scaffold `.claude/rules/`** (anchor: `Scaffold-Rules`). Generate the stack-flavored rule files in `.claude/rules/` based on the stack answers captured in step 4b (and pre-filled from 4b.i when brownfield). Each rule's own `## Scope` block (file-path-scoped rule convention) is preserved unchanged by the move; this step only selects which rule files to emit and writes them.

   Emission conditions:

   - `rules/harness-structure.md` -- always emitted (stack-independent; it is the harness's own inventory rule and ships with every project).
   - `rules/backend-*.md` -- emitted only when `BACKEND_FRAMEWORK != none`. Pick the rule file flavored for the chosen backend slug (e.g. `backend-flask.md`, `backend-fastapi.md`, `backend-django.md`, `backend-express.md`, `backend-nestjs.md`, `backend-rails.md`); if no per-slug rule exists for the answered framework, emit the generic backend rule and log a one-line note that a stack-specific rule is not yet available.
   - `rules/frontend-*.md` -- emitted only when `FRONTEND_FRAMEWORK != none`. Pick the rule file flavored for the chosen frontend slug (e.g. `frontend-react.md`, `frontend-vue.md`, `frontend-svelte.md`, `frontend-angular.md`); same generic-fallback behaviour as backend.
   - **Testing rules** -- emitted conditionally on the T-tier testing-tool answers from Section 1 (e.g. `testing-pytest.md`, `testing-jest.md`, `testing-vitest.md`, `testing-playwright.md`). Emit only the rule files matching the tools the user confirmed; skip rules for absent tools.
   - **i18n rules** -- emitted conditionally on the T-tier locale answers. Skip entirely when neither `I18N_FRONTEND_FILES` nor `I18N_BACKEND_CATALOGS` applies (consistent with the CLAUDE.md i18n-block condition in step 7c).
   - **Security rules** -- emitted conditionally on the T-tier security-constraint answers (validation library, auth model, rate-limit posture). Omit rule files whose prerequisite constraints were not declared.

   Pure-CLI / library projects (`BACKEND_FRAMEWORK == none` AND `FRONTEND_FRAMEWORK == none`) receive only `rules/harness-structure.md` plus any testing rules matching their declared test runner -- no backend, frontend, i18n, or web-auth rules.

   Preserve the file-path-scoped rule convention: the `## Scope` header inside each emitted rule is copied verbatim from the source template; `/seja-setup` does not rewrite rule bodies, it only selects which rule files to place in `.claude/rules/`.

   Anchor name: `Scaffold-Rules`. Referenced by `/design` Update when the stack flips.

7e. **Scaffold smoke-test infrastructure** (anchor: `Scaffold-SmokeTestInfra`). Generate the smoke-test files in the target (or workspace) root. Emission is gated entirely on backend presence:

   - **Skip entirely when `BACKEND_FRAMEWORK == none`.** Pure frontend-only projects and pure-CLI / library projects receive no smoke-test scaffolding at all. Do not emit `smoke_test_registry.json`, `smoke_test_api.py`, or any `e2e/` directory when there is no backend.
   - When `BACKEND_FRAMEWORK != none`, emit these files:
     - `smoke_test_registry.json` -- instantiated from `.claude/references/template/smoke-test-registry.json` with the backend stack's canonical smoke-test entries.
     - `smoke_test_api.py` -- thin runner importing `smoke_test_core`; wire it to the chosen backend framework's entry point so the registry can be invoked against a running instance.
     - `e2e/smoke.spec.ts` -- emit ONLY when BOTH `FRONTEND_FRAMEWORK != none` AND an E2E tool was chosen in Section 1 (e.g. `playwright`, `cypress`). Omit when frontend is `none` (no browser target) or when no E2E tool was declared (the T-tier testing answer did not include E2E). The generated spec file carries the canonical smoke-test shape for the chosen E2E tool.

   Anchor name: `Scaffold-SmokeTestInfra`. Referenced by `/design` Update when the stack flips.

7b. **Initial commit**: `git add . && git commit -m "chore: set up SEJA harness"` in the target (or workspace) dir. Workspace+greenfield (2b created both): commit in both. Demo mode: this step runs after step 10 (so the commit includes demo files), not after 7. If `git commit` fails (git user.name/email unconfigured), warn and continue -- do not abort.

8. **Handoff**: report the scaffolded stack summary and direct the user to `/design` for design-intent concerns. Construct the summary from the questionnaire answers: use the literal framework slugs for present stacks (e.g. `flask`, `react`) and the string `no backend` or `no frontend` when the user answered `framework: none`.

   > Your project has been set up at `<target>`. Stack scaffolded (`<backend-or-"no backend">` + `<frontend-or-"no frontend">`).
   >
   > Next steps:
   >
   > 1. Open a new Claude Code session in `<target>` (or workspace directory if separated).
   > 2. Run `/design` to define entities, permissions, metacommunication, personas, and standards.
   > 3. The source repository is no longer needed for day-to-day work -- return to it only for harness development.

## Stack-Presence Modes (Test Fixtures)

The Standard Install Flow and `--here` Flag both handle four stack-presence modes. Each mode has an expected scaffolded file set; the table below is the machine-reviewable contract that future manual verification runs against. For each mode, `/seja-setup <target>` is invoked with Section 1 answers as shown; the expected post-invocation tree under `<target>` (or cwd for `--here`) is enumerated.

| Mode | Section 1 answers | conventions.md rows | CLAUDE.md sections | .claude/rules/ | Smoke-test files |
|------|-------------------|---------------------|--------------------|----------------|------------------|
| **Full-stack** | `BACKEND_FRAMEWORK=<slug>`, `FRONTEND_FRAMEWORK=<slug>` | `PROJECT_*`, `CODEBASE_DIR`, `OUTPUT_DIR`, all `BACKEND_*`, all `FRONTEND_*`, `I18N_FRONTEND_FILES` (if answered), `I18N_BACKEND_CATALOGS` (if answered) | name + description + stack summary (both rows) + build/run (both stacks) + `## Backend Architecture Summary` + `## Frontend Architecture Summary` + i18n block (if any catalog) | `harness-structure.md` + `backend-<slug>.md` + `frontend-<slug>.md` + testing / i18n / security rules per answers | `smoke_test_registry.json` + `smoke_test_api.py`; `e2e/smoke.spec.ts` only if E2E tool declared |
| **API-only** (backend present, `FRONTEND_FRAMEWORK=none`) | `BACKEND_FRAMEWORK=<slug>`, `FRONTEND_FRAMEWORK=none` | `PROJECT_*`, `CODEBASE_DIR`, `OUTPUT_DIR`, all `BACKEND_*`, `I18N_BACKEND_CATALOGS` (if answered). No `FRONTEND_*`, no `FRONTEND_I18N_DIR`, no `I18N_FRONTEND_FILES`. | name + description + backend stack row (no frontend row) + backend build/run + `## Backend Architecture Summary` + backend-only i18n block if `I18N_BACKEND_CATALOGS` present. No frontend section. | `harness-structure.md` + `backend-<slug>.md` + backend testing / backend security rules. No `frontend-*.md`, no i18n-frontend rules. | `smoke_test_registry.json` + `smoke_test_api.py`. No `e2e/` directory (frontend absent). |
| **Frontend-only** (frontend present, `BACKEND_FRAMEWORK=none`) | `BACKEND_FRAMEWORK=none`, `FRONTEND_FRAMEWORK=<slug>` | `PROJECT_*`, `CODEBASE_DIR`, `OUTPUT_DIR`, all `FRONTEND_*`, `I18N_FRONTEND_FILES` (if answered). No `BACKEND_*`, no `I18N_BACKEND_CATALOGS`. | name + description + frontend stack row (no backend row) + frontend build/run + `## Frontend Architecture Summary` + frontend-only i18n block if `I18N_FRONTEND_FILES` present. No backend section. | `harness-structure.md` + `frontend-<slug>.md` + frontend testing rules. No `backend-*.md`, no backend auth/validation security rules. | None. Step 7e skipped entirely (no backend). |
| **CLI / library** (both `none`) | `BACKEND_FRAMEWORK=none`, `FRONTEND_FRAMEWORK=none` | Minimal valid: `PROJECT_NAME`, `PROJECT_DESCRIPTION`, `PROJECT_MODE`, `CODEBASE_DIR`, `OUTPUT_DIR`, Directory Structure variables only. Neither `I18N_FRONTEND_FILES` nor `I18N_BACKEND_CATALOGS`. | name + description + `## Project Shape` pure-CLI fallback paragraph pointing to `product-design/conventions.md`. No stack-summary rows, no architecture summary, no i18n block. | `harness-structure.md` + testing rules matching the declared test runner (if any). No backend / frontend / i18n / web-security rules. | None. Step 7e skipped entirely (no backend). |

**Invariant across all four modes**: no unresolved `{{VAR}}` placeholders remain in `product-design/conventions.md`. The Handoff message (Standard Install step 8, `--here` Step 8) reports present stacks by slug and absent stacks as the literal `no backend` / `no frontend`. For the CLI / library mode the handoff reports `no backend` + `no frontend`.

**Manual verification procedure**: for each mode, run `/seja-setup /tmp/test-<mode>` (or `/seja-setup --here` in a `git clone`d cwd), answer Section 1 per the first column, and compare the produced tree against the remaining columns. Any deviation is a bug against this contract.
