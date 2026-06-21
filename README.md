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
1200` for quick smoke runs). For `--algorithm iql` the runner also applies
convergence-oriented hyperparameters with no CLI flag of their own (a longer
epsilon anneal `1.0 → 0.05` over 80% of the budget, `lr 1e-4`, `gamma 0.99`);
VDN/QMIX keep BenchMARL's stock schedule.

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

The Pygame renderer highlights each ghost's current local observation (5x5 by default) with
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
```

Evaluation also supports explicit device selection:

```bash
py -3.11 custom_environment\eval.py --learner iql --maze pinklike --device auto
py -3.11 custom_environment\eval.py --learner qmixglobal --maze pinklike --device cuda --no-allow-cpu-fallback --checkpoint-select best
```

Use `--checkpoint-select latest` to force newest-run behavior, or `--checkpoint` to provide an explicit `.pt` file.

Useful optional parameters for training (`benchmarl_setup\run_pacman_benchmarl.py`):

```bash
--max-frames 5000 --frames-per-batch 200 --optimizer-steps 10 --train-batch-size 128 --memory-size 10000
--init-random-frames 1000
--ghost-view-size 3|5|7
--device cpu|cuda|cuda:0|auto --allow-cpu-fallback
```

Useful optional parameters for evaluation (`custom_environment\eval.py`):

```bash
--delay 0.25 --max-steps 200 --maze default --checkpoint-select best --show-reward-breakdown
--render-mode ascii|human|rgb_array --tile-size 28 --fps 12 --screenshot-out path\to\frame.png
--hide-observations --device cpu|cuda|cuda:0|auto --allow-cpu-fallback
--ghost-view-size 3|5|7
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
```

When benchmark runs are stored under device subfolders (for example `runs/<maze>/cpu` and `runs/<maze>/cuda`), set `--device-label` explicitly or leave it as `auto`:

```bash
py -3.11 custom_environment\eval_report.py --maze pinklike --algorithms iql,vdn,qmixglobal --device-label cuda --checkpoint-select best --episodes 30
py -3.11 custom_environment\eval_report.py --maze pinklike --algorithms iql,vdn,qmixglobal --device-label auto --checkpoint-select best --episodes 30
```

This writes `benchmarl_setup/runs/<maze>/evaluation_report.csv` and prints, per learner:

- `ghost_win_rate`
- `pacman_win_rate`
- `mean_episode_return`
- `std_episode_return`
- `median_episode_return`
- `mean_steps`

Useful options for deterministic report evaluation (`custom_environment\eval_report.py`):

```bash
--episodes 30 --max-steps 200 --seed-base 0 --out benchmarl_setup\runs\pinklike\evaluation_report_best.csv
--learner qmixglobal --checkpoint-select latest
--learner qmixglobal --checkpoint path\to\checkpoint.pt
--device-label auto|cpu|cuda|cuda_0
--ghost-view-size 3|5|7 --verbose
```

Use this report to compare final policy quality across algorithms under deterministic action selection (evaluation-time), instead of relying only on training scalar curves.

Useful optional rendering parameters for the random-policy demo
(`custom_environment\render_demo.py`):

```bash
--render-mode ascii|human|rgb_array --max-steps 200 --delay 0.0 --tile-size 28 --fps 12
--grid-size 20 --number-ghosts 2 --seed 0 --screenshot-out path\to\frame.png --hide-observations
```

Outputs are saved under `benchmarl_setup/runs/<maze>` by default.

### Mazes (Map Selection)

Two maze layouts are available via `--maze`:

- `default`: a 20x20 lattice maze.
- `pinklike`: a 20x20 maze resembling the classic "Pink" Pacman maze, without portals.

**Layout notation (map-authored spawns + pellets).** Mazes are defined as ASCII layouts in
`custom_environment/utils.py` (`DEFAULT_LAYOUT`, `PINKLIKE_LAYOUT`) and parsed by `parse_layout`
into a `MazeSpec` (grid + spawns + cosmetic pellet mask). The map itself declares where every
entity starts, so there are no hardcoded spawn positions. Characters:

- `%` or `#` — wall
- `.` — pellet (cosmetic only);  `o` — power pellet (treated as a pellet for now)
- `G` — ghost spawn (the number of ghosts equals the number of `G`s)
- `P` — Pac-Man spawn (exactly one)
- space (or any other char) — empty, no pellet

