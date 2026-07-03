# Research 000033 | TB | 2026-06-29 14:57 UTC | Random-Pacman win-rate ceiling at 40%

tags: reinforcement-learning, experimental-validity, environment-mechanics, evaluation, pursuit-evasion

## User brief

> seems like we are stuck on reward shaping. liveplot shows a 40% ceiling on win rate for a totally random pacman on curriculum learning. for a random pacman the capture rate should be 100%.

## Agent interpretation

The user reads the liveplot "True Capture Rate" plateau (~40%) against what they expect for the
*positive control* — a fully random Pacman, which they assume the ghosts should catch ~100% of the
time — and concludes the blocker is reward shaping. The real question is **diagnostic, not
prescriptive**: *is 40% a learning/reward failure, or is it close to the structural capture ceiling
of this environment configuration (2 equal-speed ghosts, co-location-only capture, 200-step horizon,
cyclic 20×20 maze)?* The premise "random ⇒ ~100%" is itself an unverified prior. The answer
determines whether reward/hyperparameter tuning is the right lever at all.

## Files reviewed

- `custom_environment/env/pacman_environment.py` — `step` (move order, line 330-374), `_execute_action`/capture detection (620-664), `_is_capture_state` (883-886), curriculum stage recompute (200-236), `max_steps = 200` (134).
- `custom_environment/env/domain/pacman_policy.py` — defense-first BFS policy; `pure_random` easy-stage path (96-97).
- `custom_environment/eval_report.py` — `capture_rate = captures/count` (416), `ghost_win_rate` alias (435), keeps checkpoint-defined difficulty, `--max-steps` default 200 (969).
- `benchmarl_setup/run_benchmark.py` — live capture snapshot; `curriculum_frame_offset = checkpoint_frame` (525); `capture_pct` from eval CSV (468-478).
- `benchmarl_setup/liveplot.py` — "True Capture Rate" (`capture_pct_live_eval`) vs "Estimated Capture Rate" (648-656).
- `custom_environment/utils.py` — maze layouts; default = 2 ghosts, pinklike = 4, pinklike3 = 3; 20×20 cyclic grids.
- `_output/research-logs/research-000028-evasive-pacman-benchmark-protocol.md` — R2 (scripted-pursuit ceiling) and R4 (seed-pin `_pacman_rng`) already specified, never built.

---

## Q&A log

### Q1 (initial). We seem stuck on reward shaping — liveplot shows a 40% ceiling on win rate for a totally random Pacman under curriculum learning, but a random Pacman should be caught ~100% of the time. What's going on?

**A1.**

**Headline: this is almost certainly not a reward-shaping problem.** The 40% plateau is most
plausibly explained by the environment's capture *mechanics* and a measurement *confound*, not by
the reward function or the learner. Reward shaping cannot push capture above the mechanical ceiling,
so tuning it now is premature.

#### 1. The premise "random ⇒ ~100%" is an unverified prior

Nothing in the codebase establishes 100% as the achievable ceiling for 2 equal-speed ghosts vs.
random Pacman under co-location capture and a 200-step horizon. Pursuit-evasion theory says that on
**any finite grid, 2 equal-speed cops are necessary and sufficient** to catch even an *optimally
evading* robber (Maamoun & Meyniel) — but with two important caveats for your case: (a) that
guarantee is over an *unbounded* horizon with *optimal* pursuit, not 200 steps of learned/random
pursuit; and (b) graphs with many cycles (girth ≥ 5, min-degree ≥ 3) commonly have cop-number ≥ 3, so
a heavily-looped 20×20 Pac-Man maze may need 3 pursuers against an *optimal* evader. A *random*
Pacman is easier than the worst case — so 2 ghosts catch it more often than the cop-number bound —
but "more often than worst case" is not "100%." A 40–60% capture rate for random Pacman with 2
ghosts, co-location capture, and a finite horizon is entirely plausible as a near-structural number.

#### 2. Three structural suppressors in the capture mechanics (none are reward)

