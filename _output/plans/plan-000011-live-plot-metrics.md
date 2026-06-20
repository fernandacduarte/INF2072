# Plan 000011 | FEAT live plot: win rate and other metrics | 2026-06-20 16:22 UTC | Review: light
plan_format_version: 1

## User Brief

add feat to live plot: win rate and other metrics

## Agent Interpretation

**Problem:** `liveplot.py` shows only the step-level mean reward. Researchers watching a benchmark run see a single curve and cannot tell whether ghosts are actually winning episodes or just accumulating less-negative rewards.

**Approach:** Extend the live-progress pipeline with two additional scalar channels (ghost episode reward and training loss), widen the csvl format to carry them, and switch the plotter to a three-panel horizontal layout: step reward | ghost episode reward (win proxy) | training loss.

- Ghost episode reward (`collection_ghost_reward_episode_reward_mean`) is chosen as the win-rate proxy because it maps directly to the ghost catch signal (positive = Pacman captured in that collection window). A true per-episode win rate is not derivable from BenchMARL scalars without episode-level indexing.
- Training loss (`train_ghost_loss`) shows convergence quality alongside reward.
- The csvl format gains two optional columns (backward-compatible: older readers that only parse 5 columns continue to work; liveplot detects missing columns and leaves panels empty).

**Alternatives rejected:**
- Adding a `win_rate` column derived from `ghost_ep_reward > 0`: requires episode-level granularity not available in aggregate scalars; misleading if treated as a rate.
- Running `eval.py` from within the benchmark loop: too expensive; eval requires loading a checkpoint.

## Best Practices

- Backward-compatible csvl extension (parse cols 6–7 if present; fill NaN if absent).
- Each subplot has its own y-axis and autoscales independently.
- ProgressReporter reads only the file names it already knows (no dynamic discovery), keeping the polling loop fast.

## Design Decisions

**User-visible impact:** The live plot window changes from one panel to three horizontal panels. Labels update to include `(n=K)` seed count on all panels. The window default changes from `(10, 5)` to `(18, 5)` to keep panels legible.

**Trade-offs accepted:** Wider figure is slightly more demanding on narrow monitors; three panels at once give richer signal with no extra CLI flags needed.

**Metacommunication impact:** I now show you three metrics simultaneously so you can tell at a glance whether the ghost reward is becoming positive (coordination is working) and whether training loss is decreasing (learning is progressing) — not just whether reward is going up.

## Steps

- [ ] **Step 1 — Extend ProgressReporter to write ghost_ep_reward and loss columns**
  - Files: `benchmarl_setup/run_benchmark.py`
  - References: `benchmarl_setup/liveplot.py` (consumer format)
  - Interface: csvl line format becomes `algorithm,run_id,step,frame,reward,ghost_ep_reward,loss` (columns 6–7 are float or empty string when the scalar CSV has no data yet)
  - Verify: run `py -3.11 benchmarl_setup/run_benchmark.py --algorithms iql --seeds 0 --max-frames 2000` and confirm `live_progress.csvl` lines have 7 comma-separated fields
  - Tests: N/A (no business logic; observable via csvl file content)

- [ ] **Step 2 — Update `_parse_progress_file` to parse new columns**
  - Files: `benchmarl_setup/liveplot.py`
  - References: Step 1 Interface
  - Interface: return type expands to `dict[str, dict[str, dict[int, tuple[float, float, float, float]]]]` (frame, reward, ghost_ep_reward, loss); callers receive `(frame, reward, ghost_ep_reward, loss)` 4-tuple; ghost_ep_reward and loss are `float("nan")` when column absent
  - Verify: parse a hand-crafted 5-column and 7-column csvl string and confirm tuple lengths
  - Tests: N/A (format parsing; covered by visual verification)
  - Depends on: Step 1

- [ ] **Step 3 — Update `_aggregate_algorithm_runs` to aggregate all four channels**
  - Files: `benchmarl_setup/liveplot.py`
  - References: Step 2 Interface
  - Interface: returns `(frames, mean_reward, std_reward, mean_ghost_ep, std_ghost_ep, mean_loss, std_loss, n_runs)`; NaN-tolerant aggregation reused for new channels
  - Verify: function returns 8-tuple; NaN columns produce NaN means without crashing
  - Tests: N/A
  - Depends on: Step 2

- [ ] **Step 4 — Switch `LiveComparisonPlotter` to three-panel layout**
  - Files: `benchmarl_setup/liveplot.py`
  - References: Step 3 Interface; `product-design/project/design-standards.md` §Reward Plot Style
  - Interface: `fig, (ax_reward, ax_ghost_ep, ax_loss) = plt.subplots(1, 3, figsize=(18, 5))`; panel titles: "Step Reward", "Ghost Ep. Reward (win proxy)", "Training Loss"; legend on each active panel; loss panel y-axis inverted when all values negative is NOT done (loss can be positive); each panel autoscales independently
  - Verify: launch liveplot with an active benchmark and confirm three panels render with distinct curves per algorithm
  - Tests: N/A (visual output)
  - Depends on: Step 3

## Outcomes

- `live_progress.csvl` carries 7 fields per line: algorithm, run_id, step, frame, reward, ghost_ep_reward, loss.
- `liveplot.py` displays a three-panel figure: step reward, ghost episode reward (win proxy), training loss.
- Old csvl files (5-column) are still parsed without error; panels 2–3 remain empty.
- No new CLI flags required; `--window` applies to all three panels.

smoke: false
