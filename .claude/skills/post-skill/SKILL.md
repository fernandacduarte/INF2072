---
name: post-skill
description: "[Internal] Lifecycle hook invoked by other skills for briefs update, QA logging, and git commit. Not intended for direct user invocation."
argument-hint: "<id>"
user-invocable: false
compatibility: "Designed for Claude Code with the SEJA harness"
metadata:
  last-updated: 2026-04-01 12:59 UTC
  version: 1.2.0
  category: internal
  context_budget: standard
  references: []
---

# Post skill

> Rationale for design choices and historical context: see `SKILL-rationale.md` in this directory.

## Worktree Deferred Mode

When `--deferred` is passed (by the roadmap parallel-wave orchestrator after merging a worktree branch back to main), post-skill runs a reduced pipeline. The orchestrator handles wave-level briefs, QA, and commits; `--deferred` handles only the per-plan state alignment that requires the merged code on main.

| Step | Normal | `--deferred` |
|------|--------|--------------|
| 0 (checkpoint recovery) | run | run |
| 1 (brief-log) | run | **skip** -- orchestrator writes wave-level brief |
| 1b (telemetry prep) | run | run (flushed at 8b) |
| 2 (as-coded alignment) | run | run -- merged code is now on main |
| 2b (documentation auto-run) | run | **skip** -- orchestrator handles wave-level docs |
| 2c (design intent reminder) | run | run |
| 2d (eager implement entry) | run | **skip** -- not from /plan |
| 3 (QA log) | run | **skip** -- orchestrator handles wave-level QA |
| 4-6 (commit message, safety, scope) | run | **skip** -- orchestrator commits atomically |
| 6b-6c (preflight, markers check) | run | **skip** -- orchestrator runs these once for the wave |
| 7 (index regeneration) | run | run |
| 7g (pending action creation) | run | run |
| 8 (commit) | run | **skip** -- orchestrator commits |
| 8b (telemetry flush) | run | run (appended; orchestrator includes in wave commit) |
| 9-13 (wrap-up, next-step) | run | **skip** |

When `--deferred` is active, execute steps 0, 1b, 2, 2c, 7, 7g, and 8b only. Skip all others silently.

## Skill-specific Instructions

0. **Checkpoint recovery**: if `${OUTPUT_DIR}/.post-skill-checkpoint` exists, read it (`<step> | <datetime> | <skill-id>`). If `<skill-id>` matches $ARGUMENTS[0], resume from the step AFTER `<step>`. Otherwise delete the stale file and proceed normally. Also read SKILL-reference.md for schema definitions.

1. Obtain UTC time via `date -u +"%Y-%m-%d %H:%M UTC"`; use the exact output as `<datetime>` (do not estimate).

   Run `python .claude/skills/scripts/mark_brief_done.py --brief-pattern "<brief text>" --done-time "<datetime>" [--plan-id <id>]` to mark the matching STARTED entry as DONE.

   Checkpoint: `1 | <current datetime UTC> | $ARGUMENTS[0]` to `${OUTPUT_DIR}/.post-skill-checkpoint`.

1b. **Telemetry recording** -- prepare a record in context (flushed to disk at step 8b). Prepare a telemetry record per the schema in SKILL-reference.md (Telemetry Schema). Fields and qa_type enum are defined there. Populate `session_id` from the `CLAUDE_SESSION_ID` environment variable if available in the conversation context; otherwise set to `null`.

