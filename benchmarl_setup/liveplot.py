import argparse
import colorsys
import time
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from algorithm_utils import SUPPORTED_ALGORITHMS, SUPPORTED_MAZES, normalize_algorithm, runs_root_for_maze
from device_utils import device_label


def _epsilon_schedule_from_meta(meta: dict[str, str]) -> dict[str, float | int | str] | None:
    schedule_mode = (meta.get("epsilon_schedule_mode") or "").strip().lower()
    if schedule_mode == "curriculum_piecewise":
        try:
            return {
                "epsilon_schedule_mode": "curriculum_piecewise",
                "max_frames": int(meta["max_frames"]),
                "epsilon_stage_boundary_1": int(meta.get("epsilon_stage_boundary_1", "0")),
                "epsilon_stage_boundary_2": int(meta.get("epsilon_stage_boundary_2", "0")),
                "epsilon_easy_init": float(meta.get("epsilon_easy_init", "1.0")),
                "epsilon_easy_end": float(meta.get("epsilon_easy_end", "0.25")),
                "epsilon_medium_init": float(meta.get("epsilon_medium_init", "0.65")),
                "epsilon_medium_end": float(meta.get("epsilon_medium_end", "0.20")),
                "epsilon_hard_init": float(meta.get("epsilon_hard_init", "0.55")),
                "epsilon_hard_end": float(meta.get("epsilon_hard_end", "0.08")),
                "epsilon_init": float(meta.get("epsilon_init", "1.0")),
                "epsilon_end": float(meta.get("epsilon_end", "0.08")),
                "epsilon_anneal_ratio": float(meta.get("epsilon_anneal_ratio", "1.0")),
                "epsilon_anneal_frames": int(meta.get("epsilon_anneal_frames", meta["max_frames"])),
            }
        except (KeyError, ValueError):
            return None

    try:
        return {
            "epsilon_schedule_mode": "global",
            "max_frames": int(meta["max_frames"]),
            "epsilon_init": float(meta["epsilon_init"]),
            "epsilon_end": float(meta["epsilon_end"]),
            "epsilon_anneal_ratio": float(meta["epsilon_anneal_ratio"]),
            "epsilon_anneal_frames": int(meta.get("epsilon_anneal_frames", "0") or 0),
        }
    except (KeyError, ValueError):
        return None


