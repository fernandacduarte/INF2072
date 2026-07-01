# INF2072
Repositório para a disciplina TOP INTELIGENCIA ARTIFIC III - 2026.1

## BenchMARL Setup

### Installation
Install the required dependencies:
```bash
py -3.11 -m pip install -r requirements.txt
```

### Pacman + BenchMARL Compatibility Check
BenchMARL 1.5.x does **not** provide a runtime `register_env` function.
The `register_pacman_env.py` script is a smoke test that validates:
1. Your Pacman environment instantiates correctly.
2. BenchMARL can be imported in the same Python environment.

Run it with:
```bash
py -3.11 benchmarl_setup\register_pacman_env.py
```

If the script prints that `register_env` is unavailable, that is expected for BenchMARL 1.5.x.
Custom environments must be integrated by implementing a custom BenchMARL `Task`/`TaskClass` plugin.

### Running Experiments
This repository now includes a custom BenchMARL Task/TaskClass adapter for Pacman in:

- `benchmarl_setup/pacman_benchmarl_task.py`

Use the runner below to train ghosts with IQL, VDN, QMIX local, or QMIX global:

```bash
py -3.11 benchmarl_setup\run_pacman_benchmarl.py --algorithm iql
py -3.11 benchmarl_setup\run_pacman_benchmarl.py --algorithm vdn
py -3.11 benchmarl_setup\run_pacman_benchmarl.py --algorithm qmixlocal
py -3.11 benchmarl_setup\run_pacman_benchmarl.py --algorithm qmixglobal
```

Device selection for training uses `--device` (`cpu`, `cuda`, `cuda:0`, or `auto`):

```bash
py -3.11 benchmarl_setup\run_pacman_benchmarl.py --algorithm iql --device cpu
py -3.11 benchmarl_setup\run_pacman_benchmarl.py --algorithm qmixglobal --device auto
py -3.11 benchmarl_setup\run_pacman_benchmarl.py --algorithm vdn --device cuda:0
```

If CUDA is requested but unavailable, the runner falls back to CPU by default.
To fail fast instead, use `--no-allow-cpu-fallback`.

Algorithm variants:

- `qmixlocal`: uses per-agent Q-values for mixing without centralized global state.
- `qmixglobal`: canonical QMIX variant that uses per-agent Q-values plus centralized global state for the mixer.

**IQL tuning (plan-000008).** The default training budget is now `--max-frames
60000` (a convergence-scale value; pass a smaller number such as `--max-frames
1200` for quick smoke runs). IQL, VDN, and QMIX now share the same tuned
hyperparameters for fairer comparisons: epsilon anneal `1.0 → 0.10` over 95%
of the budget, `lr 1e-4`, `gamma 0.99`, and default `--init-random-frames 5000`.

By default, training now saves a checkpoint at the end of the run.
You can disable this with:

```bash
py -3.11 benchmarl_setup\run_pacman_benchmarl.py --algorithm iql --no-checkpoint-at-end
```

To render one full episode controlled by the trained learner policy:

```bash
py -3.11 custom_environment\eval.py --learner iql
py -3.11 custom_environment\eval.py --learner vdn
py -3.11 custom_environment\eval.py --learner qmixlocal
py -3.11 custom_environment\eval.py --learner qmixglobal
```

By default, evaluation opens the human-view Pygame renderer. To preserve the
original ASCII terminal rendering, use:

```bash
py -3.11 custom_environment\eval.py --learner iql --render-mode ascii --delay 0.08
```

For step-by-step debugging of low/zero capture behavior, you can emit one JSON
diagnostics object per step in ASCII mode:

```bash
py -3.11 custom_environment\eval.py --learner iql --maze pinklike3 --render-mode ascii --delay 0 --show-reward-breakdown --ascii-step-json
```

Each JSON line includes action/reward by ghost, Pacman and ghost positions,
visibility and sighting memory, capture/timeout/pacman-win flags, pellet counts,
and reward decomposition.

The Pygame renderer highlights each ghost's current local observation (11x11 by default) with
a translucent ghost-colored overlay. When the episode ends, the window shows the
final result (`Ghosts win`, `Pacman wins`, or `Run stopped`) with steps, team
reward, and elapsed time; in `human` mode it stays open until you close it.

You can test the renderer before training any checkpoint with a random-policy
episode:

```bash
py -3.11 custom_environment\render_demo.py --render-mode human --fps 12 --max-steps 200
```

For headless smoke tests or screenshots, use `rgb_array`:

```bash
py -3.11 custom_environment\render_demo.py --render-mode rgb_array --max-steps 3 --screenshot-out benchmarl_setup\runs\default\pacman_render.png
```

`custom_environment/eval.py` loads the latest checkpoint for the selected learner from `benchmarl_setup/runs/<maze>`.
It now supports futebol2d-style best-run selection across multiple runs:

```bash
py -3.11 custom_environment\eval.py --learner iql --maze default --checkpoint-select best
py -3.11 custom_environment\eval.py --learner iql --maze default --checkpoint-select best --checkpoint-best-metric capture_rate
```

For `--checkpoint-best-metric capture_rate`, best selection is checkpoint-coupled: the
run is considered only when `evaluation_report_live_capture.csv` includes a
`checkpoint_path` that matches that run's latest checkpoint. This avoids stale
run-level capture files selecting a different checkpoint than the one replayed.
If run artifacts were moved/copied (for example `runs` -> `runs100000`), selection
also accepts a relocation-safe identity match (`run_dir` + checkpoint filename)
while still rejecting stale checkpoint-frame mismatches.
If no checkpoint-coupled capture files are available, rerun live snapshot evaluation
or temporarily use `--checkpoint-best-metric reward`.

Benchmark live snapshots now write both `evaluation_report_live_capture.csv`
(latest-pointer file) and checkpoint-specific files such as
`evaluation_report_live_capture_checkpoint_100000.csv` for provenance.

Evaluation also supports explicit device selection:

```bash
py -3.11 custom_environment\eval.py --learner iql --maze pinklike --device auto
py -3.11 custom_environment\eval.py --learner qmixglobal --maze pinklike --device cuda --no-allow-cpu-fallback --checkpoint-select best
```

Use `--checkpoint-select latest` to force newest-run behavior, or `--checkpoint` to provide an explicit `.pt` file.

Evaluation now forces hard Pacman replay by default, regardless of whether the
checkpoint was trained with fixed difficulty or curriculum. This guarantees that
final checkpoint evaluation is always performed against hard Pacman.

If you intentionally want to replay with the checkpoint's original Pacman
difficulty/curriculum behavior, opt out with:

```bash
py -3.11 custom_environment\eval.py --learner qmixglobal --allow-non-hard-checkpoint
```

`custom_environment/eval_report.py` follows the same default behavior (hard-forced
Pacman replay for all evaluated checkpoints). To preserve original checkpoint
difficulty/curriculum behavior in reports, pass:

```bash
py -3.11 custom_environment\eval_report.py --maze pinklike3 --algorithms iql,vdn,qmixglobal --allow-non-hard-checkpoint
```

Benchmark note: `benchmarl_setup/run_benchmark.py` now keeps live capture
snapshots checkpoint-native by default during training, so capture follows each
checkpoint's curriculum stage (easy -> medium -> hard over the configured thirds).
This behavior is fixed (no CLI toggle).
Snapshot evaluation now passes each checkpoint frame as curriculum offset to
`eval_report.py`, so checkpoint-native snapshots reconstruct the expected
curriculum stage for that checkpoint (for example late-third checkpoints evaluate
under hard stage).

After benchmark workers complete, `run_benchmark.py` performs a latest-checkpoint
capture refresh in hard-forced mode so end-of-run selection by
`--checkpoint-best-metric capture_rate` stays aligned with hard CLI replay in
`custom_environment/eval.py`.

Final paired benchmark evaluation (`--eval-episodes`) still uses checkpoint-native
mode by default.

Useful optional parameters for training (`benchmarl_setup\run_pacman_benchmarl.py`):

