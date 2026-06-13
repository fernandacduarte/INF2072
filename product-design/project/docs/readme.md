---
freshness: on-structural-change
diataxis: reference
---

# fernanda-INF2072

Custom Pacman multi-agent RL environment with cooperative ghost agents. Benchmarks IQL, VDN, and QMIX algorithms using BenchMARL under reproducible conditions for the INF2072 course at PUC-Rio.

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11 | Required interpreter |
| pip | latest | Dependency management |

## Getting Started

```bash
# Setup (run once)
py -3.11 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Train a single algorithm
py -3.11 benchmarl_setup\run_pacman_benchmarl.py --algorithm iql --seed 0

# Run full benchmark (5 seeds, 3 algorithms)
py -3.11 benchmarl_setup\run_benchmark.py --algorithms iql,vdn,qmix --seeds 0,1,2,3,4

# Evaluate a trained policy
py -3.11 custom_environment\eval.py --learner iql

# Run tests
py -3.11 -m pytest test/
```

## Architecture Overview

Script-based research pipeline with no web server. `custom_environment/` contains the PettingZoo AEC Pacman environment with cooperative ghost agents. `benchmarl_setup/` contains BenchMARL task adapters and experiment runners. All outputs go to `benchmarl_setup/runs/`.

## Recommended Reading Order

| # | Document | What you'll learn |
|---|----------|-------------------|
| 1 | This README | Project overview and setup |
| 2 | [conventions.md](../../conventions.md) | Directory layout and variable definitions |
| 3 | [product-design-as-intended.md](../product-design-as-intended.md) | Design intent and entity model |
| 4 | `custom_environment/pacman_env.py` | Environment implementation |
| 5 | `benchmarl_setup/run_benchmark.py` | Benchmark orchestration |

## License

Academic research project — PUC-Rio INF2072. Not for redistribution.
