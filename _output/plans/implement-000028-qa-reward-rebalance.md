# QA Log — implement plan-000028 | 2026-06-26 21:05 UTC | Reward rebalance to fix pursuit collapse

## Brief

> /implement plan-000028 — execute the reward rebalance plan (manual mode).

## Q&A / session record

### Q1. Proceed with implementation?
User chose "Implement now" after the plan was reviewed (standard depth). Ran manual mode (6 steps ≤ threshold; interdependent reward changes benefit from in-context oversight).

### Q2. Outcome of the per-step execution?
- **Step 1** (`eval_report.py`, `test_eval_report.py`): added `mean_reward_breakdown` JSON column (per-term means aggregated in `_aggregate_episodes`, explicit key in `_build_variant_summary`, appended to both field lists). Tests pass.
- **Steps 2–3** (`current.py`, `loader.py`): `CurrentRewardWeightsV3` + `PursuitFirstTeamReward` (`current_v3`) registered; runtime-verified.
- **Step 4** (`Makefile`): defaults switched to `current_v3` (V2 kept commented; reversible).
- **Step 5** (`test_reward_strategies.py`): 4 v3 tests (registration, terminal-signs == V2, move-toward > stay > away, visible-stalk shaping < get_pacman) — pass.
- **Step 6** (partial): diagnostic ran on a V2 final checkpoint; full A/B training benchmark left to the user (long CPU job).

### Q3. What did the diagnostic reveal?
The new `mean_reward_breakdown` reconciles exactly to the V2 −162.43 return and shows it is owned by `repeated_direction_reversal` (−115.65) and `two_step_cycle` (−46.80) — the ghost thrashes/ping-pongs — **not** stalking (`currently_visible` only +1.80). This confirms research-000027's revised diagnosis and validates the v3 targeting (those penalties are zeroed/softened).

### Q4. Any surprises?
A pre-existing, unrelated test failure surfaced — `test_stronger_movement_variant_changes_only_one_weight` (StrongerMovementReward built on V1 weights vs V2 baseline). Verified failing on `pre-plan-000028`; filed as **pa-000014** for separate fix. Not addressed here (out of scope).

## Result

Steps 1–5 complete, Step 6 partial. Quality gate: 51 relevant tests pass, 1 pre-existing unrelated failure. Rollback branch: `pre-plan-000028`.
