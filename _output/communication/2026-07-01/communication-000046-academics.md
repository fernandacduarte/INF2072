# Communication 000046 | ACD | 2026-07-01 20:02 UTC | Academics

# Potential-Based Reward Shaping in the Ghost-Coordination Environment

## Why this note exists

If you are working on a MARL project for INF2072, you have probably run into the same problem we ran into: a sparse terminal reward (capture Pacman, or don't) gives almost no learning signal for most of an episode, but naive dense shaping risks changing what the optimal policy actually is. Potential-based reward shaping (PBRS) is the standard tool for adding reward density without that risk. This note explains what PBRS guarantees, how we used it in the cooperative-ghost Pacman environment, where the guarantee itself became an obstacle, and how we are checking that any of this actually helps.

## 1. What PBRS is, and why it is theoretically safe

Ng, Harada, and Russell (1999) show that if you augment an MDP's reward function with a shaping term of the form

```
F(s, s') = gamma * Phi(s') - Phi(s)
```

for any potential function `Phi: S -> R`, and `gamma` is the same discount factor used by the learning algorithm, then the set of optimal policies for the shaped MDP is identical to the set of optimal policies for the original MDP. The shaping term is a telescoping quantity: summed over a trajectory it collapses to `gamma^T * Phi(s_T) - Phi(s_0)` (exactly `Phi(s_T) - Phi(s_0)` when `gamma = 1`), so it behaves like a potential-energy difference rather than an extra source of reward that a policy could exploit independently of the base task. This is the property that distinguishes PBRS from ad hoc dense-reward engineering: you get a denser gradient without the risk of the agent learning to farm the shaping term instead of solving the task. The theorem requires `Phi` to be a function of state only (not of action, and not time-varying in a way that breaks the telescoping), and it requires the same `gamma` on both sides -- get either wrong and the invariance guarantee no longer holds.

## 2. How the environment applies it, and why the potential function evolved

The cooperative-ghost Pacman environment used the shaping term long before it was isolated as "PBRS" in the code. The original git-baseline strategies, `CurrentGitTeamReward` (V1) and `CurrentTeamReward` (V2) in `custom_environment/env/rewards/current.py`, define

```
Phi(s) = -alpha * min_ghost_distance(s)
```

for V1, and a weighted two-nearest-ghost variant `Phi(s) = -alpha * (d1 + beta * d2)` for V2, where distance is BFS shortest-path distance on the grid (respecting walls), not Euclidean distance -- the metric that actually matches reachability in a maze. Each step emits `potential_shaping = Phi(s') - Phi(s)` as one term inside a much larger reward: visibility bonuses, exploration bonuses, anti-oscillation and anti-corridor-overlap penalties, and so on. This is a reasonable "kitchen sink" design for getting something working, but it makes it impossible to attribute any observed behavior change specifically to the shaping term -- there are a dozen confounded signals active at once.

`CaptureV0PurePotentialShaping` (`strategy_id = "capture_v0_pure_potential_shaping"`) was built to isolate the shaping term for causal analysis. The base reward is sparse: `GET_PACMAN = +100`, `PACMAN_TIMEOUT_WIN = -100`, `PACMAN_WIN_PALLETS = -100`, and a `timestep = -0.05` cost, nothing else. On top of that sits exactly one shaping term, with

```
Phi(s) = -alpha * mean_ghost_distance(s),  alpha = 0.7
```

using the mean BFS distance across all ghosts rather than the minimum. This min-versus-mean choice is the most interesting design decision here for anyone studying MARL specifically. With a shared team reward, a `min`-based potential only produces a gradient for whichever ghost happens to be nearest to Pacman at each step -- the other ghost's actions cannot move that minimum, so it receives a shaping signal it cannot influence, learns nothing useful from it, and empirically converges to parking in a corner. Switching the potential to the mean distance across all ghosts gives every ghost a component of the potential that responds to its own actions, so every ghost has a gradient toward Pacman. That is what produces the surrounding/coordination behavior this project is actually trying to study, rather than a single active pursuer and passive bystanders.

Two further choices in this strategy are worth flagging as implementation details that matter for correctness, not just style:

- **Exact undiscounted telescoping (`gamma = 1`).** Because `Phi <= 0` and shrinks toward zero as the team closes in, a discounted `gamma*Phi(s') - Phi(s)` with `gamma < 1` pays a strictly positive reward for any back-and-forth oscillation near Pacman (since `(1-gamma)*(-Phi) > 0` per cycle), which a greedy policy will farm. Setting `gamma = 1` makes the cumulative shaping over an episode exactly `Phi(end) - Phi(start)` regardless of the path taken, so in-place oscillation nets exactly zero shaping reward. This is a direct, practical instance of the telescoping property, not just theoretical furniture.
- **A deliberately enlarged `timestep` cost.** Once oscillation nets zero shaping reward, nothing else in the reward function penalizes standing still or camping near Pacman -- so `timestep` was raised from the more typical `-0.01`/`-0.015` used elsewhere in the codebase to `-0.05`, specifically to make camping unprofitable once the shaping term can no longer do that job.

`CaptureV0PurePotentialShapingPellets` extends the pure-PBRS strategy with a small penalty when Pacman eats a pellet, testing whether adding one more sparse signal alongside PBRS changes the learned behavior.

## 3. Where the policy-invariance guarantee became a liability

`research-000035` found a failure mode against a hard, evasive Pacman policy: if the team of ghosts maintains roughly constant distance from Pacman for an entire episode -- a pursuit stalemate -- then exact telescoping means the shaping reward sums to approximately `Phi(end) - Phi(start)` approximately zero. A policy that actively pursues Pacman all episode and one that does nothing productive both net roughly the same (near-zero) cumulative shaping reward if neither manages to close the distance. This is worth sitting with, because it is not a bug in the implementation; it is the theorem working exactly as advertised. Ng/Harada/Russell's guarantee is about final-policy optimality under the shaped MDP being identical to the unshaped MDP -- it says nothing about within-episode reward density against an adversary that can hold the potential roughly constant. Against a hard evader, that is precisely the scenario where the guarantee stops being useful: the theorem protects you from PBRS distorting the optimum, but it does not protect you from PBRS failing to provide a usable gradient in the first place.

`CaptureV0ClosingReward` is a direct response, and it is a deliberate departure from PBRS rather than a variant of it. Instead of a telescoping potential difference, it pays a persistent, non-telescoping per-step reward proportional to the reduction in mean team-BFS-distance to Pacman, clipped to bound how much a ghost can farm by oscillating at the edge of a safe-distance cordon. Because this term does not telescope, it does not cancel over an episode against an evader who holds distance -- the team is paid every step it closes in and charged every step it backs off, trading away PBRS's policy-invariance guarantee in exchange for an explicit directional pursuit bias. The honest way to describe this design is: PBRS's own invariance property was preserving the passivity that needed fixing, so the fix had to give up the invariance property on purpose. This is a useful teaching example of matching the tool to the failure mode rather than defending a technique past the point where its guarantee is doing the work you need.

## 4. How the shaping is actually checked for a causal effect

None of the above is meaningful without a control condition. `CaptureV0SparseControl` (`strategy_id = "capture_v0_sparse_control"`) is byte-identical to `CaptureV0PurePotentialShaping` except that the `potential_shaping` term is omitted entirely; it deliberately reuses the same weights dataclass so the terminal reward magnitudes and the `timestep` cost cannot drift between the two arms. This is the matched sparse-reward control for an A/B experiment (`plan-000031`) testing whether PBRS improves sample efficiency relative to sparse-only reward -- if you want to claim "PBRS helped," you need an arm where literally nothing else differs.

Comparisons across arms and algorithms (IQL/VDN/QMIX) follow the project's benchmarking-reporting standard (D-003, grounded in Papoudakis et al. 2021): mean plus 95% confidence interval across at least 5 seeds, with IQM (interquartile mean) and bootstrap confidence intervals per the small-sample-robust approach of Agarwal et al. (2021), a two-sided t-test (p < 0.05) to flag algorithms not significantly different from the best performer, both max-return and all-evals average-return reported, and a fixed greedy N-episode evaluation decoupled from training-time rollouts. This matters for the same reason the matched control matters: at n=5 seeds, a bare mean-over-runs comparison invites over-claiming, and a fixed greedy evaluation avoids conflating exploration noise during training with actual policy quality.

## 5. If you want to extend this

Reward strategies in this codebase are pluggable via a `module:Class` loader in `custom_environment/env/rewards/loader.py`, which accepts a class path string and validates/instantiates it against the shared `RewardStrategy` interface (`custom_environment/env/rewards/base.py`). If you want to try your own potential function -- a different distance metric, a different aggregation across ghosts, a discounted variant matched to the training algorithm's actual `gamma` -- you can implement a new `RewardStrategy` subclass following the pattern in `CaptureV0PurePotentialShaping` and pass its `module:Class` path via the `--reward-class` CLI flag rather than modifying the existing strategies in place. Given the min-versus-mean lesson above, anything with a shared team reward and more than one agent is worth checking for whether every agent actually receives a gradient it can act on before you assume the shaping term is doing what you designed it to do.

## References

- Ng, A. Y., Harada, D., & Russell, S. (1999). Policy invariance under reward transformations: Theory and application to reward shaping. *Proceedings of the Sixteenth International Conference on Machine Learning (ICML)*.
- Papoudakis, G., Christianos, F., Schafer, L., & Albrecht, S. V. (2021). Benchmarking multi-agent deep reinforcement learning algorithms in cooperative tasks. *NeurIPS Datasets and Benchmarks Track*.
- Agarwal, R., Schwarzer, M., Castro, P. S., Courville, A., & Bellemare, M. (2021). Deep reinforcement learning at the edge of the statistical precipice. *NeurIPS*.
