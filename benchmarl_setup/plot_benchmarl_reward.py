import argparse
import colorsys
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


# Fixed output resolution for benchmark plots: 1280x720 (720p).
_FIGURE_DPI = 100
_FIGURE_SIZE_INCHES_720P = (12.8, 7.2)


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


def _aggregate_algorithm_runs(
    run_steps: dict[str, dict[int, tuple[float, float, float]]],
    window: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, int] | None:
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

    invalid_frames = np.isnan(mean_frames)
    if np.any(invalid_frames):
        step_axis = np.arange(1, max_step + 1, dtype=np.float64)
        mean_frames[invalid_frames] = step_axis[invalid_frames]

    mean_captures = _moving_average(mean_captures, window)
    std_captures = _moving_average(std_captures, window)
    mean_rewards = _moving_average(mean_rewards, window)
    std_rewards = _moving_average(std_rewards, window)

    return mean_frames, mean_captures, std_captures, mean_rewards, std_rewards, captures_mat, n_runs


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
) -> tuple[
    dict[str, dict[str, dict[str, dict[int, tuple[float, float, float]]]]],
    dict[str, dict[str, dict[str, dict[str, dict[int, float]]]]],
]:
    # algorithm -> device_label -> run_id -> step -> (frame, capture_pct, reward)
    data: dict[str, dict[str, dict[str, dict[int, tuple[float, float, float]]]]] = {}
    term_data: dict[str, dict[str, dict[str, dict[str, dict[int, float]]]]] = {}
    if not progress_file.exists():
        return data, term_data

    meta = _parse_progress_meta(progress_file)
    reward_terms = [term.strip() for term in (meta.get("reward_terms") or "").split("|") if term.strip()]

    with progress_file.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split(",")
            if len(parts) < 5:
                continue

            if len(parts) >= 6:
                algorithm_token, run_id, step_s, frame_s, capture_s, reward_s = parts[:6]
                extra_term_values = parts[6:]
            else:
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
                    device_label_key = f"{token_parts[1]}@{token_parts[-1]}"
                elif len(token_parts) == 2:
                    # Legacy format: algorithm@device_label
                    device_label_key = token_parts[1]
                else:
                    device_label_key = "default"
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

            algo_term_data = term_data.setdefault(algorithm, {})
            device_term_data = algo_term_data.setdefault(device_label_key, {})
            run_term_data = device_term_data.setdefault(run_id, {})
            for idx, term_name in enumerate(reward_terms):
                term_step_map = run_term_data.setdefault(term_name, {})
                if idx < len(extra_term_values):
                    try:
                        term_value = float(extra_term_values[idx])
                    except ValueError:
                        term_value = float("nan")
                else:
                    term_value = float("nan")
                term_step_map[step] = term_value

    return data, term_data


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


