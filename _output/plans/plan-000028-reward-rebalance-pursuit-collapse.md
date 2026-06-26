# DONE | 2026-06-26 21:05 UTC | Plan 000028 | TB-FIX | 2026-06-26 20:42 UTC | Reward rebalance to fix pursuit collapse | Review: standard
plan_format_version: 1
source: research-000027

## User brief

> plan reward rebalance — Rebalance the ghost team reward to fix pursuit collapse (source: research-000027). The converged greedy policies capture ~0%, time out 100%, with mean return ~-140 and strongly negative shaping return — a pursuit/learning failure, not reward-hacking. Rebalance `custom_environment/env/rewards/current.py` (CurrentRewardWeightsV2 / CurrentTeamReward, the benchmark default) so shaping is net-positive toward pursuit: (1) drastically reduce or remove the anti-oscillation/movement penalties (repeated_direction_reversal, two_step_cycle, stay_still, invalid_move) that sum to ~-140/episode and suppress cornering; (2) strengthen the pursuit gradient with a non-telescoping proximity/visibility reward (or raise potential_shaping_alpha) since the potential shaping telescopes to ~0 and the +40 terminal is too sparse against a fleeing defensive Pacman; (3) FIRST add a diagnostic that emits the already-accumulated per-term reward_breakdown from eval_report.py (line 242, currently not written to CSV) so we can confirm which penalty dominates the -140 before and after the change. Keep terminal-penalty signs unchanged so existing smoke tests stay valid.

## Agent interpretation

**Problem**: All algorithms converge to a degenerate non-pursuit policy (capture ~0%, timeout 100%, mean return ~−140) because the dense team reward is dominated in practice by net-negative anti-oscillation/movement penalties that punish the exploratory cornering needed to catch a fleeing defensive Pacman, while the pursuit signal (potential shaping) telescopes to ~0 and the +40 terminal is too sparse.

**Approach**: A measurement-first, additive rebalance:
1. **Instrument before tuning** — emit the per-term reward decomposition (already computed in `eval_report._run_episode` but discarded) so the dominant penalty mass behind the −140 is confirmed empirically, and the before/after effect of the rebalance is measurable.
2. **Add a new reward variant `current_v3`** (new weights dataclass + thin strategy subclass) rather than mutating `CurrentRewardWeightsV2` in place. This preserves `current` (V2) and `current_git` (V1) as reproducible A/B baselines — required by the project's reproducibility principles (constitution T4/Q3) and matching the existing `current_git`/`current`/`current_with_overlap_or_same_corridor` extension pattern. The rebalance is then a one-line Makefile default switch, fully reversible.
3. **Rebalance v3 weights** — slash the anti-oscillation/movement penalties so shaping is net-positive toward pursuit, raise `potential_shaping_alpha` to strengthen the pursuit gradient, and moderate `currently_visible` so the (deferred) stalking risk is not reintroduced once pursuit is learned.

