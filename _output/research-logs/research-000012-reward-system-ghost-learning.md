# Research 000012 | fernanda-INF2072 | 2026-06-20 16:29 UTC | Reward system and ghost learning failure
tags: reward-shaping, irl-training, marl, credit-assignment, exploration

## User Brief

> current reward system and impact into training. ive runned benchmark and seesn like the ghosts are not learning. ran eval and at some point the ghosts just stay still near each other

## Agent Interpretation

Diagnose why IQL ghosts converge to a "stay still" policy during training (mean return degrades from -26 to -45 over 300 iterations; 0% ghost win rate in 50 eval episodes). Identify root causes in the reward function design and training configuration, and produce ranked actionable recommendations.

## Files Reviewed

- `custom_environment/env/pacman_environment.py` — `_compute_team_reward()` (lines 555–617)
- `custom_environment/env/domain/constant.py` — `Reward` enum (lines 23–43)
- `benchmarl_setup/run_pacman_benchmarl.py` — training configuration (lines 29–169)
- `custom_environment/utils.py` — map layouts, map size (20×20)
- `benchmarl_setup/runs/iql_win_rate.csv` — 0/50 wins
- `benchmarl_setup/runs/iql_train_000008.log` — reward divergence log

---

## Q&A Log

### Q1: Why are ghosts not learning and ending up staying still near each other?

**Short answer:** The reward function creates a *stay-still local optimum* because the DISTANCE_INCREASE penalty fires unpredictably on a **stale sighting position**, making random movement systematically worse in expected value than doing nothing. Combined with a training budget 10–30× too small and an opponent (BFS-Pacman) too strong for the current observation conditions, the ghosts converge to inaction.

---

### Root Cause Analysis

#### RC1 (Critical): Stale-sighting distance signal creates a "stay still" trap

**How it works:** `_compute_team_reward()` tracks `last_pacman_sighting_position` — where Pacman was last seen by *any* ghost. Every step, it measures the minimum ghost BFS-distance to this cached position and emits:
- `DISTANCE_DECREASE = +0.5` if the distance shrank
- `DISTANCE_INCREASE = -0.5` if the distance grew

**The problem:** Pacman is almost never visible. With a 5×5 ghost view (view_radius=2) on a 20×20 map, each ghost covers ~6.25% of the grid. The BFS-evasion PacmanPolicy (PACMAN_SAFE_DISTANCE=5) actively flees when ghosts come within 5 cells. So the majority of steps use a **stale** sighting. By that time, Pacman has moved to a completely different location.

**Expected value calculation:**
- `EV(move)` ≈ VALID_MOVE(+0.01) + ENTER_UNVISITED(+0.05 × p_unvisited) - DISTANCE_INCREASE(0.5 × q)
  - Where `q` = probability the stale position is in the "wrong" direction (ghost moves away from stale position). Given Pacman's BFS evasion, `q` is likely 0.5–0.8 in practice.
  - Even at `q = 0.2`: EV(move) ≈ 0.06 - 0.10 = -0.04 < EV(stay) = -0.03
- **Conclusion:** Moving is worse in expectation than staying still. Ghosts rationally learn to stand still.

This is a classic *reward shaping pathology*: the shaping signal is anti-correlated with correct behavior in the most common world state (Pacman not visible).

#### RC2 (High): Training budget is 10–30× too small

- 60k frames / 200 steps per episode ≈ **300 total episodes**
- IQL on cooperative MARL problems typically needs **1M–10M steps** (e.g., SMAC benchmark results)
- 0/300 episodes captured → the terminal +30 reward **never fires** → zero positive gradient
- Discounted value of +30 at episode start: `30 × 0.99^200 ≈ 0.45` — smaller than shaping noise even if capture happened
- **Evidence:** The training log shows reward diverging monotonically from -26 to -50, a signature of pure penalty accumulation with no offsetting positive signal.

#### RC3 (High): Terminal +30 is unreachable from scratch, and credit cannot propagate

With 200-step episodes and the stale-sighting trap, capture never occurs. IQL's TD learning cannot propagate the +30 terminal signal backward because:
1. The signal never fires (0 captures in 300 episodes)
2. Even if it did, Q-value propagation over 200 steps requires many visits, not achievable in 300 episodes

This means the policy gradient is driven entirely by the step-level shaping signals — which are dominated by DISTANCE_INCREASE (-0.5) firing on bad targets.

#### RC4 (Medium): Opponent too strong for the current observation conditions

- BFS-evasion with PACMAN_SAFE_DISTANCE=5 + 20×20 open map → near-optimal evasion
- Ghost view 5×5 → 6% map coverage per ghost → Pacman is rarely visible
- IQL (no communication) → ghosts cannot coordinate search
- This is close to the *hardest* version of the problem: highly capable opponent vs. nearly-blind, non-communicating agents from scratch

