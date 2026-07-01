# Research 000042 | fernanda-INF2072 | 2026-06-30 21:35 UTC | IQL hyperparameter tuning
tags: iql, hyperparameter-tuning, sample-efficiency, benchmarking, replay-buffer
spawned: plan-000043

---

## User Brief

> tunning hyperparameters of iql

## Agent Interpretation

The user wants guidance on which IQL (Independent Q-Learning) hyperparameters to tune and how, within the constraints of the current setup: BenchMARL 1.5.2, 60k frame budget, 5-seed benchmark, cooperative ghost agents in a custom Pacman environment.

## Files Consulted

- `benchmarl_setup/run_pacman_benchmarl.py` — main training runner, current hyperparameter values
- `benchmarl_setup/algorithm_utils.py` — `training_exploration_schedule`, shared defaults
- `_output/research-logs/research-000041-iql-gru-drqn-memory.md` — prior research context

---

## Q&A Log

### Q1

**Question**: What are the best practices for tuning hyperparameters of IQL in this project's multi-agent Pacman environment?

**Answer**:

The expert review evaluated the current hyperparameter set against 5 perspectives (PERF, ARCH, DATA, TEST, DX) and identified 4 high-impact issues and several medium-priority improvements.

#### Current hyperparameter baseline

| Hyperparameter | Current Value | Flag |
|---|---|---|
| Learning rate | 1e-4 | hardcoded in `_tune_shared_experiment` |
| Discount factor (gamma) | 0.99 | hardcoded |
| Epsilon init | 1.0 | hardcoded |
| Epsilon end | 0.10 | `--epsilon-end` |
| Epsilon anneal ratio | 0.95 | `--epsilon-anneal-ratio` |
| Frames per batch | 200 | `--frames-per-batch` |
| Optimizer steps (gradient steps/batch) | 10 | `--optimizer-steps` |
| Train batch size | 128 | `--train-batch-size` |
| Replay buffer size | 10,000 | `--memory-size` |
| Initial random frames | 5,000 | `--init-random-frames` |
| Max frames | 60,000 | `--max-frames` |

#### Key findings

**[HIGH IMPACT] Optimizer steps ratio 10:1 is too aggressive for a 10k buffer**

With optimizer_steps=10 and frames_per_batch=200, the agent runs 10 gradient updates for every 200 new frames. At 60k frames: 300 batches x 10 = 3,000 gradient steps drawing from a 10k buffer. With rare capture events (most transitions are no-capture), the buffer fills up with near-identical transitions and the network overfits them before they age out — this is "replay ratio overfitting" (Fedus et al. 2020). Ratios above 4:1 with small buffers lead to instability or policy collapse in DQN-family algorithms.

**[HIGH IMPACT] Epsilon anneal over 95% of 60k leaves only 3k exploitation frames**

Epsilon reaches its floor (0.10) at frame 57,000. Only 3,000 frames (~15 episodes) remain for the greedy policy to consolidate. A pursuit task requiring multi-agent coordination needs far more exploitation frames to stabilize. At epsilon_end=0.10, agents are still 10% random at convergence — this is too high for evaluation-quality behavior (evaluation should always be greedy, but the final training policy is the primary optimization signal).

**[HIGH IMPACT] Replay buffer too small; init_random_frames fills it only halfway**

At init_random_frames=5,000 and memory_size=10,000, training starts with a half-empty buffer. The buffer-to-batch ratio is 10,000/128 ≈ 78, below the recommended minimum of 100 for sufficient diversity. Combined with optimizer_steps=10, early training depletes buffer diversity rapidly.

**[MEDIUM] lr and gamma are hardcoded and not exposed as CLI flags**

`_tune_shared_experiment` hard-applies lr=1e-4 and gamma=0.99 to experiment_config for all three algorithms. This prevents per-algorithm overrides and blocks ablation sweeps without source code edits — the most commonly ablated hyperparameters are not reachable from the command line.

**[MEDIUM] BenchMARL IQL YAML defaults for target network update are not surfaced**

`IqlConfig.get_from_yaml()` loads the BenchMARL IQL default YAML which includes target network update frequency and double DQN flags. These are never overridden or documented. The target update period is the most IQL-specific knob: too frequent causes instability in non-stationary MARL; too infrequent slows convergence at 60k frames.

**[MEDIUM] No shared hyperparameter validation exists**

