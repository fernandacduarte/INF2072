# Research 000024 | project | 2026-06-24 10:01 UTC | Last Commits Report
tags: git-history, reward-shaping, training, coordination, debugging

## User Brief
"last commits of this codebase and report what was done"

## Agent Interpretation
Summarize the most recent git commits on the current branch (`ajustes_rewards_fred`) to give the researcher a clear picture of what changed and why.

## Files Reviewed
- `git log --oneline -15`
- `git log --stat -5`

---

## Q&A Log

**Q1:** What were the last commits of this codebase and what was done?

**A1:**

### `e78c937` — Arquivo que faltou (Jun 23, 2026)
Follow-up commit adding two missing files: `.gitignore` (3 lines) and `test/test_algorithm_utils.py` (35 lines — new smoke test for algorithm utilities).

### `cab45c6` — Transition validity hardening + reward refactor (Jun 23, 2026)
Largest commit (1,319 insertions). Four major areas:

1. **Transition validity hardening** (`pacman_environment.py`): Guards preventing out-of-bounds and negative-index wraparound from producing physically impossible transitions in the replay buffer.
2. **New `CurrentTeamReward` class** (`rewards/current.py`): Team-potential shaping revised so reward density tracks whether the joint ghost formation constrains Pacman escape routes over time. Separate same-corridor/overlap reward classes tested and removed as conflicting.
3. **Hyperparameter unification**: Common hyperparameters consolidated across IQL/VDN/QMIX scripts. IQL special-case handling still pending.
4. **Enhanced live and final plots** (`liveplot.py`, `plot_benchmarl_reward.py`): Now display mean capture %, mean reward, and epsilon value. Added `--reward-id`/`--rewards-id` flags for cross-reward-class comparison.

### `115f9fd` — Action masking + VDN/QMIX hyperparameter alignment (Jun 22, 2026)
Action masking introduced at environment level (invalid moves blocked). IQL reportedly began achieving positive rewards for the first time. VDN/QMIX hyperparameters aligned to IQL settings.

### `f5c7261` — Observation dtype fix (Jun 22, 2026)
Removed hardcoded observation cast in `pacman_benchmarl_task.py` incompatible with the environment's native `float32` observations.

### `deb1103` — `_local_cells` view window fix
Bug fix: `_local_cells` was using a hardcoded 3×3 window instead of the configured `ghost_view_size` parameter.

### `c295c6c` — Action indexing + episode termination semantics
Ghost actions standardized to discrete index `0..3`. Pacman win and timeout now treated as terminal (not truncated). Tests updated.

---

## Recommendations Summary

- **Active research frontier**: Ghosts collecting rewards without coordinating to catch Pacman — the core coordination problem remains open after `cab45c6`.
- **Pending cleanup**: IQL hyperparameter special-casing noted in `cab45c6` commit message as still requiring correction.
- **Pending action**: plan-000011 (live plot win rate) is awaiting `/implement`.
