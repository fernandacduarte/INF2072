# Reflection 000044 | 2026-06-30 22:13 UTC | what is implemented and how to test

## Artifacts reflected on

- [plan-000043 — IQL hyperparameter defaults](_output/plans/plan-000043-iql-hyperparameter-defaults.md)

## Summary

Plan-000043 tightened five IQL training hyperparameter defaults across three files:

- `training_exploration_schedule` in `algorithm_utils.py`: `anneal_ratio` 0.95→0.70, `eps_end` 0.10→0.05
- Both runner CLIs (`run_pacman_benchmarl.py`, `run_benchmark.py`): `--optimizer-steps` 10→4, `--memory-size` 10k→25k, `--init-random-frames` 5k→25k, `--epsilon-anneal-ratio` 0.95→0.70, `--epsilon-end` 0.05

Net effect: exploitation frames raised from ~3k to ~18k out of a 60k budget; buffer fully warm before the first gradient step; gradient-to-data ratio reduced from 10:1 to 4:1.

## Reflection

> "nothing changed, can we run benchmark with different hyperparams. where to start?"

The change is invisible at the surface because it touched only argparse defaults — no new flags, no new scripts. The new values are the baseline now; any run without explicit overrides already uses them. The question of "where to start" to experiment with different hyperparameters is the natural next step.

## Follow-ups

- How to pass explicit hyperparameter overrides on the CLI to compare against the new defaults
- Which hyperparameters are most worth sweeping next (lr, gamma, target-update-interval are the Rec 4 candidates deferred from this plan)
