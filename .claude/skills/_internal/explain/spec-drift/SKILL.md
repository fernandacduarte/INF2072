---
name: explain-spec-drift-internal
description: "Inlined worker for /explain spec-drift mode. Not user-invocable."
compatibility: "Designed for Claude Code with the SEJA harness"
metadata:
  internal: true
  category: internal
  version: 1.0.0
---

> This is an inlined worker; execute these instructions as part of the caller's flow. The wrapper at `.claude/skills/explain/SKILL.md` has already run C1 (pre-skill) and loaded design-spec references; execute the steps below and invoke C4 (post-skill) at the end.

### spec-drift (reference prose)

Combines read-only drift analysis with an optional sync workflow. Scope argument: `all` (default), `conceptual-design`, `metacomm`, `--promote` (promotion-only; skip to Step C), or `--promote --apply-markers plan-NNNNNN` (Phase 3b). C3 saves the drift report; C4 closes each terminal branch (sync-No, Phase 3a end, Phase 3b end).

#### Step A -- Drift Analysis

If scope is `--promote` or `--promote --apply-markers ...`, skip Steps A-B and go to Step C.

1. Determine scope from the argument (default: `all`). Accepted variants: `all`, `conceptual-design`, `metacomm`, `--promote`, `--promote --apply-markers plan-NNNNNN`, `--scope since-plan plan-NNNNNN`. If scope is `since-plan plan-NNNNNN`, validate the plan ID format against `^plan-\d{6}$`. If invalid, emit `ERROR: --scope since-plan expects plan-NNNNNN (6-digit ID). Got: <value>` and abort.

2. Read the as-intended/as-coded registry from `project/conventions.md` (fallback `template/conventions.md`). Use the Section column to narrow scans. For each row in scope: if the as-coded counterpart is `-` (research-only) or either file is missing, report and skip. Journey-ID locations: JM-TB-NNN -> `product-design-as-intended.md §15`; JM-E-NNN -> `ux-research-results.md §5`.

   For each in-scope as-intended file, also scan for `STATUS: implemented` markers (legacy `STATUS: IMPLEMENTED` also detected) lacking an `ESTABLISHED:` stamp. Collect as "pending promotion" items.

   **--scope since-plan narrowing**: when the scope is `since-plan plan-NNNNNN`, read `_output/plans/plan-<id>-*.md` to extract the Files section (all Modified + Created paths). Then filter the in-scope registry rows to those whose as-intended OR as-coded path appears in the plan's Files. For rows not touched by the plan, emit a one-line note (`Skipped N registry rows not touched by plan-<id>`) and skip the scan for those rows. Log the narrowed scope in the drift report header. Disjoint from `--promote`: if both appear, treat `since-plan` as a Step A narrowing filter only; `--promote` Phase 3a/3b operates on STATUS markers (a discovery mechanism orthogonal to registry-row scan) and ignores `since-plan`.

3. **Conceptual Design Drift** (if in scope) -- compare `${AS_CODED} § Conceptual Design` with Part I of `${DESIGN_INTENT}` section by section:

   | Category | What to compare |
   |----------|----------------|
   | Entities | Names, attributes, relationships |
   | Permissions | Role-permission mappings |
   | UX Patterns | Interaction patterns, page flows, navigation |
   | Business Rules | Validation rules, constraints, workflows |

   Classify each difference as **Added** (in as-intended, not as-coded), **Removed** (in as-coded, not as-intended), or **Modified** (in both, different).

4. **Metacomm Drift** (if in scope) -- compare `${AS_CODED} § Metacommunication` with Part II of `${DESIGN_INTENT}`:

   | Category | What to compare |
   |----------|----------------|
   | Feature Intentions | Intentions present in as-intended but not in as-coded |
   | Implementation Status | Features marked "Implemented" in as-coded but modified/removed in as-intended |
   | Designer Intent | Changes in stated intent between the two files |