```bash
--max-frames 5000 --frames-per-batch 200 --optimizer-steps 10 --train-batch-size 128 --memory-size 10000
--init-random-frames 5000
--ghost-view-size 3|5|7
--device cpu|cuda|cuda:0|auto --allow-cpu-fallback
--pacman-difficulty easy|medium|hard
--pacman-random-action-prob 0.0
--pacman-safe-distance 1
--pacman-curriculum off|easy-medium-hard|mixed-easy-medium-hard --pacman-curriculum-max-frames 60000
--epsilon-init 1.0 --epsilon-end 0.08 --epsilon-anneal-ratio 0.40
--randomize-spawns|--no-randomize-spawns --randomize-spawns-min-distance 4
```

Pacman training-difficulty control is now configurable:

- `--pacman-difficulty hard` keeps the current deterministic safety-first controller.
- `--pacman-difficulty easy` uses a weak random-valid Pacman baseline.
- `--pacman-difficulty medium` uses the safety policy with exploration noise.
- `--pacman-curriculum easy-medium-hard` keeps curriculum-learning by thirds and applies a shared stage profile to both Pacman type sampling and spawn-mode sampling:
  - easy third: `70% easy / 30% medium / 0% hard`
  - medium third: `40% easy / 40% medium / 20% hard`
  - hard third: `20% easy / 40% medium / 40% hard`
- `--pacman-curriculum mixed-easy-medium-hard` is supported as a compatibility alias and follows the same stage-coupled behavior.
- `--randomize-spawns` is **disabled by default** (`--no-randomize-spawns` effective default).
  Use `--randomize-spawns` to randomize Pacman/ghost spawn cells each episode,
  and `--randomize-spawns-min-distance` to enforce minimum ghost->Pacman BFS clearance
  for sampled starts.

Curriculum spawn modes per stage map to:

- `near`: ghosts spawn `4-8` BFS steps from Pacman
- `medium`: ghosts spawn `8-14` BFS steps from Pacman
- `normal`: map-authored default spawns

Spawn sampling enforces:

- minimum ghost-ghost BFS distance `>= 2`
- no ghost spawns directly on Pacman
- ghosts cannot all start in one corridor line (all same row or all same column)

When `--pacman-curriculum easy-medium-hard` or `--pacman-curriculum mixed-easy-medium-hard` is enabled, exploration epsilon
uses stage-aligned resets (for all algorithms). In each stage, epsilon decays
to `0.08` during the first `40%` of that stage and remains flat for the
remaining `60%`:

- Easy phase (`[0, 1/3)`): `1.00 -> 0.08` over first 40%, then stable
- Medium phase (`[1/3, 2/3)`): reset `0.65 -> 0.08` over first 40%, then stable
- Hard phase (`[2/3, 1]`): reset `0.55 -> 0.08` over first 40%, then stable

Transition boundaries use exact thirds of `--max-frames`.
With `--pacman-curriculum off`, the previous global schedule remains unchanged
(`1.00 -> 0.10` over 95% of `--max-frames`).

Explicit epsilon override rule: pass `--epsilon-init`, `--epsilon-end`, and
`--epsilon-anneal-ratio` together (all three) to override epsilon schedule
values. Partial epsilon overrides are rejected. With curriculum enabled, this
override keeps curriculum piecewise structure (third boundaries and stage
resets) while applying the provided epsilon values/decay fraction.

Examples:

```bash
# Fixed weak Pacman (bootstrap)
py -3.11 benchmarl_setup\run_pacman_benchmarl.py --algorithm vdn --maze pinklike3 --pacman-difficulty easy

# Fixed medium Pacman with stochasticity
py -3.11 benchmarl_setup\run_pacman_benchmarl.py --algorithm vdn --maze pinklike3 --pacman-difficulty medium --pacman-random-action-prob 0.25

# Curriculum: easy -> medium -> hard over the full run
py -3.11 benchmarl_setup\run_pacman_benchmarl.py --algorithm qmixglobal --maze pinklike3 --max-frames 60000 --pacman-curriculum easy-medium-hard --pacman-curriculum-max-frames 60000

# Compatibility alias for the same stage-coupled curriculum behavior
py -3.11 benchmarl_setup\run_pacman_benchmarl.py --algorithm qmixglobal --maze pinklike3 --max-frames 60000 --pacman-curriculum mixed-easy-medium-hard --pacman-curriculum-max-frames 60000

# Enable randomized spawns during training
py -3.11 benchmarl_setup\run_pacman_benchmarl.py --algorithm iql --maze pinklike3 --randomize-spawns --randomize-spawns-min-distance 4

# Explicitly keep deterministic map-authored spawns (same as default)
py -3.11 benchmarl_setup\run_pacman_benchmarl.py --algorithm iql --maze pinklike3 --no-randomize-spawns
```

The benchmark runner (`benchmarl_setup/run_benchmark.py`) follows the same default
(`--no-randomize-spawns`) and supports the same flags.

Useful optional parameters for evaluation (`custom_environment\eval.py`):

```bash
--delay 0.25 --max-steps 200 --maze default --checkpoint-select best --show-reward-breakdown
--ascii-step-json
--render-mode ascii|human|rgb_array --tile-size 28 --fps 12 --screenshot-out path\to\frame.png
--hide-observations --device cpu|cuda|cuda:0|auto --allow-cpu-fallback
--allow-non-hard-checkpoint
--ghost-view-size 3|5|7
--checkpoint-best-metric capture_rate|reward
```

If a legacy checkpoint was trained with a different local view size and auto-detection fails,
set it explicitly in eval:

```bash
py -3.11 custom_environment\eval.py --learner iql --maze default --ghost-view-size 3
```

You can also pass an explicit checkpoint to eval:

```bash
--checkpoint path\to\checkpoint_5000.pt
```

For a compact post-training quality report (deterministic policy, multiple episodes), use:

```bash
py -3.11 custom_environment\eval_report.py --maze pinklike --algorithms iql,vdn,qmixglobal --checkpoint-select best --episodes 30
py -3.11 custom_environment\eval_report.py --maze pinklike --algorithms iql,vdn,qmixglobal --checkpoint-select best --checkpoint-best-metric capture_rate --episodes 30
```

When benchmark runs are stored under device subfolders (for example `runs/<maze>/cpu` and `runs/<maze>/cuda`), set `--device-label` explicitly or leave it as `auto`:

```bash
py -3.11 custom_environment\eval_report.py --maze pinklike --algorithms iql,vdn,qmixglobal --device-label cuda --checkpoint-select best --episodes 30
py -3.11 custom_environment\eval_report.py --maze pinklike --algorithms iql,vdn,qmixglobal --device-label auto --checkpoint-select best --episodes 30
```

This writes `benchmarl_setup/runs/<maze>/evaluation_report.csv` plus an
`evaluation_report_by_variant.csv` across-training-seed summary. The detailed report includes:

- `ghost_win_rate`
- `pacman_win_rate`
- `mean_episode_return`
- `std_episode_return`
- `median_episode_return`
- `mean_steps`
- `capture_rate`, `timeout_rate`, `pellet_win_rate`, and `evaluation_cutoff_rate`
- `mean_steps_to_capture` and `median_steps_to_capture`
- `frac_steps_visible` and `mean_newly_spotted_count`
- `mean_shaping_return` and `mean_terminal_return`

Useful options for deterministic report evaluation (`custom_environment\eval_report.py`):

```bash
--episodes 30 --max-steps 200 --seed-base 0 --out benchmarl_setup\runs\pinklike\evaluation_report_best.csv
--learner qmixglobal --checkpoint-select latest
--checkpoint-select best --checkpoint-best-metric capture_rate|reward
--learner qmixglobal --checkpoint path\to\checkpoint.pt
--device-label auto|cpu|cuda|cuda_0
--reward-id current --train-seeds 0,1,2
--device cpu|cuda|cuda:0|auto --allow-cpu-fallback
--allow-non-hard-checkpoint
--jobs-path path\to\benchmark_jobs.csv
--ghost-view-size 3|5|7 --verbose
```

Reward-aware runs are discovered under `runs/<maze>/<reward_id>/<device>/`; the
legacy pre-strategy layout remains supported for `--reward-id current`. Use this
report to compare final policy quality across algorithms under deterministic action
selection instead of relying only on training scalar curves. Capture rate and
time-to-capture are the primary behavioral metrics; reward returns are diagnostic
because their scales may differ between reward strategies.

