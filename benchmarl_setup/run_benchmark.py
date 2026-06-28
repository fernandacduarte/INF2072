import argparse
import csv
import json
import shutil
import socket
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from algorithm_utils import (
    SUPPORTED_ALGORITHMS,
    SUPPORTED_MAZES,
    candidate_run_dirs,
    normalize_algorithm,
    runs_root_for_maze,
    training_exploration_schedule,
)
from device_utils import device_label, parse_device_list, resolve_device
from summarize_benchmark_runs import summarize_runs


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = PROJECT_ROOT / "benchmarl_setup" / "run_pacman_benchmarl.py"
EVAL_REPORT_PATH = PROJECT_ROOT / "custom_environment" / "eval_report.py"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from custom_environment.env.rewards import load_reward_strategy
from custom_environment.env.rewards.loader import reward_class_from_id


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


def _sanitize_machine_id(raw: str) -> str:
    value = (raw or "").strip().lower()
    if not value:
        return "unknown"

    normalized_chars: list[str] = []
    for ch in value:
        if ch.isalnum() or ch in {"-", "_"}:
            normalized_chars.append(ch)
        else:
            normalized_chars.append("-")

    normalized = "".join(normalized_chars).strip("-_")
    return normalized or "unknown"


def _default_machine_id() -> str:
    return _sanitize_machine_id(socket.gethostname())


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
        "--reward-classes",
        type=str,
        default=None,
        help="Comma-separated reward implementations as module:Class.",
    )
    parser.add_argument(
        "--reward-ids",
        type=str,
        default="current",
        help=(
            "Comma-separated reward strategy ids (for example: current,current_git,current_with_overlap_or_same_corridor). "
            "Ignored when --reward-classes is provided."
        ),
    )
    parser.add_argument(
        "--seeds",
        type=str,
        default="0,1,2,3,4",
        help="Comma-separated seeds.",
    )
    parser.add_argument("--max-frames", type=int, default=60000)
    parser.add_argument("--frames-per-batch", type=int, default=200)
    parser.add_argument("--optimizer-steps", type=int, default=10)
    parser.add_argument("--train-batch-size", type=int, default=128)
    parser.add_argument("--memory-size", type=int, default=10000)
    parser.add_argument("--init-random-frames", type=int, default=5000)
    parser.add_argument("--grid-size", type=int, default=20)
    parser.add_argument(
        "--ghost-view-size",
        type=int,
        default=None,
        help="Odd local observation width/height for ghosts (for example 3 or 5).",
    )
    parser.add_argument(
        "--pacman-difficulty",
        type=str,
        default="hard",
        choices=["easy", "medium", "hard"],
        help="Fixed Pacman controller strength when curriculum is off.",
    )
    parser.add_argument(
        "--pacman-random-action-prob",
        type=float,
        default=0.0,
        help="Exploration noise for Pacman policy in [0,1] when curriculum is off.",
    )
    parser.add_argument(
        "--pacman-safe-distance",
        type=int,
        default=None,
        help="Override safety cap used by Pacman heuristic (default uses preset).",
    )
    parser.add_argument(
        "--pacman-curriculum",
        type=str,
        default="off",
        choices=["off", "easy-medium-hard"],
        help="Pacman curriculum schedule applied over frames.",
    )
    parser.add_argument(
        "--pacman-curriculum-max-frames",
        type=int,
        default=0,
        help="Frame budget used to complete the curriculum schedule.",
    )
    parser.add_argument(
        "--maze",
        type=str,
        default="default",
        choices=SUPPORTED_MAZES,
        help="Maze layout to train on (applied to all algorithms/seeds in this benchmark).",
    )
    parser.add_argument(
        "--save-folder",
        type=str,
        default=str((PROJECT_ROOT / "benchmarl_setup" / "runs").resolve()),
        help="Base runs directory. Benchmark writes runs under <save-folder>/<maze>.",
    )
    parser.add_argument(
        "--machine-id",
        type=str,
        default=None,
        help="Machine identity used to suffix default output files (default: hostname).",
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
        default=None,
        help="Output CSV path for benchmark summary (default: <save-folder>/<maze>/benchmark_summary.csv).",
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Skip summary generation after training.",
    )
    parser.add_argument(
        "--live-progress-file",
        type=str,
        default=None,
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
        "--reset-live-progress",
        action="store_true",
        help="Truncate live_progress.csvl before starting this benchmark session.",
    )
    parser.add_argument(
        "--jobs-out",
        type=str,
        default=None,
        help="Output CSV path for per-job wall-clock timing records (default: <save-folder>/benchmark_jobs_<machine-id>.csv).",
    )
    parser.add_argument(
        "--eval-episodes",
        type=int,
        default=0,
        help=(
            "Paired objective-evaluation episodes per trained checkpoint "
            "(default: 0; set a positive value to enable)."
        ),
    )
    parser.add_argument(
        "--live-capture-eval-episodes",
        type=int,
        default=20,
        help=(
            "Deterministic eval_report episodes used to periodically backfill true capture% "
            "in live progress (set 0 to disable)."
        ),
    )
    parser.add_argument(
        "--eval-seed-base",
        type=int,
        default=0,
        help="First objective-evaluation seed, shared across all reward variants.",
    )
    parser.add_argument(
        "--eval-out",
        type=str,
        default=None,
        help="Objective evaluation CSV (default: <save-folder>/<maze>/reward_eval.csv).",
    )
    return parser.parse_args()


