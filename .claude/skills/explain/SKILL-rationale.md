# Rationale -- /explain

Maintainer-only context for `explain/SKILL.md` (with focus on the `spec-drift` mode). NOT loaded at runtime (no entry in `metadata.references`; the sync tool and call-graph generator both ignore this file). Edit both files when rationale changes.

## Phase 3a / 3b two-phase split

The promote workflow (`/explain spec-drift --promote` followed by `/explain spec-drift --promote --apply-markers plan-NNNNNN`) is split into two phases on purpose, not as an artifact of implementation convenience. The split enforces a clean division of ownership:

- **Designer owns every word of Decision prose.** Decision entries land in `product-design-as-intended.md § Decisions` as DRR-shaped `### D-NNN:` blocks. The harness must not author any sentence that ends up there.
- **Harness owns the STATUS lifecycle.** Moving `STATUS: implemented` to `STATUS: established` is a structural mutation on a Human (markers) file; the harness is allowed to make it because `apply_marker.py` is the sole write path and the change carries no prose.

Phase 3a writes a *draft* of the Decision entries to `_output/promote-proposals/promote-proposal-plan-<id>.md`. That file is a non-canonical scratchpad -- nothing reads from it except the designer's eyes. Phase 3b verifies, per per-item confirmation, that the designer copied the accepted entries into the intent file (heading-only grep on `### D-NNN:`; the title and body may have been rewritten freely), then flips the markers via `apply_marker.py`.

The non-canonical proposal file is the indirection that makes the split possible. Without it, Phase 3a would have to either write directly into the intent file (violating designer ownership) or return a blob the designer copies from chat (fragile across sessions, unreviewable by post-skill). The file on disk is the Phase-3a audit trail; the ledger entry (now singular under R1 -- see next section) is the Phase-3b completion gate.

## Designer-authorship invariant -- do NOT auto-draft DECISION_APPEND in post-skill step 6e

Negative directive. Future simplification proposals will surface the idea of collapsing Phase 3a into post-skill step 6e's "Apply now" branch: when the designer flips STATUS to `implemented` at implement-time, why not also draft the Decision entry then? This section documents why that collapse must be rejected.

At implement-time, when the designer is reviewing post-skill step 6e and chooses **Apply now**, the relevant cognitive state is: "the code landed; the STATUS marker should reflect that." The designer is confirming an implementation lifecycle event, not reflecting on what the change MEANS in the product's decision history. Decision prose requires that second pass -- the designer reading the plan's motivation, trade-offs accepted, and the implementation surface, then composing a DRR-shaped entry that captures what future maintainers need to know.

If the harness were to auto-draft a `DECISION_APPEND` into the intent file in the same step, two things would go wrong:

1. **Trust-model erosion.** `check_human_markers_only.py` exists precisely to prevent Agent-written prose from bleeding into Human (markers) files. Harness-authored Decision entries would normalize prose writes by the harness, setting a precedent that any script can claim "designer-authored" just by routing through `apply_marker.py`. The enforcement script's check would pass (the marker write is legal), but the social contract the check encodes would rot.
2. **Quality decay under interaction pressure.** An auto-drafted Decision in the intent file, committed with the implementation, is far more likely to stay in its auto-drafted shape than a draft sitting in a separate proposal file that explicitly asks the designer to rewrite. The indirection (non-canonical file -> designer pass -> canonical file) is what guarantees the designer actually exercises editorial judgment.

The fence: post-skill step 6e files `STATUS: implemented` markers (structural) and defers Decision authorship to Phase 3a. Future proposals to merge these must be redirected here, not revisited on first principles.

## Drift-review cadence merge (spec-drift-check + periodic-curation)

Prior to plan-000470, `/pending` dispatched `spec-drift-check` (14d periodic-check trigger) and `periodic-curation` (30d periodic-check trigger) through two separate bullets whose dispatch prose was effectively identical -- both printed "Suggest: run /explain spec-drift ...". The two types existed because the periodic-check layer files at two cadences, and the ledger schema carries `type` as a first-class field.

The distinct cadences are an interval choice, not a type distinction the designer can act on differently. At dispatch time, a designer seeing one bullet or the other would run the same skill invocation with the same next steps. Collapsing the two bullets into one merged handler eliminates a branch the designer cannot meaningfully choose between; the cron-filing layer (`pending.py cmd_periodic_check`) continues to file both types at 14d / 30d so the periodic-triggers table in `conventions.md` remains a tuning surface if interval-tuning ever becomes necessary.

The merge is SKILL.md-prose-only. No code moves; no test changes; historical entries of both types remain closable through the single merged dispatch path (and through `/pending done <id>` directly).

## --scope since-plan rationale

`/explain spec-drift` without a scope defaults to the full as-intended/as-coded registry. That is correct for periodic checks (what has drifted overall?) but heavy after a single plan (what did THIS plan change?). A designer running `/implement` on plan-NNNNNN and then wanting to confirm that the as-coded changes match the plan's as-intended surface doesn't need to re-scan every row in the registry.

`--scope since-plan plan-NNNNNN` narrows Step A to registry rows whose as-intended OR as-coded paths appear in the plan's Files section (Modified + Created). Rows not touched by the plan are skipped with a one-line count note; the drift report header records the narrowed scope so the output is self-describing.

The flag is disjoint from `--promote`. Phase 3a/3b operate on STATUS markers already in the intent file, a discovery mechanism that is orthogonal to the registry-row scan. If both flags appear, `since-plan` applies only as a Step A filter; `--promote` ignores it. This disjointness is intentional -- plan-scoped drift is a Step A concern (what changed in this plan's surface?); promote is a Step C concern (what STATUS markers are ready to promote?).

## Citation index

- `advisory-000175` -- STATUS: implemented -> established lifecycle that Phase 3a/3b implements.
- `advisory-000292` -- reflective practice convention (Decision-point rationale phrasing; informs the designer-authorship invariant by naming reflection as a distinct cognitive pass).
- `advisory-000412` -- `/explain` owns drift, not `/check`; the skill-boundary ruling this rationale file's `spec-drift` sections inherit.
- `advisory-000431` -- harness simplification arc under which plan-000470's R1/R2/R4 collapses were prioritized.
- `advisory-000439` -- rejected /design-into-/plan merger; narrow `/research` write path. Relevant because it established the WHAT/HOW boundary that plan-000470 preserves (R1/R2 do not cross it).
- `advisory-000448` -- research filename rename (advis* -> research); cited for context on the terminology arc that overlapped plan-000470's authoring window.
- `research-000469` -- source research for plan-000470; mapped the full drift-handling surface and identified R1 (Phase 3a/3b collapse), R2 (drift-review merge), R3 (this file), R4 (--scope since-plan).
- `plan-000458` -- established the Sibling `SKILL-rationale.md` pattern (/plan and /post-skill); this file adopts that pattern for /explain.
- `plan-000470` -- the plan that implemented R1-R4 and created this file (Step 7).
