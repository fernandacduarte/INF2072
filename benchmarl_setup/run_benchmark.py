import argparse
import csv
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from algorithm_utils import SUPPORTED_ALGORITHMS, candidate_run_dirs, normalize_algorithm
from device_utils import device_label, parse_device_list, resolve_device
from summarize_benchmark_runs import summarize_runs


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = PROJECT_ROOT / "benchmarl_setup" / "run_pacman_benchmarl.py"


def _parse_seeds(raw: str) -> list[int]:
    seeds = []
    for chunk in raw.split(","):
        item = chunk.strip()
        if not item:
            continue
        seeds.append(int(item))
    if not seeds:
        raise ValueError("At least one seed must be provided.")
    return seeds


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run multi-seed BenchMARL benchmark and summarize results."
    )
    parser.add_argument(
        "--algorithms",
        type=str,
        default="iql,vdn,qmixlocal,qmixglobal",
        help="Comma-separated algorithms to run (for example: iql,vdn,qmixlocal,qmixglobal).",
    )
    parser.add_argument(
        "--seeds",
        type=str,
        default="0,1,2,3,4",
        help="Comma-separated seeds.",
    )
    parser.add_argument("--max-frames", type=int, default=50000)
    parser.add_argument("--frames-per-batch", type=int, default=200)
    parser.add_argument("--optimizer-steps", type=int, default=10)
    parser.add_argument("--train-batch-size", type=int, default=128)
    parser.add_argument("--memory-size", type=int, default=10000)
    parser.add_argument("--init-random-frames", type=int, default=1000)
    parser.add_argument("--number-ghosts", type=int, default=2)
    parser.add_argument("--grid-size", type=int, default=20)
    parser.add_argument(
        "--maze",
        type=str,
        default="default",
        choices=["default", "pinklike"],
        help="Maze layout to train on (applied to all algorithms/seeds in this benchmark).",
    )
    parser.add_argument(
        "--save-folder",
        type=str,
        default=str((PROJECT_ROOT / "benchmarl_setup" / "runs").resolve()),
    )
    parser.add_argument(
        "--checkpoint-interval",
        type=int,
        default=0,
        help="Checkpoint interval in collected frames (0 disables periodic checkpoints).",
    )
    parser.add_argument(
        "--checkpoint-at-end",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Save a checkpoint at the end of each run.",
    )
    parser.add_argument(
        "--devices",
        type=str,
        default="cpu",
        help="Comma-separated compute devices to benchmark (for example: cpu,cuda).",
    )
    parser.add_argument(
        "--allow-cpu-fallback",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Fall back to CPU when a CUDA device is requested but unavailable.",
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop immediately if one run fails.",
    )
    parser.add_argument(
        "--tail-window",
        type=int,
        default=20,
        help="Window size used to compute tail mean reward in the summary.",
    )
    parser.add_argument(
        "--summary-out",
        type=str,
        default=str((PROJECT_ROOT / "benchmarl_setup" / "runs" / "benchmark_summary.csv").resolve()),
        help="Output CSV path for benchmark summary.",
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Skip summary generation after training.",
    )
    parser.add_argument(
        "--live-progress-file",
        type=str,
        default=str((PROJECT_ROOT / "benchmarl_setup" / "runs" / "live_progress.csvl").resolve()),
        help="Path to live progress CSVL consumed by benchmarl_setup/liveplot.py.",
    )
    parser.add_argument(
        "--report-interval-seconds",
        type=float,
        default=1.0,
        help="Polling interval used to export live progress while training is running.",
    )
    parser.add_argument(
        "--no-liveplot-report",
        action="store_true",
        help="Disable writing live progress updates for liveplot.py.",
    )
    parser.add_argument(
        "--jobs-out",
        type=str,
        default=str((PROJECT_ROOT / "benchmarl_setup" / "runs" / "benchmark_jobs.csv").resolve()),
        help="Output CSV path for per-job wall-clock timing records.",
    )
    return parser.parse_args()