Useful optional rendering parameters for the random-policy demo
(`custom_environment\render_demo.py`):

```bash
--render-mode ascii|human|rgb_array --max-steps 200 --delay 0.0 --tile-size 28 --fps 12
--grid-size 20 --seed 0 --screenshot-out path\to\frame.png --hide-observations
```

Outputs are saved under `benchmarl_setup/runs/<maze>` by default.

### Mazes (Map Selection)

### How to Set Number of Ghosts

The number of ghosts is currently defined by the maze layout itself: it equals the number of `G` spawn markers in the selected map.

How to change it:

1. Edit the layout in `custom_environment/utils.py` (`DEFAULT_LAYOUT` or `PINKLIKE_LAYOUT`), or create new layouts.
2. Add or remove `G` characters.
3. Run with that maze (`--maze default`, `--maze pinklike`, or `--maze pinklike3`).

Three maze layouts are available via `--maze`:

- `default`: a 20x20 lattice maze.
- `pinklike`: a 20x20 maze resembling the classic "Pink" Pacman maze, without portals.
- `pinklike3`: a `pinklike`-style 20x20 map variant with three ghost spawns.

**Layout notation (map-authored spawns + pellets).** Mazes are defined as ASCII layouts in
`custom_environment/utils.py` (`DEFAULT_LAYOUT`, `PINKLIKE_LAYOUT`, `PINKLIKE_LAYOUT3`) and parsed by `parse_layout`
into a `MazeSpec` (grid + spawns + cosmetic pellet mask). The map itself declares where every
entity starts, so there are no hardcoded spawn positions. Characters:

- `%` or `#` — wall
- `.` — pellet;  `o` — power pellet (treated as a pellet for now)
- `G` — ghost spawn (the number of ghosts equals the number of `G`s)
- `P` — Pac-Man spawn (exactly one)
- space (or any other char) — empty, no pellet

`parse_layout` validates a single `P`, at least one `G`, a solid border, and full connectivity
(`assert_connected`). Pellets do not alter per-step local observations, but they do affect
episode outcomes: Pacman wins when all pellets are eaten, which applies the configured
terminal reward outcome. To add a maze, define a new layout list + register it in the `MAZES` dict.

The selected maze is supported by training, benchmarking, and the render demo:

```bash
py -3.11 benchmarl_setup\run_pacman_benchmarl.py --algorithm iql --maze pinklike
py -3.11 benchmarl_setup\run_benchmark.py --algorithms iql,vdn --seeds 0,1,2 --maze pinklike
py -3.11 custom_environment\render_demo.py --render-mode human --maze pinklike
py -3.11 custom_environment\render_demo.py --render-mode human --maze pinklike3
```

Use the same `--maze` at evaluation/plot time so the command reads from the matching
subfolder.

**Keeping the two mazes' runs separate.** Runs are now separated automatically under
`benchmarl_setup/runs/<maze>`. Use `--maze` consistently across training, evaluation, and plotting:

```bash
py -3.11 benchmarl_setup\run_benchmark.py --algorithms iql,vdn --maze default
py -3.11 benchmarl_setup\run_benchmark.py --algorithms iql,vdn --maze pinklike
py -3.11 benchmarl_setup\run_benchmark.py --algorithms iql,vdn --maze pinklike3

py -3.11 custom_environment\eval.py --learner iql --maze pinklike
py -3.11 custom_environment\eval.py --learner iql --maze pinklike3
py -3.11 benchmarl_setup\plot_benchmarl_reward.py --algorithms iql,vdn --maze pinklike
py -3.11 benchmarl_setup\plot_benchmarl_reward.py --algorithms iql,vdn --maze pinklike3
```

New mazes can be registered in `custom_environment/utils.py` via the `MAZES` registry
(`grid_from_ascii` parses an ASCII layout; `assert_connected` validates reachability).

### Benchmark (Multi-Seed, Parallel by Algorithm)

You can now run a full benchmark with one command using:

- `benchmarl_setup/run_benchmark.py`

Example (5 seeds, shared training config):

```bash
py -3.11 benchmarl_setup\run_benchmark.py --algorithms iql,vdn,qmixlocal,qmixglobal --seeds 0,1,2,3,4 --max-frames 60000
```

Benchmark now supports device sweeps in one command:

```bash
py -3.11 benchmarl_setup\run_benchmark.py --algorithms iql,vdn,qmixlocal,qmixglobal --seeds 0,1,2,3,4 --devices cpu,cuda --max-frames 60000
```

If multiple requested devices resolve to the same runtime target (for example `cpu,cuda` when CUDA is unavailable and fallback is enabled), the benchmark now fails fast with an explicit error instead of silently dropping one device leg.

Runs are separated by resolved device under:

- `benchmarl_setup/runs/<maze>/cpu`
- `benchmarl_setup/runs/<maze>/cuda`

Execution strategy:

- Algorithms run in parallel (for example IQL and VDN at the same time).
- Seeds run serially inside each algorithm worker.

Useful optional parameters:

```bash
--algorithms iql,vdn,qmixlocal,qmixglobal --frames-per-batch 200 --optimizer-steps 10 --train-batch-size 128 --memory-size 10000 --init-random-frames 5000
--ghost-view-size 3|5|7
--epsilon-init 1.0 --epsilon-end 0.08 --epsilon-anneal-ratio 0.40
--devices cpu,cuda --allow-cpu-fallback --jobs-out benchmarl_setup\runs\benchmark_jobs_myhost.csv --machine-id myhost
```

This command now trains and then automatically writes a benchmark summary CSV.

By default (when explicit output paths are omitted), it writes machine-suffixed artifacts:

- `benchmarl_setup/runs/<maze>/benchmark_summary_<machine_id>.csv`
- `benchmarl_setup/runs/<maze>/reward_eval_<machine_id>.csv`
- `benchmarl_setup/runs/<maze>/live_progress_<machine_id>.csvl`
- `benchmarl_setup/runs/benchmark_jobs_<machine_id>.csv`

It also writes a per-job timing ledger (`benchmark_jobs_<machine_id>.csv`) with wall-clock duration and run mapping.

The summary CSV includes, per run:

- `device`
- `algorithm`
- `seed`
- `run_dir`
- `n_points` (points in `collection_reward_reward_mean.csv`, immediate reward metric)
- `n_episode_points` (points in `collection_reward_episode_reward_mean.csv`, episode-return metric)
- `final_reward` (immediate reward)
- `tail_mean_reward` (immediate reward)
- `best_reward` (immediate reward)
- `final_episode_return` (episode return)
- `tail_mean_episode_return` (episode return)
- `best_episode_return` (episode return)
- `duration_seconds`
- `frames_per_second`
- `checkpoint_path`

### Summarize Benchmark Runs (Standalone)

Use:

- `benchmarl_setup/summarize_benchmark_runs.py`

This script can be run independently (without re-running training) to regenerate `benchmark_summary.csv` from existing run folders.

Example (single device layout under `runs/<maze>`):

```bash
py -3.11 benchmarl_setup\summarize_benchmark_runs.py --maze pinklike --algorithms iql,vdn,qmixglobal --devices cpu
```

Example (device-separated layout under `runs/<maze>/<device>`):

```bash
py -3.11 benchmarl_setup\summarize_benchmark_runs.py --maze default --algorithms iql,vdn,qmixlocal,qmixglobal --devices cpu,cuda --jobs-path benchmarl_setup\runs\default\benchmark_jobs.csv --out benchmarl_setup\runs\default\benchmark_summary.csv
```

Useful options:

```bash
--tail-window 20 --devices cpu,cuda --jobs-path benchmarl_setup\runs\default\benchmark_jobs.csv
--out benchmarl_setup\runs\pinklike\benchmark_summary_custom.csv
```

Notes:

- `--devices` filters device labels included in the summary (for example `cpu,cuda`).
- `--jobs-path` accepts one or more jobs CSV files and merges timing metrics (`duration_seconds`, `frames_per_second`).
- If `--jobs-path` is omitted, the script auto-discovers and merges all `benchmark_jobs*.csv` under the selected runs root.
- The printed aggregate is grouped by `algorithm + device`.

### Decisive reward A/B (sparse control vs PBRS)

