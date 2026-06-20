---
name: seja-setup-here-internal
description: "Inlined worker for /seja-setup --here Flag (Finalise in place). Not user-invocable."
compatibility: "Designed for Claude Code with the SEJA harness"
metadata:
  internal: true
  category: internal
  version: 1.0.0
---

> This is an inlined worker; execute these instructions as part of the caller's flow. The wrapper at `.claude/skills/seja-setup/SKILL.md` has already run the Entry-Point Routing dispatch; execute the steps below as part of the `/seja-setup` skill's flow.

## --here Flag

> **Incompatible with `--workspace`, `--demo`, and `--upgrade`.** If combined, reject with "`--here` cannot be combined with `--workspace`, `--demo`, or `--upgrade`. Use `--here` alone to finalise SEJA setup in the current directory." Then exit.

Does NOT copy harness files (they are already in cwd from a direct clone). Finalises in place: pins version, scaffolds output + project dirs, prompts for git-history handling + cleanup, creates initial commit.

### Step 1 -- State detection

`python .claude/skills/seja-setup/detect_setup_state.py --json` in cwd. Parse into `state`, `signals`, `recommendation`.

### Step 2 -- State-based dispatch

| State | Action |
|-------|--------|
| `dev-repo-refuse` | Hard-abort with the refusal message from `## Entry-Point Routing` (cites `signals.git_remote_url`, `signals.has_seja_public_subtree`, `signals.has_dev_scripts`). Exit without mutation. |
| `public-clone-soft-confirm` | AskUserQuestion: **Yes, continue** (short-form: Recommended when this folder is intended to become your project) -> Step 3; **No, cancel** -> abort. |
| `finalised` | AskUserQuestion: **Upgrade instead** -- Recommended when you want to refresh harness files without touching project data. NOT recommended when you intend to reset everything and start over. Action: `## Upgrade Flow`, exit this invocation. **Re-run setup anyway** -- Recommended when you want to start over destructively (re-runs init on top of existing files). NOT recommended when the project is in active use and the reset is unsure. Action: Step 3. **Cancel** -- Recommended when you want to investigate before acting. |
| `fresh-download` or `partial-init` | Proceed directly to Step 3. |

### Step 3 -- Version pin capture (pre-mutation)

Run `git describe --tags --exact-match HEAD` in cwd. On success, use the returned tag (e.g. `v0.1.0`) as the pin. On failure, use the literal string `HEAD` and warn: "Warning: HEAD is not at an exact-match tag. Recording `HEAD` in .seja-version. `/seja-setup --upgrade` will use this as the baseline for future refreshes but may not resolve relative deltas cleanly." Hold the value in memory for Step 4.

### Step 4 -- Init phase (create files)

Create in cwd, in order:

1. `_output/` with subdirs `plans/`, `advisory-logs/`, `qa-logs/`, `check-logs/`.
2. `_output/briefs.md` with header `# Briefs\n\nExecution log of all skill invocations.\n\n---\n`.
3. Empty `product-design/` (ready for `/design` to populate).
4. Copy `.claude/references/template/settings.json` -> `.claude/settings.json` (skip if exists; never overwrite user settings).
5. Write `.seja-version` with the Step 3 value (one line, no trailing whitespace).

If any target already exists (common in `partial-init`), log and skip rather than overwrite. Goal is reconciliation, not replacement.

### Step 4b -- Scaffolding questionnaire (populate conventions.md)

Run the Section 1 basic-definitions scaffolding questionnaire against cwd, using the same logic as Standard Install Flow step 4b + 4c:

1. Run `.claude/references/template/questionnaire.md` with `section-include: "stack-only"` (Q 0.1 metacomm-message + all of Section 1). Gate the i18n prompts on parent-stack presence as in Standard Install step 4c: `I18N_FRONTEND_FILES` only when frontend is present; `I18N_BACKEND_CATALOGS` only when backend is present.
2. Instantiate `product-design/conventions.md` from `.claude/references/template/conventions.md` using the answers, applying the same conditional-stack population rules from Standard Install Flow step 4c -- all four modes (full-stack, API-only, frontend-only, CLI / library) handled: omit `BACKEND_*` rows (including `I18N_BACKEND_CATALOGS`) when `framework: none` for backend; omit `FRONTEND_*` rows, `FRONTEND_I18N_DIR`, and `I18N_FRONTEND_FILES` when `framework: none` for frontend; emit a minimal valid file when both are `none`; never leave an unresolved `{{VAR}}` placeholder.

**Brownfield pre-fill**: before presenting Section 1, run the same auto-detection sub-step as Standard Install Flow step 4b.i (scan `${CODEBASE_DIR}` for `package.json`, `requirements.txt`, `pyproject.toml`, etc.; map detected dependencies to `BACKEND_FRAMEWORK`, `FRONTEND_FRAMEWORK`, `DATABASE`, `BACKEND_TEST`/`FRONTEND_TEST`, directory vars; present confirmation prompts for Q1.4, Q1.5, Q1.6, Q1.9). Fall back to standard manual entry for ambiguous or undetected fields.

This step closes the first-run gap symmetrically for users who ran `git clone https://github.com/simonedjb/seja my-project` and then `/seja-setup --here`: they now end up with a populated `conventions.md` in one invocation rather than having to run `/design` afterwards just to get a bootable stack scaffold.

When `product-design/conventions.md` already exists and is fully populated (no `{{VAR}}` placeholders), skip this step rather than re-prompt -- reconciliation-first semantics apply here as elsewhere in `--here`.

### Step 4c -- Scaffold CLAUDE.md

