# Research 000037 | TB | 2026-06-30 00:43 UTC | MARL benchmarking best practices (Papoudakis 2021)

tags: reinforcement-learning, benchmarking, evaluation, statistical-validity, reproducibility

## User brief

> boas práticas de benchmarking com o paper Papoudakis_2021.pdf

## Agent interpretation

Extract the benchmarking best practices established in Papoudakis, Christianos, Schäfer & Albrecht (2021), *"Benchmarking Multi-Agent Deep Reinforcement Learning Algorithms in Cooperative Tasks"* (NeurIPS 2021, Datasets & Benchmarks Track — the EPyMARL paper), and map each practice to the current state of this project's benchmarking pipeline (`benchmarl_setup/run_benchmark.py`, `summarize_benchmark_runs.py`, `custom_environment/eval_report.py`), flagging what is already aligned and what is missing. The project benchmarks IQL/VDN/QMIX on a custom cooperative-ghost Pacman environment — the same algorithm families and the same fully-cooperative, shared-reward setting the paper studies, so the paper is a near-perfect methodological reference.

## Files

- `Papoudakis_2021.pdf` (source paper, 33 pages — text extracted via pypdf)
- `benchmarl_setup/run_benchmark.py` (multi-seed orchestrator)
- `benchmarl_setup/summarize_benchmark_runs.py` (cross-seed aggregation)
- `custom_environment/eval_report.py`, `custom_environment/eval.py` (evaluation)
- `product-design/project/constitution.md` (Q1–Q3 quality principles)

---

## What the paper establishes (the benchmarking protocol)

Papoudakis et al. compare 9 MARL algorithms (IQL, IA2C, IPPO, MADDPG, COMA, MAA2C, MAPPO, VDN, QMIX) across 25 fully-cooperative tasks in 6 environments. The contribution that matters for us is **not** the algorithm ranking — it is the **evaluation protocol** they make explicit. The reproducible-benchmarking practices are:

1. **Fixed evaluation protocol, decoupled from training.** Evaluate at *constant timestep intervals* (41 evaluation points across training), and at each point run a *fixed number of evaluation episodes* (100) with the greedy/eval policy. Evaluation is separate from the noisy training-collection rollouts.

2. **Report two metrics, not one.**
   - **Maximum returns** — at the evaluation timestep with the highest mean return across seeds, report mean ± 95% CI (final-performance metric).
   - **Average returns** — mean over *all* evaluation points during training (captures *learning speed*, not just final quality). Reporting only the endpoint hides slow vs fast learners.

3. **≥5 random seeds, with uncertainty.** Every reported number is mean ± **95% confidence interval over 5 seeds**. No single-seed claims.

4. **Statistical significance testing.** Two-sided t-test (threshold 0.05) between the best algorithm and every other algorithm per task; algorithms not significantly different from the best are marked (asterisk). Prevents over-claiming from noise.

5. **Separate hyperparameter optimisation per algorithm.** Grid search run *per environment* on one representative task, 3 seeds per HP combination, selecting on max evaluation return; the winning config is then frozen and reused for all tasks/final runs. Final-evaluation seeds are disjoint from HP-search seeds. Using one algorithm's HPs for another is an unfair comparison.

6. **Fair sample budgets across algorithm classes.** On-policy algorithms get 10× the environment samples of off-policy ones, because off-policy reuses a replay buffer and is more sample-efficient. Fairness is measured in *environment samples*, not wall-clock.

7. **Parameter sharing is an explicit, reported axis.** Shared vs non-shared parameters materially changes returns, so they run and report *both*. Under sharing, agent identity is fed as a one-hot; varying obs/action sizes are zero-padded / masked.

8. **Normalised returns for cross-task aggregation.** To average across heterogeneous tasks, per-task min-max normalise returns to [0,1] before aggregating. Never average raw returns across tasks with different scales.

9. **Report the metric the algorithm optimises.** They report *returns* (what the loss optimises), not win-rate, noting higher returns ≠ higher win-rate. For SMAC they still report win-rate in an appendix "for completeness." Lesson: pick the optimised metric as primary, report the domain-intuitive metric alongside.

10. **Implementation details dominate — so pin and disclose them.** They cite that RL results swing on implementation details (reward standardisation, entropy reg, recurrent vs FC nets, network sizes), so EPyMARL exposes them as explicit config and the full hyperparameter tables are published. Reproducibility = exact config + code version + seeds disclosed.

11. **Disclose compute.** They report CPU model, cores, and total CPU-hours (138,916). Compute budget is part of a benchmark's honesty.

---

## Mapping to this project — aligned vs gaps