This is the statistically-valid experiment that backs the PBRS claim (research-000024 R5;
constitution Q3 requires >=5 seeds). It compares two reward arms that differ **only** in
the potential-based shaping term:

- `capture_v0_sparse_control` -- the matched control: sparse terminals (+/-100) + `timestep -0.05`, **no shaping**.
- `capture_v0_pure_potential_shaping` -- the same arm **plus** the PBRS telescoping term.

Both share one weights dataclass, so the terminals and step cost cannot drift between arms.
Why a matched control and not the older `capture_v0`: `capture_v0` differs in terminals
(+45/-40/-45), `timestep` (-0.015), **and** carries an extra dense `pacman_legal_moves_reduced`
term -- comparing it to PBRS would confound shaping with three other differences.

**Run it (two commands):**

```bash
# 1. Train both arms across p in {0.25, 0.50, 0.75}, 5 seeds each (preview with --dry-run):
py -3.11 benchmarl_setup\run_reward_ab.py --devices cuda
#    (defaults: --algorithms iql,vdn,qmixglobal --seeds 0,1,2,3,4 --max-frames 60000
#     --eval-episodes 40 --maze pinklike3 --save-root benchmarl_setup\runs\ab)

# 2. Aggregate + render the comparison table and figures:
py -3.11 benchmarl_setup\plot_reward_ab.py --manifest benchmarl_setup\runs\ab\ab_manifest.csv
```

**The evasiveness regime.** With `--pacman-curriculum off`, `--pacman-difficulty hard` fixes the
defense-first Pacman heuristic (`pure_random=False`, `safe_distance=PACMAN_SAFE_DISTANCE`) and the
sole varying axis is `p = --pacman-random-action-prob`: the fraction of steps Pacman acts randomly
instead of evasively. So evasiveness `e = 1 - p`; `p=0.25` is the most evasive point, `p=0.75` the
least. The three interior points sit in the *learnable* regime (the fully-evasive `p=0` risks a
floor effect where neither arm learns). `--randomize-spawns` is held on throughout so ghosts must
pursue reactively rather than memorize a fixed route.

**How to read the figures.** PBRS is policy-invariant by construction, so the hypothesis is **faster
acquisition of pursuit (sample-efficiency), not a higher asymptotic capture_rate**. Read the headline
sample-efficiency panel (AULC / frames-to-threshold) and the `pursuit_fraction` panel first; treat
capture_rate as secondary. `pursuit_fraction` is the fraction of steps the ghost team's BFS distance
to Pacman strictly decreased -- it uses Pacman's true position as a **training/eval-time metric only**
(CTDE: the executing ghost policies never observe this distance), and it shows pursuit acquisition
that `capture_rate` alone cannot.

**Outputs and provenance (constitution T2/C1).** Per-point training writes under
`benchmarl_setup/runs/ab/p_<p>/<maze>/` (keyed by the per-`p` save-folder, the only disambiguator
since `run_benchmark.py` keys paths by maze/reward/device). The three **report artifacts** --
`ab_manifest.csv` (records the git commit + a dirty-tree flag), `reward_ab.csv`, and the comparison
PNGs -- are version-controlled (`.gitignore` negation rules), while the bulky checkpoint blobs and
per-run CSVs under `p_<p>/` stay ignored.

### CPU vs GPU Benchmark Protocol

Use this protocol for fair comparisons:

1. Keep configuration identical across devices (`--max-frames`, `--frames-per-batch`, `--optimizer-steps`, `--train-batch-size`, seeds).
2. Run a shared benchmark command with both devices:

```bash
py -3.11 benchmarl_setup\run_benchmark.py --algorithms iql,vdn,qmixlocal,qmixglobal --seeds 0,1,2,3,4 --devices cpu,cuda --max-frames 60000 --summary-out benchmarl_setup\runs\default\benchmark_summary_cpu_gpu.csv
```

3. Compare `duration_seconds` and `frames_per_second` by `algorithm` + `device` in the summary CSV.
4. If CUDA is unavailable, either install CUDA-enabled PyTorch/NVIDIA drivers or keep `--allow-cpu-fallback` enabled and inspect the resolved device logs.
5. For strict CPU-vs-GPU comparisons, prefer `--no-allow-cpu-fallback` so unavailable CUDA fails immediately.

### Live Plot During Training

Training now reports live progress to:

- `benchmarl_setup/runs/<maze>/live_progress_<machine_id>.csvl` (default)

Use `benchmarl_setup/liveplot.py` in a separate terminal to monitor running benchmarks with three synchronized axes:
- y1: rolling true capture snapshot percentage (mean ± std)
- y2: rolling average reward (plus rolling averages for individual reward terms if --individual-reward-plotting is passed).
- y3: epsilon schedule overlay

Liveplot now adds a fourth axis dedicated to terminal reward terms only
(`get_pacman`, `pacman_timeout_win`, `pacman_win_pellets`). Non-terminal
reward terms and average reward remain on y2 when individual reward plotting is enabled.
When benchmark metadata indicates curriculum mode, liveplot also draws vertical
markers at frame-boundary transitions: `easy->medium` / `medium->hard` for
`easy-medium-hard`, and `early->middle` / `middle->late` for
`mixed-easy-medium-hard`.

By default (`--device all`), it can display one line per algorithm-device pair (for example `IQL@cpu`, `IQL@cuda`).
When `iql` is included, the epsilon overlay is resolved from benchmark metadata
written to `live_progress*.csvl` (for example:
`#meta,max_frames=...,epsilon_init=...,epsilon_end=...,epsilon_anneal_ratio=...`).
Curriculum markers use the same metadata stream (`pacman_curriculum`,
`pacman_curriculum_max_frames`, `pacman_curriculum_frame_offset`).
Each metadata header also includes `machine_id=...`.
There are no built-in epsilon fallback defaults in plotting anymore.
If metadata is missing/incomplete, provide `--epsilon-*` flags explicitly.

Capture metric note: liveplot reads true capture snapshots generated by
deterministic objective evaluation over checkpoints (`eval_report.py`).
When checkpoint-specific files such as
`evaluation_report_live_capture_checkpoint_10000.csv` are available inside
each run directory, liveplot now treats them as authoritative and overlays
their capture values onto the progress stream by checkpoint frame.
This prevents stale or duplicated `live_progress*.csvl` rows from overriding
the checkpoint-native capture curve.
Non-evaluated training steps are written with `NaN` capture and ignored by
the capture curve. Reward is still emitted in the same progress stream and
shown on the second y-axis.

Reward terms note: benchmark live progress now appends per-term reward scalars
when available from deterministic `eval_report.py` snapshots using
`reward_breakdown_per_step_mean_json` (keys match your RewardStrategy
breakdown terms such as `timestep`, `reverse_action`, and
`pacman_legal_moves_delta`).
The metadata header includes `reward_terms=...`, and both live/offline plotters
can consume these columns to draw term-specific averages alongside total reward.
Individual reward-term plotting is disabled by default; enable it with
`--individual-reward-plotting`. `--reward-terms` filters terms only when
individual plotting is enabled.

Live snapshot cadence note: periodic updates require checkpoints. When
`--checkpoint-interval` is greater than zero, snapshots can appear during
training; when it is zero, snapshots appear only at end-of-run checkpoints.
By default, `run_benchmark.py` preserves machine-specific
`live_progress_<machine_id>.csvl` across sessions, so live/offline plots can
include algorithms completed in earlier runs for the same maze. Use
`--reset-live-progress` to truncate the selected stream for a clean,
session-only stream.

When `--live-progress-file` is omitted, `benchmarl_setup/liveplot.py` and
`benchmarl_setup/plot_benchmarl_reward.py` auto-discover and merge all
`live_progress*.csvl` files under `benchmarl_setup/runs/<maze>/`.

Start live monitor:

```bash
py -3.11 benchmarl_setup\liveplot.py --algorithms iql,vdn,qmixlocal,qmixglobal
```

Monitor only one device label:

```bash
py -3.11 benchmarl_setup\liveplot.py --algorithms iql,vdn --device cpu
py -3.11 benchmarl_setup\liveplot.py --algorithms iql,vdn --device cuda
```

Then run benchmark normally:

```bash
py -3.11 benchmarl_setup\run_benchmark.py --algorithms iql,vdn,qmixlocal,qmixglobal --seeds 0,1,2,3,4
py -3.11 benchmarl_setup\run_benchmark.py --algorithms iql,vdn,qmixlocal,qmixglobal --seeds 0,1,2,3,4 --checkpoint-interval 10000 --live-capture-eval-episodes 20
```

Shared network folder (many machines): when explicit output paths are not
provided, `run_benchmark.py` now writes machine-suffixed files by default:

- `live_progress_<machine_id>.csvl`
- `benchmark_summary_<machine_id>.csv`
- `reward_eval_<machine_id>.csv`
- `benchmark_jobs_<machine_id>.csv`

`machine_id` defaults to hostname (lowercased and filename-safe). Override it
with `--machine-id` if needed.

Useful options:

```bash
py -3.11 benchmarl_setup\liveplot.py --interval 1.0 --window 30
py -3.11 benchmarl_setup\liveplot.py --maze pinklike --device all --interval 1.0 --window 30
py -3.11 benchmarl_setup\liveplot.py --maze pinklike3 --algorithms iql,vdn --reward-ids capture_v0_pure_potential_shaping_pellets,capture_v0_pure_potential_shaping_pellets_fast_capture_bonus
py -3.11 benchmarl_setup\liveplot.py --individual-reward-plotting --reward-terms all
py -3.11 benchmarl_setup\liveplot.py --individual-reward-plotting --reward-terms timestep,potential_shaping
py -3.11 benchmarl_setup\liveplot.py --algorithm-labels "iql=IQL Agent,vdn=VDN Team" --reward-id-labels "current=Baseline,capture_merge4=CM4" --plot-title "Pinklike3 live comparison"
py -3.11 benchmarl_setup\run_benchmark.py --maze pinklike --live-progress-file benchmarl_setup\runs\pinklike\live_progress.csvl --report-interval-seconds 1.0
```

Live/offline legend formatting note: when every selected series is on CUDA,
the plot legends omit the redundant `@cuda` suffix.
When `--reward-ids` is provided, reward-id entries in legends follow exactly
the same order as passed on CLI.
In live plot, if all visible curves belong to a single algorithm, reward-id
curves use distinct colors (not hue/lightness variants of one base color).

### Plot Benchmark Capture % in One Figure (IQL, VDN, QMIX Local, QMIX Global)

Use:

- `benchmarl_setup/plot_benchmarl_reward.py`

This script can aggregate runs from multiple algorithms and plot all of them in the same figure with three y-axes:

- mean true capture snapshot percentage curve per algorithm (+/- std band)
- mean reward curve per algorithm
- epsilon overlay when `iql` is included

The offline plot now also includes a fourth axis dedicated to terminal reward
terms only (`get_pacman`, `pacman_timeout_win`, `pacman_win_pellets`).
Average reward and non-terminal reward terms remain on the reward axis when
individual reward plotting is enabled.
When progress metadata indicates curriculum mode, the offline plot also draws
vertical transition markers: `easy->medium` / `medium->hard` for
`easy-medium-hard`, and `early->middle` / `middle->late` for
`mixed-easy-medium-hard`.

Examples:

```bash
py -3.11 benchmarl_setup\plot_benchmarl_reward.py --algorithms iql,vdn --show-runs
py -3.11 benchmarl_setup\plot_benchmarl_reward.py --algorithms iql,vdn,qmixlocal,qmixglobal --show-runs
py -3.11 benchmarl_setup\plot_benchmarl_reward.py --algorithms iql,vdn,qmixglobal --maze pinklike3 --reward-id current --device cuda
```

Useful options:

```bash
--reward-id current --device auto|cpu|cuda|cuda:0
--reward-ids capture_merge3,capture_merge4
--progress-file benchmarl_setup\runs\pinklike3\live_progress.csvl
--epsilon-max-frames 200000 --epsilon-init 1.0 --epsilon-end 0.10 --epsilon-anneal-ratio 0.95
--individual-reward-plotting --reward-terms all|timestep,potential_shaping
--algorithm-labels "iql=IQL Agent,vdn=VDN Team" --reward-id-labels "current=Baseline,capture_merge4=CM4"
--plot-title "Benchmark True Capture Rate (Pinklike3)"
--maze pinklike --window 30 --out benchmarl_setup\runs\pinklike\benchmark_iql_vdn.png --no-open
```

By default, this script now reads from `--reward-id current` and `--device auto`
(all device labels under the selected reward root). Use `--device cuda` or
`--device cpu` to force one device folder. Epsilon overlay values are resolved
from merged `live_progress*.csvl` metadata (`max_frames`, `epsilon_init`,
`epsilon_end`, `epsilon_anneal_ratio`) with optional `--epsilon-*` overrides.
There are no built-in epsilon fallback defaults in this script; if metadata is
missing/incomplete, pass all required `--epsilon-*` values explicitly.
When metadata indicates curriculum piecewise epsilon, `--epsilon-*` overrides
now preserve curriculum piecewise shape instead of forcing a global curve.

Capture metric note: this plot reads capture values from merged
`live_progress*.csvl` files (unless `--progress-file` is provided).
For current benchmark runs, these capture points are true deterministic eval
snapshots (with non-evaluated steps as `NaN`).
When checkpoint-specific capture CSVs are present in run directories, the
offline plot now overlays those values as the source of truth per checkpoint
frame, so stale duplicate rows in `live_progress*.csvl` do not skew capture
curves.

Reward terms note: individual reward-term plotting is disabled by default.
Enable it with `--individual-reward-plotting`; then use `--reward-terms all`
or provide a comma list to focus on selected terms.

### Plot CPU vs GPU Speedup and Rewards (From Summary CSV)

Use:

- `benchmarl_setup/plot_cpu_gpu_summary.py`

This script reads `benchmark_summary.csv` and produces one image with:

- GPU/CPU speedup per algorithm (`>1.0` means GPU is faster)
- CPU vs GPU reward bars for a selected reward metric

Example:

```bash
py -3.11 benchmarl_setup\plot_cpu_gpu_summary.py --summary-csv benchmarl_setup\runs\default\benchmark_summary.csv --reward-metric tail_mean_reward --out benchmarl_setup\runs\default\cpu_gpu_summary_comparison.png
```

Alternative reward metrics:

```bash
py -3.11 benchmarl_setup\plot_cpu_gpu_summary.py --reward-metric final_reward
py -3.11 benchmarl_setup\plot_cpu_gpu_summary.py --reward-metric best_reward
```

If the script reports that no algorithm has both CPU and GPU rows, run benchmark first with `--devices cpu,cuda` and ensure CUDA is available.

### QMIX Global Mixer State Schema

For `qmixglobal`, the mixer receives a centralized state vector at each step.

For grid size `H x W` and `N` ghosts, the state dimension is:

- `H * W + 3 * N + 7`

State vector order:

1. `wall_map_flat` (`H*W`): binary static wall map flattened.
2. `ghost_positions_norm` (`2*N`): each ghost position normalized to `[0, 1]`.
3. `team_pacman_memory` (4):
   - `pacman_visible_now` (`0/1`)
   - `target_x_norm`
   - `target_y_norm`
   - `steps_since_last_seen_norm`
4. `ghost_to_target_dist_norm` (`N`): normalized BFS distance from each ghost to target memory.
5. `team_min_dist_norm` (1): minimum normalized ghost-to-target distance.
6. `episode_progress` (2):
   - `step_fraction`
   - `remaining_fraction`

Policy observations remain local (5x5 by default) for all algorithms; only `qmixglobal` mixer uses this centralized state.

If no `--out` is provided, the default output is:

- `benchmarl_setup/runs/<maze>/<reward_id>/benchmark_capture_multiseed_mean_std.png` (when plotting multiple algorithms)
- `benchmarl_setup/runs/<maze>/<reward_id>/<algorithm>_capture_multiseed_mean_std.png` (when plotting one algorithm)

### Plot de Reward IQL (Passo a Passo)

Use o script `benchmarl_setup/plot_iql_reward.py` para gerar um gráfico da média de recompensa com banda de desvio padrão rolante.

