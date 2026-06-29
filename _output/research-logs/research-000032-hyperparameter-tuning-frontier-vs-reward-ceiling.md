# Research 000032 | TB | 2026-06-29 15:04 UTC | Hyperparameter tuning frontier vs reward-shaping 40% ceiling

tags: reinforcement-learning, hyperparameter-tuning, experimental-design, benchmark, partial-observability

source: research-000032
spawned: research-000032, plan-000034
git_commit: 508cacd

## User brief

> seens like we are stuck on reward shapping. liveplot show a 40% ceiling on wein rate. I want to explore another frontier: tunning hiperparams

Clarified in-session (edited briefs entry):

> liveplot shows a 40% ceiling on win rate for a totally random pacman on curriculum learning. for a random pacman the capture rate should be 100%.

## Agent interpretation

The team has spent several cycles on reward shaping (sparse `capture_v0`, PBRS variants, the
research-000031 A/B benchmark) and now wants to pivot the frontier to **hyperparameter tuning**.
The motivating symptom is a `capture_pct_live_eval` plateau at ~40% even though, *against a
truly random Pacman*, 2–4 coordinating ghosts on a bounded grid should approach ~100% capture.

The deep result of this research is that **the 40%-vs-random gap is far more likely a confound
(curriculum-stage misattribution + known environment/eval artifacts + a possible partial-
observability wall) than a hyperparameter limit.** Hyperparameter tuning is a *legitimate
secondary frontier*, but pivoting to it now risks tuning optimizer knobs that physically cannot
cross a structural ceiling. The right move is a cheap **positive-control sanity battery first**,
then — only if 40% survives it — a focused scalar sweep on the replay-buffer / update-to-data
axis (not learning rate).

User decisions (collected via interview):
- **Ceiling condition:** random/easy Pacman — i.e. believed to be a genuine learning failure.
- **Compute:** GPU available (broader sweeps feasible).
- **Scope:** scalar hyperparameters only (no architecture/code changes).
- **Goal:** break the ceiling (raise win rate above 40%).

## Files reviewed

- `benchmarl_setup/run_pacman_benchmarl.py` — hardcoded `lr=1e-4`, `gamma=0.99` in
  `_tune_shared_experiment` (lines 57–58); exposed CLI knobs `--frames-per-batch`,
  `--optimizer-steps`, `--train-batch-size`, `--memory-size`, `--init-random-frames`,
  `--max-frames`, `--epsilon-anneal-ratio` (lines 81–90, 208–217); `evaluation = False` (line 294).
- `benchmarl_setup/algorithm_utils.py` — hardcoded epsilon floor `eps_end = 0.10` and
  `anneal_ratio = 0.95` in `training_exploration_schedule` (lines 105–113).
- `custom_environment/env/pacman_environment.py` — `_curriculum_stage` (209–217) and
  `_difficulty_params` (219–225): the **easy** stage is `pure_random=True`, **hard** is a
  deterministic evader; policy is rebuilt per curriculum stage as frames advance (line 352).
- `benchmarl_setup/liveplot.py` — plotted metric is `capture_pct_live_eval` (line 648).
- BenchMARL defaults: `conf/model/layers/mlp.yaml` (MLP `[256,256]`, Tanh, **no recurrence**);
  `conf/experiment/base_experiment.yaml` (default `lr=5e-5`, buffer `1,000,000`, `polyak_tau=0.005`).
- `_output/research-logs/research-000022-...md` — documents three structural capture-rate caps.
- `_output/research-logs/research-000028-...md` — the evasive-Pacman dose–response protocol.
- `product-design/project/constitution.md` — Q3 (≥5 seeds), T4 (explicit seeds), C1 (commit hash).

---

## Q&A log

### Q1 (initial). We're stuck on reward shaping — liveplot shows a ~40% win-rate ceiling against a totally random Pacman under curriculum learning (should be ~100%). I want to pivot to tuning hyperparameters. Is that the right frontier, and which knobs?

**A1.**

#### Bottom line, first

Tuning hyperparameters is a reasonable *secondary* frontier, but the symptom you describe — a
hard **40% plateau against a Pacman that should be ~100% catchable** — is the classic signature
of a **structural cap**, not a slow or mistuned optimizer. Three independent structural
explanations already fit your data, and none of them is fixable by any scalar hyperparameter.
**Verify the cause with a cheap positive control before you spend GPU on a sweep.** If you skip
that step you risk "tuning" knobs that cannot move a wall, then concluding (wrongly) that HP
tuning doesn't help.

#### 1. The single most important finding: "totally random Pacman" is probably a curriculum-stage misattribution

