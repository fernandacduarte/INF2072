---
designer_description: "When /plan, /check review, or any skill that evaluates a change against the review perspectives writes its review log, I'm the reference that codifies the structure -- review depth, deep-dive budget, the perspective scan table, deep-dive entries, conflict checks, execution metrics -- so every review produces a consistent, auditable trail instead of ad-hoc prose."
---

# FRAMEWORK - REVIEW LOG TEMPLATE

> Structured format for logging plan and code review iterations. Used by `plan`, `review-code`, and any skill that evaluates against `general/review-perspectives.md`.

## Review Log Format

```markdown
## Review Log

**Review depth:** Light | Standard | Deep
**Deep-dive budget:** 0/6 used

### Phase 1 — Perspective Scan (<datetime>)

| Perspective | Status | Concern |
|-------------|--------|---------|
| SEC | Adopted | Input validation covered in Step 3 |
| PERF | Deferred | Potential N+1 in bulk query — triggers Phase 2 |
| DB | Adopted | Migration is idempotent |
| ... | N/A | |

### Phase 2 — Deep-dive: PERF (iteration 1, deep-dive 1/6)

**Concern:** Bulk export may trigger N+1 queries for large datasets.
**Step ref:** Step 5 (bulk export query)
**Files read:** `backend/app/services/export_service.py`, `project/standards.md § Backend`
**Finding:** [analysis of the referenced source files]
**Recommendation:** [specific change or confirmation that no change is needed]
**Resolution:** [Plan amended — see Plan Amendment (iteration 1) / No change needed — status changed to Adopted]

### Conflict Check (iteration 1)

[If Phase 2 recommendations conflict across perspectives, document the conflict and resolution per the conflict resolution rules in `general/review-perspectives.md`. If no conflicts, write "No inter-perspective conflicts detected."]

### Execution Metrics

| Metric | Value |
|--------|-------|
| Deep-dives used | N/6 |
| Iterations completed | N/3 |
| Perspectives shortlisted | N |
| Perspectives Adopted | N |
| Perspectives Deferred (with rationale) | N |
| Convergence reason | [all resolved / iteration limit / deep-dive budget / no changes needed] |
```

## Field Definitions

- **Review depth:** Set by the complexity gate (Light, Standard, Deep). If `MINIMUM_REVIEW_DEPTH` (from project/conventions.md) or a `--review`/`--depth` flag forces depth higher, note as: `**Review depth:** Standard (overridden; auto=Light, floor=Standard)`. Effective depth = `max(auto, floor, flag)`.
- **Deep-dive budget:** Running counter, updated after each deep-dive. `N/6 used` in the header surfaces remaining budget at a glance.
- **Phase 2 header format:** `### Phase 2 — Deep-dive: <TAG> (iteration <N>, deep-dive <M>/6)` -- the `M/6` counter is mandatory.
- **Conflict Check:** Mandatory after each iteration that produces Phase 2 recommendations; evaluates whether recommendations from different perspectives contradict.
- **Execution Metrics:** Mandatory end-of-log section; provides data for tuning review thresholds over time.