1. Execute pelo menos um treino de IQL para gerar logs em `benchmarl_setup/runs/<maze>`.

2. Gere o plot da execução IQL mais recente:

```bash
py -3.11 benchmarl_setup\plot_iql_reward.py
```

3. Abra o arquivo de saída padrão:

```text
benchmarl_setup/runs/default/iql_reward_mean_stddev.png
```

4. (Opcional) Escolha uma run específica com `--run-dir`:

```bash
py -3.11 benchmarl_setup\plot_iql_reward.py --maze default --run-dir "benchmarl_setup\runs\default\iql_pacman_mlp__SEU_RUN_ID"
```

5. (Opcional) Ajuste a janela do desvio padrão rolante:

```bash
py -3.11 benchmarl_setup\plot_iql_reward.py --window 10
```

6. (Opcional) Defina um caminho de saída customizado:

```bash
py -3.11 benchmarl_setup\plot_iql_reward.py --maze pinklike --out "benchmarl_setup\runs\pinklike\meu_plot_iql.png"
```

Parâmetros principais do script:

- `--runs-root`: pasta raiz das runs (padrão: `benchmarl_setup/runs`)
- `--maze`: subpasta do labirinto dentro de `--runs-root` (padrão: `default`)
- `--run-dir`: run específica (se omitido, usa a IQL mais recente)
- `--window`: janela para cálculo do desvio padrão rolante (padrão: `5`)
- `--out`: caminho do PNG de saída

### Pacman Reward System (Current)

The environment broadcasts one shared team reward to all ghosts, but its calculation
is now delegated to a `RewardStrategy`. Strategies receive an immutable transition
snapshot and keep their own episode history; they cannot mutate the environment.

The behavior-compatible default is
`custom_environment.env.rewards.current:CurrentTeamReward`. To add an experiment,
create a zero-argument `RewardStrategy` subclass with a unique `strategy_id`; no
central registry edit is required.

Current behavior note: the `repeated_direction_reversal` term is applied from the
first opposite-direction move (for example `A -> B -> A`), then scales with
consecutive reversals up to its existing cap. The strategy also penalizes
explicit two-step cycles (`A -> B -> A`) and opposite-direction adjacent
ghost pairs to reduce local ping-pong loops in multi-ghost play. For the
current ablation run, the `overlap_or_same_corridor` penalty and its pairwise
logic are temporarily disabled to isolate their effect on reward trends as
exploration decreases. Exploration terms were intentionally reduced
(`recently_unvisited_tile` and `reveal_unseen_local_cells`) so they do not
dominate returns when capture progress is poor. The strategy also provides a
`currently_visible` bonus whenever Pacman is visible to keep early training
signal dense for pursuit learning. Potential shaping now uses a team-aware
distance metric based on the two closest reachable ghosts (`d1 + 0.5*d2`,
falling back to `d1` when only one ghost is reachable) to reduce single-ghost
free-riding and reward coordinated closing pressure.

To re-enable that term as an explicit experiment, use
`custom_environment.env.rewards.current:CurrentWithOverlapOrSameCorridor`
(`strategy_id = current_with_overlap_or_same_corridor`). This keeps
`CurrentTeamReward` unchanged as the ablation baseline while enabling a clean
A/B comparison.

Four-way comparison setup:

- `custom_environment.env.rewards.current:CaptureV0Reward`
  (`strategy_id = capture_v0`): minimal reward baseline designed for scratch
  experiments with fewer interacting terms. It keeps terminal outcomes and
  timestep penalty, disables potential-shaping and exploration/movement shaping
  terms, and adds a +1 reward when Pacman legal moves are reduced on steps
  where Pacman is visible.

- `custom_environment.env.rewards.current:CaptureV0ImproveLegalMovesIncreaseTerminalRewardsReverseAction`
  (`strategy_id = capture_v0_improve_legal_moves_increase_terminal_rewards_reverse_action`):
  capture_v0 variant with stronger terminal rewards, smooth legal-moves delta
  shaping (`0.2 * (prev_legal_moves - curr_legal_moves)` when visible), and a
  small penalty for immediate reverse ghost actions.

- `custom_environment.env.rewards.current:CaptureV0PurePotentialShapingPellets`
  (`strategy_id = capture_v0_pure_potential_shaping_pellets`):
  `capture_v0_pure_potential_shaping` plus an extra shaping penalty
  `pacman_eats_pellet = -0.5 * pellets_eaten_this_step`.

- `custom_environment.env.rewards.current:CaptureV0PurePotentialShapingPelletsFastCaptureBonus`
  (`strategy_id = capture_v0_pure_potential_shaping_pellets_fast_capture_bonus`):
  `capture_v0_pure_potential_shaping_pellets` plus
  `fast_get_pacman_bonus = 20 * (1.0 - steps_elapsed / max_episode_steps)`
  when Pacman is captured, to incentivize faster captures.

- `custom_environment.env.rewards.current:CaptureMergePotentialShaping`
  (`strategy_id = capture_merge_potential_shaping`): merged PBRS +
  coordination terms. Includes terminal outcomes, timestep, potential shaping
  (mean-distance delta), newly spotted/currently visible, recently unvisited,
  reveal unseen local cells, invalid_move/stay_still/reversal/two-step-cycle,
  plus pellet penalty and fast capture bonus. Excludes `valid_move` and
  `overlap_or_same_corridor`.

- `custom_environment.env.rewards.current:CaptureMerge`
  (`strategy_id = capture_merge`): same as
  `capture_merge_potential_shaping`, but with the `potential_shaping` and
  reversal-related reward terms disabled.

- `custom_environment.env.rewards.current:CaptureMerge2`
  (`strategy_id = capture_merge2`): tuned anti-oscillation variant. Keeps
  `potential_shaping` enabled, strengthens `two_step_cycle` and
  `repeated_direction_reversal` penalties, and adds
  `no_progress_visible` after a short grace window when Pacman is visible
  but pursuit does not improve.

- `custom_environment.env.rewards.current:CaptureMerge3`
  (`strategy_id = capture_merge3`): sparse capture objective with only
  `timestep=-0.005`, `GET_PACMAN=+100`,
  `fast_get_pacman_bonus=20*(1-step_count/max_steps)`,
  `PACMAN_TIMEOUT_WIN=-100`, `PACMAN_WIN_PELLETS=-100`,
  `pacman_eats_pellet=-0.5*pellets_eaten`, and
  `invalid_move=-0.05*invalid_moves`.

- `custom_environment.env.rewards.current:CurrentGitTeamReward`
  (`strategy_id = current_git`): git baseline rewards and logic.
- `custom_environment.env.rewards.current:CurrentTeamReward`
  (`strategy_id = current`): locally modified rewards/logic without
  overlap-or-same-corridor penalty.
- `custom_environment.env.rewards.current:CurrentWithOverlapOrSameCorridor`
  (`strategy_id = current_with_overlap_or_same_corridor`): locally modified
  rewards/logic with overlap-or-same-corridor penalty enabled.

Commands in this section provide two collapsible platform options. Windows is
expanded by default and uses the Python launcher `py -3.11`; macOS/Linux uses
`python`. Run all commands from the project root.

#### Understanding `module.path:ClassName`

A reward class is identified with a Python import path in this format:

```text
module.path:ClassName
```

For example:

```text
my_rewards.pursuit:PursuitReward
```

This has two parts:

- `my_rewards.pursuit` is the Python module. From the project root, it normally
  corresponds to the file `my_rewards/pursuit.py`.
- `PursuitReward` is the class defined inside that module.
- The colon (`:`) separates the module from the class.

Given this project structure:

```text
INF2072/
├── my_rewards/
│   ├── __init__.py
│   └── pursuit.py
└── benchmarl_setup/
```

`my_rewards/pursuit.py` could contain:

```python
from custom_environment.env.rewards import (
    RewardResult,
    RewardStrategy,
    RewardTerm,
)


class PursuitReward(RewardStrategy):
    strategy_id = "pursuit"

    def reset(self, initial_context):
        self.previous_distance = self._distance(initial_context)

    def compute(self, context):
        distance = self._distance(context)
        terms = []

        if distance < self.previous_distance:
            terms.append(RewardTerm("move_toward_pacman", 1.0))
        elif distance > self.previous_distance:
            terms.append(RewardTerm("move_away_from_pacman", -1.0))

        if context.capture_happened:
            terms.append(RewardTerm("capture", 20.0, "terminal"))

        self.previous_distance = distance
        return RewardResult(tuple(terms))

    @staticmethod
    def _distance(context):
        pacman_row, pacman_col = context.pacman_position
        return min(
            abs(ghost.current_position[0] - pacman_row)
            + abs(ghost.current_position[1] - pacman_col)
            for ghost in context.ghosts
        )
```

Select it with:

<details open>
<summary><strong>Windows (default)</strong></summary>

```cmd
py -3.11 benchmarl_setup\run_pacman_benchmarl.py --algorithm iql --reward-class my_rewards.pursuit:PursuitReward
```

Or use a built-in reward id alias:

```cmd
py -3.11 benchmarl_setup\run_pacman_benchmarl.py --algorithm iql --reward-id current_with_overlap_or_same_corridor
py -3.11 benchmarl_setup\run_pacman_benchmarl.py --algorithm iql --reward-id capture_v0
py -3.11 benchmarl_setup\run_pacman_benchmarl.py --algorithm iql --reward-id capture_v0_improve_legal_moves_increase_terminal_rewards_reverse_action
py -3.11 benchmarl_setup\run_pacman_benchmarl.py --algorithm iql --reward-id capture_v0_pure_potential_shaping_pellets
py -3.11 benchmarl_setup\run_pacman_benchmarl.py --algorithm iql --reward-id capture_v0_pure_potential_shaping_pellets_fast_capture_bonus
py -3.11 benchmarl_setup\run_pacman_benchmarl.py --algorithm iql --reward-id capture_merge
py -3.11 benchmarl_setup\run_pacman_benchmarl.py --algorithm iql --reward-id capture_merge2
py -3.11 benchmarl_setup\run_pacman_benchmarl.py --algorithm iql --reward-id capture_merge3
py -3.11 benchmarl_setup\run_pacman_benchmarl.py --algorithm iql --reward-id capture_merge_potential_shaping
```

</details>

<details>
<summary><strong>macOS/Linux</strong></summary>

```bash
python benchmarl_setup/run_pacman_benchmarl.py \
  --algorithm iql \
  --reward-class my_rewards.pursuit:PursuitReward
```

Or use a built-in reward id alias:

```bash
python benchmarl_setup/run_pacman_benchmarl.py \
  --algorithm iql \
  --reward-id current_with_overlap_or_same_corridor
python benchmarl_setup/run_pacman_benchmarl.py \
  --algorithm iql \
  --reward-id capture_v0
python benchmarl_setup/run_pacman_benchmarl.py \
  --algorithm iql \
  --reward-id capture_v0_improve_legal_moves_increase_terminal_rewards_reverse_action
python benchmarl_setup/run_pacman_benchmarl.py \
  --algorithm iql \
  --reward-id capture_v0_pure_potential_shaping_pellets
python benchmarl_setup/run_pacman_benchmarl.py \
  --algorithm iql \
  --reward-id capture_v0_pure_potential_shaping_pellets_fast_capture_bonus
python benchmarl_setup/run_pacman_benchmarl.py \
  --algorithm iql \
  --reward-id capture_merge
python benchmarl_setup/run_pacman_benchmarl.py \
  --algorithm iql \
  --reward-id capture_merge2
python benchmarl_setup/run_pacman_benchmarl.py \
  --algorithm iql \
  --reward-id capture_merge3
python benchmarl_setup/run_pacman_benchmarl.py \
  --algorithm iql \
  --reward-id capture_merge_potential_shaping
```

</details>

If the file is directly in the project root as `pursuit_reward.py`, use:

```text
pursuit_reward:PursuitReward
```

Do not use a filesystem path such as `my_rewards/pursuit.py:PursuitReward`.
Use Python dots, omit the `.py` suffix, and run the command from the project root
so the module is importable.

Every CLI-loaded reward class must:

- subclass `RewardStrategy`;
- define a unique lowercase `strategy_id`, such as `pursuit-v2`;
- be constructible without arguments; and
- implement `reset(initial_context)` and `compute(context)`.

You can verify an import path without starting training:

<details open>
<summary><strong>Windows (default)</strong></summary>

```cmd
py -3.11 -c "from custom_environment.env.rewards import load_reward_strategy; print(load_reward_strategy('my_rewards.pursuit:PursuitReward').strategy_id)"
```

</details>

<details>
<summary><strong>macOS/Linux</strong></summary>

```bash
python -c "from custom_environment.env.rewards import load_reward_strategy; print(load_reward_strategy('my_rewards.pursuit:PursuitReward').strategy_id)"
```

</details>

The expected output for the example above is `pursuit`.

Paired multi-seed comparison:

<details open>
<summary><strong>Windows (default)</strong></summary>

```cmd
py -3.11 benchmarl_setup\run_benchmark.py --algorithms iql,vdn --seeds 0,1,2 --reward-classes team_a.rewards:RewardA,team_b.rewards:RewardB
```

Built-in reward ids can also be passed directly:

```cmd
py -3.11 benchmarl_setup\run_benchmark.py --algorithms iql,vdn --seeds 0,1,2 --reward-ids current,current_with_overlap_or_same_corridor
py -3.11 benchmarl_setup\run_benchmark.py --algorithms iql --seeds 0,1,2 --reward-ids current_git,capture_v0
py -3.11 benchmarl_setup\run_benchmark.py --algorithms iql --seeds 0,1,2 --reward-ids capture_v0,capture_v0_improve_legal_moves_increase_terminal_rewards_reverse_action
py -3.11 benchmarl_setup\run_benchmark.py --algorithms iql --seeds 0,1,2 --reward-ids capture_v0_pure_potential_shaping,capture_v0_pure_potential_shaping_pellets
py -3.11 benchmarl_setup\run_benchmark.py --algorithms iql --seeds 0,1,2 --reward-ids capture_v0_pure_potential_shaping_pellets,capture_v0_pure_potential_shaping_pellets_fast_capture_bonus
```

</details>

<details>
<summary><strong>macOS/Linux</strong></summary>

```bash
python benchmarl_setup/run_benchmark.py \
  --algorithms iql,vdn \
  --seeds 0,1,2 \
  --reward-classes team_a.rewards:RewardA,team_b.rewards:RewardB
```

Built-in reward ids can also be passed directly:

```bash
python benchmarl_setup/run_benchmark.py \
  --algorithms iql,vdn \
  --seeds 0,1,2 \
  --reward-ids current,current_with_overlap_or_same_corridor
python benchmarl_setup/run_benchmark.py \
  --algorithms iql \
  --seeds 0,1,2 \
  --reward-ids current_git,capture_v0
python benchmarl_setup/run_benchmark.py \
  --algorithms iql \
  --seeds 0,1,2 \
  --reward-ids capture_v0,capture_v0_improve_legal_moves_increase_terminal_rewards_reverse_action
python benchmarl_setup/run_benchmark.py \
  --algorithms iql \
  --seeds 0,1,2 \
  --reward-ids capture_v0_pure_potential_shaping,capture_v0_pure_potential_shaping_pellets
python benchmarl_setup/run_benchmark.py \
  --algorithms iql \
  --seeds 0,1,2 \
  --reward-ids capture_v0_pure_potential_shaping_pellets,capture_v0_pure_potential_shaping_pellets_fast_capture_bonus
```

</details>

Runs are isolated under `<runs>/<maze>/<strategy_id>/<device>/`. Post-training
objective evaluation is opt-in: pass a positive value such as `--eval-episodes 100`
to evaluate every final checkpoint on the same episode seeds and write
capture-rate/time-to-capture comparisons. Raw returns remain diagnostic only because
reward scales are not comparable between strategies.

Objective evaluation is a post-training phase: it loads each final checkpoint and
runs additional episodes to measure behavior such as capture rate and
time-to-capture. It does not update the policy or change the completed training run.
By default, `--eval-episodes 0` disables this phase. Set `--eval-episodes N` to a
positive number to evaluate every checkpoint for `N` episodes after training.
This is useful when reward variants are trained in separate commands: the baseline
and variant commands below keep evaluation disabled, then a
single `eval_report.py` command evaluates both sets of checkpoints together using
the same episode seeds. That final paired evaluation is both fairer and avoids
duplicated work.