def _reward_term_style(term_name: str) -> tuple[str, str]:
    markers = ["o", "s", "^", "v", "D", "P", "X", "*", "<", ">", "h", "8"]
    linestyles = ["--", "-.", ":", (0, (3, 1, 1, 1)), (0, (5, 2)), (0, (1, 1))]
    stable_index = sum(ord(ch) for ch in term_name)
    return markers[stable_index % len(markers)], linestyles[stable_index % len(linestyles)]


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
    if selector == "auto":
        return True
    _reward_id, parsed_device = _split_reward_and_device(label)
    return parsed_device == selector


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
    merged_core: dict[str, dict[str, dict[str, dict[int, tuple[float, float, float]]]]] = {}
    merged_terms: dict[str, dict[str, dict[str, dict[str, dict[int, float]]]]] = {}
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
                merged_meta["reward_terms"] = "|".join(sorted(existing | incoming))
            elif key not in merged_meta:
                merged_meta[key] = value

        for algorithm, by_device in core_data.items():
            algo_data = merged_core.setdefault(algorithm, {})
            for device_key, by_run in by_device.items():
                device_data = algo_data.setdefault(device_key, {})
                for run_id, step_map in by_run.items():
                    merged_run_id = f"{source_machine_id}:{run_id}"
                    run_data = device_data.setdefault(merged_run_id, {})
                    run_data.update(step_map)

        for algorithm, by_device in term_data.items():
            algo_term_data = merged_terms.setdefault(algorithm, {})
            for device_key, by_run in by_device.items():
                device_term_data = algo_term_data.setdefault(device_key, {})
                for run_id, by_term in by_run.items():
                    merged_run_id = f"{source_machine_id}:{run_id}"
                    run_term_data = device_term_data.setdefault(merged_run_id, {})
                    for term_name, step_map in by_term.items():
                        term_step_map = run_term_data.setdefault(term_name, {})
                        term_step_map.update(step_map)

    return merged_core, merged_terms, merged_meta


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
    progress_files = [args.progress_file] if args.progress_file is not None else _discover_progress_files(maze_runs_root)
    if not progress_files:
        expected_pattern = maze_runs_root / "live_progress*.csvl"
        raise FileNotFoundError(f"No live progress files found for pattern: {expected_pattern}")

    payloads = [
        (path, *_parse_progress_data(path), _parse_progress_meta(path))
        for path in progress_files
    ]
    progress_data, progress_term_data, progress_meta = _merge_progress_payloads(payloads)

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

    epsilon_algorithm_raw = progress_meta.get("epsilon_algorithm", "")
    epsilon_algorithm = (
        normalize_algorithm(epsilon_algorithm_raw)
        if epsilon_algorithm_raw.strip()
        else ""
    )
    has_cli_epsilon_override = any(
        value is not None
        for value in (
            args.epsilon_max_frames,
            args.epsilon_init,
            args.epsilon_end,
            args.epsilon_anneal_ratio,
        )
    )
    show_epsilon = (
        (epsilon_algorithm in algorithms)
        or (not epsilon_algorithm and "iql" in algorithms)
        or has_cli_epsilon_override
    )
    if show_epsilon:
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
                f"Warning: no progress data found for algorithm={algorithm} in merged progress files."
            )
            continue

        if requested_device == "auto":
            selected_devices = sorted(by_device.keys())
        else:
            selected_devices = [
                key
                for key in sorted(by_device.keys())
                if _device_matches_selector(key, requested_device)
            ]

        if not selected_devices:
            print(
                f"Warning: no progress data found for algorithm={algorithm} "
                f"and requested device selector={requested_device}."
            )
            continue

        run_steps: dict[str, dict[int, tuple[float, float, float]]] = {}
        run_terms: dict[str, dict[str, dict[int, float]]] = {}
        used_run_dirs: list[str] = []
        reward_ids = {
            reward_id
            for device_key in selected_devices
            for reward_id, _parsed_device in [_split_reward_and_device(device_key)]
            if reward_id is not None
        }
        ordered_reward_ids = sorted(reward_ids)

        for device_key in selected_devices:
            for run_id, step_map in by_device.get(device_key, {}).items():
                if selected_run_names is not None and run_id not in selected_run_names:
                    continue

                run_key = f"{device_key}:{run_id}"
                run_steps[run_key] = step_map
                run_terms[run_key] = progress_term_data.get(algorithm, {}).get(device_key, {}).get(run_id, {})
                used_run_dirs.append(f"{algorithm}@{device_key}:{run_id}")

        aggregated = _aggregate_algorithm_runs(run_steps, args.window)
        if aggregated is None:
            print(
                "Warning: no true capture snapshots found for algorithm="
                f"{algorithm} in merged progress files."
            )
            continue

        frames, capture_mean, capture_std, reward_mean, reward_std, captures_mat, n_runs = aggregated

        series_label = algorithm.upper()
        color = color_map.get(algorithm, "#1f77b4")
        if len(ordered_reward_ids) == 1:
            reward_id = ordered_reward_ids[0]
            color = _reward_variant_color(color, reward_id, ordered_reward_ids)
            series_label = f"{algorithm.upper()}@{reward_id}"

        per_algorithm[algorithm] = {
            "frames": frames,
            "capture_mean": capture_mean,
            "capture_std": capture_std,
            "captures_mat": captures_mat,
            "reward_mean": reward_mean,
            "reward_std": reward_std,
            "run_terms": run_terms,
            "n_runs": n_runs,
            "used_run_dirs": used_run_dirs,
            "color": color,
            "series_label": series_label,
        }

    if not per_algorithm:
        raise FileNotFoundError(
            "No usable runs were found for selected algorithms."
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(
        1,
        1,
        figsize=_FIGURE_SIZE_INCHES_720P,
        dpi=_FIGURE_DPI,
    )
    ax_reward = ax.twinx()
    ax_eps = ax.twinx()
    ax_terminal = ax.twinx()
    ax_terminal.spines["right"].set_position(("outward", 55))
    ax_eps.spines["right"].set_position(("outward", 110))

    for algorithm, payload in per_algorithm.items():
        frames = payload["frames"]
        capture_mean = payload["capture_mean"]
        capture_std = payload["capture_std"]
        captures_mat = payload["captures_mat"]
        reward_mean = payload["reward_mean"]
        run_terms = payload["run_terms"]
        color = payload["color"]
        series_label = payload.get("series_label", algorithm.upper())

        valid_capture_mask = ~np.isnan(capture_mean)
        valid_frames = frames[valid_capture_mask]
        valid_captures = capture_mean[valid_capture_mask]
        valid_stds = capture_std[valid_capture_mask]

        if args.show_runs:
            for capture_series in captures_mat:
                ax.plot(frames, capture_series, color=color, linewidth=1, alpha=0.18)

        ax.plot(
            valid_frames,
            valid_captures,
            label=f"{series_label} mean capture % (n={payload['n_runs']})",
            color=color,
            linewidth=2,
        )
        if np.any(valid_capture_mask):
            ax.fill_between(
                valid_frames,
                np.maximum(valid_captures - valid_stds, 0.0),
                np.minimum(valid_captures + valid_stds, 100.0),
                color=color,
                alpha=0.14,
            )

        if not np.all(np.isnan(reward_mean)):
            ax_reward.plot(
                frames,
                reward_mean,
                label=f"{series_label} mean reward",
                color=color,
                linewidth=1.8,
                linestyle=":",
            )

        if args.individual_reward_plotting:
            all_term_names: set[str] = set()
            for run_term_map in run_terms.values():
                all_term_names.update(run_term_map.keys())

            for term_name in sorted(all_term_names):
                if reward_terms_filter is not None and term_name not in reward_terms_filter:
                    continue

                term_run_series: dict[str, dict[int, float]] = {}
                for run_key, run_term_map in run_terms.items():
                    step_map = run_term_map.get(term_name)
                    if step_map:
                        term_run_series[run_key] = step_map

                aggregated_term = _aggregate_term_runs(term_run_series, args.window)
                if aggregated_term is None:
                    continue

                term_mean, _term_std = aggregated_term
                term_frames = frames[: len(term_mean)]
                if np.all(np.isnan(term_mean)):
                    continue

                marker, term_linestyle = _reward_term_style(term_name)

                target_axis = ax_terminal if _is_terminal_reward_term(term_name) else ax_reward
                target_axis.plot(
                    term_frames,
                    term_mean,
                    label=f"{series_label} reward::{term_name}",
                    color=color,
                    linewidth=1.1,
                    linestyle=term_linestyle,
                    alpha=0.8,
                    marker=marker,
                    markersize=4,
                    markevery=max(1, len(term_frames) // 20),
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
    for frame, label in _curriculum_transition_frames_from_meta(progress_meta):
        if frame < 0.0 or frame > max_display_frame:
            continue
        ax.axvline(
            x=frame,
            color="#4d4d4d",
            linestyle="--",
            linewidth=1.2,
            alpha=0.8,
            zorder=2,
        )
        ax.text(
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
    reward_axis_label = (
        "Average and non-terminal rewards"
        if args.individual_reward_plotting
        else "Average team reward per step"
    )
    ax_reward.set_ylabel(reward_axis_label, color="dimgray")
    ax_reward.tick_params(axis="y", colors="dimgray")
    ax_terminal.set_ylabel("Terminal Reward", color="#8c564b")
    ax_terminal.tick_params(axis="y", colors="#8c564b")
    if not args.individual_reward_plotting:
        ax_terminal.spines["right"].set_visible(False)
        ax_terminal.tick_params(axis="y", right=False, labelright=False)
        ax_terminal.set_ylabel("")
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
    terminal_handles, terminal_labels = ax_terminal.get_legend_handles_labels()
    handles += terminal_handles
    labels += terminal_labels
    eps_handles, eps_labels = ax_eps.get_legend_handles_labels()
    handles += eps_handles
    labels += eps_labels
    ax.legend(handles, labels)

    fig.tight_layout()
    fig.savefig(args.out, dpi=_FIGURE_DPI)

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
