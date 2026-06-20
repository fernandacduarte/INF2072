---
designer_description: "I'm your project's single source of truth for directory structure, file paths, stack, test commands, validation thresholds, and the registry of as-intended and as-coded files -- every other reference file and every skill reads me to stay in sync, so when you change a path or a framework choice here, the whole system follows from one edit instead of a hunt across the repository."
---

# TEMPLATE - PROJECT CONVENTIONS

> **How to use this template:** Copy this file to `project/conventions.md` and fill in the values for your project. This is the first file to customize — all other reference files and skills reference variables defined here.
>
> Centralized project-specific definitions. All skills and reference files reference variables from this file instead of hardcoding project-specific values. To adapt the skill system to a different project, edit only this file.

---

## Project Identity

| Variable | Value | Description |
|----------|-------|-------------|
| `PROJECT_NAME` | {{PROJECT_NAME}} | Project display name |
| `PROJECT_DESCRIPTION` | {{PROJECT_DESCRIPTION}} | One-line project description |
| `PROJECT_MODE` | {{PROJECT_MODE}} | Project mode: greenfield (new project) or brownfield (existing codebase) |

---

## Directory Structure

> **Absolute path support:** Variable values can be absolute paths (e.g., `D:/workspaces/my-project/_output`). Python's `Path` joining treats absolute paths as anchors, overriding relative-to-root resolution. This enables the workspace deployment pattern where output and source directories live outside the harness root.

| Variable | Value | Description |
|----------|-------|-------------|
| `SKILLS_DIR` | `.claude/skills` | Root directory for skill definitions |
| `AGENT_SPECS_DIR` | `project/agent` | Agent-facing structured specifications in YAML (in `product-design/`) |
| `OUTPUT_DIR` | `_output` | Root directory for all generated artifacts |
| `PLANS_DIR` | `${OUTPUT_DIR}/plans` | Plan output folder |
| `SCRIPTS_DIR` | `${OUTPUT_DIR}/generated-scripts` | Script output folder |
| `ADVISORY_DIR` | `${OUTPUT_DIR}/advisory-logs` | Legacy advisory log output folder -- preserved for historical artifacts; new /research outputs go to `${RESEARCH_DIR}`. See advisory-000448. |
| `RESEARCH_DIR` | `${OUTPUT_DIR}/research-logs` | Research log output folder (new /research outputs land here; see advisory-000448) |
| `PROPOSALS_DIR` | `${OUTPUT_DIR}/proposals` | Lightweight change proposals |
| `INVENTORIES_DIR` | `${OUTPUT_DIR}/inventories` | Inventory output folder |
| `USER_TESTS_DIR` | `${OUTPUT_DIR}/user-tests` | User test plan output folder |
| `EXPLAINED_BEHAVIORS_DIR` | `${OUTPUT_DIR}/explained-behaviors` | Behavior explanation output folder |
| `EXPLAINED_CODE_DIR` | `${OUTPUT_DIR}/explained-code` | Code explanation output folder |
| `EXPLAINED_DATA_MODEL_DIR` | `${OUTPUT_DIR}/explained-data-model` | Data model explanation output folder |
| `EXPLAINED_ARCHITECTURE_DIR` | `${OUTPUT_DIR}/explained-architecture` | Architecture explanation output folder |
| `BEHAVIOR_EVOLUTION_DIR` | `${OUTPUT_DIR}/behavior-evolution` | Behavior evolution explanation output folder |
| `REFLECTIONS_DIR` | `${OUTPUT_DIR}/reflections` | Reflection report output folder |
| `ONBOARDING_PLANS_DIR` | `${OUTPUT_DIR}/onboarding-plans` | Onboarding plan output folder |
| `COMMUNICATION_DIR` | `${OUTPUT_DIR}/communication` | Communication material output folder |
| `ROADMAP_DIR` | `${OUTPUT_DIR}/roadmaps` | Roadmap output folder |
| `QA_LOGS_DIR` | `${OUTPUT_DIR}/qa-logs` | QA session log output folder |
| `CHECK_LOGS_DIR` | `${OUTPUT_DIR}/check-logs` | Check/preflight/review output folder |
| `TMP_DIR` | `${OUTPUT_DIR}/tmp` | Temporary/helper scripts |
| `CODEBASE_DIR` | {{CODEBASE_DIR}} | Root directory of the project codebase (`.` for embedded, absolute path for workspace mode) |