The shared hyperparameter set (lr, gamma, epsilon, buffer size, batch size) is applied identically across IQL/VDN/QMIX by convention, not by enforcement. A future refactor of `_tune_shared_experiment` could silently break cross-algorithm fairness, which would invalidate the D-003 benchmarking standard.

**[WORTH NOTING] Gamma=0.99 is correct; lr=1e-4 is defensible**

Gamma=0.99 gives an effective horizon of 100 steps, which correctly spans the 200-step max episode. No change needed. lr=1e-4 is in the standard range for DQN-family (1e-4 to 5e-4); the bigger wins come from the buffer and epsilon settings, not from lr tuning.

---

## Recommendations Summary

### HIGH priority

**Rec 1 — Reduce optimizer_steps and increase replay buffer**

Change the default call to:
```
--optimizer-steps 4 --memory-size 25000 --init-random-frames 12000
```

Rationale: lowers the update-to-data ratio from 10:1 to 4:1, raises buffer-to-batch ratio from 78 to ~195, and sets warmup to roughly half the buffer (standard practice). Apply identically to IQL, VDN, and QMIX. No code changes needed — these are already CLI flags.

**Rec 2 — Lower epsilon anneal ratio to 0.70 and epsilon end to 0.05**

Change the default call to:
```
--epsilon-anneal-ratio 0.70 --epsilon-end 0.05
```

Rationale: raises exploitation frames from 3k to 18k (9x more), giving ~90 near-greedy episodes for policy consolidation. Lowering epsilon_end from 0.10 to 0.05 tightens the floor at no compute cost. Apply identically to all algorithms.

**Rec 3 — Raise init_random_frames to fill the full replay buffer before first gradient update**

With memory_size=25000 (from Rec 1), set:
```
--init-random-frames 25000
```

This delays first gradient update until the buffer is full, producing higher-quality initial gradient steps. The cost is 25k "wasted" frames — but these are the cheapest frames in the budget (random policy, no backprop).

### MEDIUM priority

**Rec 4 — Expose lr, gamma, and target-update-interval as CLI flags**

Add `--lr`, `--gamma`, and `--target-update-interval` to `parse_args()` in `benchmarl_setup/run_pacman_benchmarl.py` and forward them in `_tune_shared_experiment`. This enables ablation sweeps from the command line without source edits.

**Rec 5 — Verify and document BenchMARL IQL YAML defaults**

Run a throwaway script to print all fields of `IqlConfig.get_from_yaml()`. Document the target network update period in `product-design/project/standards.md`. A reasonable target: hard copy every 2,000–5,000 environment steps.

**Rec 6 — Lock shared hyperparameters in a constants module with a validation assertion**

Create `benchmarl_setup/shared_hparams.py` defining the shared set (lr, gamma, epsilon, buffer, batch). Load it in `_tune_shared_experiment`. Add a pytest assertion that all three algorithms receive identical values for shared keys when called with defaults.

**Rec 7 — Run a minimal lr ablation before fixing lr for the final benchmark**

Test lr in {5e-5, 1e-4, 3e-4} for IQL with otherwise-default settings (after Recs 1–3). 3 values x 5 seeds = 15 runs at 60k frames each (~2–4 hours on CPU). Pick the best-performing lr for all three algorithms in the final benchmark.

### LOW priority

**Rec 8 — Defer Prioritized Experience Replay (PER)**

PER would upsample rare capture events but introduces alpha and beta hyperparameters and complicates cross-algorithm fairness. Address Recs 1–3 first; if capture rate remains near zero after those changes, revisit PER. Document this deferral.

**Rec 9 — Defer lr scheduling (cosine decay, warmup)**

At 60k frames, the complexity cost of a schedule outweighs the benefit. Revisit if the frame budget is raised above 200k.

---

## Trade-offs

| Trade-off | Resolution |
|---|---|
| PERF (buffer diversity) vs DATA (cross-algorithm fairness) | Apply buffer=25k identically to all three algorithms — safe since mixing networks don't change replay semantics |
| ARCH (expose lr/gamma as flags) vs DATA (accidental per-algorithm divergence) | Implement Rec 4 and Rec 6 together; the constants module guards against accidental divergence |
| TEST (lr ablation cost) vs frame budget | 15 runs x 60k frames ≈ 2–4 hours; one-time cost that strengthens paper claims |
| PERF (epsilon end 0.05) vs MARL non-stationarity | 0.05–0.10 is the defensible range; 0.05 applied uniformly controls the relative effect across algorithms |
