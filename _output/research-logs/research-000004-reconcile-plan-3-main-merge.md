# Research 000004 | FEATURE fernanda-INF2072 | 2026-06-19 14:21 UTC | Reconcile plan 3 with main merge
source: plan-000003
tags: plan-reconciliation, pacman-environment, merge, testability, reward-system

## User Brief

"update plan 3 with newly added merge commits from main"

## Agent Interpretation

`main` was merged into `pallets_and_rewards` (commit `becde39`) *after* plan-000003 ("Pallet system and reward update") was authored on 2026-06-15. The task: determine how the merged changes affect each of plan 3's four steps and update the plan so it stays executable against the current code.

## Files Examined

- `_output/plans/plan-000003-pallet-system-and-reward-update.md` (the plan, updated)
- `custom_environment/env/pacman_environment.py` (`__init__`, `reset`, `step`, `_build_global_state`, `_build_initial_pellet_mask`)
- `custom_environment/env/domain/constant.py` (`Reward` enum)
- `custom_environment/utils.py` (`MazeSpec`, `spec_from_grid`, `parse_layout`)
- `test/test_mazes.py` (new test patterns)
- Merge diff `git diff becde39^1 becde39`

## Findings

The merge brought map-authoring/render work: `utils.py` (`MazeSpec`, `parse_layout`, `spec_from_grid`), `render_demo.py`, configurable `GHOST_VIEW_SIZE` (default 5), and `test_mazes.py`. Impact on each plan step:

| Plan element | Status after merge | Action |
|---|---|---|
| **Step 1** — `PACMAN_WIN_PALLETS` in `Reward` enum | Anchor intact (`PACMAN_TIMEOUT_WIN = -20.0` at `constant.py:25`) | No change |
| **Step 2** — `_total_pallets` on reset | Anchor intact (`_reset_visual_pellets()` at line 160; `_pellet_mask` built at line 126). **Semantics shifted**: pellets now map-authored via `MazeSpec.pellet_mask`/`_base_pellet_mask`, not `_base_grid == EMPTY` | Note added; logic unchanged |
| **Step 3** — pallet-win in `step()` | All anchors intact (`capture_happened`/`timeout_happened` at lines 208–209; truncation loop at 216–219) | Logic unchanged; **test rewritten** |
| **Step 4** — `pallets_remaining_norm` in global state | `_build_global_state()` (line 707) and `_state_dim` formula (`(rows*cols)+(3*len(possible_agents))+7`, line 116) intact | Logic unchanged (+7→+8 still correct); **test fixed** |

**The one genuine breakage** is the Step 3/Step 4 test construction. The plan's original test built "a minimal 3×3 grid" and passed it raw. Post-merge the constructor wraps a raw grid via `spec_from_grid()`, which **hardcodes legacy spawns** `pacman_spawn=(18,9)`, `ghost_spawns=[(1,1),(1,18)]` — out of bounds for a 3×3 grid, so `reset()` would `IndexError`. The test must build a `MazeSpec` directly (or a small `parse_layout` ASCII string) with in-bounds spawns and a controlled `pellet_mask`.

Two secondary observations, folded into the plan:
- `number_ghosts` is deprecated; `possible_agents` derives from `len(ghost_spawns)`. The `_state_dim` formula reads `possible_agents` dynamically, so it stays correct.
- The merge already broke pre-merge checkpoints by changing the ghost observation from 3×3 to 5×5 (`GHOST_VIEW_SIZE`). Step 4's `+1` state-dim change adds no *new* incompatibility beyond what the merge introduced.

## Perspective Synthesis

- **CORRECTNESS**: All four step transformations remain valid against current code; the win-condition guards (`_total_pallets > 0`, `not capture_happened`) are unaffected. Map-authored pellets make `_total_pallets` *more* correct (designed pellet set vs. all empty cells).
- **TEST** (governing perspective for the change): The original fixture would crash post-merge. Fixed by mandating a `MazeSpec`/`parse_layout` fixture with in-bounds spawns. This is the highest-value update.
- **DX**: The plan now records *why* the test approach changed, preventing a future executor from re-introducing the raw-3×3-grid trap.
- **SECURITY / I18N**: N/A (local research CLI, no user-visible text).

## Recommendations Summary

1. **[HIGH]** Rewrite the Step 3/4 test to use a `MazeSpec` (or `parse_layout`) fixture with in-bounds spawns and a one-pellet `pellet_mask` — the raw-3×3-grid approach now crashes via `spec_from_grid`'s out-of-bounds legacy spawns. *(Applied to plan 3.)*
2. **[MEDIUM]** Record that pellets are map-authored post-merge, so `_total_pallets` counts the designed pellet set; Step 2 logic is unchanged. *(Applied to plan 3.)*
3. **[LOW]** Note that the merge already forces checkpoint re-training (observation 3×3→5×5), so Step 4's state-dim `+1` adds no new incompatibility. *(Applied to plan 3.)*

Steps 1–4 implementation logic requires no change; plan 3 remains executable as written once the test fixture is built per the revised instructions.

## Q&A Log

**Q1 (2026-06-19 14:21 UTC):** update plan 3 with newly added merge commits from main

**A1:** The `main` merge (`becde39`) left all four step anchors in plan 3 intact. The only logic-relevant shift is that pellets are now map-authored (`MazeSpec.pellet_mask`) rather than derived from EMPTY cells — `_total_pallets` counting still works and is more correct. The single real breakage is the Step 3/4 test: it can no longer pass a raw 3×3 grid because the back-compat `spec_from_grid` assigns out-of-bounds legacy spawns; it must build a `MazeSpec` (or `parse_layout` ASCII) with in-bounds spawns and a controlled one-pellet mask. Plan 3 was updated with a Merge Reconciliation section, a Step 2 source note, revised Step 3/4 test instructions, and a checkpoint-incompatibility note.