`parse_layout` validates a single `P`, at least one `G`, a solid border, and full connectivity
(`assert_connected`). Pellets are **cosmetic** — they do not affect observations, reward, or
termination. To add a maze, define a new layout list + register it in the `MAZES` dict.

The selected maze is supported by training, benchmarking, and the render demo:

```bash
py -3.11 benchmarl_setup\run_pacman_benchmarl.py --algorithm iql --maze pinklike
py -3.11 benchmarl_setup\run_benchmark.py --algorithms iql,vdn --seeds 0,1,2 --maze pinklike
py -3.11 custom_environment\render_demo.py --render-mode human --maze pinklike
```

Use the same `--maze` at evaluation/plot time so the command reads from the matching
subfolder.

**Keeping the two mazes' runs separate.** Runs are now separated automatically under
`benchmarl_setup/runs/<maze>`. Use `--maze` consistently across training, evaluation, and plotting:

```bash
py -3.11 benchmarl_setup\run_benchmark.py --algorithms iql,vdn --maze default
py -3.11 benchmarl_setup\run_benchmark.py --algorithms iql,vdn --maze pinklike

py -3.11 custom_environment\eval.py --learner iql --maze pinklike
py -3.11 benchmarl_setup\plot_benchmarl_reward.py --algorithms iql,vdn --maze pinklike
```

New mazes can be registered in `custom_environment/utils.py` via the `MAZES` registry
(`grid_from_ascii` parses an ASCII layout; `assert_connected` validates reachability).

### Benchmark (Multi-Seed, Parallel by Algorithm)

You can now run a full benchmark with one command using:

- `benchmarl_setup/run_benchmark.py`

Example (5 seeds, shared training config):

```bash
py -3.11 benchmarl_setup\run_benchmark.py --algorithms iql,vdn,qmixlocal,qmixglobal --seeds 0,1,2,3,4 --max-frames 50000
```

Benchmark now supports device sweeps in one command:

```bash
py -3.11 benchmarl_setup\run_benchmark.py --algorithms iql,vdn,qmixlocal,qmixglobal --seeds 0,1,2,3,4 --devices cpu,cuda --max-frames 50000
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
--algorithms iql,vdn,qmixlocal,qmixglobal --frames-per-batch 200 --optimizer-steps 10 --train-batch-size 128 --memory-size 10000 --init-random-frames 1000
--ghost-view-size 3|5|7
--devices cpu,cuda --allow-cpu-fallback --jobs-out benchmarl_setup\runs\default\benchmark_jobs.csv
```

This command now trains and then automatically writes a benchmark summary CSV.

It also writes a per-job timing ledger (`benchmark_jobs.csv`) with wall-clock duration and run mapping.

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
- `--jobs-path` merges timing metrics (`duration_seconds`, `frames_per_second`) when a benchmark jobs ledger is available.
- The printed aggregate is grouped by `algorithm + device`.

### CPU vs GPU Benchmark Protocol

Use this protocol for fair comparisons:

1. Keep configuration identical across devices (`--max-frames`, `--frames-per-batch`, `--optimizer-steps`, `--train-batch-size`, seeds).
2. Run a shared benchmark command with both devices:

```bash
py -3.11 benchmarl_setup\run_benchmark.py --algorithms iql,vdn,qmixlocal,qmixglobal --seeds 0,1,2,3,4 --devices cpu,cuda --max-frames 50000 --summary-out benchmarl_setup\runs\default\benchmark_summary_cpu_gpu.csv
```

3. Compare `duration_seconds` and `frames_per_second` by `algorithm` + `device` in the summary CSV.
4. If CUDA is unavailable, either install CUDA-enabled PyTorch/NVIDIA drivers or keep `--allow-cpu-fallback` enabled and inspect the resolved device logs.
5. For strict CPU-vs-GPU comparisons, prefer `--no-allow-cpu-fallback` so unavailable CUDA fails immediately.

### Live Plot During Training

Training now reports live progress to:

- `benchmarl_setup/runs/<maze>/live_progress.csvl`

