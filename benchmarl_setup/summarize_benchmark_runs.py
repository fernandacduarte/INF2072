import argparse
import csv
import re
from datetime import datetime
from pathlib import Path

from algorithm_utils import (
    SUPPORTED_ALGORITHMS,
    SUPPORTED_MAZES,
    candidate_run_dirs,
    normalize_algorithm,
    runs_root_for_maze,
)


def _resolve_scalars_dir(run_dir: Path) -> Path | None:
    nested = run_dir / run_dir.name / "scalars"
    if nested.exists():
        return nested
    direct = run_dir / "scalars"
    if direct.exists():
        return direct
    return None


def _read_reward_series(path: Path) -> list[float]:
    values: list[float] = []
    with path.open("r", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 2:
                continue
            values.append(float(row[1]))
    return values


def _latest_checkpoint(run_dir: Path) -> Path | None:
    checkpoints_dir = run_dir / "checkpoints"
    if not checkpoints_dir.exists():
        return None
    checkpoints = sorted(
        checkpoints_dir.glob("checkpoint_*.pt"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return checkpoints[0] if checkpoints else None


def _extract_seed(run_dir: Path) -> int | None:
    hparams = run_dir / run_dir.name / "texts" / "hparams0.txt"
    if not hparams.exists():
        return None
    content = hparams.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"^seed:\s*(\d+)\s*$", content, flags=re.MULTILINE)
    if match is None:
        return None
    return int(match.group(1))


def _tail_mean(values: list[float], window: int) -> float:
    if not values:
        return float("nan")
    n = min(window, len(values))
    return sum(values[-n:]) / float(n)


def _fmt_float(value: float) -> str:
    if value != value:  # NaN check without extra imports.
        return ""
    return f"{value:.6f}"


def _mean_from_rows(rows: list[dict[str, str]], key: str) -> float:
    values: list[float] = []
    for row in rows:
        raw = row.get(key, "")
        if raw == "":
            continue
        try:
            value = float(raw)
        except ValueError:
            continue
        if value == value:  # Skip NaN
            values.append(value)
    if not values:
        return float("nan")
    return sum(values) / float(len(values))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize BenchMARL run metrics for algorithm comparison."
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
        "--algorithms",
        type=str,
        default="iql,vdn,qmixlocal,qmixglobal",
        help="Comma-separated algorithms to include.",
    )
    parser.add_argument(
        "--tail-window",
        type=int,
        default=20,
        help="Window size used to compute tail mean reward.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output CSV path (default: <runs-root>/<maze>/benchmark_summary.csv).",
    )
    return parser.parse_args()


def summarize_runs(
    runs_root: Path,
    algorithms: list[str],
    tail_window: int,
    out: Path,
) -> list[dict[str, str]]:
    if not algorithms:
        raise ValueError("At least one algorithm must be provided.")

    normalized_algorithms = [normalize_algorithm(item) for item in algorithms if item.strip()]
    if not normalized_algorithms:
        raise ValueError("At least one algorithm must be provided.")

    invalid = [name for name in normalized_algorithms if name not in SUPPORTED_ALGORITHMS]
    if invalid:
        raise ValueError(f"Unsupported algorithm(s): {invalid}. Allowed: {list(SUPPORTED_ALGORITHMS)}")

    rows = []
    for algorithm in normalized_algorithms:
        run_dirs = candidate_run_dirs(runs_root, algorithm)
        for run_dir in run_dirs:
            scalars_dir = _resolve_scalars_dir(run_dir)
            if scalars_dir is None:
                continue

            reward_path = scalars_dir / "collection_reward_reward_mean.csv"
            episode_reward_path = scalars_dir / "collection_reward_episode_reward_mean.csv"
            if not reward_path.exists():
                continue

            rewards = _read_reward_series(reward_path)
            if not rewards:
                continue

            episode_rewards: list[float] = []
            if episode_reward_path.exists():
                episode_rewards = _read_reward_series(episode_reward_path)

            episode_final = episode_rewards[-1] if episode_rewards else float("nan")
            episode_tail = _tail_mean(episode_rewards, tail_window) if episode_rewards else float("nan")
            episode_best = max(episode_rewards) if episode_rewards else float("nan")

            checkpoint = _latest_checkpoint(run_dir)
            seed = _extract_seed(run_dir)
            mtime = datetime.fromtimestamp(run_dir.stat().st_mtime).isoformat(timespec="seconds")

            rows.append(
                {
                    "algorithm": algorithm,
                    "seed": "" if seed is None else str(seed),
                    "run_dir": run_dir.name,
                    "run_mtime": mtime,
                    "n_points": str(len(rewards)),
                    "n_episode_points": str(len(episode_rewards)),
                    "final_reward": f"{rewards[-1]:.6f}",
                    "tail_mean_reward": f"{_tail_mean(rewards, tail_window):.6f}",
                    "best_reward": f"{max(rewards):.6f}",
                    "final_episode_return": _fmt_float(episode_final),
                    "tail_mean_episode_return": _fmt_float(episode_tail),
                    "best_episode_return": _fmt_float(episode_best),
                    "checkpoint_path": "" if checkpoint is None else str(checkpoint),
                }
            )

    rows.sort(key=lambda row: (row["algorithm"], row["seed"], row["run_mtime"]))

    out.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "algorithm",
        "seed",
        "run_dir",
        "run_mtime",
        "n_points",
        "n_episode_points",
        "final_reward",
        "tail_mean_reward",
        "best_reward",
        "final_episode_return",
        "tail_mean_episode_return",
        "best_episode_return",
        "checkpoint_path",
    ]
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to: {out}")

    if not rows:
        print("No matching runs were found.")
        return rows

    by_algorithm: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_algorithm.setdefault(row["algorithm"], []).append(row)

    print("\nAggregate summary (mean over runs):")
    for algorithm in sorted(by_algorithm):
        group = by_algorithm[algorithm]
        final_mean = _mean_from_rows(group, "final_reward")
        tail_mean = _mean_from_rows(group, "tail_mean_reward")
        best_mean = _mean_from_rows(group, "best_reward")
        final_episode_mean = _mean_from_rows(group, "final_episode_return")
        tail_episode_mean = _mean_from_rows(group, "tail_mean_episode_return")
        best_episode_mean = _mean_from_rows(group, "best_episode_return")
        print(
            f"- {algorithm}: runs={len(group)} "
            f"reward_final_mean={final_mean:.4f} "
            f"reward_tail_mean={tail_mean:.4f} "
            f"reward_best_mean={best_mean:.4f} "
            f"episode_final_mean={final_episode_mean:.4f} "
            f"episode_tail_mean={tail_episode_mean:.4f} "
            f"episode_best_mean={best_episode_mean:.4f}"
        )

    return rows


def main() -> None:
    args = parse_args()
    algorithms = [normalize_algorithm(item) for item in args.algorithms.split(",") if item.strip()]
    maze_runs_root = runs_root_for_maze(args.runs_root, args.maze)
    out = args.out if args.out is not None else maze_runs_root / "benchmark_summary.csv"
    summarize_runs(
        runs_root=maze_runs_root,
        algorithms=algorithms,
        tail_window=args.tail_window,
        out=out,
    )


if __name__ == "__main__":
    main()