1. **Co-location-only capture + Pacman resolves first.** Each step Pacman moves *first*
   (`pacman_environment.py:349-360`), using the ghosts' *current* positions to flee, while the
   ghosts execute actions they committed from the *previous* observation. Capture is registered only
   when a ghost lands *on Pacman's cell* (or vice-versa, or same-cell at step end —
   `_is_capture_state`, 883-886). The classic cop-number endgame — "corner the robber, then step onto
   it" — therefore never closes: the instant a ghost is adjacent and about to pounce, Pacman has
   already vacated. **"Adjacent and cornering" degrades to a near-miss.** This "flee the cornered
   cell" timing is the *dominant* suppressor.
2. **Narrow swap loophole (smaller than first feared).** Because Pacman resolves first and moving
   *into* a ghost's standing cell fires a capture (line 652), head-on collisions *are* caught. The
   residual loophole is only the moving-target edge swap where a ghost steps into the cell Pacman
   *just vacated* on the same edge — a smaller effect than a general pass-through.
3. **Finite 200-step horizon + only 2 ghosts on a cyclic maze** (`max_steps = 200`). Even
   theoretically-sufficient strategies need time to close; imperfect/random pursuit + the broken
   endgame ⇒ most episodes time out, which is counted as a loss (`timeout_happened`, line 394).

#### 3. A measurement confound makes the 40% number itself partly an artifact

The liveplot "True Capture Rate" comes from a periodic eval whose Pacman difficulty **ramps with the
checkpoint frame**: `curriculum_frame_offset = checkpoint_frame` (`run_benchmark.py:525`). Worse, the
curriculum stage is recomputed **every step** from `pacman_curriculum_frame_offset +
_curriculum_global_step` (`pacman_environment.py:204-217`). So during a *late-checkpoint* eval, the
offset is large and `_curriculum_global_step` keeps accumulating *within* the eval episode — meaning
`_curriculum_progress()` can cross 1/3 (or 2/3) and **silently promote Pacman from "easy/random" to
"medium" (noise 0.30, safe_distance 2) or "hard" mid-episode**. Your "random positive control" may
not be running pure-random for the whole episode at all. Separately, `_pacman_rng` is seeded from OS
entropy and not reseeded per training seed (research-000028 R4), so the eval opponent is not
reproducible run-to-run — extra variance on the 40%.

Net: the 40% is contaminated as a control and cannot yet be interpreted as either "structural
ceiling" or "learning failure."

#### 4. The decisive, cheapest diagnostic — do this before touching reward or hyperparameters

Build the **scripted greedy-pursuit ghost ceiling** that research-000028 R2 already prescribed (grep
confirms it was never built). Hard-code each ghost to step along its BFS-shortest path toward
Pacman's current cell, run 200–500 eval episodes vs. `pure_random` Pacman on the default 2-ghost
maze, no training. Decision rule:

- Scripted ghosts also cap ~40–60% ⇒ **capture mechanics are the bottleneck**, the "random ⇒ 100%"
  premise is false, and reward shaping is the wrong lever.
- Scripted ghosts hit ~90%+ but learned ghosts stall at 40% ⇒ **learners are leaving capture on the
  table** and reward/learning work is justified.

This converts the whole debate into one cheap experiment (≈1–2 h to write, minutes of CPU) and
pre-empts the examiner's first question. Pair it with a **near-miss counter** (log per step whether a
ghost was Manhattan-distance 1 from Pacman at step start and whether that converted to a capture) to
measure the capture-rule suppression directly rather than arguing it.

#### 5. If — and only if — you confirm the ceiling is genuinely below target, ranked remedies

By capture-rate impact per unit of methodological cost:

1. **Relax capture to adjacency (+ edge-swap) capture (HIGH impact, low cost).** Register capture
   when a ghost is Manhattan-distance ≤ 1 from Pacman *after* moves resolve. This directly defeats
   the "flee the cornered cell" dynamic — the dominant suppressor. A few lines in `_is_capture_state`.
   Caveat: it changes the task definition, so report it as a deliberate rule revision (decision
   entry), re-baseline all algorithms under the new rule, and never mix pre/post-change capture rates
   in one figure.
