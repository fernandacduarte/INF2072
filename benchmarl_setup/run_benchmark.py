import argparse
import subprocess
import sys
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

    total = len(algorithms) * len(seeds)
    index = 0
    failures: list[tuple[str, int, int]] = []

    print(f"Running {total} benchmark jobs.")
    for algorithm in algorithms:
        for seed in seeds:
            index += 1
            cmd = _build_command(args, algorithm, seed)
            print(f"[{index}/{total}] algorithm={algorithm} seed={seed}")
            print(" ".join(cmd))
            completed = subprocess.run(cmd, check=False)
            if completed.returncode != 0:
                print(
                    f"Job failed: algorithm={algorithm} seed={seed} returncode={completed.returncode}"
                )
                failures.append((algorithm, seed, completed.returncode))
                if args.stop_on_error:
                    break
        if failures and args.stop_on_error:
            break

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
