---
name: implement
description: Execute a previously generated plan to add a feature, fix a bug, or refactor code. Use when user mentions "implement", "execute plan", or "run plan".
argument-hint: "<planned-item-id> [--manual] [--roadmap <roadmap-id>] [--pending] [--checkpoint wave|plan|none] [--max-iterations N] [--dry-run] [--skip-checks] [--skip-docs]"
compatibility: "Designed for Claude Code with the SEJA harness"
metadata:
  last-updated: 2026-03-27 12:00 UTC
  version: 1.0.0
  plan_format_version: 1
  category: planning
  context_budget: heavy
  eager_references:
    - project/product-design-as-coded.md
    - project/product-design-as-intended.md
    - general/report-conventions.md
    - general/coding-standards.md
  references:
    - project/product-design-as-coded.md
    - project/product-design-as-intended.md
    - general/report-conventions.md
    - general/coding-standards.md
    - project/standards.md
    - project/security-checklists.md
    - general/review-perspectives.md
---

> Overview: see [./SKILL-quickguide.md](./SKILL-quickguide.md)

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `<planned-item-id>` | Yes | The 6-digit ID of the plan to execute |
| `--manual` | No | Execute all steps sequentially in the current context instead of using subagents. Default: auto mode |
| `--max-iterations N` | No | Set the iteration cap for auto mode. Default: `20` |
| `--dry-run` | No | Preview what changes would be made without applying them |
| `--roadmap <roadmap-id>` | No | Execute all plans in a roadmap, wave by wave. Mutually exclusive with `<planned-item-id>` |
| `--checkpoint <wave\|plan\|none>` | No | Checkpoint granularity for roadmap mode. Default: `wave` |
| `--skip-checks` | No | Skip the automatic quality checks (`/check validate` + `/check review`) at the end |
| `--skip-docs` | No | Skip the automatic documentation generation at post-skill step 2b. Files an `update-documentation` pending entry instead |
| `--pending` | No | Execute all pending plans by generating a lightweight roadmap and running roadmap mode. Mutually exclusive with `<planned-item-id>` and `--roadmap` |

# Execute a plan

If no argument was provided, ask the user for the planned item id.

## Definitions

| Term | Definition |
|------|------------|
| Plan file | Resolve `$ARGUMENTS[0]` via `${OUTPUT_DIR}/INDEX.md` (run `python .claude/skills/scripts/generate_macro_index.py` if missing); construct `${PLANS_DIR}/plan-<id>-<slug>.md`. Abort if the ID is not in the index. |
| Progress file | `${PLANS_DIR}/plan-<id>-progress.md` -- append-only cross-iteration learnings. Created at start of auto mode; each subagent reads it and appends. |
| Rollback branch | `git branch pre-plan-<id>` from current HEAD before executing. Inform the user; undo via `git checkout pre-plan-<id>`. |
| Worktree mode | When the orchestrator spawns a subagent with `isolation: "worktree"`, the subagent operates in deferred-write mode: skip `pre-skill` brief-log writes, skip `post-skill` entirely, write only to per-plan files (progress file, plan status, source code). The orchestrator handles shared-state writes (briefs, pending, index, telemetry) in the serialized merge phase after the worktree is merged back. |

After each step (or iteration in auto mode), output the updated to-do list, update and save the plan-file to-do list immediately.

## Quality Gate

Runs validation, code review, and tests. Skipped if `--skip-checks`.

1. Run `/check validate`.
2. Run `/check review`.
3. Launch the `test-runner` agent with scope "all".
4. If the plan's `smoke` field is `true`, run `/check smoke api`.
5. **Critical** issues (failing tests, security findings, blocking validation errors) must be fixed before proceeding; non-critical issues become deferred items in the plan summary.

### Generator-Critic Loop (Auto Mode Only)

