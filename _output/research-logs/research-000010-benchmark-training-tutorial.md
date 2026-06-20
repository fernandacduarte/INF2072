# Research 000010 | fernanda-INF2072 | 2026-06-20 15:09 UTC | Benchmark training tutorial
tags: benchmark, training, documentation, benchmarl, how-to

## User brief

> parse readme and create a comprehensive tutorial on how to run benchmark training

## Agent interpretation

Read [README.md](../../README.md) and the benchmark-related scripts, then produce a
self-contained, step-by-step tutorial for running multi-seed benchmark training in this
project — covering setup, the one-command benchmark, live monitoring, the output artifacts,
plotting, win-rate evaluation, and the most common knobs and pitfalls. This is a how-to
deliverable, not a design decision, so no Decision (D-NNN) entries are proposed.

## Files reviewed

- [README.md](../../README.md) — canonical usage documentation
- [benchmarl_setup/run_benchmark.py](../../benchmarl_setup/run_benchmark.py) — multi-seed orchestrator (source of truth for CLI args/defaults)
- [benchmarl_setup/run_pacman_benchmarl.py](../../benchmarl_setup/run_pacman_benchmarl.py) — single-run training runner invoked per (algorithm, seed)
- [benchmarl_setup/algorithm_utils.py](../../benchmarl_setup/algorithm_utils.py) — supported algorithms, run-dir naming
- [benchmarl_setup/liveplot.py](../../benchmarl_setup/liveplot.py), [benchmarl_setup/plot_benchmarl_reward.py](../../benchmarl_setup/plot_benchmarl_reward.py), [benchmarl_setup/summarize_benchmark_runs.py](../../benchmarl_setup/summarize_benchmark_runs.py) — monitoring/plotting/summary

---

# Tutorial — Running Benchmark Training

> A "benchmark" here = training **multiple algorithms × multiple seeds** in one command,
> then aggregating the results into a summary CSV and a comparison plot. The entrypoint is
> [`benchmarl_setup/run_benchmark.py`](../../benchmarl_setup/run_benchmark.py). It runs
> **algorithms in parallel** and **seeds serially within each algorithm**.

## 0. Prerequisites (one-time)

All scripts require **Python 3.11**. Verify and set up the environment:

```bash
# Confirm 3.11 is available
py -3.11 --version

# Create and activate a venv (PowerShell)
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1

# Install pinned dependencies
py -3.11 -m pip install -r requirements.txt
```

Sanity-check that the custom Pacman env and BenchMARL import together:

```bash
py -3.11 benchmarl_setup\register_pacman_env.py
```

A message that `register_env` is unavailable is **expected** for BenchMARL 1.5.x — the env
is integrated through the custom `PacmanTask` adapter, not a runtime register call.

## 1. The one-command benchmark

Full benchmark across all four algorithms and 5 seeds:

```bash
py -3.11 benchmarl_setup\run_benchmark.py --algorithms iql,vdn,qmixlocal,qmixglobal --seeds 0,1,2,3,4 --max-frames 50000
```

This single command:

1. Launches one **parallel worker per algorithm** (e.g. IQL, VDN, QMIX-local, QMIX-global all train at once).
2. Inside each worker, runs the **seeds serially** (seed 0, then 1, …).
3. Streams **live progress** to `benchmarl_setup/runs/live_progress.csvl`.
4. On completion, writes a **summary CSV** to `benchmarl_setup/runs/benchmark_summary.csv`.

The four valid algorithm names (`SUPPORTED_ALGORITHMS`):

| Name | Meaning |
|------|---------|
| `iql` | Independent Q-Learning — the independent baseline (gets auto-tuned hyperparameters) |
| `vdn` | Value Decomposition Networks |
| `qmixlocal` | QMIX mixing per-agent Q-values **without** centralized global state |
| `qmixglobal` | Canonical QMIX — per-agent Q-values **plus** centralized global state |

> `qmix` is accepted as a backward-compatible alias and maps to `qmixlocal`.

