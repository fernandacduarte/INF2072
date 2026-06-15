# Plan 000003 | FEATURE fernanda-INF2072 | 2026-06-15 16:38 UTC | Pallet system and reward update | Review: light
plan_format_version: 1
source: research-000001

## User Brief

"Research this codebase in order to understand how it works and the reward system. My current goal is to implement a pallet system (the points/coins that Pacman eats throughout the game) and update the reward system in order to account for this new mechanic (if Pacman eats all pallets, Pacman wins)."

## Agent Interpretation

**Problem**: The environment's `_pellet_mask` drives rendering but has no effect on game logic — there is no pallet-count tracking, no "all pallets eaten" terminal condition, and no reward signal for the new mechanic.

**Approach**: Extend the existing infrastructure minimally — `_pellet_mask` and `_consume_visual_pellet` are already correct, so the only gaps are (1) a new `Reward` enum value, (2) `_total_pallets` tracking on `reset()`, (3) a third terminal condition in `step()`, and (4) optionally surfacing pallet progress in the global state for QMIX/VDN.

**Selection rationale** (from research-000001):
- Included: R1 — Add `PACMAN_WIN_PALLETS` to `Reward` enum; minimal and necessary.
- Included: R2 — Track `self._total_pallets` on `reset()`; zero-risk addition after `_reset_visual_pellets()`.
- Included: R3 — Detect `pallets_all_eaten` and apply terminal condition + reward in `step()`; core feature.
- Included: R4 — Add `pallets_remaining_norm` to `_build_global_state()` so VDN/QMIX agents can see board progress; low-cost signal that helps coordination.
- Deferred: R5 — Change pallet-win from `truncation` to `termination`; either is valid for BenchMARL training, and matching the existing timeout pattern (also `truncation`) keeps the step() logic consistent for now.

## Best Practices

- Match the pattern of the existing `PACMAN_TIMEOUT_WIN` for symmetry (same magnitude, same truncation style).
- Guard the pallet-win check with `not capture_happened` to preserve capture priority.
- Keep `_total_pallets` updated only on `reset()` — it is an episode-level constant.
- Add `pallets_remaining_norm` at the end of `_build_global_state()` to avoid invalidating `_state_dim`; update `_state_dim` in `__init__` to +1.

## Design Decisions

**User-visible impact**: Episodes can now end with a Pacman-wins outcome when all pallets are consumed. Ghost agents receive a −20 reward (same magnitude as timeout loss). The global state vector gains one additional normalized feature, which means saved checkpoints trained without this feature are incompatible unless re-trained.

**Trade-offs accepted**: Adding `pallets_remaining_norm` to the state increases `_state_dim` by 1 — existing checkpoints must be re-trained. This is acceptable at the current research stage and is the reward of giving coordinating algorithms visibility into the threat level. The alternative (not adding the state feature) would leave QMIX/VDN blind to pallet progress, reducing the value of the new mechanic for coordination research.

**Metacommunication impact**: The system now communicates to ghost agents that there is a third way to lose (pallet exhaustion), not only timeout and capture. This shapes the trained policy — agents must balance pursuit with patrol coverage to prevent Pacman from clearing the board.

---

## Steps

### Step 1: Add `PACMAN_WIN_PALLETS` to the `Reward` enum

Add a new enum member `PACMAN_WIN_PALLETS = -20.0` to the `Reward` class in `constant.py`, immediately after `PACMAN_TIMEOUT_WIN`. This value represents the ghost team's penalty when Pacman eats all pallets and wins.

- **Files**: `custom_environment/env/domain/constant.py` (modify)
- **References**: N/A
- **Interface**: `Reward.PACMAN_WIN_PALLETS` — float value `−20.0`, accessible as `Reward.PACMAN_WIN_PALLETS.value`
- **Verify**: `python -c "from custom_environment.env.domain.constant import Reward; assert Reward.PACMAN_WIN_PALLETS.value == -20.0"` passes
- **Tests**: N/A — enum value addition; covered by Step 3's integration test
- [ ] Done

### Step 2: Track total pallet count on episode reset

In `pacman_environment.py`, after the call to `self._reset_visual_pellets()` inside `reset()`, add:

```python
self._total_pallets = int(self._pellet_mask.sum()) if self._pellet_mask is not None else 0
```

This captures the per-episode pallet count from the already-correct `_pellet_mask`. No change needed to `_consume_visual_pellet` — it already decrements the mask correctly.

Also initialize `self._total_pallets = 0` in `__init__` (before `_pellet_mask` is built) to avoid attribute errors if `state()` is called before the first `reset()`.

