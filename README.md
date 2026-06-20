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

Algorithm variants:

- `qmixlocal`: uses per-agent Q-values for mixing without centralized global state.
- `qmixglobal`: canonical QMIX variant that uses per-agent Q-values plus centralized global state for the mixer.

**IQL tuning (plan-000008).** The default training budget is now `--max-frames
60000` (a convergence-scale value; pass a smaller number such as `--max-frames
1200` for quick smoke runs). For `--algorithm iql` the runner also applies
convergence-oriented hyperparameters with no CLI flag of their own (a longer
epsilon anneal `1.0 → 0.05` over 80% of the budget, `lr 1e-4`, `gamma 0.99`);
VDN/QMIX keep BenchMARL's stock schedule. After training, confirm the ghosts win
with the [Win-Rate Evaluation](#win-rate-evaluation-does-iql-actually-win) harness.

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

Use `--checkpoint-select latest` to force newest-run behavior, or `--checkpoint` to provide an explicit `.pt` file.

Useful optional parameters for training (`benchmarl_setup\run_pacman_benchmarl.py`):

```bash
--max-frames 5000 --frames-per-batch 200 --optimizer-steps 10 --train-batch-size 128 --memory-size 10000
--init-random-frames 1000
```

Useful optional parameters for evaluation (`custom_environment\eval.py`):

```bash
--delay 0.25 --max-steps 200 --checkpoint-select best --show-reward-breakdown
--render-mode ascii|human|rgb_array --tile-size 28 --fps 12 --screenshot-out path\to\frame.png
--hide-observations
--episodes 50 --eval-epsilon 0.05 --win-rate-out path\to\iql_win_rate.csv --seed 0
```

You can also pass an explicit checkpoint to eval:

```bash
--checkpoint path\to\checkpoint_5000.pt
```

### Win-Rate Evaluation (Does IQL Actually Win?)

To quantify how often the trained ghosts win — rather than watching a single
episode — run the headless win-rate harness by asking for more than one episode
(or by providing `--win-rate-out`):

```bash
py -3.11 custom_environment\eval.py --learner iql --episodes 50 --eval-epsilon 0.05 --win-rate-out benchmarl_setup\runs\iql_win_rate.csv
```

It prints a summary line and (optionally) writes a one-row CSV
(`episodes,ghosts_win,pacman_win,timeout,ghosts_win_rate`):

```text
Win-rate over 50 episodes | learner=iql | ghosts win 33 (66.0%) | pacman win 17 | timeout 0
```

A ghost win means a ghost captured Pacman; `pacman win` means Pacman survived to
the environment time limit; `timeout` means the runner step cap was hit without a
terminal.

**Measured IQL baseline (plan-000008).** With the tuned recipe and retuned
rewards, IQL was trained at both 60k and 300k frames (seed 0). Both runs measure
a **0% ghost win rate** over 50 episodes, and the per-step training reward curve
stays flat (~`-0.20`) with no upward trend. This is a coordination ceiling, not a
budget shortfall: IQL learns each ghost's Q-values **independently**, so two
ghosts with only a 5×5 local view never discover the joint pincer needed to
corner a Pacman that actively flees to keep distance `PACMAN_SAFE_DISTANCE = 5`.
This is the expected role of IQL as the **independent baseline** — the value
factorization algorithms (`vdn`, `qmixlocal`, `qmixglobal`) are the coordination
path and are the ones expected to win. The win-rate harness is the tool that
makes this contrast measurable.

**Why `--eval-epsilon` matters.** The environment is fully deterministic (a
deterministic defense-first Pacman policy, fixed map-authored spawns, and a
greedy ghost policy), so every greedy episode is identical — a naive win rate
would be a trivial 0% or 100%. `--eval-epsilon` injects per-ghost epsilon-greedy
randomness (default `0.05`) with a per-episode seed so episodes vary and the rate
reflects policy robustness near-greedy. Use `--eval-epsilon 0` to collapse to the
single deterministic outcome. The base seed comes from `--seed` (episode `e` uses
`seed + e`; default base seed `0`). Win-rate mode is headless and ignores
`--render-mode`. In single-episode render mode (`--episodes 1` with no
`--win-rate-out`), `--eval-epsilon` is ignored.

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

Execution strategy:

- Algorithms run in parallel (for example IQL and VDN at the same time).
- Seeds run serially inside each algorithm worker.

Useful optional parameters:

```bash
--algorithms iql,vdn,qmixlocal,qmixglobal --frames-per-batch 200 --optimizer-steps 10 --train-batch-size 128 --memory-size 10000 --init-random-frames 1000
```

This command now trains and then automatically writes a benchmark summary CSV.

The summary CSV includes, per run:

- `algorithm`
- `seed`
- `run_dir`
- `n_points`
- `final_reward`
- `tail_mean_reward`
- `best_reward`
- `checkpoint_path`

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

> **Reward magnitudes were retuned in plan-000008** for a sharper pursuit→capture
> gradient (capture raised to `+30`, the distance signal made denser/symmetric at
> `±0.5`, `currently_visible` raised to `+0.3`, and the exploration bonuses
> trimmed). Signs are unchanged. Because absolute magnitudes shifted, reward
> curves are **not directly comparable** to runs produced before this change.

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
1. `+30.0` if Pacman is captured
2. `-20.0` if Pacman wins by timeout
3. `+1.0` if Pacman is newly spotted (visibility false -> true)
4. `+0.5` if Pacman target distance decreases (minimum over ghosts)
5. `-0.5` if Pacman target distance increases (minimum over ghosts)
6. `+0.3` if Pacman is currently visible to any ghost
7. `+0.05` if a ghost enters a recently-unvisited tile
8. `+0.03` if a ghost reveals previously unseen local cells
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
