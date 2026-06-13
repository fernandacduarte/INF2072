---
name: design
description: "Define or update project design — stack, conventions, domain model, conceptual design, and standards. Use when user mentions 'design', 'design project', 'configure project', 'update design', or 'project setup'."
argument-hint: "[--mode interview] [--generate-spec] [--add-docs] [spec-file-path]"
compatibility: "Designed for Claude Code with the SEJA harness"
metadata:
  last-updated: 2026-04-26 00:00 UTC
  version: 1.0.8
  category: planning
  context_budget: standard
  questionnaire_version: 7
  references:
    - general/report-conventions.md
    - general/review-perspectives.md
    - general/shared-definitions.md
---

> Overview: see [./SKILL-quickguide.md](./SKILL-quickguide.md)

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `[spec-file-path]` | No | Path to a pre-filled spec file for automated configuration |
| `--mode interview` | No | Run in Interview-Driven mode (Mode 5): conversational intake instead of fixed questionnaire |
| `--generate-spec` | No | Generate a blank spec skeleton to fill out offline |
| `--add-docs` | No | Jump directly to the Add Documentation Templates mode |
| `update <section-slug>` | No | When project design exists, go directly to the update flow for `<section-slug>` and skip the interactive menu. Valid slugs: `stack`, `conceptual`, `metacomm`, `backend-standards`, `frontend-standards`, `ux-standards`, `ui-standards`, `i18n`, `security`, `testing`, `constitution`, `full`. If the slug is invalid or missing, I list the valid slugs and fall back to the menu. |

# Design

> **`/seja-setup`** scaffolds topology-WHAT (stack, directory layout, CLAUDE.md, rules, smoke-test infra). **`/design`** defines design-intent-WHAT and WHY (entities, permissions, metacomm, personas, standards, constitution). **`/plan`** defines HOW to build it and WHY those hows. Setup creates, design refines, plan schedules.

## Overview

Manages `product-design/` design foundations: stack, conventions, conceptual design, metacommunication, standards. Serves initial configuration (after `/seja-setup`) and ongoing design evolution.

## Detection Logic

Dispatch on invocation arguments and the state of `product-design/` files:

| Condition | Route |
|---|---|
| `--mode interview` flag present | Mode 5 (Interview-Driven) |
| `--add-docs` passed | Mode 3 (Add Documentation Templates) |
| `--generate-spec` passed | Mode 4 (Generate Blank Spec) |
| Positional `update <slug>` + `product-design-as-intended.md` exists + slug valid | Design Update fast path: skip steps 1-2, jump to step 3 for the named section. See [Design Update CLI fast path](#design-update-project-definitions-exist). |
| Positional `update <slug>` but slug missing/invalid | Print valid slugs, fall back to interactive menu (do not abort) |
| Spec file path passed | Mode 2 (From Spec File) |
| `specs/design-in-progress.md` exists | Interrupted-session wins: read the `mode` field in that file and route to that mode's phase handler. Missing `mode` field is treated as `mode: 1` (backward compat for sessions interrupted before Mode 5 existed). For Mode 5, resume from the active `phase` field. For Mode 1, route to step 1 (resume-or-fresh prompt). |
| `conventions.md` exists AND `product-design-as-intended.md` does NOT exist AND no placeholders AND `BACKEND_FRAMEWORK` populated | **partial-design** state: route directly to Initial Design Mode 1 but start at Section 0 (metacomm) and skip Section 1 entirely (stack already answered by `/seja-setup`). Continue through Section 2 (conceptual-design), Sections 3-4 (design standards), Section 5+ (standards and docs). Mode 1 step 2 loads the questionnaire with `section-include: "design-intent-only"` (shortcut defined in `template/questionnaire.md § Parser directives`). |
| `conventions.md` exists AND `product-design-as-intended.md` does NOT exist AND (placeholders remain OR `BACKEND_FRAMEWORK` unpopulated) | Legacy pre-scaffolding fallback: route to Mode 1 step 5b's A4 legacy-fallback branch (re-run Section 1 inline). |
| `conventions.md` does not exist | Initial design -- present Mode Selection menu (full Section 0 + Section 1 + 2-5+ flow). |
| `product-design-as-intended.md` exists | **Design Update** -- show summary, offer update menu. |

Valid slugs: `stack`, `conceptual`, `metacomm`, `backend-standards`, `frontend-standards`, `ux-standards`, `ui-standards`, `i18n`, `security`, `testing`, `constitution`, `full`.

**Partial-design vs. Design Update**: partial-design applies to the post-`/seja-setup` bootstrap state (conventions.md populated by scaffolding, design-intent artifacts not yet authored); Design Update applies to fully-finalised projects where `product-design-as-intended.md` exists.

**Stack updates vs. initial stack scaffolding**: initial stack scaffolding (first-time `conventions.md` population + the `Scaffold-CLAUDE.md` / `Scaffold-Rules` / `Scaffold-SmokeTestInfra` anchors) goes through `/seja-setup`. Stack updates in finalised projects (swapping backend framework, adding or removing a frontend, etc.) go through `/design update stack` (or the interactive Update menu option 1). The Update flow re-invokes the three `Scaffold-*` anchors by name so the downstream artifacts stay consistent -- see Design Update step 5 ("Regenerate dependent files").

**Disambiguation precedence (Amendment A1)**: evaluate conditions top-to-bottom; the first match wins. An interrupted `specs/design-in-progress.md` session wins over partial-design (the user was mid-flight and should be offered resume-or-fresh). A conventions.md with `{{VAR}}` placeholders or an unpopulated `BACKEND_FRAMEWORK` wins over partial-design (legacy pre-scaffolding state requires the A4 inline Section 1 re-run before design intent can proceed).

---

## Mode 3: Add Documentation Templates

Triggered when `--add-docs` is passed.

1. **Verify project exists**: `project/conventions.md` must exist in `product-design/`, else abort "No project design found. Run `/design` first."

2. **Check existing docs**: If `project/docs/` already exists, list instantiated templates and ask "Some documentation templates are already set up. Add more, or replace all?"

3. **Present template checklist**: Read all `template/docs/*.md`. Extract `recommended` and `depends_on` from YAML frontmatter. Mark recommended templates with `(Recommended)`; templates whose `depends_on` matches the project's app type (from `project/design-standards.md § UX patterns`) with `(Suggested for your app type)`. Let the user multi-select.

4. **Instantiate selected templates**: Copy selected `template/docs/*.md` to `project/docs/`.

5. **Summary**: List instantiated templates and suggest: "Documentation templates added. Populate placeholders in each file. For contextual help, create one page per UI screen."

## Mode 4: Generate Blank Spec

1. **Create `specs/`** if missing.
2. **Generate the spec file**: Copy `template/project-spec.md` to `specs/project-spec-YYYY-MM-DD HH.MM UTC.md`.
3. **Output next steps**: "Spec file created at `<path>`. Fill in your choices (each field has inline comments; required fields marked). Then run `/design <spec-file-path>` to apply it."

---

## Dispatch

Once Detection Logic has resolved the active mode, read the corresponding internal SKILL.md via the Read tool (not the Skill tool -- to avoid re-entering dispatch) and execute its instructions inline as part of this skill's flow. Initial-design modes (1, 2, 5) do not invoke pre-skill; the Design Update internal owns its own pre-skill invocation (step 1 of the update branch). Field Classification and Versioning are defined above and remain in context for all internals.

| Mode | Internal SKILL.md path |
|------|------------------------|
| Mode 1: Interactive Questionnaire | `.claude/skills/_internal/design/questionnaire/SKILL.md` |
| Mode 2: From Spec File | `.claude/skills/_internal/design/from-spec/SKILL.md` |
| Mode 3: Add Documentation Templates | Inline (see above) |
| Mode 4: Generate Blank Spec | Inline (see above) |
| Mode 5: Interview-Driven | `.claude/skills/_internal/design/interview/SKILL.md` |
| Design Update | `.claude/skills/_internal/design/update/SKILL.md` |

---

## Field Classification

**Required (ask if missing)**: `name` (Project display name), `description` (what the app does), Backend `framework` (or explicit "none"), Frontend `framework` (or explicit "none").

**Required conceptual design (ask if missing)**: Entity hierarchy (Q2.3), Permission levels (Q2.6), Greenfield/evolving status (Q2.9), `PROJECT_MODE` (derived from Q2.9: greenfield -> `greenfield`, evolving -> `brownfield`), Metacommunication message (Final Step, or Q0.1).

**Additionally required for brownfield**: Existing tech stack (Q2.12), Migration constraints (Q2.13).

**Required with sensible defaults** (inform user of default if missing):

| Field | Default | Inference |
|---|---|---|
| `CODEBASE_DIR` | `.` | `.` for embedded, absolute path if workspace mode |
| `output_dir` | `_output` | Static |
| `backend` / `frontend` dir | `backend` / `frontend` | Static |
| `orm` | Inferred | SQLAlchemy for Flask/FastAPI; Django ORM for Django; Prisma for Express/NestJS |
| `database` | `PostgreSQL` | Static |
| `migrations` | Inferred | Alembic for SQLAlchemy; Django Migrations for Django ORM; Prisma Migrate for Prisma |
| `validation` | Inferred | Marshmallow for Flask; Pydantic for FastAPI; Django Forms for Django; Zod for Express/NestJS |
| `auth` | `JWT (HttpOnly cookies)` | Static |
| `primary_locale` | `en-US` | Static |
| `build_tool` | `Vite` | Vite for React/Vue/Svelte |
| `css` / `state` | `Tailwind CSS` / `React Context + hooks` | Static |
| `data_fetching` / `http_client` / `router` | `TanStack Query` / `Axios` / `React Router v7` | Router for React only |
| `backend_test` / `frontend_test` | Inferred | pytest/Jest by language; Vitest with Vite else Jest |
| `e2e` / `wcag` | `Playwright` / `AA` | Static |

**Optional (omit silently if not provided)**: `rich_text_editor`, `dark_mode`, `primary_color`, `secondary_color`, `sans_font`, `serif_font`, `context_providers`, `initial_components`, `secondary_locale`, `backend_default_locale`, `localized_emails`, `translatable_entities`, `access_token_expiry`, `refresh_token_expiry`, `rate_limit`, `file_uploads`, `import_export`, `integration_suite`, `e2e_base_url`, conceptual design details beyond Q2.3/2.6 (free-form), security validation constants (free-form).

---

## Versioning

- Current questionnaire version is declared in this skill's frontmatter (`questionnaire_version`) and in `template/questionnaire.md`.
- Spec files declare their version via the `version:` field on the first non-comment line. When versions differ, consult the Version History table in `template/questionnaire.md`.
- When adding new questions: (1) increment `questionnaire_version` in both this frontmatter and `template/questionnaire.md`; (2) add new fields to `template/project-spec.md`; (3) add a Version History entry; (4) add default values to the Field Classification table above.
