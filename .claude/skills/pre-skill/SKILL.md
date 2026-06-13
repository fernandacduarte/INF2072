---
name: pre-skill
description: "[Internal] Lifecycle hook invoked by other skills to load references and log briefs. Not intended for direct user invocation."
argument-hint: "<skill-name> <brief>"
user-invocable: false
compatibility: "Designed for Claude Code with the SEJA harness"
metadata:
  last-updated: 2026-03-28 12:40 UTC
  version: 1.0.0
  category: internal
  context_budget: standard
  references: []
---

Pre-skill runs 6 stages: help, brief-log, budget-eval, pending-check, ref-load, constitution. Three are critical (brief-log, budget-eval, ref-load) and always run. Non-critical stages are skipped if listed in the calling skill's `metadata.skip_stages` and error-isolated (warn and continue). Legacy IDs `orphan-check` and `compaction-check` are recognized by budget-eval's sub-steps.

If "$ARGUMENTS" is empty, ask for the skill name and brief.

# Pre-skill

### Stage: help

Before any other processing, check if the calling skill's arguments contain `--help`. If so:
   a. Read `.claude/skills/$ARGUMENTS[0]/SKILL-quickguide.md` and display its full body (YAML frontmatter stripped, if any).
   b. If the sibling file does not exist, display the `description` field from `.claude/skills/$ARGUMENTS[0]/SKILL.md`'s YAML frontmatter.
   c. **Stop here** -- do not proceed with the remaining pre-skill stages or the calling skill's instructions.

The shared `load_quickguide(skill_dir)` helper at `.claude/skills/scripts/load_quickguide.py` is the canonical loader for scripts; the agent replicates its behavior here.

### Stage: brief-log

First, obtain the current UTC time by running `date -u +"%Y-%m-%d %H:%M UTC"` and capturing its output. Use this exact output as `<start-datetime UTC>` below — do not estimate or guess the time.

Without asking for authorization, insert into `${BRIEFS_FILE}` (see project/conventions.md) a new entry as the first entry after the `# Briefs Log` header and its following blank line (i.e., newest entries appear first). Format:
- Format: `STARTED | <start-datetime UTC> | <skill-name> | <brief>`
- Example: `STARTED | 2026-03-19 21:00 UTC | plan | Add user profile page`
- The datetime must be in format `YYYY-MM-DD HH:MM UTC` (obtained from the `date` command above)
- The brief should be exactly what the user wrote, except when it is an error log. In this case, summarize the error in one sentence and use that as the brief, prepended by `ERROR: ` (e.g., "ERROR: Database connection timeout error").
- Ensure the briefs are separated by a blank line
- When completed, post-skill prepends `DONE | <end-datetime UTC> |` and appends `| PLAN | <plan-id>` if applicable

Without asking for authorization, save `${BRIEFS_FILE}` before continuing, so the user can see a log of the requests if the system crashes after this.

**Sub-step: Conversation trace linkage** (after brief-log entry is saved): call `python .claude/skills/scripts/conversation_trace.py last-evt-id --session-id $CLAUDE_SESSION_ID` (env var value, or "null" if unavailable). If the output is not "null", call `python .claude/skills/scripts/conversation_trace.py backfill-skill --evt-id <last_evt_id> --skill-id "<skill-name> <brief>"` to link the preceding conversation exchange to this skill invocation. The last entry for a session is the agent's response entry (emitter=claude), which is the natural anchor for "what skill followed this exchange." Skip silently if no conversation trace entries exist for the session or if the script is not found.

### Stage: budget-eval

Read the calling skill's SKILL.md file at `.claude/skills/$ARGUMENTS[0]/SKILL.md` and parse its YAML frontmatter. Determine the **context budget** from `metadata.context_budget` (default: `standard` if not specified). Act per the tier:

