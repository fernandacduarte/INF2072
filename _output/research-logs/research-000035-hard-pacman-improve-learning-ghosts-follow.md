# Research 000035 | TB | 2026-06-29 18:00 UTC | Hard-Pacman: improve learning and make ghosts follow Pacman

tags: reinforcement-learning, reward-shaping, pursuit-evasion, experimental-validity, partial-observability

source: research-000035
spawned: research-000035, plan-000036

## User brief

> assuming hard pacman, how can we improve the learning and make the ghosts follow the pacman? we did not see this yet

## Agent interpretation

The user accepts `hard` Pacman as the target opponent (no longer debating the random-Pacman ceiling
of research-000033) and asks two coupled questions: (1) how to improve learning, and (2) how to make
the trained ghosts visibly **pursue/follow** Pacman — a behavior they have *not yet observed*. The
real problem is that "follow Pacman" is a **pursuit** objective, while the current setup reinforces a
**capture** objective that, against a near-perfect evader, almost never produces a reward — and the
shaping meant to drive pursuit (`capture_v0_pure_potential_shaping`, exact-telescoping PBRS) cancels
to ~zero in exactly the hard-evader regime. The answer therefore has to separate "reinforce pursuit"
from "achieve capture," and reframe the success metric from capture rate to pursuit quality.

## Files reviewed

- `custom_environment/env/rewards/current.py` — active branch reward `CaptureV0PurePotentialShaping`
  (line 782): pure PBRS, exact telescoping γ=1, `Φ = -0.7 * mean_dist` (lines 828-869); sparse
  terminals +100/-100; `timestep = -0.05`. Also `CaptureV0Reward` `pacman_legal_moves_reduced`
  containment term (line 499) and `CaptureV0SparseControl` (line 872).
- `custom_environment/env/domain/pacman_policy.py` — defense-first BFS evader; safety-first
  lexicographic key (lines 80-139); `pure_random` path (96-97).
- `custom_environment/env/domain/constant.py` — `PACMAN_SAFE_DISTANCE = 3` (line 66).
- `custom_environment/env/pacman_environment.py` — Pacman-moves-first (349-360), co-location capture
  `_is_capture_state` (883-886), bearing-to-last-sighting belief feature `_shared_memory_features`
  (734-780), curriculum stage recompute (201-225), `max_steps = 200` (134), `pacman_difficulty`
  default `hard` (85).
- `benchmarl_setup/run_pacman_benchmarl.py` — `lr=1e-4`, `gamma=0.99` (57-58); CLI knobs
  `--memory-size 10000`, `--optimizer-steps 10`, `--max-frames 60000` (81-90).
- `benchmarl_setup/algorithm_utils.py` — hardcoded epsilon floor `eps_end = 0.10` (line 106).
- `_output/plans/plan-000029.md` — in-flight evasiveness sweep + **scripted greedy-pursuit ghost
  ceiling** evaluator (the L1 diagnostic below is already being built).
- `_output/research-logs/research-000033`, `research-000032`, `research-000028` — prior structural
  ceiling, hyperparameter-frontier, and dose-response analyses.

---

## Q&A log

### Q1 (initial). Assuming hard Pacman, how can we improve the learning and make the ghosts follow Pacman? We have not seen following behavior yet.

**A1.**

**Bottom line:** "follow Pacman" is a *pursuit* objective. The current setup reinforces a *capture*
objective that almost never fires against a hard evader, while the shaping meant to drive pursuit
**telescopes to zero** in exactly that regime. The agent rationally learns to do nothing. To see
following: reinforce pursuit *persistently*, make capture *attainable* so it can anchor the behavior,
and *measure pursuit directly* rather than capture rate.

#### Why following has not emerged — the causal chain

1. **The capture reward almost never fires against hard Pacman.** Deterministic defense-first evader
   (`safe_distance=3`), Pacman moves first each step, co-location-only capture. Two equal-speed ghosts
   on a cyclic 20×20 maze cannot reliably *force* capture (research-000033 cop-number/endgame). So the
   `+100 GET_PACMAN` terminal rarely happens → pursuit is essentially never reinforced by capture.

2. **The shaping that should teach following telescopes to zero.** `capture_v0_pure_potential_shaping`
   uses exact telescoping (γ=1): `F = Φ(s') - Φ(s)`, `Φ = -0.7·mean_dist`. Summed over an episode this
   collapses to `Φ(end) - Φ(start)`, path-independent. Against an evader that holds distance roughly
   constant, net mean-distance change ≈ 0 → cumulative pursuit reward ≈ 0. The dominant remaining
   signal is `timestep = -0.05`/step plus the `-100` timeout. Net lesson: "I lose -100 regardless;
   minimize step cost" → passivity.

3. **Discount mismatch.** Ng–Harada–Russell invariance needs `F = γΦ(s') - Φ(s)` with the *learner's*
   γ (0.99); the shaping uses γ=1. So it is neither cleanly invariant nor a reliable behavior driver.
   γ=1 was chosen to stop in-place oscillation farming, trading that for net-zero pursuit pressure.

4. **Memoryless MLP under partial observability.** Once Pacman leaves the 11×11 view a feedforward net
   has no memory. An engineered belief substitute exists — relative bearing to last sighting
   (`_shared_memory_features`) — but a memoryless net on a stale bearing tracks weakly, and before the
   first sighting the bearing is neutral (no direction to pursue).