Your curriculum maps frames to difficulty like this
([pacman_environment.py:219-225](../../custom_environment/env/pacman_environment.py#L219-L225)):

| Curriculum stage | When (of curriculum frames) | Pacman behavior |
|---|---|---|
| **easy** | first 1/3 | `pure_random=True`, noise 0.0 → **fully random** |
| **medium** | middle 1/3 | noise 0.30, safe_distance 2 → mostly evasive |
| **hard** | final 1/3 | noise 0.0, full lookahead → **deterministic evader** |

The policy is **rebuilt to follow the curriculum stage as training advances** (line 352). So
Pacman is only *fully random during the first third* of training. The `capture_pct_live_eval`
value you read **late in the run is being measured against the hard deterministic evader**, not a
random Pacman. A 40% ceiling there is exactly the catchability wall that
[research-000028](research-000028-evasive-pacman-benchmark-protocol.md) was built to characterize —
it may be a correct, expected result rather than a bug or an HP failure. **"40% on a random
Pacman" and "40% at the end of an easy→hard curriculum" are very different claims, and your
live-plot cannot tell them apart.**

#### 2. Even setting the curriculum aside, you already have three documented structural caps

[research-000022](research-000022-eval-ghosts-stop-pacman-oscillates.md) recorded environment/eval
interactions that cap capture rate *independent of any hyperparameter*:

- **Oscillation saddle (RC2):** a stateless Pacman can enter a 2-cell back-and-forth that keeps
  it permanently just outside ghost view.
- **Safe-distance cordon (RC3):** `PACMAN_SAFE_DISTANCE=5` vs a ghost view radius of ~2 lets
  *stopped* ghosts cordon off the board without ever closing in.
- **Orbit reward (RC4):** a `CURRENTLY_VISIBLE=+0.3/step` term trains ghosts to *orbit* Pacman
  rather than capture it.

RC2/RC3 are properties of the Pacman controller and grid geometry — they would cap capture rate
even with a perfectly tuned learner.

#### 3. The architectural ceiling (relevant even though you scoped it out): memoryless MLP under partial observability

Your model is an **MLP `[256,256]` with no GRU/LSTM**, and observations can be a *local* window
(`--ghost-view-size`). In a POMDP, a memoryless policy cannot integrate information across time:
once Pacman leaves the view window, a feedforward ghost has no internal state to track it. This is
the textbook situation where **recurrence (or frame-stacking / a belief state) is the actual
lever** — and no value of `lr`, `epsilon`, or buffer size lifts it. The canonical QMIX/PyMARL
recipe that *does* solve hard cooperative tasks uses a **GRU + an episodic replay buffer**, both
of which are architecture, not scalars. **If your ceiling condition uses a local view, scalar-only
HP tuning is aiming at the wrong wall.** If it uses *full* observability, this concern is N/A and
the case for a scalar sweep is stronger — so decide and document the observability regime first.

#### 4. Within scalar-only scope: which knobs are real levers and which are red herrings

Your current config vs BenchMARL defaults:

| Knob | Current | BenchMARL default | Verdict |
|---|---|---|---|
| `off_policy_memory_size` (replay buffer) | **10,000** | 1,000,000 | **High-payoff (H1)** |
| `off_policy_n_optimizer_steps` | 10 | 1 | **High-payoff (H1)** |
| `frames_per_batch` | 200 | 6000 | interacts with UTD (H1) |
| `max_frames` | 60,000 | — | plausibly undertrained (H4) |
| epsilon floor `eps_end` | **0.10** | 0.05 (PyMARL) | real lever (H2), **hardcoded** |
| `lr` | 1e-4 | 5e-5 | **red herring (H3)** |
| `gamma` | 0.99 | 0.99 | fine |

- **H1 — replay buffer / update-to-data ratio (REAL, highest payoff).** Your UTD =
  `(10 optimizer_steps × 128 batch) / 200 collected frames` = **~6.4 gradient updates per
  collected frame**, against a 10k buffer that fully cycles roughly every 50 batches. That is a
  high-UTD, tiny-buffer regime — strong off-policy bias, catastrophic-forgetting risk, and
  overfitting to the most recent ~50 batches. Web best-practice corroborates: small buffers cause
  "high and unstable forgetting"; naive high UTD "can lead to collapse in off-policy deep RL." The
  fix is in-scope and already CLI-exposed: raise `--memory-size` to 100k–500k and/or lower
  `--optimizer-steps` to 1–4.
- **H2 — epsilon floor 0.10 (REAL, but hardcoded).** A 0.10 floor on two agents means ~19% chance
  at least one ghost acts randomly *every step* at convergence — it both degrades greedy rollouts
  during training and biases the on-policy capture metric downward. Lower to 0.02–0.05. **Caveat:
  this value is hardcoded in `algorithm_utils.py:106`, not a CLI flag.**
- **H4 — frame budget 60k (plausible).** Likely undertrained relative to BenchMARL's
  6000-frames-per-batch scale and the 5M+ step regimes used for hard cooperative MARL. Raise
  `--max-frames` to 150k–300k on the GPU.
- **H3 — learning rate 1e-4 (RED HERRING).** 1e-4 vs 5e-5 is a factor of two, well within stable
  Adam range; it is not a credible root cause for a 60-point capture gap. **Drop it from the
  sweep.**

#### 5. Your "scalar-only, no code changes" scope is internally contradictory — but not blocking

`lr` and `gamma` are hardcoded at
[run_pacman_benchmarl.py:57-58](../../benchmarl_setup/run_pacman_benchmarl.py#L57-L58); the epsilon
floor at [algorithm_utils.py:106](../../benchmarl_setup/algorithm_utils.py#L106). They **cannot be
swept without editing source.** The good news: the *highest-payoff* knobs (`--memory-size`,
`--optimizer-steps`, `--max-frames`) are already CLI flags, so a first sweep wave needs **zero
code changes**. Promote `lr`/`gamma`/epsilon-floor to flags only if wave 1 doesn't break the
ceiling. Reframe the constraint as "configuration-surface edits allowed; no model-architecture or
environment-logic changes."

#### 6. A defensible, GPU-efficient sweep methodology

- **Coordinate descent, not a full grid.** Tune one axis at a time (buffer → opt-steps →
  frames), holding the others — ~3–4 values × ≥5 seeds × 3 axes — instead of a combinatorial grid
  (hundreds of runs). Use small random search over the joint space only if budget allows. Skip
  Bayesian optimization — overkill and tooling risk for a course project.
- **≥5 seeds per point (constitution Q3).** Explicit seeds (T4); record the commit hash with each
  run (C1). Reuse the research-000028 sweep-manifest pattern for provenance.
- **You currently have no first-class eval metric.** `experiment_config.evaluation = False` and
  the only logger is CSV, so there is no comparable greedy capture-rate signal across runs. Before
  sweeping, add one in-loop **greedy (epsilon=0) capture-rate eval** with a fixed Pacman condition
  and fixed eval seeds — otherwise "did we break the ceiling?" is not reproducibly answerable.

#### 7. The verification battery you should run *before* the sweep

The cheapest experiment with the highest information value. A handful of short runs:

1. **Isolate the random condition.** Curriculum **off**, `--pacman-random-action-prob 1.0`
   (truly uniform random), **full observability** (`--ghost-view-size` unset), with the
   research-000022 artifacts neutralized (set `--pacman-safe-distance` near the view radius; avoid
   the orbit reward). Measure greedy capture.
   - If it jumps well above 40% → the ceiling was a **confound (curriculum stage / env artifact)**,
     *not* HP. Fix the environment/eval and **skip the sweep**.
   - If it stays ~40% → a **genuine learning limit**; the scalar sweep (§4) is now justified.
2. **Separate the metric artifact.** Add a greedy epsilon=0 eval distinct from the training-time
   on-policy metric to rule out the epsilon-floor measurement bias.
3. **Match eval to training observability** (research-000022 R5) so you are not measuring a
   train/eval view mismatch.

This battery costs little GPU and decides whether the entire sweep is worth running.

---

## Recommendations summary

| # | Priority | Recommendation |
|---|----------|----------------|
| R1 | HIGH | **Run a positive-control sanity battery BEFORE any sweep.** Curriculum off, `--pacman-random-action-prob 1.0`, full observability, research-000022 artifacts neutralized, greedy (ε=0) eval. If capture jumps above 40% → the ceiling was a confound, not HP → fix the env and skip the sweep. If it stays ~40% → genuine limit → sweep is justified. Highest information value per GPU-hour. |
| R2 | HIGH | **Disentangle "random Pacman" from "end-of-curriculum hard evader."** The curriculum's easy stage is the only fully-random phase; the late live-eval 40% is plausibly measured against the *hard deterministic evader* (= the research-000028 catchability wall), not a random Pacman. Confirm the exact condition the 40% is measured under before drawing any HP conclusion. |
| R3 | HIGH | **Decide and document the observability regime.** If the ceiling condition uses a *local* ghost view + memoryless MLP, scalar HP tuning cannot cross the POMDP wall (recurrence is the real lever, out of scope) — document it as structural. If *full* observability, the scalar sweep is on firmer ground. |
| R4 | MEDIUM | **If R1 confirms a genuine limit, sweep the UTD-interaction knobs, not lr.** In order: raise `--memory-size` 10k→100k–500k and/or lower `--optimizer-steps` 10→1–4 (H1); raise `--max-frames` 60k→150k–300k (H4). These are already CLI-exposed (zero code change). |
| R5 | MEDIUM | **Lower the epsilon floor 0.10→0.02–0.05 (H2).** Requires promoting the hardcoded `eps_end` (`algorithm_utils.py:106`) to a CLI flag — a small, bounded code change. Treat `lr` (H3, 1e-4 vs 5e-5) as fixed; drop it from the sweep. |
| R6 | MEDIUM | **Use coordinate descent (not full grid), ≥5 seeds/point (Q3), explicit seeds (T4), commit hash per run (C1).** Reuse the research-000028 sweep-manifest provenance pattern. Skip Bayesian optimization. |
| R7 | MEDIUM | **Add a first-class in-loop greedy (ε=0) capture-rate eval with a fixed Pacman condition and fixed eval seeds before sweeping** (`evaluation` is currently `False`; only CSV logger). Without it, sweep results are not comparable or citable. |
| R8 | LOW | **Promote `lr`, `gamma`, and the epsilon floor to CLI flags and amend the scope statement** to "configuration-surface edits allowed; no architecture/environment-logic changes." Resolves the internal contradiction in the scalar-only constraint. |