- **Files**: `custom_environment/env/pacman_environment.py` (modify)
- **References**: N/A
- **Depends on**: Step 1
- **Interface**: `self._total_pallets` — episode-level int, read-only after `reset()`
- **Verify**: After `env.reset()`, `env._total_pallets > 0` for a standard grid
- **Tests**: N/A — internal state; verified by Step 3's integration test
- [ ] Done

### Step 3: Detect pallet-win terminal condition in `step()` and apply reward

In `step()`, after computing `capture_happened` and `timeout_happened`, add:

```python
pallets_all_eaten = (
    self._pellet_mask is not None
    and self._total_pallets > 0
    and int(self._pellet_mask.sum()) == 0
)
pacman_win_happened = pallets_all_eaten and not capture_happened
```

Then, alongside the existing timeout reward block, add:

```python
if pacman_win_happened:
    team_reward += float(Reward.PACMAN_WIN_PALLETS.value)
```

Update truncations to include the new outcome:

```python
truncations[ghost.id] = bool(timeout_happened or pacman_win_happened)
```

The existing `if any(terminations.values()) or all(truncations.values()): self.agents = []` block already handles this correctly and needs no change.

- **Files**: `custom_environment/env/pacman_environment.py` (modify)
- **References**: `project/standards.md § Testing`
- **Depends on**: Step 1, Step 2
- **Interface**: N/A
- **Verify**: `py -3.11 -m pytest test/test_petting_zoo.py` passes; manually confirm episode terminates when pellet mask is all-False
- **Tests**: Add `test/test_pallet_win.py` with a smoke test: build a minimal 3×3 grid with one EMPTY cell, reset the env, manually consume that pellet via `_consume_visual_pellet`, call `step()` with any actions, and assert `truncations` are `True` and `rewards` equal `Reward.PACMAN_WIN_PALLETS.value + Reward.TIMESTEP_PENALTY.value`.
- [ ] Done

### Step 4: Expose pallet progress in global state

In `_build_global_state()`, before the final `state_vector = np.asarray(...)` assembly, compute:

```python
pallets_remaining_norm = (
    float(int(self._pellet_mask.sum())) / float(max(1, self._total_pallets))
    if self._pellet_mask is not None and self._total_pallets > 0
    else 1.0
)
```

Append `pallets_remaining_norm` to the feature list at the end of the `state_vector` concatenation.

In `__init__`, update `_state_dim` from `(rows * cols) + (3 * len(self.possible_agents)) + 7` to `+ 8` (one extra feature).

- **Files**: `custom_environment/env/pacman_environment.py` (modify)
- **References**: N/A
- **Depends on**: Step 2
- **Interface**: N/A
- **Verify**: After `env.reset()`, `env.state().shape[0] == env._state_dim` with the updated value; `env.state()[-1]` equals `1.0` at episode start (all pallets present)
- **Tests**: Add assertion to `test/test_pallet_win.py`: after consuming all pellets, `env.state()[-1] == 0.0`
- [ ] Done

---

## Outcomes

- Episodes terminate with a Pacman-wins outcome when all pallets are consumed.
- Ghost agents receive `PACMAN_WIN_PALLETS = −20.0` reward for this outcome, symmetric with the timeout loss.
- QMIX/VDN agents have access to `pallets_remaining_norm` in the global state, enabling coordination strategies that account for board clearance urgency.
- All existing tests remain passing; new `test_pallet_win.py` smoke test validates the new terminal condition end-to-end.

**smoke**: false

---

## Review Log

**Depth**: light (3 action steps, touches 2 files — below light threshold of ≤6 steps / ≤4 files)

**Step metadata validation**: all steps pass — Files, Interface, Verify, Tests present; Dependencies flow forward (2→3, 2→4); no step touches >5 files; no circular dependencies.

**Perspectives reviewed** (shortlist for FEATURE / environment extension):

| Perspective | Status | Note |
|---|---|---|
| CORRECTNESS | Adopted | Pallet-win guard (`not capture_happened`) preserves capture priority; `_total_pallets > 0` prevents false trigger on grids without pellets |
| TEST | Adopted | Dedicated smoke test in Step 3/4; existing PettingZoo API test still covers protocol compliance |
| PERF | Adopted | `_pellet_mask.sum()` called once per step — O(N) on a 20×20 grid = 400 ops; negligible |
| DX | Adopted | State dim comment updated inline; no new public API surface; change is additive |
| SECURITY | N/A | Local research CLI, no attack surface affected |
| I18N | N/A | No user-visible text added |

**Execution metrics**:

| Metric | Value |
|---|---|
| Perspectives loaded | 4 |
| Perspectives N/A | 2 |
| Deferred concerns | 0 |
| Phase 2 deep-dives | 0 (light depth) |
| Iterations | 1 |