def _build_command(
    args: argparse.Namespace,
    algorithm: str,
    seed: int,
    requested_device: str,
    save_folder: Path,
    reward_class: str,
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
        "--grid-size",
        str(args.grid_size),
        "--maze",
        str(args.maze),
        "--reward-class",
        reward_class,
        "--save-folder",
        str(save_folder),
        "--save-folder-includes-maze",
        "--checkpoint-interval",
        str(args.checkpoint_interval),
        "--device",
        requested_device,
    ]

    if args.ghost_view_size is not None:
        command.extend(["--ghost-view-size", str(args.ghost_view_size)])

    command.extend(["--pacman-difficulty", str(args.pacman_difficulty)])
    command.extend(["--pacman-random-action-prob", str(args.pacman_random_action_prob)])
    if args.pacman_safe_distance is not None:
        command.extend(["--pacman-safe-distance", str(args.pacman_safe_distance)])
    command.extend(["--pacman-curriculum", str(args.pacman_curriculum)])
    command.extend(["--pacman-curriculum-max-frames", str(args.pacman_curriculum_max_frames)])

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


def _discover_reward_term_files(scalars_dir: Path) -> dict[str, Path]:
    # Intentionally disabled: reward-term curves should come from true
    # RewardStrategy breakdown keys exported by eval_report snapshots,
    # not from generic training collector scalar names.
    _ = scalars_dir
    return {}


def _resolve_checkpoints_dir(run_dir: Path) -> Path | None:
    nested = run_dir / run_dir.name / "checkpoints"
    if nested.exists():
        return nested
    direct = run_dir / "checkpoints"
    if direct.exists():
        return direct
    return None