2. **As-Coded alignment** -- run when parent skill is `implement` (brief skill field). Skip when parent is `plan` (no code yet).

   a. Read the plan to identify changes: entities added/modified/removed, permissions, UX patterns, metacomm intents.

   b. **Conceptual design -- `project/product-design-as-coded.md § Conceptual Design`**:

      Let `LEGACY` = `conceptual-design-as-is.md`, `metacomm-as-is.md`, `journey-maps-as-is.md`.

      | Branch | Condition | Action |
      |---|---|---|
      | 1 | `product-design-as-coded.md` exists | Incremental anchor-based `Edit` on H3 subsections under `## Conceptual Design` (add / update / remove per plan). |
      | 2 | File absent AND no `LEGACY` file exists | Instantiate from `template/product-design-as-coded.md`; populate `## Conceptual Design`; leave `## Metacommunication` and `## Journey Maps` as placeholders (2c/2d fill them). |
      | 3 | File absent AND any `LEGACY` file exists | Emit the warning below; return from as-coded alignment (2b/2c/2d no-op). Do not create `product-design-as-coded.md` or edit `LEGACY`. Continue appending to `${CD_AS_IS_CHANGELOG}`. |

      Branch 3 warning (verbatim):

      ```
      WARNING: legacy as-is layout detected (one or more of
      conceptual-design-as-is.md, metacomm-as-is.md, journey-maps-as-is.md
      present) but project/product-design-as-coded.md is missing. Skipping as-coded alignment
      for this plan. Migrate per CHANGELOG 2.8.4 Migration Option 1 or 2,
      or run /seja-setup --upgrade. This warning repeats on every post-skill invocation
      until migrated.
      ```

      After branch 1 or 2, append a changelog entry to `${CD_AS_IS_CHANGELOG}` (instantiate from `template/product-design-changelog.md` if absent):

      ```
      ### vN -- YYYY-MM-DD
      - **Added/Changed/Removed**: {{description}}
      - **Source**: agent (post-skill)
      - **Plan**: {{plan-id}}
      ```

   c. **Metacommunication -- `product-design-as-coded.md § Metacommunication`** (inherit branch from 2b; branch 3 -> no-op): if the plan carried metacomm framing, update `### 4. Per-Feature Metacommunication Log` with the implemented intent and set Implementation Status to "Implemented"; for modified-metacomm features, update Designer Intent and Last Updated; append changelog to `### 5. Changelog`. **Phrasing rule**: use "I" (designer) and "you" (user), never third-person or passive (see `general/shared-definitions.md § Phrasing rule`). Tag changes `source: agent (post-skill)`. Anchor `Edit` on H3 heading text; all edits stay within `## Metacommunication`.

   d. **Journey maps -- `product-design-as-coded.md § Journey Maps`** (inherit branch from 2b; branch 3 -> no-op): skip silently if `## Journey Maps` is a placeholder or `product-design-as-intended.md §15` is absent. Otherwise update incrementally: for each plan-added/modified feature, match against `JM-TB-NNN` in `product-design-as-intended.md §15 (Designed User Journeys)` and update status under `### JM-TB-NNN: ...`; for `JM-E-NNN`, cross-reference `project/ux-research-results.md §5`; update `### Delta from As-Intended`; append changelog to `### Changelog`. Tag `source: agent (post-skill)`. Anchor `Edit` on H3 text; stay within `## Journey Maps`; multi-section updates require multiple Edits (enforced by `check_section_boundary_writes.py` at 6c).

   e. **DONE marker proposal** -- if the plan implemented any user-facing features or journey steps:
      1. Read the as-intended/as-coded registry from `project/conventions.md` (or `template/conventions.md`); for each as-intended file listed, scan `product-design/` for sections/rows matching features implemented by this plan (step descriptions + Files). Ignore items already carrying `STATUS: implemented` / `STATUS: IMPLEMENTED` / `ESTABLISHED`. Prepare a proposal listing: file path (rel to `product-design/`), heading/row id, and the marker `<!-- STATUS: implemented | plan-NNNNNN | YYYY-MM-DD -->`.
      2. Present via AskUserQuestion: "The following as-intended items appear to have been implemented by this plan. Apply markers now, defer for later review, or skip?" Options (rationale per `.claude/references/general/constraints.md`):
         - **Apply now** -- I flip STATUS markers to `implemented` now, while the mapping is fresh. Recommended when the implementation has been verified in this session. NOT recommended when you are unsure whether every candidate item matches what shipped.
         - **Defer for later review** -- I add each candidate to the pending ledger for verification later. Recommended when the implementation looks right but you want a cool-down period. NOT recommended when the candidates are trivially correct and deferring is pure procrastination.
         - **Skip** -- I do nothing. Recommended when the plan did not implement as-intended items (refactor, tooling, docs). NOT recommended when real candidates would be lost.
      3. Action dispatch; tag all marker changes `source: agent (post-skill)`:
         - **Apply now** -> route markers through `python .claude/skills/scripts/apply_marker.py` for any file in the Human (markers) registry (`HUMAN_MARKERS_FILES` in `human_markers_registry.py`); inline HTML-comment insertion continues to work for Human/Human-Agent files outside the registry.
         - **Defer for later review** -> for each candidate: `python .claude/skills/scripts/pending.py add --type mark-implemented --source plan-<id> --description "Flip STATUS markers on <file> for <entry-id> after verification"`. Silent on success; one-line warning on failure.
         - **Skip** -> do nothing.
      > Markers on `ux-research-results.md` and `product-design-as-intended.md` must go through `apply_marker.py` (both Human (markers)). Prose stays human-authored; agents write only STATUS (D-NNN, §15), ESTABLISHED (legacy), INCORPORATED, and CHANGELOG_APPEND after AskUserQuestion confirmation.

   f. Include updated as-coded files and as-intended files with DONE markers in the commit scope (step 8).

   g. **Pending action creation from plan metadata** (same gate as step 2). Each invocation is silent on success; one-line `Warning: could not create pending action <type>: <reason>` on failure; never block.
      i. Count Modified + Created in the plan's Files. If count >= `Verify-as-coded file threshold` from `## Periodic Triggers` in conventions.md (default 5): `python .claude/skills/scripts/pending.py add --type verify-as-coded --source plan-<id> --description "Review product-design/product-design-as-coded.md against the real implementation of plan-<id>"`.
      ii. If the plan has a non-empty `## Test plan` / `## Test Plan`: `python .claude/skills/scripts/pending.py add --type test-implementation --source plan-<id> --description "Run manual tests per plan-<id>'s Test plan section"`.
      iii. If step 2b's opt-out branch was taken (parent `/implement` had `--skip-docs` per 2b.c, or user chose "Skip" on 2b.d) AND the plan has any non-N/A `Docs:` step: `python .claude/skills/scripts/pending.py add --type update-documentation --source plan-<id> --description "Run /document --plan plan-<id>"`.
      iv. **Implement mark-done safety net**: `python .claude/skills/scripts/pending.py done --source plan-<id> --type implement` unconditionally. Closes the entry filed at `/plan` step 7h; idempotent (no-op if absent or already done). Also recovers when a crash occurred between `/implement`'s rename and its own mark-done call.

