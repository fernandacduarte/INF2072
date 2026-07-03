# Communication 000048 | EVL | 2026-07-01 | Evaluators

> CTOs, tech leads, and engineering managers assessing the soundness of this project's reward-shaping design.

## Project Overview

fernanda-INF2072 is a custom multi-agent Pacman RL environment built for PUC-Rio's INF2072 course. Ghosts are cooperative agents trained with BenchMARL (IQL, VDN, QMIX) to coordinate and capture a Pacman that runs its own fixed, evasion-aware policy. The engineering bar for this kind of project is reproducibility and honest reporting of what a given reward design does and does not solve -- the reward function is the primary lever available to change ghost behavior, so its design history is a first-class engineering artifact, not an implementation detail.

This brief covers one specific reward configuration in that history: `capture_v0_closing`.

## What Problem This Reward Solves

The project's reward logic is pluggable: multiple reward-strategy classes implement a common interface and are selected at run time via a strategy loader, so different reward designs can be A/B tested without touching training code. `capture_v0_closing` is one strategy in that family (alongside `capture_v0`, `capture_v0_pure_potential_shaping`, and others).

The strategy immediately before it, `capture_v0_pure_potential_shaping`, implemented classic potential-based reward shaping (PBRS, Ng/Harada/Russell 1999) with an exact telescoping sum (discount factor of 1). PBRS has a well-known theoretical guarantee: it does not change the optimal policy, because the shaping reward over an episode collapses to `Phi(end) - Phi(start)` regardless of the path taken.

That guarantee turned out to be the bug. Internal diagnosis (research-000035) found that against a hard, evasive Pacman that holds its distance from the ghost team roughly constant, the telescoping sum nets to approximately zero over an episode. The team could spend an entire episode pursuing Pacman and be paid nothing net for it. The learned policy responded rationally to that incentive: it stopped chasing.

`capture_v0_closing` is the fix, and it is a deliberate trade-off, not a free improvement: it replaces the policy-invariant, telescoping shaping term with a persistent, non-telescoping per-step reward for reducing distance to Pacman. The team gives up PBRS's optimality-preservation guarantee in exchange for an incentive that survives contact with an evader who tries to run out the clock. That is the central engineering judgment call in this design, and it is the one worth scrutinizing.

## How the Reward Is Structured

`capture_v0_closing` is implemented as `CaptureV0ClosingReward` in `custom_environment/env/rewards/current.py`, subclassing `CaptureV0Reward` (which itself subclasses `CurrentGitTeamReward`). It reuses existing BFS-distance and legal-move-counting helpers from its parent classes rather than duplicating them. Weights live in a separate `CaptureV0ClosingRewardWeights` dataclass, which keeps tuning changes isolated from the reward logic itself.

Terminal (episode-ending) signals:

| Condition | Value |
|---|---|
| Ghosts capture Pacman | +100.0 |
| Pacman survives to timeout | -100.0 |
| Pacman clears all pellets | -100.0 |

Per-step signals:

| Term | Value | Purpose |
|---|---|---|
| Timestep cost | -0.05 every step | Cost of time passing; discourages stalling |
| Closing reward | `2.0 * clip(prev_mean_distance - current_mean_distance, -2.0, +2.0)` | Persistent pursuit incentive, described below |
| Containment bonus | +0.5 | Rewards reducing Pacman's legal-move count, described below |

### The closing term: why mean distance, and why clipped

The closing term is computed from the mean BFS-graph distance across all ghosts to Pacman's true position on the board -- not the minimum distance of the nearest ghost. This is a deliberate choice with a specific failure mode in mind: if the reward only responded to whichever ghost happens to be closest, the other ghosts have no gradient pushing them toward Pacman and tend to park in a corner, leaving a single pursuer that a competent evader can out-run indefinitely. Mean distance gives every ghost on the team a gradient toward Pacman on every step, which is what produces the coordinated "surround" behavior the project is trying to elicit -- this is the actual mechanism connecting the reward design to the multi-agent coordination goal, not just a scalar tuning choice.

The per-step delta is clipped to +/-2.0 before being weighted. This closes a specific exploit identified earlier in the project (labeled RC4 in research-000022): without a clip, a ghost could "farm" the closing reward by oscillating in and out at the edge of a safe-distance cordon around Pacman, collecting reward for large swings without ever committing to a capture. The clip caps how much any single step can pay out, removing the incentive to game the metric rather than pursue.

The weight on this term, 2.0, is a calibration choice: because mean distance moves roughly half as fast as minimum distance would with two ghosts, doubling the weight keeps the signal magnitude comparable to the reward design that preceded this family, avoiding an implicit change in how strongly pursuit is weighted relative to the other terms.

A property worth calling out because it is easy to get wrong when reasoning about non-telescoping rewards: in-place oscillation (the team closing distance one step and giving it back the next) nets to approximately zero, because the positive and negative per-step deltas cancel directly. The design intentionally keeps that cancellation local to oscillation, not global to the episode -- which is exactly the distinction that fixes the passivity bug in the PBRS predecessor.

### The containment term

A separate, smaller bonus (+0.5) rewards the team when Pacman is visible and its number of legal moves (BFS-adjacent free cells) has decreased from the previous step. This is a herding signal: closing distance alone does not guarantee a capture against a smart evader with room to maneuver, so this term specifically rewards the team for reducing Pacman's escape options, i.e., pushing it toward corners and dead ends. It is the term that is supposed to convert "we are close" into "we can actually catch it."

## Scope Boundaries

This is a deliberately narrow, sparse-plus-one-signal reward. It does not include several shaping terms present in sibling strategies in the same codebase:

- No movement-quality shaping (no penalties for invalid moves, staying still, reversing direction, or ghosts overlapping the same corridor) -- those exist in the `current` / `current_git` variants but were stripped here.
- No visibility or exploration bonuses.
- No per-pellet penalty (that lives in a separate variant, `capture_v0_pure_potential_shaping_pellets`).

The intent is that the closing and containment terms carry the full weight of the pursuit incentive, with as little else competing for gradient as possible.

## Test Coverage

The closing-reward logic has a dedicated unit test file, `test/test_closing_reward.py`, that exercises the mechanism in isolation on a synthetic corridor board (so BFS distance reduces to a simple column difference). It verifies, independently of training: that the strategy registers and loads correctly by ID; that closing distance pays the expected positive reward; that backing off pays the expected negative reward; that a large jump in distance is correctly clipped rather than paid in full; and that in-place oscillation nets to zero. This gives confidence that the reward mechanics match the design intent described above, independent of whether a given training run converges.

## What to Watch

The trade-off this design makes -- give up PBRS's policy-invariance guarantee to get a persistent pursuit signal -- is explicit and well-reasoned given the diagnosed failure mode, but it is still a trade-off. A non-telescoping, hand-clipped reward term does not carry a theoretical optimality proof the way PBRS does; its correctness rests on empirical validation (the accompanying test suite, plus benchmark results against the evasive Pacman) rather than a guarantee. That is a reasonable and clearly documented choice for a research project at this scale, but it is the point at which a reviewer should look for benchmark evidence that the closing incentive actually improves capture rate against the hard Pacman policy, rather than accepting the mechanism as sufficient on its own.
