# Research 000001 | fernanda-INF2072 | 2026-06-13 19:02 UTC | Pallet system and reward design
tags: reward-shaping, environment-design, pacman, pallet-system, marl
spawned: plan-000003

## User Brief

"Research this codebase in order to understand how it works and the reward system. My current goal is to implement a pallet system (the points/coins that Pacman eats throughout the game) and update the reward system in order to account for this new mechanic (if Pacman eats all pallets, Pacman wins)."

## Agent Interpretation

Understand the current environment + reward architecture, then identify exactly what needs to change to add:
1. A functional pallet system (pallets consumed as Pacman moves, tracked in state)
2. A new terminal condition: all pallets eaten → Pacman wins (ghosts lose)
3. Reward signal reflecting this new mechanic

---

## Files Reviewed

- `custom_environment/env/pacman_environment.py` — main PettingZoo `ParallelEnv`
- `custom_environment/env/domain/constant.py` — `Observation`, `Action`, `Reward` enums
- `custom_environment/env/domain/agent.py`, `ghost.py`, `pacman.py` — agent dataclasses
- `custom_environment/utils.py` — `create_grid()`, `Graph`
- `custom_environment/env/rendering.py` — Pygame renderer

---

## Q&A Log

### Q1: How does the current environment work, and what is the reward system?

**Architecture overview:**

- **Grid**: 20×20 NumPy array (`global_view`), cells encoded as `Observation` enum values: `WALL=5`, `EMPTY=2`, `GHOST=3`, `PAC_MAN=4`, `CAPTURED=1`.
- **Agents**: Ghosts (`ghost_1`, `ghost_2`) are the *trainable* PettingZoo parallel agents. Pacman (`pacman`) is driven by a **random policy** internally — it is not an RL agent.
- **Episode flow**: Each `step()` call moves Pacman randomly first, then applies ghost actions from the policy. Termination: capture OR timeout (200 steps).
- **Reward**: A *shared team reward* is broadcast to every ghost at each step. The reward function (`_compute_team_reward`) computes a single scalar from ~12 shaping terms:

| Signal | Value | Condition |
|---|---|---|
| `TIMESTEP_PENALTY` | −0.01 | every step |
| `GET_PACMAN` | +20.0 | terminal: ghost catches Pacman |
| `PACMAN_TIMEOUT_WIN` | −20.0 | terminal: 200 steps elapsed without capture |
| `NEWLY_SPOTTED` | +1.0 | Pacman re-enters ghost FOV after ≥6 unseen steps |
| `CURRENTLY_VISIBLE` | +0.2 | Pacman visible to any ghost this step |
| `DISTANCE_DECREASE` | +0.3 | team BFS distance to last known Pacman position decreased |
| `DISTANCE_INCREASE` | −0.3 | team BFS distance increased |
| `VALID_MOVE` | +0.01 | ghost moved to a new cell |
| `INVALID_MOVE` | −0.08 | ghost hit a wall |
| `STAY_STILL` | −0.03 | ghost didn't move (no wall) |
| `ENTER_RECENTLY_UNVISITED_TILE` | +0.08 | ghost enters a tile not visited in 10 steps |
| `REVEAL_UNSEEN_LOCAL_CELLS` | +0.05 | ghost FOV reveals new unseen cell |
| `REPEATED_DIRECTION_REVERSAL` | −0.02× | consecutive back-and-forth movement |
| `GHOST_OVERLAP_OR_SAME_CORRIDOR` | −0.05 | two ghosts overlap or shadow each other |

**Pallet system (current state — visual only):**

The environment already has *partial* pallet infrastructure:
- `_pellet_mask`: a `bool` NumPy array (same shape as grid), `True` where a cell was `EMPTY` at episode start. Built by `_build_initial_pellet_mask()`.
- `_reset_visual_pellets()`: resets the mask each episode and clears starting positions of agents.
- `_consume_visual_pellet(position)`: sets `_pellet_mask[row, col] = False` whenever Pacman steps onto a cell.
- The renderer draws a small pellet dot on every tile where `pellet_mask[row, col]` is `True`.

**What is missing**: `_pellet_mask` only drives rendering. There is no:
- Total pallet count tracked per episode
- Check for "all pallets eaten" → Pacman wins terminal condition
- Reward signal reflecting pallet consumption

---

### Q2: What exactly needs to change to add the pallet system and Pacman-wins terminal condition?

**Summary of changes required:**

#### 1. `constant.py` — add a new Reward value

```python
PACMAN_WIN_PALLETS = -20.0  # Ghosts lose when Pacman eats all pallets
```

Symmetric to `PACMAN_TIMEOUT_WIN` — both represent Pacman winning.

#### 2. `pacman_environment.py` — track total pallets and detect win condition

**In `__init__` / `reset`:**

```python
# After _reset_visual_pellets():
self._total_pallets = int(self._pellet_mask.sum())
```

`_pellet_mask` at reset has `True` only for `EMPTY` cells not occupied by agents, so `sum()` gives the correct initial pallet count.

**In `step()` — add a third terminal condition:**

```python
pallets_all_eaten = (self._pellet_mask is not None) and (self._pellet_mask.sum() == 0) and (self._total_pallets > 0)
pacman_win_happened = pallets_all_eaten and (not capture_happened)
```

Then apply the penalty alongside the existing timeout penalty:

```python
if pacman_win_happened:
    team_reward += float(Reward.PACMAN_WIN_PALLETS.value)
```

And update truncations (or terminations — see design note below):

```python
for ghost in self.ghosts:
    truncations[ghost.id] = bool(timeout_happened or pacman_win_happened)
```

Update the agents-clearing condition:

```python
if any(terminations.values()) or all(truncations.values()):
    self.agents = []
```

#### 3. (Optional) Expose pallet progress in observations or global state

The current ghost observation is a 3×3 local FOV — pellet information isn't directly useful there. But the global state vector used by QMIX/VDN could include:

```python
pallets_remaining_norm = float(self._pellet_mask.sum()) / max(1, self._total_pallets)
```

This would give coordinating agents a signal about how urgent it is to capture Pacman before it clears the board.

**Design note — termination vs truncation:**

In PettingZoo:
- `termination=True` → natural episode end (goal achieved or failure within the rules)
- `truncation=True` → externally forced end (time limit exceeded)

"Pacman eats all pallets" is a legitimate episode-ending game rule, so `termination=True` is more semantically correct than `truncation`. Timeout and pallet-win are currently both handled as truncation for symmetry with the existing timeout logic, but either is acceptable for BenchMARL training.

---

## Recommendations Summary

| Priority | Recommendation |
|---|---|
| HIGH | Add `PACMAN_WIN_PALLETS = -20.0` to `Reward` enum in `constant.py` |
| HIGH | Track `self._total_pallets` on `reset()` from `_pellet_mask.sum()` |
| HIGH | In `step()`, detect `pallets_all_eaten` and trigger termination + apply `PACMAN_WIN_PALLETS` reward |
| MEDIUM | Add `pallets_remaining_norm` to `_build_global_state()` so QMIX/VDN agents can see board progress |
| LOW | Consider making pallet-win a `termination` (not `truncation`) for semantic correctness |

The `_pellet_mask` and `_consume_visual_pellet` machinery is already correct and complete — no changes needed there. The gap is only in the reward and terminal-condition logic.