2. **Give ghosts a speed advantage (HIGH impact, medium cost).** A faster pursuer beats an
   equal-speed evader on most connected graphs — the most theoretically guaranteed route to ~100%,
   but the largest change to the environment's identity and to comparison validity.
3. **Add a 3rd/4th ghost (MEDIUM-HIGH impact, low config cost — `pinklike3`/`pinklike` already
   exist).** If the maze's cop-number is 3, going 2→3 is the *theoretically correct* fix. Caveat:
   raises the MARL coordination/credit-assignment burden, which can *lower* learned capture even as
   the structural ceiling rises — so measure the scripted ceiling on the same maze.
4. **Simpler / less-cyclic maze (MEDIUM impact, medium cost).** Fewer cycles lowers cop-number and
   removes the loops a random evader exploits; but changes the benchmark task and the Pac-Man
   identity.
5. **Longer horizon (LOW impact as a remedy, useful as a diagnostic).** Helps only if captures are
   *slow* rather than *prevented*. On a cyclic equal-speed graph, more steps give diminishing
   returns. Best used to *test* structurality (does capture% rise with horizon?), not to fix it.

#### 6. Trade-offs to hold in mind

- **Capture-rule realism vs. benchmark comparability:** any rule change (remedy 1) invalidates
  comparisons gathered under the old rule. Make the change once, atomically, re-baseline, document.
- **Structural ceiling vs. learning difficulty:** every change that raises the structural ceiling
  (more/faster ghosts) also raises coordination difficulty, so report the normalized
  `learned / scripted` ratio (research-000028 R2) to avoid conflating the two.
- **Clean control vs. effort:** the in-eval curriculum promotion (§3) means the cheapest reading
  ("40% = random ceiling") is currently unsafe; fix the control before concluding either way.

---

## Recommendations summary

| # | Priority | Recommendation |
|---|----------|----------------|
| R1 | HIGH | **Build the scripted greedy-pursuit ghost ceiling (research-000028 R2)** and run it vs. `pure_random` Pacman on the 2-ghost maze **before** touching reward or hyperparameters. Decision rule: scripted ~40–60% ⇒ mechanics-bound (reward is wrong lever); scripted ~90%+ ⇒ learning-bound. Cheapest decisive diagnostic. |
| R2 | HIGH | **Fix the in-eval curriculum-promotion confound** so the "random" control is pure-random end-to-end: freeze the curriculum stage at episode start, or run controls with `pacman_curriculum=off` and difficulty pinned. Until fixed, the 40% is a contaminated control. |
| R3 | HIGH | **Instrument a near-miss counter** in eval (adjacent-at-step-start → capture vs. escape) to measure the capture-rule suppression directly and separate "rule" (ARCH) from "learning" (TEST) as the cause. |
| R4 | MEDIUM | **Seed-pin `_pacman_rng`** in `reset()` (research-000028 R4; one line) so the control is reproducible per training seed (constitution T4). |
| R5 | LOW | **Defer reward-shaping / hyperparameter work until R1 returns** — it is the most expensive lever (full retraining, multi-seed) and only justified if the scripted ceiling is high. |
| Remedy ranking (conditional on R1 showing a real gap) | — | (1) adjacency + edge-swap capture, (2) ghost speed advantage, (3) add a ghost, (4) simpler maze, (5) longer horizon. |

**Bottom line:** the hypothesis that 40% is near-structural rather than a reward failure is the more
probable explanation and is well-grounded, but it is **not yet measured**. Do not present 40% as "the
random-Pacman ceiling" — fix the control (R2), build the scripted ceiling (R1), instrument near-misses
(R3); then the number becomes evidence instead of an anecdote, and you'll know whether reward shaping
was ever the right place to look.

## Sources

- [Cops and robber on grids and tori (arXiv:1708.08255)](https://arxiv.org/pdf/1708.08255)
- [Catching a fast robber on the grid (arXiv:1609.01002)](https://arxiv.org/pdf/1609.01002)
- [Pursuit-Evasion in Graphs: Zombies, Lazy Zombies and a Survivor (arXiv:2204.11926)](https://arxiv.org/pdf/2204.11926)
