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
) -> dict[str, dict[str, dict[str, dict[int, tuple[float, float]]]]]:
    # Returns: algorithm -> device_label -> run_id -> step -> (frame, reward)
    data: dict[str, dict[str, dict[str, dict[int, tuple[float, float]]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(dict))
    )

    if not progress_file.exists():
        return data

    with progress_file.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue

            parts = line.split(",")
            if len(parts) != 5:
                continue

            algorithm_token, run_id, step_s, frame_s, reward_s = parts
            try:
                step = int(step_s)
                frame = float(frame_s)
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

            data[algorithm][label][run_id][step] = (frame, reward)

    return data


def _aggregate_algorithm_runs(
    run_steps: dict[str, dict[int, tuple[float, float]]],
    window: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int] | None:
    if not run_steps:
        return None

    max_step = max((max(step_map.keys()) for step_map in run_steps.values() if step_map), default=0)
    if max_step <= 0:
        return None

    n_runs = len(run_steps)
    frames_mat = np.full((n_runs, max_step), np.nan, dtype=np.float64)
    rewards_mat = np.full((n_runs, max_step), np.nan, dtype=np.float64)

    for run_idx, step_map in enumerate(run_steps.values()):
        for step, values in step_map.items():
            if 1 <= step <= max_step:
                frame, reward = values
                frames_mat[run_idx, step - 1] = frame
                rewards_mat[run_idx, step - 1] = reward

    mean_rewards = np.nanmean(rewards_mat, axis=0)
    std_rewards = np.nanstd(rewards_mat, axis=0)
    mean_frames = np.nanmean(frames_mat, axis=0)

    # Fallback when frame values are not available for a point.
    invalid_frames = np.isnan(mean_frames)
    if np.any(invalid_frames):
        step_axis = np.arange(1, max_step + 1, dtype=np.float64)
        mean_frames[invalid_frames] = step_axis[invalid_frames]

    mean_rewards = _moving_average(mean_rewards, window)
    std_rewards = _moving_average(std_rewards, window)
    mean_frames = mean_frames[: len(mean_rewards)]

    return mean_frames, mean_rewards, std_rewards, n_runs


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
    ) -> None:
        self.algorithms = algorithms
        self.window = window
        self.device_selector = device_selector
        self.epsilon_max_frames = max(1, int(epsilon_max_frames))
        self.epsilon_init = float(epsilon_init)
        self.epsilon_end = float(epsilon_end)
        self.epsilon_anneal_ratio = float(epsilon_anneal_ratio)

        self.fig, self.ax = plt.subplots(1, 1, figsize=(10, 5))
        self.ax_eps = self.ax.twinx()
        self.lines: dict[str, any] = {}
        self.fills: dict[str, any] = {}
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
        self.ax.set_title("Live Benchmark Comparison (Mean +/- Std)")
        self.ax.set_xlabel("Total frames")
        self.ax.set_ylabel("Reward")
        self.ax.grid(True, alpha=0.3)
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

    def update_from_file(self, progress_file: Path) -> None:
        data = _parse_progress_file(progress_file)

        # Remove old fills so uncertainty bands can be redrawn cleanly.
        for fill in self.fills.values():
            fill.remove()
        self.fills.clear()

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

                frames, mean_rewards, std_rewards, n_runs = aggregated
                if frames.size:
                    max_display_frame = max(max_display_frame, float(np.nanmax(frames)))
                color = self.color_map.get(algorithm, "#1f77b4")
                line_style = self._line_style_for_device(device_key)
                series_key = f"{algorithm}@{device_key}"
                active_keys.add(series_key)
                legend_label = f"{algorithm.upper()}@{device_key} (n={n_runs})"

                if series_key not in self.lines:
                    (line,) = self.ax.plot(
                        frames,
                        mean_rewards,
                        color=color,
                        linestyle=line_style,
                        linewidth=2,
                        label=legend_label,
                    )
                    self.lines[series_key] = line
                else:
                    line = self.lines[series_key]
                    line.set_data(frames, mean_rewards)
                    line.set_label(legend_label)
                    line.set_linestyle(line_style)

                self.fills[series_key] = self.ax.fill_between(
                    frames,
                    mean_rewards - std_rewards,
                    mean_rewards + std_rewards,
                    color=color,
                    alpha=0.15,
                )

        stale_keys = [key for key in self.lines.keys() if key not in active_keys]
        for key in stale_keys:
            line = self.lines.pop(key)
            line.remove()
            fill = self.fills.pop(key, None)
            if fill is not None:
                fill.remove()

        # Keep legend current with active algorithms.
        show_epsilon = "iql" in self.algorithms
        self._update_epsilon_curve(max_display_frame, show=show_epsilon)

        handles, labels = self.ax.get_legend_handles_labels()
        if self.epsilon_line is not None:
            eps_handles, eps_labels = self.ax_eps.get_legend_handles_labels()
            handles += eps_handles
            labels += eps_labels
        if handles:
            self.ax.legend(handles, labels)

        self.ax.relim()
        self.ax.autoscale_view()
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
        default=100000,
        help="Frame budget used for epsilon schedule overlay.",
    )
    parser.add_argument(
        "--epsilon-init",
        type=float,
        default=1.0,
        help="Initial epsilon for overlay.",
    )
    parser.add_argument(
        "--epsilon-end",
        type=float,
        default=0.05,
        help="Final epsilon floor for overlay.",
    )
    parser.add_argument(
        "--epsilon-anneal-ratio",
        type=float,
        default=0.8,
        help="Fraction of epsilon-max-frames used for linear anneal.",
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
    if args.epsilon_max_frames < 1:
        raise ValueError("--epsilon-max-frames must be >= 1")
    if not (0.0 <= args.epsilon_end <= args.epsilon_init <= 1.0):
        raise ValueError("--epsilon values must satisfy 0 <= epsilon-end <= epsilon-init <= 1")
    if not (0.0 < args.epsilon_anneal_ratio <= 1.0):
        raise ValueError("--epsilon-anneal-ratio must be in (0, 1]")

    print(f"[LivePlot] Watching: {progress_file}")
    print(f"[LivePlot] Algorithms: {', '.join(algorithms)}")
    print(f"[LivePlot] Device selector: {device_selector}")
    print(
        "[LivePlot] Epsilon overlay: "
        f"init={args.epsilon_init} end={args.epsilon_end} "
        f"anneal_ratio={args.epsilon_anneal_ratio} max_frames={args.epsilon_max_frames}"
    )

    plotter = LiveComparisonPlotter(
        algorithms=algorithms,
        window=max(1, args.window),
        device_selector=device_selector,
        epsilon_max_frames=args.epsilon_max_frames,
        epsilon_init=args.epsilon_init,
        epsilon_end=args.epsilon_end,
        epsilon_anneal_ratio=args.epsilon_anneal_ratio,
    )
    try:
        while True:
            plotter.update_from_file(progress_file)
            time.sleep(max(0.2, args.interval))
    except KeyboardInterrupt:
        print("\n[LivePlot] Exiting on user interrupt.")
        plotter.close()


if __name__ == "__main__":
    main()
