# Research 000046 | fernanda-INF2072 | 2026-07-01 04:05 UTC | Full-benchmark preset check

tags: makefile, benchmark, configuration, reproducibility, training

## User Brief

> check current makefile presets. i want to run a full benchmark with the new parameters weve explored in last research.

## Agent Interpretation

The user is about to launch a full multi-seed benchmark (`make benchmark` / `make pipeline`) and wants confirmation that the current Makefile presets are correct and reflect the parameters settled in the most recent research (research-000045 on `PACMAN_RANDOM_ACTION_PROB`/`EVASIVENESS`, and the committed config change `fde51ea`). "Full benchmark" = all algorithms × 5 seeds at the production frame budget, per constitution Q3 and D-003.

## Files Reviewed

- `Makefile` (working tree, uncommitted edits + committed defaults)
- `benchmarl_setup/run_benchmark.py` (lines 75-76 algo default, 1263-1270 algo validation)
- `benchmarl_setup/algorithm_utils.py` (`SUPPORTED_ALGORITHMS`, `normalize_algorithm`)
- `_output/research-logs/research-000045-*.md` (last research — PACMAN_RANDOM_ACTION_PROB / EVASIVENESS)
- `_output/research-logs/research-000042-*.md` → plan-000043 (IQL hparam defaults, now baked into code)
- git: `git diff Makefile`, `git log` (commit `fde51ea`)

---

## Q&A Log

### Q1: Check the current Makefile presets; I want to run a full benchmark with the new parameters we explored in the last research.

**Answer:**

There is **one blocker** and **two optional decisions**. Everything else is correctly set for a full benchmark.

#### Current benchmark presets (working tree)

The Makefile has **uncommitted edits** that scale it up from a smoke-test config to a full-benchmark config:

| Variable | Value | Status |
|---|---|---|
| `ALGOS` | `iql,qdn,qmixglobal` | ❌ **`qdn` is invalid — typo for `vdn`** |
| `SEEDS` | `0,1,2,3,4` | ✓ 5 seeds (constitution Q3 / D-003) |
| `FRAMES` | `1000000` | ✓ 1M frames/run (committed default `fde51ea`) |
| `CHECKPOINT_INTERVAL` | `10000` | ✓ |
| `DEVICE` | `cuda` | ✓ |
| `REWARD_ID` | `capture_v0_closing` | ✓ |
| `CURRICULUM` | `off` | ⚠ see R2 (last research suggested curriculum for final runs) |
| `PACMAN_DIFFICULTY` | `hard` | ✓ (only active because `CURRICULUM=off`) |
| `PACMAN_RANDOM_ACTION_PROB` | `0.2` | ✓ committed default (`fde51ea`; was 0.5 in research-000045) |
| `EPSILON_ANNEAL_RATIO` / `EPSILON_END` | `0.4` / `0.05` | ✓ stabler-curve settings |
| `RANDOMIZE_SPAWNS` / min-distance | `1` / `4` | ✓ reactive-pursuit spawns |
| `CAPTURE_RADIUS` | `0` | ✓ co-location capture (don't mix radii in a plot) |
| `EVASIVENESS` (eval) | `0.8` | ⚠ see R3 (headline result wants 1.0) |

The tightened IQL hyperparameters from research-000042 → plan-000043 are now **code defaults** in `run_pacman_benchmarl.py`, so the benchmark picks them up automatically — no Makefile knob needed.

#### �︖ Blocker: `ALGOS = iql,qdn,qmixglobal`

`qdn` is not a valid algorithm. The supported set (`algorithm_utils.py:3`) is `iql, vdn, qmixlocal, qmixglobal`. `run_benchmark.py:1268-1270` validates the list up front and **raises `ValueError: Unsupported algorithm(s): ['qdn']` immediately**, aborting the *entire* benchmark before any training starts — so no compute is wasted, but the run won't start at all. `qdn` is an obvious transposition of `vdn` (the standard IQL/VDN/QMIX trio the project targets; `R1_ALGOS` already uses `iql,vdn,qmixglobal`).

**Fix:** change `ALGOS ?= iql,qdn,qmixglobal` → `ALGOS ?= iql,vdn,qmixglobal`.

#### Scale of this run

`iql,vdn,qmixglobal` × 5 seeds × 1,000,000 frames = **15 training runs** on `cuda`. Algorithms run in parallel, seeds serial (per the target's design), so wall-clock ≈ 5 serial seeds × 1M frames. This is a long run — worth confirming the frame budget is intended (the previous committed value was 100k for smoke testing).

---

## Recommendations Summary

- **R1 (HIGH) — Fix the `qdn` typo before running.** Change `ALGOS` to `iql,vdn,qmixglobal`. Without this the whole `make benchmark`/`make pipeline` aborts on a `ValueError` at startup.
- **R2 (MEDIUM) — Decide CURRICULUM for the final run.** Presets use `CURRICULUM=off` (fixed hard Pacman at 20% noise). research-000045 R2 recommended `CURRICULUM=easy-medium-hard` for final/publishable runs as a better-matched difficulty ramp. Pick one and keep it fixed across all seeds for a comparable plot. If staying with `off`, the `PACMAN_DIFFICULTY=hard` + `PACMAN_RANDOM_ACTION_PROB=0.2` combo is the effective opponent.
- **R3 (LOW) — Eval headline at EVASIVENESS=1.0.** `make benchmark` doesn't use `EVASIVENESS`; only the eval stage does. For the canonical report number run `make eval-report EVASIVENESS=1.0` (deterministic hard Pacman, per D-003); the `0.8` default is fine for debugging.
- **R4 (LOW) — Confirm FRAMES=1000000 is intended** (up from the 100k smoke default) and that the Makefile edits get committed so the run is reproducible against a clean commit (constitution C1).

### Recommended command (after fixing `qdn`)

```bash
make pipeline ALGOS=iql,vdn,qmixglobal      # benchmark -> summarize -> eval-report
# then, for the headline eval number:
make eval-report EVASIVENESS=1.0
```
