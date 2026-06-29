# Research 000027 | fernanda-INF2072 | 2026-06-28 23:54 UTC | What happened with the main-branch code merged here

tags: git-branch-management, merge, branch-history, marl-environment

source: research-000026

## User brief

> what happened with the code that was at the main branch and was merged here

## Agent interpretation

Explain, from the git history, what the `origin/main` code that was merged into the
current `capture_v0_pure_potential_shaping` branch actually was, how the merge went
(conflicts, resolution), and what state the branch is in now as a result. This is an
informational/historical question — a recount of the merge `52003eb`, not a design
decision.

## Files

- Report: `_output/research-logs/research-000027-what-happened-with-main-branch-code-merged-here.md`
- Prior context: `_output/research-logs/research-000026-branch-capture-v0-pure-potential-shaping-merge-prep.md`

---

## 1. What the merge was

On **2026-06-28 18:45**, `origin/main` was merged into this branch:

```
52003eb  Merge remote-tracking branch 'origin/main' into capture_v0_pure_potential_shaping
  parent 1 (ours):  f4721de  chore(briefs): index research-000026 reservation
  parent 2 (theirs): 210e5ac  Merge pull request #25 (origin/main)
  merge-base:        3818f6c  plan-000025: mark DONE
```

The two histories had split at **`3818f6c`** (`plan-000025` DONE). From that point:

- **Our side** added 5 commits + uncommitted work (PBRS farm-proofing, mean-distance
  coordination, FR4 bearing observation, ε-anneal knob, spawn randomization, eval fix).
- **Main's side** added the work merged via PRs #24/#26/#27 → #25.

## 2. What main brought in (the code that was merged here)

13 commits on main's side, landing as a net change of **8 files, +1104 / −103**:

| File | What main changed |
|------|-------------------|
| `custom_environment/eval.py` | +302 — large eval rework |
| `benchmarl_setup/liveplot.py` | +216 — live-plot improvements |
| `benchmarl_setup/plot_benchmarl_reward.py` | +194 — multi-reward-system comparison plots |
| `benchmarl_setup/summarize_benchmark_runs.py` | +159 |
| `benchmarl_setup/run_benchmark.py` | +140 — **multi-machine training** (`machine_id`) |
| `custom_environment/eval_report.py` | +100 |
| `README.md` | +93 |
| `Makefile` | +3 |

Themed, the merged main code is:

1. **Multi-machine training** (`6c84ce4`, PRs #24/#25) — `--machine-id` threaded through
   the benchmark runner so runs can be split across machines.
2. **Eval + curriculum-learning fixes** (`3ccb628`, `cb3bc6c`, `baeac6a`, PR #26) —
   corrections to the eval path and to curriculum learning.
3. **Plot/reporting improvements** (`d2f2641`) — better multi-reward comparison graphs;
   the "best" checkpoint now selected by **capture rate, not reward**.
4. **Faster in-training eval** (`60f536c`) — eval episodes during training cut 100 → 20,
   plus some warnings disabled.

Note: `origin/main` had itself already merged most of *this* branch's earlier history
(up to the merge-base `3818f6c`) via PR #27 — so the `capture_v0` reward system, the
`rewards/` refactor, plan-000025's pure-PBRS variant, curriculum learning and the 11×11
local observation were already on main before this merge.

## 3. How the merge went — clean, with one trivial auto-resolution

The merge-prep doc (research-000026) predicted 3 overlapping files. In practice the merge
completed with **zero manual conflicts**:

- **`run_benchmark.py`** — the only file where both sides edited adjacent lines. Git's
  combined diff shows it kept **both** additions: main's `machine_id` parameter **and** our
  `epsilon_anneal_ratio` parameter, in both the `ProgressReporter` signature and the
  `main()` call site. Correct resolution.
- **`Makefile`** and **`eval.py`** — both sides touched them but in non-overlapping
  regions, so git auto-merged cleanly (they show up in the merge's name-only list but have
  no conflict hunks).

Verified semantically: the critical **eval observation-match fix held** — `eval.py` no
longer force-disables `shared_memory_in_observation_enabled` (grep finds no such line), so
main's +302-line eval rework did not silently re-introduce the OOD-observation bug.

## 4. What happened after the merge

Two follow-up commits:

- **`5f615ae`** — fixed two reward tests that were failing, but those were **pre-existing
  failures inherited from main's lineage** (they also fail at the merge-base `3818f6c`),
  not caused by our work or the merge:
  - `test_capture_v0_improved...`: the code was right (legal-move delta = 2 → reward 0.4);
    the test's "3−2=1" comment had miscounted the start cell. Expectation corrected to 0.4.
  - `StrongerMovementReward` example was built on `CurrentRewardWeights` (V1) while the
    baseline had migrated to `CurrentRewardWeightsV2`, so it no longer changed "exactly one
    weight." Rebuilt the example on V2. **Full suite: 81 passed.**
- **`d5cd170`** — docs: recorded in research-000026 that the merge completed cleanly and
  tests are green.

## 5. Net result / current state

- The branch `capture_v0_pure_potential_shaping` now **contains all of main's work**
  (multi-machine training, eval/curriculum fixes, improved plots, faster in-training eval)
  **plus** this branch's unique work (PBRS farm-proofing, mean-distance coordination, FR4
  bearing observation, ε-anneal knob, spawn randomization, eval obs-match fix).
- **81 tests pass.** No outstanding conflicts.
- The original plan in research-000026 was "salvage as patches, then delete-and-recreate on
  a clean branch." That was **abandoned in favor of a direct merge** because the conflict
  surface turned out to be trivial. The salvage patches under
  `_output/branch-salvage/capture_v0_pure_potential_shaping/` remain as a backup but are no
  longer the active path.
- **Caveat (from research-000026):** local `main` is stale — `git pull` it before basing
  future work on it. The merge used `origin/main` (remote), which was current.

---

## Recommendations summary

This was an informational recount; no design decision was made. One operational note
carried forward from research-000026:

| Priority | Recommendation |
|----------|----------------|
| LOW | `git pull` local `main` before cutting any future branch — local `main` is stale; the merge correctly used `origin/main`. |

## Q&A log

**Q1 (2026-06-28):** what happened with the code that was at the main branch and was merged here

**A1:** `origin/main` (PR #25, `210e5ac`) was merged into this branch on 2026-06-28 as
merge commit `52003eb`. The histories had diverged at `3818f6c` (plan-000025 DONE); main's
side contributed 8 files / +1104−103 of code: multi-machine training (`machine_id` in
`run_benchmark.py`), an eval rework + curriculum/eval fixes, improved comparison plots
(best checkpoint now picked by capture rate, not reward), and faster in-training eval
(100→20 episodes). The merge completed with **no manual conflicts**: `run_benchmark.py`
auto-kept both main's `machine_id` and our `epsilon_anneal_ratio`; `Makefile` and `eval.py`
auto-merged non-overlapping regions. The branch's own eval observation-match fix survived
(no force-disable of `shared_memory_in_observation_enabled`). Two reward tests then failed,
but they were **pre-existing failures inherited from main**, fixed in `5f615ae` (full suite
81 passed). The branch now holds main's work + this branch's unique work, all green. The
earlier delete-and-recreate plan (research-000026 §6) was dropped because the merge was
clean; the salvage patches remain as backup. Only caveat: local `main` is stale — pull it
before future branching.