5. **Substrate weaknesses (research-000032).** Replay buffer 10k, UTD ≈6.4, epsilon floor 0.10
   (≈19% chance some ghost acts randomly every step at convergence — corrupts greedy pursuit), 60k
   frames likely undertrained.

#### The conceptual reframe

Against a near-perfect evader, capture rate is the wrong success metric and the wrong training signal.
Reward pursuit *persistently* and measure it directly: mean distance-to-Pacman, % steps Pacman is
visible/contained, time-to-first-contact. Capture rate becomes secondary, meaningful only once capture
is mechanically attainable.

#### Ranked levers

- **L1 (HIGH, diagnostic, low cost — already in-flight):** Add pursuit metrics to eval and run the
  **scripted greedy-pursuit ghost ceiling vs hard Pacman** (plan-000029). Decides (a) whether *any*
  policy can capture hard Pacman, and (b) whether the trained ghosts already follow but cannot close.
- **L2 (HIGH):** Replace/augment with a **persistent (non-telescoping) closing reward** — reward
  per-step *decrease* in team min-BFS distance (clipped), plus the existing `pacman_legal_moves_reduced`
  containment term. Non-telescoping, so it does not cancel; this is what makes following visibly emerge.
  Reward *closing*, not *sitting at* a fixed distance, to avoid the RC4 orbit hack (research-000022).
- **L3 (HIGH):** Make capture attainable so `+100` can anchor pursuit: adjacency capture (Manhattan ≤ 1
  after moves resolve) cheapest/highest-impact; or 3rd ghost (`pinklike3` exists); or lower
  `PACMAN_SAFE_DISTANCE`. Re-baseline after any rule change; never mix pre/post-change capture rates.
- **L4 (MEDIUM-HIGH):** Use easy→hard **curriculum to bootstrap pursuit** — learn to chase a weak/random
  Pacman first (where chasing→capture→+100 closes the loop), then anneal to hard; following transfers.
  Fix the in-eval stage-promotion confound (research-000033 R2) so measurement is clean.
- **L5 (MEDIUM):** Fix substrate HPs (research-000032): buffer 10k→100–500k, optimizer-steps 10→1–4,
  epsilon floor 0.10→0.05, frames 60k→150–300k. All but the epsilon floor are already CLI flags.
- **L6 (MEDIUM, high cost):** Add recurrence (GRU) or verify the bearing channel — the real POMDP lever
  so following can be represented when Pacman is out of view.

#### Recommended sequence

1. (free) Add pursuit metrics + run scripted-pursuit ceiling vs hard Pacman (L1 / plan-000029).
2. If capture structurally impossible → redefine success as pursuit quality + persistent closing reward
   (L2). If attainable → adjacency capture / 3rd ghost (L3).
3. In parallel, fix cheap substrate HPs (L5) and bootstrap with curriculum (L4).
4. If following still cannot be represented out-of-view → add recurrence (L6).

The single biggest unlock: the current reward gives **zero net pursuit pressure against an evader**
while the capture anchor never fires, so the agent rationally does nothing. Fix either side — a
persistent pursuit reward *or* attainable capture — and following should appear.

---

## Recommendations summary

| # | Priority | Recommendation |
|---|----------|----------------|
| R1 | HIGH | **Add pursuit metrics and run the scripted greedy-pursuit ghost ceiling vs hard Pacman** (plan-000029) before retraining. Decides whether capture is attainable and whether ghosts already follow but cannot close. |
| R2 | HIGH | **Switch from exact-telescoping PBRS to a persistent (non-telescoping) closing reward** (reward per-step decrease in team min-BFS distance, clipped) + reuse `pacman_legal_moves_reduced` containment. Reward closing, not orbiting (RC4). This is what makes following emerge against an evader. |
| R3 | HIGH | **Make capture attainable** so `+100` anchors pursuit: adjacency capture (Manhattan ≤ 1) cheapest; or 3rd ghost (`pinklike3`); or lower `PACMAN_SAFE_DISTANCE`. Re-baseline after the rule change. |
| R4 | MEDIUM | **Bootstrap pursuit with the easy→hard curriculum** and fix the in-eval stage-promotion confound (research-000033 R2). |
| R5 | MEDIUM | **Fix substrate HPs** (research-000032): buffer 10k→100–500k, optimizer-steps 10→1–4, epsilon floor 0.10→0.05, frames 60k→150–300k. |
| R6 | MEDIUM | **Reframe the success metric to pursuit quality** (mean distance, % steps contained/visible, time-to-contact); treat capture rate as secondary against a near-perfect evader. |
| R7 | LOW | **Add recurrence (GRU)** or validate the bearing channel as the real POMDP lever for tracking Pacman out of view. |

## Sources

- Ng, Harada & Russell (1999), *Policy invariance under reward transformations* — PBRS requires
  `F = γΦ(s') − Φ(s)` with the learner's γ for optimality preservation.
- `_output/research-logs/research-000033` — structural capture ceiling, capture-mechanics suppressors.
- `_output/research-logs/research-000032` — hyperparameter frontier, POMDP/recurrence wall.
- `_output/research-logs/research-000028` — evasive-Pacman dose-response + scripted-pursuit ceiling.