2c. **Design intent curation reminder** (same gate as step 2). Informational only -- do **not** perform the promotion (designer owns every word of Decision entries; harness manages only the STATUS marker lifecycle). Output (text, not AskUserQuestion):
   > "Design intent from plan [plan-id] has been implemented. Consider promoting items to `established` status via `/explain spec-drift --promote` (Phase 3a generates a draft Decision entry proposal; Phase 3b flips the STATUS markers after you apply the prose). P0 priority items: §4 Permission Model, §11 Global Vision, §13 Solution Representations, §14 Per-Feature Intentions."

2b. **Documentation auto-run** (same gate as step 2; skip silently if no plan -- advisory, explain, check).

   a. Collect non-N/A `Docs:` fields into a list. Skip silently if the plan predates the field (no steps have it).
   b. FEATURE/REDESIGN always trigger; FIX/CHORE trigger only when any step has non-N/A `Docs:`.
   c. **Preset opt-out**: if parent `/implement` carried `--skip-docs` (conversation-context channel, same as step 6d `--roadmap` and step 3 `skip_qa_log`), skip the AskUserQuestion and go directly to 2b.f (Skip). Log the opt-out.
   d. Otherwise, present an `AskUserQuestion` with header `"The plan identified these documentation needs:\n- [list each non-N/A Docs: field value]"` and these options (rationale per `.claude/references/general/constraints.md`):

      - **Auto-run now** *(recommended)* -- I run `/document --plan <plan-id>` now, while Docs: fields and implementation are fresh. Recommended when Docs: fields accurately describe what needs documenting. NOT recommended when docs require manual investigation first (e.g., you want to read generated code before writing prose).
      - **Skip** -- I file an `update-documentation` pending entry; you run `/document --plan <plan-id>` later. Recommended when you want to review the implementation offline before documenting, or when Docs: fields need adjustment. NOT recommended when docs are straightforward and deferring is pure procrastination.

      Mark "Auto-run now" as recommended (first option + "(Recommended)" suffix). On freeform `Other`: reply containing "skip" (case-insensitive) -> Skip; otherwise -> Auto-run now.
   e. **Auto-run now** -> run `/document --plan <plan-id>` (uses `.claude/references/template/docs/` and `.claude/references/general/documentation-quality.md`). Include updated docs in the commit scope (step 8).
   f. **Skip** (AskUserQuestion or `--skip-docs` preset) -> do not run `/document`; continue to step 3. Step 7g.iii files the `update-documentation` pending entry.