| Tier | Loads | Then |
|------|-------|------|
| `light` | skips all briefs and reference files -- brief-log only | skip ref-load and constitution stages |
| `standard` (default) | briefs index `${BRIEFS_INDEX_FILE}` (generate via `python .claude/skills/scripts/generate_briefs_index.py` if missing) instead of full `${BRIEFS_FILE}` | proceed to orphan detection sub-step, then ref-load |
| `heavy` | full `${BRIEFS_FILE}` with **recency windowing** -- first 50 entries (newest first), append summary `"N earlier entries from DATE to DATE, not loaded."` for older ones; also load plan index `${PLANS_DIR}/INDEX.md` | proceed to orphan detection and compaction warning sub-steps, then ref-load |

**Sub-step: Orphan detection** (standard and heavy tiers; skip if `orphan-check` is in the calling skill's `skip_stages`): After loading the briefs index or full briefs, scan for entries with status `STARTED` (no matching `DONE`). If any orphaned entries are found (excluding the entry just appended in the brief-log stage), emit a warning: "Warning: N orphaned STARTED entries found in briefs index (no matching DONE). These may be from crashed sessions. Consider reviewing them." Then list the 5 most recent orphaned entries (by date, newest first) in a compact format:
   ```
   - <date> | <skill> | <brief (truncated to 80 chars)>
   ```

**Sub-step: Compaction warning** (heavy tier only; skip if `compaction-check` is in the calling skill's `skip_stages`): Count STARTED entries (both orphaned and completed) in `${BRIEFS_FILE}` whose timestamp falls within the last 2 hours. If the count exceeds the threshold (default: 8 invocations), emit a warning: "Warning: Context may be getting heavy after N skill invocations in this session. Consider starting a fresh conversation for best results, or use the session scratchpad (`${TMP_DIR}/session-notes.md`) to persist key decisions before starting a new session." This sub-step is advisory-only -- it warns but does not block.

### Stage: pending-check

Run `python .claude/skills/scripts/pending.py status --overdue-days 14 --format banner`. Print the output verbatim if non-empty. Never block the skill invocation; this stage is purely informational.

### Stage: ref-load

Load reference files (applies to standard and heavy tiers only):

Always include:
- Read and inject `product-design/conventions.md`. If it does not exist, read and inject `.claude/references/template/conventions.md` instead.
- Read and inject `.claude/references/general/permissions.md`
- Read and inject `.claude/references/general/constraints.md`

**Dynamic reference loading** -- mode determined by whether the calling skill declares `metadata.eager_references`.

**Mode 1 -- Eager-only (no `eager_references` field):** read and inject every file in `metadata.references`, resolving each path via the routing table below (legacy behavior). An empty `references: []` is valid (skill intentionally loads no additional refs).

**Mode 2 -- Demand-pull (`eager_references` field present):**
1. **Eager tier** -- read and inject each file in `eager_references` alongside the mandatory refs (conventions, permissions, constraints).
2. **Lazy tier** -- entries in `metadata.references` NOT in `eager_references` become available on demand. Emit the "Available references" block below listing each lazy ref; do NOT read or inject lazy refs at this stage.

An empty `eager_references: []` is valid (all skill-specific refs lazy; only mandatory refs loaded upfront).

**Available references block (demand-pull mode only):**
After loading eager refs, emit a compact numbered list: each lazy ref's path followed by a trigger hint derived from its filename and subdirectory (e.g., `project/security-checklists.md` -> "reviewing security concerns"). Routing: `general/` -> `.claude/references/general/`, `template/` -> `.claude/references/template/`, `project/` -> `product-design/`.

If the calling skill's SKILL.md **does not** contain a `metadata.references` field at all, log a warning: "Skill <name> has no metadata.references -- cannot load skill-specific references." All skills are expected to declare their references in frontmatter.

### Stage: constitution

Read and inject `product-design/constitution.md`. If it does not exist, skip silently (constitution is optional for backwards compatibility with projects that haven't generated one yet).

### Util scripts

- When planning, check `${SCRIPTS_DIR}` (see project/conventions.md) for useful scripts.
