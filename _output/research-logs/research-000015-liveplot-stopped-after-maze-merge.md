# Research 000015 | fernanda-INF2072 | 2026-06-20 19:35 UTC | liveplot stopped working after maze-options merge

tags: liveplot, maze-layout, makefile, regression, benchmarl

**User brief:** after merge that introduced maze options and multiple folders output make liveplot stopped working

**Agent interpretation:** PR #12 (`maze_layout_separate_training_report_improvements`) introduced maze-namespaced output folders — training now writes to `benchmarl_setup/runs/<maze>/`. The live progress file is written under the same maze subfolder. After the merge, `make liveplot` silently watches the wrong path and shows nothing.

**Files examined:**
- `Makefile`
- `benchmarl_setup/liveplot.py`
- `benchmarl_setup/run_benchmark.py`
- `benchmarl_setup/algorithm_utils.py`
- git diff of merge commit `5547a72`

---

## Q&A Log

**Q1:** After the merge that introduced maze options and multiple-folder outputs, `make liveplot` stopped working. Why?

**A1:**

### Root Cause

The merge (PR #12) changed the training output layout so that all experiment artifacts — including the live progress file — are now written under a maze-namespaced subfolder:

```
benchmarl_setup/runs/<maze>/live_progress.csvl   # written by run_benchmark.py
benchmarl_setup/runs/<maze>/<run_dirs>/           # training checkpoints/logs
```

`run_benchmark.py` correctly uses `runs_root_for_maze(Path(args.save_folder), args.maze)` to compute this path.

`liveplot.py` also supports `--maze` and correctly builds `maze_runs_root / "live_progress.csvl"`. But its default is `--maze default`.

The Makefile `liveplot` target:
```makefile
liveplot:
    $(PYTHON) benchmarl_setup/liveplot.py --algorithms $(ALGOS)
```
…does **not** pass `--maze $(MAZE)`.

Meanwhile the `benchmark` target uses `MAZE ?= pinklike` (the Makefile default). So:

- `make benchmark` → writes to `benchmarl_setup/runs/pinklike/live_progress.csvl`
- `make liveplot` → watches `benchmarl_setup/runs/default/live_progress.csvl` (doesn't exist)

Liveplot starts, prints the path it's watching, finds no file, and polls forever with an empty plot.

### Fix

One line in the Makefile:

```makefile
# Before
liveplot:
    $(PYTHON) benchmarl_setup/liveplot.py --algorithms $(ALGOS)

# After
liveplot:
    $(PYTHON) benchmarl_setup/liveplot.py --algorithms $(ALGOS) --maze $(MAZE)
```

This ensures liveplot always watches the same maze subfolder that `make benchmark` writes to, regardless of what `MAZE` is set to.

### Why it wasn't caught

The liveplot `--maze` argument already existed (it was added as part of the maze feature), but the Makefile wiring was missed. The tool doesn't error on a missing progress file — it silently waits, which makes the failure look like the tool is "just not updating yet."

---

## Recommendations Summary

1. **(HIGH) Add `--maze $(MAZE)` to the Makefile `liveplot` target** — one-line fix; restores liveplot for all maze variants. `Makefile:60`.
