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
py -3.11 custom_environment\render_demo.py --render-mode rgb_array --max-steps 3 --screenshot-out benchmarl_setup\runs\pacman_render.png
```

`custom_environment/eval.py` loads the latest checkpoint for the selected learner from `benchmarl_setup/runs`.
It now supports futebol2d-style best-run selection across multiple runs:

```bash
py -3.11 custom_environment\eval.py --learner iql --checkpoint-select best
```

Evaluation also supports explicit device selection:

```bash
py -3.11 custom_environment\eval.py --learner iql --device auto
py -3.11 custom_environment\eval.py --learner qmixglobal --device cuda --no-allow-cpu-fallback
```

Use `--checkpoint-select latest` to force newest-run behavior, or `--checkpoint` to provide an explicit `.pt` file.

Useful optional parameters for training (`benchmarl_setup\run_pacman_benchmarl.py`):

```bash
--max-frames 5000 --frames-per-batch 200 --optimizer-steps 10 --train-batch-size 128 --memory-size 10000
--init-random-frames 1000
--device cpu|cuda|cuda:0|auto --allow-cpu-fallback
```

Useful optional parameters for evaluation (`custom_environment\eval.py`):

```bash
--delay 0.25 --max-steps 200 --checkpoint-select best --show-reward-breakdown
--render-mode ascii|human|rgb_array --tile-size 28 --fps 12 --screenshot-out path\to\frame.png
--hide-observations --device cpu|cuda|cuda:0|auto --allow-cpu-fallback
```

You can also pass an explicit checkpoint to eval:

```bash
--checkpoint path\to\checkpoint_5000.pt
```

Useful optional rendering parameters for the random-policy demo
(`custom_environment\render_demo.py`):

```bash
--render-mode ascii|human|rgb_array --max-steps 200 --delay 0.0 --tile-size 28 --fps 12
--grid-size 20 --number-ghosts 2 --seed 0 --screenshot-out path\to\frame.png --hide-observations
```

Outputs are saved under `benchmarl_setup/runs` by default.

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

The maze is recorded in each run's task config, so `eval.py` rebuilds the correct maze
automatically from the checkpoint (no `--maze` needed for evaluation).

**Keeping the two mazes' runs separate.** Both mazes write run folders with the same
`<algorithm>_pacman_*` prefix, so train each maze into its own output folder and read it
back with `--runs-root` during evaluation/plotting:

```bash
py -3.11 benchmarl_setup\run_benchmark.py --algorithms iql,vdn --maze default   --save-folder benchmarl_setup\runs\default
py -3.11 benchmarl_setup\run_benchmark.py --algorithms iql,vdn --maze pinklike  --save-folder benchmarl_setup\runs\pinklike

py -3.11 custom_environment\eval.py --learner iql --runs-root benchmarl_setup\runs\pinklike
py -3.11 benchmarl_setup\plot_benchmarl_reward.py --algorithms iql,vdn --runs-root benchmarl_setup\runs\pinklike
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

- `benchmarl_setup/runs/cpu`
- `benchmarl_setup/runs/cuda`

Execution strategy:

- Algorithms run in parallel (for example IQL and VDN at the same time).
- Seeds run serially inside each algorithm worker.

Useful optional parameters:

```bash
--algorithms iql,vdn,qmixlocal,qmixglobal --frames-per-batch 200 --optimizer-steps 10 --train-batch-size 128 --memory-size 10000 --init-random-frames 1000
--devices cpu,cuda --allow-cpu-fallback --jobs-out benchmarl_setup\runs\benchmark_jobs.csv
```

This command now trains and then automatically writes a benchmark summary CSV.

It also writes a per-job timing ledger (`benchmark_jobs.csv`) with wall-clock duration and run mapping.

The summary CSV includes, per run:

- `device`
- `algorithm`
- `seed`
- `run_dir`
- `n_points`
- `final_reward`
- `tail_mean_reward`
- `best_reward`
- `duration_seconds`
- `frames_per_second`
- `checkpoint_path`

### CPU vs GPU Benchmark Protocol

Use this protocol for fair comparisons:

1. Keep configuration identical across devices (`--max-frames`, `--frames-per-batch`, `--optimizer-steps`, `--train-batch-size`, seeds).
2. Run a shared benchmark command with both devices:

```bash
py -3.11 benchmarl_setup\run_benchmark.py --algorithms iql,vdn,qmixlocal,qmixglobal --seeds 0,1,2,3,4 --devices cpu,cuda --max-frames 50000 --summary-out benchmarl_setup\runs\benchmark_summary_cpu_gpu.csv
```

3. Compare `duration_seconds` and `frames_per_second` by `algorithm` + `device` in the summary CSV.
4. If CUDA is unavailable, either install CUDA-enabled PyTorch/NVIDIA drivers or keep `--allow-cpu-fallback` enabled and inspect the resolved device logs.
5. For strict CPU-vs-GPU comparisons, prefer `--no-allow-cpu-fallback` so unavailable CUDA fails immediately.

### Live Plot During Training

Training now reports live progress to:

- `benchmarl_setup/runs/live_progress.csvl`

Use `benchmarl_setup/liveplot.py` in a separate terminal to monitor running benchmarks with mean ± std curves per algorithm.

