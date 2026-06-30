# Plan 000043 | CHORE-X | 2026-06-30 21:30 UTC | IQL hyperparameter defaults | Review: light
# DONE | 2026-06-30 21:47 UTC |
plan_format_version: 1
source: research-000042 -- apply HIGH-priority hyperparameter default changes

---

## User Brief

> Apply HIGH-priority IQL hyperparameter defaults from research-000042: lower optimizer_steps from 10 to 4, raise memory_size from 10000 to 25000, raise init_random_frames from 5000 to 25000, lower epsilon_anneal_ratio from 0.95 to 0.70, lower epsilon_end from 0.10 to 0.05.

## Agent Interpretation

**Problem**: The current default hyperparameters create three compounding issues: (1) a 10:1 gradient-update-to-data ratio with a small 10k replay buffer causes replay overfitting; (2) epsilon annealing over 95% of the budget leaves only 3k exploitation frames; (3) training begins on a half-empty buffer.

**Approach**: Change the argparse defaults in both runner scripts and the `training_exploration_schedule` function signature defaults in `algorithm_utils.py` to match the recommended values. Update `test_algorithm_utils.py` to match the new function defaults.

**Alternatives rejected**: Changing only the function signature without the CLI (or vice versa) would leave the canonical source of truth inconsistent. Exposing more flags (lr, gamma, target-update-interval) is deferred per Rec 4 in research-000042 — this plan covers only the HIGH-priority Recs 1–3.

**Selection rationale**:
- Included: Rec 1 (optimizer_steps=4, memory_size=25000, init_random_frames=25000) — directly addresses replay overfitting and buffer warmup
- Included: Rec 2 (epsilon_anneal_ratio=0.70, epsilon_end=0.05) — raises exploitation frames from 3k to 18k
- Included: Rec 3 (init_random_frames=25000 fills the full buffer) — combined with Rec 1 above
- Excluded: Rec 4 (expose lr, gamma, target-update flags) — medium priority, separate plan
- Excluded: Rec 6 (shared constants module) — medium priority, separate plan
- Excluded: Rec 7 (lr ablation sweep) — research/experiment task, not a code change

## Files

- `benchmarl_setup/algorithm_utils.py` — `training_exploration_schedule` default parameter values
- `benchmarl_setup/run_pacman_benchmarl.py` — argparse defaults for optimizer_steps, memory_size, init_random_frames, epsilon_anneal_ratio, epsilon_end
- `benchmarl_setup/run_benchmark.py` — same argparse defaults
- `test/test_algorithm_utils.py` — expected values in `test_training_schedule_is_shared_across_algorithms_and_mazes`

## Best Practices

- Change defaults in all three call sites (function signature, both runner CLIs) together so `training_exploration_schedule(algorithm, maze, frames)` without keyword overrides produces the same values as the CLI defaults.
- Update the existing test to reflect the new defaults rather than adding a second test — the old expected values are no longer the project default.
- Apply identically to all algorithms (IQL, VDN, QMIX) per D-003 cross-algorithm fairness requirement.

## Design Decisions

**User-visible impact**: Running `py -3.11 run_pacman_benchmarl.py` or `run_benchmark.py` without explicit overrides will now use the improved defaults. Researchers who have been relying on the old defaults must either update their invocation scripts or pass the old values explicitly. The change is logged in the reproducibility banner (via `vars(args)`) and is traceable via git commit.

**Trade-offs accepted**: init_random_frames raised from 5k to 25k — training starts 20k frames later, but early gradient quality improves substantially. The total frame budget (60k) is unchanged; the first meaningful gradient step occurs at frame 25k instead of frame 5k.

**Metacommunication impact**: The CLI help strings for `--optimizer-steps`, `--memory-size`, `--init-random-frames`, `--epsilon-anneal-ratio`, and `--epsilon-end` will reflect the new default values in their `default=` argparse field. No help-text wording changes are required — the defaults self-document.

## Steps

