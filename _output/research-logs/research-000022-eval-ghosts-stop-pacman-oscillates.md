# Research 000022 | fernanda-INF2072 | 2026-06-20 22:37 UTC | Eval: ghosts stop, Pacman oscillates near view boundary
tags: pacman-policy, reward-shaping, eval-behavior, marl, ghost-training

## User Brief

> there is something strange when i run eval. the ghosts stop and the pac man move back and forth to be in the visible range of the phantom. but the pac man does not enter in the visible range more, nor get other pellets

## Agent Interpretation

Diagnose why, during eval, ghosts stop moving and Pacman oscillates near the ghost view boundary without collecting pellets. Identify root causes in the Pacman policy, ghost reward shaping, and the interaction between checkpoint policy and the current environment.

## Files Reviewed

- `custom_environment/env/domain/pacman_policy.py` — `PacmanPolicy.choose_action()` (lines 61–108)
- `custom_environment/env/domain/constant.py` — `Reward` enum, `PACMAN_SAFE_DISTANCE=5` (lines 23–65)
- `custom_environment/env/pacman_environment.py` — `_compute_team_reward()`, `_get_observation()`, `step()` (lines 203–280, 551–636)
- `custom_environment/eval.py` — eval loop (lines 397–544)
- `_output/research-logs/research-000012-reward-system-ghost-learning.md` — prior RC analysis (RC1: stale-sighting stay-still trap)

---

## Q&A Log

### Q1: Why do ghosts stop and Pacman oscillate near the view boundary?

**Short answer:** Three interacting root causes produce the deadlock. (1) The eval checkpoint was trained under the old stale-sighting reward (pre-plan-000021), which shaped a "stay still" Q-policy — the ghosts stop because they were rewarded for inaction. (2) The memoryless `PacmanPolicy` can enter a 2-cell oscillation saddle when both cells have identical safety scores and each cell's best pellet-progress move is the other. (3) `PACMAN_SAFE_DISTANCE=5` is much larger than the ghost view radius (2), so stopped ghosts block Pacman from most of the board.

---

### Root Cause Analysis

#### RC1 (Critical): Checkpoint learned "stay still" under the old reward — not yet retrained

The eval checkpoint was trained with `DISTANCE_DECREASE/INCREASE` (stale-sighting signal). As documented in research-000012 RC1, that signal had negative expected value for movement when Pacman was unseen (which is most of the time). The policy converged to inaction.

Plan-000021 replaced that signal with potential-based shaping — but this only affects **new training runs**. The frozen checkpoint still carries the old Q-values. Eval runs the frozen policy in the current environment; the policy outputs "stay still" regardless of the new reward signal.

**Evidence:** The reward-shaping redesign was applied to `pacman_environment.py` but the training run that would learn from it has not yet been started/completed.

#### RC2 (High): Memoryless Pacman policy enters 2-cell oscillation saddle

`PacmanPolicy.choose_action()` is stateless (no cross-step memory). Each step it picks the move with the best `(safety, -pellet_dist)` key.

The saddle condition:
1. Cell A and cell B are both `≥ PACMAN_SAFE_DISTANCE=5` BFS steps from any ghost → `safety=5` (cap) for both.
2. From A, the cell with highest pellet-progress is B. From B, the highest pellet-progress cell is A.
3. Pacman bounces A → B → A → B indefinitely.

This triggers when stopped ghosts create a region where: (a) all pellet-direction cells are inside the 5-cell danger zone, and (b) only two "safe" cells exist on either side of the ghost's position. The capping of `safety` at `PACMAN_SAFE_DISTANCE` is the enabler: once both cells are at the cap, safety no longer differentiates them.

#### RC3 (High): PACMAN_SAFE_DISTANCE=5 >> ghost view radius=2 → most pellets are blocked

| Constant | Value | Meaning |
|---|---|---|
| `PACMAN_SAFE_DISTANCE` | 5 cells (BFS) | Pacman's exclusion zone around any ghost |
| `GHOST_VIEW_SIZE` | 5×5 → radius 2 | Ghost can see Pacman only within 2 cells |
| Map size | 20×20 | 5-cell exclusion zone is ~25% of the map per ghost |

Pacman flees from a ghost it cannot be seen by (ghost detection range = 2, Pacman flee range = 5). Two stopped ghosts with 5-cell exclusion zones can cordon off large portions of the board. Pellets behind the cordon are unreachable under the safety-first policy — Pacman will never enter the danger zone even to access them.

#### RC4 (Medium): CURRENTLY_VISIBLE incentive trains ghosts to orbit, not capture

`CURRENTLY_VISIBLE = +0.3/step` with `STAY_STILL = -0.03/step` gives a net +0.27/step for camping with Pacman in view. This dominates the potential-shaping signal at short distances, creating a "orbit at view boundary" attractor even in newly trained policies. The ghost earns more by maintaining visual contact than by closing in for capture.

---

### Summary Table

| Root Cause | Effect | Severity |
|---|---|---|
| RC1: Stale checkpoint | Ghosts stop (learned inaction) | Critical |
| RC2: Stateless Pacman policy | Oscillation in 2-cell saddle | High |
| RC3: PACMAN_SAFE_DISTANCE >> view radius | Most board blocked for Pacman | High |
| RC4: CURRENTLY_VISIBLE too high | Trains orbit instead of capture | Medium |

---

## Recommendations Summary

**R1 (HIGH) — Retrain with plan-000021 reward.**
The visible behavior is a stale-checkpoint artifact. Run a new training session with the current potential-based reward. Until the checkpoint is updated, eval will always show the old stay-still ghost behavior. Use `make train-iql` (or equivalent) with `--checkpoint-at-end`.

**R2 (HIGH) — Add anti-oscillation state to `PacmanPolicy`.**
Track the last 2 positions. If the policy is about to return to a cell visited in the last 2 steps, add a small tiebreaker penalty (`-ε`) to that move. This breaks the A↔B saddle without changing safety-first priority.
File: `custom_environment/env/domain/pacman_policy.py`:61 — add `self._recent_positions: deque[tuple[int,int]] = deque(maxlen=2)` and subtract `ε=0.01` from the key when revisiting.

**R3 (MEDIUM) — Reduce `PACMAN_SAFE_DISTANCE` from 5 to 3.**
The ghost view radius is 2 cells. A 5-cell safety margin causes Pacman to avoid ghosts that cannot even observe it and blocks large parts of the board. Reducing to 3 keeps Pacman outside ghost detection range while freeing most of the board for pellet collection. File: `custom_environment/env/domain/constant.py`:65.

**R4 (MEDIUM) — Reduce or condition `CURRENTLY_VISIBLE` reward.**
`+0.3/step` creates a strong orbit incentive that can persist even after retraining. Consider reducing to 0.1, or making it conditional: `CURRENTLY_VISIBLE` only fires when the ghost also moved closer to Pacman this step (combine with `valid_move` and `potential_shaping > 0` guard).
File: `custom_environment/env/domain/constant.py`:39.

**R5 (LOW) — Verify ghost_view_size auto-detection in eval.**
Run eval with `--show-reward-breakdown` and `--render-mode ascii` to confirm observations are consistent with the training view size. Mismatched view sizes cause observation distribution shift (the policy was trained on one view size, evaluated on another).