Apply the `Scaffold-CLAUDE.md` anchor body from Standard Install Flow step 7c against cwd. Same semantics: scaffolded CLAUDE.md carries project name, stack summary, build/run commands, conditional architecture summaries (Backend / Frontend / pure-CLI fallback), conditional i18n block, and `@`-references to `.claude/rules/` and `product-design/conventions.md` -- explicitly OMIT design-intent `@`-references. If `CLAUDE.md` already exists in cwd (common for `partial-init` or a prior `--here` reconciliation), skip rather than overwrite; `/design` will amend it in place afterwards.

### Step 4d -- Scaffold `.claude/rules/`

Apply the `Scaffold-Rules` anchor body from Standard Install Flow step 7d against cwd. Same semantics: emit `rules/harness-structure.md` unconditionally; emit `rules/backend-*.md` only when `BACKEND_FRAMEWORK != none`; emit `rules/frontend-*.md` only when `FRONTEND_FRAMEWORK != none`; emit testing, i18n, and security rules conditionally per Section 1 T-tier answers. Preserve each rule's `## Scope` block verbatim. If `.claude/rules/` already contains the matching rule files (a prior `--here` reconciliation populated them), skip rather than overwrite. Stack-specific rule selection reuses the slug answered (or pre-filled) in Step 4b.

### Step 4e -- Scaffold smoke-test infrastructure

Apply the `Scaffold-SmokeTestInfra` anchor body from Standard Install Flow step 7e against cwd. Same semantics: skip entirely when `BACKEND_FRAMEWORK == none`; otherwise emit `smoke_test_registry.json` and `smoke_test_api.py` in cwd, plus `e2e/smoke.spec.ts` only when BOTH `FRONTEND_FRAMEWORK != none` AND an E2E tool was chosen in Section 1. If the smoke-test files already exist (a prior `--here` reconciliation populated them), skip rather than overwrite. Stack decisions reuse the slug answered (or pre-filled) in Step 4b.

### Step 5 -- Git history handling

AskUserQuestion (two-line rationale; trade-offs are non-obvious):

- **Re-init fresh** -- Recommended when the project's history starts here -- SEJA's history is not yours. NOT recommended when you intend to fork and track upstream SEJA changes. Action: REQUIRE a second confirmation (see safeguard below) before `rm -rf .git && git init`.
- **Keep history and add a project remote** -- Recommended when you intend to fork and track upstream SEJA changes. NOT recommended when you do not want SEJA's history in your project repo. Action: prompt for the project's git remote URL, then `git remote rename origin upstream && git remote add origin <url>`.
- **Leave as-is** -- Recommended for throwaway exploration that you will not push to a remote. NOT recommended when setting up a long-lived project.

**Critical safeguard**: never auto-delete `.git`. **Re-init fresh** MUST issue a second free-text confirmation (NOT AskUserQuestion -- prevents muscle-memory click-through):

> "This will delete SEJA's git history permanently. Type 'confirm' to proceed, or cancel."

Only proceed with `rm -rf .git && git init` if the user types exactly `confirm` (case-insensitive). Any other input (including "yes", "ok", Enter with no text) -> abort the git-history action and leave `.git` intact.

### Step 6 -- Cleanup artefacts

Inspect cwd first; absent artefacts must NOT appear in the prompt -- only list rows for files that exist.

Present a single multi-select AskUserQuestion titled "Which harness-dev artefacts should I clean up?" with defaults preselected so the user can accept-all or customise. Nothing is silently deleted or moved; the submission confirms the batch.

| Artefact | Default action | Alternative actions |
|----------|----------------|---------------------|
| `docs/` | Move to `docs/seja/` | Keep in place / Remove |
| SEJA's `README.md` | Rename to `SEJA-README.md` | Keep as-is / Remove |
| SEJA's `CHANGELOG.md` | Rename to `SEJA-CHANGELOG.md` | Keep as-is / Remove |
| `LICENSE`, `TRADEMARKS.md` | Keep in place | Remove (warn about attribution) |
| `.github/workflows/sync-public.yml` | Remove | Keep |
| `.githooks/` | Remove | Keep |

**Per-option rationale** (surface in the AskUserQuestion descriptions when non-obvious):

- `docs/` -> `docs/seja/`: preserves SEJA contextual help under a namespaced subdir, freeing `docs/` for project docs. Recommended when authoring project docs under `docs/`. NOT recommended when discarding SEJA docs entirely (choose Remove).
- `README.md` / `CHANGELOG.md` rename: keeps SEJA attribution while freeing the name for your project. Recommended when authoring your own. NOT recommended when preserving SEJA's as-is (choose Keep as-is).
- `LICENSE`, `TRADEMARKS.md`: keeping preserves attribution; removing may violate license terms (alternative action surfaces a warning first).
- `sync-public.yml` workflow + `.githooks/`: harness-publication checks consumers do not need; default Remove.

Apply chosen actions sequentially; log each rename/move before executing.

### Step 7 -- Initial commit

`git add . && git commit -m "chore: finalise SEJA setup in place (plan-000392)"` in cwd. If it fails (git user.name/email unconfigured, or Re-init fresh already produced an initial commit), warn and continue to handoff -- do not abort.

### Step 8 -- Handoff

Report the scaffolded stack summary, then direct to `/design`. Stack-aware: render present frameworks as their slug (e.g. `flask`, `react`) and absent stacks as `no backend` / `no frontend`.

> Your SEJA setup has been finalised in `<cwd>`. Stack scaffolded (`<backend-or-"no backend">` + `<frontend-or-"no frontend">`).
>
> Next steps:
>
> 1. Run `/design` to define entities, permissions, metacommunication, personas, and standards.
> 2. Once `/design` completes, you are ready to run `/research`, `/plan`, `/implement`, and the other SEJA skills.
> 3. `.seja-version` is pinned to `<version>` -- `/seja-setup --upgrade` will use this as the baseline next time you want to refresh harness files.