def _build_command(
    args: argparse.Namespace,
    algorithm: str,
    seed: int,
    requested_device: str,
    save_folder: Path,
) -> list[str]:
    command = [
        sys.executable,
        str(RUNNER_PATH),
        "--algorithm",
        algorithm,
        "--seed",
        str(seed),
        "--max-frames",
        str(args.max_frames),
        "--frames-per-batch",
        str(args.frames_per_batch),
        "--optimizer-steps",
        str(args.optimizer_steps),
        "--train-batch-size",
        str(args.train_batch_size),
        "--memory-size",
        str(args.memory_size),
        "--init-random-frames",
        str(args.init_random_frames),
        "--number-ghosts",
        str(args.number_ghosts),
        "--grid-size",
        str(args.grid_size),
        "--maze",
        str(args.maze),
        "--save-folder",
        str(save_folder),
        "--checkpoint-interval",
        str(args.checkpoint_interval),
        "--device",
        requested_device,
    ]

    if args.allow_cpu_fallback:
        command.append("--allow-cpu-fallback")
    else:
        command.append("--no-allow-cpu-fallback")

    if args.checkpoint_at_end:
        command.append("--checkpoint-at-end")
    else:
        command.append("--no-checkpoint-at-end")

    return command


def _resolve_scalars_dir(run_dir: Path) -> Path | None:
    nested = run_dir / run_dir.name / "scalars"
    if nested.exists():
        return nested
    direct = run_dir / "scalars"
    if direct.exists():
        return direct
    return None


def _load_two_col_csv(path: Path) -> tuple[list[float], list[float]]:
    x_vals: list[float] = []
    y_vals: list[float] = []
    if not path.exists():
        return x_vals, y_vals

    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 2:
                continue
            try:
                x_vals.append(float(row[0]))
                y_vals.append(float(row[1]))
            except ValueError:
                continue
    return x_vals, y_vals


class ProgressReporter:
    def __init__(
        self,
        runs_roots_by_label: dict[str, Path],
        algorithms: list[str],
        output_file: Path,
        interval_seconds: float,
    ) -> None:
        self.runs_roots_by_label = runs_roots_by_label
        self.algorithms = algorithms
        self.output_file = output_file
        self.interval_seconds = max(0.2, interval_seconds)
        self._last_step_by_run: dict[tuple[str, str, str], int] = {}
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._existing_run_ids: set[tuple[str, str, str]] = set()
        self._tracked_run_ids: set[tuple[str, str, str]] = set()

    def start(self) -> None:
        for label, runs_root in self.runs_roots_by_label.items():
            for algorithm in self.algorithms:
                for run_dir in candidate_run_dirs(runs_root, algorithm):
                    self._existing_run_ids.add((label, algorithm, run_dir.name))

        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        # Truncate at the beginning of a new benchmark session.
        self.output_file.write_text("", encoding="utf-8")
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
        self.poll_once()

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            self.poll_once()
            time.sleep(self.interval_seconds)

    def poll_once(self) -> None:
        lines: list[str] = []
        for label, runs_root in self.runs_roots_by_label.items():
            for algorithm in self.algorithms:
                for run_dir in candidate_run_dirs(runs_root, algorithm):
                    scalars_dir = _resolve_scalars_dir(run_dir)
                    if scalars_dir is None:
                        continue

                    frames_path = scalars_dir / "counters_total_frames.csv"
                    reward_path = scalars_dir / "collection_reward_reward_mean.csv"
                    _, frames = _load_two_col_csv(frames_path)
                    _, rewards = _load_two_col_csv(reward_path)

                    n = min(len(frames), len(rewards))
                    if n <= 0:
                        continue

                    run_key = (label, algorithm, run_dir.name)

                    # Ignore pre-existing runs and only track runs created in this session.
                    if run_key not in self._tracked_run_ids:
                        if run_key in self._existing_run_ids:
                            continue
                        self._tracked_run_ids.add(run_key)

                    last_step = self._last_step_by_run.get(run_key, 0)

                    for step in range(last_step + 1, n + 1):
                        frame_value = frames[step - 1]
                        reward_value = rewards[step - 1]
                        lines.append(
                            f"{algorithm}@{label},{run_dir.name},{step},{frame_value},{reward_value}\n"
                        )

                    self._last_step_by_run[run_key] = n

        if lines:
            with self.output_file.open("a", encoding="utf-8") as f:
                f.writelines(lines)


