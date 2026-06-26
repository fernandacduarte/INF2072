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
    normalize_algorithm,
    runs_root_for_maze,
)
from device_utils import device_label


def _moving_average(values: np.ndarray, window: int) -> np.ndarray:
    if window <= 1:
        return values.copy()
    out = np.zeros_like(values)
    for i in range(len(values)):
        start = max(0, i - window + 1)
        out[i] = float(np.mean(values[start : i + 1]))
    return out


def _epsilon_for_frames(
    frames: np.ndarray,
    epsilon_max_frames: int,
    epsilon_init: float,
    epsilon_end: float,
    epsilon_anneal_ratio: float,
) -> np.ndarray:
    anneal_frames = max(1.0, float(epsilon_max_frames) * float(epsilon_anneal_ratio))
    span = float(epsilon_init) - float(epsilon_end)
    eps = float(epsilon_init) - span * np.minimum(frames, anneal_frames) / anneal_frames
    return np.maximum(eps, float(epsilon_end))


def _parse_progress_meta(progress_file: Path) -> dict[str, str]:
    if not progress_file.exists():
        return {}

    meta: dict[str, str] = {}
    with progress_file.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line.startswith("#meta,"):
                continue
            for chunk in line[len("#meta,") :].split(","):
                key, sep, value = chunk.partition("=")
                if sep != "=":
                    continue
                parsed_key = key.strip()
                if not parsed_key:
                    continue
                meta[parsed_key] = value.strip()
    return meta


def _parse_progress_data(
    progress_file: Path,
) -> dict[str, dict[str, dict[str, dict[int, tuple[float, float, float]]]]]:
    # algorithm -> device_label -> run_id -> step -> (frame, capture_pct, reward)
    data: dict[str, dict[str, dict[str, dict[int, tuple[float, float, float]]]]] = {}
    if not progress_file.exists():
        return data

    with progress_file.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split(",")
            if len(parts) not in (5, 6):
                continue

            if len(parts) == 6:
                algorithm_token, run_id, step_s, frame_s, capture_s, reward_s = parts
            else:
                algorithm_token, run_id, step_s, frame_s, capture_s = parts
                reward_s = "nan"

            try:
                step = int(step_s)
                frame = float(frame_s)
                capture_pct = float(capture_s)
                reward = float(reward_s)
            except ValueError:
                continue

            if step <= 0:
                continue

            if "@" in algorithm_token:
                algorithm, device_label_key = algorithm_token.split("@", 1)
                device_label_key = device_label_key.strip().lower()
            else:
                algorithm = algorithm_token.strip().lower()
                device_label_key = "default"

            algorithm = algorithm.strip().lower()
            if not algorithm:
                continue

            algo_data = data.setdefault(algorithm, {})
            device_data = algo_data.setdefault(device_label_key, {})
            run_data = device_data.setdefault(run_id, {})
            run_data[step] = (frame, capture_pct, reward)

    return data


