# Research 000026 | fernanda-INF2072 | 2026-06-28 18:04 | Branch capture_v0_pure_potential_shaping merge-prep & salvage inventory

tags: git-branch-management, merge-conflict, reward-shaping, marl-environment, salvage-artifact

## User brief

> tudo o que foi feito até agora nesta branch. Vamos nos preparar para fazer um merge com a main. pode ser que dê muitos conflitos. eu quero ter a chance de apagar o que foi feito aqui e o que tem potencial de ser usado em uma branch limpa, e refazer depois. quero guardar um artefato de informação que permita fazer isso.

## Agent interpretation

Produce a durable, self-contained inventory of everything done on the
`capture_v0_pure_potential_shaping` branch that is **not yet in `origin/main`**, so the
branch can be safely **deleted** and its valuable work **recreated on a clean branch
later**. The artifact must (a) catalogue the work, (b) classify what is worth keeping,
(c) map the merge-conflict surface, and (d) ship the actual code as re-appliable patch
files so deleting the branch loses nothing.

## Files

- Report: `_output/research-logs/research-000026-branch-capture-v0-pure-potential-shaping-merge-prep.md`
- **Salvage patches (the recreation payload):** `_output/branch-salvage/capture_v0_pure_potential_shaping/`
  - `0001-fix-reward-close-PBRS-reward-farming-loophole-in-cap.patch`
  - `0002-research-000024-append-PBRS-reward-farming-follow-up.patch`
  - `0003-feat-obs-encode-relative-bearing-to-Pacman-in-ghost-.patch`
  - `0004-fix-reward-use-mean-of-all-ghosts-distance-for-coord.patch`
  - `0005-feat-train-expose-EPSILON_ANNEAL_RATIO-knob-for-expl.patch`
  - `UNCOMMITTED-spawn-randomization-and-eval-fix.patch`
- Source research this branch extends: `_output/research-logs/research-000024-deep-eval-pinklike3-reintroduce-pbrs.md`

---

## 1. Headline finding — the branch is mostly ALREADY merged

