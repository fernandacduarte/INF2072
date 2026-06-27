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


def _read_last_frame_count(path: Path) -> float | None:
    if not path.exists():
        return None
    last_value: float | None = None
    with path.open("r", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 2:
                continue
            try:
                last_value = float(row[1])
            except ValueError:
                continue
    return last_value

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

def _parse_device_labels(raw: str) -> list[str]:
    labels = [item.strip() for item in raw.split(",") if item.strip()]
    if not labels:
        raise ValueError("At least one device label must be provided.")
    return labels

def _discover_jobs_paths(runs_root: Path) -> list[Path]:
    candidates = sorted(runs_root.glob("benchmark_jobs*.csv"))
    if candidates:
        return candidates

    legacy_file = runs_root / "benchmark_jobs.csv"
    if legacy_file.exists():
        return [legacy_file]
    return []


def _load_job_metrics(paths: list[Path]) -> dict[tuple[str, str, str, str, str, str], dict[str, float | str]]:
    if not paths:
        return {}

    metrics: dict[tuple[str, str, str, str, str, str], dict[str, float | str]] = {}
    for path in paths:
        if not path.exists():
            continue
        with path.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                run_dir = (row.get("run_dir") or "").strip()
                if not run_dir:
                    continue
                machine_id = (row.get("machine_id") or "").strip().lower() or "unknown"
                key = (
                    machine_id,
                    (row.get("reward_id") or "current").strip(),
                    (row.get("algorithm") or "").strip(),
                    (row.get("seed") or "").strip(),
                    (row.get("device_label") or "").strip(),
                    run_dir,
                )
                try:
                    duration_seconds = float(row.get("duration_seconds", "nan"))
                except ValueError:
                    duration_seconds = float("nan")
                metrics[key] = {
                    "duration_seconds": duration_seconds,
                    "machine_id": machine_id,
                }
    return metrics

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
        "--rewards",
        type=str,
        default="current",
        help="Comma-separated reward strategy IDs to include.",
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
    parser.add_argument(
        "--devices",
        type=str,
        default="cpu",
        help="Comma-separated device labels to include (for example: cpu,cuda,cuda_0).",
    )
    parser.add_argument(
        "--jobs-path",
        type=Path,
        nargs="+",
        default=None,
        help="Optional benchmark jobs CSV file(s) used to merge wall-clock duration metrics (default: auto-discover benchmark_jobs*.csv).",
    )
    return parser.parse_args()


def summarize_runs(
    runs_root: Path,
    algorithms: list[str],
    rewards: list[str] | None,
    tail_window: int,
    out: Path,
    devices: list[str] | None = None,
    jobs_paths: list[Path] | None = None,
) -> list[dict[str, str]]:
    if not algorithms:
        raise ValueError("At least one algorithm must be provided.")

    normalized_algorithms = [normalize_algorithm(item) for item in algorithms if item.strip()]
    if not normalized_algorithms:
        raise ValueError("At least one algorithm must be provided.")

    invalid = [name for name in normalized_algorithms if name not in SUPPORTED_ALGORITHMS]
    if invalid:
        raise ValueError(f"Unsupported algorithm(s): {invalid}. Allowed: {list(SUPPORTED_ALGORITHMS)}")

    device_labels = devices or ["cpu"]
    if not device_labels:
        raise ValueError("At least one device label must be provided.")

    resolved_jobs_paths = jobs_paths or _discover_jobs_paths(runs_root)
    job_metrics = _load_job_metrics(resolved_jobs_paths)
    reward_ids = rewards or ["current"]

    rows: list[dict[str, str]] = []
    for reward_id in reward_ids:
        reward_root = runs_root / reward_id
        if not reward_root.exists() and reward_id == "current":
            reward_root = runs_root  # Backward-compatible legacy layout.
        for device in device_labels:
            device_root = reward_root / device
            if not device_root.exists():
                print(f"Warning: device runs folder does not exist, skipping: {device_root}")
                continue

            for algorithm in normalized_algorithms:
                run_dirs = candidate_run_dirs(device_root, algorithm)
                for run_dir in run_dirs:
                    scalars_dir = _resolve_scalars_dir(run_dir)
                    if scalars_dir is None:
                        continue

                    reward_path = scalars_dir / "collection_reward_reward_mean.csv"
                    if not reward_path.exists():
                        continue
                    reward_values = _read_reward_series(reward_path)
                    if not reward_values:
                        continue

                    episode_reward_path = scalars_dir / "collection_reward_episode_reward_mean.csv"
                    episode_rewards: list[float] = []
                    if episode_reward_path.exists():
                        episode_rewards = _read_reward_series(episode_reward_path)

                    episode_final = episode_rewards[-1] if episode_rewards else float("nan")
                    episode_tail = _tail_mean(episode_rewards, tail_window) if episode_rewards else float("nan")
                    episode_best = max(episode_rewards) if episode_rewards else float("nan")
                    frames_value = _read_last_frame_count(scalars_dir / "counters_total_frames.csv")
                    checkpoint = _latest_checkpoint(run_dir)
                    seed = _extract_seed(run_dir)
                    mtime = datetime.fromtimestamp(run_dir.stat().st_mtime).isoformat(timespec="seconds")

                    seed_value = "" if seed is None else str(seed)
                    timing = {}
                    selected_machine_id = ""
                    for key, value in job_metrics.items():
                        machine_id, key_reward_id, key_algorithm, key_seed, key_device, key_run_dir = key
                        if (
                            key_reward_id == reward_id
                            and key_algorithm == algorithm
                            and key_seed == seed_value
                            and key_device == device
                            and key_run_dir == run_dir.name
                        ):
                            timing = value
                            selected_machine_id = str(value.get("machine_id", machine_id))
                            break

                    duration_seconds = float(timing.get("duration_seconds", float("nan")))
                    fps_value = float("nan")
                    if duration_seconds > 0.0 and frames_value is not None and frames_value > 0.0:
                        fps_value = frames_value / duration_seconds

                    rows.append(
                        {
                            "reward_id": reward_id,
                            "device": device,
                            "algorithm": algorithm,
                            "seed": seed_value,
                            "machine_id": selected_machine_id,
                            "run_dir": run_dir.name,
                            "run_mtime": mtime,
                            "n_points": str(len(reward_values)),
                            "n_episode_points": str(len(episode_rewards)),
                            "final_reward": f"{reward_values[-1]:.6f}",
                            "tail_mean_reward": f"{_tail_mean(reward_values, tail_window):.6f}",
                            "best_reward": f"{max(reward_values):.6f}",
                            "final_episode_return": _fmt_float(episode_final),
                            "tail_mean_episode_return": _fmt_float(episode_tail),
                            "best_episode_return": _fmt_float(episode_best),
                            "duration_seconds": _fmt_float(duration_seconds),
                            "frames_per_second": _fmt_float(fps_value),
                            "checkpoint_path": "" if checkpoint is None else str(checkpoint),
                        }
                    )

    rows.sort(key=lambda row: (row["reward_id"], row["algorithm"], row["device"], row["seed"], row["run_mtime"]))

    out.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "reward_id",
        "device",
        "algorithm",
        "seed",
        "machine_id",
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
        "duration_seconds",
        "frames_per_second",
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

    by_algorithm_device: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for row in rows:
        key = (row["reward_id"], row["algorithm"], row["device"])
        by_algorithm_device.setdefault(key, []).append(row)

    print("\nAggregate summary (mean over runs by algorithm+device):")
    for reward_id, algorithm, device in sorted(by_algorithm_device):
        group = by_algorithm_device[(reward_id, algorithm, device)]
        final_mean = _mean_from_rows(group, "final_reward")
        tail_mean = _mean_from_rows(group, "tail_mean_reward")
        best_mean = _mean_from_rows(group, "best_reward")
        final_episode_mean = _mean_from_rows(group, "final_episode_return")
        tail_episode_mean = _mean_from_rows(group, "tail_mean_episode_return")
        best_episode_mean = _mean_from_rows(group, "best_episode_return")
        duration_mean = _mean_from_rows(group, "duration_seconds")
        fps_mean = _mean_from_rows(group, "frames_per_second")
        print(
            f"- {reward_id}/{algorithm}@{device}: runs={len(group)} "
            f"final_mean={final_mean:.4f} tail_mean={tail_mean:.4f} best_mean={best_mean:.4f} "
            f"episode_final_mean={final_episode_mean:.4f} "
            f"episode_tail_mean={tail_episode_mean:.4f} "
            f"episode_best_mean={best_episode_mean:.4f} "
            f"duration_mean={duration_mean:.2f}s fps_mean={fps_mean:.2f}"
        )

    return rows


def main() -> None:
    args = parse_args()
    algorithms = [normalize_algorithm(item) for item in args.algorithms.split(",") if item.strip()]
    rewards = [item.strip() for item in args.rewards.split(",") if item.strip()]
    maze_runs_root = runs_root_for_maze(args.runs_root, args.maze)
    out = args.out if args.out is not None else maze_runs_root / "benchmark_summary.csv"
    devices = _parse_device_labels(args.devices)
    summarize_runs(
        runs_root=maze_runs_root,
        algorithms=algorithms,
        rewards=rewards,
        tail_window=args.tail_window,
        out=out,
        devices=devices,
        jobs_paths=args.jobs_path,
    )


if __name__ == "__main__":
    main()
