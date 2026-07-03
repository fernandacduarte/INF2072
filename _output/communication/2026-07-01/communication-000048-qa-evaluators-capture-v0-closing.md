# QA Log | Communication 000048 | 2026-07-01 20:08 UTC | Evaluators explainer for capture_v0_closing reward

## Brief Summary
User asked to explain the `capture_v0_closing` reward policy via `/communicate explique a politica de reward capture_v0_closing`. Audience was clarified as Evaluator (EVL), and a tailored Markdown/HTML explainer was generated.

## Q1
explique a politica de reward capture_v0_closing (invoked via `/communicate`)

## A1
Ran pre-skill (brief log, budget-eval with orphan-detection warning on a stale STARTED entry, pending-check surfacing 9 outstanding pending actions, ref-load of conventions/permissions/constraints, constitution). Asked the user which audience segment the explanation targets via AskUserQuestion (Evaluator / Client / End User / Academic); user selected **Evaluator (EVL)**.

Read `custom_environment/env/rewards/current.py` to extract ground truth on the `CaptureV0ClosingReward` strategy (`strategy_id = "capture_v0_closing"`, lines ~872-994): its motivation (fixing PBRS telescoping passivity diagnosed in research-000035), its weight dataclass (`get_pacman=100`, `pacman_timeout_win=-100`, `pacman_win_pellets=-100`, `timestep=-0.05`, `closing_weight=2.0`, `closing_clip=2.0`, `pacman_legal_moves_reduced=0.5`), the non-telescoping mean-BFS-distance closing term, the containment (legal-moves-reduced) bonus, its class hierarchy, and what shaping terms it deliberately omits versus sibling reward variants.

Reserved communication ID 000048, computed the output path `_output/communication/2026-07-01/communication-000048-evaluators.md`, and launched the `communication-generator` agent (as a general-purpose subagent) with this ground truth plus the standard project-context inputs (conventions, constitution, as-intended/as-coded fallbacks) to produce the CTO/tech-lead-register explainer.

The agent verified the ground truth directly against the source file and `test/test_closing_reward.py`, then wrote:
- `_output/communication/2026-07-01/communication-000048-evaluators.md`
- `_output/communication/2026-07-01/communication-000048-evaluators.html`
- updated the date-folder `index.md` / `index.html` (folder now holds multiple artifacts)

Content covers: brief project orientation, why `capture_v0_closing` replaces the PBRS-based `capture_v0_pure_potential_shaping` (telescoping summed to ~zero against a distance-holding evader, causing ghost passivity), the mechanics of the persistent (non-telescoping) mean-distance closing term and its clip/weight rationale, the legal-moves-reduced containment bonus, the pluggable reward-strategy architecture, what the variant deliberately omits, its test coverage, and a closing note that the design trades away PBRS's policy-invariance guarantee and should be validated with benchmark evidence.