> **Reproducibility (constitution Q3):** use **at least 5 seeds** for any result you intend
> to report. Single-seed runs are not statistically meaningful for algorithm comparison.

## 2. CLI arguments and defaults

These are the actual defaults from [`run_benchmark.py`](../../benchmarl_setup/run_benchmark.py):

| Flag | Default | Purpose |
|------|---------|---------|
| `--algorithms` | `iql,vdn,qmixlocal,qmixglobal` | Comma-separated algorithms (run in parallel) |
| `--seeds` | `0,1,2,3,4` | Comma-separated seeds (run serially per algorithm) |
| `--max-frames` | `50000` | Total collected frames per run (training budget) |
| `--frames-per-batch` | `200` | Frames collected before each optimization phase |
| `--optimizer-steps` | `10` | Gradient steps per batch |
| `--train-batch-size` | `128` | Minibatch size sampled from replay |
| `--memory-size` | `10000` | Replay buffer capacity |
| `--init-random-frames` | `1000` | Random-action frames before learning starts |
| `--number-ghosts` | `2` | Cooperative ghost agents |
| `--grid-size` | `20` | Grid dimension |
| `--maze` | `default` | `default` or `pinklike` |
| `--save-folder` | `benchmarl_setup/runs` | Where run folders + summary are written |
| `--checkpoint-interval` | `0` | Periodic checkpoint cadence in frames (`0` = off) |
| `--checkpoint-at-end` / `--no-checkpoint-at-end` | on | Save a final checkpoint per run |
| `--stop-on-error` | off | Abort the whole benchmark if any run fails |
| `--tail-window` | `20` | Window for `tail_mean_reward` in the summary |
| `--summary-out` | `benchmarl_setup/runs/benchmark_summary.csv` | Summary CSV path |
| `--no-summary` | off | Skip summary generation |
| `--live-progress-file` | `benchmarl_setup/runs/live_progress.csvl` | Live progress stream consumed by `liveplot.py` |
| `--report-interval-seconds` | `1.0` | Live-progress polling interval |
| `--no-liveplot-report` | off | Disable live-progress writing |

> **Heads-up — defaults differ between the two runners.** The benchmark orchestrator
> defaults to `--max-frames 50000` and `--init-random-frames 1000`, whereas the single-run
> runner [`run_pacman_benchmarl.py`](../../benchmarl_setup/run_pacman_benchmarl.py) defaults
> to `60000` and `2000`. Pass the flags explicitly if you need them identical across both
> paths.

> **IQL auto-tuning.** For `--algorithm iql`, the single-run runner applies convergence-
> oriented hyperparameters with **no CLI flags of their own**: epsilon anneal `1.0 → 0.05`
> over 80% of the budget, `lr 1e-4`, `gamma 0.99`. VDN/QMIX keep BenchMARL's stock schedule.
> This is applied automatically inside each benchmark sub-run too.

## 3. Recommended workflow (with live monitoring)

Run the monitor in one terminal and the benchmark in another so you can watch
mean ± std reward curves per algorithm as they train.

**Terminal A — live monitor:**

```bash
py -3.11 benchmarl_setup\liveplot.py --algorithms iql,vdn,qmixlocal,qmixglobal
```

**Terminal B — benchmark:**

```bash
py -3.11 benchmarl_setup\run_benchmark.py --algorithms iql,vdn,qmixlocal,qmixglobal --seeds 0,1,2,3,4
```

Live-monitor tuning:

```bash
py -3.11 benchmarl_setup\liveplot.py --interval 1.0 --window 3
py -3.11 benchmarl_setup\run_benchmark.py --live-progress-file benchmarl_setup\runs\live_progress.csvl --report-interval-seconds 1.0
```

## 4. Quick smoke test first

Before committing to a long run, validate the whole pipeline end-to-end with a tiny budget
and fewer seeds (seconds-to-minutes, not hours):

```bash
py -3.11 benchmarl_setup\run_benchmark.py --algorithms iql,vdn --seeds 0,1 --max-frames 1200
```