- [x] **Step 1 — Update `training_exploration_schedule` function signature defaults**
  - Files: `benchmarl_setup/algorithm_utils.py`
  - Interface: `training_exploration_schedule(algorithm, maze, max_frames, anneal_ratio=0.70, eps_end=0.05)`
  - Verify: function called without keyword args returns `epsilon_anneal_ratio=0.70, epsilon_end=0.05`
  - Tests: `test_algorithm_utils.py::test_training_schedule_is_shared_across_algorithms_and_mazes` (updated in Step 4)
  - References: research-000042 Rec 2

- [x] **Step 2 — Update `run_pacman_benchmarl.py` argparse defaults**
  - Files: `benchmarl_setup/run_pacman_benchmarl.py`
  - Interface: `--optimizer-steps` default=4, `--memory-size` default=25000, `--init-random-frames` default=25000, `--epsilon-anneal-ratio` default=0.70, `--epsilon-end` default=0.05
  - Verify: `py -3.11 run_pacman_benchmarl.py --help` shows updated defaults
  - Tests: N/A (argparse defaults are not directly tested; covered by smoke test if run)
  - References: research-000042 Recs 1–3

- [x] **Step 3 — Update `run_benchmark.py` argparse defaults**
  - Files: `benchmarl_setup/run_benchmark.py`
  - Interface: same five flags as Step 2
  - Verify: `py -3.11 run_benchmark.py --help` shows updated defaults
  - Tests: N/A (same reasoning as Step 2)
  - References: research-000042 Recs 1–3

- [x] **Step 4 — Update `test_algorithm_utils.py` expected values**
  - Files: `test/test_algorithm_utils.py`
  - Interface: N/A
  - Verify: `py -3.11 -m pytest test/test_algorithm_utils.py -v` passes
  - Tests: updated expected dict: `epsilon_end=0.05, epsilon_anneal_ratio=0.70, epsilon_anneal_frames=int(60000*0.70)`
  - References: project standards.md § Testing

## Review Log

### Phase 1 — Perspective triage (Light depth)

| Perspective | Status | Note |
|---|---|---|
| PERF | Adopted | The change directly implements the PERF recommendations from research-000042; no performance regressions introduced |
| ARCH | Adopted | Defaults changed in all three call sites simultaneously; no architectural coupling introduced |
| DX | Adopted | Help strings auto-update via argparse `default=` field |
| TEST | Adopted | Existing test updated; no coverage lost |
| SEC | N/A | No auth, secrets, or sensitive data involved |
| DB | N/A | No database or migrations |
| API | N/A | CLI tool, no REST API |

#### Execution Metrics

| Metric | Value |
|---|---|
| Perspectives evaluated | 4 |
| Perspectives N/A | 3 |
| Phase 2 triggered | No (Light depth) |
| Amendments | 0 |

## Outcomes

- `training_exploration_schedule(algorithm, maze, 60000)` returns `epsilon_anneal_ratio=0.70, epsilon_end=0.05, epsilon_anneal_frames=42000`
- All three algorithms default to `optimizer_steps=4, memory_size=25000, init_random_frames=25000`
- Existing test suite passes
- `run_benchmark.py` reproducibility banner captures the new defaults in `vars(args)`

## Smoke

false

## Implementation Summary

**Steps completed**: 4/4 | **Iterations**: 1 (pre-implemented in commit `3e6c7d4`) | **Tests**: 124 passed

### Changes applied

| File | Change |
|------|--------|
| `benchmarl_setup/algorithm_utils.py` | `training_exploration_schedule` signature defaults updated: `anneal_ratio=0.70`, `eps_end=0.05` |
| `benchmarl_setup/run_pacman_benchmarl.py` | argparse defaults: `--optimizer-steps=4`, `--memory-size=25000`, `--init-random-frames=25000`, `--epsilon-anneal-ratio=0.70`, `--epsilon-end=0.05` |
| `benchmarl_setup/run_benchmark.py` | same five argparse defaults as above |
| `test/test_algorithm_utils.py` | expected dict updated: `epsilon_end=0.05`, `epsilon_anneal_ratio=0.70`, `epsilon_anneal_frames=42000` |

### Quality gate

- `/check validate`: N/A (no validation scripts for argparse defaults)
- `/check review`: Review log embedded in plan (all perspectives Adopted or N/A)
- Tests: **124 passed**, 0 failed