def _resolve_epsilon_from_cli_or_meta(
    args: argparse.Namespace,
    meta: dict[str, str],
) -> tuple[int, float, float, float]:
    resolved: dict[str, float | int] = {}
    missing: list[str] = []

    if args.epsilon_max_frames is not None:
        resolved["max_frames"] = int(args.epsilon_max_frames)
    elif "max_frames" in meta:
        try:
            resolved["max_frames"] = int(meta["max_frames"])
        except ValueError as exc:
            raise ValueError("Invalid max_frames value in progress metadata.") from exc
    else:
        missing.append("max_frames")

    if args.epsilon_init is not None:
        resolved["epsilon_init"] = float(args.epsilon_init)
    elif "epsilon_init" in meta:
        try:
            resolved["epsilon_init"] = float(meta["epsilon_init"])
        except ValueError as exc:
            raise ValueError("Invalid epsilon_init value in progress metadata.") from exc
    else:
        missing.append("epsilon_init")

    if args.epsilon_end is not None:
        resolved["epsilon_end"] = float(args.epsilon_end)
    elif "epsilon_end" in meta:
        try:
            resolved["epsilon_end"] = float(meta["epsilon_end"])
        except ValueError as exc:
            raise ValueError("Invalid epsilon_end value in progress metadata.") from exc
    else:
        missing.append("epsilon_end")

    if args.epsilon_anneal_ratio is not None:
        resolved["epsilon_anneal_ratio"] = float(args.epsilon_anneal_ratio)
    elif "epsilon_anneal_ratio" in meta:
        try:
            resolved["epsilon_anneal_ratio"] = float(meta["epsilon_anneal_ratio"])
        except ValueError as exc:
            raise ValueError("Invalid epsilon_anneal_ratio value in progress metadata.") from exc
    else:
        missing.append("epsilon_anneal_ratio")

    if missing:
        raise ValueError(
            "Missing epsilon schedule values: "
            + ", ".join(missing)
            + ". Provide all missing --epsilon-* flags or use a progress file emitted by run_benchmark.py with full #meta epsilon keys."
        )

    epsilon_max_frames = int(resolved["max_frames"])
    epsilon_init = float(resolved["epsilon_init"])
    epsilon_end = float(resolved["epsilon_end"])
    epsilon_anneal_ratio = float(resolved["epsilon_anneal_ratio"])

    if epsilon_max_frames < 1:
        raise ValueError("--epsilon-max-frames must be >= 1")
    if not (0.0 <= epsilon_end <= epsilon_init <= 1.0):
        raise ValueError("--epsilon values must satisfy 0 <= epsilon-end <= epsilon-init <= 1")
    if not (0.0 < epsilon_anneal_ratio <= 1.0):
        raise ValueError("--epsilon-anneal-ratio must be in (0, 1]")

    return epsilon_max_frames, epsilon_init, epsilon_end, epsilon_anneal_ratio


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
        description="Plot true capture snapshots, average reward, and epsilon across benchmark runs."
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
        "--reward-id",
        type=str,
        default="current",
        help=(
            "Reward strategy folder under <runs-root>/<maze> (default: current). "
            "When absent and reward-id is current, the script falls back to legacy layouts."
        ),
    )
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        help=(
            "Device subfolder to read from (for example: cpu, cuda, cuda:0). "
            "Use 'auto' to include all available device labels under the selected root."
        ),
    )
    parser.add_argument(
        "--progress-file",
        type=Path,
        default=None,
        help=(
            "Progress file generated by run_benchmark.py (default: <runs-root>/<maze>/live_progress.csvl). "
            "Used to auto-read epsilon max-frames metadata when available."
        ),
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
        "--epsilon-max-frames",
        type=int,
        default=None,
        help="Frame budget used for epsilon overlay (default: auto-match training schedule).",
    )
    parser.add_argument(
        "--epsilon-init",
        type=float,
        default=None,
        help="Initial epsilon for overlay (default: auto-match training schedule).",
    )
    parser.add_argument(
        "--epsilon-end",
        type=float,
        default=None,
        help="Final epsilon floor for overlay (default: auto-match training schedule).",
    )
    parser.add_argument(
        "--epsilon-anneal-ratio",
        type=float,
        default=None,
        help="Fraction of epsilon-max-frames used for linear anneal (default: auto-match training schedule).",
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
        help="Output PNG path. Defaults to <runs-root>/<maze>/<reward-id>/<algorithm>_capture_multiseed_mean_std.png",
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
    progress_file = args.progress_file if args.progress_file is not None else maze_runs_root / "live_progress.csvl"
    progress_data = _parse_progress_data(progress_file)

    reward_runs_root = maze_runs_root / args.reward_id
    if reward_runs_root.exists():
        discovery_root = reward_runs_root
    elif args.reward_id == "current":
        # Backward compatibility for older layouts that did not isolate by reward id.
        discovery_root = maze_runs_root
    else:
        raise FileNotFoundError(
            f"Reward folder not found: {reward_runs_root}. "
            "Check --reward-id or --runs-root/--maze."
        )

    requested_device = args.device.strip().lower()
    if requested_device != "auto":
        selected_device_label = device_label(requested_device)
        device_root = discovery_root / selected_device_label
        if not device_root.exists():
            raise FileNotFoundError(
                f"Device folder not found: {device_root}. "
                "Use --device auto to search all device labels."
            )
        discovery_root = device_root

    # Always save default plots under the selected reward-id folder.
    default_out_root = reward_runs_root

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

    show_epsilon = "iql" in algorithms
    if show_epsilon:
        progress_meta = _parse_progress_meta(progress_file)
        epsilon_max_frames, epsilon_init, epsilon_end, epsilon_anneal_ratio = _resolve_epsilon_from_cli_or_meta(
            args,
            progress_meta,
        )
        epsilon_source = (
            "metadata"
            if all(
                value is None
                for value in (
                    args.epsilon_max_frames,
                    args.epsilon_init,
                    args.epsilon_end,
                    args.epsilon_anneal_ratio,
                )
            )
            else "cli+metadata"
        )
    else:
        epsilon_max_frames = 1
        epsilon_init = 1.0
        epsilon_end = 0.0
        epsilon_anneal_ratio = 1.0
        epsilon_source = "disabled"

    if args.out is None:
        if len(algorithms) == 1:
            args.out = default_out_root / f"{algorithms[0]}_capture_multiseed_mean_std.png"
        else:
            args.out = default_out_root / "benchmark_capture_multiseed_mean_std.png"

    color_map = {
        "iql": "#1f77b4",
        "vdn": "#d62728",
        "qmixlocal": "#2ca02c",
        "qmixglobal": "#9467bd",
    }

    per_algorithm: dict[str, dict[str, object]] = {}
    selected_run_names = (
        {path.name for path in args.run_dir if path is not None}
        if args.run_dir
        else None
    )

    for algorithm in algorithms:
        by_device = progress_data.get(algorithm, {})
        if not by_device:
            print(
                f"Warning: no progress data found for algorithm={algorithm} in {progress_file}"
            )
            continue

        if requested_device == "auto":
            selected_devices = sorted(by_device.keys())
        else:
            selected_label = device_label(requested_device)
            selected_devices = [selected_label] if selected_label in by_device else []

        if not selected_devices:
            print(
                f"Warning: no progress data found for algorithm={algorithm} "
                f"and requested device selector={requested_device}."
            )
            continue

        series_frames: list[np.ndarray] = []
        series_capture_pct: list[np.ndarray] = []
        series_reward_mean: list[np.ndarray] = []
        used_run_dirs: list[str] = []

        for device_key in selected_devices:
            for run_id, step_map in by_device.get(device_key, {}).items():
                if selected_run_names is not None and run_id not in selected_run_names:
                    continue

                ordered_steps = sorted(step_map.keys())
                if not ordered_steps:
                    continue

                frames = np.asarray([step_map[step][0] for step in ordered_steps], dtype=float)
                captures = np.asarray([step_map[step][1] for step in ordered_steps], dtype=float)
                rewards = np.asarray([step_map[step][2] for step in ordered_steps], dtype=float)

                # Keep only points with true capture snapshots (NaN marks non-evaluated steps).
                valid_mask = ~np.isnan(captures)
                if not np.any(valid_mask):
                    continue

                frames = frames[valid_mask]
                captures = captures[valid_mask]
                rewards = rewards[valid_mask]

                captures = _moving_average(captures, args.window)
                rewards = _moving_average(rewards, args.window)

                series_frames.append(frames)
                series_capture_pct.append(captures)
                series_reward_mean.append(rewards)
                used_run_dirs.append(f"{algorithm}@{device_key}:{run_id}")

        if not series_capture_pct:
            print(
                "Warning: no true capture snapshots found for algorithm="
                f"{algorithm} in {progress_file}."
            )
            continue

        min_len = min(
            min(len(arr) for arr in series_capture_pct),
            min(len(arr) for arr in series_reward_mean),
        )
        captures_mat = np.vstack([arr[:min_len] for arr in series_capture_pct])
        rewards_mat = np.vstack([arr[:min_len] for arr in series_reward_mean])
        frames_mat = np.vstack([arr[:min_len] for arr in series_frames])

        per_algorithm[algorithm] = {
            "frames": np.mean(frames_mat, axis=0),
            "capture_mean": np.mean(captures_mat, axis=0),
            "capture_std": np.std(captures_mat, axis=0),
            "captures_mat": captures_mat,
            "reward_mean": np.mean(rewards_mat, axis=0),
            "reward_std": np.std(rewards_mat, axis=0),
            "used_run_dirs": used_run_dirs,
            "color": color_map.get(algorithm, "#1f77b4"),
        }

    if not per_algorithm:
        raise FileNotFoundError(
            "No usable runs were found for selected algorithms."
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(1, 1, figsize=(10, 5))
    ax_reward = ax.twinx()
    ax_eps = ax.twinx()
    ax_eps.spines["right"].set_position(("outward", 55))

    for algorithm, payload in per_algorithm.items():
        frames = payload["frames"]
        capture_mean = payload["capture_mean"]
        capture_std = payload["capture_std"]
        captures_mat = payload["captures_mat"]
        reward_mean = payload["reward_mean"]
        color = payload["color"]

        if args.show_runs:
            for capture_series in captures_mat:
                ax.plot(frames, capture_series, color=color, linewidth=1, alpha=0.18)

        ax.plot(
            frames,
            capture_mean,
            label=f"{algorithm.upper()} mean capture % (n={captures_mat.shape[0]})",
            color=color,
            linewidth=2,
        )
        ax.fill_between(
            frames,
            np.maximum(capture_mean - capture_std, 0.0),
            np.minimum(capture_mean + capture_std, 100.0),
            color=color,
            alpha=0.14,
        )

        ax_reward.plot(
            frames,
            reward_mean,
            label=f"{algorithm.upper()} mean reward",
            color=color,
            linewidth=1.8,
            linestyle=":",
        )

    max_display_frame = max(
        float(np.nanmax(payload["frames"]))
        for payload in per_algorithm.values()
        if np.asarray(payload["frames"]).size > 0
    )

    if show_epsilon and max_display_frame > 0.0:
        x_eps = np.linspace(0.0, max_display_frame, 256, dtype=np.float64)
        y_eps = _epsilon_for_frames(
            x_eps,
            epsilon_max_frames=epsilon_max_frames,
            epsilon_init=epsilon_init,
            epsilon_end=epsilon_end,
            epsilon_anneal_ratio=epsilon_anneal_ratio,
        )
        ax_eps.plot(
            x_eps,
            y_eps,
            color="black",
            linewidth=2,
            linestyle="-",
            label="Epsilon",
        )
    ax_reward.set_ylabel("Average Reward", color="dimgray")
    ax_reward.tick_params(axis="y", colors="dimgray")
    ax_eps.set_ylabel("Epsilon", color="black")
    ax_eps.set_ylim(0.0, 1.05)
    ax_eps.tick_params(axis="y", colors="black")

    ax.set_xlabel("Total frames")
    ax.set_ylabel("True Capture Rate (%)")
    ax.set_ylim(0.0, 100.0)
    ax.set_title("Benchmark True Capture Rate Across Runs")
    ax.grid(True, alpha=0.3)
    handles, labels = ax.get_legend_handles_labels()
    reward_handles, reward_labels = ax_reward.get_legend_handles_labels()
    handles += reward_handles
    labels += reward_labels
    eps_handles, eps_labels = ax_eps.get_legend_handles_labels()
    handles += eps_handles
    labels += eps_labels
    ax.legend(handles, labels)

    fig.tight_layout()
    fig.savefig(args.out, dpi=150)

    print(f"Algorithms: {', '.join(sorted(per_algorithm.keys()))}")
    print(
        "Epsilon overlay: "
        f"init={epsilon_init} end={epsilon_end} "
        f"anneal_ratio={epsilon_anneal_ratio} max_frames={epsilon_max_frames}"
    )
    print(f"Epsilon source: {epsilon_source}")
    for algorithm, payload in per_algorithm.items():
        used_run_dirs = payload["used_run_dirs"]
        capture_mean = payload["capture_mean"]
        capture_std = payload["capture_std"]
        reward_mean = payload["reward_mean"]
        reward_std = payload["reward_std"]
        print(f"\nAlgorithm: {algorithm}")
        print(f"Included runs: {len(used_run_dirs)}")
        for run_dir in used_run_dirs:
            print(f"- {run_dir}")
        print(f"Mean capture % min/max: {capture_mean.min():.3f}/{capture_mean.max():.3f}")
        print(f"Std capture % min/max: {capture_std.min():.3f}/{capture_std.max():.3f}")
        print(f"Mean reward min/max: {reward_mean.min():.3f}/{reward_mean.max():.3f}")
        print(f"Std reward min/max: {reward_std.min():.3f}/{reward_std.max():.3f}")

    print(f"Saved: {args.out}")

    if not args.no_open:
        _open_file(args.out)


if __name__ == "__main__":
    main()
