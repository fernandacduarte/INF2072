import argparse
import csv
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

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
        default="iql,vdn",
        help="Comma-separated algorithms to run (for example: iql,vdn).",
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
    return parser.parse_args()


def _build_command(args: argparse.Namespace, algorithm: str, seed: int) -> list[str]:
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
        "--save-folder",
        str(args.save_folder),
        "--checkpoint-interval",
        str(args.checkpoint_interval),
    ]

    if args.checkpoint_at_end:
        command.append("--checkpoint-at-end")
    else:
        command.append("--no-checkpoint-at-end")

    return command


def _candidate_run_dirs(runs_root: Path, algorithm: str) -> list[Path]:
    prefix = f"{algorithm}_pacman_"
    if not runs_root.exists():
        return []
    return [p for p in runs_root.iterdir() if p.is_dir() and p.name.startswith(prefix)]


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
        runs_root: Path,
        algorithms: list[str],
        output_file: Path,
        interval_seconds: float,
    ) -> None:
        self.runs_root = runs_root
        self.algorithms = algorithms
        self.output_file = output_file
        self.interval_seconds = max(0.2, interval_seconds)
        self._last_step_by_run: dict[tuple[str, str], int] = {}
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._existing_run_ids: set[tuple[str, str]] = set()
        self._tracked_run_ids: set[tuple[str, str]] = set()

    def start(self) -> None:
        for algorithm in self.algorithms:
            for run_dir in _candidate_run_dirs(self.runs_root, algorithm):
                self._existing_run_ids.add((algorithm, run_dir.name))

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
        for algorithm in self.algorithms:
            for run_dir in _candidate_run_dirs(self.runs_root, algorithm):
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

                run_key = (algorithm, run_dir.name)

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
                        f"{algorithm},{run_dir.name},{step},{frame_value},{reward_value}\n"
                    )

                self._last_step_by_run[run_key] = n

        if lines:
            with self.output_file.open("a", encoding="utf-8") as f:
                f.writelines(lines)


def _run_algorithm_serial_seeds(
    args: argparse.Namespace,
    algorithm: str,
    seeds: list[int],
    stop_event: threading.Event,
) -> list[tuple[str, int, int]]:
    failures: list[tuple[str, int, int]] = []
    for seed in seeds:
        if args.stop_on_error and stop_event.is_set():
            break

        cmd = _build_command(args, algorithm, seed)
        print(f"[algorithm={algorithm}] seed={seed}")
        print(" ".join(cmd))

        completed = subprocess.run(cmd, check=False)
        if completed.returncode != 0:
            print(
                f"Job failed: algorithm={algorithm} seed={seed} returncode={completed.returncode}"
            )
            failures.append((algorithm, seed, completed.returncode))
            if args.stop_on_error:
                stop_event.set()
                break

    return failures


def main() -> None:
    args = parse_args()

    algorithms = [item.strip().lower() for item in args.algorithms.split(",") if item.strip()]
    if not algorithms:
        raise ValueError("At least one algorithm must be provided.")

    allowed = {"iql", "vdn", "qmix"}
    invalid = [name for name in algorithms if name not in allowed]
    if invalid:
        raise ValueError(f"Unsupported algorithm(s): {invalid}. Allowed: {sorted(allowed)}")

    seeds = _parse_seeds(args.seeds)

    failures: list[tuple[str, int, int]] = []

    reporter: ProgressReporter | None = None
    if not args.no_liveplot_report:
        reporter = ProgressReporter(
            runs_root=Path(args.save_folder),
            algorithms=algorithms,
            output_file=Path(args.live_progress_file),
            interval_seconds=args.report_interval_seconds,
        )
        reporter.start()
        print(f"Live progress enabled: {args.live_progress_file}")

    total = len(algorithms) * len(seeds)
    print(
        "Running benchmark jobs with parallel algorithms and serial seeds per algorithm. "
        f"Total jobs: {total}"
    )

    stop_event = threading.Event()
    try:
        with ThreadPoolExecutor(max_workers=len(algorithms)) as executor:
            future_map = {
                executor.submit(
                    _run_algorithm_serial_seeds,
                    args,
                    algorithm,
                    seeds,
                    stop_event,
                ): algorithm
                for algorithm in algorithms
            }

            for future, algorithm in future_map.items():
                try:
                    failures.extend(future.result())
                except Exception as exc:
                    print(f"Worker crashed: algorithm={algorithm} error={exc}")
                    failures.append((algorithm, -1, 1))
                    if args.stop_on_error:
                        stop_event.set()
    finally:
        if reporter is not None:
            reporter.stop()

    print()
    if failures:
        print("Benchmark finished with failures:")
        for algorithm, seed, returncode in failures:
            print(f"- algorithm={algorithm} seed={seed} returncode={returncode}")
        raise SystemExit(1)

    print("Benchmark finished successfully.")

    if args.no_summary:
        print("Summary generation skipped (--no-summary).")
        return

    summary_out = Path(args.summary_out)
    summarize_runs(
        runs_root=Path(args.save_folder),
        algorithms=algorithms,
        tail_window=args.tail_window,
        out=summary_out,
    )


if __name__ == "__main__":
    main()
