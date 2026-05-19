# Simple 2D Football MARL with PyTorch

This small project implements three cooperative multi-agent reinforcement learning algorithms from scratch for a toy 2D football environment:

- `IQL` (Independent Q-Learning)
- `VDN` (Value Decomposition Networks)
- `QMIX`

## Environment

The environment is a simple grid world with two cooperating agents. The team gets a shared reward when the ball-holder successfully shoots from the rightmost column.

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

From the workspace root, run with the package module form:

```bash
python3 -m futebol2d.train --algo iql --episodes 300
python3 -m futebol2d.train --algo vdn --episodes 300
python3 -m futebol2d.train --algo qmix --episodes 300
```

Each training run now saves:

- a CSV log: `iql_training.csv`, `vdn_training.csv`, or `qmix_training.csv`
- a model checkpoint: `iql_model.pth`, `vdn_model.pth`, or `qmix_model.pth`

If you prefer to run the script directly, set `PYTHONPATH` to the workspace root first:

```bash
set PYTHONPATH=.
python3 futebol2d/train.py --algo iql --episodes 300
```

Compare average rewards and convergence speed.

## Render trained agents

After training, visualize a learned policy with:

```bash
python3 -m futebol2d.eval --algo qmix --model-path qmix_model.pth --episodes 1 --delay 0.5
```

This will print the grid and step-by-step action trace.

## Plot training results

Compare reward curves across algorithms:

```bash
python3 -m futebol2d.plot iql_training.csv vdn_training.csv qmix_training.csv --labels IQL VDN QMIX --window 20
```

Save the plot image with:

```bash
python3 -m futebol2d.plot iql_training.csv vdn_training.csv qmix_training.csv --labels IQL VDN QMIX --window 20 --save comparison.png
```

## Next steps

- increase environment complexity (defenders, passing, goals)
- extend observations with velocities and directional features
- add centralized training with decentralized execution
- compare IQL, VDN, and QMIX on the same reward curve
