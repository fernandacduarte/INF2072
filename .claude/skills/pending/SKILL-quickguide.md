**What it does**: Lists outstanding human actions the harness is tracking for you, showing each one with type-specific advice on how to resolve it, then stops. Six subcommands cover the full lifecycle: list (read-only listing with advice), address (guided resolution for marker-flip types), add, done, snooze, and dismiss. The ledger lives at `_output/pending.jsonl` and is append-only, so you never lose history.

Twelve action types the harness can file:

| Type | Filed by | Typical resolution |
|------|----------|--------------------|
| `mark-implemented` | post-skill | Flip STATUS markers via `/pending` dispatch |
| `test-implementation` | post-skill | Run the plan's test plan manually |
| `verify-as-coded` | post-skill | Run `/explain spec-drift` to confirm |
| `update-documentation` | post-skill / `--skip-docs` | Run `/document --plan <source>` |
| `apply-promote-markers` | `/explain spec-drift --promote` | Write Decision entries, then `--apply-markers` |
| `spec-drift-check` | periodic trigger | Run `/explain spec-drift` |
| `periodic-curation` | periodic trigger | Review and triage the ledger |
| `incorporate-research-markers` | post-skill | Flip INCORPORATED markers in UX research |
| `implement` | post-skill (after `/plan`) | Run `/implement <plan-id>` |
| `review-downstream-plan` | `/implement` (file-overlap check) | Review affected plan for assumption drift |
| `create-decision-entry` | `/research` (decision-extract) | Create a D-NNN entry in as-intended |
| `user-defined` | `/pending add` | Whatever you described |

**Examples**:
> `/pending`
> Lists all pending items grouped by type, each with advice on how to resolve it (e.g., which skill to run, which file to open). Prints a footer showing available subcommands, then stops.

> `/pending address pa-000003`
> Runs the guided resolution workflow for item pa-000003. For mark-implemented and incorporate-research-markers types, walks you through per-candidate marker flips with confirmation. For other types, prints the type-specific advice.

> `/pending add --type user-defined --source plan-000042 --description "review CSRF middleware"`
> Appends a custom reminder to the ledger. Pre-skill will surface it at the top of every skill invocation until resolved.

> `/pending done pa-000003`
> Marks item pa-000003 as done.

> `/pending snooze pa-000005 --until 2026-05-01`
> Hides item pa-000005 until May 1st, then resurfaces it.

> `/pending dismiss pa-000007 --reason "no longer relevant after redesign"`
> Dismisses an item without completing it. The reason is recorded in the ledger.

**When to use**: After `/implement` if you chose "Defer for later review" at post-skill, when pre-skill tells you there are pending actions, when the periodic curation trigger has fired, or any time you want to review what the harness is tracking for you.

**Related**: `/check health` Check 9 reports the pending-ledger count (diagnostic only). Any mutation (address/add/done/snooze/dismiss) still flows through `/pending`. The two skills are intentionally separate -- see advisory-000442.

**Next step**: `/explain spec-drift --promote` after addressing periodic curation items (generates a Decision proposal for promotion candidates), or `/implement` once you have reviewed the outstanding review items.
