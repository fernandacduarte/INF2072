# Research 000045 | fernanda-INF2072 | 2026-06-30 22:12 UTC | PACMAN_RANDOM_ACTION_PROB and EVASIVENESS usage and pipeline impact

tags: pacman-policy, training, evaluation, make-pipeline, difficulty

## User Brief

How `PACMAN_RANDOM_ACTION_PROB` and `EVASIVENESS` are being used and how they affect the make pipeline.

## Agent Interpretation

The user wants to understand the semantics and data flow of two Makefile-level knobs that control Pacman's in-game behavior:
1. `PACMAN_RANDOM_ACTION_PROB` — training-time noise injected into the Pacman policy.
2. `EVASIVENESS` — eval-time difficulty expressed as the fraction of moves Pacman plays optimally.

---

## Files Reviewed

- `Makefile`
- `custom_environment/env/domain/pacman_policy.py`
- `custom_environment/env/pacman_environment.py` (lines 80–260)
- `custom_environment/eval.py` (function `_set_pacman_evasiveness_for_eval`, lines 740–770)
- `custom_environment/eval_report.py`
- `benchmarl_setup/run_benchmark.py` (lines 115–130, 355–365, 1258)
- `benchmarl_setup/run_r1_positive_control.py`

---

## Q&A Log

### Q1: How `PACMAN_RANDOM_ACTION_PROB` and `EVASIVENESS` are being used and how they affect the make pipeline?

---

### The two knobs and their semantics

**`PACMAN_RANDOM_ACTION_PROB`** (float in [0, 1], default in Makefile: **0.5**)

This is a **training-time** knob. It controls how often the Pacman heuristic policy takes a random legal action instead of its defense-first optimal move.

- `0.0` = fully deterministic: Pacman always maximizes safety then pellet progress. Maximum pressure on the ghost agents.
- `1.0` = fully random: Pacman is purely stochastic. Easiest prey for the ghost agents to capture.
- Intermediate values (e.g., `0.5`) inject noise to make pursuit learning easier to bootstrap.

**Important constraint**: This knob only takes effect when `CURRICULUM=off`. When `CURRICULUM=easy-medium-hard`, the curriculum scheduler (`_build_pacman_policy`) sets the noise per stage:
- `easy` → `pure_random=True` (100% random, ignores `PACMAN_RANDOM_ACTION_PROB` entirely)
- `medium` → `random_action_prob=0.30` (30% noise)
- `hard` → `random_action_prob=0.0` (fully deterministic)

The Makefile documents this explicitly at lines 43–47:
```
# NOTE: PACMAN_DIFFICULTY and PACMAN_RANDOM_ACTION_PROB only take effect when
# CURRICULUM=off; with a curriculum the easy->medium->hard schedule sets these
# per stage. Eval always forces a hard Pacman regardless of these (by design).
```

**Code path**: `Makefile` → `run_benchmark.py --pacman-random-action-prob` → `pacman_benchmarl_task.py` → `PacmanEnvironment(pacman_random_action_prob=...)` → `_build_pacman_policy()` → `PacmanPolicy(random_action_prob=...)` → `choose_action()` (line 99: `if rng.random() < random_action_prob: pick random`).

---

**`EVASIVENESS`** (float in [0, 1], default in Makefile: **0.8**)

This is an **eval-time** knob. It expresses Pacman's difficulty as the fraction of moves played optimally during evaluation.

Internally it maps to: `pacman_random_action_prob = 1.0 - evasiveness`

- `1.0` = fully evasive = `random_action_prob=0.0` = deterministic hard Pacman. Maximum eval pressure.
- `0.8` = 80% evasive = `random_action_prob=0.20` = Pacman takes a random action 20% of the time.
- `0.0` = fully random Pacman during eval.

The conversion is done by `_set_pacman_evasiveness_for_eval()` (eval.py line 740–770), which also forces `pacman_difficulty="hard"` and `pacman_curriculum="off"` so the eval opponent is always a stable, single difficulty regardless of what was used during training.