#### RC5 (Low): GHOST_OVERLAP_OR_SAME_CORRIDOR adds noise for IQL

The -0.05 overlap penalty discourages ghosts from being close or moving in parallel. Without communication, IQL ghosts cannot coordinate spatial positioning — this penalty just adds noise to an already confusing signal. It is more meaningful for QMIX (centralized critic) than IQL.

---

### Why the training curve gets *worse* over time

Early training (random policy): occasional captures by accident → rare +30 spikes. The log shows positive returns at iterations 33, 48, 69, 84, 86, 97, 108, 132, etc. As IQL learns to avoid *some* penalties, it adopts progressively more conservative (less random) movement. This reduces lucky captures and increases time spent in the DISTANCE_INCREASE/STAY_STILL penalty regime → mean return degrades monotonically after ~iteration 150.

---

## Recommendations Summary

Ordered by impact. Address sequentially — later items are only needed if earlier fixes don't resolve learning.

**[R1 — HIGH] Fix the stale-sighting distance signal**

Disable `DISTANCE_DECREASE/INCREASE` when Pacman has not been seen recently. The cleanest fix: only apply these signals when `any_visible is True` (Pacman is currently visible to at least one ghost). When not visible, rely on exploration bonuses to drive movement.

```python
# In _compute_team_reward(), in the distance block (lines ~579–587):
# Change:
#   if target_position is not None:
#       min_distance = ...
#       if min_distance < self.last_target_min_distance:
#           add_term("distance_decrease", ...)
#       elif min_distance > ...:
#           add_term("distance_increase", ...)
# To:
if any_visible and target_position is not None:
    min_distance = ...
    if min_distance < self.last_target_min_distance:
        add_term("distance_decrease", ...)
    elif min_distance > ...:
        add_term("distance_increase", ...)
```

Alternative (stronger): Use potential-based shaping with *true* Pacman distance (available to the reward function even if not in the agent's observation). `F(s) = -α × min_bfs_distance_to_pacman`, reward = `F(s') - F(s)`. This is policy-invariant per Ng et al. (1999) and provides a smooth gradient toward capture.

**[R2 — HIGH] Increase training budget**

Minimum viable: 500k frames (2,500 episodes). Target for comparison-quality results: 2M frames. The default 60k is a smoke-test budget, not a learning budget. Add to CLI:

```bash
py -3.11 benchmarl_setup/run_pacman_benchmarl.py --algorithm iql --max-frames 500000
```

**[R3 — HIGH] Balance exploration incentives**

Raise `VALID_MOVE` and `ENTER_RECENTLY_UNVISITED_TILE` so EV(move) > EV(stay) even without approach signal:

```python
VALID_MOVE                    = 0.05   # was 0.01
ENTER_RECENTLY_UNVISITED_TILE = 0.15   # was 0.05
```

This ensures ghosts always have a positive incentive to explore rather than freezing.

**[R4 — MEDIUM] Add a reward-calibration unit test**

Test that `EV(move toward known Pacman location) > EV(stay)` under the current reward function. This would have caught the stale-sighting regression before any training run:

```python
# test/test_reward_calibration.py
def test_move_toward_pacman_is_better_than_staying():
    # Set up env with Pacman 3 cells from ghost, ghost knows sighting
    # Assert team_reward(move_toward) > team_reward(stay_still)
```

**[R5 — MEDIUM] Add per-term reward logging to training CSV**

Log mean episode contribution of each reward term to the run CSV. Without this, diagnosing which term dominates is impossible from the outside. Implementation: pass `last_team_reward_breakdown` to the telemetry at each episode end.

**[R6 — MEDIUM] Use a training curriculum for debugging**

Phase 1: stationary Pacman → Phase 2: random-walk Pacman → Phase 3: BFS-evasion Pacman. Promote phases at >20% ghost win rate. This decouples reward design from difficulty calibration.

**[R7 — LOW] Increase ghost view radius for initial experiments**

Change `GHOST_VIEW_SIZE = 5` to `7` or `9` to give ghosts more spatial awareness. With 6% map coverage, Pacman is near-invisible. This is optional once R1 is fixed and should be reverted for the final benchmark if the research question specifically targets partial observability.

**[R8 — LOW] Consider removing GHOST_OVERLAP_OR_SAME_CORRIDOR for IQL runs**

IQL cannot coordinate spatial positions without communication. This penalty adds noise without teaching useful coordination. Keep it for VDN/QMIX experiments where the centralized critic can learn joint positioning.

---

## Implementation priority

If only one change is made: **R1** (fix stale-sighting distance signal). This is the mechanical cause of the stay-still optimum. It is a 2-line code change with high expected impact.

If two changes: **R1 + R3** (also boost exploration incentives). Together these ensure movement is always preferred over inaction.

For a proper training run with results worth reporting: **R1 + R3 + R2** (fix signal, boost exploration, increase budget to 500k frames).
