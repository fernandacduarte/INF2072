# Research 000025 | fernanda-INF2072 | 2026-06-26 12:12 UTC | liveplot blank — reward_id token regression
tags: liveplot, benchmark, regression, rewards-refactor, device-filter
spawned: plan-000026

## User brief

> liveplot: `$(PYTHON) benchmarl_setup/liveplot.py --algorithms $(ALGOS) --maze $(MAZE) --device $(DEVICE)` is not showing anything. investigate what changed.

## Agent interpretation

`make liveplot` runs the live monitor but the plot stays empty (no capture/reward lines), even though a benchmark is producing data in `live_progress.csvl`. Goal: find the regression and recommend a fix.

## Files

- [benchmarl_setup/liveplot.py](benchmarl_setup/liveplot.py) — the monitor; token parser at lines 78–89, device filter at lines 347–353
- [benchmarl_setup/run_benchmark.py](benchmarl_setup/run_benchmark.py) — writes `live_progress.csvl`; label key construction
- [Makefile](Makefile) — `DEVICE ?= cpu`, `liveplot` target passes `--device $(DEVICE)`
- `benchmarl_setup/runs/pinklike3/live_progress.csvl` — evidence of the token format

## Root cause

The live-progress rows now carry a **three-part token** `algorithm@reward_id@device`, e.g.:

```
iql@current@cpu,iql_pacman_mlp__96aa06cb_...,1,200.0,nan,-0.16969...
```

But `liveplot.py`'s parser still assumes a **two-part token** `algorithm@device`. It splits on the *first* `@` only:

```python
# liveplot.py:78-83
if "@" in algorithm_token:
    algorithm, label = algorithm_token.split("@", 1)   # -> "iql", "current@cpu"
    label = label.strip().lower()
```

So the device label becomes `current@cpu` instead of `cpu`. The device filter then can't match:

```python
# liveplot.py:347-350
if self.device_selector == "all":
    selected_labels = sorted(by_device.keys())
else:
    selected_labels = [self.device_selector] if self.device_selector in by_device else []
```

`make liveplot` passes `--device cpu` (Makefile `DEVICE ?= cpu`). `_normalize_device_selector("cpu")` → `device_label("cpu")` → `"cpu"`. But `by_device` keys are `{"current@cpu"}`, so `"cpu" in by_device` is **False** → `selected_labels = []` → no series drawn → **blank plot**.

### What changed

This was **not** broken by the most recent commit `4142e1e` (true-capture rework) — that commit kept the same 3-part token. The regression was introduced earlier by:

```
8b20c74  refactor: isolate rewards system
```

Before `8b20c74`, the live-progress label key was just the device (`cfg['label']`, e.g. `cpu`), so the token was `iql@cpu` and `--device cpu` matched. That refactor changed the key to `f"{reward_id}@{cfg['label']}"` (`current@cpu`), inserting a middle `reward_id` segment. `liveplot.py`'s parser was never updated to account for it, so the device filter has been silently failing for any explicit `--device <cpu|cuda>` ever since.

### Why it sometimes "half-works"

With `--device all`, `selected_labels` takes *all* keys, so lines do appear — but under the label `current@cpu`, and `_line_style_for_device("current@cpu")` doesn't recognize cpu/cuda, so the cpu/cuda dashed/solid styling is also lost. The Makefile default (`--device cpu`) hits the fully-blank case.

## Recommendations summary

1. **[HIGH] Fix the token parser in `liveplot.py` to handle the 3-part `algorithm@reward_id@device` token.** Split on all `@`, take the first segment as algorithm and the **last** as the device label (so `--device cpu` matches again), and fold the middle `reward_id` segment into the run identity to avoid collisions when multiple reward classes are present. Sketch:

   ```python
   parts = algorithm_token.split("@")
   algorithm = parts[0].strip().lower()
   if len(parts) >= 3:
       reward_id = "@".join(parts[1:-1]).strip().lower()
       label = parts[-1].strip().lower()
   elif len(parts) == 2:
       reward_id = "default"
       label = parts[1].strip().lower()
   else:
       reward_id, label = "default", "default"
   # disambiguate runs across reward_ids:
   data[algorithm][label][f"{reward_id}::{run_id}"][step] = (frame, capture_pct, reward)
   ```

   This restores both the `--device cpu/cuda` filter and the cpu/cuda line styling, and is forward-compatible with multiple reward classes.

2. **[MEDIUM] Add a smoke test** that feeds a sample `live_progress.csvl` row with the 3-part token through `_parse_progress_file` and asserts the device label is `cpu` (not `current@cpu`). This guards the writer/reader contract that just drifted — the two formats live in separate files with no shared constant.

3. **[LOW] Consider a single source of truth for the token format.** The token is built in `run_benchmark.py` and re-parsed in `liveplot.py` independently. A shared helper (e.g. in `algorithm_utils.py`) to encode/decode `algorithm@reward_id@device` would prevent this class of drift recurring.

## Q&A log

**Q1 (2026-06-26 12:12 UTC):** liveplot `--device $(DEVICE)` shows nothing — investigate what changed.

**A1:** The live-progress token format changed from `algorithm@device` to `algorithm@reward_id@device` (e.g. `iql@current@cpu`) in commit `8b20c74` ("refactor: isolate rewards system"). `liveplot.py` still parses with `split("@", 1)`, so the device label is read as `current@cpu`. The Makefile's default `--device cpu` no longer matches that key, so the device filter selects nothing and the plot stays blank. (The latest commit `4142e1e` did not cause this; it kept the same 3-part token.) Fix: update `liveplot.py`'s parser to extract the device from the last `@` segment and keep `reward_id` in the run identity (Rec 1).
