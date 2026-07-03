# Research 000024 | fernanda-INF2072 | 2026-06-27 21:34 UTC | Deep eval of pinklike3 benchmark + reintroduce potential-based reward shaping
tags: reward-shaping, pbrs, marl, eval-behavior, experimental-design
spawned: plan-000025, plan-000031

## User Brief

> ive ran benchmark and when eval-latest the ghosts are not following pacman. We need to tune the reward system. im studiyng the potency reward shapping. lets think about reintroducing it. but first lets do a deep evaluation on last benchmark results

## Agent Interpretation

Two-part request. (1) **Deep-eval** the last benchmark on disk (`runs/pinklike3`) to explain *why* the trained ghosts do not pursue Pacman. (2) Decide whether and how to **reintroduce potential-based reward shaping (PBRS, "potency reward shaping")** to induce active pursuit. User clarified: the run is `pinklike3 / qmixglobal / seed 0`; the success signal is **active pursuit behavior** (ghosts visibly close distance, not just final capture rate); and the desired PBRS flavor is **pure, theoretically policy-invariant PBRS on the sparse `capture_v0` base**, kept clean for an academic report.

## Files Reviewed

- `custom_environment/env/rewards/current.py` — `CaptureV0ImproveLegalMovesIncreaseTerminalRewardsReverseAction` (604–684, active reward); `CaptureV0Reward` w/ commented-out PBRS (489–576); `CurrentTeamReward._team_distance` (437–458) + telescoping (354–364); `_bfs_distance` (281–304)
- `custom_environment/env/rewards/base.py` — `RewardContext`, `RewardTerm`, `RewardResult`
- `custom_environment/env/rewards/loader.py`, `__init__.py` — strategy registry / loading
- `custom_environment/env/pacman_environment.py` — `RewardContext` construction (810–820): `pacman_position` is the **true** position; `pacman_visible` is separate
- `custom_environment/env/domain/constant.py` — `PACMAN_SAFE_DISTANCE = 3` (already reduced from 5)
- `benchmarl_setup/run_pacman_benchmarl.py` — `gamma = 0.99`
- `benchmarl_setup/runs/pinklike3/` — `benchmark_summary.csv`, `evaluation_report_live_capture[_by_variant].csv`, `live_progress.csvl`
- `Makefile` — `REWARD_ID`, `MAZE=pinklike3`, `CURRICULUM=easy-medium-hard`
- `_output/research-logs/research-000022-eval-ghosts-stop-pacman-oscillates.md` — prior root-cause analysis

---

## Q&A Log

### Q1: Why don't the trained ghosts follow Pacman in the pinklike3 benchmark, and should we reintroduce potential-based reward shaping?

**Short answer:** The ghosts don't pursue because **the reward gives them almost no signal that points toward Pacman**. The active reward (`capture_v0_improve_legal_moves_increase_terminal_rewards_reverse_action`) is sparse: a +100 capture terminal that fires only 36% of the time, plus two dense terms that are either near-zero (`pacman_legal_moves_delta`, mean **+0.0018/step**, and only when Pacman is visible — 16% of steps) or actively *anti-pursuit* (`reverse_action`, mean **−0.056/step**). With Pacman invisible 84% of the time and a maze that requires reversing at junctions to chase, the agents have no per-step gradient telling them to close distance. The training capture curve is **flat at ~26–36% across all 100k frames** — QMIX plateaued at a wandering/cornering policy, not a pursuit policy. **Reintroducing PBRS is the correct fix**: a distance potential `Φ = −α·(team BFS distance to Pacman)` supplies a dense, every-step signal (computed from the simulator's true Pacman position — privileged training-time info, fully legitimate under CTDE) that is exactly what the sparse reward lacks. Three conditions make it "pure" and report-defensible: (a) include the **γ factor** the current telescoping omits, (b) handle **terminal vs. timeout** potentials correctly, and (c) **drop the `reverse_action` penalty**, which is non-potential and contradicts both invariance and pursuit.

---

### Part 1 — Deep evaluation of `pinklike3`

#### 1.1 What was actually run

| Dimension | Value |
|---|---|
| Maze | `pinklike3` |
| Algorithm | `qmixglobal` (QMIX, global state) |
| Seeds | **1** (seed 0 only) |
| Frames | 100,000 |
| Curriculum | `easy-medium-hard` (pacman policy difficulty ramp over 100k frames) |
| Reward | `CaptureV0ImproveLegalMovesIncreaseTerminalRewardsReverseAction` |
| γ (discount) | 0.99 |

