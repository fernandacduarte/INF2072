# Research 000027 | TB | 2026-06-26 12:55 UTC | Algorithms fail to learn capture (rate falls 80%→20%)

tags: reward-shaping, reward-hacking, marl, benchmark, rl-correctness
spawned: plan-000028

## User brief

> there is benchmark and liveplot running. however all algorithms fail to learn how to capture (capture rate is showing a decrease from 80% to 20% across frames).

## Agent interpretation

A multi-seed benchmark (IQL, VDN, QMIX — all DQN-family value methods) is training cooperative ghosts to capture a fleeing Pacman. The liveplot shows the **measured capture rate declining monotonically from ~80% to ~20%** as training progresses, across *all* algorithms. The capture rate is now measured by periodic deterministic eval of the trained checkpoint (the old `reward > 0` proxy was replaced in commit `4142e1e`), so the decline reflects a genuine policy regression rather than a metric artifact — *with one caveat the review flagged (see Q&A A4)*. The question: why are the ghosts getting **worse** at capturing the longer they train?

## Files examined

- `Makefile` — benchmark uses `REWARDS = custom_environment.env.rewards.current:CurrentTeamReward` (the V2 reward)
- `custom_environment/env/rewards/current.py` — `CurrentTeamReward` (V2) and `CurrentGitTeamReward` (V1) strategies
- `custom_environment/env/rewards/loader.py`, `base.py` — strategy resolution / context schema
- `custom_environment/env/domain/constant.py` — reward enum / shaping-alpha exposition
- `custom_environment/env/pacman_environment.py` — `max_steps = 200`, `GHOST_VIEW_SIZE = 5`
- `custom_environment/env/domain/pacman_policy.py` — defensive (flee-first) Pacman policy
- `benchmarl_setup/run_benchmark.py` — periodic deterministic capture-eval snapshots

---

## Q&A log

### Q1. Why does capture rate fall from 80% to 20% across training, for all algorithms?

**Root cause: the dense reward `currently_visible = +0.6`, paid every step Pacman is visible, makes *stalking* Pacman more profitable than *capturing* it.** The ghosts are not failing to learn — they are correctly learning a degenerate optimum that the reward function actually rewards.

The benchmark default reward is `CurrentTeamReward` (V2 weights, `Makefile:21`). In its `compute()` (`current.py:366-372`), the visibility bonus is appended **unconditionally** whenever Pacman is visible:

```python
if context.pacman_visible:
    if (not self._last_any_pacman_visible and self._unseen_steps >= ...):
        terms.append(RewardTerm("newly_spotted", w.newly_spotted))
    terms.append(RewardTerm("currently_visible", w.currently_visible))   # <-- +0.6 EVERY visible step
```

Contrast the V1 strategy `CurrentGitTeamReward` (`current.py:126-127`), where the same term is **gated on `visibility_progress`** — only paid when the ghost is actually *closing distance*:

```python
if visibility_progress:
    terms.append(RewardTerm("currently_visible", w.currently_visible))
```

This single difference (unconditional vs. progress-gated) is the regression.

**Why it changes the optimal policy.** `currently_visible` is a *non-potential-based* dense bonus: it pays the agent for merely *being in* a state feature (Pacman visible), not for *making progress*. Ng, Harada & Russell (1999) proved that only **potential-based** shaping of the form `F = γΦ(s') − Φ(s)` preserves the optimal policy; arbitrary per-step bonuses **shift** it. A reward that pays +0.6/step for keeping Pacman in view, while the +40 capture stays available for later, makes the *return-maximizing* behavior "keep Pacman at the edge of the 5×5 view and never close in." That is exactly the stalking/hovering behavior an earlier report (`research-000022`) independently observed: ghosts stop and hover keeping Pacman just in range without capturing.

**Why all three algorithms agree.** IQL, VDN, and QMIX optimize the *same* misaligned objective, so they converge to the *same* degenerate optimum. (Caveat: identical decline across algorithms is *also* consistent with a shared learner pathology or shared eval harness — see A4.)

**Why it falls over training rather than starting low.** Early in training ε is high, so exploration stumbles into captures (and the greedy policy is not yet trusted). As ε decays and the learned greedy value estimates take over, the policy commits to the stalking optimum it has discovered — and capture rate falls.

### Q2. Show the reward arithmetic — is stalking really worth more than capturing?

Yes, though the margin is narrower than a first pass suggests. **Corrected ledger** (the review caught two errors in my first cut):

Episode horizon `max_steps = 200`. Suppose a ghost acquires Pacman and then patrols to keep it visible for ~130 of the remaining steps:

| Behavior | Reward components | Episode return |
|---|---|---|
| **Stalk to timeout** | ~130 visible steps × (`currently_visible` +0.6 + `valid_move` +0.03 + `timestep` −0.01) ≈ **+73…+81**, then `pacman_timeout_win` **−35** | **≈ +38 … +46** |
| **Capture promptly** | `get_pacman` **+40** terminal, forgoing most of the presence bonus by ending early | **≈ +40** |

