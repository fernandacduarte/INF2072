# Research 000028 | TB | 2026-06-29 00:11 UTC | Evasive-Pacman benchmark protocol

tags: experimental-design, benchmark, reinforcement-learning, reproducibility, evaluation

## User brief

> Quero bolar um protocolo de teste para a apresentação final da disciplina (INF2072, estudo de Reinforcement Learning). O algoritmo funcionava quando o Pacman era 100% aleatório (os fantasmas aprendiam a capturá-lo), mas com o Pacman super evasivo o aprendizado é quase impossível mesmo com curriculum learning e potential shaping. Quero pipelines de benchmark para gerar gráficos para a apresentação. Já usamos curriculum learning e potential shaping. Acho interessante pararmos aqui e perguntarmos: **o quão evasivo o Pacman precisa ser para os nossos fantasmas pararem de aprender a capturá-lo?**

## Agent interpretation

This is a **dose–response / psychometric-threshold experiment**, not a feature build. The independent variable is *Pacman evasiveness*; the dependent variable is *whether the cooperative ghost team learns to capture*. The codebase already exposes a clean continuous evasiveness dial (`--pacman-random-action-prob p`), with the two endpoints anchored to known outcomes (p=1.0 → fully random → learning works; p=0.0 → fully deterministic flee → learning fails). The task is to (a) design a methodologically defensible protocol that locates the threshold, (b) wire it onto the existing benchmark harness with minimal new code, and (c) produce presentation-quality figures — all under a tight 1–2 day CPU budget.

User decisions (collected via interview):
- **Budget:** tight (1–2 days, CPU).
- **Primary evasiveness axis:** stochasticity `random_action_prob` (sweep 1.0 → 0.0).
- **Primary metric:** deterministic-eval `capture_rate`.
- **Algorithms:** IQL (baseline), VDN, QMIX.

## Files reviewed

- `custom_environment/env/domain/pacman_policy.py` — defense-first BFS policy; evasiveness dials `random_action_prob`, `pure_random`, `safe_distance`; **unseeded default RNG** (line 78).
- `custom_environment/env/pacman_environment.py` — difficulty/curriculum mapping (`_difficulty_params`, lines 219–225); `_build_pacman_policy` (227–236); `self._pacman_rng = np.random.default_rng()` at line 168 is **not** reseeded by `reset(seed=...)` (only `_spawn_rng` is, line 243).
- `benchmarl_setup/run_pacman_benchmarl.py` — single-run knobs incl. `--pacman-random-action-prob`, `--pacman-difficulty`, `--pacman-safe-distance`.
- `benchmarl_setup/run_benchmark.py` — multi-seed/algorithm harness; output paths keyed by `maze/reward/device` only (1245–1252, **collision risk on sweep**); `--eval-episodes` defaults to **0** (line 240); paired eval gated at 1377.
- `benchmarl_setup/algorithm_utils.py` — epsilon schedule, supported algorithms/mazes.
- `custom_environment/eval_report.py` — **keeps checkpoint-defined difficulty** (line 448) → automatic train-at-`e`/eval-at-`e`; emits `capture_rate` (379).
- `product-design/project/constitution.md` — Q3 (≥5 seeds), T4 (explicit seeds), C1 (commit hash).

---

## Q&A log

### Q1 (initial). How evasive does Pacman need to be before the ghosts stop learning to capture it, and how do I turn that into a benchmark protocol with presentation graphs?

**A1.**

#### 1. The experiment, framed correctly

Treat this as a **dose–response curve**. Define evasiveness `e = 1 − p` where `p = --pacman-random-action-prob`. Sweep `p` and measure the ghost team's learned `capture_rate(e)`. The result you present is the curve and the **threshold band** where capture collapses.

You already have the perfect single-axis knob. With `--pacman-difficulty hard --pacman-random-action-prob p`:
- `safe_distance` stays pinned at 5 (planning depth held constant — *no confound*),
- only the stochastic mix varies,
- `p = 1.0` reproduces your known-good "100% random" condition (verified: at `p=1.0` the policy always returns a uniform-random legal action, identical to `pure_random`),
- `p = 0.0` is the perfectly deterministic evader you can't beat.