2d. **Eager-file implement entry from /plan completion** -- runs when parent skill is `/plan` (brief skill field = `plan`) AND the brief carries `PLAN | <id>`. Opposite of 2/2b/2c/7g. Skip for any other parent.

   1. Read the plan header to extract the short title (text after the last `|` in `# Plan <id> | <prefix>-<scope> | <datetime> | <short title> | Review: <depth>`).
   2. Invoke (`--if-absent` keeps this idempotent under checkpoint recovery):
      ```
      python .claude/skills/scripts/pending.py add --if-absent --type implement --source plan-<id> --description "Execute plan-<id> <short title>"
      ```
   3. Silent on success (script prints pa-NNNNNN or `INFO: existing open ... skipping`). Non-zero -> `Warning: could not file implement entry for plan-<id>: <reason>`. Do not block.

3. **Caller skip check**: if the parent passed `skip_qa_log: true` (conversation-context channel, same as step 6d `--roadmap`), skip to step 4. Default `false`. Skip is appropriate only when the parent's primary content shape is a Q&A transcript (currently `/research`, which embeds `## Q&A log` at its own steps 8 and 11). Plans, checks, inventories, etc. keep the companion to preserve Human (markers) classification and the `/reflect` diff signal.

   Otherwise, run /qa-log with overrides: `no_commit: true` (post-skill commits at step 8); `filename` = `<prefix>${ARGUMENTS[0]}-qa-<truncated short title slug>.md` (prefix matches the kind: plan-, advisory-, check-, ...; slug from prior-generated file or conversation topic); `output_dir` resolved from the prefix via the map below -- QA logs collocate with the parent artifact. `${QA_LOGS_DIR}` is the fallback for user-invoked `/qa-log` without a parent; `implement-` -> `${PLANS_DIR}` (lifecycle logs belong with the plan).

   Resolve the output directory via the prefix map in SKILL-reference.md (QA-Log Directory Mapping).

   The file includes the brief and the full Q&A log.

   Checkpoint: `3 | <current datetime UTC> | $ARGUMENTS[0]`.

4. Create an appropriate commit message including $ARGUMENTS[0].

5. **Git-state safety check**: run `git status`. Do NOT commit if a rebase is in progress (`rebase-merge` / `rebase-apply` in `.git/`), an unmerged conflict exists, or HEAD is detached -- inform the user and output the commit message for manual use. On `main`/`master`: warn and ask for confirmation.

6. **Commit scope verification**: run `python .claude/skills/scripts/verify_commit_scope.py --skill-type <type> --artifact-id <id> [--plan-id <id>] --always-include <paths>` to check staged files against expected paths. Pass `--roadmap-id <id>` when `--roadmap` was supplied to the parent skill. The script outputs JSON with `expected`, `staged`, `unexpected`, `missing`, and `pass` keys. Unexpected pre-staged files -> warn, list, output the commit message for manual use. Otherwise stage and commit.

6b. **Fast preflight gate** -- `python .claude/skills/scripts/run_preflight_fast.py`. Exit 0 -> proceed silently. Non-zero -> display failures; ask whether to proceed or abort (advisory, not blocking -- post-skill runs after lengthy work; `.githooks/pre-commit` is the hard gate). Script not found -> skip silently.

6c. **Human markers verifier** -- `python .claude/skills/scripts/check_human_markers_only.py --staged`. Exit 0 -> proceed silently. Exit 1 (prose mutation in a Human (markers) file) -> display the violation; ask via AskUserQuestion whether to abort or proceed. Default recommendation: abort (unauthorized edit should go through `apply_marker.py`). Script not found -> skip silently.

7. **Index regeneration**:
   a. `python .claude/skills/scripts/generate_briefs_index.py` -- refreshes `${BRIEFS_INDEX_FILE}`.
   b. `python .claude/skills/scripts/generate_macro_index.py` -- refreshes `${ARTIFACT_INDEX_FILE}` (`${OUTPUT_DIR}/INDEX.md`).
   c. **Cross-reference update**: run `python .claude/skills/scripts/update_cross_refs.py --artifact <path>` on the produced artifact. The script reads the `source:` header and updates the `spawned:` field on the source artifact automatically.
   d. **Decision digest regeneration** (conditional): if the completed skill was `/research` with HIGH/MEDIUM recommendations, OR a plan applied DECISION_APPEND markers: `python .claude/skills/post-skill/generate_decision_digest.py` to regenerate `${DECISION_DIGEST_FILE}` (`${OUTPUT_DIR}/decision-digest.jsonl`); include in commit scope. Skip silently if not found.

   Checkpoint: `7 | <current datetime UTC> | $ARGUMENTS[0]`.

   Capture the current HEAD SHA via `git rev-parse HEAD` and hold it in memory as `<pre-commit-sha>` for use in step 8b.

