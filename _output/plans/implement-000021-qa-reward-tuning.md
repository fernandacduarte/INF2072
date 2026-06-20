# QA Log — implement-000021 | reward tuning from research 12

> Session log for plan-000021 (reward tuning from research-000012). Captures the planning decisions, implementation, and the pre-commit benchmark exploration.

## Brief

> reward tunning from research 12

Source: `_output/research-logs/research-000012-reward-system-ghost-learning.md` — IQL ghosts converge to a stay-still policy (mean return −26 → −45, 0/50 eval wins).

## Q&A / Decision Log

### Q1 — R1 mechanism: how to kill the stay-still trap?

Research-12 R1 offered two mechanisms. **Decision: potential-based shaping (true distance).**
Replace the stale `last_pacman_sighting_position` distance term with `F(s) = -POTENTIAL_SHAPING_ALPHA * min_bfs(ghosts → TRUE Pacman)`, reward `F(s')−F(s)`. Policy-invariant (Ng et al. 1999); dense gradient even when Pacman is unseen. Trade-off accepted: reward uses privileged true position (policy still acts on local 5×5 view only).

### Q2 — Include R3 exploration bump?

R3 raises `VALID_MOVE` and `ENTER_RECENTLY_UNVISITED_TILE`, which plan-000008 had deliberately trimmed. **Decision: include the full R3 bump** (VALID_MOVE 0.01→0.05, ENTER_UNVISITED 0.05→0.15).

### Q3 — Extra scope beyond the core reward change?

**Decision: R4 calibration test only.** Excluded: R2 (training budget — CLI, separate), R5 (per-term training CSV — out of reward-tuning scope), R6/R7/R8.

### Q4 — Commit, or run a benchmark first?

**Decision: run a benchmark before committing** (user request). Ran IQL seed 0, 60k frames, CPU (same budget that exhibited the failure).

### Q5 — After validation, commit or probe further?

**Decision: hold / inspect, then explore the results together.** Examined the per-term reward breakdown and the full 301-point return trajectory.

### Q6 — How to handle the late-training collapse?

**Decision: just commit the fix.** The core goal (break the stay-still trap) is proven; late-stability is a separate budget/tuning concern, filed as follow-up pa-000011.

## Implementation

5/5 steps, manual mode. Files:
- `custom_environment/env/domain/constant.py` — `POTENTIAL_SHAPING_ALPHA = 0.5`; R3 bumps; deprecated `DISTANCE_DECREASE/INCREASE`.
- `custom_environment/env/pacman_environment.py` — `last_potential` state; potential-based shaping in `_compute_team_reward()`.
- `test/test_reward_calibration.py` (new) — move-toward > stay, move-toward > move-away.

Tests: **27/27 passing** (2 new).

## Validation Findings (IQL 60k, CPU, full 301-point trajectory)

**Core fix works — stay-still trap broken:**
- **16 capture-level batches (>30)** vs **0** in the research-12 baseline.
- First ~150 iters: mean return +10 to +17 (vs baseline −26 → −45 collapse).

**Known limitation (follow-up pa-000011): late collapse.**
- After iter ~150 the policy degrades — captures vanish, mean → ~−20 by iter ~260.
- Per-term breakdown (random policy): `recently_unvisited_tile` +14.9, `valid_move` +11.4, `potential_shaping` +7.9 — R3 exploration terms outweigh pursuit; greedy late policy may optimize wandering over capture.
- Two non-exclusive causes: budget too small (research R2, ε-floor ~iter 240) and R3 over-bump. Collapse onset (~150) precedes ε-floor (~240), implicating R3 at least partially.

Diagnostic scripts (temp, not committed): `_output/tmp/reward_breakdown_diag.py`, `_output/tmp/analyze_run.py`.

## Outcome

plan-000021 committed. Follow-up pa-000011 (`tune-late-stability`) filed to diagnose budget vs R3 over-bump.
