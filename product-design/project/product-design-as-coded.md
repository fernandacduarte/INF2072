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
- Deterministic defense-first Pacman policy: Pacman is no longer a uniform random walker. `custom_environment/env/domain/pacman_policy.py` defines `PacmanPolicy`, a stateless controller whose **primary** objective is survival and **secondary** objective is pellet collection. Per step it runs two multi-source BFS flood-fills (from all ghosts, and from all pellets; O(R*C) total) and scores each legal move with a lexicographic key: `(safety, pellet_progress)`, where `safety = min(distance_to_nearest_ghost, PACMAN_SAFE_DISTANCE)` and `pellet_progress = -distance_to_nearest_pellet`. Because safety is the first key, Pacman always takes the move that keeps it furthest from ghosts; it pursues pellets only among moves already at the safety cap (`PACMAN_SAFE_DISTANCE = 5`, defined in `constant.py`). This makes "flee the ghosts" dominate "grab pellets" without an explicit state machine, and never lures Pacman toward a ghost-adjacent pellet. Suicidal moves (onto a GHOST cell) and walls are excluded. `PacManEnvironment` instantiates a fresh `PacmanPolicy` in `__init__` and `reset()` and calls `choose_action(...)` at the Pacman step. This raises survival pressure on the ghost RL agents (only genuinely coordinated ghosts can corner an evasive Pacman). Source: plan-000007 / research-000006 (defense-first revision).

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