So the whole study is one knob between two anchored endpoints. That's a clean, communicable design.

#### 2. The pipeline (minimal new code)

The harness already does the heavy lifting; it just doesn't sweep `p` or tag output by it. You need **two small scripts**:

**(a) Sweep wrapper** — loops over `p`, invoking `run_benchmark.py` once per point into a *distinct* save-folder (mandatory: output paths are keyed only by maze/reward/device, so reusing one folder co-mingles points). Per point:

```
py -3.11 benchmarl_setup/run_benchmark.py \
  --algorithms iql,vdn,qmixglobal \
  --reward-ids capture_v0_pure_potential_shaping \
  --seeds 0,1,2,3,4 \
  --max-frames 60000 \
  --pacman-difficulty hard \
  --pacman-random-action-prob <p> \
  --eval-episodes 40 \
  --checkpoint-at-end \
  --save-folder benchmarl_setup/runs_sweep/p_<p>
```

The wrapper also writes a `sweep_manifest.csv` (one row per point: `p, evasiveness, algorithm, seeds, frames, eval_episodes, save_folder, git_commit`) — this satisfies C1 (commit hash) and makes the plot auditable.

**(b) Aggregator + plotter** — reads each point's `reward_eval_*.csv` (which carries `capture_rate_mean/std` per algorithm), assembles the dose–response table, and renders the figure (300 DPI PNG, one line per algorithm, per-seed scatter + bootstrap CI band, x-axis "evasiveness = 1 − p").

`eval_report.py` already evaluates each checkpoint against the *same* evasiveness it trained on (it keeps the checkpoint-defined difficulty), so `capture_rate` is automatically the train-at-`e`/eval-at-`e` number you want. **You must set `--eval-episodes` > 0** (default is 0) or the DV silently comes out empty.

#### 3. Three methodological fixes that decide whether the result is publishable

These are what separate "the ghosts failed" from "we *measured* where and why they fail." In priority order:

1. **Add a normalization ceiling (HIGH).** Raw `capture_rate` confounds "how learnable" with "how catchable in principle." A perfectly evasive Pacman on a connected maze may be *mathematically* uncatchable by 2 ghosts (pursuit–evasion / cop-number of the graph) — in which case 0% capture is a property of the maze, not a failure of VDN/QMIX. Run a **scripted greedy-pursuit ghost team** (no training, cheap) at each `p` to get `ceiling(p)`, and report **`capture_rate / ceiling(p)`** alongside the raw curve. This is the single highest-signal addition for the cost: it makes your negative control interpretable and pre-empts the obvious examiner question. If a scripted pursuer is too much for 1–2 days, use the random-Pacman ceiling as a fallback.

2. **Break the under-training confound (HIGH).** With a fixed 60k-frame budget, harder points get *sparser* capture events → fewer usable learning signals → a low `capture_rate` that may just mean "undertrained," not "unwinnable." Defend against this: for the two hardest points (`p=0.1`, `p=0.0`) plot the **learning curve** (capture vs frames) to show it has *plateaued*, and run at least one **extended-budget point** (2–4× frames). "Fails even at 4× budget" is a dramatically stronger claim than "fails at 60k."

3. **Seeds + seed-pinning (HIGH).** (i) The constitution requires ≥5 seeds (Q3); 3 cannot support a threshold estimate with honest uncertainty. (ii) `self._pacman_rng` is created with OS entropy and never reseeded from the training seed, so every `p>0` opponent (including the `p=1.0` control) is **not reproducible run-to-run** — a one-line fix (`self._pacman_rng = np.random.default_rng(int(seed))` inside the seeded branch of `reset`) closes it and satisfies T4. With ≥5 eval episodes the *mean* is stable regardless, but exact reproducibility is a constitution requirement and a trivial fix.

#### 4. Honest threshold reporting