The active reward terms (current.py:604–684): `GET_PACMAN +100` (terminal), `PACMAN_TIMEOUT_WIN −100`, `PACMAN_WIN_PALLETS −100`, `timestep −0.01`, `pacman_legal_moves_delta = 0.2·(prev_legal − curr_legal)` **only when Pacman visible**, `reverse_action = −0.02` per ghost direction reversal. **No distance/potential shaping** — the PBRS code is commented out (current.py:489–496, 520–576).

#### 1.2 Eval results (100 episodes, checkpoint @100k)

| Metric | Value | Reading |
|---|---|---|
| capture_rate | **0.36** | ghosts win only ~1/3 of episodes |
| timeout_rate | **0.64** | Pacman survives the clock most of the time |
| pellet_win_rate | 0.00 | Pacman never wins by pellets — it's running, not eating |
| mean_steps_to_capture | ~100 | captures are slow when they happen |
| frac_steps_visible | **0.16** | Pacman is in ghost view only 16% of steps |
| mean_episode_return | −38.9 | dominated by the −100 timeouts |
| mean_newly_spotted_count | 0.0 | artifact — this reward never emits `newly_spotted` |

Per-step reward breakdown (mean): `GET_PACMAN +1.55`, `PACMAN_TIMEOUT_WIN −0.50`, `pacman_legal_moves_delta +0.0018`, `reverse_action −0.056`, `timestep −0.010`.

#### 1.3 Training curve

From `live_progress.csvl`: the eval capture-% samples are essentially **flat** — 29% at 5k frames, 26% at 40k, 36% at 100k — with `reward_mean` just bouncing between ~−0.55 (timeout windows) and ~+0.5/+1.5 (lucky-capture windows). There is **no learning trend**: the policy reached a baseline early and never improved. That is the fingerprint of an under-specified (signal-starved) reward, not of an under-trained run.

#### 1.4 Root causes (why no pursuit)

| # | Root cause | Evidence | Severity |
|---|---|---|---|
| RC1 | **No distance gradient.** No reward term increases as ghosts get closer to Pacman. | PBRS commented out; breakdown has no distance term | **Critical** |
| RC2 | **The one dense "approach" term fires 16% of the time and is ~0.** `pacman_legal_moves_delta` is visible-gated and averaged +0.0018/step. | frac_steps_visible=0.16; breakdown +0.0018 | High |
| RC3 | **The dominant dense signal is *anti*-pursuit.** `reverse_action −0.02` averaged −0.056/step — ~30× the legal-moves term — penalizing exactly the junction reversals a maze chase requires. | breakdown −0.056 | High |
| RC4 | **Sparse +100 terminal is too rare to bootstrap.** Reached 36% of episodes; with 84% partial-observability QMIX can't propagate it into a pursuit policy. | flat training curve | High |
| RC5 | **Single seed ⇒ not a benchmark.** Constitution Q3 / §10 require ≥5 seeds; nan std everywhere. | benchmark_summary has 1 row | Medium (validity) |

Note RC1–RC4 are reward-design causes (fixable now); they are distinct from research-000022's findings, several of which were already applied (`PACMAN_SAFE_DISTANCE` is now 3, anti-oscillation, etc.). The previous run's "stale checkpoint" issue does **not** apply here — this checkpoint *was* trained on the active reward; the reward itself is the limiter.

---

### Part 2 — Reintroducing potential-based reward shaping (PBRS)

**Verdict: do it.** PBRS directly targets the signal-density gap (RC1/RC2/RC4) and there is a working implementation already in the file. To keep it "pure" (policy-invariant, report-defensible), three corrections are required over the legacy code. The expert review (research-reviewer, 5 perspectives) concurs and adds the theory caveats below.

#### 2.1 The mechanism

Reuse `CurrentTeamReward._team_distance` (current.py:437–458): `Φ(s) = −α·(d1 + 0.5·d2)`, where `d1,d2` are the BFS distances of the two nearest ghosts to Pacman. Per Ng/Harada/Russell (1999), add the telescoping shaping term:

```
F(s, s') = γ·Φ(s') − Φ(s)
```

This **provably does not change the optimal policy** — it only reshapes *where* reward lands in time, accelerating credit assignment. That is precisely the property you want to advertise in the report.

#### 2.2 Three corrections vs. the legacy code

