---
name: check
description: "Run quality checks: validation, code review, smoke tests, preflight, or harness health."
argument-hint: "<validate | review | smoke | preflight | health | test-plan | docs | freshness | telemetry | semiotic-inspection> [--depth <light|standard|deep>] [--source <path>] [scope]"
compatibility: "Designed for Claude Code with the SEJA harness"
metadata:
  last-updated: 2026-03-29 00:15:00
  version: 1.0.0
  category: analysis
  context_budget: heavy
  references:
    - general/report-conventions.md
    - project/standards.md
    - project/design-standards.md
    - project/security-checklists.md
    - general/review-perspectives.md
    - general/review-perspectives-index.md
    - general/review-log-template.md
---

> Overview: see [./SKILL-quickguide.md](./SKILL-quickguide.md)

## Arguments

| Mode | Description |
|------|-------------|
| `validate [scope]` | Run project validation scripts. Scope: `all`, `i18n`, `auth`, `migrations`, `constants`, `po`, `coverage`, `tests`, `spec` |
| `review [scope]` | Structured code review against quality perspectives. Scope: `staged`, file path, or directory path |
| `smoke [scope]` | Runtime smoke tests. Scope: `all`, `api`, `ui` |
| `preflight [scope]` | Combined validate + review in one pass (pre-merge checkpoint). Scope: `staged`, `all`, or directory path |
| `health` | Harness self-diagnosis and integrity check. Supports `--verbose`, `--source <path>` |
| `test-plan [brief]` | Generate a structured manual test plan for the given brief |
| `docs [--plugins LIST]` | Documentation consistency check. Supports `--plugins`, `--verbose`, `--filter` |
| `freshness` | Runtime git-freshness check for configured repos (workspace + codebase when distinct). Never pulls |
| `telemetry` | Usage analytics and skill invocation statistics from telemetry.jsonl |
| `semiotic-inspection [scope]` | SIM-based communicability evaluation. Scope: feature, page, flow, or `all` |

> One mode is required. Modes are mutually exclusive. Global flag: `--depth <light|standard|deep>` overrides review depth for `review` and `preflight`.

## Common Steps (all modes)

Shared execution pattern across the 10 modes. Each mode below names which common steps it uses; modes with mostly-unique content list their unique steps in full.

**C1. Pre-skill.** Run /pre-skill "check" $ARGUMENTS to add general instructions to the context window. Parse the first argument to determine the mode; remaining arguments are the scope.

**C2. Stack filtering** (validate + preflight only). Read `BACKEND_FRAMEWORK` and `FRONTEND_FRAMEWORK` from `product-design/conventions.md` (via `project_config.py`), then load `.claude/skills/scripts/check_plugin_registry.json` and keep each plugin entry where both `stack.backend` and `stack.frontend` are either empty (stack-agnostic) or contain the project's value. Run only the matching scripts; skip non-matching silently.

Fallback (legacy projects): if `conventions.md` has no stack variables and they cannot be inferred from the codebase, run all scripts and include this warning in the report:

> Warning: No stack framework variables found in conventions.md. Running all check scripts. Add BACKEND_FRAMEWORK and FRONTEND_FRAMEWORK to conventions.md to enable stack filtering.

**C3. Reserve ID + save report.** Output folder: `${CHECK_LOGS_DIR}` (see `project/conventions.md`). Filename: `check-<id>-<truncated short title slug>.md` (6-digit zero-padded ID). Reserve the next global ID via `python .claude/skills/scripts/reserve_id.py --type check --title '<title>'`. Save per report conventions with the mode-specific header and body described in each mode section.

**C4. Present + post-skill.** Present the summary to the user, highlighting failures (or the mode-appropriate severity). Run /post-skill <id>.

## Adding a Check Plugin

A new plugin needs two artifacts (the orchestrator auto-discovers via the registry at runtime; no further wiring).

**1. Script** at `.claude/skills/scripts/check_<name>.py` with a `CHECK_PLUGIN_MANIFEST` YAML block in the module docstring.

**2. Registry entry** in `.claude/skills/scripts/check_plugin_registry.json` whose `script`, `name`, `stack.{backend,frontend}`, `scope`, and `critical` fields mirror the manifest.

Field reference (identical in both places):

