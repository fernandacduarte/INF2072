import argparse
import csv
import os
from pathlib import Path
import subprocess
import sys
import webbrowser

import matplotlib.pyplot as plt
import numpy as np

from algorithm_utils import (
    SUPPORTED_ALGORITHMS,
    SUPPORTED_MAZES,
    candidate_run_dirs,
    normalize_algorithm,
    runs_root_for_maze,
)


def _load_two_col_csv(path: Path) -> tuple[np.ndarray, np.ndarray]:
    x_vals = []
    y_vals = []
    with path.open("r", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 2:
                continue
            x_vals.append(float(row[0]))
            y_vals.append(float(row[1]))
    return np.asarray(x_vals, dtype=float), np.asarray(y_vals, dtype=float)


def _moving_average(values: np.ndarray, window: int) -> np.ndarray:
    if window <= 1:
        return values.copy()
    out = np.zeros_like(values)
    for i in range(len(values)):
        start = max(0, i - window + 1)
        out[i] = float(np.mean(values[start : i + 1]))
    return out


def _resolve_scalars_dir(run_dir: Path) -> Path | None:
    nested = run_dir / run_dir.name / "scalars"
    if nested.exists():
        return nested
    direct = run_dir / "scalars"
    if direct.exists():
        return direct
    return None


def _open_file(path: Path) -> None:
    resolved = path.resolve()
    if not resolved.exists():
        print(f"Warning: output file does not exist, cannot open automatically: {resolved}")
        return

    try:
        if sys.platform.startswith("win"):
            escaped_path = str(resolved).replace("'", "''")

            # Prefer a deterministic open path in Windows.
            ps_cmd = (
                "$p = Start-Process -FilePath '"
                + escaped_path
                + "' -PassThru -ErrorAction Stop; "
                "if ($p -and $p.Id) { exit 0 } else { exit 1 }"
            )
            rc = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                check=False,
            ).returncode
            if rc == 0:
                print("Opened plot using: powershell Start-Process")
                return

            # Fallback for restricted environments.
            if webbrowser.open(resolved.as_uri(), new=0, autoraise=True):
                print("Opened plot using: webbrowser")
                return

            # Last fallback: open parent folder and select the generated file.
            subprocess.run(["explorer", "/select,", str(resolved)], check=False)
            print("Warning: could not open file directly; opened containing folder instead.")
        elif sys.platform == "darwin":
            rc = subprocess.run(["open", str(resolved)], check=False).returncode
            if rc == 0:
                print("Opened plot using: open")
            else:
                print(f"Warning: could not open image automatically (open returncode={rc}).")
        else:
            rc = subprocess.run(["xdg-open", str(resolved)], check=False).returncode
            if rc == 0:
                print("Opened plot using: xdg-open")
            else:
                print(f"Warning: could not open image automatically (xdg-open returncode={rc}).")
    except Exception as exc:
        print(f"Warning: could not open image automatically: {exc}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot reward mean +/- std across multiple BenchMARL runs for one or more algorithms."
    )
    parser.add_argument(
        "--algorithm",
        choices=["iql", "vdn", "qmix", "qmixlocal", "qmixglobal"],
        default=None,
        help="Single algorithm to aggregate (backward-compatible alias).",
    )
    parser.add_argument(
        "--algorithms",
        type=str,
        default=None,
        help="Comma-separated algorithms to aggregate together (for example: iql,vdn,qmixlocal,qmixglobal).",
    )
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=Path("benchmarl_setup") / "runs",
        help="Base runs directory.",
    )
    parser.add_argument(
        "--maze",
        type=str,
        default="default",
        choices=SUPPORTED_MAZES,
        help="Maze subfolder under --runs-root.",
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        action="append",
        default=None,
        help=(
            "Specific run directory to include. Can be passed multiple times. "
            "When provided, run discovery by algorithm prefix is ignored."
        ),
    )
    parser.add_argument(
        "--window",
        type=int,
        default=30,
        help="Smoothing window applied to each run before aggregation.",
    )
    parser.add_argument(
        "--show-runs",
        action="store_true",
        help="Overlay each run as a faint line.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output PNG path. Defaults to <runs-root>/<maze>/<algorithm>_reward_multiseed_mean_std.png",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not open the generated PNG automatically.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    maze_runs_root = runs_root_for_maze(args.runs_root, args.maze)

    if args.window < 1:
        raise ValueError("--window must be >= 1")

    algorithms: list[str]
    if args.algorithms:
        algorithms = [normalize_algorithm(item) for item in args.algorithms.split(",") if item.strip()]
    elif args.algorithm:
        algorithms = [normalize_algorithm(args.algorithm)]
    else:
        algorithms = ["iql", "vdn", "qmixlocal", "qmixglobal"]

    allowed = set(SUPPORTED_ALGORITHMS)
    invalid = [name for name in algorithms if name not in allowed]
    if invalid:
        raise ValueError(f"Unsupported algorithm(s): {invalid}. Allowed: {sorted(allowed)}")

    if args.out is None:
        if len(algorithms) == 1:
            args.out = maze_runs_root / f"{algorithms[0]}_reward_multiseed_mean_std.png"
        else:
            args.out = maze_runs_root / "benchmark_reward_multiseed_mean_std.png"

    color_map = {
        "iql": "#1f77b4",
        "vdn": "#d62728",
        "qmixlocal": "#2ca02c",
        "qmixglobal": "#9467bd",
    }

    per_algorithm: dict[str, dict[str, object]] = {}

    for algorithm in algorithms:
        if args.run_dir:
            run_dirs = args.run_dir
        else:
            run_dirs = candidate_run_dirs(maze_runs_root, algorithm)

        if not run_dirs:
            print(f"Warning: no run directories found for algorithm={algorithm} in {maze_runs_root}")
            continue

        series_frames: list[np.ndarray] = []
        series_rewards: list[np.ndarray] = []
        used_run_dirs: list[Path] = []

        for run_dir in run_dirs:
            scalars_dir = _resolve_scalars_dir(run_dir)
            if scalars_dir is None:
                continue

            frames_path = scalars_dir / "counters_total_frames.csv"
            reward_mean_path = scalars_dir / "collection_reward_reward_mean.csv"
            if not frames_path.exists() or not reward_mean_path.exists():
                continue

            _, frames = _load_two_col_csv(frames_path)
            _, reward_mean = _load_two_col_csv(reward_mean_path)
            n = min(len(frames), len(reward_mean))
            if n == 0:
                continue

            frames = frames[:n]
            reward_mean = reward_mean[:n]
            reward_mean = _moving_average(reward_mean, args.window)

            series_frames.append(frames)
            series_rewards.append(reward_mean)
            used_run_dirs.append(run_dir)

        if not series_rewards:
            print(
                "Warning: no usable scalar files found for algorithm="
                f"{algorithm} (expected counters_total_frames.csv and collection_reward_reward_mean.csv)."
            )
            continue

        min_len = min(len(arr) for arr in series_rewards)
        rewards_mat = np.vstack([arr[:min_len] for arr in series_rewards])
        frames_mat = np.vstack([arr[:min_len] for arr in series_frames])

        per_algorithm[algorithm] = {
            "frames": np.mean(frames_mat, axis=0),
            "reward_mean": np.mean(rewards_mat, axis=0),
            "reward_std": np.std(rewards_mat, axis=0),
            "rewards_mat": rewards_mat,
            "used_run_dirs": used_run_dirs,
            "color": color_map.get(algorithm, "#1f77b4"),
        }

    if not per_algorithm:
        raise FileNotFoundError(
            "No usable runs were found for selected algorithms."
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(1, 1, figsize=(10, 5))

    for algorithm, payload in per_algorithm.items():
        frames = payload["frames"]
        reward_mean = payload["reward_mean"]
        reward_std = payload["reward_std"]
        rewards_mat = payload["rewards_mat"]
        color = payload["color"]

        if args.show_runs:
            for rewards in rewards_mat:
                ax.plot(frames, rewards, color=color, linewidth=1, alpha=0.18)

        ax.plot(
            frames,
            reward_mean,
            label=f"{algorithm.upper()} mean reward (n={rewards_mat.shape[0]})",
            color=color,
            linewidth=2,
        )
        ax.fill_between(
            frames,
            reward_mean - reward_std,
            reward_mean + reward_std,
            color=color,
            alpha=0.14,
        )

    ax.set_xlabel("Total frames")
    ax.set_ylabel("Reward")
    ax.set_title("Benchmark Reward Across Runs")
    ax.grid(True, alpha=0.3)
    ax.legend()

    fig.tight_layout()
    fig.savefig(args.out, dpi=150)

    print(f"Algorithms: {', '.join(sorted(per_algorithm.keys()))}")
    for algorithm, payload in per_algorithm.items():
        used_run_dirs = payload["used_run_dirs"]
        reward_mean = payload["reward_mean"]
        reward_std = payload["reward_std"]
        print(f"\nAlgorithm: {algorithm}")
        print(f"Included runs: {len(used_run_dirs)}")
        for run_dir in used_run_dirs:
            print(f"- {run_dir}")
        print(f"Mean reward min/max: {reward_mean.min():.3f}/{reward_mean.max():.3f}")
        print(f"Std reward min/max: {reward_std.min():.3f}/{reward_std.max():.3f}")

    print(f"Saved: {args.out}")

    if not args.no_open:
        _open_file(args.out)


if __name__ == "__main__":
    main()
