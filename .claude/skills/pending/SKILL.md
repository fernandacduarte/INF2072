---
name: pending
description: "List and address outstanding human actions from the pending ledger: verify implementations, flip status markers, run periodic curation, manage deferred work."
argument-hint: "[list|address <id>|add|done|snooze|dismiss] [args]"
compatibility: "Designed for Claude Code with the SEJA harness"
metadata:
  last-updated: 2026-04-27 22:00 UTC
  version: 1.0.0
  category: utility
  context_budget: light
  skip_stages: [pending-check, orphan-check, compaction-check, constitution]
  eager_references: []
  references:
    - general/shared-definitions.md
---

> Overview: see [./SKILL-quickguide.md](./SKILL-quickguide.md)

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| (none, or `list`) | No | List all pending items with per-item recommendation, then stop |
| `address <id>` | No | Run the guided resolution workflow for a specific item (marker flips, confirmation prompts) |
| `add --type <type> --source <id> --description "<text>"` | No | Append a new pending action directly |
| `done <id>` | No | Mark a pending item as done |
| `snooze <id> --until <YYYY-MM-DD>` | No | Snooze an item until a future date |
| `dismiss <id> [--reason <text>]` | No | Dismiss an item without completing it |

# Pending

0. Run /pre-skill "pending" $ARGUMENTS[0] to add general instructions to the context window.

If the argument begins with `add`, `done`, `snooze`, or `dismiss`, forward the arguments to `python .claude/skills/scripts/pending.py <subcommand> <rest>`, capture the exit code, print the output, then run `/post-skill` and stop.

If the argument begins with `address`, go to [Address dispatch](#address-dispatch).

If there is no argument or `list`:

1. Run `python .claude/skills/scripts/pending.py list --status pending --json`. Parse the JSON output.

2a. If empty list: print `No pending actions.` and run `/post-skill` and stop.

2b. If non-empty list: group items by `type`. For each group, print a header with the count (e.g., "**mark-implemented** (2)"). For each item in the group, print:

   - `<id>` -- `<type>` -- source: `<source>` -- age: N days
     - **Recommendation**: type-specific recommendation from the table below. If multiple, write each on a new line. Provide filenames and links to relevant files or plans when applicable. If the recommendation involves running a skill, include the exact command with arguments.
   <blank line>

   After all groups, print the action footer:

   ```
   --- To act on items ---
     /pending address <id>                     -- run the guided resolution for this item
     /pending done <id>                        -- mark as completed
     /pending snooze <id> --until YYYY-MM-DD   -- defer until a future date
     /pending dismiss <id> --reason "..."      -- dismiss without completing
   ```

3. Run `/post-skill pending` silently (without outputting intermediate actions) and stop.

### Type-specific recommendations

| Type | Recommendation |
|------|----------------|
| `mark-implemented` | Verify the implementation matches `<source>`. Run `/pending address <id>` to flip STATUS markers interactively. |
| `test-implementation` | Run the test plan from `_output/plans/plan-<source>-*.md`, then `/pending done <id>`. |
| `verify-as-coded` | Run `/explain spec-drift` to compare as-coded vs as-intended, then `/pending done <id>`. |
| `update-documentation` | Run `/document --plan <source>`, then `/pending done <id>`. |
| `apply-promote-markers` | Open `_output/promote-proposals/promote-proposal-plan-<source>.md`, rewrite Decision entries in your voice, copy to as-intended section Decisions, then `/explain spec-drift --promote --apply-markers <source>` (auto-marks done). |
| `spec-drift-check` | Run `/explain spec-drift`. Follow with `--promote` if STATUS items need promotion. Then `/pending done <id>`. |
| `periodic-curation` | Review the pending ledger: dismiss stale items, snooze items not yet due. Then `/pending done <id>`. |
| `incorporate-research-markers` | Run `/pending address <id>` to flip INCORPORATED markers interactively. |
| `implement` | Run `/implement <source>`. The entry auto-closes when the plan's DONE header is written. |
| `review-downstream-plan` | Open referenced plan files and compare against what `<source>` changed. Revise drifted plans via `/plan`, then `/pending done <id>`. |
| `create-decision-entry` | Create a D-NNN entry in product-design-as-intended.md section Decisions, then `/pending done <id>`. |
| `user-defined` / unknown | Complete the described action, then `/pending done <id>`. |

### Address dispatch

When invoked as `/pending address <id>`:

1. Run `python .claude/skills/scripts/pending.py list --status pending --json`. Find the item matching `<id>`. If not found or not pending, print an error and stop.

2. Dispatch based on the item's `type` field:

   - **mark-implemented**: Parse the `description` and `source` fields to find the target file and candidate entry IDs. For each candidate, run an `AskUserQuestion` confirmation offering `STATUS: implemented` flips. On each confirmation, invoke `python .claude/skills/scripts/apply_marker.py --file <path> --id <entry-id> --marker STATUS --value implemented --plan <source>`. When all candidates are addressed, invoke `pending.py done <id>`.

   - **incorporate-research-markers**: Same marker-flip flow as mark-implemented but with `--marker INCORPORATED`. Target is a ux-research file. Parse candidate entry IDs from description. When all candidates are addressed, invoke `pending.py done <id>`.

   - **All other types**: Print the type-specific recommendation from the table above and stop. These types resolve via external commands, not via internal dispatch. List the skills (with options and arguments) necessary to resolve each item. If an item is a plan, include a link to the plan file in the recommendation (including the plan file slug).

3. Run `/post-skill pending` and stop.

## Notes

- The `skip_stages: [pending-check, ...]` in the frontmatter prevents recursion: without it, running `/pending` would trigger `pending-check` in pre-skill, which would run `pending.py status` at the same time this skill is walking the ledger. Critical stages (brief-log, budget-eval, ref-load) still run.
- All state transitions go through `pending.py` subcommands; this skill never writes to `pending.jsonl` directly.
- Marker flips on `Human (markers)` files go through `apply_marker.py`; this skill never calls `Edit` on those files directly.
- **Source-based shortcut**: `pending.py done --source <id> --type <type>` closes all matching open entries in one call. Used when `/implement` writes the `# DONE | ...` header and by post-skill's safety net. Idempotent: no-op when no open entry matches.
- **Uniqueness invariant for implement**: a plan's `implement` entry is filed via `pending.py add --if-absent` so the (source, type) pair is unique under the script's atomicity (no agent-level race). Running `/plan` re-runs or post-skill checkpoint recovery do not duplicate entries.
- **Orphan cleanup for implement**: `pending.py cleanup` (24h-throttled) auto-dismisses `implement` entries whose plan file has been deleted from `_output/plans/`. Leftover `-progress.md` / `-qa-*.md` siblings do not mask a deletion. Dismissal reason: `plan file deleted`.