| Field | Type | Meaning |
|---|---|---|
| `name` | string | Human-readable plugin name |
| `stack.backend` | list | Matching backends, or `[any]` for stack-agnostic |
| `stack.frontend` | list | Matching frontends, or `[any]` for stack-agnostic |
| `scope` | string | Validate scope keyword (e.g. `auth`, `i18n`, `constants`) |
| `critical` | bool | `true` blocks preflight on failure |

Example manifest block (script docstring):

```python
"""
Description of what this check does.

CHECK_PLUGIN_MANIFEST:
  name: <human-readable name>
  stack:
    backend: [flask]
    frontend: [react]
  scope: auth
  critical: true
"""
```

# Check

If there are no arguments, use the AskUserQuestion tool (or a numbered text list if unavailable) to ask which mode to run, with these options:
- "1. validate -- run project validation scripts (scope: all, i18n, auth, migrations, constants, po, coverage, tests, spec)"
- "2. review -- structured code review against quality perspectives (scope: staged, file, or directory)"
- "3. smoke -- runtime smoke tests against API endpoints or UI pages (scope: all, api, ui)"
- "4. preflight -- validate + review in one pass as a pre-merge checkpoint (scope: staged, all, or directory)"
- "5. health -- harness self-diagnosis and integrity check (9 built-in checks; --source enables drift check)"
- "6. test-plan -- generate a structured manual test plan from a brief or recent plans"
- "7. docs -- documentation consistency check via plugin-based scanners (paths, env vars, terminology)"
- "8. freshness -- compare local branches to upstream for configured repos; advisory-only, never pulls"
- "9. telemetry -- usage analytics and skill invocation statistics from telemetry.jsonl"
- "10. semiotic-inspection -- Semiotic Inspection Method (SIM) evaluation of interface communicability (scope: feature, page, flow)"

## Skill-specific Instructions

Run C1 (pre-skill + argument parse). Dispatch on the mode and execute the matching mode section below. Every mode except `telemetry` ends with C3 (save) + C4 (present + post-skill).

---

### Mode: validate

Reference prose for the shared pattern; other modes delta against this or Common Steps, whichever is shorter. Scope options: `all` (default) | `i18n` | `auth` | `migrations` | `constants` | `po` | `coverage` | `tests` | `spec`

> **Role boundary:** This skill is the *user-facing orchestrator*; the `standards-checker` agent is the *execution engine*.

1. Determine the validation scope from the argument (default: `all`).

2. Apply C2 (Stack Filtering): resolve applicable scripts from the plugin registry and pass only the matching list to the agent. For legacy projects with no stack variables, pass all scripts and include the warning in the report.

3. Dispatch by scope:

   | Scope | Action |
   |---|---|
   | `migrations` | Launch `standards-checker` (chain script) AND `migration-validator` (deep inspection + idempotency) |
   | `tests` | Launch `test-runner` with scope `all` |
   | `spec` | Run `python .claude/skills/check/check_spec_conformance.py` directly (no agent) |
   | `all` | Launch `standards-checker` with `all`; run `check_spec_conformance.py`; ask whether to also run tests |
   | other | Launch `standards-checker` with the scope |

4. C3 with header `# Check <id> | CHORE<scope> | <current datetime> | Validation Report`; body = scope, summary table (check / status PASS|FAIL|INFO / error count / warning count), per-failure details, overall `X/Y checks passed`.

5. C4 (present summary, highlight failures, run /post-skill <id>).

---

### Mode: review

Reuses C1, C3, C4. Scope options: `staged` (default) | file path | directory path.

1. Determine the review scope: `staged` -> `git diff --cached`; file path -> that file; directory -> all source files in it; no scope -> ask the user.

   **Review depth:** if `--depth <light|standard|deep>` is provided, resolve effective depth as `max(floor, flag)` where `floor` = `MINIMUM_REVIEW_DEPTH` from `project/conventions.md` (default `light`). With no `--depth` flag, the code-reviewer evaluates all 16 perspectives (equivalent to `deep`).

2. Launch the `code-reviewer` agent with scope and depth. The agent uses the two-stage loading protocol (see `general/review-perspectives.md` section "Two-Stage Loading"): load the index, select 4-6 relevant perspectives based on change content, load only those `review-perspectives/<tag>.md` files (load all 16 for `deep` or when explicitly requested), evaluate, and return a structured report.

3. C3 with header `# Check <id> | REVIEW<scope> | <current datetime> | Code Review: <short description>`; body = scope, perspective evaluation table (Adopted/Deferred/N/A), prioritized issues (severity, perspective, description, file:line), recommendations.