Fit a **logistic per algorithm** only where the curve is actually sigmoidal (likely VDN/QMIX; IQL may be flat-low and a logistic would fit garbage). Report R²/residuals. Watch for a **non-monotone bump** near `p≈0.1` — a little randomness can occasionally walk Pacman into a trap and *help* the ghosts. Present `e*` as a **qualitative band** ("capture collapses between p=0.25 and p=0.1"), not a false-precision point estimate like "e* = 0.83 ± 0.04" — 3–5 seeds don't earn that.

#### 5. Budget-fit execution order (1–2 days, CPU)

Don't spend half your budget on a 6-point × 3-seed sweep that might have a broken DV. Sequence it:

1. **Pilot (½ day):** 2 points only — `p=1.0` (positive control, must converge) and `p=0.0` (negative control, must fail) — × 5 seeds × 3 algorithms, `--eval-episodes 40`. This validates the whole pipeline *and* your controls end-to-end. The 3 algorithms run in parallel (one worker each); ~3 serial seed-slots per point.
2. **Fill interior (1 day):** add `p ∈ {0.5, 0.25, 0.1}` (adaptive — densify wherever the drop appears; a threshold study needs density near `e*`, not uniform spacing).
3. **Harden (remaining):** extended-budget runs at the two hardest points + the scripted-pursuit ceiling sweep.

If compute forces a cut, **cut x-points or one algorithm before cutting seeds** — IQL+QMIX at 5 seeds is more defensible than IQL+VDN+QMIX at 3. You chose all three; the pilot will tell you quickly whether all three fit.

#### 6. The figure(s) for the slides

- **Primary:** `capture_rate` (y) vs `evasiveness = 1−p` (x), one colored line per algorithm, per-seed scatter + bootstrap CI band, horizontal ceiling reference line, the two endpoints annotated "positive control" / "negative control," fitted logistic overlay where valid. This one chart *is* the answer to your question.
- **Secondary:** normalized `capture_rate / ceiling(p)` (separates "harder task" from "learning failure"); time-to-capture vs evasiveness (coordination efficiency); learning curves at the hard points (convergence evidence).

---

## Recommendations summary

| # | Priority | Recommendation |
|---|----------|----------------|
| R1 | HIGH | Frame as a dose–response sweep on `--pacman-random-action-prob` with `--pacman-difficulty hard` fixed (holds `safe_distance=5`); `p=1.0`/`p=0.0` as anchored positive/negative controls. |
| R2 | HIGH | Add a **scripted greedy-pursuit ghost ceiling** per `p` and report normalized `capture_rate / ceiling(p)` to separate "task got harder" from "learning failed" (cop-number / uncatchability risk). Random-Pacman ceiling as fallback. |
| R3 | HIGH | Defend against the under-training confound: plot **plateaued learning curves** at the hard points and run ≥1 **extended-budget (2–4×)** point; "fails even at 4×" is the strong claim. |
| R4 | HIGH | Use **≥5 seeds** (constitution Q3) and **seed-pin `_pacman_rng`** in `reset()` (one-line fix; satisfies T4). If seeds must drop, document the deviation and downgrade `e*` to a qualitative band. |
| R5 | MEDIUM | Two new scripts only: a **sweep wrapper** (distinct `--save-folder` per `p`, writes `sweep_manifest.csv` with git commit) and an **aggregator/plotter**; set `--eval-episodes 40` explicitly (default 0 → empty DV). |
| R6 | MEDIUM | Fit logistic **per algorithm**, report R²/residuals, present `e*` as a band, and check for the non-monotone bump near `p≈0.1`. |
| R7 | MEDIUM | Execute in order **pilot (2 controls × 5 seeds) → interior fill (adaptive) → harden**; cut x-points/algorithms before seeds. |
| R8 | LOW | Presentation polish per design-standards: 300 DPI, consistent per-algorithm colors, colorblind-safe palette, bootstrap CI bands, ceiling reference line, controls annotated, x-axis "evasiveness = 1 − p". |