`origin/main` advanced to **210e5ac (PR #25)**, and **PR #27** already merged this branch's
history up to the common ancestor **`3818f6c`** (`plan-000025: mark DONE`). So the large
bulk of this branch — `capture_v0` reward system, the rewards refactor (`rewards/` package),
plan-000025's pure-PBRS variant, the curriculum learning, the 11x11 local observation,
action-decoder hardening, masking — **is already in `origin/main`. Do not recreate any of it.**

The git topology:

```
                3818f6c  (merge-base = "plan-000025 DONE")
                 /     \
   OUR 5 commits        THEIR work (multi-machine, eval fixes, curriculum tweaks,
   652aa0c (HEAD)        plot improvements) → merged into origin/main = 210e5ac (PR#25)
                 \      already contains everything up to 3818f6c via PR#27
   + uncommitted
   working tree
```

What is **unique to this branch** (the only thing at risk on a delete) is just:
- **5 commits** (`3818f6c..HEAD`), and
- **uncommitted working-tree changes** (6 files; the spawn-randomization feature + an eval fix).

Everything below catalogues exactly those.

---

## 2. The 5 unique commits (committed, captured as patches 0001–0005)

| # | Commit | Type | Files | Keep? |
|---|--------|------|-------|-------|
| 0001 | `256b761` fix(reward): close PBRS reward-farming loophole | env logic | `rewards/current.py`, `test_reward_strategies.py` | **KEEP — high** |
| 0002 | `58d1975` research(000024): append PBRS farming follow-up | doc | research-000024 log | KEEP — low effort |
| 0003 | `46fa226` feat(obs): relative bearing to Pacman in shared memory (FR4) | env/obs | `pacman_environment.py`, `test_observation_bearing.py` | **KEEP — high** |
| 0004 | `96f164a` fix(reward): mean-of-all-ghosts distance for coordination | env logic | `rewards/current.py`, `test_reward_strategies.py` | **KEEP — high** |
| 0005 | `652aa0c` feat(train): expose EPSILON_ANNEAL_RATIO knob | training cfg | `Makefile`, `algorithm_utils.py`, `run_benchmark.py`, `run_pacman_benchmarl.py` | **KEEP — high** |

### Detail

**0001 — PBRS reward-farming loophole (farm-proofing).** Eval of the PBRS policy showed
ghosts collapsing to 2-cell oscillations, ignoring a stationary Pacman, banking +50 team
shaping over 80 steps with zero captures. Root cause: discounted telescoping (γ=0.99) with
Φ≤0 pays a positive residual per back-and-forth, and a "two nearest ghosts" team distance was
discontinuous. Fix: **exact (γ=1) telescoping** `F = Φ(s') − Φ(s)` over the **smooth MIN ghost
distance**, so any in-place oscillation nets exactly 0; stronger −0.05 timestep makes camping
strictly negative. An 80-step camp went from +50.1 → −3.3. Regression test added.

**0003 — FR4 relative bearing (observation).** The shared-memory row encoded Pacman's
*absolute* board position while the ghost's own position was absent, so a ghost couldn't derive
a direction toward an off-screen Pacman. Replaced `features[1],[2]` with the normalized
**relative vector `(pacman − ghost)` per ghost** (ego-relative bearing). Observation shape
unchanged. New `test/test_observation_bearing.py`.

**0004 — mean-of-all-ghosts coordination.** With the MIN-distance potential and a shared team
reward, non-nearest ghosts get reward they can't influence → no gradient → they park far away
(observed: 2 of 3 ghosts at distance 23, standoff, no captures). Fix: potential over the
**MEAN distance of all ghosts**, so every ghost is rewarded for closing in and the team
coordinates a surround. Still γ=1 / farm-proof (80-step camp nets a bounded +0.7).
**Note:** 0004 supersedes 0001's MIN choice — they touch the same function in `rewards/current.py`;
apply 0001 then 0004 in order, or recreate just the final mean-distance form.

**0005 — EPSILON_ANNEAL_RATIO knob.** Anneal ratio was hardcoded 0.95, so on a 300k run ε only
reached 0.1 at 285k — no long greedy phase, wildly unstable capture curve (25–79% swings).
Threaded `--epsilon-anneal-ratio` through `run_benchmark → subprocess → run_pacman_benchmarl →
training_exploration_schedule` (validated in (0,1]); Makefile default 0.5.

---

## 3. Uncommitted working-tree changes (captured as the UNCOMMITTED patch)

**This is the highest-risk material — it is not committed anywhere and a branch delete +
`git checkout` would erase it permanently.** It is now saved in
`UNCOMMITTED-spawn-randomization-and-eval-fix.patch`.

| Change | Files | Keep? |
|--------|-------|-------|
| **Spawn randomization feature** — `randomize_spawns` / `randomize_spawns_min_distance` | `pacman_environment.py` (`_sample_random_spawns`, reset wiring, seeded RNG), `pacman_benchmarl_task.py`, `run_benchmark.py`, `run_pacman_benchmarl.py`, `Makefile` (`RANDOMIZE_SPAWNS*` vars) | **KEEP — high** |
| **Eval observation-match fix** — stop forcing `shared_memory_in_observation_enabled = False` in eval | `custom_environment/eval.py` | **KEEP — high (correctness)** |
| Deleted stale benchmark PNG | `runs/pinklike3/.../benchmark_capture_multiseed_mean_std.png` | discard (regenerated output) |

**Spawn randomization:** when on (default 1 in Makefile, but argparse default False), `reset()`
draws fresh Pacman/ghost cells each episode from non-wall tiles, accepting a draw only when every
ghost is BFS-reachable and ≥ `min_distance` from Pacman (200-attempt budget, falls back to
map-authored spawns). Seeded once from the first seeded reset for reproducibility. Rationale:
stop the policy memorizing a fixed route to a fixed start cell; force reactive pursuit using the
FR4 bearing channel. Pairs naturally with commit 0003.

**Eval fix (important correctness bug):** eval was hard-setting
`raw_env.shared_memory_in_observation_enabled = False`, which **zeroed the bearing channel the
policy was trained with** → out-of-distribution observation → trained ghosts wandered instead of
chasing. Eval must match training (which runs with it enabled). Without this fix, *any* eval of
an FR4-trained checkpoint is misleading.

---

## 4. Merge-conflict surface (small and mechanical)

Files changed on **both** sides since the `3818f6c` merge-base:

| File | Our change | Their change (origin/main) | Conflict |
|------|-----------|----------------------------|----------|
| `Makefile` | +EPSILON_ANNEAL_RATIO, +RANDOMIZE_SPAWNS vars | +3 lines | **Yes (mechanical)** |
| `benchmarl_setup/run_benchmark.py` | +argparse args, +command threading | +140 lines (multi-machine) | **Yes (mechanical)** |
| `custom_environment/eval.py` | 1-line obs fix (uncommitted) | +302 lines (eval rework) | **Yes — verify their rework didn't already re-add the bug** |

Files **only we** touched (no conflict): `algorithm_utils.py`, `run_pacman_benchmarl.py`,
`pacman_environment.py`, `rewards/current.py`, `pacman_benchmarl_task.py`,
`test_observation_bearing.py`, `test_reward_strategies.py`, research-000024 log.

Files **only they** touched: `README.md`, `liveplot.py`, `plot_benchmarl_reward.py`,
`summarize_benchmark_runs.py`, `eval_report.py`.

The conflicts are all **additive argparse/arg-threading** plus one eval line — none are deep
logic merges. The user's fear of "muitos conflitos" is overstated by file count but real in
that 3 files overlap; each resolves by keeping both additions.

> **Check during recreation:** `origin/main`'s eval rework (+302 lines) may have changed or
> removed the `shared_memory_in_observation_enabled = False` line. Re-read that area on the
> fresh branch before re-applying the eval fix (0004's eval portion) — it may already be fixed,
> moved, or need re-expressing.

---

## 5. Recommendations summary

| Priority | Recommendation |
|----------|----------------|
| **HIGH** | **Do NOT delete the branch until the patches are committed somewhere durable.** The 6 patch files in `_output/branch-salvage/...` are now that durable copy — commit them (they live under `_output/`, which is tracked). The uncommitted patch is the only irreplaceable artifact. |
| **HIGH** | **Recreate, don't merge.** Given only 5 small commits + 1 uncommitted change diverge, recreate them on a branch cut from fresh `origin/main` rather than fighting a tangled merge. Recommended path in §6. |
| **HIGH** | Keep all 5 commits and the spawn-randomization + eval fix — every one addresses a concrete, eval-verified failure (reward farming, parked ghosts, OOD eval, unstable ε curve, route memorization). None is speculative. |
| **MEDIUM** | When re-applying, collapse 0001+0004 into the final **mean-distance, γ=1** form (0004 supersedes 0001's MIN choice in the same function). |
| **MEDIUM** | Before re-applying the eval fix, re-read `origin/main`'s reworked `eval.py` — the bug may already be resolved upstream. |
| **LOW** | Drop the deleted-PNG change; regenerated outputs don't belong in a clean recreation. |

---

## 6. Recreation playbook (clean branch from fresh origin/main)

```bash
# 0. SAFETY: commit the salvage artifacts first, while still on this branch.
git add _output/branch-salvage _output/research-logs/research-000026-*.md
git commit -m "docs: salvage capture_v0_pure_potential_shaping branch as patches + inventory"
git push origin capture_v0_pure_potential_shaping   # durable remote copy

# 1. Cut a clean branch from the up-to-date main.
git fetch origin
git switch -c capture_v0_pbrs_clean origin/main

# 2a. EASY PATH — replay the 5 commits as-is (Co-Authored-By + messages preserved):
git am _output/branch-salvage/capture_v0_pure_potential_shaping/000{1,2,3,4,5}-*.patch
#     ...resolve the Makefile / run_benchmark.py conflicts (keep both additions),
#        then: git am --continue

# 2b. Re-apply the uncommitted spawn-randomization + eval fix:
git apply --3way _output/branch-salvage/capture_v0_pure_potential_shaping/UNCOMMITTED-*.patch
#     If eval.py rejects, open origin/main's eval.py and re-express the 1-line obs fix by hand.

# 3. Verify, then commit the uncommitted piece.
py -3.11 -m pytest test/test_reward_strategies.py test/test_observation_bearing.py
git add -A && git commit -m "feat(env): per-episode spawn randomization + eval obs-match fix"
```

> Alternative if `git am` conflicts are annoying: cherry-pick by hash instead while both branches
> exist — `git cherry-pick 256b761 46fa226 96f164a 652aa0c` (skip the doc-only 58d1975 or
> include it). Both branch and patches remain available until you choose to delete.

**Only delete the old branch (`git branch -D capture_v0_pure_potential_shaping`,
`git push origin --delete ...`) after step 3 verifies the clean branch builds and tests pass.**

---

## Q&A log

**Q1 (2026-06-28):** tudo o que foi feito até agora nesta branch. Vamos nos preparar para
fazer um merge com a main. pode ser que dê muitos conflitos. eu quero ter a chance de apagar o
que foi feito aqui e o que tem potencial de ser usado em uma branch limpa, e refazer depois.
quero guardar um artefato de informação que permita fazer isso.

**A1:** The branch is mostly already in `origin/main` (PR #27 merged it up to `3818f6c`); only
**5 commits + uncommitted working-tree changes** are unique. All unique work is worth keeping
(PBRS farm-proofing, mean-distance coordination, FR4 bearing observation, ε-anneal knob,
per-episode spawn randomization, eval observation-match fix). The conflict surface is just
3 files (`Makefile`, `run_benchmark.py`, `eval.py`), all additive/mechanical. To let you delete
the branch safely, I exported all unique work as 6 re-appliable patch files under
`_output/branch-salvage/capture_v0_pure_potential_shaping/` and wrote a recreation playbook
(§6): commit the patches, cut a clean branch from fresh `origin/main`, `git am` the 5 commits +
`git apply` the uncommitted patch, verify tests, then delete the old branch.
