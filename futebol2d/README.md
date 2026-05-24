# Simple 2D Football MARL with PyTorch

This small project implements three cooperative multi-agent reinforcement learning algorithms from scratch for a toy 2D football environment:

- `IQL` (Independent Q-Learning)
- `VDN` (Value Decomposition Networks)
- `QMIX`

## Environment

The environment is a simple grid world with two cooperating agents. The team gets a shared reward when the ball-holder successfully shoots from the rightmost column.

Reward is now shaped to improve learning stability and speed:
- score bonus (dominant objective)
- small step penalty (faster solutions)
- dense ball-progress reward (moving ball right)
- forward-pass bonus and backward-pass penalty
- failed-shot penalty and timeout penalty

These coefficients are configurable through `SimpleFootballEnv(..., reward_weights={...})` in `env.py`.

Observations per agent include:
- own normalized position
- teammate normalized position
- ball normalized position
- binary possession flag

The action space includes:
- stay
- move up/down/left/right
- shoot

## Algorithms

### IQL

Each agent learns an independent Q-network using the shared reward signal.
Pros:
- easy to implement
- works for fully independent tasks

Cons:
- ignores coordination structure
- can struggle when teammates change behavior (non-stationarity)

### VDN

Each agent has its own Q-network, but the joint value is the sum of individual Q-values.
Pros:
- encourages cooperation via a shared value decomposition
- still relatively simple

Cons:
- only additive factorization is supported
- cannot represent complex joint action interactions

### QMIX

Each agent Q-values are combined by a mixing network conditioned on the global state.
Pros:
- more expressive than VDN
- preserves monotonicity so optimization remains stable

Cons:
- more complex to implement
- still restricted by monotonicity constraints

## Running experiments

```bash
python train.py --algo iql --episodes 300
python train.py --algo vdn --episodes 300
python train.py --algo qmix --episodes 300
```

Use `--device` to select the compute device (`cpu` or `cuda`). Example:

```bash
python train.py --algo qmix --episodes 300 --device cuda
python train.py --algo iql --episodes 300 --device cpu
```

If `cuda` is requested but not available, install a CUDA-enabled PyTorch and run on a machine with an NVIDIA GPU, or use `--device cpu` instead.

Each training run now saves:

- a CSV log: `iql_training.csv`, `vdn_training.csv`, or `qmix_training.csv`
- a model checkpoint: `iql_model.pth`, `vdn_model.pth`, or `qmix_model.pth`
- greedy evaluation metrics printed at the end (`mean_reward`, `std`, `score_rate`)

Compare average rewards and convergence speed.

### Multi-seed training and evaluation

Run repeated experiments from a seed range and automatically save aggregated reports:

```bash
python train.py --algo vdn --episodes 300 --n-seeds 5 --seed 0 --eval-episodes 20 --output-dir runs_vdn
python train.py --algo qmix --episodes 300 --n-seeds 5 --seed 0 --eval-episodes 20 --output-dir runs_qmix
```

For each seed, this creates:

- `{algo}_seed{seed}_training.csv`
- `{algo}_seed{seed}_model.pth`

And for the full seed set, this creates:

- `{algo}_multiseed_summary.csv` (per-episode mean/std/min/max reward across seeds)
- `{algo}_multiseed_eval.csv` (per-seed greedy eval metrics and artifact paths)

## Batch training all algorithms

To train IQL, VDN, and QMIX in sequence with the same parameters, use the provided batch script:

```bat
train_all.bat --episodes 300 --n-seeds 5 --seed 0 --eval-episodes 20 --output-dir runs_all
```

Pass any arguments you would normally give to `train.py` (except `--algo`). The script will run all three algorithms with those settings, saving results in the specified output directory.

Artifacts for each algorithm will be named as described above (e.g., `iql_multiseed_summary.csv`, `vdn_multiseed_summary.csv`, etc.).

## Render trained agents


After training, visualize a learned policy with:

```bash
python3 -m eval --algo qmix --models-dir runs_all --episodes 1 --delay 0.5
```

The evaluator automatically picks the best seed using `{algo}_multiseed_eval.csv` in the models directory.

This will print the grid and step-by-step action trace.

## Plot training results

`plot.py` now supports automatic comparison of the three algorithms from a runs folder.

All seeds (uses `*_multiseed_summary.csv` for IQL/VDN/QMIX):

```bash
python3 -m plot --runs-dir runs_all
```

Specific seed (uses `*_seed{seed}_training.csv` for IQL/VDN/QMIX):

```bash
python3 -m plot --runs-dir runs_all --seed 2
```

Notes:
- In all-seeds mode, rewards are plotted as mean with shaded `mean ± std`.
- In specific-seed mode, rewards use moving average and epsilon is plotted in a second figure.
- Output files are saved automatically as `compare_multiseed.png` or `compare_seed{seed}.png` inside the runs folder (unless `--save` is provided).

Manual CSV mode is still available for custom comparisons:

```bash
python3 -m plot iql_training.csv vdn_training.csv qmix_training.csv --labels IQL VDN QMIX --window 20 --save comparison.png
```

## Next steps

- increase environment complexity (defenders, passing, goals)
- extend observations with velocities and directional features
- add centralized training with decentralized execution
- compare IQL, VDN, and QMIX on the same reward curve