1. **Add the γ factor.** The legacy telescoping (current.py:357–364) computes `potential − last_potential`, i.e. γ=1. With γ=0.99 that is **not** the Ng-1999 form and is not policy-invariant. Fix: `F = w.gamma * potential − self._last_potential` (γ=0.99). One line; it is the single change that makes "pure PBRS" a true claim.
2. **Terminal vs. truncation potentials.**
   - *Capture (true terminal):* BFS=0 ⇒ Φ=0 naturally; the final transition emits `γ·0 − Φ(s) = +α·dist_before` — a desirable "you closed the gap" pulse. Verify the capture step actually runs `compute`.
   - *Timeout (truncation, not termination):* do **not** zero Φ — that injects a spurious `−Φ(s)` penalty into the 64%-timeout regime. Treat timeout as time-limit truncation (bootstrap), letting Φ carry its real value.
3. **Drop `reverse_action`.** It is action/history-based (not a state potential), so it *re-breaks* invariance, and it penalizes legitimate maze-chase reversals. PBRS already discourages useless oscillation for free: A→B→A nets zero potential change but costs two `timestep` ticks. Keep the variant strictly: `sparse terminals + timestep + PBRS`.

#### 2.3 Magnitude / α

With `timestep −0.01` and terminal ±100, target a per-step PBRS magnitude that *guides without drowning*: a one-tile distance change should yield `F ≈ α` (order 0.1–1.0). The legacy weights used α=0.5 (`CurrentRewardWeights`) and 1.2 (V2). **Start at α≈0.5–0.9**, then sanity-check the logged per-term breakdown so mean |PBRS/step| sits well above the 0.01 timestep cost and well below the terminal. Keep the `d1 + 0.5·d2` team form (not `min`): it keeps a secondary pull on the second ghost, encouraging the pincer/coordination behavior that is the project's actual thesis — and guards against the "lazy second agent" failure mode. Ablate `min` vs `d1+0.5·d2` to back the coordination claim empirically.

#### 2.4 Privileged information — methodological framing

`_bfs_distance` reads `context.pacman_position` (the true position, pacman_environment.py:818) regardless of visibility. This is **legitimate and standard** for Centralized-Training/Decentralized-Execution: the privileged true position is a *training-time reward signal only*; the ghost **policies still observe only their partial 11×11 local view** and use no privileged info at execution. State it that way explicitly in the report to pre-empt a "the ghosts cheat" critique. PBRS theory explicitly permits an oracle potential, including under partial observability, because shaping changes the reward, not the policy's observation.

#### 2.5 Experimental design to prove it helps

Because PBRS is *policy-invariant by construction*, the claim is **not** "higher asymptotic capture rate" — it is **"PBRS accelerates acquisition of pursuit behavior" (sample efficiency)**. Design:

- Two arms, identical hyperparameters: **A** = `capture_v0` sparse (no shaping); **B** = `capture_v0 + γΦ PBRS`.
- **≥5 seeds each** (0–4), per constitution Q3.
- Report mean±std on: `capture_rate`, `mean_steps_to_capture`, **and a pursuit-specific metric** capture_rate cannot show — e.g. *fraction of steps where team BFS-distance decreases*, or *mean Δ(team_distance)/step while Pacman is visible*. Headline the learning-speed metric (area-under-training-curve or steps-to-threshold), not the final number.

---

## Recommendations Summary

**R1 (HIGH) — Reintroduce pure PBRS on the `capture_v0` sparse base.** New reward variant = sparse terminals (+100 / −100 / −100) + `timestep −0.01` + telescoping `F = γΦ(s′) − Φ(s)` with `Φ = −α·(d1 + 0.5·d2)` (reuse `_team_distance`). Targets the critical no-distance-gradient root cause. *(decision)*

**R2 (HIGH) — Include the γ factor.** Implement `F = gamma * potential − last_potential` (γ=0.99). Without it the shaping is not the Ng-1999 form and the "policy-invariant" report claim is false. *(decision)*

**R3 (HIGH) — Drop `reverse_action` (and any non-potential term) from this variant.** It breaks invariance and punishes legitimate maze pursuit; PBRS already suppresses dithering. *(decision)*

**R4 (HIGH) — Handle terminal vs. timeout potentials.** Φ=0 at capture (verify the capture transition emits the `+α·dist` pulse); do **not** zero Φ at timeout (truncation/bootstrap). Add a unit test for both cases. *(decision)*

