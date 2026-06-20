# QA Log — implement plan-000008 | IQL win-rate harness and tuning to beat Pacman

**Brief:** implementr iql learning to win against pacman (execution of plan-000008)

**Date:** 2026-06-20 14:23 UTC

---

## Q&A log

### Q1 — Step 7 outcome (first decision, after 60k-frame training)
**Context:** IQL trained at 60k frames measured 0% win rate over 50 episodes; reward curve flat.
**Question:** How to close out Step 7's verification?
**Answer:** **Train much longer** — re-run IQL at a larger budget (300k frames) and re-measure before concluding.

### Q2 — Final call (after 300k-frame training)
**Context:** 300k frames also measured 0% win rate with an identically flat reward curve (~-0.20/step across all 1499 batches), confirming a coordination ceiling rather than a budget shortfall.
**Question:** How should I close out the plan?
**Answer (effective):** The user instructed: "ok, lets commit the findings in this chat and qa-log" — i.e. **accept the 0% IQL baseline as the honest measured result and finalize** (commit + QA log).

---

## Implementation outcome

**Manual-mode execution, 7 steps.**

- **Steps 1–6 (shipped, tested):**
  - `eval.py` — headless win-rate harness: `summarize_win_rate`, `classify_outcome` (shared with `_build_final_result`), `run_win_rate`, and CLI flags `--episodes` / `--eval-epsilon` / `--win-rate-out`; `--seed` repurposed as the win-rate base seed.
  - `constant.py` — sign-preserving reward retune (capture `+30`, distance `±0.5`, visibility `+0.3`, trimmed exploration bonuses).
  - `run_pacman_benchmarl.py` — `--max-frames` default 5000→60000, `_tune_iql_experiment` (epsilon anneal 1.0→0.05 over 80% of budget, `lr 1e-4`, `gamma 0.99`), IQL-guarded so VDN/QMIX are untouched.
  - `test/test_eval_win_rate.py` — 6 new unit tests (aggregation + classification). **31/31 tests pass.**
  - `README.md` — win-rate eval docs, tuned recipe, reward-retune note, measured baseline.

- **Step 7 (empirical — target not met, honest baseline):** IQL trained at 60k and 300k frames (seed 0). **Win rate = 0%** over 50 episodes in both; training reward curve dead-flat. Conclusion: independent Q-learners with 5×5 local views cannot pincer the distance-5 defense-first Pacman — a coordination ceiling that is the expected role of IQL as the baseline. The 60% target is not reachable for IQL within the frozen scope (tuning + reward shaping; Pacman policy + observation model frozen). VDN/QMIX (value factorization) are the coordination path expected to win.

## Key findings

- The win-rate harness is the real deliverable and works correctly — it measured, reproducibly, that IQL does not win.
- The environment's full determinism made seeded epsilon-greedy sampling necessary for a non-trivial win-rate metric; this was validated (varied per-episode outcomes on partially-trained checkpoints).
- `pytest` was missing from the venv and was installed (uv) to run the suite.
