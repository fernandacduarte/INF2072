import argparse
import csv
import os
from pathlib import Path
import subprocess
import sys

import matplotlib.pyplot as plt
import numpy as np


def _load_two_col_csv(path: Path) -> tuple[np.ndarray, np.ndarray]:
    x_vals = []
    y_vals = []
    with path.open("r", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            x_vals.append(float(row[0]))
            y_vals.append(float(row[1]))
    return np.asarray(x_vals, dtype=float), np.asarray(y_vals, dtype=float)


def _rolling_std(values: np.ndarray, window: int) -> np.ndarray:
    if window <= 1:
        return np.zeros_like(values)
    out = np.zeros_like(values)
    for i in range(len(values)):
        start = max(0, i - window + 1)
        segment = values[start : i + 1]
        out[i] = float(np.std(segment, ddof=0))
    return out


def _find_latest_run(runs_root: Path) -> Path:
    candidates = [p for p in runs_root.iterdir() if p.is_dir() and p.name.startswith("iql_")]
    if not candidates:
        raise FileNotFoundError(f"No IQL run folder found in {runs_root}")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _resolve_scalars_dir(run_dir: Path) -> Path:
    nested = run_dir / run_dir.name / "scalars"
    if nested.exists():
        return nested
    direct = run_dir / "scalars"
    if direct.exists():
        return direct
    raise FileNotFoundError(f"Could not find scalars directory inside {run_dir}")


def _open_file(path: Path) -> None:
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except Exception as exc:
        print(f"Warning: could not open image automatically: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot reward mean and stddev from BenchMARL logs.")
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=Path("benchmarl_setup") / "runs",
        help="Root directory containing BenchMARL run folders.",
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=None,
        help="Specific run directory. If omitted, latest iql_* run is used.",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=5,
        help="Window for rolling stddev computed over reward mean.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("benchmarl_setup") / "runs" / "iql_reward_mean_stddev.png",
        help="Output PNG path.",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not open the generated PNG automatically.",
    )
    args = parser.parse_args()

    run_dir = args.run_dir if args.run_dir is not None else _find_latest_run(args.runs_root)
    scalars_dir = _resolve_scalars_dir(run_dir)

    frames_path = scalars_dir / "counters_total_frames.csv"
    reward_mean_path = scalars_dir / "collection_reward_reward_mean.csv"

    _, frames = _load_two_col_csv(frames_path)
    _, reward_mean = _load_two_col_csv(reward_mean_path)

    n = min(len(frames), len(reward_mean))
    frames = frames[:n]
    reward_mean = reward_mean[:n]

    reward_std = _rolling_std(reward_mean, window=args.window)

    args.out.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(1, 1, figsize=(10, 5))

    ax.plot(frames, reward_mean, label="Reward mean", color="#1f77b4", linewidth=2)
    ax.fill_between(
        frames,
        reward_mean - reward_std,
        reward_mean + reward_std,
        color="#1f77b4",
        alpha=0.2,
        label="Mean +/- rolling stddev",
    )
    ax.set_xlabel("Total frames")
    ax.set_ylabel("Reward")
    ax.set_title("IQL Average Reward with Stddev Band")
    ax.grid(True, alpha=0.3)
    ax.legend()

    fig.tight_layout()
    fig.savefig(args.out, dpi=150)

    print(f"Run dir: {run_dir}")
    print(f"Scalars dir: {scalars_dir}")
    print(f"Saved: {args.out}")
    print(f"Reward mean min/max: {reward_mean.min():.3f}/{reward_mean.max():.3f}")
    print(f"Reward stddev min/max: {reward_std.min():.3f}/{reward_std.max():.3f}")

    if not args.no_open:
        _open_file(args.out)


if __name__ == "__main__":
    main()
