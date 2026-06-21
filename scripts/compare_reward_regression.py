"""Compare deterministic BenchMARL scalar series from the two A/B runs."""

from __future__ import annotations

import argparse
import csv
import math
import os
import tempfile
from pathlib import Path


def _find_scalars(run_root: Path) -> Path:
    candidates = [
        path
        for path in run_root.rglob("scalars")
        if (path / "collection_reward_reward_mean.csv").exists()
    ]
    if len(candidates) != 1:
        raise RuntimeError(
            f"Expected exactly one scalar directory under {run_root}, found {len(candidates)}."
        )
    return candidates[0]


def _read_numeric_rows(path: Path) -> list[tuple[float, ...]]:
    rows = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.reader(handle):
            try:
                rows.append(tuple(float(value) for value in row))
            except ValueError:
                continue
    return rows


def _difference(left: float, right: float) -> float:
    if math.isnan(left) and math.isnan(right):
        return 0.0
    return abs(left - right)


def main() -> None:
    default_root = Path(
        os.environ.get(
            "REWARD_REGRESSION_ROOT",
            str(Path(tempfile.gettempdir()) / "inf2072_reward_regression"),
        )
    )
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=default_root)
    parser.add_argument("--tolerance", type=float, default=1e-8)
    args = parser.parse_args()

    old_scalars = _find_scalars(args.root / "main")
    new_scalars = _find_scalars(args.root / "refactored")
    old_files = {path.name: path for path in old_scalars.glob("*.csv")}
    new_files = {path.name: path for path in new_scalars.glob("*.csv")}
    metric_names = sorted(
        name
        for name in old_files.keys() & new_files.keys()
        if not name.startswith("timers_")
    )

    failed = False
    print(f"Main scalars:       {old_scalars}")
    print(f"Refactored scalars: {new_scalars}")
    print(f"Tolerance:          {args.tolerance:g}\n")
    for name in metric_names:
        old_rows = _read_numeric_rows(old_files[name])
        new_rows = _read_numeric_rows(new_files[name])
        if len(old_rows) != len(new_rows):
            print(f"DIFF {name}: row counts {len(old_rows)} != {len(new_rows)}")
            failed = True
            continue
        max_difference = 0.0
        for old_row, new_row in zip(old_rows, new_rows):
            if len(old_row) != len(new_row):
                max_difference = math.inf
                break
            max_difference = max(
                max_difference,
                *(_difference(old, new) for old, new in zip(old_row, new_row)),
            )
        status = "SAME" if max_difference <= args.tolerance else "DIFF"
        print(f"{status:4} {name}: rows={len(old_rows)}, max_abs_diff={max_difference:.12g}")
        failed = failed or status == "DIFF"

    missing = sorted(old_files.keys() ^ new_files.keys())
    if missing:
        print("\nFiles present in only one run:", ", ".join(missing))
        failed = True
    if not metric_names:
        raise SystemExit("No common scalar metrics were found.")
    if failed:
        raise SystemExit("\nResult: DIFFERENT. Inspect the metrics marked DIFF.")
    print("\nResult: SAME within tolerance.")


if __name__ == "__main__":
    main()