**Alternatives rejected**:
- *Retune `CurrentRewardWeightsV2` in place* — simplest, but destroys the V2 baseline mid-experiment, breaking reproducible A/B comparison (the lone qmixglobal capture and the V1/V2 distinction are baselines worth keeping). Rejected for a new variant.
- *Rewrite the pursuit signal as a fully potential-based reward (γΦ(s')−Φ(s) only)* — theoretically cleanest, but a larger refactor of `compute()` and, per research-000027, the missing-γ defect is not the regression driver. Deferred; v3 reuses the existing `CurrentTeamReward.compute()` logic and changes only weights.
- *Add an entirely new proximity term in `compute()`* — the existing `currently_visible` + `potential_shaping` terms already provide proximity/visibility signal; raising `potential_shaping_alpha` and keeping `currently_visible` moderate strengthens pursuit without new code paths. A non-telescoping term is deferred unless the post-rebalance benchmark still shows weak pursuit.

**Selection rationale** (source: research-000027):
- Included: Rec #1 (rebalance shaping net-positive; slash anti-oscillation/movement penalties) — core of Steps 2-3.
- Included: Rec #2 (strengthen pursuit gradient — raise `potential_shaping_alpha`) — Step 2 weights.
- Included: Rec #3 (pinpoint dominant penalty via per-term `reward_breakdown`) — Step 1, sequenced first.
- Partially included: Rec #4 (curriculum / ε floor / solvability) — out of scope for a reward-only change; captured as a follow-up note, not a step.
- Excluded: original (pre-revision) Recs #1-#3 (gate `currently_visible`, cap shaping budget, γ-discounted shaping) — deferred per the research follow-up (LOW; not the active blocker), except that v3 moderates `currently_visible` and bounds total shaping as a guardrail.

## Files

- **Modify** `custom_environment/eval_report.py` — aggregate per-term `reward_breakdown` across episodes; emit as a JSON column in `REPORT_FIELDS` and `VARIANT_FIELDS`.
- **Modify** `custom_environment/env/rewards/current.py` — add `CurrentRewardWeightsV3` dataclass and `PursuitFirstTeamReward` strategy (`strategy_id = "current_v3"`).
- **Modify** `custom_environment/env/rewards/loader.py` — register `current_v3` in `_REWARD_CLASS_BY_ID`.
- **Modify** `Makefile` — switch `REWARDS` / `REWARD_ID` defaults to the v3 variant (keep prior default in a comment for reversibility).
- **Modify** `test/test_reward_strategies.py` — add v3 coverage (registration, pursuit calibration, bounded shaping, terminal signs unchanged).
- **Modify** `test/test_eval_report.py` — assert the per-term breakdown column is populated.

## Root cause

(From research-000027, confirmed against live eval CSVs.) At convergence the greedy policy captures ~0%, times out every episode (mean_steps=200), with `mean_shaping_return ∈ [−132, −60]` and low `frac_steps_visible`. The dense reward's anti-oscillation/movement penalties (`invalid_move −0.08`, `stay_still −0.03`, `repeated_direction_reversal` up to −0.2/step, `two_step_cycle −0.08`) sum to ~−140/episode and dominate; they punish the exploratory back-and-forth required to corner a Pacman that holds BFS distance ≥3 and flees. The pursuit signal (`potential_shaping`, α=1.2) telescopes to ≈0 over an episode, giving no net incentive to *end* closer, and the +40 capture terminal is too sparse for the greedy policy to reach once ε anneals. Net: RL converges to a far-worse return (−140) than an available capturing policy (~+30) — a pursuit/learning failure, not reward exploitation.

## Best practices

- **Measure before tuning**: emit the per-term decomposition first so weight changes are evidence-driven, not guessed (research-000027 Rec #3).
- **Additive, reversible variants**: new `strategy_id` preserves baselines and matches the existing reward-strategy registry pattern; supports the project's reproducible A/B comparison requirement.
- **Keep terminal reward dominant**: bound total non-terminal shaping per episode well below `get_pacman` (+40) so pursuit shaping guides without rivalling the capture signal (guards against the deferred stalking failure mode).
- **Preserve calibration invariants**: the existing pursuit-calibration tests (move-toward > stay; move-toward > move-away) must still pass for v3.

## Design decisions

- **User-visible impact**: A researcher running `make benchmark` / `make liveplot` with defaults now trains on the `current_v3` reward and should see ghosts that actually pursue and capture (capture rate rising over training instead of collapsing). The eval report CSV gains a `mean_reward_breakdown` column exposing per-term reward mass. The old `current` (V2) and `current_git` (V1) rewards remain selectable for comparison.
- **Trade-offs accepted**: Gained — empirical diagnosability and a reward that rewards pursuit, with baselines preserved for A/B. Given up — the exact v3 weights are an initial hypothesis that still requires one validation benchmark to confirm (Step 6); a perfectly potential-based reward is deferred.
- **Metacommunication impact**: The eval report now communicates *which* reward terms drive the episode return (per-term breakdown), so I am telling you not just "the policy failed" but "this penalty term dominated the return" — turning an opaque score into an auditable decomposition you can act on.

## Steps

### Step 1 — Emit per-term reward breakdown in eval_report (diagnostic, sequenced first)
- [x] Aggregate the per-episode `reward_breakdown` (already accumulated at `eval_report.py:242-243`, carried in `EpisodeResult["reward_breakdown"]`) into a per-term mean across episodes inside `_aggregate_episodes`, and add it to that function's return dict as a single JSON-encoded `mean_reward_breakdown` field (one column, robust to strategy-varying term names). **In `_build_variant_summary` (lines 457-494) the output dict is built by explicit key enumeration — it does NOT propagate `pooled_stats` automatically — so explicitly add `"mean_reward_breakdown": pooled_stats["mean_reward_breakdown"]` to that dict literal.** Append `"mean_reward_breakdown"` to both `REPORT_FIELDS` and `VARIANT_FIELDS` (`csv.DictWriter(extrasaction="ignore")` drops unlisted keys).
- **Files**: `custom_environment/eval_report.py`, `test/test_eval_report.py`
- **References**: research-000027 follow-up Q6/Rec#3; `_aggregate_episodes` (line 291); `_build_variant_summary` explicit-key dict (lines 457-494); `REPORT_FIELDS` (line 499), `VARIANT_FIELDS` (line 525); `base.py` `RewardResult.breakdown` includes terminal terms (73-78)
- **Interface**: produces a `mean_reward_breakdown` JSON column in both per-seed rows and pooled variant rows, consumed by Step 6 validation and downstream analysis. `_aggregate_episodes` return dict gains key `mean_reward_breakdown` (JSON string).
- **Verify**: run `eval_report` on an existing final checkpoint (e.g. `benchmarl_setup/runs/pinklike3/current/cpu/iql_pacman_mlp__0b057b18_*/checkpoints/checkpoint_200000.pt`) with `--episodes 3`; confirm the CSV has a non-empty `mean_reward_breakdown` whose per-term values sum (≈) to `mean_episode_return` (reconciliation holds exactly because `breakdown` includes terminal terms and `team_return` == `total` broadcast to all ghosts).
- **Tests**: extend the `test_eval_report.py` `_episode` helper (lines 10-34) with a `reward_breakdown=None` kwarg (default `{}`); then when `_aggregate_episodes` is given episodes whose `reward_breakdown` dicts contain `{"timestep": -2.0, "valid_move": 1.0}`, the returned `mean_reward_breakdown` JSON decodes to the per-term mean across those episodes.
- **Docs**: N/A

### Step 2 — Add CurrentRewardWeightsV3 (rebalanced weights)
- [x] Add a frozen `CurrentRewardWeightsV3` dataclass in `current.py` mirroring `CurrentRewardWeightsV2`'s fields, with: terminal signs unchanged (`get_pacman=40.0`, `pacman_timeout_win=-35.0`, `pacman_win_pellets=-35.0`); anti-oscillation/movement penalties slashed but **not all zeroed** — `repeated_direction_reversal≈0.0`, but keep small `two_step_cycle≈-0.02` and `stay_still≈-0.02` so an in-place ping-pong that merely keeps Pacman visible is **not** net-positive; `invalid_move≈-0.02`; pursuit gradient strengthened (`potential_shaping_alpha≈2.0`); **`currently_visible` lowered to ≈0.05–0.1** (NOT 0.2) — it is granted *every* visible step unconditionally (current.py:372), so at raised α a 200-step visible-but-no-capture episode could otherwise accrue shaping rivalling the +40 terminal (the deferred stalking optimum); `valid_move≈0.05` to keep movement net-positive (must satisfy `valid_move + min-positive shaping > stay_still penalty` so move-toward > stay survives — see Step 5b); `timestep=-0.01` retained. Add a comment that the per-episode visible-stalking shaping budget must stay below `get_pacman` (tie to Step 5d). Treat these as documented initial values (cite research-000027) to be confirmed in Step 6.
- **Files**: `custom_environment/env/rewards/current.py`
- **References**: `CurrentRewardWeightsV2` (current.py:39-61); unconditional `currently_visible` (current.py:372); `_team_distance` telescoping (current.py:437-445); research-000027 Recs #1-#2
- **Interface**: exposes `CurrentRewardWeightsV3` consumed by Step 3.
- **Verify**: `py -3.11 -c "from custom_environment.env.rewards.current import CurrentRewardWeightsV3; w=CurrentRewardWeightsV3(); print(w.get_pacman, w.repeated_direction_reversal, w.two_step_cycle, w.currently_visible, w.potential_shaping_alpha)"` prints the expected values.
- **Tests**: N/A (covered via Step 3 strategy tests)
- **Docs**: N/A

### Step 3 — Add PursuitFirstTeamReward strategy + register it
- [x] Add `class PursuitFirstTeamReward(CurrentTeamReward)` with `strategy_id = "current_v3"`, overriding **`__init__` only** (`def __init__(self, weights=None): super().__init__(weights or CurrentRewardWeightsV3())`). Do **not** override `reset()` — `CurrentTeamReward.reset()` reads `self.weights` and does not re-instantiate it (current.py:324-345), so V3 weights are already honored; `compute()` is inherited unchanged. The `__init__(self, weights=None)` signature stays no-arg-constructible (loader.py:88-93 calls `target()`). Register `"current_v3": "custom_environment.env.rewards.current:PursuitFirstTeamReward"` in `loader.py:_REWARD_CLASS_BY_ID`.
- **Files**: `custom_environment/env/rewards/current.py`, `custom_environment/env/rewards/loader.py`
- **References**: `CurrentTeamReward` (current.py:307-345), `_REWARD_CLASS_BY_ID` (loader.py:16-22)
- **Interface**: `load_reward_strategy("custom_environment.env.rewards.current:PursuitFirstTeamReward")` and `reward_class_from_id("current_v3")` both resolve to the new strategy.
- **Verify**: `py -3.11 -c "from custom_environment.env.rewards.loader import reward_class_from_id, load_reward_strategy; s=load_reward_strategy(reward_class_from_id('current_v3')); print(s.strategy_id, type(s.weights).__name__)"` prints `current_v3 CurrentRewardWeightsV3`.
- **Tests**: `reward_class_from_id("current_v3")` returns the `PursuitFirstTeamReward` path and `load_reward_strategy` yields an instance whose `strategy_id == "current_v3"` and `weights` is `CurrentRewardWeightsV3`.
- **Docs**: N/A

### Step 4 — Point Makefile benchmark/eval defaults at current_v3
- [x] Update `REWARDS` (line 21) to `custom_environment.env.rewards.current:PursuitFirstTeamReward` and `REWARD_ID` (line 22) to `current_v3`; keep the previous values in a trailing comment so the switch is one-line reversible. The `benchmark` target consumes `REWARDS` (line 53) and `eval-latest` consumes `REWARD_ID` (line 50). **Note: `liveplot` (line 57) takes neither — it discovers run directories**, so it needs no reward arg; just confirm `liveplot.py` still locates `current_v3/` run dirs (recent commits 6a44562/7dc27ef touched its reward_id token parser).
- **Files**: `Makefile`
- **References**: `Makefile:21-22` (REWARDS / REWARD_ID), `Makefile:50,53,57` (eval-latest / benchmark / liveplot targets)
- **Interface**: `make benchmark` / `make eval-latest` now default to `current_v3`; `make liveplot` discovers v3 run dirs.
- **Verify**: `grep -nE "REWARDS|REWARD_ID" Makefile` shows the v3 defaults plus the commented-out prior values; `grep -n reward_id benchmarl_setup/liveplot.py` confirms it discovers/filters v3 runs.
- **Tests**: N/A (Makefile variables; behavior covered by Step 6 validation)
- **Docs**: N/A

### Step 5 — Tests: v3 registration, pursuit calibration, bounded shaping, terminal signs
- [x] In `test/test_reward_strategies.py`, add tests asserting: (a) `current_v3` registers (`reward_class_from_id`) and loads (`load_reward_strategy`) with `weights` = `CurrentRewardWeightsV3`; (b) v3 preserves the pursuit-calibration property (move one BFS-cell toward the true Pacman scores higher than staying and higher than moving away) — **exercise v3 explicitly by instantiating `PursuitFirstTeamReward` directly and driving `compute()` (or injecting it as `env.reward_strategy`), since `test_reward_calibration.py` otherwise drives only the default `current`**; the invariant survives because `valid_move (+0.05) + min-positive potential_shaping > stay_still penalty (−0.02)`; (c) v3 terminal weights equal V2's (`get_pacman=40`, `pacman_timeout_win=-35`, `pacman_win_pellets=-35`); (d) **guardrail — the worst case is a Pacman-visible-every-step episode (not oscillation), since `currently_visible` accrues unconditionally**: drive a 200-step episode with `pacman_visible=True` each step and assert `sum(non-terminal shaping terms) < get_pacman` (40); keep an all-oscillation episode as a secondary assertion.
- **Files**: `test/test_reward_strategies.py`
- **References**: `test/test_reward_calibration.py` (pivot scenario + `_reward_for_move` harness), `custom_environment/env/rewards/current.py` (unconditional `currently_visible` 372), existing strategy tests in `test_reward_strategies.py`
- **Interface**: N/A
- **Verify**: `py -3.11 -m pytest test/test_reward_strategies.py test/test_reward_calibration.py -q` passes.
- **Tests**: v3 strategy — move-toward reward > stay reward and > move-away reward (via direct `PursuitFirstTeamReward` injection); v3 terminal weights equal the V2 terminal weights; summed non-terminal shaping over a 200-step Pacman-visible-every-step episode < `get_pacman`.
- **Docs**: N/A

### Step 6 — Validate: short A/B benchmark + eval breakdown (manual, non-authoritative)
- [~] Run a short A/B benchmark comparing `current` (V2) vs `current_v3` on the default maze with reduced frames, then inspect the new `mean_reward_breakdown` column and capture rate. Confirm: v3 shaping return is net-positive-toward-pursuit (penalty terms no longer dominate), capture rate improves over V2, and the dominant −140 penalty term identified in Step 1 is materially reduced. **This 2-seed run is a non-authoritative directional smoke check only — per constitution Q3 / design §10, any V2-vs-v3 capture-rate comparison recorded as a result must come from a full ≥5-seed `make benchmark` run.** Also confirm the benchmark-driven auto-eval (`reward_eval.csv`, `run_benchmark.py:771`) emits `mean_reward_breakdown`, not just the standalone `eval_report.py` path.
- **Files**: (none — execution/validation step)
- **References**: `benchmarl_setup/run_benchmark.py` (auto-eval → `reward_eval.csv` line 771), `custom_environment/eval_report.py`
- **Interface**: N/A
- **Verify**: `py -3.11 benchmarl_setup/run_benchmark.py --algorithms iql --reward-classes custom_environment.env.rewards.current:CurrentTeamReward,custom_environment.env.rewards.current:PursuitFirstTeamReward --seeds 0,1 --max-frames 40000 --maze pinklike3 --devices cpu` completes; `reward_eval.csv` has the `mean_reward_breakdown` column; per-term breakdown and capture rate show v3 ≥ V2 on capture and net-positive pursuit shaping (directional only).
- **Tests**: N/A (manual validation; documented in Test plan)
- **Docs**: N/A

## Test plan

1. `py -3.11 -m pytest test/test_reward_strategies.py test/test_reward_calibration.py test/test_eval_report.py -q` — all green.
2. `py -3.11 -m pytest test/` — full smoke suite still passes (no regression in env/terminal-sign tests).
3. Diagnostic on an existing checkpoint: `py -3.11 custom_environment/eval_report.py --learner iql --checkpoint <…/checkpoint_200000.pt> --reward-id current --episodes 5 --out _output/tmp/v2_breakdown.csv` — confirm `mean_reward_breakdown` reveals which penalty owns the −140.
4. Short A/B benchmark per Step 6 Verify; compare capture rate and shaping sign for V2 vs v3.

## Outcomes

- The eval report exposes a per-term `mean_reward_breakdown`, making the −140 return auditable.
- A new `current_v3` reward variant rewards pursuit (net-positive shaping toward capture), with V1/V2 baselines preserved for A/B.
- Default `make benchmark` / `make liveplot` train on `current_v3`; capture rate should rise over training instead of collapsing.
- Existing pursuit-calibration and terminal-sign tests remain valid.

## smoke
false

## Review log

**Review depth:** Standard | **Deep-dive budget:** 4/6 used | Reviewer: plan-reviewer agent

### Phase 1 — Perspective Scan

Prefix `TB-FIX` → FIX-B shortlist (SEC, DB, ARCH, TEST, PERF, DX); DB N/A (no database), SEC N/A (no new attack surface, constitution S1/S2 untouched); added DATA (numeric reconciliation of the new column).

| Perspective | Status | Concern |
|-------------|--------|---------|
| ARCH | Deferred → amended | Subclass weight-injection precision + reward over-correction (stalking) risk |
| TEST | Deferred → amended | Step 1 test-helper gap; guardrail under-specified; v3 calibration injection |
| DATA | Deferred → amended | `_build_variant_summary` explicit-key gap; per-term/terminal reconciliation |
| DX | Deferred → amended | liveplot takes no reward arg; 2-seed validation vs constitution Q3; ordering |
| PERF | Adopted | Breakdown aggregation O(terms), already computed — no concern |
| SEC, DB | N/A | No new secrets/checkpoint-load paths; no database |

### Phase 2 deep-dives (key findings)

- **ARCH** — New variant (vs in-place retune) is the **correct, reproducibility-preserving** call: `run_benchmark.py` derives run-dir partition + `reward_id` from `strategy_id`, so retuning V2 in place would silently change every prior `current/` run (breaks A/B; constitution T4/Q3). Subclass needs **`__init__` override only** (`reset()` reads `self.weights`, doesn't re-instantiate). **Over-correction risk confirmed**: unconditional `currently_visible` (current.py:372) + raised α could let a visible-but-no-capture episode rival the +40 terminal → lower `currently_visible` to 0.05–0.1 and keep small `two_step_cycle`/`stay_still` penalties.
- **DATA** — Reconciliation holds exactly: `RewardResult.breakdown` includes terminal terms and `team_return == total` broadcast to all ghosts, so per-term means sum to `mean_episode_return`. **`_build_variant_summary` builds its dict by explicit key enumeration** — must add `mean_reward_breakdown` explicitly (does not propagate via `pooled_stats`). `DictWriter(extrasaction="ignore")` ⇒ must append to both field lists.
- **TEST** — `test_eval_report.py::_episode` hardcodes `reward_breakdown={}` → needs a kwarg. Terminal-sign tests stay valid (no existing test asserts `current` terminal magnitudes; v3 adds new equality asserts). Calibration tests drive only default `current` → v3 must be injected explicitly. **Guardrail worst case is visible-every-step, not oscillation.**
- **DX** — Makefile line refs accurate; **liveplot takes no reward arg** (discovers run dirs) — confirm it finds `current_v3/` dirs. `@`-partition safe (`strategy_id` regex forbids `@`). Step 6 2-seed run must be labeled **non-authoritative**; recorded comparisons need ≥5 seeds (constitution Q3). Step ordering sound (measure → tune → flip → test → validate).

### Conflict check

No inter-perspective conflicts. ARCH (lower `currently_visible`, keep small oscillation penalties) and TEST (guardrail must bound the visible path) are mutually reinforcing.

### Plan Amendment (iteration 1)

All four deep-dive findings applied to the Steps section in place (Steps 1–6 above reflect the amendments): Step 1 (explicit `_build_variant_summary` key + test-helper kwarg + reconciliation note), Step 2 (lower `currently_visible` to 0.05–0.1, keep small `two_step_cycle`/`stay_still`), Step 3 (`__init__`-only override), Step 4 (liveplot needs no reward arg; verify v3 dir discovery), Step 5 (inject v3 directly; guardrail = visible-every-step episode), Step 6 (non-authoritative smoke; ≥5 seeds for recorded comparison; confirm benchmark eval emits the column). Core approach (measurement-first, additive variant) preserved.

### Execution Metrics

| Metric | Value |
|--------|-------|
| Deep-dives used | 4/6 |
| Iterations | 1/3 |
| Perspectives shortlisted | 6 (SEC/DB → N/A; +DATA) |
| Adopted | 1 (PERF) |
| Deferred-then-amended | 4 (ARCH, TEST, DATA, DX) |
| Convergence | All findings produced concrete, non-conflicting amendments; terminated iteration 1 |

## Implementation summary

**Status:** Steps 1–5 complete (`- [x]`); Step 6 partial (`- [~]`) — the diagnostic half ran; the full multi-seed A/B training benchmark is left for the user (long CPU job).
**Mode:** manual | **Iterations:** n/a | **Rollback branch:** `pre-plan-000028`

### What shipped (per-step commits)
- **Step 1** (`eval_report.py`, `test_eval_report.py`): per-term means aggregated in `_aggregate_episodes`, explicit key added in `_build_variant_summary`, `mean_reward_breakdown` JSON column appended to `REPORT_FIELDS` + `VARIANT_FIELDS`. `_episode` test helper gained a `reward_breakdown` kwarg; 2 new tests assert decoded per-term means.
- **Steps 2–3** (`current.py`, `loader.py`): `CurrentRewardWeightsV3` (terminals unchanged; `repeated_direction_reversal=0.0`, `two_step_cycle=-0.02`, `stay_still=-0.02`, `invalid_move=-0.02`, `valid_move=0.05`, `potential_shaping_alpha=2.0`, `currently_visible=0.08`) + `PursuitFirstTeamReward` (`strategy_id="current_v3"`, `__init__`-only override) registered as `current_v3`.
- **Step 4** (`Makefile`): `REWARDS`/`REWARD_ID` default to v3 (prior V2 defaults kept commented; one-line revert). liveplot confirmed to need no reward arg.
- **Step 5** (`test_reward_strategies.py`): 4 tests — registration/load, terminal weights == V2, move-toward > stay > away (direct v3 drive), 200-step visible-every-step shaping < `get_pacman`.

### Diagnostic result (Step 6, partial — the key empirical finding)
Ran `eval_report` on an existing V2 final checkpoint (`iql … checkpoint_200000.pt`, 5 episodes). The new `mean_reward_breakdown` reconciles **exactly** to `mean_episode_return = −162.43`, and pinpoints the dominant penalties:

| Term | Mean reward |
|---|---|
| `repeated_direction_reversal` | **−115.65** |
| `two_step_cycle` | **−46.80** |
| `PACMAN_TIMEOUT_WIN` (terminal) | −35.00 |
| `timestep` | −2.00 |
| `currently_visible` | +1.80 |
| `potential_shaping` | +16.20 |
| `valid_move` | +18.00 |

This **confirms the revised diagnosis** (research-000027): the −162 is owned by the anti-oscillation penalties (the ghost thrashes/ping-pongs; `repeated_direction_reversal` multiplies up to ×4 per streak), **not** by stalking (`currently_visible` only +1.8). V3 zeros `repeated_direction_reversal` and softens `two_step_cycle` → removes ~−160 of penalty mass directly.

### Quality gate
- `test_reward_strategies.py`, `test_reward_calibration.py`, `test_eval_report.py`, `test_algorithm_utils.py`, `test_liveplot.py`: **35 passed, 1 failed**. `test_petting_zoo.py` + `test_pallet_win.py`: **16 passed**.
- The single failure — `test_stronger_movement_variant_changes_only_one_weight` — is **pre-existing and unrelated** to this plan (verified failing on `pre-plan-000028`): `StrongerMovementReward` is built on V1 `CurrentRewardWeights` (get_pacman=30) but the test compares it field-by-field against V2 `CurrentTeamReward` (get_pacman=40). Filed as **pa-000014** for separate fix (do not fix here — out of scope).

### Remaining manual work
- **Step 6 full validation**: run the A/B benchmark (`current` vs `current_v3`), ideally ≥5 seeds per constitution Q3 before recording any capture-rate comparison. The currently-running benchmark/liveplot is on the old `current` (V2) reward — restart it on `current_v3` to see the fix.
