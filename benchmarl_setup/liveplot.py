import argparse
import time
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from algorithm_utils import SUPPORTED_ALGORITHMS, SUPPORTED_MAZES, normalize_algorithm, runs_root_for_maze
from device_utils import device_label


def _moving_average(values: np.ndarray, window: int) -> np.ndarray:
    if window <= 1:
        return values.copy()

    out = np.zeros_like(values)
    for i in range(len(values)):
        start = max(0, i - window + 1)
        out[i] = float(np.mean(values[start : i + 1]))
    return out


def _parse_progress_file(
    progress_file: Path,
) -> tuple[dict[str, dict[str, dict[str, dict[int, tuple[float, float, float]]]]], dict[str, str]]:
    # Returns: algorithm -> device_label -> run_id -> step -> (frame, capture_pct, reward)
    data: dict[str, dict[str, dict[str, dict[int, tuple[float, float, float]]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(dict))
    )
    meta: dict[str, str] = {}

    if not progress_file.exists():
        return data, meta

    with progress_file.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue

            if line.startswith("#meta,"):
                for chunk in line[len("#meta,") :].split(","):
                    key, sep, value = chunk.partition("=")
                    if sep != "=":
                        continue
                    parsed_key = key.strip()
                    if not parsed_key:
                        continue
                    meta[parsed_key] = value.strip()
                continue

            parts = line.split(",")
            if len(parts) not in (5, 6):
                continue

            if len(parts) == 6:
                algorithm_token, run_id, step_s, frame_s, capture_s, reward_s = parts
            else:
                # Backward compatibility with old progress files that only carried one metric.
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
                algorithm, label = algorithm_token.split("@", 1)
                label = label.strip().lower()
            else:
                algorithm = algorithm_token
                label = "default"

            algorithm = algorithm.strip().lower()
            if not algorithm:
                continue

            data[algorithm][label][run_id][step] = (frame, capture_pct, reward)

    return data, meta


def _resolve_epsilon_from_cli_or_meta(
    args: argparse.Namespace,
    meta: dict[str, str],
) -> tuple[int, float, float, float] | None:
    resolved: dict[str, float | int] = {}
    missing: list[str] = []

    cli_fields = (
        args.epsilon_max_frames,
        args.epsilon_init,
        args.epsilon_end,
        args.epsilon_anneal_ratio,
    )
    any_cli_override = any(value is not None for value in cli_fields)

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
        if not any_cli_override:
            # No fallback constants: simply wait until progress metadata is available.
            return None
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


def _aggregate_algorithm_runs(
    run_steps: dict[str, dict[int, tuple[float, float, float]]],
    window: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, int] | None:
    if not run_steps:
        return None

    max_step = max((max(step_map.keys()) for step_map in run_steps.values() if step_map), default=0)
    if max_step <= 0:
        return None

    n_runs = len(run_steps)
    frames_mat = np.full((n_runs, max_step), np.nan, dtype=np.float64)
    captures_mat = np.full((n_runs, max_step), np.nan, dtype=np.float64)
    rewards_mat = np.full((n_runs, max_step), np.nan, dtype=np.float64)

    for run_idx, step_map in enumerate(run_steps.values()):
        for step, values in step_map.items():
            if 1 <= step <= max_step:
                frame, capture_pct, reward = values
                frames_mat[run_idx, step - 1] = frame
                captures_mat[run_idx, step - 1] = capture_pct
                rewards_mat[run_idx, step - 1] = reward

    mean_captures = np.nanmean(captures_mat, axis=0)
    std_captures = np.nanstd(captures_mat, axis=0)
    mean_rewards = np.nanmean(rewards_mat, axis=0)
    std_rewards = np.nanstd(rewards_mat, axis=0)
    mean_frames = np.nanmean(frames_mat, axis=0)

    # Fallback when frame values are not available for a point.
    invalid_frames = np.isnan(mean_frames)
    if np.any(invalid_frames):
        step_axis = np.arange(1, max_step + 1, dtype=np.float64)
        mean_frames[invalid_frames] = step_axis[invalid_frames]

    mean_captures = _moving_average(mean_captures, window)
    std_captures = _moving_average(std_captures, window)
    mean_rewards = _moving_average(mean_rewards, window)
    std_rewards = _moving_average(std_rewards, window)
    mean_frames = mean_frames[: len(mean_captures)]

    return mean_frames, mean_captures, std_captures, mean_rewards, std_rewards, n_runs


class LiveComparisonPlotter:
    def __init__(
        self,
        algorithms: list[str],
        window: int,
        device_selector: str,
        epsilon_max_frames: int,
        epsilon_init: float,
        epsilon_end: float,
        epsilon_anneal_ratio: float,
        show_epsilon_overlay: bool,
    ) -> None:
        self.algorithms = algorithms
        self.window = window
        self.device_selector = device_selector
        self.epsilon_max_frames = max(1, int(epsilon_max_frames))
        self.epsilon_init = float(epsilon_init)
        self.epsilon_end = float(epsilon_end)
        self.epsilon_anneal_ratio = float(epsilon_anneal_ratio)
        self.show_epsilon_overlay = bool(show_epsilon_overlay)

        self.fig, self.ax = plt.subplots(1, 1, figsize=(10, 5))
        self.ax_reward = self.ax.twinx()
        self.ax_eps = self.ax.twinx()
        self.ax_eps.spines["right"].set_position(("outward", 55))
        self.lines_capture: dict[str, any] = {}
        self.lines_reward: dict[str, any] = {}
        self.fills_capture: dict[str, any] = {}
        self.epsilon_line = None

        self.color_map = {
            "iql": "#1f77b4",
            "vdn": "#d62728",
            "qmixlocal": "#2ca02c",
            "qmixglobal": "#9467bd",
        }

        self.style_map = {
            "cpu": "--",
            "cuda": "-",
            "default": "-",
        }

        self._init_plot()

    def _init_plot(self) -> None:
        self.ax.set_title("Live Benchmark Comparison (Rolling Capture %)")
        self.ax.set_xlabel("Total frames")
        self.ax.set_ylabel("Estimated Capture Rate (%)")
        self.ax.set_ylim(0.0, 100.0)
        self.ax.grid(True, alpha=0.3)
        self.ax_reward.set_ylabel("Average Reward", color="dimgray")
        self.ax_reward.tick_params(axis="y", colors="dimgray")
        self.ax_eps.set_ylabel("Epsilon", color="black")
        self.ax_eps.set_ylim(0.0, 1.05)
        self.ax_eps.tick_params(axis="y", colors="black")
        plt.ion()
        plt.show(block=False)

    def _line_style_for_device(self, device_key: str) -> str:
        key = (device_key or "").strip().lower()
        if key.startswith("cuda"):
            return "-"
        if key.startswith("cpu"):
            return "--"
        return self.style_map.get(key, "-")

    def _epsilon_for_frames(self, frames: np.ndarray) -> np.ndarray:
        anneal_frames = max(1.0, float(self.epsilon_max_frames) * self.epsilon_anneal_ratio)
        span = self.epsilon_init - self.epsilon_end
        eps = self.epsilon_init - span * np.minimum(frames, anneal_frames) / anneal_frames
        return np.maximum(eps, self.epsilon_end)

    def _update_epsilon_curve(self, max_display_frame: float, show: bool) -> None:
        if not show or max_display_frame <= 0:
            if self.epsilon_line is not None:
                self.epsilon_line.remove()
                self.epsilon_line = None
            return

        x = np.linspace(0.0, max_display_frame, 256, dtype=np.float64)
        y = self._epsilon_for_frames(x)
        if self.epsilon_line is None:
            (self.epsilon_line,) = self.ax_eps.plot(
                x,
                y,
                color="black",
                linewidth=2,
                linestyle="-",
                label="Epsilon",
            )
        else:
            self.epsilon_line.set_data(x, y)

    def set_epsilon_schedule(
        self,
        epsilon_max_frames: int,
        epsilon_init: float,
        epsilon_end: float,
        epsilon_anneal_ratio: float,
    ) -> None:
        self.epsilon_max_frames = max(1, int(epsilon_max_frames))
        self.epsilon_init = float(epsilon_init)
        self.epsilon_end = float(epsilon_end)
        self.epsilon_anneal_ratio = float(epsilon_anneal_ratio)
        self.show_epsilon_overlay = True

    def update_from_file(self, progress_file: Path) -> None:
        data, _meta = _parse_progress_file(progress_file)

        # Remove old fills so uncertainty bands can be redrawn cleanly.
        for fill in self.fills_capture.values():
            fill.remove()
        self.fills_capture.clear()

        active_keys: set[str] = set()
        max_display_frame = 0.0
        for algorithm in self.algorithms:
            by_device = data.get(algorithm, {})
            if not by_device:
                continue

            if self.device_selector == "all":
                selected_labels = sorted(by_device.keys())
            else:
                selected_labels = [self.device_selector] if self.device_selector in by_device else []

            for device_key in selected_labels:
                run_steps = by_device.get(device_key, {})
                aggregated = _aggregate_algorithm_runs(run_steps, self.window)
                if aggregated is None:
                    continue

                frames, mean_captures, std_captures, mean_rewards, _std_rewards, n_runs = aggregated
                if frames.size:
                    max_display_frame = max(max_display_frame, float(np.nanmax(frames)))
                color = self.color_map.get(algorithm, "#1f77b4")
                line_style = self._line_style_for_device(device_key)
                series_key = f"{algorithm}@{device_key}"
                active_keys.add(series_key)
                legend_capture = f"{algorithm.upper()}@{device_key} capture% (n={n_runs})"
                legend_reward = f"{algorithm.upper()}@{device_key} reward"

                if series_key not in self.lines_capture:
                    (line,) = self.ax.plot(
                        frames,
                        mean_captures,
                        color=color,
                        linestyle=line_style,
                        linewidth=2,
                        label=legend_capture,
                    )
                    self.lines_capture[series_key] = line
                else:
                    line = self.lines_capture[series_key]
                    line.set_data(frames, mean_captures)
                    line.set_label(legend_capture)
                    line.set_linestyle(line_style)

                self.fills_capture[series_key] = self.ax.fill_between(
                    frames,
                    np.maximum(mean_captures - std_captures, 0.0),
                    np.minimum(mean_captures + std_captures, 100.0),
                    color=color,
                    alpha=0.15,
                )

                if not np.all(np.isnan(mean_rewards)):
                    if series_key not in self.lines_reward:
                        (reward_line,) = self.ax_reward.plot(
                            frames,
                            mean_rewards,
                            color=color,
                            linestyle=":",
                            linewidth=1.8,
                            label=legend_reward,
                        )
                        self.lines_reward[series_key] = reward_line
                    else:
                        reward_line = self.lines_reward[series_key]
                        reward_line.set_data(frames, mean_rewards)
                        reward_line.set_label(legend_reward)
                elif series_key in self.lines_reward:
                    stale_reward = self.lines_reward.pop(series_key)
                    stale_reward.remove()

        stale_keys = [key for key in self.lines_capture.keys() if key not in active_keys]
        for key in stale_keys:
            line = self.lines_capture.pop(key)
            line.remove()
            fill = self.fills_capture.pop(key, None)
            if fill is not None:
                fill.remove()
            reward_line = self.lines_reward.pop(key, None)
            if reward_line is not None:
                reward_line.remove()

        # Keep legend current with active algorithms.
        show_epsilon = "iql" in self.algorithms and self.show_epsilon_overlay
        self._update_epsilon_curve(max_display_frame, show=show_epsilon)

        handles, labels = self.ax.get_legend_handles_labels()
        reward_handles, reward_labels = self.ax_reward.get_legend_handles_labels()
        handles += reward_handles
        labels += reward_labels
        if self.epsilon_line is not None:
            eps_handles, eps_labels = self.ax_eps.get_legend_handles_labels()
            handles += eps_handles
            labels += eps_labels
        if handles:
            self.ax.legend(handles, labels)

        self.ax.relim()
        self.ax.autoscale_view()
        self.ax_reward.relim()
        self.ax_reward.autoscale_view()
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    def close(self) -> None:
        plt.close(self.fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Monitor benchmark live progress and plot mean +/- std across algorithms."
    )
    parser.add_argument(
        "--progress-file",
        type=Path,
        default=None,
        help="Progress file generated by run_benchmark.py (default: <runs-root>/<maze>/live_progress.csvl).",
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
        help="Comma-separated algorithms to display.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Polling interval in seconds.",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=30,
        help="Smoothing window applied to aggregated curves.",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="all",
        help=(
            "Device label to display from live progress (for example: cpu, cuda, cuda_0). "
            "Use 'all' to show all device labels present in the file."
        ),
    )
    parser.add_argument(
        "--epsilon-max-frames",
        type=int,
        default=None,
        help="Frame budget used for epsilon schedule overlay (default: auto-match training schedule).",
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
    return parser.parse_args()


def _normalize_device_selector(raw: str) -> str:
    value = raw.strip().lower()
    if value == "all":
        return value
    if not value:
        raise ValueError("Device selector cannot be empty.")
    return device_label(value)


def main() -> None:
    args = parse_args()
    maze_runs_root = runs_root_for_maze(args.runs_root, args.maze)
    progress_file = args.progress_file if args.progress_file is not None else maze_runs_root / "live_progress.csvl"
    algorithms = [normalize_algorithm(item) for item in args.algorithms.split(",") if item.strip()]
    if not algorithms:
        raise ValueError("At least one algorithm must be provided.")
    invalid = [name for name in algorithms if name not in SUPPORTED_ALGORITHMS]
    if invalid:
        raise ValueError(f"Unsupported algorithm(s): {invalid}. Allowed: {list(SUPPORTED_ALGORITHMS)}")
    device_selector = _normalize_device_selector(args.device)

    if args.window < 1:
        raise ValueError("--window must be >= 1")

    show_epsilon = "iql" in algorithms
    waiting_for_meta = False
    if show_epsilon:
        _, meta = _parse_progress_file(progress_file)
        epsilon_cfg = _resolve_epsilon_from_cli_or_meta(
            args,
            meta,
        )
        if epsilon_cfg is None:
            waiting_for_meta = True
            epsilon_max_frames = 1
            epsilon_init = 1.0
            epsilon_end = 0.0
            epsilon_anneal_ratio = 1.0
        else:
            epsilon_max_frames, epsilon_init, epsilon_end, epsilon_anneal_ratio = epsilon_cfg
    else:
        epsilon_max_frames = 1
        epsilon_init = 1.0
        epsilon_end = 0.0
        epsilon_anneal_ratio = 1.0

    print(f"[LivePlot] Watching: {progress_file}")
    print(f"[LivePlot] Algorithms: {', '.join(algorithms)}")
    print(f"[LivePlot] Device selector: {device_selector}")
    print(
        "[LivePlot] Epsilon overlay: "
        f"init={epsilon_init} end={epsilon_end} "
        f"anneal_ratio={epsilon_anneal_ratio} max_frames={epsilon_max_frames}"
    )
    if waiting_for_meta:
        print(
            "[LivePlot] Epsilon overlay pending: waiting for full #meta keys "
            "(max_frames, epsilon_init, epsilon_end, epsilon_anneal_ratio)."
        )

    plotter = LiveComparisonPlotter(
        algorithms=algorithms,
        window=max(1, args.window),
        device_selector=device_selector,
        epsilon_max_frames=epsilon_max_frames,
        epsilon_init=epsilon_init,
        epsilon_end=epsilon_end,
        epsilon_anneal_ratio=epsilon_anneal_ratio,
        show_epsilon_overlay=show_epsilon and not waiting_for_meta,
    )
    try:
        while True:
            if show_epsilon and not plotter.show_epsilon_overlay:
                _, loop_meta = _parse_progress_file(progress_file)
                loop_epsilon_cfg = _resolve_epsilon_from_cli_or_meta(args, loop_meta)
                if loop_epsilon_cfg is not None:
                    loop_max_frames, loop_init, loop_end, loop_ratio = loop_epsilon_cfg
                    plotter.set_epsilon_schedule(
                        epsilon_max_frames=loop_max_frames,
                        epsilon_init=loop_init,
                        epsilon_end=loop_end,
                        epsilon_anneal_ratio=loop_ratio,
                    )
                    print(
                        "[LivePlot] Epsilon overlay enabled from progress metadata: "
                        f"init={loop_init} end={loop_end} anneal_ratio={loop_ratio} "
                        f"max_frames={loop_max_frames}"
                    )
            plotter.update_from_file(progress_file)
            time.sleep(max(0.2, args.interval))
    except KeyboardInterrupt:
        print("\n[LivePlot] Exiting on user interrupt.")
        plotter.close()


if __name__ == "__main__":
    main()