Auto mode runs a bounded retry loop for critical code-review findings. Manual mode treats review findings as advisory (the user decides). After Quality Gate step 2: classify each finding as **critical** (security, correctness, failing tests) or **advisory** (non-blocking); set `retry_count = 0`; while critical findings exist AND `retry_count < 2`, increment, build a fix prompt per critical finding (description + file/line + plan context), launch a `general-purpose` subagent, re-run `/check review` on changed files only, re-classify. If `retry_count` hits 2 with criticals remaining, log them as **unresolved** in the plan summary and continue -- do not block. Append to the quality gate output (verbatim):
```
### Generator-Critic Iterations
- Iteration count: N/2
- Findings per iteration: [list counts]
- Resolution status: all resolved / N unresolved critical findings remain
```

## Execution Modes

Dispatch: `--pending` -> pending; else `--roadmap` -> roadmap; else `--manual` -> manual; else auto (default).

| Mode | Recommended when | Topology |
|------|------------------|----------|
| Auto (default) | Most plans, especially >6 steps where context degradation is a risk. | Each step runs in a fresh `general-purpose` subagent (Ralph pattern); state via the progress file. |
| Manual (`--manual`) | Small plans (<=6 steps) or when per-step confirmation is needed. | Sequential in the current context. |
| Roadmap (`--roadmap <id>`) | Executing every plan in a roadmap without per-plan invocation. | Each plan runs auto mode in a fresh subagent; pauses between waves per `--checkpoint`. |
| Pending (`--pending`) | Clearing all pending implement entries in one go. | Generates a lightweight roadmap from pending entries, then dispatches to roadmap mode. |

**Flags.** `--max-iterations N` caps auto-mode iterations (default 20; ignored in manual). `--dry-run` previews per-step file creates/modifies without writing. `--skip-checks` skips the final quality gate. `--skip-docs` suppresses the post-skill step 2b auto-doc `AskUserQuestion` (goes straight to Skip; files an `update-documentation` pending entry) -- use when documenting in a separate session or for harness-internal-only plans.

## Manual Mode -- Skill-specific Instructions

1. Run /pre-skill "implement" $ARGUMENTS[0] to add general instructions to the context window.

2. Read the planned item from the plan file.

3. **Load references on demand** based on what the step touches:

   | When step touches | Load |
   |-------------------|------|
   | backend / frontend / testing / i18n files | `project/standards.md` |
   | auth or validation | `project/security-checklists.md` |
   | quality gate (step 8) | `general/review-perspectives.md` |

4. If the plan file lacks a to-do list, append one; check each item off as completed and output the updated to-do list.

5. Execute the plan actions. If an affected file has unsaved or uncommitted changes, pause and ask for authorization before proceeding.

6. Document every file, constant, class, method, and key code fragment created or modified. Save the to-do list.

7. **Test generation** (skipped if `--skip-checks`): for each step with a non-N/A `Tests` field, write or update tests per `project/standards.md § Testing`. Absent field (pre-format plans) -- infer from modified files. If a bug is found, record a new plan, do not execute it, and alert the user when concluding. Revise or eliminate obsolete tests. **Note (mode split):** manual mode retains test-after ordering by design. The user's presence provides the quality oversight that the TDD red-green cycle substitutes for in auto mode. Do not invert this order in manual mode.