| # | Practice | Project status | Action |
|---|----------|----------------|--------|
| 3 | ≥5 seeds | **✓ Aligned** — `--seeds 0,1,2,3,4` default; constitution Q3 mandates ≥5 | Keep |
| 1 | Fixed eval, decoupled from training | **◐ Partial** — `eval_report.py`/`eval.py` exist, but the benchmark summary's capture% / reward come from *training-collection* series (`collection_reward_*`), not a fixed greedy-eval pass | Add a fixed N-episode greedy eval at the end (and at intervals) feeding the summary |
| 2 | Max **and** average returns | **◐ Partial** — summary has `best_*` (≈max) and `tail_mean_*` (last-window only). Missing the paper's *average-over-all-evals* learning-speed metric | Add area-under-curve / all-eval mean alongside tail mean |
| 4 | Mean ± 95% CI across seeds | **✗ Gap** — `summarize_benchmark_runs.py` aggregates **mean over runs only**; no std, no CI | Add std + 95% CI (t-dist, n=5) per algorithm |
| 4 | Significance testing | **✗ Gap** — no t-test between best and others | Add pairwise two-sided t-test, p<0.05, mark non-significant ties |
| 5 | Per-algorithm HP tuning + disjoint seeds | **✗ Gap** — algorithms appear to share default HPs; no documented grid search; risk of HP-search/eval seed overlap | Run a small per-algorithm grid on one Pacman config (3 seeds), freeze, reuse; reserve seeds 0–4 for eval only |
| 6 | Fair sample budget | **N/A (favourable)** — IQL, VDN, QMIX are all off-policy value-based, so the 10× rule does not apply; identical `--max-frames` is already fair | Note in report; revisit only if an on-policy algo (e.g. MAPPO) is added |
| 7 | Parameter sharing as reported axis | **✗ Gap / clarify** — sharing config not surfaced as a benchmark dimension | Document the sharing setting; if comparing, report both |
| 8 | Normalised returns for aggregation | **○ Not yet needed** — currently effectively one task | Adopt min-max normalisation if/when multiple mazes/configs are aggregated |
| 9 | Report optimised metric + domain metric | **✓ Largely aligned** — reports both episode return *and* capture % (capture % is our "win-rate") | Keep; label return as primary, capture% as the intuitive companion |
| 10 | Pin & disclose implementation details | **✓ Strong** — constitution T4 (seed via CLI), C1 (commit hash in papers); run dirs carry config | Ensure HP tables land in the report |
| 11 | Disclose compute | **✓ Aligned** — summary already records `duration`, `fps`, device; CPU/GPU split tooling exists | Keep; add total compute-hours to the final report |

`max-frames` default is 60000 — far below the paper's 2M–40M scale. That is fine for iteration, but final benchmark claims should use a budget large enough that learning curves have plateaued (per the max-return-at-best-eval-point logic), otherwise "max return" is just "wherever the short run happened to stop."

---

## Perspective synthesis