def _save_folder_for_device(base_save_folder: Path, resolved_device: str) -> Path:
    return base_save_folder / device_label(resolved_device)


def _build_device_configs(args: argparse.Namespace) -> list[dict[str, str]]:
    requested_values = parse_device_list(args.devices)
    configs: list[dict[str, str]] = []
    seen_requested: set[str] = set()
    by_label: dict[str, list[str]] = {}

    for requested in requested_values:
        if requested in seen_requested:
            continue
        seen_requested.add(requested)

        resolved, reason = resolve_device(
            requested_device=requested,
            allow_cpu_fallback=args.allow_cpu_fallback,
        )
        label = device_label(resolved)
        by_label.setdefault(label, []).append(requested)
        configs.append(
            {
                "requested": requested,
                "resolved": resolved,
                "reason": reason,
                "label": label,
            }
        )

    collisions = {label: reqs for label, reqs in by_label.items() if len(reqs) > 1}
    if collisions:
        details = "; ".join(
            f"{label} <= {','.join(reqs)}" for label, reqs in sorted(collisions.items())
        )
        raise ValueError(
            "Device benchmark matrix collapsed because multiple requested devices resolved "
            f"to the same runtime device: {details}. "
            "Use --no-allow-cpu-fallback to fail on unavailable CUDA, or adjust --devices."
        )

    return configs


def _discover_new_run_dir(
    runs_root: Path,
    algorithm: str,
    before_names: set[str],
    started_at: float,
    ended_at: float,
) -> str:
    candidates = []
    for run_dir in candidate_run_dirs(runs_root, algorithm):
        if run_dir.name in before_names:
            continue
        mtime = run_dir.stat().st_mtime
        if (started_at - 5.0) <= mtime <= (ended_at + 120.0):
            candidates.append(run_dir)

    if not candidates:
        return ""

    candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return candidates[0].name


