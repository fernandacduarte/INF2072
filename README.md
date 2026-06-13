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

By default, evaluation preserves the original ASCII terminal rendering. To open
the human-view Pygame renderer, use:

```bash
py -3.11 custom_environment\eval.py --learner iql --render-mode human --delay 0.08
```

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
```

You can also pass an explicit checkpoint to eval:

```bash
--checkpoint path\to\checkpoint_5000.pt
```

Outputs are saved under `benchmarl_setup/runs` by default.

### Benchmark (Multi-Seed, Parallel by Algorithm)

You can now run a full benchmark with one command using:

- `benchmarl_setup/run_benchmark.py`

Example (5 seeds, shared training config):

```bash
py -3.11 benchmarl_setup\run_benchmark.py --algorithms iql,vdn --seeds 0,1,2,3,4 --max-frames 50000
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

Policy observations remain local 3x3 for all algorithms; only `qmixglobal` mixer uses this centralized state.

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
1. Each ghost only observes its local 3x3 neighborhood.
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
