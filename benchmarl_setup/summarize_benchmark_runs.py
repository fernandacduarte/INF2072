import argparse
import csv
import re
from datetime import datetime
from pathlib import Path

from algorithm_utils import SUPPORTED_ALGORITHMS, candidate_run_dirs, normalize_algorithm


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


def _parse_device_labels(raw: str) -> list[str]:
    labels = [item.strip() for item in raw.split(",") if item.strip()]
    if not labels:
        raise ValueError("At least one device label must be provided.")
    return labels


def _load_job_metrics(path: Path | None) -> dict[tuple[str, str, str, str], dict[str, float]]:
    if path is None or not path.exists():
        return {}

    metrics: dict[tuple[str, str, str, str], dict[str, float]] = {}
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            run_dir = (row.get("run_dir") or "").strip()
            if not run_dir:
                continue
            key = (
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
        default=Path("benchmarl_setup") / "runs" / "benchmark_summary.csv",
        help="Output CSV path.",
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
        default=Path("benchmarl_setup") / "runs" / "benchmark_jobs.csv",
        help="Optional benchmark jobs CSV used to merge wall-clock duration metrics.",
    )
    return parser.parse_args()


def summarize_runs(
    runs_root: Path,
    algorithms: list[str],
    tail_window: int,
    out: Path,
    devices: list[str] | None = None,
    jobs_path: Path | None = None,
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

    job_metrics = _load_job_metrics(jobs_path)

    rows = []
    for device in device_labels:
        device_root = runs_root / device
        if not device_root.exists():
            if len(device_labels) == 1:
                device_root = runs_root
            else:
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

                rewards = _read_reward_series(reward_path)
                if not rewards:
                    continue

                frames_value = _read_last_frame_count(scalars_dir / "counters_total_frames.csv")

                checkpoint = _latest_checkpoint(run_dir)
                seed = _extract_seed(run_dir)
                mtime = datetime.fromtimestamp(run_dir.stat().st_mtime).isoformat(timespec="seconds")

                seed_value = "" if seed is None else str(seed)
                timing = job_metrics.get((algorithm, seed_value, device, run_dir.name), {})
                duration_seconds = float(timing.get("duration_seconds", float("nan")))
                fps_value = float("nan")
                if duration_seconds > 0.0 and frames_value is not None and frames_value > 0.0:
                    fps_value = frames_value / duration_seconds

                rows.append(
                    {
                        "device": device,
                        "algorithm": algorithm,
                        "seed": seed_value,
                        "run_dir": run_dir.name,
                        "run_mtime": mtime,
                        "n_points": str(len(rewards)),
                        "final_reward": f"{rewards[-1]:.6f}",
                        "tail_mean_reward": f"{_tail_mean(rewards, tail_window):.6f}",
                        "best_reward": f"{max(rewards):.6f}",
                        "duration_seconds": "" if duration_seconds != duration_seconds else f"{duration_seconds:.6f}",
                        "frames_per_second": "" if fps_value != fps_value else f"{fps_value:.6f}",
                        "checkpoint_path": "" if checkpoint is None else str(checkpoint),
                    }
                )

    rows.sort(key=lambda row: (row["algorithm"], row["device"], row["seed"], row["run_mtime"]))

    out.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "device",
        "algorithm",
        "seed",
        "run_dir",
        "run_mtime",
        "n_points",
        "final_reward",
        "tail_mean_reward",
        "best_reward",
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

    by_algorithm_device: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in rows:
        key = (row["algorithm"], row["device"])
        by_algorithm_device.setdefault(key, []).append(row)

    print("\nAggregate summary (mean over runs by algorithm+device):")
    for algorithm, device in sorted(by_algorithm_device):
        group = by_algorithm_device[(algorithm, device)]
        final_mean = sum(float(row["final_reward"]) for row in group) / float(len(group))
        tail_mean = sum(float(row["tail_mean_reward"]) for row in group) / float(len(group))
        best_mean = sum(float(row["best_reward"]) for row in group) / float(len(group))
        durations = [float(row["duration_seconds"]) for row in group if row["duration_seconds"]]
        fps_values = [float(row["frames_per_second"]) for row in group if row["frames_per_second"]]
        duration_mean = float("nan") if not durations else sum(durations) / float(len(durations))
        fps_mean = float("nan") if not fps_values else sum(fps_values) / float(len(fps_values))
        print(
            f"- {algorithm}@{device}: runs={len(group)} "
            f"final_mean={final_mean:.4f} tail_mean={tail_mean:.4f} best_mean={best_mean:.4f} "
            f"duration_mean={duration_mean:.2f}s fps_mean={fps_mean:.2f}"
        )

    return rows


def main() -> None:
    args = parse_args()
    algorithms = [normalize_algorithm(item) for item in args.algorithms.split(",") if item.strip()]
    devices = _parse_device_labels(args.devices)
    summarize_runs(
        runs_root=args.runs_root,
        algorithms=algorithms,
        tail_window=args.tail_window,
        out=args.out,
        devices=devices,
        jobs_path=args.jobs_path,
    )


if __name__ == "__main__":
    main()