4. C4, highlighting HIGH severity issues.

---

### Mode: smoke

Reuses C1, C3, C4. Scope options: `all` (default) | `api` | `ui`.

> **Role boundary:** This skill is the *user-facing orchestrator*; the scripts are the *execution engines* -- `smoke_test_api.py` exercises backend API endpoints, `smoke.spec.ts` walks UI pages via Playwright.

1. Determine the scope (default: `all`).

2. Execute per scope:
   - **api**: `cd backend && python ../.claude/skills/scripts/smoke_test_api.py` via Bash; capture stdout. Runs against in-memory SQLite via Flask test client -- no servers required.
   - **ui**: if `e2e/smoke.spec.ts` is missing, tell the user: "UI smoke testing requires E2E infrastructure. Generate it via `/design` with `e2e != none`, or create `e2e/smoke.spec.ts` manually." Otherwise `cd e2e && npx playwright test smoke.spec.ts`; capture stdout/stderr. Requires backend (port 5000) and frontend (port 3000) running.
   - **all**: run API first (faster, independent), then UI if `e2e/smoke.spec.ts` exists.

   > **Note:** API endpoints are driven by `.claude/skills/scripts/smoke_test_registry.json`; edit that JSON to add/modify endpoints. The generic engine lives in `smoke_test_core.py`.

3. Parse results: API summary line (`PASS: N | WARN: N | FAIL: N`) + FAIL details; UI pass/fail + runtime error details.

4. C3 with header `# Check <id> | CHORE-X | <current datetime> | Smoke Test Report`; body = scope (`api`/`ui`/`all`), API results table (if applicable), UI results table (if applicable), captured errors, overall verdict (`PASS` / `FAIL`).

5. Present summary, highlighting failures. If failures are found, ask whether to investigate and fix, create a plan, or dismiss. Run /post-skill <id>.

---

### Mode: preflight

Reuses C1, C2, C3, C4. Combines validate + review into a single pre-merge checkpoint.