- **Statistical validity (primary):** The single biggest, lowest-effort win is reporting **mean ± 95% CI over the 5 seeds you already run** and a **two-sided t-test** to mark ties. You are paying the cost of 5 seeds but discarding the variance information — the aggregate collapses to a bare mean. *Pro:* turns existing data into defensible claims; *con:* with n=5 the t-CI is wide — but that honesty is the point and is exactly what the paper does.
- **Reproducibility:** Project is already strong here (constitution T4/C1, config in run dirs). The remaining gap is **disjoint HP-search vs evaluation seeds** and **publishing the HP table** — without these, "tuned" comparisons are not reproducible/fair.
- **Scientific rigor / fair comparison:** Per-algorithm HP tuning (#5) is the integrity item. Right now an unfavourable default could make VDN/QMIX look worse than IQL for reasons of tuning, not capability. Even a coarse 3-seed grid per algorithm removes that confound. The off-policy-only roster means the awkward 10×-budget rule does **not** bite you — a genuine simplification worth stating explicitly in the course report.
- **Evaluation methodology:** Decouple eval from training collection (#1). Capture% read off training rollouts is biased by exploration ε and replay staleness; a fixed greedy N=100-episode eval is the honest number and is what makes "capture rate" comparable across algorithms.

---

## Recommendations summary

1. **[HIGH] Report mean ± 95% CI across the 5 seeds** in `summarize_benchmark_runs.py` aggregate (currently mean-only). t-distribution CI, n=5. Lowest effort, highest credibility gain.
2. **[HIGH] Add pairwise significance testing** (two-sided t-test, p<0.05) between the best algorithm and each other, marking non-significant ties — so the course report cannot over-claim a winner.
3. **[HIGH] Decouple evaluation from training collection** — run a fixed greedy N-episode eval (e.g. 100) for the reported capture%/return, instead of reading training-collection series.
4. **[MEDIUM] Report both "max return" and "average-over-all-evaluations" return** (learning-speed metric), not just `tail_mean` and `best`.
5. **[MEDIUM] Per-algorithm hyperparameter tuning** with a coarse grid (3 seeds) on one Pacman config, frozen and reused; keep HP-search seeds disjoint from eval seeds 0–4; publish the HP table.
6. **[MEDIUM] Use a final-benchmark frame budget large enough to plateau** (current 60k is iteration-scale); document the budget and rationale.
7. **[LOW] Make parameter sharing an explicit, documented benchmark axis**; report the setting used (and both, if compared).
8. **[LOW] If aggregating across multiple mazes/configs, min-max normalise per task** before averaging.
9. **[LOW] State explicitly in the report that all three algorithms are off-policy**, so equal sample budgets are already a fair comparison (the paper's 10× rule does not apply).

## Q&A log

**Q1 (user):** boas práticas de benchmarking com o paper Papoudakis_2021.pdf

**A1 (agent):** Extracted the 11 benchmarking practices the EPyMARL paper makes explicit (fixed decoupled eval protocol; max + average returns; ≥5 seeds with 95% CI; significance testing; per-algorithm HP tuning with disjoint seeds; fair per-class sample budgets; parameter-sharing as a reported axis; normalised returns for cross-task aggregation; report the optimised metric alongside the domain metric; pin & disclose implementation details/HPs; disclose compute). Mapped each to this project: already aligned on ≥5 seeds, compute disclosure, implementation-detail discipline, and reporting both return and capture%. Key gaps: no cross-seed CI/std (aggregate is mean-only), no significance testing, eval read from training-collection rather than a fixed greedy pass, no per-algorithm HP tuning, and missing the average-over-all-evals learning-speed metric. The off-policy-only roster (IQL/VDN/QMIX) means the paper's 10× on-/off-policy budget rule does not apply — equal `--max-frames` is already fair. Top three actions are statistical: report mean ± 95% CI over the seeds already run, add a two-sided t-test to mark ties, and decouple evaluation from training collection.

---

### Follow-up (group chat — Sardinha/Fred/Andrey): seeds count, "last 10%", frames, epsilon

**Q2 (user):** Chat group raised: (a) seeds — we use 5/algorithm, ChatGPT suggested 30–50; (b) "médias são medidas a partir dos últimos 10%"; (c) number of steps/frames; (d) the ghost exploration epsilon — someone saw "1 → 0.05 linear"; what is a good value and how do we tune this slider?

**A2 (agent):**

- **Seeds (5 vs 30–50):** Both are defensible but measure different things. **5 + 95% CI is the citeable MARL-benchmark standard (Papoudakis; matches constitution Q3) — keep it.** ChatGPT's 30–50 is classical-statistics ideal (tighter CI, more t-test power) but infeasible at MARL compute cost and not what the RL literature practices. The modern reconciliation to cite: **Agarwal et al., NeurIPS 2021, "Deep RL at the Edge of the Statistical Precipice"** (`rliable`) — with few runs, don't chase seed count; report **robust interval estimates** (IQM + stratified-bootstrap CIs, performance profiles) instead of bare mean±std. Verdict: 5 is the floor, 10 a good middle if compute allows; the real fix is reporting the CI you currently discard (gap #1).

- **"últimos 10%":** Terminology caution — this is **not** Papoudakis's "average returns." The paper reports (i) **max returns** = best of 41 eval points, mean ± 95% CI (final perf), and (ii) **average returns** = mean over **all** 41 eval points (learning speed). The "last 10%" tail-average is a third, legitimate smoothing convention — exactly what the project's `tail_mean` already does — but label it correctly. Report the paper's two metrics; keep tail-mean as smoothing.

- **Frames:** Not transferable (paper uses 2M–40M, env-dependent). Principle: train until the learning curve plateaus, else "max return" is just where the short run stopped. Project's 60k is iteration-scale; for final benchmark, watch liveplot until capture-rate flattens and fix that budget across all final runs.

- **Epsilon — the exploration slider:** It is ε-greedy for the off-policy value-based algorithms (IQL/VDN/QMIX); ε = random-action prob during **training collection**; evaluation must be greedy (ε=0), which `eval_report.py:564` already enforces via `ExplorationType.DETERMINISTIC`. The "1 → 0.05 linear" is the PyMARL/EPyMARL default schedule. It's not one number but a 3-knob schedule. Current project values in `algorithm_utils.py:105-113`: `eps_init=1.0` (✓), `eps_end=0.10` (**high — consider 0.05/0.01**), `anneal_ratio=0.95` (**ε reaches floor only at 95% of training — too late; the near-greedy phase barely gets to converge**). The knob that matters is the anneal length, not the endpoints: anneal to the floor over **~30–50% of training** (`anneal_ratio ≈ 0.3–0.5`), leaving the back half near-greedy to converge. Tune by liveplot: capture-rate plateaus long before ε hits floor → anneal faster (lower ratio); never converges / stays noisy → anneal slower or lower the floor. Directly relevant to the research-000033/000035 capture-rate ceiling: a too-high end-of-training ε (0.10) or non-greedy eval would undertrain/understate the learned policy.

## Recommendations summary (follow-up)

10. **[MEDIUM] Lower `eps_end` to ~0.05 and `anneal_ratio` to ~0.3–0.5** so ε reaches its floor early and the policy converges near-greedy; tune against the liveplot. (`benchmarl_setup/algorithm_utils.py:105-113`)
11. **[MEDIUM] Adopt `rliable`-style robust reporting** (IQM + stratified-bootstrap CIs) given the 5-seed budget — cite Agarwal et al. 2021 — rather than increasing seed count to 30–50.
12. **[LOW] Fix terminology in reports/plots:** distinguish max-return, all-evals average-return (Papoudakis), and last-10% tail-mean (smoothing); do not conflate.
13. **[LOW] Choose the final frame budget by plateau**, not a fixed 60k; document it.

---

### Follow-up Q3 (user): second source — tabular Q-Learning Pacman project (Experimental Setup §4.1)

**Q3 (user):** "vamos adicionar também" — incorporate an excerpt from a tabular Q-Learning Pacman project report (α=0.5, ε=0.3→0.1, γ=0.9, 2000–3000 episodes; reward: +10/dot, −1/step, −500 caught, +500 board-clear; Table 2: tiny 6×6 → 75% win, medium 10×6 → 0% win at the same episode budget).

**A3 (agent):** Recorded as a secondary, corroborating source. It is *tabular* single-learner Q-Learning (no function approximation), so it is not methodologically comparable to this project's deep MARL (IQL/VDN/QMIX with neural nets + parameter sharing) — but two lessons transfer directly:

1. **ε exploitation (corroborates rec #10).** They dropped ε from 0.3→0.1 because "the high exploration factor resulted in excessive random actions even after the agent had acquired substantial knowledge of optimal policies." This is exactly the rationale for our `EPSILON_END=0.05` + faster `EPSILON_ANNEAL_RATIO=0.4`: once the policy is learned, cut residual exploration so the greedy policy exploits and converges tighter. Independent empirical support for the epsilon change.

2. **Budget must scale with state-space size (resolves the open FRAMES question, rec #13).** Tiny 6×6 reached 75% win, but the *same* episode budget on a medium 10×6 grid collapsed to 0% — the curse of dimensionality. Lesson for us: **a frame budget validated on one maze is not transferable to a larger maze.** Our default maze (`pinklike3`) is substantially larger than 6×6, so `FRAMES` should be **set per maze and confirmed against the liveplot plateau**, not fixed once. Caveat: deep function approximation generalises across states, so we will not see the same hard 0% cliff a tabular agent does — but the monotone "bigger grid → more frames to converge" relationship still holds and should govern how we pick `FRAMES`.

**On the FRAMES default specifically:** rather than blindly bump 100000, the principled action is (a) keep `FRAMES` an explicit per-maze knob, and (b) confirm the capture-rate curve has plateaued for `pinklike3` at the chosen budget before reporting. The runs directory is gitignored, so no curve was available in-session to pick a number empirically — this needs a liveplot/curve check.

**Reward-shaping note (informational, out of scope):** the cited reward (+10/dot, −1/step, ±500 terminal) is a dense, hand-tuned scheme. This project deliberately studies sparse `capture_v0` + PBRS (D-003 / research-000024/000035); the cited scheme is not a target to adopt, only context.

## Recommendations summary (follow-up Q3)

14. **[MEDIUM] Treat `FRAMES` as a per-maze, plateau-validated budget** (not a fixed constant): confirm the `pinklike3` capture-rate curve plateaus before reporting; scale up for larger mazes. Corroborated by the tabular-Q-Learning state-space/budget result.
15. **[LOW] Cite the second source as independent empirical support** for the epsilon-exploitation change (ε reduced once the policy is learned).