def _epsilon_for_frames_schedule(frames: np.ndarray, schedule: dict[str, float | int | str]) -> np.ndarray:
    mode = str(schedule.get("epsilon_schedule_mode", "global")).strip().lower()
    x = np.maximum(frames.astype(np.float64), 0.0)

    if mode == "curriculum_piecewise":
        max_frames = max(1, int(schedule.get("max_frames", 1) or 1))
        b1 = max(0, min(max_frames, int(schedule.get("epsilon_stage_boundary_1", max_frames // 3) or 0)))
        b2 = max(b1, min(max_frames, int(schedule.get("epsilon_stage_boundary_2", (2 * max_frames) // 3) or b1)))

        easy_init = float(schedule.get("epsilon_easy_init", 1.0))
        easy_end = float(schedule.get("epsilon_easy_end", easy_init))
        medium_init = float(schedule.get("epsilon_medium_init", 0.65))
        medium_end = float(schedule.get("epsilon_medium_end", medium_init))
        hard_init = float(schedule.get("epsilon_hard_init", 0.55))
        hard_end = float(schedule.get("epsilon_hard_end", hard_init))

        y = np.empty_like(x)

        def _interp(start_frame: float, end_frame: float, start_eps: float, end_eps: float, values: np.ndarray) -> np.ndarray:
            span = max(1.0, end_frame - start_frame)
            progress = np.clip((values - start_frame) / span, 0.0, 1.0)
            return start_eps + (end_eps - start_eps) * progress

        easy_mask = x < float(b1)
        medium_mask = (x >= float(b1)) & (x < float(b2))
        hard_mask = x >= float(b2)

        y[easy_mask] = _interp(0.0, float(b1), easy_init, easy_end, x[easy_mask])
        y[medium_mask] = _interp(float(b1), float(b2), medium_init, medium_end, x[medium_mask])
        y[hard_mask] = _interp(float(b2), float(max_frames), hard_init, hard_end, np.minimum(x[hard_mask], float(max_frames)))
        return y

    epsilon_max_frames = max(1.0, float(schedule.get("max_frames", 1) or 1))
    epsilon_init = float(schedule.get("epsilon_init", 1.0))
    epsilon_end = float(schedule.get("epsilon_end", 0.1))
    epsilon_anneal_ratio = float(schedule.get("epsilon_anneal_ratio", 0.95))
    anneal_frames = max(1.0, epsilon_max_frames * epsilon_anneal_ratio)
    span = epsilon_init - epsilon_end
    eps = epsilon_init - span * np.minimum(x, anneal_frames) / anneal_frames
    return np.maximum(eps, epsilon_end)


def _moving_average(values: np.ndarray, window: int) -> np.ndarray:
    if window <= 1:
        return values.copy()

    out = np.full_like(values, np.nan, dtype=np.float64)
    for i in range(len(values)):
        start = max(0, i - window + 1)
        window_values = values[start : i + 1]
        if np.all(np.isnan(window_values)):
            out[i] = np.nan
        else:
            out[i] = float(np.nanmean(window_values))
    return out


def _parse_reward_terms_from_meta(meta: dict[str, str]) -> list[str]:
    raw_terms = (meta.get("reward_terms") or "").strip()
    if not raw_terms:
        return []
    return [term.strip() for term in raw_terms.split("|") if term.strip()]


def _is_terminal_reward_term(term_name: str) -> bool:
    normalized = str(term_name).strip().lower()
    return normalized in {
        "get_pacman",
        "pacman_timeout_win",
        "pacman_win_pellets",
    }


def _split_reward_and_device(label: str) -> tuple[str | None, str]:
    parts = [part.strip().lower() for part in str(label).split("@") if part.strip()]
    if not parts:
        return None, "default"
    if len(parts) == 1:
        return None, parts[0]
    return parts[0], parts[-1]


def _device_matches_selector(label: str, selector: str) -> bool:
    if selector == "all":
        return True
    _reward_id, parsed_device = _split_reward_and_device(label)
    return parsed_device == selector


def _reward_matches_selector(label: str, allowed_reward_ids: set[str] | None) -> bool:
    if allowed_reward_ids is None:
        return True
    reward_id, _parsed_device = _split_reward_and_device(label)
    # Legacy progress rows may not carry reward_id; treat them as current baseline.
    effective_reward_id = reward_id if reward_id is not None else "current"
    return effective_reward_id in allowed_reward_ids


def _color_with_multiplier(hex_color: str, multiplier: float) -> str:
    raw = str(hex_color).strip().lstrip("#")
    if len(raw) != 6:
        return hex_color
    try:
        r = int(raw[0:2], 16)
        g = int(raw[2:4], 16)
        b = int(raw[4:6], 16)
    except ValueError:
        return hex_color

    clamp = lambda channel: max(0, min(255, int(round(channel * multiplier))))
    return f"#{clamp(r):02x}{clamp(g):02x}{clamp(b):02x}"


def _hex_to_rgb01(hex_color: str) -> tuple[float, float, float] | None:
    raw = str(hex_color).strip().lstrip("#")
    if len(raw) != 6:
        return None
    try:
        r = int(raw[0:2], 16)
        g = int(raw[2:4], 16)
        b = int(raw[4:6], 16)
    except ValueError:
        return None
    return (r / 255.0, g / 255.0, b / 255.0)


def _rgb01_to_hex(rgb: tuple[float, float, float]) -> str:
    r, g, b = rgb
    clamp = lambda value: max(0, min(255, int(round(value * 255.0))))
    return f"#{clamp(r):02x}{clamp(g):02x}{clamp(b):02x}"


def _reward_variant_color(base_color: str, reward_id: str, ordered_reward_ids: list[str]) -> str:
    if len(ordered_reward_ids) <= 1:
        return base_color
    rgb = _hex_to_rgb01(base_color)
    if rgb is None:
        return base_color
    try:
        idx = ordered_reward_ids.index(reward_id)
    except ValueError:
        idx = 0
    count = len(ordered_reward_ids)
    phase = 0.5 if count <= 1 else idx / float(count - 1)
    h, l, s = colorsys.rgb_to_hls(*rgb)

    # Stronger separation for multiple reward IDs of the same algorithm.
    hue_shift = -0.42 + 0.84 * phase
    var_h = (h + hue_shift) % 1.0
    sat_targets = (0.98, 0.42, 0.90, 0.50)
    light_targets = (0.30, 0.72, 0.42, 0.62)
    var_s = sat_targets[idx % len(sat_targets)]
    var_l = light_targets[idx % len(light_targets)]

    variant_rgb = colorsys.hls_to_rgb(var_h, var_l, var_s)
    return _rgb01_to_hex(variant_rgb)


def _curriculum_transition_frames_from_meta(meta: dict[str, str]) -> list[tuple[float, str]]:
    curriculum_mode = (meta.get("pacman_curriculum") or "").strip().lower()
    if curriculum_mode != "easy-medium-hard":
        return []

    max_frames_raw = (meta.get("pacman_curriculum_max_frames") or "").strip()
    if not max_frames_raw:
        return []

    try:
        curriculum_max_frames = float(max_frames_raw)
    except ValueError:
        return []

    if curriculum_max_frames <= 0.0:
        return []

    offset_raw = (meta.get("pacman_curriculum_frame_offset") or "0").strip()
    try:
        frame_offset = float(offset_raw)
    except ValueError:
        frame_offset = 0.0

    return [
        (frame_offset + (curriculum_max_frames / 3.0), "easy->medium"),
        (frame_offset + ((2.0 * curriculum_max_frames) / 3.0), "medium->hard"),
    ]


def _discover_progress_files(maze_runs_root: Path) -> list[Path]:
    candidates = sorted(maze_runs_root.glob("live_progress*.csvl"))
    if candidates:
        return candidates

    legacy_file = maze_runs_root / "live_progress.csvl"
    if legacy_file.exists():
        return [legacy_file]
    return []


def _merge_progress_payloads(
    payloads: list[
        tuple[
            Path,
            dict[str, dict[str, dict[str, dict[int, tuple[float, float, float]]]]],
            dict[str, dict[str, dict[str, dict[str, dict[int, float]]]]],
            dict[str, str],
        ]
    ]
) -> tuple[
    dict[str, dict[str, dict[str, dict[int, tuple[float, float, float]]]]],
    dict[str, dict[str, dict[str, dict[str, dict[int, float]]]]],
    dict[str, str],
]:
    merged_core: dict[str, dict[str, dict[str, dict[int, tuple[float, float, float]]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(dict))
    )
    merged_terms: dict[str, dict[str, dict[str, dict[str, dict[int, float]]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    )
    merged_meta: dict[str, str] = {}

    for file_path, core_data, term_data, meta in payloads:
        source_name = file_path.stem
        source_machine_id = (meta.get("machine_id") or "").strip().lower() or source_name.lower()

        for key, value in meta.items():
            if key == "reward_terms":
                existing = {
                    item.strip().lower()
                    for item in (merged_meta.get("reward_terms") or "").split("|")
                    if item.strip()
                }
                incoming = {item.strip().lower() for item in value.split("|") if item.strip()}
                merged_terms_meta = sorted(existing | incoming)
                merged_meta["reward_terms"] = "|".join(merged_terms_meta)
            elif key not in merged_meta:
                merged_meta[key] = value

        for algorithm, by_device in core_data.items():
            for device_key, by_run in by_device.items():
                for run_id, step_map in by_run.items():
                    merged_run_id = f"{source_machine_id}:{run_id}"
                    merged_core[algorithm][device_key][merged_run_id].update(step_map)

        for algorithm, by_device in term_data.items():
            for device_key, by_run in by_device.items():
                for run_id, by_term in by_run.items():
                    merged_run_id = f"{source_machine_id}:{run_id}"
                    for term_name, step_map in by_term.items():
                        merged_terms[algorithm][device_key][merged_run_id][term_name].update(step_map)

    return merged_core, merged_terms, merged_meta


def _parse_progress_file(
    progress_file: Path,
) -> tuple[
    dict[str, dict[str, dict[str, dict[int, tuple[float, float, float]]]]],
    dict[str, dict[str, dict[str, dict[str, dict[int, float]]]]],
    dict[str, str],
]:
    # Returns:
    # core_data: algorithm -> device_label -> run_id -> step -> (frame, capture_pct, reward)
    # term_data: algorithm -> device_label -> run_id -> term_name -> step -> value
    core_data: dict[str, dict[str, dict[str, dict[int, tuple[float, float, float]]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(dict))
    )
    term_data: dict[str, dict[str, dict[str, dict[str, dict[int, float]]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    )
    meta: dict[str, str] = {}

    if not progress_file.exists():
        return core_data, term_data, meta

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
            reward_terms = _parse_reward_terms_from_meta(meta)
            if len(parts) < 5:
                continue

            if len(parts) >= 6:
                algorithm_token, run_id, step_s, frame_s, capture_s, reward_s = parts[:6]
                extra_term_values = parts[6:]
            else:
                # Backward compatibility with old progress files that only carried one metric.
                algorithm_token, run_id, step_s, frame_s, capture_s = parts
                reward_s = "nan"
                extra_term_values = []
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
                token_parts = [part.strip().lower() for part in algorithm_token.split("@") if part.strip()]
                algorithm = token_parts[0] if token_parts else ""
                if len(token_parts) >= 3:
                    # New format: algorithm@reward_id@device_label
                    label = f"{token_parts[1]}@{token_parts[-1]}"
                elif len(token_parts) == 2:
                    # Legacy format: algorithm@device_label
                    label = token_parts[1]
                else:
                    label = "default"
            else:
                algorithm = algorithm_token
                label = "default"

            algorithm = algorithm.strip().lower()
            if not algorithm:
                continue

            core_data[algorithm][label][run_id][step] = (frame, capture_pct, reward)

            for idx, term_name in enumerate(reward_terms):
                if idx >= len(extra_term_values):
                    value = float("nan")
                else:
                    try:
                        value = float(extra_term_values[idx])
                    except ValueError:
                        value = float("nan")
                term_data[algorithm][label][run_id][term_name][step] = value

    return core_data, term_data, meta


def _resolve_epsilon_from_cli_or_meta(
    args: argparse.Namespace,
    meta: dict[str, str],
) -> dict[str, float | int | str] | None:
    resolved: dict[str, float | int | str] = {}
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

    schedule_from_meta = _epsilon_schedule_from_meta(meta)
    if schedule_from_meta is None:
        schedule_from_meta = {
            "epsilon_schedule_mode": "global",
            "max_frames": epsilon_max_frames,
            "epsilon_init": epsilon_init,
            "epsilon_end": epsilon_end,
            "epsilon_anneal_ratio": epsilon_anneal_ratio,
            "epsilon_anneal_frames": int(epsilon_max_frames * epsilon_anneal_ratio),
        }

    if any_cli_override:
        # Preserve CLI overrides for global curve semantics.
        return {
            "epsilon_schedule_mode": "global",
            "max_frames": epsilon_max_frames,
            "epsilon_init": epsilon_init,
            "epsilon_end": epsilon_end,
            "epsilon_anneal_ratio": epsilon_anneal_ratio,
            "epsilon_anneal_frames": int(epsilon_max_frames * epsilon_anneal_ratio),
        }
    return schedule_from_meta


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


def _aggregate_term_runs(
    run_terms: dict[str, dict[int, float]],
    window: int,
) -> tuple[np.ndarray, np.ndarray] | None:
    if not run_terms:
        return None

    max_step = max((max(step_map.keys()) for step_map in run_terms.values() if step_map), default=0)
    if max_step <= 0:
        return None

    n_runs = len(run_terms)
    values_mat = np.full((n_runs, max_step), np.nan, dtype=np.float64)
    for run_idx, step_map in enumerate(run_terms.values()):
        for step, value in step_map.items():
            if 1 <= step <= max_step:
                values_mat[run_idx, step - 1] = value

    mean_values = np.nanmean(values_mat, axis=0)
    std_values = np.nanstd(values_mat, axis=0)
    mean_values = _moving_average(mean_values, window)
    std_values = _moving_average(std_values, window)
    return mean_values, std_values


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
        show_individual_reward_terms: bool,
        reward_terms_filter: set[str] | None,
        reward_ids_filter: set[str] | None,
    ) -> None:
        self.algorithms = algorithms
        self.window = window
        self.device_selector = device_selector
        self.epsilon_max_frames = max(1, int(epsilon_max_frames))
        self.epsilon_init = float(epsilon_init)
        self.epsilon_end = float(epsilon_end)
        self.epsilon_anneal_ratio = float(epsilon_anneal_ratio)
        self.show_epsilon_overlay = bool(show_epsilon_overlay)
        self.show_individual_reward_terms = bool(show_individual_reward_terms)
        self.reward_terms_filter = reward_terms_filter
        self.reward_ids_filter = reward_ids_filter

        self.fig, self.ax = plt.subplots(1, 1, figsize=(10, 5))
        self.ax_reward = self.ax.twinx()
        self.ax_eps = self.ax.twinx()
        self.ax_terminal = self.ax.twinx()
        self.ax_terminal.spines["right"].set_position(("outward", 55))
        self.ax_eps.spines["right"].set_position(("outward", 110))
        self.lines_capture: dict[str, any] = {}
        self.lines_reward: dict[str, any] = {}
        self.lines_reward_terms: dict[str, any] = {}
        self.lines_terminal_terms: dict[str, any] = {}
        self.fills_capture: dict[str, any] = {}
        self.marker_scatter_capture: dict[str, any] = {}
        self.epsilon_line = None
        self.epsilon_schedule: dict[str, float | int | str] = {
            "epsilon_schedule_mode": "global",
            "max_frames": self.epsilon_max_frames,
            "epsilon_init": self.epsilon_init,
            "epsilon_end": self.epsilon_end,
            "epsilon_anneal_ratio": self.epsilon_anneal_ratio,
            "epsilon_anneal_frames": int(self.epsilon_max_frames * self.epsilon_anneal_ratio),
        }
        self.curriculum_lines: list[any] = []
        self.curriculum_texts: list[any] = []

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
        self.reward_term_markers = ["o", "s", "^", "v", "D", "P", "X", "*", "<", ">", "h", "8"]
        self.reward_term_linestyles = ["--", "-.", ":", (0, (3, 1, 1, 1)), (0, (5, 2)), (0, (1, 1))]

        self._init_plot()

    def _init_plot(self) -> None:
        self.ax.set_title("Live Benchmark Comparison (True Capture Snapshots)")
        self.ax.set_xlabel("Total frames")
        self.ax.set_ylabel("True Capture Rate (%)")
        # Keep a small negative margin so zero-valued capture lines/markers are visible above the axis frame.
        self.ax.set_ylim(-1.0, 100.0)
        self.ax.grid(True, alpha=0.3)
        reward_axis_label = (
            "Average and non-terminal rewards"
            if self.show_individual_reward_terms
            else "Average team reward per step"
        )
        self.ax_reward.set_ylabel(reward_axis_label, color="dimgray")
        self.ax_reward.tick_params(axis="y", colors="dimgray")
        self.ax_eps.set_ylabel("Epsilon", color="black")
        self.ax_eps.set_ylim(0.0, 1.05)
        self.ax_eps.tick_params(axis="y", colors="black")
        self.ax_terminal.set_ylabel("Terminal Reward", color="#8c564b")
        self.ax_terminal.tick_params(axis="y", colors="#8c564b")
        if not self.show_individual_reward_terms:
            self.ax_terminal.spines["right"].set_visible(False)
            self.ax_terminal.tick_params(axis="y", right=False, labelright=False)
            self.ax_terminal.set_ylabel("")
        plt.ion()
        plt.show(block=False)

    def _line_style_for_device(self, device_key: str) -> str:
        _reward_id, parsed_device = _split_reward_and_device(device_key)
        key = parsed_device
        if key.startswith("cuda"):
            return "-"
        if key.startswith("cpu"):
            return "--"
        return self.style_map.get(key, "-")

    def _reward_term_style(self, term_name: str) -> tuple[str, str]:
        stable_index = sum(ord(ch) for ch in term_name)
        marker = self.reward_term_markers[stable_index % len(self.reward_term_markers)]
        linestyle = self.reward_term_linestyles[stable_index % len(self.reward_term_linestyles)]
        return marker, linestyle

    def _epsilon_for_frames(self, frames: np.ndarray) -> np.ndarray:
        return _epsilon_for_frames_schedule(frames, self.epsilon_schedule)

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

    def _update_curriculum_markers(self, meta: dict[str, str], max_display_frame: float) -> None:
        for line in self.curriculum_lines:
            line.remove()
        self.curriculum_lines.clear()
        for text in self.curriculum_texts:
            text.remove()
        self.curriculum_texts.clear()

        if max_display_frame <= 0.0:
            return

        transitions = _curriculum_transition_frames_from_meta(meta)
        for frame, label in transitions:
            if frame < 0.0 or frame > max_display_frame:
                continue

            marker_line = self.ax.axvline(
                x=frame,
                color="#4d4d4d",
                linestyle="--",
                linewidth=1.2,
                alpha=0.8,
                zorder=2,
            )
            marker_text = self.ax.text(
                frame,
                99.0,
                label,
                rotation=90,
                va="top",
                ha="right",
                color="#4d4d4d",
                fontsize=8,
                alpha=0.9,
                zorder=2,
            )
            self.curriculum_lines.append(marker_line)
            self.curriculum_texts.append(marker_text)

    def set_epsilon_schedule(
        self,
        epsilon_schedule: dict[str, float | int | str],
    ) -> None:
        self.epsilon_schedule = dict(epsilon_schedule)
        self.epsilon_max_frames = max(1, int(self.epsilon_schedule.get("max_frames", 1) or 1))
        self.epsilon_init = float(self.epsilon_schedule.get("epsilon_init", 1.0))
        self.epsilon_end = float(self.epsilon_schedule.get("epsilon_end", 0.0))
        self.epsilon_anneal_ratio = float(self.epsilon_schedule.get("epsilon_anneal_ratio", 1.0))
        self.show_epsilon_overlay = True

    def update_from_payload(
        self,
        data: dict[str, dict[str, dict[str, dict[int, tuple[float, float, float]]]]],
        term_data: dict[str, dict[str, dict[str, dict[str, dict[int, float]]]]],
        meta: dict[str, str],
    ) -> None:

        metric_name = (meta.get("metric") or "").strip().lower()
        if metric_name == "capture_pct_live_eval":
            self.ax.set_ylabel("True Capture Rate (%)")
            self.ax.set_title("Live Benchmark Comparison (Rolling True Capture Rate)")
        elif metric_name:
            self.ax.set_ylabel("Estimated Capture Rate (%)")
            self.ax.set_title("Live Benchmark Comparison (Rolling Estimated Capture Rate)")
        else:
            self.ax.set_ylabel("Capture Rate (%)")
            self.ax.set_title("Live Benchmark Comparison (Rolling Capture Rate)")

        # Remove old fills so uncertainty bands can be redrawn cleanly.
        for fill in self.fills_capture.values():
            fill.remove()
        self.fills_capture.clear()

        for scatter in self.marker_scatter_capture.values():
            scatter.remove()
        self.marker_scatter_capture.clear()

        active_keys: set[str] = set()
        max_display_frame = 0.0
        reward_ids_by_algorithm: dict[str, list[str]] = {}
        for algorithm in self.algorithms:
            by_device = data.get(algorithm, {})
            reward_ids = {
                reward_id
                for device_key in by_device.keys()
                for reward_id, _parsed_device in [_split_reward_and_device(device_key)]
                if reward_id is not None
            }
            reward_ids_by_algorithm[algorithm] = sorted(reward_ids)

        for algorithm in self.algorithms:
            by_device = data.get(algorithm, {})
            if not by_device:
                continue

            if self.device_selector == "all":
                selected_labels = sorted(by_device.keys())
            else:
                selected_labels = [
                    key for key in sorted(by_device.keys()) if _device_matches_selector(key, self.device_selector)
                ]
            selected_labels = [
                key for key in selected_labels if _reward_matches_selector(key, self.reward_ids_filter)
            ]

            for device_key in selected_labels:
                run_steps = by_device.get(device_key, {})
                aggregated = _aggregate_algorithm_runs(run_steps, self.window)
                if aggregated is None:
                    continue

                frames, mean_captures, std_captures, mean_rewards, _std_rewards, n_runs = aggregated
                if frames.size:
                    max_display_frame = max(max_display_frame, float(np.nanmax(frames)))
                line_style = self._line_style_for_device(device_key)
                series_key = f"{algorithm}@{device_key}"
                active_keys.add(series_key)
                reward_id, parsed_device = _split_reward_and_device(device_key)
                legend_suffix = (
                    f"{reward_id}@{parsed_device}" if reward_id is not None else parsed_device
                )
                ordered_reward_ids = reward_ids_by_algorithm.get(algorithm, [])
                color = self.color_map.get(algorithm, "#1f77b4")
                if reward_id is not None:
                    color = _reward_variant_color(color, reward_id, ordered_reward_ids)
                legend_capture = f"{algorithm.upper()}@{legend_suffix} capture snapshot% (n={n_runs})"
                legend_reward = f"{algorithm.upper()}@{legend_suffix} reward"
                valid_mask = ~np.isnan(mean_captures)
                valid_frames = frames[valid_mask]
                valid_captures = mean_captures[valid_mask]
                valid_stds = std_captures[valid_mask]

                if series_key not in self.lines_capture:
                    (line,) = self.ax.plot(
                        valid_frames,
                        valid_captures,
                        color=color,
                        linestyle=line_style,
                        linewidth=2.6,
                        alpha=1.0,
                        zorder=6,
                        label=legend_capture,
                    )
                    self.lines_capture[series_key] = line
                else:
                    line = self.lines_capture[series_key]
                    line.set_data(valid_frames, valid_captures)
                    line.set_label(legend_capture)
                    line.set_linestyle(line_style)
                    line.set_linewidth(2.6)
                    line.set_alpha(1.0)
                    line.set_zorder(6)

                if np.any(valid_mask):
                    self.fills_capture[series_key] = self.ax.fill_between(
                        valid_frames,
                        np.maximum(valid_captures - valid_stds, 0.0),
                        np.minimum(valid_captures + valid_stds, 100.0),
                        color=color,
                        alpha=0.15,
                    )
                    self.marker_scatter_capture[series_key] = self.ax.scatter(
                        valid_frames,
                        valid_captures,
                        s=44,
                        marker="o",
                        color=color,
                        edgecolors="black",
                        linewidths=0.5,
                        alpha=1.0,
                        zorder=8,
                        clip_on=False,
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

                if self.show_individual_reward_terms:
                    by_term_for_device = term_data.get(algorithm, {}).get(device_key, {})
                    all_term_names: set[str] = set()
                    for run_term_map in by_term_for_device.values():
                        all_term_names.update(run_term_map.keys())

                    for term_name in sorted(all_term_names):
                        if self.reward_terms_filter is not None and term_name not in self.reward_terms_filter:
                            continue

                        term_run_series: dict[str, dict[int, float]] = {}
                        for run_id, run_term_map in by_term_for_device.items():
                            step_map = run_term_map.get(term_name)
                            if step_map:
                                term_run_series[run_id] = step_map

                        aggregated_term = _aggregate_term_runs(term_run_series, self.window)
                        term_series_key = f"{series_key}::reward::{term_name}"
                        if aggregated_term is None:
                            stale = self.lines_reward_terms.pop(term_series_key, None)
                            if stale is not None:
                                stale.remove()
                            continue

                        term_mean, _term_std = aggregated_term
                        term_frames = frames[: len(term_mean)]
                        if np.all(np.isnan(term_mean)):
                            stale = self.lines_reward_terms.pop(term_series_key, None)
                            if stale is not None:
                                stale.remove()
                            stale_terminal = self.lines_terminal_terms.pop(term_series_key, None)
                            if stale_terminal is not None:
                                stale_terminal.remove()
                            continue

                        legend_term = f"{algorithm.upper()}@{legend_suffix} reward::{term_name}"
                        marker, term_linestyle = self._reward_term_style(term_name)
                        is_terminal_term = _is_terminal_reward_term(term_name)
                        target_lines = self.lines_terminal_terms if is_terminal_term else self.lines_reward_terms
                        other_lines = self.lines_reward_terms if is_terminal_term else self.lines_terminal_terms
                        stale_other = other_lines.pop(term_series_key, None)
                        if stale_other is not None:
                            stale_other.remove()

                        target_axis = self.ax_terminal if is_terminal_term else self.ax_reward
                        if term_series_key not in target_lines:
                            (term_line,) = target_axis.plot(
                                term_frames,
                                term_mean,
                                color=color,
                                linestyle=term_linestyle,
                                linewidth=1.2,
                                alpha=0.8,
                                marker=marker,
                                markersize=4,
                                markevery=max(1, len(term_frames) // 20),
                                label=legend_term,
                            )
                            target_lines[term_series_key] = term_line
                        else:
                            term_line = target_lines[term_series_key]
                            term_line.set_data(term_frames, term_mean)
                            term_line.set_label(legend_term)
                            term_line.set_linestyle(term_linestyle)
                            term_line.set_marker(marker)
                            term_line.set_markevery(max(1, len(term_frames) // 20))

        stale_keys = [key for key in self.lines_capture.keys() if key not in active_keys]
        for key in stale_keys:
            line = self.lines_capture.pop(key)
            line.remove()
            fill = self.fills_capture.pop(key, None)
            if fill is not None:
                fill.remove()
            marker_scatter = self.marker_scatter_capture.pop(key, None)
            if marker_scatter is not None:
                marker_scatter.remove()
            reward_line = self.lines_reward.pop(key, None)
            if reward_line is not None:
                reward_line.remove()

        stale_term_keys = [
            key for key in self.lines_reward_terms.keys() if key.split("::reward::", 1)[0] not in active_keys
        ]
        for key in stale_term_keys:
            term_line = self.lines_reward_terms.pop(key)
            term_line.remove()

        stale_terminal_term_keys = [
            key for key in self.lines_terminal_terms.keys() if key.split("::reward::", 1)[0] not in active_keys
        ]
        for key in stale_terminal_term_keys:
            term_line = self.lines_terminal_terms.pop(key)
            term_line.remove()

        # Keep legend current with active algorithms.
        show_epsilon = "iql" in self.algorithms and self.show_epsilon_overlay
        self._update_epsilon_curve(max_display_frame, show=show_epsilon)
        self._update_curriculum_markers(meta, max_display_frame)

        handles, labels = self.ax.get_legend_handles_labels()
        reward_handles, reward_labels = self.ax_reward.get_legend_handles_labels()
        handles += reward_handles
        labels += reward_labels
        terminal_handles, terminal_labels = self.ax_terminal.get_legend_handles_labels()
        handles += terminal_handles
        labels += terminal_labels
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
        self.ax_terminal.relim()
        self.ax_terminal.autoscale_view()
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    def close(self) -> None:
        plt.close(self.fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Monitor benchmark live progress with true capture snapshots and reward trends."
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
        "--reward-ids",
        type=str,
        default="all",
        help=(
            "Comma-separated reward ids to display (for example: current,capture_v0). "
            "Use 'all' to show all reward ids present in progress data."
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
    parser.add_argument(
        "--reward-terms",
        type=str,
        default="all",
        help="Comma-separated reward terms to display (default: all).",
    )
    parser.add_argument(
        "--individual-reward-plotting",
        action="store_true",
        help="Enable plotting individual reward terms (disabled by default).",
    )
    return parser.parse_args()


def _normalize_device_selector(raw: str) -> str:
    value = raw.strip().lower()
    if value == "all":
        return value
    if not value:
        raise ValueError("Device selector cannot be empty.")
    return device_label(value)


def _normalize_reward_ids_selector(raw: str) -> set[str] | None:
    value = str(raw).strip().lower()
    if value in {"", "all", "*"}:
        return None
    reward_ids = {item.strip().lower() for item in value.split(",") if item.strip()}
    if not reward_ids:
        raise ValueError("Reward id selector cannot be empty.")
    return reward_ids


def main() -> None:
    args = parse_args()
    maze_runs_root = runs_root_for_maze(args.runs_root, args.maze)
    progress_files = [args.progress_file] if args.progress_file is not None else _discover_progress_files(maze_runs_root)
    if not progress_files:
        expected_pattern = maze_runs_root / "live_progress*.csvl"
        raise FileNotFoundError(f"No live progress files found for pattern: {expected_pattern}")
    algorithms = [normalize_algorithm(item) for item in args.algorithms.split(",") if item.strip()]
    if not algorithms:
        raise ValueError("At least one algorithm must be provided.")
    invalid = [name for name in algorithms if name not in SUPPORTED_ALGORITHMS]
    if invalid:
        raise ValueError(f"Unsupported algorithm(s): {invalid}. Allowed: {list(SUPPORTED_ALGORITHMS)}")
    device_selector = _normalize_device_selector(args.device)
    reward_ids_filter = _normalize_reward_ids_selector(args.reward_ids)

    if args.window < 1:
        raise ValueError("--window must be >= 1")

    reward_terms_filter: set[str] | None
    if args.individual_reward_plotting:
        if args.reward_terms.strip().lower() == "all":
            reward_terms_filter = None
        else:
            reward_terms_filter = {
                item.strip().lower() for item in args.reward_terms.split(",") if item.strip()
            }
            if not reward_terms_filter:
                raise ValueError("--reward-terms must be 'all' or a non-empty comma-separated list.")
    else:
        reward_terms_filter = set()

    show_epsilon = "iql" in algorithms
    waiting_for_meta = False
    init_payloads = [
        (path, *_parse_progress_file(path))
        for path in progress_files
    ]
    init_core_data, init_term_data, init_meta = _merge_progress_payloads(init_payloads)
    if show_epsilon:
        epsilon_cfg = _resolve_epsilon_from_cli_or_meta(
            args,
            init_meta,
        )
        if epsilon_cfg is None:
            waiting_for_meta = True
            epsilon_schedule = {
                "epsilon_schedule_mode": "global",
                "max_frames": 1,
                "epsilon_init": 1.0,
                "epsilon_end": 0.0,
                "epsilon_anneal_ratio": 1.0,
                "epsilon_anneal_frames": 1,
            }
        else:
            epsilon_schedule = epsilon_cfg
    else:
        epsilon_schedule = {
            "epsilon_schedule_mode": "global",
            "max_frames": 1,
            "epsilon_init": 1.0,
            "epsilon_end": 0.0,
            "epsilon_anneal_ratio": 1.0,
            "epsilon_anneal_frames": 1,
        }

    print("[LivePlot] Watching progress files:")
    for progress_file in progress_files:
        print(f"- {progress_file}")
    print(f"[LivePlot] Algorithms: {', '.join(algorithms)}")
    print(f"[LivePlot] Device selector: {device_selector}")
    if reward_ids_filter is None:
        print("[LivePlot] Reward-id selector: all")
    else:
        print(f"[LivePlot] Reward-id selector: {', '.join(sorted(reward_ids_filter))}")
    epsilon_max_frames = int(epsilon_schedule.get("max_frames", 1) or 1)
    epsilon_init = float(epsilon_schedule.get("epsilon_init", 1.0))
    epsilon_end = float(epsilon_schedule.get("epsilon_end", 0.0))
    epsilon_anneal_ratio = float(epsilon_schedule.get("epsilon_anneal_ratio", 1.0))
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
        show_individual_reward_terms=args.individual_reward_plotting,
        reward_terms_filter=reward_terms_filter,
        reward_ids_filter=reward_ids_filter,
    )
    plotter.epsilon_schedule = dict(epsilon_schedule)
    try:
        while True:
            if show_epsilon and not plotter.show_epsilon_overlay:
                loop_payloads = [
                    (path, *_parse_progress_file(path))
                    for path in progress_files
                ]
                _loop_core_data, _loop_term_data, loop_meta = _merge_progress_payloads(loop_payloads)
                loop_epsilon_cfg = _resolve_epsilon_from_cli_or_meta(args, loop_meta)
                if loop_epsilon_cfg is not None:
                    plotter.set_epsilon_schedule(epsilon_schedule=loop_epsilon_cfg)
                    loop_max_frames = int(loop_epsilon_cfg.get("max_frames", 1) or 1)
                    loop_init = float(loop_epsilon_cfg.get("epsilon_init", 1.0))
                    loop_end = float(loop_epsilon_cfg.get("epsilon_end", 0.0))
                    loop_ratio = float(loop_epsilon_cfg.get("epsilon_anneal_ratio", 1.0))
                    print(
                        "[LivePlot] Epsilon overlay enabled from progress metadata: "
                        f"init={loop_init} end={loop_end} anneal_ratio={loop_ratio} "
                        f"max_frames={loop_max_frames}"
                    )
            payloads = [
                (path, *_parse_progress_file(path))
                for path in progress_files
            ]
            merged_core_data, merged_term_data, merged_meta = _merge_progress_payloads(payloads)
            plotter.update_from_payload(merged_core_data, merged_term_data, merged_meta)
            time.sleep(max(0.2, args.interval))
    except KeyboardInterrupt:
        print("\n[LivePlot] Exiting on user interrupt.")
        plotter.close()


if __name__ == "__main__":
    main()
