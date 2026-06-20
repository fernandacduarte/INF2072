# AS-CODED — fernanda-INF2072

<!-- maintained-by: Agent (post-skill) -->

---

## Conceptual Design

### 1. Platform Purpose

Custom Pacman multi-agent RL environment. Scripts in `benchmarl_setup/` wrap the environment into BenchMARL tasks and run IQL, VDN, QMIX experiments. `custom_environment/` holds the PettingZoo AEC environment, evaluation, and rendering logic.

### 2. Entity Hierarchy

```
Experiment Run (run directory in benchmarl_setup/runs/)
└── Algorithm Config (YAML/JSON in run dir)
    └── Episode (in-memory during training)
        └── Reward Log (CSV output per run)
```

### 3. Domain-Specific Concepts

- Ghost coordination via shared joint reward
- Multi-seed benchmark aggregation (CSV + plot)
- BenchMARL task adapter in `benchmarl_setup/`
- Pallet-win condition: when Pacman eats every map-authored pallet (`_pellet_mask` drained), the episode truncates and the ghost team takes `Reward.PACMAN_WIN_PALLETS = -20.0` (symmetric with the timeout loss). `_total_pallets` is captured per-episode on `reset()`; the global state exposes `pallets_remaining_norm` (trailing feature) so VDN/QMIX see board-clearance urgency. Source: plan-000003.
- Deterministic safety-aware Pacman policy: Pacman is no longer a uniform random walker. `custom_environment/env/domain/pacman_policy.py` defines `PacmanPolicy`, a goal-directed controller whose objective is survival while eating pellets. Per step it runs a single BFS flood-fill (O(R*C), pellet-count independent) and routes Pacman along ghost-free corridors to the nearest reachable pellet. A three-state machine (`SEEKING_PELLET → FLEEING → COOLDOWN`) flees when any ghost is within `PACMAN_DANGER_RADIUS = 3` BFS cells (defined in `constant.py`); the flee target maximizes the minimum BFS distance to any ghost, and the COOLDOWN hold prevents oscillation at the danger boundary. `PacManEnvironment` instantiates a fresh `PacmanPolicy` in `__init__` and `reset()` and calls `choose_action(...)` at the Pacman step. This raises survival pressure on the ghost RL agents (uncoordinated ghosts now lose to pallet-clearance more often). Source: plan-000007 / research-000006.

### 4. Permission Model

Single-user local CLI tool. No authentication.

### 5. Export Formats

- CSV: benchmark results
- PNG: reward plots
- PT: PyTorch model checkpoints

---

## Metacommunication

*Populated by post-skill on first plan execution.*

---

## Journey Maps

*Populated by post-skill on first plan execution.*