**R5 (HIGH) — Run a ≥5-seed A/B (sparse vs sparse+PBRS) before any conclusion.** Single-seed `pinklike3` cannot support a causal claim (constitution Q3). Frame the hypothesis as sample-efficiency, and report a pursuit-specific metric (fraction of steps closing distance), not just capture_rate.

**R6 (MEDIUM) — Tune and document α (start 0.5–0.9); ablate `d1+0.5·d2` vs `min`-distance** to substantiate the coordination thesis and avoid the lazy-second-ghost pattern.

**R7 (LOW) — Consolidate reward code.** Delete the dead commented-out PBRS blocks (current.py:489–576); ensure the active variant contains exactly the terms claimed in the report, with α/γ as named documented weights.

---

## Follow-up — 2026-06-28 | PBRS reward-farming loophole found in eval

### Q2: After training `capture_v0_pure_potential_shaping`, eval shows ghosts moving in circles even with Pacman visible. Why?

**Short answer:** The γ-correct PBRS I shipped (R1–R4) had a **reward-farming loophole** that the policy learned to exploit. I ran a headless 80-step eval (`--render-mode ascii --ascii-step-json`) on the latest PBRS checkpoint (`b1eedebe`, 3 ghosts). Findings:

- **No capture in 80 steps, yet Pacman was visible 60/80 (75%)** and sat *stationary* 3 cells from ghost_3 for 40+ steps. Ghosts never closed in.
- **Every ghost collapsed to a 2-cell oscillation** (ghost_1: (7,1)↔(7,2) 40/40; ghost_3: (8,12)↔(9,12) 38/36).
- ghost_3's up/down cycle yielded `potential_shaping` of **−1.995 then +2.184** repeatedly → **+0.19 net per cycle**. Cumulative `potential_shaping = +17.50` over 80 steps with **zero captures** (×3 ghosts = the +50 episode reward).

**Root cause (two compounding bugs in the shipped variant):**
1. **Discounted telescoping subsidizes camping.** With `F = γΦ(s′) − Φ(s)`, γ=0.99, and `Φ = −α·dist ≤ 0`, a round trip nets `(1−γ)·(−Φ) > 0`. The γ factor added for "policy invariance" *created* a per-cycle camping subsidy because Φ is always negative.
2. **`d1 + 0.5·d2` (two nearest ghosts) is discontinuous.** As ghosts bob, the nearest-ghost identity swaps, producing large non-cancelling per-step potential swings (±2) instead of clean telescoping.

Capturing would *end* the lucrative shaping stream and is hard against an evading hard-mode Pacman, so the greedy policy settled on a **herd-and-camp** local optimum. This is the PBRS truncation / non-zero-potential farming pathology (research-reviewer's caveat) made concrete; more training exploits it *more*.

**Fix shipped** (commit `256b761`): exact **γ=1 telescoping** `F = Φ(s′) − Φ(s)` over the smooth **min** ghost distance (`_minimum_distance`). With γ=1 the cumulative shaping = `Φ(end) − Φ(start)` is path-independent, so any in-place oscillation nets exactly 0; min-distance removes the nearest-pair discontinuity; `timestep` strengthened to **−0.05** so camping is strictly negative. **Verified:** an 80-step camp now nets **−3.30** (was +50.1). Regression test `test_pure_pbrs_in_place_oscillation_cannot_be_farmed` added. This supersedes R2 (the γ factor) and the `d1+0.5·d2` choice from R1/R6.

### Follow-up Recommendations Summary

**FR1 (HIGH) — Retrain with the fixed reward.** The fix only affects new runs; the `b1eedebe`/`a04cc3d7` checkpoints carry the farmed policy. Retrain `capture_v0_pure_potential_shaping` (≥300k frames) and re-eval.
**FR2 (HIGH, supersedes R2/R1-metric) — Use γ=1 exact telescoping over min-distance.** Done in `256b761`. The discounted form is unsafe here because `Φ ≤ 0`.
**FR3 (MEDIUM) — Treat timeout as truncation/bootstrap.** The env reports timeout as `terminations=True` (plan-000025 deferred concern); bootstrapping would further discourage banking shaping over capture. Still open.
**FR4 (MEDIUM, reaffirms earlier) — Add a *relative* bearing to last-seen Pacman to the ghost observation.** Even farm-proof, the actor cannot pursue an unseen Pacman from its absolute coordinate alone. Still the key lever for off-screen pursuit. Still open.