**Code path**: `Makefile EVASIVENESS=0.8` → `eval.py --pacman-evasiveness` → `_set_pacman_evasiveness_for_eval(raw_env, 0.8)` → sets `raw_env.pacman_random_action_prob = 0.2` + `raw_env.pacman_difficulty = "hard"` → rebuilds `_pacman_policy`.

`eval_report.py` follows the same pattern for the headless quantitative eval.

---

### Pipeline targets and which knob each uses

| `make` target | Knob used | Effective argument |
|---|---|---|
| `make benchmark` | `PACMAN_RANDOM_ACTION_PROB` (Makefile default 0.5) | `--pacman-random-action-prob $(PACMAN_RANDOM_ACTION_PROB)` |
| `make pipeline` | same as `benchmark` + no eval knob | `EVASIVENESS` is **not** passed to `summarize`; only `eval-report` uses it |
| `make eval-latest` | `EVASIVENESS` (default 0.8) | `--pacman-evasiveness $(EVASIVENESS)` |
| `make eval-report` | `EVASIVENESS` (default 0.8) | `--pacman-evasiveness $(EVASIVENESS)` |
| `make r1-positive-control` (condition P) | hardcodes `--pacman-random-action-prob 1.0` | fully random Pacman, ignores `PACMAN_RANDOM_ACTION_PROB` |

---

### Key asymmetry: the train/eval gap

There is a deliberate train/eval asymmetry:

- **During training** (`make benchmark`): `PACMAN_RANDOM_ACTION_PROB=0.5` means Pacman is 50% noisy. This makes pursuit easier to learn initially but the trained policy never sees a deterministic hard Pacman.
- **During eval** (`make eval-report`): `EVASIVENESS=0.8` → `random_action_prob=0.20`, which means Pacman takes only 20% random actions. The eval Pacman is **harder** than the training Pacman (20% noise vs 50% noise).

This gap is intentional in research contexts (evaluate against a tougher opponent than was trained against), but it needs to be understood when interpreting capture rates: if the reported eval capture rate is lower than the training reward, part of that gap comes from the harder eval Pacman, not just generalization failure.

---

### Default values currently in the Makefile

| Variable | Makefile default | Meaning |
|---|---|---|
| `PACMAN_RANDOM_ACTION_PROB` | `0.5` | 50% noise during training (when `CURRICULUM=off`) |
| `EVASIVENESS` | `0.8` | 80% evasive during eval → 20% random |

Note: the branch salvage patches (`_output/branch-salvage/`) show `PACMAN_RANDOM_ACTION_PROB ?= 0.0` was the prior default. The current `0.5` reflects a deliberate decision to make training Pacman easier. This means the current default pipeline trains against a noisy opponent and evaluates against a harder one.

---

## Recommendations Summary

### R1 (HIGH) — Document the train/eval difficulty gap explicitly in the report
The current defaults create a systematic gap: training uses `p=0.5` noise (easy Pacman) but eval uses `e=0.8` → `p=0.2` (harder Pacman). Any capture-rate comparison between training reward and eval report must account for this asymmetry, or the reader may incorrectly attribute the difference to learning quality.

**Action**: When writing the course report, state explicitly:
- Training opponent: `CURRICULUM=off, PACMAN_RANDOM_ACTION_PROB=0.5` (50% random)
- Eval opponent: `EVASIVENESS=0.8` → `random_action_prob=0.20` (20% random, harder)

### R2 (MEDIUM) — For final benchmark runs, use CURRICULUM=easy-medium-hard instead of PACMAN_RANDOM_ACTION_PROB
When `CURRICULUM=off`, `PACMAN_RANDOM_ACTION_PROB=0.5` fixes the opponent difficulty for the entire training run. The curriculum provides a structured ramp (easy→medium→hard) that better matches established MARL training practice and avoids locking in a difficulty that may be too easy for late-game convergence.

### R3 (LOW) — Eval at EVASIVENESS=1.0 for the canonical publishable result
For the course report's primary result table (following Papoudakis-2021 / D-003), use `make eval-report EVASIVENESS=1.0` to evaluate against the deterministic hard Pacman. `EVASIVENESS=0.8` (the default) gives a slightly easier eval opponent that is appropriate for debugging but not for the headline number.