Two corrections vs. my initial estimate:
1. **Per-step net is ~+0.56–0.62, not +0.59**, depending on whether the ghost freezes (`stay_still` −0.03) or patrols to avoid the anti-cycle penalties (`repeated_direction_reversal`, `two_step_cycle`). A *patrolling* hover that dodges those penalties is the profitable variant.
2. **Potential shaping does NOT reward stalking.** `F = Φ(s') − Φ(s)` with `Φ = −1.2·distance` *telescopes*: over an episode it sums to `Φ(end) − Φ(start)`. A stalker that ends at the same distance it started contributes ≈ 0 from shaping. So the potential term is the *one term behaving correctly* and must be excluded from the stalking ledger. (My earlier framing wrongly implicated it.)

Even with the corrected, less-dramatic numbers, **stalking (≈ +38–46) ≳ prompt capture (+40)** — and crucially, stalking at distance against a *fleeing* Pacman is far *easier and more reliable* than cornering it, so the policy gradient/value estimates favor it strongly.

### Q3. Isn't this just RL instability (deadly triad), not a reward bug?

The code evidence + `research-000022`'s behavioral observation make **reward misalignment the leading hypothesis**, but the review correctly notes the *clean monotonic* 80→20 shape does not by itself prove it. The same shape is consistent with **deadly-triad soft divergence / value overestimation** (van Hasselt et al. 2018) — IQL/VDN/QMIX are all bootstrapped, off-policy, function-approximated, so they have the full triad, and "all three decline identically" is equally explained by shared triad susceptibility. **This is why the diagnostics below are on the critical path, not optional.** They discriminate: stalking predicts *rising mean episode length* and `currently_visible` *dominating episodic return*; the triad predicts *blowing-up Q-value/TD-error magnitudes* with flat episode length.

### Q4. Anything suspicious about the metric itself?

Possibly. **An 80% capture rate at the *start* of training is unusual** — deterministic greedy eval of a barely-trained checkpoint should be *low*, not high. Before fully attributing the curve to the reward, sanity-check the just-changed eval path (commit `4142e1e`): confirm ε is actually 0 in eval, and that checkpoint loading/indexing isn't pairing the "early frame" x-axis with a late/mislabeled checkpoint. This is cheap to rule out and the unusual starting value warrants it.

---

## Recommendations summary

Priority-ordered; fixes #1–#3 are complementary (ship the cheap one now, land the durable one after).

1. **(HIGH) Gate `currently_visible` on progress — restore the V1 behavior.** Two-line change matching existing `CurrentGitTeamReward` code (`current.py:126-127`): only pay `currently_visible` when `visibility_progress` is true (ghost closing distance), instead of unconditionally at `current.py:372`. Cheapest decisive fix; also a clean A/B isolating gating-vs-weights.
2. **(HIGH) Make "total non-terminal shaping per episode" a design invariant capped well below `get_pacman`.** Budget cumulative shaping to ≤ ~0.25 × `get_pacman` (≤ +10 vs +40). With `max_steps=200` that forces any per-visible-step bonus below ~+0.05 or requires it to be self-limiting (potential-based / progress-gated). This kills the *class* of stalking bugs, not just this instance.
3. **(HIGH) Route guidance through the potential function and adopt the γ-discounted form `F = γΦ(s') − Φ(s)`** (`current.py:360` currently omits γ). Gives provable policy-invariance and removes the need for ad-hoc per-step bonuses. Do this for *correctness*; the missing-γ defect alone is **not** the regression driver, so don't expect it to reverse the curve by itself.
4. **(HIGH) Run discriminating diagnostics in the *same* run as the fix.** Log (a) mean episode length over training, (b) per-term reward decomposition (the `RewardResult.breakdown` already exists), (c) `get_pacman` frequency, and (d) a Q-value/TD-error magnitude trace. Confirms the stalking mechanism (episode length should drop and capture frequency rise after the fix) and excludes the deadly-triad alternative. Also verify the V1 (`current_git`) vs V2 (`current`) A/B.
5. **(MEDIUM) Sanity-check the eval harness for the "starts at 80%" anomaly** — confirm eval ε=0 and correct checkpoint↔frame pairing in the periodic capture-eval snapshot path (`run_benchmark.py`, commit `4142e1e`).
6. **(MEDIUM) Add time pressure only if diagnostics show residual stalking after #1–#3.** Prefer a modestly larger `timestep` penalty over inflating the −35 timeout (large terminal penalties add value-estimation variance that hurts DQN-family learners). Don't apply reflexively — over-correction risks a "rush-and-miss" policy.

---

## FOLLOW-UP (2026-06-26 13:05 UTC) — eval verification overturns the stalking hypothesis

