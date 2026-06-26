# Plan 000026 | FIX-liveplot | 2026-06-26 12:24 UTC | Fix liveplot 3-part token parser | Review: light
plan_format_version: 1
source: research-000025

## User brief

Fix liveplot.py blank-plot regression: the `live_progress.csvl` token is now 3-part (`algorithm@reward_id@device`, e.g. `iql@current@cpu`) but `liveplot.py`'s `_parse_progress_file` splits on the first `@`, so the device label is read as `current@cpu` and `--device cpu` no longer matches, leaving the plot blank. Fix the parser to split on all `@`, take the first segment as algorithm and the last as the device label, and fold the middle `reward_id` segment into the run identity to avoid run collisions across reward classes. Add a smoke test that feeds a 3-part-token row through `_parse_progress_file` and asserts the device label is `cpu` (not `current@cpu`).

## Agent interpretation

- **Problem**: `make liveplot` (which passes `--device cpu`) renders an empty plot because the live-progress token gained a middle `reward_id` segment that the parser mis-attributes to the device label.
- **Approach**: Change the token decode in `_parse_progress_file` to split on every `@`: first segment = algorithm, last segment = device label, middle segment(s) = `reward_id`. Fold `reward_id` into the per-run dict key (`<reward_id>::<run_id>`) so runs from different reward classes don't overwrite each other under the same `(algorithm, device)`. This restores the `--device cpu/cuda` filter and the cpu/cuda line styling, and is forward-compatible with multiple reward classes. No writer change needed — the producer (`run_benchmark.py`) already emits the canonical 3-part token.
- **Alternatives rejected**:
  - *Change `run_benchmark.py` to drop `reward_id` from the token*: rejected — `reward_id` is intentional (rewards-system refactor, commit `8b20c74`) and is needed once multiple reward classes coexist; the reader is the side that's out of date.
  - *Match the device selector against the trailing segment while keeping the full `reward_id@device` as the dict key*: rejected — leaves `reward_id@device` in legends and breaks `_line_style_for_device` (cpu/cuda styling); folding `reward_id` into the run key is cleaner and keeps the existing `algorithm -> device -> run` data model intact.
- **Selection rationale** (source: research-000025):
  - Included: R1 (HIGH) — fix the 3-part token parser; the core of this plan.
  - Included: R2 (MEDIUM) — add a smoke test asserting device parses to `cpu`.
  - Excluded: R3 (LOW) — shared encode/decode helper across `run_benchmark.py` and `liveplot.py`; deferred as a follow-up refactor, out of scope for this regression fix.

## Files

- Modified: [benchmarl_setup/liveplot.py](benchmarl_setup/liveplot.py) — token decode in `_parse_progress_file` (lines ~78-89)
- Created: [test/test_liveplot.py](test/test_liveplot.py) — smoke test for the parser

## Root cause

The live-progress label key changed from the device alone (`cpu`) to `f"{reward_id}@{cfg['label']}"` (`current@cpu`) in commit `8b20c74` ("refactor: isolate rewards system"). The emitted token is therefore `algorithm@reward_id@device` (e.g. `iql@current@cpu`). `liveplot.py`'s `_parse_progress_file` still does `algorithm_token.split("@", 1)`, yielding `algorithm="iql"`, `label="current@cpu"`. The device filter (`self.device_selector in by_device`) then fails for `--device cpu` (the Makefile default), so no series are selected and the plot is blank. See research-000025 for the full diagnosis.

## Best practices

- Keep the parser tolerant of legacy 2-part tokens (`algorithm@device`) and bare tokens (algorithm only) for backward compatibility with older progress files.
- Normalize segments with `strip().lower()` consistently, matching the existing code's casing rules.
- Place the test alongside existing `test/test_*.py`; reuse the established `sys.path` bootstrap, extended to put `benchmarl_setup/` on the path (liveplot.py uses top-level imports `from algorithm_utils import ...`).

## Design decisions

- **User-visible impact**: `make liveplot` (and any `liveplot.py --device cpu|cuda`) again renders capture/reward curves during a benchmark, with correct cpu/cuda line styling. No CLI surface changes.
- **Trade-offs accepted**: Gained correct device filtering and forward-compatibility with multiple reward classes; the run-identity key now embeds `reward_id`, so a single chart still aggregates only runs that share `(algorithm, device, reward_id)` — intended behavior. No writer changes, minimizing blast radius.
- **Metacommunication impact**: I now correctly tell you, through the live plot, which device each algorithm is training on — the device legend reads `cpu`/`cuda` again instead of being silently empty, so you can trust that an empty plot means "no data yet," not "filter mismatch."

