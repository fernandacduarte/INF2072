# Research 000041 | fernanda-INF2072 | 2026-06-30 21:21 UTC | IQL network memory — DRQN / GRU
tags: iql, drqn, gru, recurrent, partial-observability

---

## User Brief

> is there any way to give a iql net a memory ?

## Agent Interpretation

The user is asking whether the IQL Q-network can be given temporal memory so it can reason across consecutive time steps rather than treating each observation as independent. This is the standard DRQN (Deep Recurrent Q-Network) problem. The question has two layers: (a) is it theoretically valid, and (b) is it practically feasible in BenchMARL?

## Files Consulted

- `benchmarl_setup/run_pacman_benchmarl.py` — current training script (MlpConfig, line 320)
- `.venv/Lib/site-packages/benchmarl/algorithms/common.py` — sequence-length / has_rnn handling (lines 158–164)
- `.venv/Lib/site-packages/benchmarl/models/gru.py` — GRU model implementation
- `.venv/Lib/site-packages/benchmarl/conf/model/layers/gru.yaml` — default GRU config

---

## Q&A Log

### Q1

**Question**: Is there any way to give an IQL network memory?

**Answer**:

Yes. The technique is **DRQN (Deep Recurrent Q-Network)** — replace the MLP in the Q-network with a GRU or LSTM. The network maintains a hidden state `h_t` that accumulates information over consecutive time steps, converting the agent from a memoryless function `Q(o_t)` into a stateful function `Q(o_t, h_t)`.

#### Motivation for this project

With `ghost_view_size=3` or `5`, each ghost sees only a local window of the grid. From a single frame, the ghost cannot determine whether Pacman is moving left, right, toward it, or away. A GRU hidden state lets the agent accumulate trajectory information over time — making the distinction between "Pacman moving toward me" vs. "Pacman moving away" possible, which is critical for reactive pursuit.

#### BenchMARL native support

BenchMARL 1.5.2 ships `GruConfig` and `LstmConfig` as first-class model configs. The change is **one line** in `benchmarl_setup/run_pacman_benchmarl.py`:

```python
# Before (line 320):
from benchmarl.models import MlpConfig
model_config = MlpConfig.get_from_yaml()

# After:
from benchmarl.models import GruConfig
model_config = GruConfig.get_from_yaml()
model_config.num_feature_dims = 2  # same as MLP
```

#### Replay buffer adaptation (automatic)

The hard part of DRQN with off-policy algorithms (IQL uses a replay buffer) is that randomly sampled `(s, a, r, s')` transitions destroy temporal ordering, making hidden-state bootstrapping impossible. BenchMARL handles this automatically: when `has_rnn=True`, `Algorithm.get_replay_buffer()` (common.py lines 158–164) switches to storing full episode sequences and adjusts `memory_size` and `sampling_size` by `sequence_length`.

BenchMARL uses **zero-state initialization** — the GRU hidden state resets to zero at episode boundaries (enforced by the `is_init` flag in the GRU forward pass). This is the standard DRQN approach and is valid when sequences are long enough (your `frames_per_batch=200` with `n_envs=1` gives sequences of ~200 steps, more than sufficient for warm-up).

#### What memory improves

| Aspect | Before (MLP) | After (GRU) |
|---|---|---|
| Temporal reasoning | Stateless — each step independent | Stateful — accumulates history |
| Partial observability handling | Single-frame only | Trajectory-aware |
| Ghost-to-ghost coordination | None (IQL) | None (still IQL — GRU does not help coordination) |

#### What memory does NOT fix

IQL is still independent. Each ghost has its **own** hidden state. The GRU improves individual temporal reasoning but not ghost-to-ghost coordination. For both memory AND coordination, use **VDN-GRU** or **QMIX-GRU**.

#### GRU vs. LSTM

Both are available in BenchMARL. GRU is simpler (one fewer gate than LSTM), trains slightly faster, and tends to perform similarly on short-to-medium sequence lengths. Prefer GRU as the default; try LSTM only if GRU underperforms.

#### GRU default config

```
hidden_size: 128
n_layers: 1
bias: True
dropout: 0
mlp_num_cells: [256, 256]   # MLP head after the recurrent layer
```

#### Training cost

GRU is heavier: each minibatch sample is now a full episode sequence (200 steps), not a single transition. Expect slower wall-clock time per iteration. The memory budget per sample also increases. Reduce `off_policy_train_batch_size` if you run out of RAM (e.g., 64 instead of 128).

---

## Expert Review Perspectives

*Evaluated by research-reviewer agent.*

| Perspective | Status | Finding |
|---|---|---|
| ARCH (algorithm correctness) | Adopted | DRQN is theoretically sound for the POMDP case; BenchMARL's native `has_rnn` path makes GruConfig valid without custom code |
| DX (implementation risk) | Adopted | Change is a one-line swap; BenchMARL absorbs replay-buffer complexity automatically; risk is low |
| PERF (training stability) | Deferred | Zero-state init introduces ~5-10% gradient bias at start of sequences; sequence-level replay shrinks effective buffer diversity |
| TEST (experimental validity) | ⚠️ Deferred — key concern | Applying GRU only to IQL while leaving VDN/QMIX on MLP creates an asymmetric comparison. The coordination mechanism becomes confounded with the memory advantage. **If GRU is used for IQL, apply it uniformly to all algorithms.** |

### TEST concern in detail

If the research question is "which coordination structure (IQL vs. VDN vs. QMIX) performs better?", then giving IQL a memory upgrade that the others don't have taints the comparison. The recommended designs are:

- **Option A** — Run one MLP sweep (all three algorithms, no memory) and one GRU sweep (all three, with memory). Report separately.
- **Option B** — Use GRU-IQL as an explicit ablation labeled as such, not as the primary IQL baseline.
- **Option C** — Add `--model mlp|gru` flag to `run_benchmark.py` so the config is explicit and recorded in the run name.

The reviewer's framing: "does memory help IQL at all?" and "does coordination structure add value beyond memory alone?" are actually two richer findings than a single mixed comparison.

---

## Recommendations Summary

| Priority | Recommendation |
|---|---|
| **HIGH** | If you use GRU for any algorithm, apply it uniformly to all (IQL, VDN, QMIX) so coordination is the sole independent variable in the comparison. |
| **HIGH** | Replace `MlpConfig` with `GruConfig` in `run_pacman_benchmarl.py` when using partial observations (`ghost_view_size=3/5`). Cost: one line change. BenchMARL handles replay-buffer adaptation automatically. |
| **MEDIUM** | Run a 2×2 ablation: `{MLP, GRU} × {IQL, QMIX}`. Separates the memory effect from the coordination effect; richer story for the course report. |
| **MEDIUM** | Verify `algorithm.has_rnn == True` and log `sequence_length` at startup before committing to a 5-seed benchmark run. |
| **LOW** | Acknowledge zero-state init bias in the methods section. BenchMARL does not implement R2D2-style burn-in; one sentence is sufficient. |
| **LOW** | Monitor RAM on the first GRU run. If constrained, reduce `off_policy_train_batch_size` (128→64), not `sequence_length`. |