If this produces run folders and a `benchmark_summary.csv`, scale up to the full
convergence-scale benchmark.

## 5. Outputs — what you get

Everything lands under `--save-folder` (default `benchmarl_setup/runs/`):

- **Per-run folders** named `<prefix>_pacman_*` (prefix is `iql`, `vdn`, or `qmix`;
  QMIX-local vs QMIX-global are disambiguated by the `include_global_state` flag recorded in
  each run's `hparams`). Each contains CSV scalar logs and (by default) a final checkpoint.
- **`benchmark_summary.csv`** — one row per run with these columns:

  | Column | Meaning |
  |--------|---------|
  | `algorithm` | Algorithm name |
  | `seed` | Seed |
  | `run_dir` | Path to the run folder |
  | `n_points` | Number of logged reward points |
  | `final_reward` | Last reward value |
  | `tail_mean_reward` | Mean over the last `--tail-window` points |
  | `best_reward` | Best reward observed |
  | `checkpoint_path` | Path to the saved checkpoint |

- **`live_progress.csvl`** — streaming progress consumed by `liveplot.py`.

## 6. Plot the comparison figure

After the benchmark finishes, render all algorithms in one figure (mean curve + std band per
algorithm):

```bash
py -3.11 benchmarl_setup\plot_benchmarl_reward.py --algorithms iql,vdn,qmixlocal,qmixglobal --show-runs
```

Useful options:

```bash
--window 5 --out benchmarl_setup\runs\benchmark_iql_vdn.png --no-open
```

Default output paths when `--out` is omitted:

- Multiple algorithms → `benchmarl_setup/runs/benchmark_reward_multiseed_mean_std.png`
- Single algorithm → `benchmarl_setup/runs/<algorithm>_reward_multiseed_mean_std.png`

## 7. Did the ghosts actually learn to win? (win-rate evaluation)

Reward curves alone do not tell you whether the trained policy *wins*. Use the headless
win-rate harness (ask for more than one episode, or pass `--win-rate-out`):

```bash
py -3.11 custom_environment\eval.py --learner iql --episodes 50 --eval-epsilon 0.05 --win-rate-out benchmarl_setup\runs\iql_win_rate.csv
```

Prints a summary like:

```text
Win-rate over 50 episodes | learner=iql | ghosts win 33 (66.0%) | pacman win 17 | timeout 0
```

- **`--eval-epsilon`** matters because the environment is fully deterministic; without
  injected per-ghost randomness every greedy episode is identical (trivial 0%/100%).
  `0.05` is the default; `0` collapses to the single deterministic outcome.
- Episode `e` uses `seed + e` (base seed from `--seed`, default `0`).

> **Expected result for IQL (plan-000008 baseline):** IQL measures a **0% ghost win rate**
> even at 300k frames. This is a coordination ceiling, not a budget problem — IQL learns each
> ghost's Q-values *independently*, so two ghosts with only a 5×5 local view never discover
> the joint pincer needed to corner a fleeing Pacman. The value-factorization algorithms
> (`vdn`, `qmixlocal`, `qmixglobal`) are the coordination path expected to win. The win-rate
> harness is the tool that makes this contrast measurable.

## 8. Keeping two mazes separate

Both mazes write the same `<algorithm>_pacman_*` prefix, so train each maze into its own
folder and read it back with `--runs-root` / `--save-folder`:

```bash
py -3.11 benchmarl_setup\run_benchmark.py --algorithms iql,vdn --maze default  --save-folder benchmarl_setup\runs\default
py -3.11 benchmarl_setup\run_benchmark.py --algorithms iql,vdn --maze pinklike --save-folder benchmarl_setup\runs\pinklike

py -3.11 benchmarl_setup\plot_benchmarl_reward.py --algorithms iql,vdn --runs-root benchmarl_setup\runs\pinklike
```

The maze is recorded in each run's task config, so `eval.py` rebuilds the correct maze from
the checkpoint automatically (no `--maze` needed at eval time).

## 9. Common pitfalls

- **Wrong Python** — always `py -3.11`. Reproducibility (constitution T1) depends on it.
- **Too few seeds** — `<5` seeds is not reportable (constitution Q3).
- **Comparing reward curves across reward-system versions** — magnitudes were retuned in
  plan-000008; curves from before that change are **not directly comparable**.
- **Long wall-clock time** — full convergence-scale benchmarks are slow. Smoke-test with
  `--max-frames 1200 --seeds 0,1` first.
- **One bad run aborting everything** — by default a failed run is recorded and the benchmark
  continues; add `--stop-on-error` only if you want fail-fast.
- **`--init-random-frames` / `--max-frames` mismatch** between the benchmark and single
  runner defaults — set them explicitly when comparing single vs benchmark runs.

## 10. End-to-end recipe (copy/paste)

```bash
# 1. Setup (once)
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
py -3.11 -m pip install -r requirements.txt
py -3.11 benchmarl_setup\register_pacman_env.py

# 2. Smoke test
py -3.11 benchmarl_setup\run_benchmark.py --algorithms iql,vdn --seeds 0,1 --max-frames 1200

# 3. Full benchmark (Terminal A: monitor; Terminal B: train)
py -3.11 benchmarl_setup\liveplot.py --algorithms iql,vdn,qmixlocal,qmixglobal
py -3.11 benchmarl_setup\run_benchmark.py --algorithms iql,vdn,qmixlocal,qmixglobal --seeds 0,1,2,3,4 --max-frames 50000

# 4. Plot comparison
py -3.11 benchmarl_setup\plot_benchmarl_reward.py --algorithms iql,vdn,qmixlocal,qmixglobal --show-runs

# 5. Win-rate per algorithm
py -3.11 custom_environment\eval.py --learner vdn --episodes 50 --eval-epsilon 0.05 --win-rate-out benchmarl_setup\runs\vdn_win_rate.csv
```

---

## Q&A log

**Q1 (2026-06-20 15:09 UTC):** parse readme and create a comprehensive tutorial on how to run benchmark training

**A1:** Produced the step-by-step tutorial above, grounded in `README.md` and verified against
the actual CLI definitions in `run_benchmark.py` and `run_pacman_benchmarl.py`. The benchmark
entrypoint is `benchmarl_setup/run_benchmark.py` (parallel algorithms, serial seeds); the
one-command full benchmark is
`py -3.11 benchmarl_setup\run_benchmark.py --algorithms iql,vdn,qmixlocal,qmixglobal --seeds 0,1,2,3,4 --max-frames 50000`.
Outputs (per-run folders, `benchmark_summary.csv`, `live_progress.csvl`) go to
`benchmarl_setup/runs/`. Monitor live with `liveplot.py`, plot with `plot_benchmarl_reward.py`,
and quantify wins with the `eval.py` win-rate harness. Two defaults differ between the
benchmark orchestrator and the single runner (`--max-frames` 50000 vs 60000;
`--init-random-frames` 1000 vs 2000) — flagged as a pitfall.

## Recommendations summary

1. **(HIGH) Use `run_benchmark.py` as the single benchmark entrypoint** — it orchestrates
   parallel-algorithm / serial-seed execution and auto-writes the summary CSV; do not script
   multiple `run_pacman_benchmarl.py` calls manually.
2. **(HIGH) Smoke-test before full runs** — `--algorithms iql,vdn --seeds 0,1 --max-frames 1200`
   validates the pipeline cheaply before committing to convergence-scale budgets.
3. **(MEDIUM) Always run ≥5 seeds for reportable results** (constitution Q3) and validate
   policy quality with the `eval.py` win-rate harness, not reward curves alone.
4. **(MEDIUM) Set `--max-frames` and `--init-random-frames` explicitly** when comparing
   single-run vs benchmark results, because the two runners ship different defaults.
5. **(LOW) Optionally promote this tutorial into the repo** as a standalone
   `docs/`/`TUTORIAL.md` or via `/document`, so it lives next to the code rather than only in
   `_output/research-logs/`.
