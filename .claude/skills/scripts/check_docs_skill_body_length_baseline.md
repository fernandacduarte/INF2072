# Skill body length calibration baseline

Authoritative post-plan-000458 baseline for the `skill-body-length` plugin in
`check_docs.py`. Generated at plan-000458 step 3. Step 11 verification checks
against this table; future compression/expansion PRs should update it in step.

## Per-tier thresholds

| Tier | Body-line ceiling |
|---|---|
| light | 150 |
| standard | 300 |
| heavy | 500 |

Thresholds are calibrated against the plan-000451 post-compression baseline and
are NOT to be adjusted without a documented rationale -- calibration = adjust
the world, not the lint (see plan-000458 step 1).

## Per-skill baseline (post-plan-000458 step 3)

Body line count is the agent-facing body from the first heading after
`## Arguments` through EOF, as reported by
`python .claude/skills/check/check_docs.py --plugins skill-body-length --verbose`.

| Skill | Tier | Body lines | Threshold | Delta | Status |
|---|---|---|---|---|---|
| check | heavy | 326 | 500 | -174 | PASS |
| communicate | standard | 104 | 300 | -196 | PASS (1 inlined-template WARN, step-11 follow-up candidate) |
| design | standard | 323 | 300 | +23 | WAIVER |
| document | standard | 149 | 300 | -151 | PASS (1 citation WARN, address via steps 8-9) |
| explain | standard | 259 | 300 | -41 | PASS |
| help | light | 71 | 150 | -79 | PASS |
| implement | heavy | 199 | 500 | -301 | PASS |
| onboard | standard | 129 | 300 | -171 | PASS |
| pending | light | 56 | 150 | -94 | PASS |
| plan | heavy | 423 | 500 | -77 | PASS |
| post-skill | standard | 216 | 300 | -84 | PASS |
| pre-skill | standard | 185 | 300 | -115 | PASS |
| qa-log | light | 55 | 150 | -95 | PASS (1 citation WARN, address via steps 8-9) |
| reflect | standard | 136 | 300 | -164 | PASS |
| research | standard | 114 | 300 | -186 | PASS |
| seja-setup | standard | 306 | 300 | +6 | WAIVER |

Total: 16 skills. Zero length-threshold WARNINGs (2 waivers, 14 PASS). The 4
remaining WARNINGs (1 inlined-template, 3 citations) are out of scope for step 3
and are addressed in later plan-000458 steps.

## Waiver registry

Waiver comments live in the body of the waived SKILL.md (below the first body
heading, per the plugin's detection rule). Suppressed signals: length threshold
only.

| Skill | Body lines | Tier | Waiver reason |
|---|---|---|---|
| design | 323 | standard | Project-setup flow is load-bearing; further compression risks losing execution fidelity; revisit after Common Steps mode factoring lands. |
| seja-setup | 306 | standard | State-dispatch across 5 mode variants (install/finalise/workspace/demo/upgrade) is load-bearing; re-tiered from `light` in plan-000458 step 3; revisit once the 5-mode surface can be factored via Common Steps. |

## Decisions logged in step 3

- `seja-setup`: re-tiered `metadata.context_budget` from `light` to `standard`.
  Rationale: `light` was inherited from before the skill grew its 5-mode
  dispatch surface; references list is empty (`references: []`) and no
  `eager_references`, so `standard` (not `heavy`) matches the reference-load
  rule in plan-000458 step 3. At 306 body lines the skill sits +6 over the
  `standard` threshold, covered by a waiver that documents the load-bearing
  dispatch surface and points at Common Steps factoring as the follow-up.
- `design`: waivered rather than compressed. The body is execution-dense
  (tables, per-mode step lists, registry columns) and a 25-line editorial pass
  would have risked losing fidelity. The waiver points at Common Steps mode
  factoring as the follow-up.

## Follow-ups surfaced but deferred

- `communicate/SKILL.md:60` carries a 22-line inlined code fence. Candidate for
  extraction to `.claude/references/template/`. Not in plan-000458 scope (no Common
  Steps factoring planned for `/communicate`). File a separate plan when the
  next compression sweep runs.
- 3 citation WARNs (`document`, `qa-log`, `seja-setup`) remain. These are
  addressed by the SKILL-rationale.md sibling pattern adopted in plan-000458
  steps 7-9.