5. Compile the drift report:

   ```
   ## Drift Summary

   | Scope | Added | Removed | Modified | Total |
   |-------|-------|---------|----------|-------|
   | Entities | N | N | N | N |
   | Permissions | N | N | N | N |
   | UX Patterns | N | N | N | N |
   | Business Rules | N | N | N | N |
   | Metacomm Intentions | N | N | N | N |

   ## Detailed Changes
   (list each change with category, type, description)

   ## Pending Promotions

   Items marked `STATUS: implemented` in registered Human (markers) files not yet promoted to `established`.
   Candidates for `/explain spec-drift --promote` (Phase 3a drafts the Decision entry; Phase 3b flips the markers).

   | File | Section / Row | Marker | Plan |
   |------|--------------|--------|------|
   | (none) OR list of found items |
   ```

6. Apply C3 to save the drift report.

7. Present the summary to the user.

#### Step B -- Sync Prompt

Use AskUserQuestion (fallback: numbered text list) with these options:
- "1. Conceptual-design to metacomm -- align metacomm with the conceptual design"
- "2. Metacomm to conceptual-design -- align conceptual design with the metacomm"
- "3. Bidirectional -- reconcile both (with user confirmation for conflicts)"
- "4. Promote implemented items -- draft DRR-shaped Decision entries for `STATUS: implemented` items (Phase 3a)"
- "5. No -- skip sync"

If **No**: apply C4 and stop. If **Promote implemented items**: go to Step C (Phase 3a).

#### Step C -- Promote Workflow (two-phase)

The promote workflow has two phases so the designer owns every word of the Decision prose while the harness manages the STATUS lifecycle structurally:

- **Phase 3a -- Proposal generation** (`/explain spec-drift --promote`): draft DRR-shaped entries for `STATUS: implemented` items to `_output/promote-proposals/promote-proposal-plan-<id>.md`. Do NOT modify `product-design-as-intended.md`. File one pending action (`apply-promote-markers`).
- **Phase 3b -- Marker flip** (`/explain spec-drift --promote --apply-markers plan-NNNNNN`, 6-digit plan ID): verify `### D-NNN:` entries were added (heading-only grep), run per-item AskUserQuestion confirmation, invoke `apply_marker.py` on confirmed items. Post-skill's `check_human_markers_only.py` and `check_changelog_append_only.py` verify marker flips do not bleed prose.

##### Phase 3a steps (`/explain spec-drift --promote`)

1. Read the registry from `project/conventions.md` (fallback `template/conventions.md`). Scan registered `product-design-as-intended.md` (and any other Human (markers) files) for `STATUS: implemented` markers lacking `ESTABLISHED:`.