def _write_job_records(path: Path, records: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "algorithm",
        "seed",
        "requested_device",
        "resolved_device",
        "device_label",
        "save_folder",
        "run_dir",
        "returncode",
        "duration_seconds",
        "started_at_utc",
        "ended_at_utc",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    print(f"Wrote {len(records)} benchmark job rows to: {path}")


def _run_algorithm_serial_seeds(
    args: argparse.Namespace,
    algorithm: str,
    device_config: dict[str, str],
    save_folder: Path,
    seeds: list[int],
    stop_event: threading.Event,
) -> tuple[list[tuple[str, int, int, str]], list[dict[str, str]]]:
    failures: list[tuple[str, int, int, str]] = []
    job_records: list[dict[str, str]] = []
    for seed in seeds:
        if args.stop_on_error and stop_event.is_set():
            break

        before_names = {run_dir.name for run_dir in candidate_run_dirs(save_folder, algorithm)}
        cmd = _build_command(
            args=args,
            algorithm=algorithm,
            seed=seed,
            requested_device=device_config["requested"],
            save_folder=save_folder,
        )
        print(
            f"[algorithm={algorithm}] seed={seed} "
            f"requested_device={device_config['requested']} resolved_device={device_config['resolved']}"
        )
        print(" ".join(cmd))

        start_perf = time.perf_counter()
        start_wall = time.time()
        started_at_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
        completed = subprocess.run(cmd, check=False)
        duration_seconds = time.perf_counter() - start_perf
        end_wall = time.time()
        ended_at_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")

        run_dir_name = _discover_new_run_dir(
            runs_root=save_folder,
            algorithm=algorithm,
            before_names=before_names,
            started_at=start_wall,
            ended_at=end_wall,
        )

        job_records.append(
            {
                "algorithm": algorithm,
                "seed": str(seed),
                "requested_device": device_config["requested"],
                "resolved_device": device_config["resolved"],
                "device_label": device_config["label"],
                "save_folder": str(save_folder),
                "run_dir": run_dir_name,
                "returncode": str(completed.returncode),
                "duration_seconds": f"{duration_seconds:.6f}",
                "started_at_utc": started_at_iso,
                "ended_at_utc": ended_at_iso,
            }
        )

        if completed.returncode != 0:
            print(
                "Job failed: "
                f"algorithm={algorithm} seed={seed} "
                f"device={device_config['resolved']} returncode={completed.returncode}"
            )
            failures.append((algorithm, seed, completed.returncode, device_config["resolved"]))
            if args.stop_on_error:
                stop_event.set()
                break

    return failures, job_records


def main() -> None:
    args = parse_args()

    algorithms = [normalize_algorithm(item) for item in args.algorithms.split(",") if item.strip()]
    if not algorithms:
        raise ValueError("At least one algorithm must be provided.")

    allowed = set(SUPPORTED_ALGORITHMS)
    invalid = [name for name in algorithms if name not in allowed]
    if invalid:
        raise ValueError(f"Unsupported algorithm(s): {invalid}. Allowed: {sorted(allowed)}")

    seeds = _parse_seeds(args.seeds)
    device_configs = _build_device_configs(args)

    base_save_folder = Path(args.save_folder)
    runs_roots_by_label = {
        cfg["label"]: _save_folder_for_device(base_save_folder, cfg["resolved"])
        for cfg in device_configs
    }
    for label, root in runs_roots_by_label.items():
        root.mkdir(parents=True, exist_ok=True)

    print("Benchmark device matrix:")
    for cfg in device_configs:
        print(
            f"- requested={cfg['requested']} resolved={cfg['resolved']} "
            f"label={cfg['label']} reason={cfg['reason']}"
        )

    failures: list[tuple[str, int, int, str]] = []
    job_records: list[dict[str, str]] = []

    reporter: ProgressReporter | None = None
    if not args.no_liveplot_report:
        reporter = ProgressReporter(
            runs_roots_by_label=runs_roots_by_label,
            algorithms=algorithms,
            output_file=Path(args.live_progress_file),
            interval_seconds=args.report_interval_seconds,
        )
        reporter.start()
        print(f"Live progress enabled: {args.live_progress_file}")

    total = len(algorithms) * len(seeds) * len(device_configs)
    print(
        "Running benchmark jobs with parallel algorithm-device workers and serial seeds per worker. "
        f"Total jobs: {total}"
    )

    stop_event = threading.Event()
    worker_specs = [
        (algorithm, cfg, runs_roots_by_label[cfg["label"]])
        for cfg in device_configs
        for algorithm in algorithms
    ]
    try:
        with ThreadPoolExecutor(max_workers=len(worker_specs)) as executor:
            future_map = {
                executor.submit(
                    _run_algorithm_serial_seeds,
                    args,
                    algorithm,
                    device_config,
                    save_folder,
                    seeds,
                    stop_event,
                ): (algorithm, device_config["resolved"])
                for algorithm, device_config, save_folder in worker_specs
            }

            for future, worker_id in future_map.items():
                try:
                    worker_failures, worker_records = future.result()
                    failures.extend(worker_failures)
                    job_records.extend(worker_records)
                except Exception as exc:
                    algorithm, resolved_device = worker_id
                    print(
                        "Worker crashed: "
                        f"algorithm={algorithm} device={resolved_device} error={exc}"
                    )
                    failures.append((algorithm, -1, 1, resolved_device))
                    if args.stop_on_error:
                        stop_event.set()
    finally:
        if reporter is not None:
            reporter.stop()

    jobs_out = Path(args.jobs_out)
    _write_job_records(jobs_out, job_records)

    print()
    if failures:
        print("Benchmark finished with failures:")
        for algorithm, seed, returncode, resolved_device in failures:
            print(
                f"- algorithm={algorithm} seed={seed} device={resolved_device} "
                f"returncode={returncode}"
            )
        raise SystemExit(1)

    print("Benchmark finished successfully.")

    if args.no_summary:
        print("Summary generation skipped (--no-summary).")
        return

    summary_out = Path(args.summary_out)
    summarize_runs(
        runs_root=base_save_folder,
        algorithms=algorithms,
        tail_window=args.tail_window,
        out=summary_out,
        devices=[cfg["label"] for cfg in device_configs],
        jobs_path=jobs_out,
    )


if __name__ == "__main__":
    main()
