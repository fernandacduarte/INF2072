# Plan 000025 | fernanda-INF2072 | 2026-06-27 21:57 UTC | Reintroduce pure PBRS reward variant | Review: light
plan_format_version: 1
source: research-000024

## User Brief

> Reintroduce pure potential-based reward shaping (PBRS) as a new reward variant on the sparse capture_v0 base, per research-000024. Requirements: (1) New RewardStrategy subclass in custom_environment/env/rewards/current.py registered in loader.py, keeping the capture_v0 sparse terminals (GET_PACMAN +100, timeout -100, pellet-win -100) + timestep -0.01, and ADDING a telescoping PBRS term F = gamma*Phi(s') - Phi(s) with Phi = -alpha*(d1 + 0.5*d2) (team BFS distance to true Pacman position, reusing _team_distance / _bfs_distance). (2) gamma=0.99 must be a documented weight; do NOT use the legacy gamma=1 telescoping. (3) Phi=0 at capture (BFS dist 0) and emit the +alpha*dist pulse; do NOT zero Phi at timeout (treat as truncation). (4) Drop the reverse_action penalty entirely from this variant. (5) alpha as a documented weight, default ~0.5-0.9. (6) Add unit tests asserting: capture transition yields +alpha*dist_before shaping pulse, timeout yields no spurious -Phi term, and per-step PBRS magnitude sits between timestep cost and the terminal. Keep d1+0.5*d2 team distance (ablation vs min-distance is out of scope for this plan). source: research-000024

## Agent Interpretation

- **Problem**: The current `capture_v0_improve_legal_moves...reverse_action` reward has no distance gradient, so trained ghosts do not pursue Pacman (research-000024 diagnosis). We need a new reward variant that adds a dense, theoretically policy-invariant pursuit signal.
- **Approach**: Add one new `RewardStrategy` subclass (`CaptureV0PurePotentialShaping`) layered on the sparse `capture_v0` terminals + `timestep`, plus a γ-correct telescoping PBRS term over team BFS distance `Φ = −α·(d1 + 0.5·d2)`. The strategy subclasses `CaptureV0Reward` to inherit `_bfs_distance` and the sparse-terminal scaffolding, defines its own `compute`/`reset`, and is registered in `loader.py` + exported from `__init__.py`. No environment changes — `compute()` already runs on the capturing transition (BFS dist 0 ⇒ Φ=0 ⇒ the +α·dist pulse emerges naturally) and the strategy adds no special terminal-zeroing, so timeout is not zeroed by construction.
- **Alternatives rejected**:
  - *Edit the existing `CaptureV0ImproveLegalMoves...` class in place* — rejected: keeping the old sparse variant intact preserves the A/B baseline (research-000024 R5) and reproducibility of prior runs.
  - *Reuse `CurrentTeamReward` (the legacy PBRS class)* — rejected: it carries γ=1 telescoping, visibility/coordination/anti-cycle terms, and the `reverse_action`-adjacent penalties the research said to drop; not "pure" PBRS.
  - *Make γ/α read from the BenchMARL trainer config* — rejected as scope creep; they are documented dataclass weights here (γ default 0.99 matches the trainer's `gamma`).
- **Selection rationale** (source: research-000024):
  - Included: R1 — new pure-PBRS variant on sparse base (this plan's core).
  - Included: R2 — γ factor `F = γΦ(s′) − Φ(s)`, γ=0.99 documented weight.
  - Included: R3 — `reverse_action` dropped (absent from the new class).
  - Included: R4 — Φ=0 at capture (emit pulse); no Φ-zeroing at timeout; unit tests for both.
  - Included (partial): R6 — α a documented weight (default 0.7); the `min`-vs-`d1+0.5·d2` ablation is explicitly out of scope per the brief.
  - Excluded: R5 — the ≥5-seed A/B run is an experiment-execution task, not a code change; deferred to a separate benchmark run after this lands.
  - Excluded: R7 — deleting the dead commented PBRS code is a separate cleanup; out of scope to keep this diff minimal.

## Files

- `custom_environment/env/rewards/current.py` — Modified: add `CaptureV0PurePotentialShapingWeights` dataclass + `CaptureV0PurePotentialShaping(CaptureV0Reward)` class.
- `custom_environment/env/rewards/loader.py` — Modified: register `capture_v0_pure_potential_shaping` in `_REWARD_CLASS_BY_ID`.
- `custom_environment/env/rewards/__init__.py` — Modified: import + `__all__` export of the new class.
- `test/test_reward_strategies.py` — Modified: add unit tests for the new variant.

## Best Practices

- **Potential-based reward shaping (Ng, Harada & Russell 1999)**: `F(s,a,s′) = γΦ(s′) − Φ(s)` is the only form that guarantees the optimal policy is unchanged. γ must match the trainer's discount (0.99).
- **CTDE privileged signal**: Φ uses the simulator's true Pacman position; this is a training-time reward signal only — ghost policies still observe only their partial local view. Document this in the class docstring.
- **Episode-scoped state**: `_last_potential` is reset per episode in `reset()`; strategies are deepcopied per-env by the loader, so no cross-env leakage.
- **Auditable decomposition**: emit the PBRS contribution as a named `RewardTerm("potential_shaping", ...)` so it appears in `reward_breakdown_per_step_mean_json` and eval reports.

## Design Decisions

- **User-visible impact**: A new selectable reward id `capture_v0_pure_potential_shaping` becomes available via `--reward-id` / `REWARD_ID`. No existing variant changes; existing checkpoints and runs are unaffected.
- **Trade-offs accepted**: Gained — a clean, citable, policy-invariant dense pursuit signal usable in the report. Given up — the legacy visibility/coordination shaping terms (intentionally, for theoretical purity); the `min`-distance coordination ablation (deferred).
- **Metacommunication impact**: Eval/training reward breakdowns will now surface a `potential_shaping` term for this variant, communicating to the researcher how much dense pursuit signal accrued per step (between the −0.01 timestep cost and the ±100 terminal).

## Steps

### Step 1 — Add the pure-PBRS reward class and weights
- [ ] Add `CaptureV0PurePotentialShapingWeights` dataclass and `CaptureV0PurePotentialShaping(CaptureV0Reward)` to `current.py`.
- **Files**: `custom_environment/env/rewards/current.py`
- **References**: `CaptureV0Reward` (current.py:499–601) for sparse terminals + `_bfs_distance`; `CurrentTeamReward._team_distance`/`_reachable_distances` (current.py:437–458) for the `d1+0.5·d2` pattern; `base.py` `RewardContext`/`RewardTerm`.
- **Interface**: exports class `CaptureV0PurePotentialShaping` with `strategy_id = "capture_v0_pure_potential_shaping"`; weights dataclass with fields `get_pacman=100.0, pacman_timeout_win=-100.0, pacman_win_pellets=-100.0, timestep=-0.01, potential_shaping_alpha=0.7, potential_second_ghost_weight=0.5, gamma=0.99`.
- **Implementation notes**:
  - `__init__(self, weights=None)`: store weights; `self._last_potential: float | None = None`.
  - `reset(self, initial_context)`: `self._last_potential = None`.
  - `compute(self, context)`:
    1. `terms = [RewardTerm("timestep", w.timestep)]`.
    2. if `context.capture_happened`: append `RewardTerm("GET_PACMAN", w.get_pacman, "terminal")`.
    3. `team_distance = self._team_distance(context)`; if not None: `potential = -w.potential_shaping_alpha * float(team_distance)`; if `self._last_potential is not None`: append `RewardTerm("potential_shaping", w.gamma * potential - self._last_potential)`; set `self._last_potential = potential`.
    4. if `context.timeout_happened`: append `RewardTerm("PACMAN_TIMEOUT_WIN", w.pacman_timeout_win, "terminal")`.
    5. if `context.pacman_win_happened`: append `RewardTerm("PACMAN_WIN_PALLETS", w.pacman_win_pellets, "terminal")`.
    6. return `RewardResult(tuple(terms))`.
  - Add a `_team_distance(self, context) -> float | None` method (copy the `d1 + 0.5·d2` logic from `CurrentTeamReward._team_distance` + `_reachable_distances`, using inherited static `_bfs_distance`). No `reverse_action`, no visibility terms, no movement terms.
  - Docstring states: pure PBRS (Ng 1999) `F = γΦ(s′) − Φ(s)`; Φ uses privileged true Pacman position (CTDE training-time signal only).
- **Verify**: `py -3.11 -c "from custom_environment.env.rewards.current import CaptureV0PurePotentialShaping; s=CaptureV0PurePotentialShaping(); print(s.strategy_id, s.weights.gamma, s.weights.potential_shaping_alpha)"` prints `capture_v0_pure_potential_shaping 0.99 0.7`.
- **Tests**: When `compute` runs on a non-terminal step after a prior step, it returns a `potential_shaping` term equal to `γ·(−α·d_now) − (−α·d_prev)`. (test in Step 4)

### Step 2 — Register the new id in the loader
- [ ] Add `"capture_v0_pure_potential_shaping": "custom_environment.env.rewards.current:CaptureV0PurePotentialShaping"` to `_REWARD_CLASS_BY_ID`.
- **Files**: `custom_environment/env/rewards/loader.py`
- **References**: `_REWARD_CLASS_BY_ID` (loader.py:16–29).
- **Interface**: `reward_class_from_id("capture_v0_pure_potential_shaping")` resolves to the new class path.
- **Verify**: `py -3.11 -c "from custom_environment.env.rewards.loader import load_reward_strategy, reward_class_from_id; print(type(load_reward_strategy(reward_class_from_id('capture_v0_pure_potential_shaping'))).__name__)"` prints `CaptureV0PurePotentialShaping`.
- **Tests**: loader resolves the new id (test in Step 4).

### Step 3 — Export the class from the package
- [ ] Add the class to the `current` import block and `__all__` in `__init__.py`.
- **Files**: `custom_environment/env/rewards/__init__.py`
- **References**: existing import block (`__init__.py:10–16`) and `__all__` (23–37).
- **Interface**: `from custom_environment.env.rewards import CaptureV0PurePotentialShaping` succeeds.
- **Verify**: `py -3.11 -c "from custom_environment.env.rewards import CaptureV0PurePotentialShaping; print('ok')"` prints `ok`.
- **Tests**: covered by the import in Step 4's test module.

### Step 4 — Unit tests for PBRS correctness
- [ ] Add tests to `test/test_reward_strategies.py` following the existing `_context()` builder pattern.
- **Files**: `test/test_reward_strategies.py`
- **References**: `_context()` helper (test_reward_strategies.py:26–52); loader-resolution tests (83–90).
- **Interface**: N/A (tests only).
- **Implementation notes** — add these tests (build small `RewardContext` objects with a known wall layout so BFS distances are deterministic; for a 1-D corridor `board_shape=(1, N)` with no walls, BFS distance = |Δcol|):
  1. `test_loader_resolves_pure_pbrs_id` — `reward_class_from_id` resolves and `strategy_id == "capture_v0_pure_potential_shaping"`.
  2. `test_pure_pbrs_telescoping_term` — `reset` then two `compute` calls with the ghost moving from distance d_prev to d_now; assert the second call's `potential_shaping` term ≈ `γ·(−α·d_now) − (−α·d_prev)` (use `pytest.approx`). First call after reset emits **no** `potential_shaping` term (`_last_potential` was None).
  3. `test_pure_pbrs_capture_pulse` — context where the ghost reaches Pacman (`ghost.current_position == pacman_position`, `capture_happened=True`) after a prior step at distance d_prev; assert breakdown contains `GET_PACMAN == 100.0` AND `potential_shaping ≈ +α·d_prev` (since γ·0 − (−α·d_prev) ... note the γ factor makes the prior potential the only surviving term; assert it equals `−self._last_potential` i.e. `+α·d_prev`).
  4. `test_pure_pbrs_timeout_no_phi_zeroing` — a `timeout_happened=True` step where Pacman is still at distance d>0; assert the `potential_shaping` term uses the **real** distance (`γ·(−α·d_now) − (−α·d_prev)`), NOT a forced `+α·d_prev` zeroing pulse; assert `PACMAN_TIMEOUT_WIN == -100.0` present.
  5. `test_pure_pbrs_magnitude_bounds` — for a one-tile distance change, assert `abs(potential_shaping) > abs(timestep)` (0.01) and `abs(potential_shaping) < abs(get_pacman)` (100).
  6. `test_pure_pbrs_has_no_reverse_action_term` — assert no `reverse_action` key appears in the breakdown across a multi-step rollout.
- **Verify**: `py -3.11 -m pytest test/test_reward_strategies.py -q` passes.
- **Tests**: this step IS the tests.

## Review Log

**Complexity gate**: 4 action steps, touches 4 files → **Light** (≤6 steps AND ≤4 files). Floor = `light`. No `--review` override. Effective depth = **light** → Phase 1 only, inline.

**Phase 1 — Perspective triage (prefix FEATURE/additive; shortlist):**

| Perspective | Status | Concern / Note |
|---|---|---|
| ARCH (RL-theory correctness) | Adopted | γ-correct telescoping; Φ=0-at-capture verified via env (compute runs on capturing transition); no terminal-zeroing ⇒ timeout not zeroed. Sound. |
| TEST (testability) | Adopted | Deterministic BFS via 1-D corridor contexts; 6 targeted tests cover telescoping, capture pulse, timeout non-zeroing, magnitude bounds, no-reverse, loader. |
| DX (maintainability) | Adopted | New class mirrors existing `CaptureV0*` shape; weights are a documented frozen dataclass; old variant untouched (A/B preserved). |
| REUSE | Adopted | Reuses inherited `_bfs_distance`; copies the small `d1+0.5·d2` logic from `CurrentTeamReward` (acceptable duplication to keep the pure variant self-contained; full consolidation deferred per research R7). |
| PERF | N/A | BFS already runs in the legacy variants at the same board scale; no new hot path. |
| SEC / A11Y / DATA | N/A | No web/UI/PII/secrets surface; privileged true-position use is a documented training-time signal. |

**Deferred concern (noted, out of scope):** The environment reports timeout as `terminations=True, truncations=False` (pacman_environment.py:385–386). For strict PBRS invariance under a time-limit, timeout should bootstrap (truncation) rather than terminate. This is a pre-existing environment design choice independent of the reward strategy and is **out of scope** for this plan; flagged for a possible follow-up. The reward strategy itself correctly avoids injecting a spurious Φ-zeroing term at timeout.

No Phase 2 (Light depth). No amendments.

## Outcomes

- A new `capture_v0_pure_potential_shaping` reward id, selectable via `--reward-id`/`REWARD_ID`, emitting a γ-correct PBRS `potential_shaping` term on the sparse capture base, with `reverse_action` removed.
- Unit tests proving the telescoping form, the capture pulse, timeout non-zeroing, magnitude bounds, and absence of `reverse_action`.
- Existing reward variants and checkpoints unchanged. Next step (separate task): a ≥5-seed sparse-vs-PBRS benchmark A/B (research-000024 R5).

## smoke
false