---

## Key Files

| Variable | Value | Description | Maintained by |
|----------|-------|-------------|-------------- |
| `BRIEFS_FILE` | `${OUTPUT_DIR}/briefs.md` | Execution log of all skill invocations | Agent |
| `BRIEFS_INDEX_FILE` | `${OUTPUT_DIR}/briefs-index.md` | Lightweight briefs index (one-line summaries) | Agent |
| `ARTIFACT_INDEX_FILE` | `${OUTPUT_DIR}/INDEX.md` | Single global artifact index (no per-folder INDEX.md files) | Agent |
| `CONSTITUTION_FILE` | `project/constitution.md` | Project constitution -- immutable principles (in `product-design/`) | Human |
| `AS_CODED` | `project/product-design-as-coded.md` | Unified implementation state: Conceptual Design, Metacommunication, Journey Maps (in `product-design/`) | Agent |
| `CD_AS_IS_CHANGELOG` | `project/product-design-changelog.md` | As-built conceptual design changelog (in `product-design/`) | Agent |
| `DESIGN_INTENT` | `project/product-design-as-intended.md` | Unified working intent (§0-§17) + DRR Decision log (## Decisions) + CHANGELOG (in `product-design/`) | Human (markers) |
| `DESIGN_INTENT_TO_BE` | `project/product-design-as-intended.md` | Legacy alias for `DESIGN_INTENT` (workspace-mode backward compat; see plan-000268 Amendment A6) | Human (markers) |
| `UX_RESEARCH` | `project/ux-research-results.md` | UX research: personas, problem scenarios, journeys, processing status, CHANGELOG (in `product-design/`) | Human (markers) |
| `STANDARDS` | `project/standards.md` | Unified engineering standards: Backend, Frontend, Testing, i18n (in `product-design/`) | Human / Agent |
| `DESIGN_STANDARDS` | `project/design-standards.md` | Unified design standards: UX patterns and graphic/visual design (in `product-design/`) | Human / Agent |
| `SESSION_NOTES_FILE` | `${TMP_DIR}/session-notes.md` | Session-scoped working memory for structured note-taking | Agent |
| `DECISION_DIGEST_FILE` | `${OUTPUT_DIR}/decision-digest.jsonl` | Machine-readable decision index (one JSON line per design decision) | Agent |
| `CONVERSATION_TRACE_FILE` | `${OUTPUT_DIR}/conversation-trace.jsonl` | Append-only conversation trace log (per-utterance exchanges with session and event-chain linkage) | Agent |

---

## As-Intended / As-Coded Registry

> Canonical list of all as-intended files and their as-coded counterparts in this project.
> Read by `/design` (template generation), `/explain spec-drift` (drift checking),
> and post-skill (DONE marking proposals). Add a row when a new as-intended file
> is introduced. `as-coded` is optional -- set to `-` if not applicable (e.g., research-only files).
> The Section column identifies which portion of a file corresponds to each registry row when a file hosts multiple artifact types. Tools that scan for drift use the ID prefix (JM-TB-NNN for designed journeys, JM-E-NNN for discovered journeys) to discriminate artifact types within the same file.
>
> **Lifecycle markers**: the pre-2.8.3 harness tracked a separate "established" file per registered row. Post-merge, the `STATUS: established` lifecycle state is recorded inline in the as-intended file (on Decision entries and §15 journeys) rather than in a separate file -- no registry column is required.

| As-Intended file | Section | As-Coded counterpart |
| ---------------- | ------- | -------------------- |
| `${DESIGN_INTENT}` | §0-§17 design intent + Decisions + CHANGELOG | `${AS_CODED}` |
| `${DESIGN_INTENT}` | §15 designed journeys | `${AS_CODED} § Journey Maps` |
| `${UX_RESEARCH}` | all (personas, scenarios, journeys, CHANGELOG) | `-` |

---

## Review Configuration

| Variable | Value | Description |
|----------|-------|-------------|
| `MINIMUM_REVIEW_DEPTH` | `{{MINIMUM_REVIEW_DEPTH}}` | Minimum review depth floor. Valid values: `light`, `standard`, `deep`. The automatic complexity gate and per-call flags can only raise the depth above this floor, never lower it. Depth ordering: light < standard < deep. Default: `light`. |

---

## Periodic Triggers

> Configurable intervals for the `pending-check` pre-skill stage's lazy periodic-action creation. Read by `pending.py periodic-check` at skill invocation time. Empty or missing intervals disable the corresponding trigger.

| Trigger | Interval (days) | Action type | Description |
|---------|-----------------|-------------|-------------|
| Periodic curation | 30 | `periodic-curation` | Review `product-design-as-intended.md` for items ready to promote from `implemented` to `established` |
| Spec-drift check | 14 | `spec-drift-check` | Run `/explain spec-drift` to surface drift between design intent and as-coded state |
| Git freshness check | 7 | `check-git-freshness` | Compare each project git repo to its upstream; surface behind/ahead counts. Resolve via `/check freshness`. Default: 7; blank to disable. |

| Threshold | Value | Description |
|-----------|-------|-------------|
| Pending plan age escalation | 30 | Days before an open `implement` pending entry is surfaced with the overdue banner in pre-skill (parallel to the publish-overdue banner). A plan generated via `/plan` but never run via `/implement` crosses this threshold silently; past this age, pre-skill escalates it on every skill invocation until the entry is addressed or dismissed. |
| Verify-as-coded file threshold | 5 | Minimum number of files changed by a plan before post-skill auto-creates a `verify-as-coded` pending action |
| Pending age escalation | 14 | Days before a pending action is flagged "overdue" in pre-skill notices |
| Pending auto-dismiss | 90 | Days after which unaddressed pending actions are auto-dismissed by `pending.py cleanup` |

---

## Source Directories

> Add one row per source directory in your project (e.g., backend, frontend, shared libraries, mobile).

| Variable | Value | Description |
|----------|-------|-------------|
<!-- CONDITIONAL: BACKEND_FRAMEWORK != none -->
| `BACKEND_DIR` | `{{BACKEND_DIR}}` | Backend source root |
<!-- CONDITIONAL: FRONTEND_FRAMEWORK != none -->
| `FRONTEND_DIR` | `{{FRONTEND_DIR}}` | Frontend source root |
<!-- CONDITIONAL: BACKEND_FRAMEWORK != none -->
| `BACKEND_FRAMEWORK` | `{{BACKEND_FRAMEWORK}}` | Backend framework identifier (e.g., `flask`, `fastapi`, `django`, `express`, `none`) |
<!-- CONDITIONAL: FRONTEND_FRAMEWORK != none -->
| `FRONTEND_FRAMEWORK` | `{{FRONTEND_FRAMEWORK}}` | Frontend framework identifier (e.g., `react`, `vue`, `angular`, `none`) |

---

## Stack Description

| Variable | Value | Description |
|----------|-------|-------------|
<!-- CONDITIONAL: BACKEND_FRAMEWORK != none -->
| `BACKEND_STACK` | {{BACKEND_STACK}} | Backend technology summary (e.g., "Flask + SQLAlchemy + PostgreSQL") |
<!-- CONDITIONAL: FRONTEND_FRAMEWORK != none -->
| `FRONTEND_STACK` | {{FRONTEND_STACK}} | Frontend technology summary (e.g., "React + TypeScript + Vite") |
| `TESTING_STACK` | {{TESTING_STACK}} | Testing technology summary (e.g., "pytest + Vitest + Playwright") |
| `DEPLOYMENT_STACK` | {{DEPLOYMENT_STACK}} | Deployment technology summary (e.g., "Docker + Caddy") |

---

## Architecture Description

| Variable | Value | Description |
|----------|-------|-------------|
| `ARCHITECTURE_DESCRIPTION` | {{ARCHITECTURE_DESCRIPTION}} | High-level architecture description |
| `ARCHITECTURE_PATTERN` | {{ARCHITECTURE_PATTERN}} | Architecture pattern (e.g., "3-layer: API / Service / Model") |
<!-- CONDITIONAL: BACKEND_FRAMEWORK != none -->
| `BACKEND_ARCHITECTURE_SUMMARY` | {{BACKEND_ARCHITECTURE_SUMMARY}} | Backend architecture summary for CLAUDE.md |
<!-- CONDITIONAL: FRONTEND_FRAMEWORK != none -->
| `FRONTEND_ARCHITECTURE_SUMMARY` | {{FRONTEND_ARCHITECTURE_SUMMARY}} | Frontend architecture summary for CLAUDE.md |
<!-- CONDITIONAL: BACKEND_FRAMEWORK != none -->
| `MODELS_DIR` | `${BACKEND_DIR}/app/models` | Database models directory |
| `CONVENTION_1` | {{CONVENTION_1}} | Key project convention #1 for CLAUDE.md |
| `CONVENTION_2` | {{CONVENTION_2}} | Key project convention #2 for CLAUDE.md |
| `CONVENTION_3` | {{CONVENTION_3}} | Key project convention #3 for CLAUDE.md |

---

## Backend Structure

| Variable | Value | Description |
|----------|-------|-------------|
<!-- CONDITIONAL: BACKEND_FRAMEWORK != none -->
| `BACKEND_APP_DIR` | `${BACKEND_DIR}/app` | Backend application root |
<!-- CONDITIONAL: BACKEND_FRAMEWORK != none -->
| `BACKEND_API_DIR` | `${BACKEND_APP_DIR}/api` | API blueprints/routes directory |
<!-- CONDITIONAL: BACKEND_FRAMEWORK != none -->
| `BACKEND_SCHEMAS_DIR` | `${BACKEND_APP_DIR}/schemas` | Marshmallow/validation schemas |
<!-- CONDITIONAL: BACKEND_FRAMEWORK != none -->
| `BACKEND_UTILS_DIR` | `${BACKEND_APP_DIR}/utils` | Backend utilities directory |
<!-- CONDITIONAL: BACKEND_FRAMEWORK != none -->
| `BACKEND_CONSTANTS_FILE` | `validation_constants.py` | Backend validation constants filename (resolved under BACKEND_UTILS_DIR) |
<!-- CONDITIONAL: BACKEND_FRAMEWORK != none -->
| `MIGRATIONS_DIR` | `${BACKEND_DIR}/migrations/versions` | Alembic migration files |
<!-- CONDITIONAL: BACKEND_FRAMEWORK != none -->
| `TRANSLATIONS_DIR` | `${BACKEND_DIR}/translations` | Flask-Babel translation catalogs |

---

## Frontend Structure

| Variable | Value | Description |
|----------|-------|-------------|
<!-- CONDITIONAL: FRONTEND_FRAMEWORK != none -->
| `FRONTEND_SRC_DIR` | `${FRONTEND_DIR}/src` | Frontend source root |
<!-- CONDITIONAL: FRONTEND_FRAMEWORK != none -->
| `FRONTEND_API_DIR` | `${FRONTEND_SRC_DIR}/api` | API client/type definitions |
<!-- CONDITIONAL: FRONTEND_FRAMEWORK != none -->
| `FRONTEND_UTILS_DIR` | `${FRONTEND_SRC_DIR}/utils` | Frontend utilities directory |
<!-- CONDITIONAL: FRONTEND_FRAMEWORK != none -->
| `FRONTEND_CONSTANTS_FILE` | `constants.ts` | Frontend validation constants filename (resolved under FRONTEND_UTILS_DIR) |
<!-- CONDITIONAL: FRONTEND_FRAMEWORK != none -->
| `FRONTEND_I18N_DIR` | `${FRONTEND_SRC_DIR}/i18n/locales` | i18n locale JSON files |

---

## i18n Configuration

| Variable                 | Value                       | Description                                                          |
|--------------------------|-----------------------------| ---------------------------------------------------------------------|
<!-- CONDITIONAL: FRONTEND_FRAMEWORK != none -->
| `I18N_FRONTEND_FILES`    | `{{I18N_FRONTEND_FILES}}`   | Comma-separated frontend locale filenames (e.g., `en-US.json,pt-BR.json`)  |
<!-- CONDITIONAL: BACKEND_FRAMEWORK != none -->
| `I18N_BACKEND_CATALOGS`  | `{{I18N_BACKEND_CATALOGS}}` | Comma-separated backend catalog names (e.g., `en_US,pt_BR`)          |

---

## Test Configuration

| Variable | Value | Description |
|----------|-------|-------------|
<!-- CONDITIONAL: BACKEND_FRAMEWORK != none -->
| `BACKEND_SUBPACKAGES` | `{{BACKEND_SUBPACKAGES}}` | Comma-separated backend subpackage names for coverage grouping |
<!-- CONDITIONAL: FRONTEND_FRAMEWORK != none -->
| `FRONTEND_SUBPACKAGES` | `{{FRONTEND_SUBPACKAGES}}` | Comma-separated frontend subpackage names for coverage grouping |
<!-- CONDITIONAL: FRONTEND_FRAMEWORK != none -->
| `FRONTEND_ENTRY_POINTS` | `{{FRONTEND_ENTRY_POINTS}}` | Comma-separated entry point filenames to exclude from unused-file checks |

---

## Secret Scanning

| Variable | Value | Description |
|----------|-------|-------------|
| `SECRETS_EXTRA_SKIP_PATTERNS` | `{{SECRETS_EXTRA_SKIP_PATTERNS}}` | Additional filename substrings to skip during secret scanning (comma-separated) |
| `SECRETS_EXTRA_SKIP_DIRS` | `{{SECRETS_EXTRA_SKIP_DIRS}}` | Additional directory names to skip during secret scanning (comma-separated) |
| `SECRETS_EXTRA_SKIP_EXTENSIONS` | `{{SECRETS_EXTRA_SKIP_EXTENSIONS}}` | Additional file extensions to skip during secret scanning (comma-separated, with dots) |
| `SECRETS_EXTRA_FALSE_POSITIVES` | `{{SECRETS_EXTRA_FALSE_POSITIVES}}` | Additional false-positive regex patterns (comma-separated, case-insensitive) |
| `SECRETS_EXTRA_PATTERNS` | `{{SECRETS_EXTRA_PATTERNS}}` | Additional secret-detection regex patterns (comma-separated, case-insensitive, auto-named) |

---

## Build & Test Commands

| Variable | Value | Description |
|----------|-------|-------------|
| `ALL_TESTS_CMD` | {{ALL_TESTS_CMD}} | Command to run all tests |
<!-- CONDITIONAL: BACKEND_FRAMEWORK != none -->
| `BACKEND_TEST_CMD` | {{BACKEND_TEST_CMD}} | Command to run backend tests |
<!-- CONDITIONAL: BACKEND_FRAMEWORK != none -->
| `BACKEND_INTEGRATION_TEST_CMD` | {{BACKEND_INTEGRATION_TEST_CMD}} | Command to run backend integration tests |
<!-- CONDITIONAL: BACKEND_FRAMEWORK != none -->
| `BACKEND_TEST_FILE_CMD` | {{BACKEND_TEST_FILE_CMD}} | Command to run a single backend test file |
<!-- CONDITIONAL: FRONTEND_FRAMEWORK != none -->
| `FRONTEND_TEST_CMD` | {{FRONTEND_TEST_CMD}} | Command to run frontend tests |
<!-- CONDITIONAL: FRONTEND_FRAMEWORK != none -->
| `FRONTEND_TEST_FILE_CMD` | {{FRONTEND_TEST_FILE_CMD}} | Command to run a single frontend test file |
<!-- CONDITIONAL: FRONTEND_FRAMEWORK != none -->
| `E2E_TEST_CMD` | {{E2E_TEST_CMD}} | Command to run E2E tests |
<!-- CONDITIONAL: BACKEND_FRAMEWORK != none -->
| `MIGRATION_CHAIN_SCRIPT` | {{MIGRATION_CHAIN_SCRIPT}} | Script to check migration chain integrity |

---

## Workspace Deployment

When using the foundational SEJA harness as a companion to an existing codebase, the recommended deployment pattern is:

- The **foundational SEJA harness** is available somewhere (as a cloned repo) -- it is the single source of truth for all skills, scripts, templates, and references
- The ***ProjectName* workspace** is a standalone git repo containing `.claude/`, `product-design/`, and `_output/` -- created from the foundational harness via `/seja-setup --workspace` or `create_workspace.py`
- The ***ProjectName* codebase** is accessed via `claude --add-dir <codebase-path>` -- no harness files are added to it
- `OUTPUT_DIR` points inside the workspace (version-controlled alongside harness config and design decisions)
- `BACKEND_DIR` and `FRONTEND_DIR` point at the codebase via absolute paths
- Setup: `python .claude/skills/scripts/create_workspace.py --from <foundational-harness> --workspace <path> --target <codebase>`
- Update: `python .claude/skills/scripts/upgrade_harness.py --from <foundational-harness> --target <workspace>`