def _latest_checkpoint_path(run_dir: Path) -> Path | None:
    checkpoints_dir = _resolve_checkpoints_dir(run_dir)
    if checkpoints_dir is None:
        return None
    checkpoints = sorted(
        checkpoints_dir.glob("checkpoint_*.pt"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return checkpoints[0] if checkpoints else None


def _list_checkpoints_in_creation_order(run_dir: Path) -> list[Path]:
    checkpoints_dir = _resolve_checkpoints_dir(run_dir)
    if checkpoints_dir is None:
        return []

    def _sort_key(path: Path) -> tuple[int, float, str]:
        stem = path.stem
        prefix = "checkpoint_"
        frame_idx = -1
        if stem.startswith(prefix):
            suffix = stem[len(prefix):]
            if suffix.isdigit():
                frame_idx = int(suffix)
        return (frame_idx, path.stat().st_mtime, path.name)

    return sorted(checkpoints_dir.glob("checkpoint_*.pt"), key=_sort_key)


def _checkpoint_frame_from_path(path: Path) -> int | None:
    stem = path.stem
    prefix = "checkpoint_"
    if not stem.startswith(prefix):
        return None
    suffix = stem[len(prefix):]
    if not suffix.isdigit():
        return None
    return int(suffix)


def _step_index_for_checkpoint_frame(frames: list[float], checkpoint_frame: int | None) -> int:
    if not frames:
        return 1
    if checkpoint_frame is None:
        return len(frames)
    for idx, frame_value in enumerate(frames, start=1):
        if frame_value >= float(checkpoint_frame):
            return idx
    return len(frames)


def _read_capture_pct_from_eval_csv(path: Path) -> float | None:
    if not path.exists():
        return None

    with path.open("r", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            raw_capture_rate = (row.get("capture_rate") or "").strip()
            if not raw_capture_rate:
                continue
            try:
                return float(raw_capture_rate) * 100.0
            except ValueError:
                continue
    return None


def _read_breakdown_per_step_from_eval_csv(path: Path) -> dict[str, float]:
    if not path.exists():
        return {}

    with path.open("r", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            raw_json = (row.get("reward_breakdown_per_step_mean_json") or "").strip()
            if not raw_json:
                continue
            try:
                parsed = json.loads(raw_json)
            except json.JSONDecodeError:
                continue
            if not isinstance(parsed, dict):
                continue

            output: dict[str, float] = {}
            for key, value in parsed.items():
                try:
                    output[str(key).strip().lower()] = float(value)
                except (TypeError, ValueError):
                    continue
            return output
    return {}


def _run_eval_capture_snapshot(
    *,
    algorithm: str,
    reward_id: str,
    run_dir: Path,
    checkpoint_path: Path,
    episodes: int,
    eval_seed_base: int,
    device: str,
    allow_cpu_fallback: bool,
    allow_non_hard_checkpoint: bool,
) -> tuple[float | None, dict[str, float]]:
    latest_out_csv = run_dir / "evaluation_report_live_capture.csv"
    checkpoint_frame = _checkpoint_frame_from_path(checkpoint_path)
    checkpoint_suffix = str(checkpoint_frame) if checkpoint_frame is not None else "latest"
    curriculum_frame_offset = checkpoint_frame if checkpoint_frame is not None else 0
    out_csv = run_dir / f"evaluation_report_live_capture_checkpoint_{checkpoint_suffix}.csv"
    command = [
        sys.executable,
        str(EVAL_REPORT_PATH),
        "--learner",
        algorithm,
        "--checkpoint",
        str(checkpoint_path),
        "--reward-id",
        reward_id,
        "--episodes",
        str(episodes),
        "--eval-seed-base",
        str(eval_seed_base),
        "--curriculum-frame-offset",
        str(curriculum_frame_offset),
        "--device",
        device,
        "--out",
        str(out_csv),
    ]
    if allow_non_hard_checkpoint:
        command.append("--allow-non-hard-checkpoint")
    command.append("--allow-cpu-fallback" if allow_cpu_fallback else "--no-allow-cpu-fallback")

    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        print(
            "Live capture snapshot failed: "
            f"algorithm={algorithm} reward={reward_id} checkpoint={checkpoint_path} "
            f"returncode={completed.returncode}"
        )
        return None, {}

    if out_csv != latest_out_csv:
        try:
            shutil.copyfile(out_csv, latest_out_csv)
        except OSError as exc:
            print(
                "Live capture snapshot copy failed: "
                f"source={out_csv} target={latest_out_csv} error={exc}"
            )

    capture_pct = _read_capture_pct_from_eval_csv(out_csv)
    reward_breakdown = _read_breakdown_per_step_from_eval_csv(out_csv)
    if capture_pct is None:
        print(f"Live capture snapshot missing capture_rate in {out_csv}")
    return capture_pct, reward_breakdown


def _refresh_latest_capture_snapshots(
    *,
    runs_roots_by_label: dict[str, Path],
    algorithms: list[str],
    eval_device_by_label: dict[str, str],
    episodes: int,
    eval_seed_base: int,
    allow_cpu_fallback: bool,
    final_allow_non_hard_checkpoint: bool,
) -> None:
    if episodes <= 0:
        return

    refreshed = 0
    skipped = 0
    refresh_mode = "checkpoint-native" if final_allow_non_hard_checkpoint else "hard-forced"
    print(
        "Refreshing latest checkpoint capture snapshots for completed runs "
        f"(mode={refresh_mode})..."
    )
    for label, runs_root in runs_roots_by_label.items():
        reward_id, _, _device_label = label.partition("@")
        eval_device = eval_device_by_label.get(label)
        if not reward_id or not eval_device:
            continue

        for algorithm in algorithms:
            for run_dir in candidate_run_dirs(runs_root, algorithm):
                checkpoint_path = _latest_checkpoint_path(run_dir)
                if checkpoint_path is None:
                    skipped += 1
                    continue
                capture_pct, _reward_breakdown = _run_eval_capture_snapshot(
                    algorithm=algorithm,
                    reward_id=reward_id,
                    run_dir=run_dir,
                    checkpoint_path=checkpoint_path,
                    episodes=episodes,
                    eval_seed_base=eval_seed_base,
                    device=eval_device,
                    allow_cpu_fallback=allow_cpu_fallback,
                    allow_non_hard_checkpoint=final_allow_non_hard_checkpoint,
                )
                if capture_pct is None:
                    skipped += 1
                    continue
                refreshed += 1
    print(f"Latest capture snapshot refresh finished: refreshed={refreshed} skipped={skipped}")


class ProgressReporter:
    def __init__(
        self,
        runs_roots_by_label: dict[str, Path],
        algorithms: list[str],
        output_file: Path,
        interval_seconds: float,
        max_frames: int,
        maze: str,
        pacman_curriculum: str,
        pacman_curriculum_max_frames: int,
        pacman_curriculum_frame_offset: int,
        machine_id: str,
        epsilon_algorithm: str,
        live_capture_eval_episodes: int,
        eval_seed_base: int,
        allow_cpu_fallback: bool,
        eval_device_by_label: dict[str, str],
        reset_output_file: bool,
    ) -> None:
        self.runs_roots_by_label = runs_roots_by_label
        self.algorithms = algorithms
        self.output_file = output_file
        self.interval_seconds = max(0.2, interval_seconds)
        self.max_frames = int(max_frames)
        self.maze = maze
        self.pacman_curriculum = str(pacman_curriculum).strip().lower()
        self.pacman_curriculum_max_frames = int(pacman_curriculum_max_frames)
        self.pacman_curriculum_frame_offset = int(pacman_curriculum_frame_offset)
        self.machine_id = _sanitize_machine_id(machine_id)
        self.epsilon_algorithm = normalize_algorithm(epsilon_algorithm)
        self.epsilon_schedule = training_exploration_schedule(
            self.epsilon_algorithm,
            self.maze,
            self.max_frames,
            pacman_curriculum=self.pacman_curriculum,
        )
        self.live_capture_eval_episodes = int(live_capture_eval_episodes)
        self.eval_seed_base = int(eval_seed_base)
        self.allow_cpu_fallback = bool(allow_cpu_fallback)
        self.eval_device_by_label = eval_device_by_label
        self.reset_output_file = bool(reset_output_file)
        self._last_step_by_run: dict[tuple[str, str, str], int] = {}
        self._evaluated_checkpoint_keys_by_run: dict[tuple[str, str, str], set[str]] = {}
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._existing_run_ids: set[tuple[str, str, str]] = set()
        self._tracked_run_ids: set[tuple[str, str, str]] = set()
        self._io_lock = threading.Lock()
        self._run_term_series_cache: dict[tuple[str, str, str], dict[str, list[float]]] = {}
        self._run_eval_term_snapshot_cache: dict[tuple[str, str, str], dict[str, float]] = {}
        self._reward_terms_order: list[str] = []
        self._default_step_term_values_by_label: dict[str, dict[str, float]] = {}

    def _seed_reward_terms_from_strategy(self) -> None:
        seeded_terms: set[str] = set(self._reward_terms_order)
        for label in self.runs_roots_by_label.keys():
            reward_id = label.split("@", 1)[0] if "@" in label else "current"
            try:
                strategy_class = reward_class_from_id(reward_id)
                strategy = load_reward_strategy(strategy_class)
            except Exception:
                continue

            # Prefer an explicit weights dataclass if present; otherwise include
            # already-known common breakdown keys used in this project.
            weights = getattr(strategy, "weights", None)
            if weights is not None and hasattr(weights, "__dataclass_fields__"):
                for key in sorted(weights.__dataclass_fields__.keys()):
                    seeded_terms.add(str(key).strip().lower())

                timestep_value = getattr(weights, "timestep", None)
                try:
                    if timestep_value is not None:
                        self._default_step_term_values_by_label.setdefault(label, {})[
                            "timestep"
                        ] = float(timestep_value)
                except (TypeError, ValueError):
                    pass

            seeded_terms.update({
                "get_pacman",
                "pacman_timeout_win",
                "pacman_win_pellets",
                "timestep",
                "pacman_legal_moves_delta",
                "reverse_action",
            })

        self._reward_terms_order = sorted(seeded_terms)

    def _build_meta_line(self) -> str:
        schedule_mode = str(self.epsilon_schedule.get("epsilon_schedule_mode", "global"))
        extra_schedule = ""
        if schedule_mode == "curriculum_piecewise":
            extra_schedule = (
                f"epsilon_stage_boundary_1={self.epsilon_schedule.get('epsilon_stage_boundary_1', 0)},"
                f"epsilon_stage_boundary_2={self.epsilon_schedule.get('epsilon_stage_boundary_2', 0)},"
                f"epsilon_easy_init={self.epsilon_schedule.get('epsilon_easy_init', 1.0)},"
                f"epsilon_easy_end={self.epsilon_schedule.get('epsilon_easy_end', 0.25)},"
                f"epsilon_medium_init={self.epsilon_schedule.get('epsilon_medium_init', 0.65)},"
                f"epsilon_medium_end={self.epsilon_schedule.get('epsilon_medium_end', 0.20)},"
                f"epsilon_hard_init={self.epsilon_schedule.get('epsilon_hard_init', 0.55)},"
                f"epsilon_hard_end={self.epsilon_schedule.get('epsilon_hard_end', 0.08)},"
            )

        return (
            "#meta,"
            f"max_frames={self.epsilon_schedule['max_frames']},"
            f"epsilon_schedule_mode={schedule_mode},"
            f"epsilon_init={self.epsilon_schedule['epsilon_init']},"
            f"epsilon_end={self.epsilon_schedule['epsilon_end']},"
            f"epsilon_anneal_ratio={self.epsilon_schedule['epsilon_anneal_ratio']},"
            f"epsilon_anneal_frames={self.epsilon_schedule['epsilon_anneal_frames']},"
            f"{extra_schedule}"
            f"epsilon_algorithm={self.epsilon_algorithm},"
            f"maze={self.maze},"
            f"pacman_curriculum={self.pacman_curriculum},"
            f"pacman_curriculum_max_frames={self.pacman_curriculum_max_frames},"
            f"pacman_curriculum_frame_offset={self.pacman_curriculum_frame_offset},"
            f"machine_id={self.machine_id},"
            "metric=capture_pct_eval,"
            "reward=collection_reward_reward_mean,"
            f"reward_terms={self._reward_terms_metadata_value()}\n"
        )

    def _refresh_reward_terms_order(self) -> None:
        discovered_terms: set[str] = set()
        for label, runs_root in self.runs_roots_by_label.items():
            for algorithm in self.algorithms:
                for run_dir in candidate_run_dirs(runs_root, algorithm):
                    scalars_dir = _resolve_scalars_dir(run_dir)
                    if scalars_dir is None:
                        continue
                    discovered_terms.update(_discover_reward_term_files(scalars_dir).keys())
        self._reward_terms_order = sorted(discovered_terms)

    def _load_reward_term_series(
        self,
        run_key: tuple[str, str, str],
        scalars_dir: Path,
    ) -> dict[str, list[float]]:
        cached = self._run_term_series_cache.get(run_key)
        if cached is not None:
            return cached

        term_file_map = _discover_reward_term_files(scalars_dir)
        term_series: dict[str, list[float]] = {}
        for term_name, path in term_file_map.items():
            _x_vals, y_vals = _load_two_col_csv(path)
            term_series[term_name] = y_vals

        changed_order = False
        for term_name in sorted(term_series.keys()):
            if term_name not in self._reward_terms_order:
                self._reward_terms_order.append(term_name)
                changed_order = True

        if changed_order:
            with self._io_lock:
                with self.output_file.open("a", encoding="utf-8") as f:
                    f.write(self._build_meta_line())

        self._run_term_series_cache[run_key] = term_series
        return term_series

    def _term_series_for_step(
        self,
        run_key: tuple[str, str, str],
        term_series: dict[str, list[float]],
        step: int,
    ) -> dict[str, list[float]]:
        merged: dict[str, list[float]] = dict(term_series)

        label = run_key[0]
        default_step_terms = self._default_step_term_values_by_label.get(label, {})
        for term_name, value in default_step_terms.items():
            base_series = list(merged.get(term_name, []))
            if len(base_series) < step:
                base_series.extend([float("nan")] * (step - len(base_series)))
            base_series[step - 1] = float(value)
            merged[term_name] = base_series

        snapshot = self._run_eval_term_snapshot_cache.get(run_key)
        if not snapshot:
            return merged

        for term_name, value in snapshot.items():
            base_series = list(merged.get(term_name, []))
            if len(base_series) < step:
                base_series.extend([float("nan")] * (step - len(base_series)))
            base_series[step - 1] = float(value)
            merged[term_name] = base_series
            if term_name not in self._reward_terms_order:
                self._reward_terms_order.append(term_name)
                with self._io_lock:
                    with self.output_file.open("a", encoding="utf-8") as f:
                        f.write(self._build_meta_line())
        return merged

    def _reward_terms_metadata_value(self) -> str:
        if not self._reward_terms_order:
            return ""
        return "|".join(self._reward_terms_order)

    def _build_progress_row(
        self,
        algorithm_label: str,
        run_id: str,
        step: int,
        frame_value: float,
        capture_pct: float,
        reward_value: float,
        term_series: dict[str, list[float]],
    ) -> str:
        row_values: list[str] = [
            algorithm_label,
            run_id,
            str(step),
            str(frame_value),
            str(capture_pct),
            str(reward_value),
        ]
        for term_name in self._reward_terms_order:
            series = term_series.get(term_name, [])
            if step - 1 < len(series):
                row_values.append(str(series[step - 1]))
            else:
                row_values.append("nan")
        return ",".join(row_values) + "\n"

    def start(self) -> None:
        for label, runs_root in self.runs_roots_by_label.items():
            for algorithm in self.algorithms:
                for run_dir in candidate_run_dirs(runs_root, algorithm):
                    self._existing_run_ids.add((label, algorithm, run_dir.name))

        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        self._refresh_reward_terms_order()
        self._seed_reward_terms_from_strategy()
        if self.reset_output_file or not self.output_file.exists():
            self.output_file.write_text(self._build_meta_line(), encoding="utf-8")
        else:
            with self.output_file.open("a", encoding="utf-8") as handle:
                handle.write(self._build_meta_line())
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
            reward_id = label.split("@", 1)[0] if "@" in label else "current"
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
                    term_series = self._load_reward_term_series(run_key, scalars_dir)

                    # Ignore pre-existing runs and only track runs created in this session.
                    if run_key not in self._tracked_run_ids:
                        if run_key in self._existing_run_ids:
                            continue
                        self._tracked_run_ids.add(run_key)

                    last_step = self._last_step_by_run.get(run_key, 0)

                    for step in range(last_step + 1, n + 1):
                        frame_value = frames[step - 1]
                        capture_pct = float("nan")
                        reward_value = rewards[step - 1]
                        step_term_series = self._term_series_for_step(run_key, term_series, step)
                        lines.append(
                            self._build_progress_row(
                                algorithm_label=f"{algorithm}@{label}",
                                run_id=run_dir.name,
                                step=step,
                                frame_value=frame_value,
                                capture_pct=capture_pct,
                                reward_value=reward_value,
                                term_series=step_term_series,
                            )
                        )

                    self._last_step_by_run[run_key] = n

                    if self.live_capture_eval_episodes <= 0:
                        continue

                    checkpoints = _list_checkpoints_in_creation_order(run_dir)
                    if not checkpoints:
                        continue

                    seen_keys = self._evaluated_checkpoint_keys_by_run.setdefault(run_key, set())

                    reward_id, _, _device_label = label.partition("@")
                    eval_device = self.eval_device_by_label.get(label)
                    if not reward_id or not eval_device:
                        continue

                    for checkpoint_path in checkpoints:
                        checkpoint_key = str(checkpoint_path.resolve())
                        if checkpoint_key in seen_keys:
                            continue

                        capture_pct, eval_breakdown_per_step = _run_eval_capture_snapshot(
                            algorithm=algorithm,
                            reward_id=reward_id,
                            run_dir=run_dir,
                            checkpoint_path=checkpoint_path,
                            episodes=self.live_capture_eval_episodes,
                            eval_seed_base=self.eval_seed_base,
                            device=eval_device,
                            allow_cpu_fallback=self.allow_cpu_fallback,
                            allow_non_hard_checkpoint=True,
                        )
                        if capture_pct is None:
                            continue

                        seen_keys.add(checkpoint_key)

                        if eval_breakdown_per_step:
                            self._run_eval_term_snapshot_cache[run_key] = eval_breakdown_per_step

                        checkpoint_frame = _checkpoint_frame_from_path(checkpoint_path)
                        checkpoint_step = _step_index_for_checkpoint_frame(frames, checkpoint_frame)
                        checkpoint_step = max(1, min(n, checkpoint_step))
                        frame_value = frames[checkpoint_step - 1]
                        reward_value = rewards[checkpoint_step - 1]
                        step_term_series = self._term_series_for_step(
                            run_key,
                            term_series,
                            checkpoint_step,
                        )
                        lines.append(
                            self._build_progress_row(
                                algorithm_label=f"{algorithm}@{label}",
                                run_id=run_dir.name,
                                step=checkpoint_step,
                                frame_value=frame_value,
                                capture_pct=capture_pct,
                                reward_value=reward_value,
                                term_series=step_term_series,
                            )
                        )

        if lines:
            with self._io_lock:
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
        "machine_id",
        "algorithm",
        "reward_id",
        "reward_class",
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
    reward_id: str,
    reward_class: str,
    machine_id: str,
    seeds: list[int],
    stop_event: threading.Event,
) -> tuple[list[tuple[str, str, int, int, str]], list[dict[str, str]]]:
    failures: list[tuple[str, str, int, int, str]] = []
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
            reward_class=reward_class,
        )
        print(
            f"[algorithm={algorithm}] reward={reward_id} seed={seed} "
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
                "machine_id": _sanitize_machine_id(machine_id),
                "algorithm": algorithm,
                "reward_id": reward_id,
                "reward_class": reward_class,
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
            failures.append(
                (
                    algorithm,
                    reward_id,
                    seed,
                    completed.returncode,
                    device_config["resolved"],
                )
            )
            if args.stop_on_error:
                stop_event.set()
                break

    return failures, job_records


def main() -> None:
    args = parse_args()
    if not (0.0 <= float(args.pacman_random_action_prob) <= 1.0):
        raise ValueError("--pacman-random-action-prob must be in [0,1].")
    if int(args.pacman_curriculum_max_frames) < 0:
        raise ValueError("--pacman-curriculum-max-frames must be >= 0.")

    algorithms = [normalize_algorithm(item) for item in args.algorithms.split(",") if item.strip()]
    if not algorithms:
        raise ValueError("At least one algorithm must be provided.")

    allowed = set(SUPPORTED_ALGORITHMS)
    invalid = [name for name in algorithms if name not in allowed]
    if invalid:
        raise ValueError(f"Unsupported algorithm(s): {invalid}. Allowed: {sorted(allowed)}")

    reward_specs: list[tuple[str, str]] = []
    reward_ids_seen: set[str] = set()
    if args.reward_classes and str(args.reward_classes).strip():
        reward_class_inputs = [
            item.strip() for item in str(args.reward_classes).split(",") if item.strip()
        ]
    else:
        reward_class_inputs = [
            reward_class_from_id(item.strip())
            for item in str(args.reward_ids).split(",")
            if item.strip()
        ]

    for class_path in reward_class_inputs:
        if not class_path:
            continue
        strategy = load_reward_strategy(class_path)
        if strategy.strategy_id in reward_ids_seen:
            raise ValueError(f"Duplicate reward strategy_id: {strategy.strategy_id!r}")
        reward_ids_seen.add(strategy.strategy_id)
        reward_specs.append((strategy.strategy_id, class_path))
    if not reward_specs:
        raise ValueError("At least one reward class must be provided.")
    if args.eval_episodes < 0:
        raise ValueError("--eval-episodes must be non-negative.")
    if args.live_capture_eval_episodes < 0:
        raise ValueError("--live-capture-eval-episodes must be non-negative.")
    if (args.eval_episodes or args.live_capture_eval_episodes) and not args.checkpoint_at_end:
        raise ValueError(
            "Automatic objective evaluation and live capture snapshots require --checkpoint-at-end."
        )
    if args.live_capture_eval_episodes and args.checkpoint_interval <= 0:
        print(
            "Live capture snapshots enabled with --checkpoint-interval=0; "
            "updates will occur only when end-of-run checkpoints are produced."
        )

    seeds = _parse_seeds(args.seeds)
    machine_id = _sanitize_machine_id(args.machine_id) if args.machine_id is not None else _default_machine_id()
    maze_runs_root = runs_root_for_maze(Path(args.save_folder), args.maze)
    live_progress_file = (
        Path(args.live_progress_file)
        if args.live_progress_file is not None
        else maze_runs_root / f"live_progress_{machine_id}.csvl"
    )
    summary_out = (
        Path(args.summary_out)
        if args.summary_out is not None
        else maze_runs_root / f"benchmark_summary_{machine_id}.csv"
    )
    eval_out = (
        Path(args.eval_out)
        if args.eval_out is not None
        else maze_runs_root / f"reward_eval_{machine_id}.csv"
    )
    jobs_out = (
        Path(args.jobs_out)
        if args.jobs_out is not None
        else Path(args.save_folder) / f"benchmark_jobs_{machine_id}.csv"
    )
    device_configs = _build_device_configs(args)

    base_save_folder = maze_runs_root
    runs_roots_by_label = {
        f"{reward_id}@{cfg['label']}": _save_folder_for_device(
            base_save_folder / reward_id, cfg["resolved"]
        )
        for reward_id, _ in reward_specs
        for cfg in device_configs
    }
    eval_device_by_label = {
        f"{reward_id}@{cfg['label']}": cfg["resolved"]
        for reward_id, _ in reward_specs
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

    failures: list[tuple[str, str, int, int, str]] = []
    job_records: list[dict[str, str]] = []

    reporter: ProgressReporter | None = None
    if not args.no_liveplot_report:
        epsilon_algorithm = "iql" if "iql" in algorithms else algorithms[0]
        reporter = ProgressReporter(
            runs_roots_by_label=runs_roots_by_label,
            algorithms=algorithms,
            output_file=live_progress_file,
            interval_seconds=args.report_interval_seconds,
            max_frames=args.max_frames,
            maze=args.maze,
            pacman_curriculum=args.pacman_curriculum,
            pacman_curriculum_max_frames=args.pacman_curriculum_max_frames,
            pacman_curriculum_frame_offset=0,
            machine_id=machine_id,
            epsilon_algorithm=epsilon_algorithm,
            live_capture_eval_episodes=args.live_capture_eval_episodes,
            eval_seed_base=args.eval_seed_base,
            allow_cpu_fallback=args.allow_cpu_fallback,
            eval_device_by_label=eval_device_by_label,
            reset_output_file=args.reset_live_progress,
        )
        reporter.start()
        print(f"Live progress enabled: {live_progress_file}")

    print(f"Machine id: {machine_id}")

    total = len(algorithms) * len(reward_specs) * len(seeds) * len(device_configs)
    print(
        "Running benchmark jobs with parallel algorithm-device workers and serial seeds per worker. "
        f"Total jobs: {total}"
    )

    stop_event = threading.Event()
    worker_specs = [
        (
            algorithm,
            reward_id,
            reward_class,
            cfg,
            runs_roots_by_label[f"{reward_id}@{cfg['label']}"],
        )
        for reward_id, reward_class in reward_specs
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
                    reward_id,
                    reward_class,
                    machine_id,
                    seeds,
                    stop_event,
                ): (algorithm, reward_id, device_config["resolved"])
                for algorithm, reward_id, reward_class, device_config, save_folder in worker_specs
            }

            for future, worker_id in future_map.items():
                try:
                    worker_failures, worker_records = future.result()
                    failures.extend(worker_failures)
                    job_records.extend(worker_records)
                except Exception as exc:
                    algorithm, reward_id, resolved_device = worker_id
                    print(
                        "Worker crashed: "
                        f"algorithm={algorithm} reward={reward_id} device={resolved_device} error={exc}"
                    )
                    failures.append((algorithm, reward_id, -1, 1, resolved_device))
                    if args.stop_on_error:
                        stop_event.set()
    finally:
        if reporter is not None:
            reporter.stop()

    _refresh_latest_capture_snapshots(
        runs_roots_by_label=runs_roots_by_label,
        algorithms=algorithms,
        eval_device_by_label=eval_device_by_label,
        episodes=args.live_capture_eval_episodes,
        eval_seed_base=args.eval_seed_base,
        allow_cpu_fallback=args.allow_cpu_fallback,
        final_allow_non_hard_checkpoint=False,
    )

    _write_job_records(jobs_out, job_records)

    print()
    if failures:
        print("Benchmark finished with failures:")
        for algorithm, reward_id, seed, returncode, resolved_device in failures:
            print(
                f"- algorithm={algorithm} reward={reward_id} seed={seed} device={resolved_device} "
                f"returncode={returncode}"
            )
        raise SystemExit(1)

    print("Benchmark finished successfully.")

    if args.eval_episodes:
        eval_command = [
            sys.executable,
            str(EVAL_REPORT_PATH),
            "--jobs-path",
            str(jobs_out),
            "--episodes",
            str(args.eval_episodes),
            "--eval-seed-base",
            str(args.eval_seed_base),
            "--out",
            str(eval_out),
        ]
        # Benchmark evaluation should reflect checkpoint-native curriculum stage.
        eval_command.append("--allow-non-hard-checkpoint")
        print("Running paired objective evaluation:")
        print(" ".join(eval_command))
        completed_eval = subprocess.run(eval_command, check=False)
        if completed_eval.returncode != 0:
            raise SystemExit(completed_eval.returncode)

    if args.no_summary:
        print("Summary generation skipped (--no-summary).")
        return

    summarize_runs(
        runs_root=base_save_folder,
        algorithms=algorithms,
        rewards=[reward_id for reward_id, _ in reward_specs],
        tail_window=args.tail_window,
        out=summary_out,
        devices=[cfg["label"] for cfg in device_configs],
        jobs_paths=[jobs_out],
    )


if __name__ == "__main__":
    main()