#### Regression-check the refactor against `main`

The repository includes a small deterministic A/B experiment. Both runs use IQL,
seed `17`, CPU, and `4,000` frames. The only command difference is that the refactored
run explicitly selects `CurrentTeamReward`; old `main` uses its built-in reward.

1. From the project root on the refactor branch, using the project's Python 3.11
   environment, run:

   <details open>
   <summary><strong>Windows (default)</strong></summary>

   ```cmd
   py -3.11 scripts\run_refactored_reward_regression.py
   ```

   </details>

   <details>
   <summary><strong>macOS/Linux</strong></summary>

   ```bash
   python scripts/run_refactored_reward_regression.py
   ```

   </details>

   Results are written outside the repository under the system temporary directory,
   in `inf2072_reward_regression/refactored`. The script also copies the baseline
   runner and comparator there so they survive a branch switch.

2. Commit the refactor, make sure the worktree is clean, and switch to unmodified
   `main`:

   ```bash
   git switch main
   ```

3. Run the exact baseline command printed by step 1. Typical paths are:

   <details open>
   <summary><strong>Windows (default)</strong></summary>

   ```cmd
   py -3.11 "%TEMP%\inf2072_reward_regression\tools\run_main_reward_regression.py"
   ```

   </details>

   <details>
   <summary><strong>macOS/Linux</strong></summary>

   ```bash
   python /tmp/inf2072_reward_regression/tools/run_main_reward_regression.py
   ```

   </details>

   Use the printed path rather than copying this example; Windows uses its own
   temporary-directory path. The baseline script refuses to run unless the current
   branch is `main` and the worktree is clean.

4. Run the comparator command printed by the baseline script:

   <details open>
   <summary><strong>Windows (default)</strong></summary>

   ```cmd
   py -3.11 "%TEMP%\inf2072_reward_regression\tools\compare_reward_regression.py"
   ```

   </details>

   <details>
   <summary><strong>macOS/Linux</strong></summary>

   ```bash
   python /tmp/inf2072_reward_regression/tools/compare_reward_regression.py
   ```

   </details>

The comparator checks every common non-timing BenchMARL scalar series, including
step rewards, episode returns, loss, gradient norm, and frame counters. `SAME` means
the maximum absolute difference is at most `1e-8`; timing metrics are intentionally
ignored. If repeating the experiment, remove or rename the prior temporary output
first—the runners refuse to mix multiple runs in one comparison directory.

#### Compare the default reward with a one-weight variant

`StrongerMovementReward` is an example experimental strategy. It inherits the full
current reward and changes only `valid_move`, from `0.01` to `0.10`. Its import path is:

```text
my_rewards.movement_bonus:StrongerMovementReward
```

First train the current reward baseline:

<details open>
<summary><strong>Windows (default)</strong></summary>

```cmd
py -3.11 benchmarl_setup\run_benchmark.py --algorithms iql --reward-classes custom_environment.env.rewards.current:CurrentTeamReward --seeds 0,1,2 --max-frames 60000 --maze default --devices cpu --save-folder benchmarl_setup\runs\reward_weight_study --jobs-out benchmarl_setup\runs\reward_weight_study\current_jobs.csv --summary-out benchmarl_setup\runs\reward_weight_study\current_training_summary.csv --eval-episodes 0 --no-liveplot-report
```

</details>

<details>
<summary><strong>macOS/Linux</strong></summary>

```bash
python benchmarl_setup/run_benchmark.py \
  --algorithms iql \
  --reward-classes custom_environment.env.rewards.current:CurrentTeamReward \
  --seeds 0,1,2 \
  --max-frames 60000 \
  --maze default \
  --devices cpu \
  --save-folder benchmarl_setup/runs/reward_weight_study \
  --jobs-out benchmarl_setup/runs/reward_weight_study/current_jobs.csv \
  --summary-out benchmarl_setup/runs/reward_weight_study/current_training_summary.csv \
  --eval-episodes 0 \
  --no-liveplot-report
```

</details>

Then train the one-weight variant with the same algorithms, seeds, frame budget,
maze, and device:

<details open>
<summary><strong>Windows (default)</strong></summary>

```cmd
py -3.11 benchmarl_setup\run_benchmark.py --algorithms iql --reward-classes my_rewards.movement_bonus:StrongerMovementReward --seeds 0,1,2 --max-frames 60000 --maze default --devices cpu --save-folder benchmarl_setup\runs\reward_weight_study --jobs-out benchmarl_setup\runs\reward_weight_study\valid_move_010_jobs.csv --summary-out benchmarl_setup\runs\reward_weight_study\valid_move_010_training_summary.csv --eval-episodes 0 --no-liveplot-report
```

</details>

<details>
<summary><strong>macOS/Linux</strong></summary>

```bash
python benchmarl_setup/run_benchmark.py \
  --algorithms iql \
  --reward-classes my_rewards.movement_bonus:StrongerMovementReward \
  --seeds 0,1,2 \
  --max-frames 60000 \
  --maze default \
  --devices cpu \
  --save-folder benchmarl_setup/runs/reward_weight_study \
  --jobs-out benchmarl_setup/runs/reward_weight_study/valid_move_010_jobs.csv \
  --summary-out benchmarl_setup/runs/reward_weight_study/valid_move_010_training_summary.csv \
  --eval-episodes 0 \
  --no-liveplot-report
```

</details>

Finally, evaluate the already-trained checkpoints together on the same 100 episode
seeds:

Note: `custom_environment/eval_report.py` only uses benchmark jobs mode when
`--jobs-path` is provided. If omitted, it evaluates checkpoints via direct
run-folder discovery (for the selected reward/algorithms/device-label).

<details open>
<summary><strong>Windows (default)</strong></summary>

```cmd
py -3.11 custom_environment\eval_report.py --jobs-path benchmarl_setup\runs\reward_weight_study\current_jobs.csv benchmarl_setup\runs\reward_weight_study\valid_move_010_jobs.csv --episodes 100 --eval-seed-base 10000 --device cpu --out benchmarl_setup\runs\reward_weight_study\reward_comparison.csv
```

</details>

<details>
<summary><strong>macOS/Linux</strong></summary>

```bash
python custom_environment/eval_report.py \
  --jobs-path \
    benchmarl_setup/runs/reward_weight_study/current_jobs.csv \
    benchmarl_setup/runs/reward_weight_study/valid_move_010_jobs.csv \
  --episodes 100 \
  --eval-seed-base 10000 \
  --device cpu \
  --out benchmarl_setup/runs/reward_weight_study/reward_comparison.csv
```

</details>

Use `reward_comparison_by_variant.csv` for the final comparison. Capture-rate mean
and time-to-capture mean are the decision metrics; raw return values are diagnostic
only because changing a reward weight also changes the return scale. For a quicker
smoke experiment, replace `--max-frames 60000` with `--max-frames 10000` in both
training commands.

### Python Environment

This project requires **Python 3.11**. Ensure you are using the correct version by running:

```bash
python --version
```

If you do not have Python 3.11 installed, download and install it from the [official Python website](https://www.python.org/downloads/).

#### Setting Up the Virtual Environment

1. Create a virtual environment using Python 3.11:
   ```bash
   py -3.11 -m venv venv
   ```

2. Activate the virtual environment:
   - On Windows (Command Prompt):
     ```bash
     venv\Scripts\activate
     ```
   - On Windows (PowerShell):
     ```bash
     .\venv\Scripts\Activate.ps1
     ```

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. **(Optional) Set the `PYTHONPATH`**:
   - On Windows (Command Prompt):
     ```cmd
     set PYTHONPATH=.
     ```
   - On Windows (PowerShell):
     ```powershell
     $env:PYTHONPATH="."
     ```

   This is optional for `benchmarl_setup\\register_pacman_env.py` and `benchmarl_setup\\run_pacman_benchmarl.py` because both scripts add the project root to `sys.path` automatically.

5. **Run the Compatibility Script**:
   ```bash
   py -3.11 benchmarl_setup\register_pacman_env.py
   ```