Start live monitor:

```bash
py -3.11 benchmarl_setup\liveplot.py --algorithms iql,vdn,qmixlocal,qmixglobal
```

Then run benchmark normally:

```bash
py -3.11 benchmarl_setup\run_benchmark.py --algorithms iql,vdn,qmixlocal,qmixglobal --seeds 0,1,2,3,4
```

Useful options:

```bash
py -3.11 benchmarl_setup\liveplot.py --interval 1.0 --window 3
py -3.11 benchmarl_setup\run_benchmark.py --live-progress-file benchmarl_setup\runs\live_progress.csvl --report-interval-seconds 1.0
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
py -3.11 benchmarl_setup\plot_cpu_gpu_summary.py --summary-csv benchmarl_setup\runs\benchmark_summary.csv --reward-metric tail_mean_reward --out benchmarl_setup\runs\cpu_gpu_summary_comparison.png
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
--window 5 --out benchmarl_setup\runs\benchmark_iql_vdn.png --no-open
```

If no `--out` is provided, the default output is:

- `benchmarl_setup/runs/benchmark_reward_multiseed_mean_std.png` (when plotting multiple algorithms)
- `benchmarl_setup/runs/<algorithm>_reward_multiseed_mean_std.png` (when plotting one algorithm)

### Plot de Reward IQL (Passo a Passo)

Use o script `benchmarl_setup/plot_iql_reward.py` para gerar um gráfico da média de recompensa com banda de desvio padrão rolante.

1. Execute pelo menos um treino de IQL para gerar logs em `benchmarl_setup/runs`.

2. Gere o plot da execução IQL mais recente:

```bash
py -3.11 benchmarl_setup\plot_iql_reward.py
```

3. Abra o arquivo de saída padrão:

```text
benchmarl_setup/runs/iql_reward_mean_stddev.png
```

4. (Opcional) Escolha uma run específica com `--run-dir`:

```bash
py -3.11 benchmarl_setup\plot_iql_reward.py --run-dir "benchmarl_setup\runs\iql_pacman_mlp__SEU_RUN_ID"
```

5. (Opcional) Ajuste a janela do desvio padrão rolante:

```bash
py -3.11 benchmarl_setup\plot_iql_reward.py --window 10
```

6. (Opcional) Defina um caminho de saída customizado:

```bash
py -3.11 benchmarl_setup\plot_iql_reward.py --out "benchmarl_setup\runs\meu_plot_iql.png"
```

Parâmetros principais do script:

- `--runs-root`: pasta raiz das runs (padrão: `benchmarl_setup/runs`)
- `--run-dir`: run específica (se omitido, usa a IQL mais recente)
- `--window`: janela para cálculo do desvio padrão rolante (padrão: `5`)
- `--out`: caminho do PNG de saída

### Pacman Reward System (Current)

The environment now uses a **shared team reward**: one scalar reward is computed per step and broadcast to all ghosts.

Observability and shared information rules:
1. Each ghost only observes its local neighborhood (5x5 by default).
   - **Changing the view size:** edit the single constant `GHOST_VIEW_SIZE` in
     `custom_environment/env/pacman_environment.py` (any odd integer: `3`→3x3, `5`→5x5, `7`→7x7).
     It applies to every algorithm/training; off-grid cells near the border are padded with walls,
     so the maze needs no changes. Note that resizing changes the policy input shape, so existing
     checkpoints must be retrained.
2. Team-level visibility is computed from local observations only (logical OR across ghosts).
3. The only shared memory about Pacman location is:
   - `last_pacman_sighting_position`
   - `last_pacman_sighting_step`
4. If any ghost sees Pacman, last sighting is updated.
5. If no ghost sees Pacman, last sighting remains unchanged.

Default episode parameters:
1. `max_steps = 200` (timeout)
2. `recently_unvisited_window = 10`

Reward terms:
1. `+20.0` if Pacman is captured
2. `-20.0` if Pacman wins by timeout
3. `+1.0` if Pacman is newly spotted (visibility false -> true)
4. `+0.3` if Pacman target distance decreases (minimum over ghosts)
5. `-0.3` if Pacman target distance increases (minimum over ghosts)
6. `+0.2` if Pacman is currently visible to any ghost
7. `+0.08` if a ghost enters a recently-unvisited tile
8. `+0.05` if a ghost reveals previously unseen local cells
9. `+0.01` if a ghost performs a valid move
10. `-0.08` if a ghost attempts an invalid move (blocked by wall/occupied cell)
11. `-0.03` if a ghost stays still (without invalid-move attempt)
12. `-0.02` if a ghost repeatedly reverses direction (movement loop)
13. `-0.05` if ghosts overlap or follow the same corridor closely
14. `-0.01` timestep penalty

Anti-exploit guards:
1. `newly_spotted` is only awarded if Pacman was unseen for at least `6` consecutive steps before becoming visible again.
2. Reversal penalty scales with repetition streak (stronger punishment for persistent ping-pong loops).

Distance-target rule:
1. If Pacman is visible now, distance shaping uses current visible Pacman position.
2. If Pacman is not visible, distance shaping uses `last_pacman_sighting_position`.
3. If no sighting exists yet, distance shaping is skipped.

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