8. Stage the affected files (including regenerated indexes and updated as-coded files) and commit using the message from step 4. Checkpoint: `8 | <current datetime UTC> | $ARGUMENTS[0]`. Then delete `${OUTPUT_DIR}/.post-skill-checkpoint` -- post-skill completed successfully.

8b. **Telemetry flush** -- enrich the step-1b record and write it. Populate the 3 commit-dependent fields left `null` at 1b: `git_commit_sha` via `git rev-parse HEAD`, `files_changed` via `git diff-tree --no-commit-id --name-only -r HEAD | wc -l`, `parent_skill` from conversation context (each `null` if commit skipped or unknown). Run `python .claude/skills/scripts/build_telemetry.py --skill <skill> --id <id> --outcome <outcome> --timestamp <ISO> --duration-seconds <N> [all other fields]` to construct and append the complete record. See SKILL-reference.md (Telemetry Flush Example) for the complete record shape.

    **Gate**: compare `git rev-parse HEAD` now against the SHA captured before step 8. If they are equal (step 8 produced no commit), log `'telemetry deferred: no primary commit at <datetime>'` and skip the remainder of this step -- the pending telemetry record is dropped.

    Otherwise, commit telemetry as a separate trailing commit: `git add ${OUTPUT_DIR}/telemetry.jsonl && git commit -m "telemetry: <skill> <id>"`. Keeps telemetry co-located with skill output and avoids amend-after-push divergence when an editor auto-syncs the pre-amend commit. On any failure (commit, permission, missing prior commit), log `WARNING: telemetry commit failed (<reason>); record not persisted` and continue -- this step must not block.

9. If manual actions are needed (db upgrade, environment/config update, backend/frontend restart), append the plan file with the instructions (separate dev and production), and inform the user.

10. If there were surprises during the skill execution, output them, together with their resolution and status (resolved or pending), if applicable.

11. Output a link to the generated file within `${OUTPUT_DIR}` (see project/conventions.md).

12. When done with the skill and Q&A, output the following:

```
<brief> (if available)
<links to files (ex: plan id.md)>

**--- SKILL COMPLETE: <skill name> <plan|roadmap|research|...> <id> ---**

```

13. **Contextual next-step suggestions**: read `.claude/references/general/skill-graph.md` and look up the completed skill in the "After" column. Only nudge when the skill has entries there; if the file is absent, skip silently. When matched: first output the numbered options as plain text (if skill invocations, include the entire call, with arguments as needed), then present the user with numbered options (one per suggested skill). Question text:

    > "You might want to try next:"

    **Suppression rules** -- omit a suggestion when any of these conditions hold:
    1. If check modes ran at step 6b or 6c in this post-skill invocation, omit `/check validate`, `/check review`, and `/check preflight` (already covered).
    2. If `/document` was offered or ran at step 2b, omit `/document` (already covered).
    3. If the brief's plan prefix is CHORE or DOCUMENT, omit `/reflect` (low-value reflection target).

    **Top-N cap**: present at most 3 suggestions plus Skip. If more than 3 candidates remain after suppression, select the 3 most contextually relevant (prefer suggestions that continue the current workflow thread over lateral or reflective suggestions).

    Each option's description carries the skill-graph reason verbatim plus one line on *when the suggestion would be wrong*, per the Decision-point rationale convention in `.claude/references/general/constraints.md`. If the graph omits a "when NOT recommended" note, derive one from the skill's failure modes (Quick Guide "When to use", argument-hint).

    Options (shape):
    - `/suggested-skill-N` -- *Recommended when*: <reason from the graph>. *NOT recommended when*: <derived from the skill's failure mode>.
    - if in AskUserQuestion: "End" -- *Recommended when*: the current workflow is complete and you want to stop here. *NOT recommended when*: you are skipping because the choices feel like friction, in which case one of the suggestions probably earns its place.

    On selection: execute the skill; on End: stage, commit, and end post-skill.