> **REVISED.** The user chose "verify eval first" before changing the reward. Inspecting the actual eval CSVs from the running benchmark (`benchmarl_setup/runs/pinklike3/current/cpu/*/evaluation_report_live_capture.csv` and `live_progress.csvl`) **refuted the original reward-hacking-by-stalking diagnosis** above. The recommendations summary below supersedes the original for prioritization; the original is preserved for the record.

### Q5. Is the eval harness sound (ε=0, correct pairing)?

**Yes.** Episodes run under `with torch.no_grad(), set_exploration_type(ExplorationType.DETERMINISTIC)` (`eval_report.py:403`), with deterministic per-episode seeding (`_seed_episode`, line 201). Capture is greedy. The capture snapshot pairs the latest checkpoint with the latest frame monotonically (`run_benchmark.py:491-521`). **The eval-artifact hypothesis (Q4) is ruled out** — the decline is genuine greedy-policy behavior.

### Q6. What do the actual converged-policy eval numbers show?

Final-checkpoint (200k-frame) eval, aggregated across seeds:

| Algo | Capture | Mean return | Signature |
|---|---|---|---|
| iql | 0/5 | −144.6 | timeout=1.0, mean_steps=200 |
| vdn | 0/5 | −135.6 | timeout=1.0, mean_steps=200 |
| qmixlocal | 0/5 | −131.0 | timeout=1.0, mean_steps=200 |
| qmixglobal | 1/4 | −83.7 | one run captures (steps=61, return≈+30) |

Per-run diagnostics: `mean_shaping_return` ∈ [−132, −60], `frac_steps_visible` ∈ [0.0, 0.52] (mostly low), `timeout_rate` = 1.0, `mean_steps` = 200.

**This refutes stalking.** Reward-hacking `currently_visible (+0.6/visible step)` would produce *positive* shaping return and *high* visibility. Instead shaping is strongly **negative** and visibility low. The converged policy earns **−140 return** when a capturing episode yields **~+30** — RL converged to a far *worse* return than an available capturing policy. That is a **pursuit/learning failure**, not reward exploitation.

### Q7. Then where does the "80%→20% across frames" curve come from?

A plotting/aggregation effect, not within-training collapse. Capture is evaluated **only at the final checkpoint** (no intermediate checkpoints are written, so `live_progress.csvl` has real capture values only at frame 200000; all other rows are `nan`). `liveplot.py` `nanmean`s per-seed end-values across runs as they finish (`liveplot.py:210`). Early-finishing lucky seeds pull the mean to ~80%; it settles to ~20% as more (failing) seeds complete. True converged capture ≈ 0–25%.

### Q8. Revised root cause

The agents **never learn deliberate pursuit**; the greedy policy is a worse pursuer than early high-ε random exploration. During training, experience is collected with annealing ε (1.0→0.1 over 190k frames); early random ghost movement stumbles into the fleeing Pacman (captures enter the buffer), but the network never learns to corner a *defensive* Pacman (holds BFS distance ≥3, flees optimally — needs multi-ghost coordination). The dense reward is **dominated in practice by net-negative anti-oscillation/movement penalties (~−140/episode: `invalid_move` −0.08, `stay_still` −0.03, `repeated_direction_reversal` up to −0.2, `two_step_cycle` −0.08)** that punish the exploratory back-and-forth needed to corner a target, while the pursuit signal (potential shaping) **telescopes to ~0** and gives no net incentive to *end* closer. As ε anneals, the greedy policy's true ~0% pursuit ability surfaces — appearing as "unlearning." `research-000022`'s "ghosts stop and oscillate" is reinterpreted as penalty-avoidance thrashing, not deliberate stalking.

### Revised recommendations summary (supersedes the original for prioritization)

1. **(HIGH) Rebalance shaping to be net-positive toward pursuit.** The anti-oscillation/movement penalties sum to ~−140/episode and suppress cornering. Slash or remove `repeated_direction_reversal`, `two_step_cycle`, `stay_still`, `invalid_move`; make "getting closer / capture" the dominant *positive* signal.
2. **(HIGH) Strengthen the pursuit gradient.** Potential shaping telescopes to ~0 (no net incentive to end closer). Add a non-telescoping proximity/visibility reward or raise `potential_shaping_alpha`; the lone +40 terminal is too sparse against a fleeing target.
3. **(HIGH) Pinpoint the dominant penalty first.** Run `eval_report` on a final checkpoint and emit the already-accumulated `reward_breakdown` (`eval_report.py:242`, currently not written to CSV) to confirm whether `invalid_move`/reversal penalties own the −140. One-line change.
4. **(MEDIUM) Address exploration / task difficulty.** A defensive Pacman holding distance ≥3 may be near-unsolvable without coordination; consider a curriculum (slower/closer Pacman early), a higher ε floor, or a solvability check. Early-random 80% and the lone qmixglobal capture show the task *is* solvable.
5. **(LOW) Defer the original `currently_visible` un-gating fix** (original recs #1–#3). Theoretically valid (would cause stalking *once pursuit is learned*) but **not the current blocker** — the data shows `currently_visible` is barely earned at convergence.