8. Run the [Quality Gate](#quality-gate) (skipped if `--skip-checks`).

9. Mark the plan id with `# DONE | <YYYY-MM-DD HH:MM UTC> |`. Save. Invoke `python .claude/skills/scripts/pending.py done --source plan-<id> --type implement` (idempotent; one-line warning on non-zero exit; do not block -- post-skill step 7g.iv is the safety net).

10. Append a summary of all changes to the plan file.

11. If `--roadmap <roadmap-id>` is in `$ARGUMENTS`: open the roadmap (resolve `<roadmap-id>` via `${OUTPUT_DIR}/INDEX.md`) and flip **only this plan's** Wave Summary row Status to `done`. Must happen **before** step 12 so the edit lands in the same commit as the plan rename. If this was the **last** roadmap item, run the [Quality Gate](#quality-gate) with review scope = all changes since `pre-plan-<first-plan-id>`. **File-overlap check**: collect the completed plan's `Files:` entries (all Modified + Created paths) and compare against each remaining plan's (Status != `done`) `Files:` entries; resolve remaining plan files via INDEX.md. If any overlap exists: `python .claude/skills/scripts/pending.py add --type review-downstream-plan --source plan-<id> --description "Plan <id> modified files also referenced by plan(s) <overlapping-ids>: review step descriptions for assumption drift before implementing."` -- silent on success; one-line warning on non-zero exit; do not block.

12. Run /post-skill <planned-item-id>.

## Auto Mode -- Skill-specific Instructions

### Phase 0: Setup

1. Run /pre-skill "implement" $ARGUMENTS[0] to add general instructions to the context window.

2. Read the planned item from the plan file.

3. Parse the Steps section. Each step has structured metadata (title, description, Files, References, Verify, checkbox; optional: Depends on, Docs, Traces). **Version check**: read the plan header for `plan_format_version`; if absent or != `1`, warn and fall back to manual mode (plans without version metadata predate the structured step format). A future v2 must extend this skill or provide a migration path.

4. Create the progress file if missing, with header (verbatim):
   ```markdown
   # Progress -- Plan <id>

   Append-only cross-iteration learnings. Each subagent reads this file at the start and appends findings at the end.

   ## Codebase Patterns
   <!-- Subagents consolidate reusable patterns here -->

   ## Iteration Log
   ```

5. Build the execution queue: incomplete steps (unchecked `- [ ] Done`) in dependency order. A step whose "Depends on" lists any incomplete step is not yet eligible. Steps without a "Depends on" field have no dependencies (eligible immediately when the queue reaches them).

6. Inform the user (verbatim): "Auto mode: N steps remaining, max M iterations. Each step runs in a fresh subagent. Use Ctrl+C to stop between iterations."

### Phase 1: Iteration Loop

For each step in the execution queue, up to `--max-iterations` (default 20):

7. **Pick the next step**: select the next eligible step (all dependencies complete). If all steps are done, exit to Phase 2. If only blocked steps remain, pause and ask the user for guidance.

8. **Build the subagent prompt** for a `general-purpose` agent. Include: the step's full description (title + body -- self-contained per plan conventions), **Files**, **Verify**, **Tests** (if non-N/A; absent -> infer from modified files), **Interface** (if present and non-N/A), and the progress-file content. Tell the subagent to read `product-design/conventions.md`, `.claude/references/general/coding-standards.md`, and **only** the `product-design/` files named in the step's References (e.g., `project/standards.md § Backend`) -- do not load all 9. Action contract: if `Tests:` is non-N/A, follow the TDD red-green cycle -- (a) write a failing test per `Tests:` (if `Interface:` is present, use it as the type contract; if the test passes before any implementation, report PARTIAL with note "test already passes -- possible scope overlap with existing code"); (b) implement the step until the test passes (green phase); (c) run test commands from `project/conventions.md` to confirm **Verify**; on failure, retry the green phase up to 3 times before returning PARTIAL. If `Tests:` is N/A or absent (pre-format plans), use the legacy order: implement the step; infer and write/update tests from modified files; run test commands to confirm **Verify**; on failure, retry up to 3 times before returning PARTIAL. Commit message: `plan-<id> step <N>: <step title>`. Append discoveries / gotchas / useful context to the progress file; promote reusable patterns to "Codebase Patterns" at the top. Report **SUCCESS** (verify met), **PARTIAL** (some progress, blocked), or **FAILED**; on PARTIAL/FAILED, describe the blocker in the progress file.

9. **Spawn the subagent** and wait for completion.

10. **Process result**:

    | Result | Plan checkbox | Action |
    |--------|---------------|--------|
    | SUCCESS | `- [x] Done` | Save plan file; continue. |
    | PARTIAL | `- [~] Partial` | Read progress-file blocker; if addressable (missing file/fixture), proceed -- a later step may unblock. After 2 consecutive PARTIAL/FAILED, pause and ask the user. |
    | FAILED | `- [!] Failed` | Read progress-file failure; pause and ask the user: skip, retry, or abort. |

11. **Inter-iteration checkpoint**: report "Step N/M complete. Remaining: K steps."

### Phase 2: Wrap-up

12. Run the [Quality Gate](#quality-gate) (skipped if `--skip-checks`). Test failures here may be fixed in-context (small targeted fix).

13. Mark the plan id with `# DONE | <datetime> |`. Save. Invoke `python .claude/skills/scripts/pending.py done --source plan-<id> --type implement` (idempotent; one-line warning on non-zero exit; do not block -- post-skill step 7g.iv is the safety net).

14. Append an aggregated summary to the plan file: steps completed vs total, iterations used, any partial/failed, key progress-file learnings.

15. If `--roadmap <roadmap-id>` is in `$ARGUMENTS`: open the roadmap (resolve via `${OUTPUT_DIR}/INDEX.md`), flip **only this plan's** Wave Summary row Status to `done`. Must run **before** step 16 so the edit lands in the same commit as the plan rename. If this was the **last** roadmap item, run the [Quality Gate](#quality-gate) with review scope = all changes since `pre-plan-<first-plan-id>`. **File-overlap check**: collect the completed plan's `Files:` entries (all Modified + Created paths) and compare against each remaining plan's (Status != `done`) `Files:` entries; resolve remaining plan files via INDEX.md. If any overlap exists: `python .claude/skills/scripts/pending.py add --type review-downstream-plan --source plan-<id> --description "Plan <id> modified files also referenced by plan(s) <overlapping-ids>: review step descriptions for assumption drift before implementing."` -- silent on success; one-line warning on non-zero exit; do not block.

16. Run /post-skill <planned-item-id>.

## Roadmap Mode -- Skill-specific Instructions

> Used when `--roadmap <id>` is present. Skip the Manual Mode and Auto Mode sections above entirely.

### Phase 0: Setup

1. Run /pre-skill "implement" --roadmap $ARGUMENTS to add general instructions to the context window.

2. **Resolve roadmap file**: look up the roadmap ID in `${OUTPUT_DIR}/INDEX.md`; read `${ROADMAP_DIR}/roadmap-<id>-*.md`. Abort if not found.

3. **Parse wave summary**: extract per-item Wave number, Item ID + title, Plan ID (skip `plan-TBD`/missing), Dependencies, Status.

4. **Filter to incomplete items**: drop status `done`. If none remain, inform the user: "All roadmap items are already complete." and exit.

5. **Validate plan availability**: for each incomplete item, verify the plan file exists in `${PLANS_DIR}`. If any are missing, list them and ask the user to skip or abort.

6. **Determine checkpoint mode** from `--checkpoint` (default `wave`): `wave` -> pause between waves; `plan` -> pause after every plan; `none` -> full autopilot, progress notes only.

7. **Create rollback branches**: `git branch pre-roadmap-<id>` from current HEAD. Inform the user: "Roadmap mode: N plans remaining across W waves. Checkpoint: <mode>. Rollback branch: pre-roadmap-<id>. Use Ctrl+C to stop between plans."

### Phase 1: Wave Execution Loop

For each wave (Wave 0, Wave 1, ...) with incomplete plans:

8. **Start wave**: `git branch pre-wave-<N>-<roadmap-id>` from current HEAD.

9. **Identify plans in this wave** and determine parallelism: Wave 0 is always sequential (migration chain safety); Wave 1+ may run in parallel when plans' Files lists do not overlap, otherwise sequentially.

   **Enhanced overlap check**: after the Files-list comparison, load `.claude/references/general/call-graph.json` (skip with warning if absent or stale). For each pair of plans in the wave, check if any file in Plan A's `Files:` scope has an import/call edge to any file in Plan B's scope. If any edge exists, treat as overlapping (conservative default) and downgrade to sequential. Log: "Plans X and Y have call-graph dependency via <file-A> -> <file-B>; running sequentially."

10. **Execute plans** per the parallelism decision from step 9.

    **Sequential execution** (Wave 0, or overlapping Files): for each plan, launch a `general-purpose` subagent with a self-contained prompt that runs `/implement <plan-id> --roadmap <roadmap-id>` in auto mode. The `--roadmap` pass-through activates per-plan roadmap-file maintenance: Auto Mode step 15 / Manual Mode step 11 flips this plan's Wave Summary Status to `done` **before** `/post-skill`, so the roadmap edit lands in the same commit as the plan rename. Include plan path, roadmap path, project conventions, coding standards. Subagent reports SUCCESS / PARTIAL / FAILED. Pass through `--skip-checks` and `--max-iterations` if provided. Wait for each subagent before moving on.

    **Parallel execution** (Wave 1+ with non-overlapping Files): use worktree isolation to run plans concurrently.

    a. For each plan in the wave, spawn: `Agent(subagent_type="general-purpose", isolation="worktree", prompt=<implement-plan-prompt with worktree_mode=true>)`. The subagent prompt includes plan path, roadmap path, project conventions, coding standards, and the worktree-mode contract (skip pre-skill brief-log, skip post-skill entirely, commit within the worktree branch). Pass through `--skip-checks` and `--max-iterations`.
    b. Launch **all agents in a single message** so they execute in parallel.
    c. Wait for all agents to complete. Each returns SUCCESS / PARTIAL / FAILED plus worktree path and branch name (auto-cleaned if no changes).
    d. Enter the **serialized merge phase** (step 10e-10h).
    e. For each completed worktree in plan-ID order (deterministic): if FAILED, log and skip (do not merge). Otherwise: `git rebase main <worktree-branch>`.
    f. If rebase succeeds: `git merge --ff-only <worktree-branch>`, then `git worktree remove <path>`.
    g. If rebase fails (conflicts): pause via AskUserQuestion:
       - **Resolve manually** -- Recommended when conflicts are in source code you understand.
       - **Skip this plan** -- Recommended when the conflicting plan can be re-run after other plans merge. NOT recommended when the plan's changes are critical to this wave.
       - **Abort wave** -- Recommended when conflicts indicate the plans were not truly independent. Resets to `pre-wave-<N>-<roadmap-id>`.
    h. After all merges: run deferred post-skill operations. For each successfully merged plan, run `/post-skill <plan-id> --deferred` on the main branch (shared-state writes: briefs, pending entries, index updates, telemetry). Then flip each merged plan's Wave Summary Status to `done` in the roadmap file.
    i. **Worktree cleanup**: run `git worktree list`; for each worktree not matching the main working tree, attempt `git worktree remove <path>` (retry up to 3 times with 2s/4s/8s delays on failure); run `git worktree prune`.

11. **Process wave results**:
    a. Count SUCCESS / PARTIAL / FAILED.
    b. Re-parse the roadmap to confirm all SUCCESS plans show Status `done` (each subagent flipped its own row via the step-10 pass-through). This is reconciliation, not a write -- any SUCCESS row still `pending` triggers a warning and a safety-net flip.
    c. If any plan FAILED: pause regardless of checkpoint mode and ask the user:
       - **Continue** -- Recommended when the failed plan is non-blocking for downstream waves. NOT recommended when later plans depend on it.
       - **Retry** -- Recommended when the failure looked transient or context-induced.
       - **Abort** -- Recommended when the failure exposes a roadmap-level issue that needs replanning. Completed plans are preserved.
    d. **Compaction warning**: count the cumulative completed plans across all waves so far (all plans with Status `done` in the roadmap). If the count exceeds 6, emit (advisory only -- do not block): "Context is getting heavy after N plans. Consider stopping here and resuming in a fresh session -- `/implement --roadmap <id>` will pick up from the next incomplete item."

12. **Inter-wave checkpoint** (per `--checkpoint`):
    - **`wave`** (default): show wave summary (completed, failed, remaining) + key files modified, then ask "Wave N complete. Continue to Wave N+1?" Also emit: "Before continuing, scan the next wave's plan descriptions for step assumptions that may have changed based on what this wave implemented. If any steps reference files or interfaces this wave altered, choose 'Review changes' and revise the affected plan.":
      - **Continue** -- Recommended when the wave summary looks correct and no next-wave plan's steps reference files this wave altered.
      - **Review changes** -- Recommended when you want to inspect code first, or when a next-wave plan's step descriptions may assume a state this wave altered. NOT recommended when the wave is purely additive and low-risk.
      - **Abort** -- Recommended when output reveals a roadmap-level problem. Completed work is preserved.
    - **`plan`**: per-plan pauses are handled by each `/implement` invocation's post-skill step 11; the orchestrator reads status after each and proceeds.
    - **`none`**: emit "Wave N complete (K/M plans succeeded). Continuing to Wave N+1..." and proceed. Failures still pause (failures always get user attention).

### Phase 2: Wrap-up

13. **Final quality gate**: run the [Quality Gate](#quality-gate) with review scope = all changes since `pre-roadmap-<id>`. Cross-plan integration check. Skipped only if `--skip-checks`.

14. **Update roadmap file**: write final status for all items. If all are `done`, append:
    ```
    ## Completion
    Roadmap completed at <datetime UTC>. All N plans executed across W waves.
    ```
    After writing the Completion block, close the roadmap pending entry: `python .claude/skills/scripts/pending.py done --source roadmap-<id> --type implement` (idempotent; silent on success; one-line warning on non-zero exit; do not block).

15. **Report summary**: total plans executed vs total; waves completed; failures (if any); total files changed (`git diff --stat pre-roadmap-<id>..HEAD`); rollback instructions: "To undo all changes: `git checkout pre-roadmap-<id>`. To undo a specific wave: `git checkout pre-wave-<N>-<roadmap-id>`."

16. Run /post-skill --roadmap <roadmap-id>.

### Constraints

Each plan runs in auto mode via a fresh subagent; manual mode is not supported for roadmap execution. `--skip-checks` applies only to per-plan quality gates (the roadmap-level final gate at step 13 is never skipped). `--max-iterations` applies to each plan's auto-mode iteration cap. `--dry-run` previews all plans without executing; output is shown sequentially, wave by wave. Resumable: re-running `/implement --roadmap <id>` on a partially-complete roadmap picks up from the first incomplete item; completed plans are not re-executed.

## Pending Mode -- Skill-specific Instructions

> Used when `--pending` is present. A thin wrapper that generates a roadmap from pending implement entries and dispatches to Roadmap Mode.

1. Run /pre-skill "implement" --pending to add general instructions to the context window.

2. **Reserve roadmap ID**: run `python .claude/skills/scripts/reserve_id.py --type roadmap --title "pending plans auto-roadmap"` and capture the returned ID.

3. **Generate roadmap**: run `python .claude/skills/scripts/generate_pending_roadmap.py --roadmap-id <id>`. Handle exit codes:
   - Exit 0: roadmap generated successfully; continue.
   - Exit 1: no pending implement entries found. Inform the user: "No pending implement entries found." and exit.
   - Exit 2: script error. Show the stderr message and exit.

4. **Display wave summary**: read the generated roadmap file (`${ROADMAP_DIR}/roadmap-<id>-*.md`) and display the Wave Summary section to the user.

5. **Confirmation gate**: ask the user to confirm before executing:
   - **Execute** -- Recommended when the wave summary correctly groups the pending plans and you are ready to run them all.
   - **Review roadmap** -- Recommended when you want to inspect or edit the generated roadmap file before executing. NOT recommended when the plans are simple and non-overlapping.
   - **Abort** -- Recommended when the pending plans need replanning or are not ready for execution.

6. On "Execute": dispatch to [Roadmap Mode Phase 0 step 2](#phase-0-setup-2) with the generated roadmap ID. Pass through `--skip-checks`, `--max-iterations`, and `--checkpoint` if provided by the user.

7. On "Review roadmap": display the roadmap file path and wait for the user to confirm they are ready to proceed. On confirmation, dispatch to Roadmap Mode Phase 0 step 2 as in step 6.

8. On "Abort": exit without executing.