Use `benchmarl_setup/liveplot.py` in a separate terminal to monitor running benchmarks with mean ± std curves per algorithm.
By default (`--device all`), it can display one line per algorithm-device pair (for example `IQL@cpu`, `IQL@cuda`).

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
```

Useful options:

```bash
py -3.11 benchmarl_setup\liveplot.py --interval 1.0 --window 30
py -3.11 benchmarl_setup\liveplot.py --maze pinklike --device all --interval 1.0 --window 30
py -3.11 benchmarl_setup\run_benchmark.py --maze pinklike --live-progress-file benchmarl_setup\runs\pinklike\live_progress.csvl --report-interval-seconds 1.0
```

### Plot Benchmark Reward in One Figure (IQL, VDN, QMIX Local, QMIX Global)

Use:

- `benchmarl_setup/plot_benchmarl_reward.py`

This script can aggregate runs from multiple algorithms and plot all of them in the same figure:

- Mean reward curve per algorithm
- Standard deviation band per algorithm

Examples:

```bash
py -3.11 benchmarl_setup\plot_benchmarl_reward.py --algorithms iql,vdn --show-runs
py -3.11 benchmarl_setup\plot_benchmarl_reward.py --algorithms iql,vdn,qmixlocal,qmixglobal --show-runs
```

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

Optional parameters:

```bash
--maze pinklike --window 30 --out benchmarl_setup\runs\pinklike\benchmark_iql_vdn.png --no-open
```

If no `--out` is provided, the default output is:

- `benchmarl_setup/runs/<maze>/benchmark_reward_multiseed_mean_std.png` (when plotting multiple algorithms)
- `benchmarl_setup/runs/<maze>/<algorithm>_reward_multiseed_mean_std.png` (when plotting one algorithm)

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

```bash
python benchmarl_setup/run_pacman_benchmarl.py \
  --algorithm iql \
  --reward-class my_rewards.pursuit:PursuitReward
```

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

```bash
python -c "from custom_environment.env.rewards import load_reward_strategy; print(load_reward_strategy('my_rewards.pursuit:PursuitReward').strategy_id)"
```

The expected output for the example above is `pursuit`.

Paired multi-seed comparison:

```bash
python benchmarl_setup/run_benchmark.py \
  --algorithms iql,vdn \
  --seeds 0,1,2 \
  --reward-classes team_a.rewards:RewardA,team_b.rewards:RewardB
```

Runs are isolated under `<runs>/<maze>/<strategy_id>/<device>/`. After training,
the benchmark evaluates every final checkpoint on the same episode seeds and writes
capture-rate/time-to-capture comparisons. Raw returns remain diagnostic only because
reward scales are not comparable between strategies. Use `--eval-episodes 0` to skip
the automatic objective evaluation.

#### Regression-check the refactor against `main`

The repository includes a small deterministic A/B experiment. Both runs use IQL,
seed `17`, CPU, and `4,000` frames. The only command difference is that the refactored
run explicitly selects `CurrentTeamReward`; old `main` uses its built-in reward.

1. From the project root on the refactor branch, using the project's Python 3.11
   environment, run:

   ```bash
   python scripts/run_refactored_reward_regression.py
   ```

   Results are written outside the repository under the system temporary directory,
   in `inf2072_reward_regression/refactored`. The script also copies the baseline
   runner and comparator there so they survive a branch switch.

2. Commit the refactor, make sure the worktree is clean, and switch to unmodified
   `main`:

   ```bash
   git switch main
   ```

3. Run the exact baseline command printed by step 1. On macOS/Linux it normally
   looks like:

   ```bash
   python /tmp/inf2072_reward_regression/tools/run_main_reward_regression.py
   ```

   Use the printed path rather than copying this example; Windows uses its own
   temporary-directory path. The baseline script refuses to run unless the current
   branch is `main` and the worktree is clean.

4. Run the comparator command printed by the baseline script. It normally looks like:

   ```bash
   python /tmp/inf2072_reward_regression/tools/compare_reward_regression.py
   ```

The comparator checks every common non-timing BenchMARL scalar series, including
step rewards, episode returns, loss, gradient norm, and frame counters. `SAME` means
the maximum absolute difference is at most `1e-8`; timing metrics are intentionally
ignored. If repeating the experiment, remove or rename the prior temporary output
first—the runners refuse to mix multiple runs in one comparison directory.

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
