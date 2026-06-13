# fernanda-INF2072

Multi-agent RL research — custom Pacman environment with ghost coordination using BenchMARL (IQL, VDN, QMIX), for INF2072 at PUC-Rio.

## Stack

- Python 3.11
- BenchMARL + TorchRL (multi-agent RL algorithms: IQL, VDN, QMIX)
- gymnasium + PettingZoo (environment interfaces)
- pytest (testing)
- Deployment: local (Windows, Python 3.11 venv)

## Build & Run

```bash
# Setup
py -3.11 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Train
py -3.11 benchmarl_setup\run_pacman_benchmarl.py --algorithm iql

# Benchmark (multi-seed)
py -3.11 benchmarl_setup\run_benchmark.py --algorithms iql,vdn --seeds 0,1,2,3,4

# Evaluate
py -3.11 custom_environment\eval.py --learner iql

# Tests
py -3.11 -m pytest test/
```

## Project Shape

This is a research CLI project, not a web application. Scripts are organized by concern:

- `benchmarl_setup/` — training runners, benchmark orchestration, reward plotting
- `custom_environment/` — Pacman RL environment, evaluation, rendering
- `test/` — smoke tests
- `slides-aulas/` — course slides

All experiment outputs (checkpoints, reward plots, benchmark CSVs) go to `benchmarl_setup/runs/`.

See `product-design/conventions.md` for the full directory layout and path variables.

## Key Conventions

- Python 3.11 required; use `py -3.11` to invoke scripts
- All experiment outputs go to `benchmarl_setup/runs/`
- Custom environment in `custom_environment/`; BenchMARL integration adapters in `benchmarl_setup/`

@.claude/rules/
@product-design/conventions.md
