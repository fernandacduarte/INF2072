# QA Log — plan-000008 | IQL win-rate harness and tuning to beat Pacman

**Brief:** implementr iql learning to win against pacman

**Date:** 2026-06-20 03:25 UTC

---

## Q&A log

### Q1 — Definition of done
**Question:** What is the primary deliverable for "IQL learning to win against Pacman"? (IQL training already runs.)
**Answer:** **Win-rate harness + tuned IQL** — add a win-rate evaluation (run N episodes on a checkpoint, report % ghost captures) AND tune training budget/hyperparameters so IQL demonstrably reaches a target win rate.

### Q2 — Approach latitude
**Question:** How far may the plan go to make IQL win, beyond hyperparameter/budget tuning?
**Answer:** **Tuning + reward shaping** — allow adjusting reward terms and training config, but keep the Pacman policy and the 5×5 observation model frozen.

### Q3 — Next step after plan
**Question:** Plan 000008 is reviewed and ready. What next?
**Answer:** **Implement now** — commit the plan and run /implement 000008.

---

## Key findings established during planning

- IQL training is already fully wired (`run_pacman_benchmarl.py --algorithm iql`); ghosts are the trainable agents and "winning" = capturing Pacman before timeout/pallet-clear.
- The environment is **deterministic** (deterministic defense-first Pacman policy + fixed map-authored spawns + greedy ghost policy), so a multi-episode win rate requires seeded stochastic ghost-action sampling (`--eval-epsilon`) to be non-trivial.
- No win-rate metric exists anywhere today — only reward proxies (`final_reward`, `tail_mean`).
- Default `--max-frames 5000` is smoke-test scale; convergence needs a larger budget + tuned exploration.
- Reward constants are global (shared across IQL/VDN/QMIX); sign-preserving retune keeps existing smoke tests (`test_pallet_win.py`) valid.

## Review outcome (Standard, plan-reviewer)

Three source-validated defects fixed via amendment: non-existent `_decode` reference (use `_tensor_to_int_list`); duplicated/untested win classification (extract shared `classify_outcome` from `_build_final_result` predicates + unit-test it); silently repurposed `--seed` flag (fix help text + explicit harness trigger). PERF/SEC clean.