| Step | Common? | Delta |
|---|---|---|
| 1 | -- | Resolve scope: `staged` (default) -> validate all + review staged; `all` -> validate all + review all modified (staged + unstaged); directory path -> validate all + review files in that directory |
| 2 | C2 | Apply stack filtering before launching validation (legacy fallback: pass all scripts + include warning) |
| 3 | -- | Parallel fan-out: launch `standards-checker` (scope `all`, filtered script list), `code-reviewer` (determined review scope), and smoke test (if plan's `smoke` is `true`) as concurrent Agent invocations, each writing to a unique output section. If one check fails (agent error, timeout), the others still produce results -- do not abort preflight |
| 4 | C3 | Header `# Check <id> | CHORE<scope> | <current datetime> | Preflight Check`; body = validation summary table, code review perspective table, merged issues prioritized by severity, overall status (READY only if all validation checks pass and no HIGH severity review issues; otherwise NOT READY) |
| 5 | C4 | Present with a clear go/no-go recommendation |

---

### Mode: health

Reuses C1, C3, C4. Flags: `[--verbose] [--source <path>]`.

1. Apply C1 (pre-skill + argument parse) and C3 to reserve a `check-NNN` ID via `python .claude/skills/scripts/reserve_id.py --type check --title 'Harness Health Report'` and compute the output path `${CHECK_LOGS_DIR}/check-<id>-harness-health.md`.

2. Launch the `harness-health-evaluator` agent via the Agent tool with inputs `{id, output_path, verbose, source}`. When `--source <path>` is provided, pass `source` to the agent so it can run the harness drift check against the given canonical source directory. The agent runs the 9 built-in diagnostic checks (skill system integrity, orphaned briefs, stale plans, reference file completeness, conventions completeness, constitution presence, skill spec compliance, pending ledger summary, harness drift) and writes the Harness Health Report to `output_path`.

3. On return, read the written report file and present the summary per C4, highlighting failures and warnings. Run /post-skill <id>.

---

### Mode: test-plan

Reuses C1 and C4; C3 is adapted because output folder, ID type, and header shape differ. Scope: a brief describing what to test. If no brief is provided, ask the user.

1. Apply C1 (pre-skill + argument parse). Reserve a `usertest-NNN` ID via `python .claude/skills/scripts/reserve_id.py --type usertest --title '<title>'` (note: `--type usertest`, NOT `check`). Compute output path `${USER_TESTS_DIR}/usertest-<id>-<slug>.md`. Header shape on output: `# User test <id> | <prefix><scope> | <current datetime> | <short title>`.

2. Launch the `test-plan-generator` agent via the Agent tool with inputs `{brief, id, output_path}`. The agent reads `${OUTPUT_DIR}/INDEX.md`, filters for recently DONE plans relevant to the brief, carries unchecked items forward from prior user tests, phrases each to-do as a command to the user, and writes the test plan to `output_path`.

3. On return, apply C4 (present summary), then run /post-skill <id>.

---

### Mode: docs

Reuses C1, C3, C4. Flags: `[--plugins LIST] [--verbose] [--filter SEVERITY]`. Documentation consistency checker powered by `check_docs.py` with plugin-based scanners.

| Step | Common? | Delta |
|---|---|---|
| 1 | -- | Run `python .claude/skills/check/check_docs.py` passing through `--plugins LIST` (default: all), `--verbose` (show passing + detail), `--filter SEVERITY` (`error` / `warning` / `info`; default `info`). Available plugins: `harness-integrity` (all stacks), `path-liveness` (all), `env-vars` (django/node/next), `command-refs` (django/node/next), `terminology` (all) |
| 2 | -- | Parse the output. Exit 0 = no issues; 1 = issues found; 2 = script error |
| 3 | C3 | Header `# Check <id> | CHORE-docs | <current datetime> | Documentation Consistency Report`; body = error/warning/info counts, per-plugin findings grouped by plugin (severity, location, message), overall status (PASS / ISSUES FOUND) |
| 4 | C4 | Present, highlighting errors or warnings |

---

### Mode: freshness

Reuses C1, C3, C4. Scope is implicit (configured repos): workspace root plus CODEBASE_DIR when absolute and distinct.

1. Run `python .claude/skills/check/check_git_freshness.py --json` and parse the payload.
2. Render one `### <abs-path>` section per repo in the check log body with branch, upstream, ahead/behind counts, fetch status, and suggested next action:
  - behind > 0 and ahead == 0: suggest `git pull --ff-only`.
  - behind > 0 and ahead > 0: suggest checking divergence via `git status` then rebase/merge strategy.
  - behind == 0 and ahead > 0: suggest `git push` when appropriate.
  - behind == 0 and ahead == 0: mark as up to date.
3. Include the raw JSON payload as a fenced code block for downstream tooling.
4. C3 with header `# Check <id> | CHORE-X | <current datetime> | Git Freshness Report`; body = per-repo sections + summary line from script output.
5. C4 (present summary, highlight behind/diverged repos first, run /post-skill <id>).

---

### Mode: telemetry

Reuses C1 only. Read-only informational mode: do NOT apply C3 (no ID reserved, no check-log file) or C4 (no /post-skill).

1. Run `python .claude/skills/check/generate_telemetry_report.py` via Bash. Capture stdout.
2. Display the markdown output directly to the user.

---

### Mode: semiotic-inspection

Reuses C1, C3, C4. Scope: a feature name, page, user flow, or `all`. If no scope is provided, ask the user.

Conducts a Semiotic Inspection Method (SIM) evaluation of a project's interface communicability. The agent reconstructs the designer's metacommunication message across three sign classes (metalinguistic, static, dynamic), collates them, and produces a communicability judgment. The agent acts as **evaluator-as-user-advocate** -- representing users' interests through HCI knowledge, not replacing them.

1. Apply C1 (pre-skill + argument parse) and C3 to reserve a `check-NNN` ID via `python .claude/skills/scripts/reserve_id.py --type check --title 'Semiotic Inspection: <scope>'` and compute output path `${CHECK_LOGS_DIR}/check-<id>-semiotic-inspection-<scope-slug>.md`.

2. Launch the `semiotic-inspector` agent via the Agent tool with inputs `{scope, id, output_path}`. The agent reads the metacommunication files, conducts per-sign-class analysis, applies the 5 scaffold questions and the 4 SigniFYIng Interaction dimensions, and writes the SIM report with header `# Check <id> | CHORE-O | <current datetime> | Semiotic Inspection: <scope>`.

3. On return, apply C4 (present summary, highlighting communicability risks), then run /post-skill <id>.

## Rationale

SIM method citations and evaluator-as-user-advocate sourcing: see `.claude/agents/semiotic-inspector.md`. Pending-ledger separation in health Check 9: advisory-000442.