2. Group candidates by plan ID (from the STATUS marker's plan field). If none, tell the user ("No implemented items pending promotion.") and apply C4.

3. For each candidate, draft a DRR-shaped entry per `template/docs/drr.md`. Sources: Context from the plan's Agent Interpretation; Decision from the chosen approach; Consequences from Trade-offs (if present) + any REQ markers the plan touched.

4. Assign stable `D-NNN` IDs by scanning existing Decision entries in `product-design-as-intended.md § Decisions` and using the next available number. REQ and D-NNN are orthogonal namespaces.

5. Write the proposal to `_output/promote-proposals/promote-proposal-plan-<id>.md` with a header linking back to the source plan and each draft Decision entry in a copy-paste-friendly fenced block. The proposal is a designer-owned draft -- the designer may rewrite the prose freely before copying.

6. **Dedup before adding pending actions**: grep the pending ledger for existing `apply-promote-markers` entries with `source: plan-<id>`.
   - Status `pending` exists: do NOT add duplicates. Tell the designer: "Proposal already queued. See `_output/promote-proposals/promote-proposal-plan-<id>.md`, or run Phase 3b to continue."
   - Only status `done` exists: proceed with a fresh entry (re-promotion is valid).
   - Otherwise: invoke `python .claude/skills/scripts/pending.py add --type apply-promote-markers --source plan-<id> --description "Copy draft Decision entries from _output/promote-proposals/promote-proposal-plan-<id>.md into product-design-as-intended.md § Decisions, then run /explain spec-drift --promote --apply-markers plan-<id> to flip STATUS markers (Phase 3b)"`.

7. Tell the designer: "Phase 3a complete. Drafted N Decision entries in `_output/promote-proposals/promote-proposal-plan-<id>.md`. Review, edit to your voice, copy into `product-design-as-intended.md § Decisions`, save, then run `/explain spec-drift --promote --apply-markers plan-<id>` to flip the STATUS markers."

8. Apply C4.

##### Phase 3b steps (`/explain spec-drift --promote --apply-markers plan-NNNNNN`)

1. Read the pending ledger to find the matching `apply-promote-markers` action for this plan ID. If not found, warn and continue (designer may be running Phase 3b without a prior Phase 3a).

2. Read `_output/promote-proposals/promote-proposal-plan-<id>.md`. Extract the list of drafted `D-NNN` IDs.

3. **Heading-only grep** `product-design/product-design-as-intended.md` for each D-NNN: regex `^###\s+D-NNN(?::|\s*$)`. Do NOT match title text, Context prose, or body -- the designer may have rewritten the prose (designer-voice preservation). Split results into `present` and `missing`.
   - `present` empty: abort with "No D-NNN entries from the proposal found in `product-design-as-intended.md`. Copy the draft entries from `_output/promote-proposals/promote-proposal-plan-<id>.md` first, then re-run `/explain spec-drift --promote --apply-markers plan-<id>`."
   - `present` non-empty: proceed with present set; at end of phase, report `missing` set to the designer.

4. For each D-NNN in both the proposal and the file, AskUserQuestion: "Flip STATUS from implemented to established for D-NNN?" (per-item confirmation).

5. For confirmed items, invoke `python .claude/skills/scripts/apply_marker.py --file product-design/product-design-as-intended.md --id D-<NNN> --marker STATUS --value established --plan plan-<id> --date <today>`. Legacy `STATUS: IMPLEMENTED` is detected by the widened regex and REPLACED (not stacked) by the lowercase form.

6. **Pending ledger lifecycle updates** (2-branch closure):
   - All proposed `D-NNN` entries present in the intent file AND every present item was flipped successfully: invoke `python .claude/skills/scripts/pending.py done --source plan-<id> --type apply-promote-markers`.
   - Otherwise: leave `apply-promote-markers` PENDING and emit a message enumerating which `D-NNN` IDs are missing from the intent file (from the `missing` set) and/or which were declined during the per-item confirmation, so the designer knows what to finish before re-running Phase 3b.

7. Apply C4.

#### Step D -- Sync Workflow

If the user chose a sync direction in Step B.

**Provenance.** Every entry created or modified carries `source` (one of `human`, `agent (explain)`, `agent (post-skill)`, `agent (plan)`) and `last-synced` (`YYYY-MM-DD HH:MM UTC`).

**Directions.**
- **conceptual-design -> metacomm**: for each entity/feature/UX-pattern in `${DESIGN_INTENT}` lacking a metacomm entry, draft a metacommunication intention, present for confirmation/revision, record user revisions verbatim (`general/shared-definitions.md § Verbatim rule`), add on confirmation with `source: agent (explain)`.
- **metacomm -> conceptual-design**: for each metacomm intention implying entities/permissions/UX-patterns not present, propose additions, present for confirmation/revision, add on confirmation with `source: agent (explain)`.
- **bidirectional**: run both directions sequentially; present all gaps and conflicts together for human resolution.

**Conflict detection.** When the two files disagree: present both sides, ask the user to resolve (keep conceptual-design, keep metacomm, or provide a new resolution). **Never auto-resolve.**

**Finalization.** Update `last-synced` on all modified entries. Update "Delta from As-Coded" sections in both as-intended files if as-coded exists. Apply C4.

### Voice and framing (spec-drift)

**spec-drift**: combines drift analysis and optional sync (replaces the former `/spec` skill). Two-phase promote workflow in Step C.
