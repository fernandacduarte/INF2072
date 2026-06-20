# Research 000017 | fernanda-INF2072 | 2026-06-20 19:46 UTC | Pacman policy after --maze feature

tags: pacman-policy, maze-layout, bfs, behavioral-analysis, testing

**User brief:** pacman policy after --maze feature

**Agent interpretation:** Assess the current state of `PacmanPolicy` (defense-first BFS controller) in the context of the `--maze` CLI feature introduced in the maze-layout-separate-training merge. Identify any correctness issues, undocumented behavioral changes, or improvement opportunities specific to the multi-maze context.

**Files consulted:**
- `custom_environment/env/domain/pacman_policy.py`
- `custom_environment/env/pacman_environment.py`
- `custom_environment/utils.py`
- `benchmarl_setup/pacman_benchmarl_task.py`
- `benchmarl_setup/run_pacman_benchmarl.py`
- `benchmarl_setup/run_benchmark.py`
- `product-design/project/product-design-as-coded.md`
- git log (maze-related commits: 6677abc, c2c200c, 5547a72)

---

## Q&A Log

**Q1: How does the PacmanPolicy behave after the --maze feature was introduced?**

The `PacmanPolicy` is **maze-agnostic by construction**. It operates entirely on `global_view` (the live grid state), which is populated from whatever `MazeSpec` was loaded via `build_maze(name)`. No changes were made to `pacman_policy.py` during the maze feature merge. The two multi-source BFS flood-fills — one from all ghost positions, one from all pellet positions — work correctly across any maze because they respect `global_view` walls (`Observation.WALL.value`) and consider only passable cells.

### What is correct

- **BFS wall handling**: `_multi_source_bfs` skips `WALL` cells using `global_view`, correctly adapting to any loaded maze topology.
- **EMPTY-only move filter**: `if global_view[nx, ny] != Observation.EMPTY.value: continue` — the policy only proposes moves to EMPTY cells, which is coherent with `_execute_action`'s own `can_move` rule for non-capture Pacman movement.
- **State dimension**: `_state_dim = rows*cols + 3*N_ghosts + 8` matches `_build_global_state` output for both 20×20 mazes. Breakdown: `wall_map_flat` (rows×cols) + `ghost_positions_norm` (2×N) + `ghost_to_target_dist_norm` (N) + 4 pacman-memory scalars + 3 episode scalars + 1 pallets scalar = rows×cols + 3×N + 8. ✓
- **No code regression**: The `--maze` feature was a pure infrastructure change (CLI flag, output path routing, MazeSpec loading). `pacman_policy.py` was not touched.

### Behavioral shift in pinklike (undocumented, not a bug)

`PACMAN_SAFE_DISTANCE = 5` is a topology-blind constant. In `default`'s open corridors, many cells have `ghost_dist ≥ 5`, so the safety cap saturates and pellet distance is only a secondary tiebreaker. In `pinklike`'s narrower corridors — and with ghosts spawning at **(7,9)/(7,10) in the center** rather than at the top corners (1,1)/(1,18) as in `default` — more reachable cells have `ghost_dist < 5`. This collapses the safety term's dynamic range: **pellet proximity becomes the dominant scoring signal more often**, making Pacman more pellet-aggressive and less defensively conservative than in the default maze, without any code change.

This is not a correctness bug, but it is an undocumented behavioral divergence between mazes that could confuse future contributors comparing training dynamics.

### Highest-risk gap: dead-end fallback

When all four neighbors of Pacman's position are non-EMPTY (walls or ghosts), the policy finds no candidate moves and falls back to `Action.choose_random()`. In `pinklike`'s tight corridors, this situation is more frequent than in `default`. A random action in this state will typically land on a ghost cell (= immediate capture). **This code path has no test coverage.**

---

## Recommendations Summary

| # | Priority | Recommendation |
|---|----------|----------------|
| R1 | MEDIUM | Add a policy test for the dead-end fallback: construct a synthetic `global_view` with all four neighbors non-EMPTY and assert `choose_action` returns a valid `Action` without exception. File: `test/test_pacman_policy.py` |
| R2 | MEDIUM | Add a test asserting the EMPTY-only invariant: policy never selects a GHOST cell as its move, exercising both `default` and `pinklike` topology configurations. File: `test/test_pacman_policy.py` |
| R3 | LOW | Document `PACMAN_SAFE_DISTANCE = 5` with a comment explaining its relationship to maze corridor length. Note: tuned for default open-corridor layout; lower values may be more appropriate for pinklike. File: `custom_environment/env/domain/constant.py` |
| R4 | LOW | Consider making `PACMAN_SAFE_DISTANCE` a `MazeSpec`-level attribute or CLI-overridable default, consistent with the project's "no opaque defaults" principle (T4). Not urgent before course submission. |