## Steps

### Step 1 — Decode the 3-part token in `_parse_progress_file`

- [ ] Replace the first-`@`-only split with a full split that extracts algorithm (first segment), device label (last segment), and `reward_id` (middle segment(s)); fold `reward_id` into the per-run dict key.
- Files: `benchmarl_setup/liveplot.py`
- References: research-000025 § Recommended fix
- Interface: `_parse_progress_file(progress_file)` return type unchanged (`algorithm -> device_label -> run_key -> step -> (frame, capture_pct, reward)`); `run_key` now `"<reward_id>::<run_id>"`.
- Details: Replace lines ~78-89:
  ```python
  token_parts = [part.strip() for part in algorithm_token.split("@")]
  algorithm = token_parts[0].lower()
  if len(token_parts) >= 3:
      reward_id = "@".join(token_parts[1:-1]).lower() or "default"
      label = token_parts[-1].lower() or "default"
  elif len(token_parts) == 2:
      reward_id = "default"
      label = token_parts[1].lower() or "default"
  else:
      reward_id = "default"
      label = "default"

  if not algorithm:
      continue

  run_key = f"{reward_id}::{run_id}"
  data[algorithm][label][run_key][step] = (frame, capture_pct, reward)
  ```
- Verify: Run `py -3.11 benchmarl_setup/liveplot.py --algorithms iql,vdn,qmixlocal,qmixglobal --maze pinklike3 --device cpu` against an existing `live_progress.csvl`; confirm series are drawn (non-blank plot).
- Tests: When `_parse_progress_file` reads a row with token `iql@current@cpu`, the returned data has the run under `data["iql"]["cpu"]` (device label `cpu`, not `current@cpu`).

### Step 2 — Add parser smoke test

- [ ] Create `test/test_liveplot.py` that writes a small `live_progress.csvl` (with `#meta` line + a 3-part-token row), calls `_parse_progress_file`, and asserts the device label key is `cpu`. Add a second assertion that two rows differing only in `reward_id` produce distinct run keys under the same `(algorithm, device)`.
- Files: `test/test_liveplot.py`
- References: `test/test_algorithm_utils.py` (sys.path bootstrap pattern)
- Interface: N/A
- Details: Bootstrap `sys.path` with both `PROJECT_ROOT` and `PROJECT_ROOT / "benchmarl_setup"` (liveplot.py uses top-level imports), then `import liveplot`. Use `tmp_path` for the csvl file.
- Verify: `py -3.11 -m pytest test/test_liveplot.py -q` passes.
- Tests: With a csvl containing `iql@current@cpu,run_a,1,200.0,nan,-0.17`, `_parse_progress_file` returns a dict where `"cpu" in data["iql"]` is True and `"current@cpu" not in data["iql"]`.

## Review log

### Phase 1 — Perspective triage (light, FIX prefix)

Shortlist for FIX: COR (correctness), TEST (testability), REG (regression), DX (developer experience). Others marked N/A.

| Perspective | Status | Concern |
|---|---|---|
| COR (correctness) | Adopted | Parser now extracts device from the correct segment; legacy 2-part and bare tokens still handled. |
| REG (regression) | Adopted | Folding `reward_id` into the run key prevents cross-reward-class run collisions that would otherwise silently aggregate; backward-compatible with old 2-part progress files. |
| TEST (testability) | Adopted | Step 2 adds a direct unit test of the decode contract that just drifted; pins device-label extraction. |
| DX (developer experience) | Adopted | `make liveplot` works again with zero workflow change; empty plot now unambiguously means "no data." |
| SEC, PERF, A11Y, I18N, others | N/A | No security, performance, accessibility, or i18n surface. |

No Deferred concerns → no Phase 2.

#### Execution Metrics

| Metric | Value |
|---|---|
| Review depth | light (Phase 1 only) |
| Action steps | 2 |
| Files touched | 2 |
| Perspectives evaluated | 4 (COR, REG, TEST, DX) |
| Phase 2 deep-dives | 0 |
| Iterations | 1 |

## Outcomes

- `liveplot.py --device cpu|cuda` renders capture/reward curves again during benchmarks.
- cpu/cuda line styling restored (device label is `cpu`/`cuda`, not `current@cpu`).
- A regression test pins the 3-part-token decode contract.

## smoke

false
