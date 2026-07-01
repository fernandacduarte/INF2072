"""R1 positive-control decision-readout (plan-000034, source research-000032).

Reads the *checkpoint-native* paired objective-evaluation CSVs produced by
``run_benchmark.py --eval-episodes`` for the two battery conditions and prints a
per-algorithm capture-rate table plus the verdict: was the ~40% "ceiling against
a random Pacman" a **confound** or a **genuine learning limit**?

Correctness note (discovered while implementing plan-000034): ``run_benchmark.py``
produces TWO families of eval CSVs:

* ``reward_eval_*`` (paired ``--eval-episodes`` eval) -- **checkpoint-native**
  (run with ``--allow-non-hard-checkpoint``), so capture_rate reflects the
  *training* opponent. This is what we read.
* ``evaluation_report_live_capture*`` (liveplot backfill) -- **hard-forced**, so
  capture_rate always reflects a hard evader regardless of training. We MUST NOT
  read these, or Condition P would falsely read ~40%. They are excluded by name.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

# Substrings that mark a hard-forced live-capture CSV -- never read these.
_LIVE_CAPTURE_MARKER = "evaluation_report_live_capture"


def _to_percent(raw: str) -> float | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    # capture_rate is stored as a fraction in [0, 1]; promote to percent.
    return value * 100.0 if value <= 1.0 else value


def read_capture_rates(save_folder: str | Path) -> dict[str, list[float]]:
    """Map algorithm -> list of checkpoint-native capture rates (percent).

    Prefers per-variant aggregates (``reward_eval_*_by_variant.csv``,
    ``capture_rate_mean`` per learner); falls back to per-seed rows
    (``reward_eval_*.csv``, ``capture_rate`` per train_seed). Hard-forced
    ``evaluation_report_live_capture*`` files are skipped.
    """
    root = Path(save_folder)
    rates: dict[str, list[float]] = {}
    if not root.exists():
        return rates

    def _accumulate(files: list[Path], value_column: str) -> bool:
        found = False
        for path in files:
            if _LIVE_CAPTURE_MARKER in path.name:
                continue
            with path.open("r", newline="", encoding="utf-8") as handle:
                for row in csv.DictReader(handle):
                    learner = (row.get("learner") or "").strip()
                    pct = _to_percent(row.get(value_column, ""))
                    if learner and pct is not None:
                        rates.setdefault(learner, []).append(pct)
                        found = True
        return found

    by_variant = sorted(root.glob("**/reward_eval_*_by_variant.csv"))
    if _accumulate(by_variant, "capture_rate_mean"):
        return rates

    # Fallback: per-seed paired-eval rows.
    per_seed = [
        p for p in sorted(root.glob("**/reward_eval_*.csv"))
        if "_by_variant" not in p.name
    ]
    _accumulate(per_seed, "capture_rate")
    return rates


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _best_mean(rates: dict[str, list[float]]) -> float:
    """Highest per-algorithm mean capture rate (the most-learned algorithm)."""
    return max((_mean(v) for v in rates.values()), default=0.0)


def verdict(
    p_rates: dict[str, list[float]],
    c_rates: dict[str, list[float]],
    threshold: float = 40.0,
) -> str:
    """Return a human verdict string given the two conditions' capture rates.

    * Condition P clears the ceiling (best algorithm well above threshold)
      -> the 40% was a CONFOUND (hard-forced eval / curriculum stage); skip the sweep.
    * Condition P also sits near/below threshold -> a GENUINE learning limit;
      the scalar UTD-axis sweep (research-000032 R4) is justified.
    """
    p_best = _best_mean(p_rates)
    c_best = _best_mean(c_rates)
    head = (
        f"Condition P (random opponent) best-algorithm capture = {p_best:.1f}% | "
        f"Condition C (curriculum) best-algorithm capture = {c_best:.1f}% | "
        f"reference line = {threshold:.0f}%."
    )
    if not p_rates:
        return head + " INCONCLUSIVE: no checkpoint-native eval rows for Condition P (did --eval-episodes run?)."
    if p_best >= threshold + 30.0:
        return (
            head
            + " VERDICT: CONFOUND -- the truly-random opponent IS learnable; the 40% came"
            " from the hard-forced live-capture eval / end-of-curriculum stage, not a"
            " hyperparameter limit. Fix the framing/eval and SKIP the sweep."
        )
    if p_best <= threshold + 10.0:
        return (
            head
            + " VERDICT: GENUINE LIMIT -- even the truly-random opponent plateaus near"
            " the ceiling. The scalar UTD-axis sweep (research-000032 R4) is justified."
        )
    return (
        head
        + " VERDICT: INCONCLUSIVE -- Condition P is between the clear-confound and"
        " genuine-limit bands; add seeds/frames or inspect learning curves before deciding."
    )


def _print_table(label: str, rates: dict[str, list[float]]) -> None:
    print(f"\n[{label}]")
    if not rates:
        print("  (no checkpoint-native reward_eval_* rows found)")
        return
    for learner in sorted(rates):
        values = rates[learner]
        mean = _mean(values)
        spread = max(values) - min(values) if values else 0.0
        print(f"  {learner:<12} capture = {mean:6.1f}%  (n={len(values)}, range {spread:.1f})")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--p-folder", required=True, help="Condition P save-folder (random opponent).")
    parser.add_argument("--c-folder", required=True, help="Condition C save-folder (curriculum).")
    parser.add_argument("--threshold", type=float, default=40.0, help="Reference ceiling (percent).")
    args = parser.parse_args(argv)

    p_rates = read_capture_rates(args.p_folder)
    c_rates = read_capture_rates(args.c_folder)

    print("R1 positive-control sanity battery -- checkpoint-native capture rates")
    _print_table("Condition P (curriculum off, random-prob 1.0)", p_rates)
    _print_table("Condition C (curriculum easy-medium-hard)", c_rates)
    print("\n" + verdict(p_rates, c_rates, args.threshold))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
