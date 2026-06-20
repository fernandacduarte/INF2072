# Implement Q&A 000003 | fernanda-INF2072 | 2026-06-19 14:34 UTC | Pallet system and reward update

source: plan-000003

## Brief

`/implement 3` — execute plan-000003 (pallet system and reward update), in manual mode.

## Session Log

**Mode**: manual (4 steps, 2 source files — below the auto-mode threshold).

1. **Step 1** — Added `Reward.PACMAN_WIN_PALLETS = -20.0` in `custom_environment/env/domain/constant.py`.
2. **Step 2** — Initialized `self._total_pallets = 0` in `__init__`; recorded the per-episode pallet count in `reset()` after `_reset_visual_pellets()` (post spawn-cell consumption) in `custom_environment/env/pacman_environment.py`.
3. **Step 3** — Added pallet-exhaustion detection in `step()` (`pacman_win_happened`, guarded by `not capture_happened` and `_total_pallets > 0`), applied the `PACMAN_WIN_PALLETS` penalty, and OR'd the outcome into `truncations`.
4. **Step 4** — Appended `pallets_remaining_norm` to `_build_global_state()` and bumped `_state_dim` from `+7` to `+8`.
5. **Tests** — Added `test/test_pallet_win.py` (4 tests). Built the fixture from a `parse_layout` ASCII `MazeSpec` (not a raw grid) per the plan's Merge Reconciliation note, since the back-compat `spec_from_grid` assigns out-of-bounds legacy spawns.

## Outcome notes

- New tests: 4/4 pass (run directly via `.venv` Python — pytest is not installed in this environment).
- Regression: PettingZoo `parallel_api_test` passes on `default` + `pinklike` mazes and the back-compat raw-grid path; `state().shape[0] == _state_dim`.
- Quality-gate automation (`/check validate`, `/check review`, `test-runner`) could not run — ruff/pyright/pytest absent from `.venv`. Verified behavior directly instead. Re-run `py -3.11 -m pytest test/` after installing dev dependencies.
