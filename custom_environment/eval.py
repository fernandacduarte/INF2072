import argparse
import csv
import json
import math
import time
import warnings
from pathlib import Path
import sys
from collections import Counter

import numpy as np
import torch

from benchmarl.experiment import Experiment
from torchrl.envs.utils import ExplorationType, set_exploration_type, step_mdp

# Ensure workspace root is importable when running this file by path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from custom_environment.env.domain.constant import Observation
from benchmarl_setup.algorithm_utils import (
    SUPPORTED_ALGORITHMS,
    SUPPORTED_MAZES,
    candidate_run_dirs,
    normalize_algorithm,
    runs_root_for_maze,
)
from benchmarl_setup.device_utils import device_label, resolve_device


SYMBOLS = {
    Observation.CAPUTRED.value: "X",
    Observation.EMPTY.value: " ",
    Observation.GHOST.value: "G",
    Observation.PAC_MAN.value: "P",
    Observation.WALL.value: "#",
}

# Environment action-space indices (0..3) map to Action enum order.
ACTION_NAME = {
    0: "RIGHT",
    1: "LEFT",
    2: "UP",
    3: "DOWN",
}


CHECKPOINT_BEST_METRICS = ("reward", "capture_rate")


def _configure_warning_filters() -> None:
    warnings.filterwarnings(
        "ignore",
        message=(
            r"^You are using `torch\.load` with `weights_only=False` "
            r"\(the current default value\), which uses the default pickle "
            r"module implicitly\."
        ),
        category=FutureWarning,
        module=r"^benchmarl\.experiment\.experiment$",
    )
    warnings.filterwarnings(
        "ignore",
        message=r"^PettingZoo in TorchRL is tested using version == 1\.24\.3",
        category=UserWarning,
        module=r"^torchrl\.envs\.libs\.pettingzoo$",
    )
    warnings.filterwarnings(
        "ignore",
        message=(
            r"^SyncDataCollector has been deprecated and will be removed in v0\.13\. "
            r"Please use Collector instead\.$"
        ),
        category=DeprecationWarning,
        module=r"^torchrl\.collectors\._base$",
    )


def render_ascii(grid) -> str:
    lines = []
    for row in grid:
        lines.append("".join(SYMBOLS.get(int(cell), "?") for cell in row))
    return "\n".join(lines)


def save_rgb_frame(frame: np.ndarray, output_path: Path) -> None:
    try:
        import pygame
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Pygame is required to save render screenshots. Install dependencies with "
            "`python -m pip install -r requirements.txt`."
        ) from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    surface = pygame.surfarray.make_surface(np.transpose(frame, (1, 0, 2)))
    pygame.image.save(surface, str(output_path))


def _read_scalar_values(csv_path: Path) -> list[float]:
    values = []
    with csv_path.open("r", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 2:
                continue
            values.append(float(row[1]))
    return values


def _scalars_dir_for_run(run_dir: Path) -> Path | None:
    nested = run_dir / run_dir.name / "scalars"
    if nested.exists():
        return nested
    direct = run_dir / "scalars"
    if direct.exists():
        return direct
    return None


def _latest_checkpoint_in_run(run_dir: Path) -> Path | None:
    checkpoints_dir = run_dir / "checkpoints"
    if not checkpoints_dir.exists():
        return None
    checkpoint_files = sorted(
        checkpoints_dir.glob("checkpoint_*.pt"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return checkpoint_files[0] if checkpoint_files else None


def _score_run_for_selection(run_dir: Path) -> tuple[float, float, float]:
    scalars_dir = _scalars_dir_for_run(run_dir)
    if scalars_dir is None:
        return (-float("inf"), -float("inf"), run_dir.stat().st_mtime)

    reward_file = scalars_dir / "collection_reward_reward_mean.csv"
    if not reward_file.exists():
        return (-float("inf"), -float("inf"), run_dir.stat().st_mtime)

    rewards = _read_scalar_values(reward_file)
    if not rewards:
        return (-float("inf"), -float("inf"), run_dir.stat().st_mtime)

    window = min(20, len(rewards))
    tail_mean = sum(rewards[-window:]) / float(window)
    best_single = max(rewards)
    recency = run_dir.stat().st_mtime
    return (tail_mean, best_single, recency)


def _capture_rate_for_run(run_dir: Path) -> float:
    return _capture_rate_for_run_checkpoint(run_dir, expected_checkpoint=None)


def _paths_equivalent(left: Path, right: Path) -> bool:
    left_resolved = str(left.resolve(strict=False)).replace("\\", "/").lower()
    right_resolved = str(right.resolve(strict=False)).replace("\\", "/").lower()
    return left_resolved == right_resolved


def _checkpoint_identity(path: Path) -> tuple[str, str]:
    run_dir_name = ""
    if len(path.parents) >= 2:
        run_dir_name = path.parents[1].name.strip().lower()
    return run_dir_name, path.name.strip().lower()


def _checkpoint_matches_expected(
    snapshot_checkpoint: Path,
    expected_checkpoint: Path,
) -> tuple[bool, str]:
    if _paths_equivalent(snapshot_checkpoint, expected_checkpoint):
        return True, "absolute"

    snapshot_run_name, snapshot_checkpoint_name = _checkpoint_identity(snapshot_checkpoint)
    expected_run_name, expected_checkpoint_name = _checkpoint_identity(expected_checkpoint)
    if (
        snapshot_run_name
        and expected_run_name
        and snapshot_run_name == expected_run_name
        and snapshot_checkpoint_name == expected_checkpoint_name
    ):
        return True, "identity"

    return False, "none"


def _capture_snapshot_for_run(run_dir: Path) -> dict[str, object] | None:
    report_path = run_dir / "evaluation_report_live_capture.csv"
    if not report_path.exists():
        return None

    try:
        with report_path.open("r", newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                raw_capture = (row.get("capture_rate") or "").strip()
                if not raw_capture:
                    continue
                capture_rate = float(raw_capture)
                if capture_rate != capture_rate:
                    continue

                raw_checkpoint = (row.get("checkpoint_path") or "").strip()
                checkpoint_path = Path(raw_checkpoint) if raw_checkpoint else None
                return {
                    "capture_rate": capture_rate,
                    "report_path": report_path,
                    "report_mtime": report_path.stat().st_mtime,
                    "checkpoint_path": checkpoint_path,
                }
    except (OSError, ValueError, csv.Error):
        return None
    return None


def _capture_rate_for_run_checkpoint(
    run_dir: Path,
    expected_checkpoint: Path | None,
) -> float:
    snapshot = _capture_snapshot_for_run(run_dir)
    if snapshot is None:
        return float("-inf")

    if expected_checkpoint is None:
        return float(snapshot["capture_rate"])

    snapshot_checkpoint = snapshot["checkpoint_path"]
    if not isinstance(snapshot_checkpoint, Path):
        return float("-inf")
    matches_checkpoint, _match_mode = _checkpoint_matches_expected(
        snapshot_checkpoint,
        expected_checkpoint,
    )
    if not matches_checkpoint:
        return float("-inf")
    return float(snapshot["capture_rate"])


def _extract_seed_from_run_dir(run_dir: Path) -> int | None:
    candidates = [
        run_dir / run_dir.name / "texts" / "hparams0.txt",
        run_dir / "texts" / "hparams0.txt",
    ]
    for hparams_path in candidates:
        if not hparams_path.exists():
            continue
        try:
            for raw_line in hparams_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = raw_line.strip()
                if not line.startswith("seed:"):
                    continue
                _, _, tail = line.partition(":")
                value = tail.strip()
                if not value:
                    return None
                return int(value)
        except (OSError, ValueError):
            return None
    return None


def _format_optional_float(value: float | None, digits: int = 4) -> str:
    if value is None:
        return "n/a"
    if value != value:
        return "n/a"
    return f"{value:.{digits}f}"


def _print_selected_seed_stats(checkpoint_path: Path, tail_window: int = 20) -> None:
    run_dir = checkpoint_path.parent.parent
    seed = _extract_seed_from_run_dir(run_dir)

    final_reward: float | None = None
    tail_mean_reward: float | None = None
    best_reward: float | None = None
    scalars_dir = _scalars_dir_for_run(run_dir)
    if scalars_dir is not None:
        reward_file = scalars_dir / "collection_reward_reward_mean.csv"
        if reward_file.exists():
            rewards = _read_scalar_values(reward_file)
            if rewards:
                final_reward = rewards[-1]
                window = min(tail_window, len(rewards))
                tail_mean_reward = sum(rewards[-window:]) / float(window)
                best_reward = max(rewards)

    capture_pct: float | None = None
    checkpoint_match = False
    checkpoint_match_mode = "none"
    snapshot = _capture_snapshot_for_run(run_dir)
    if snapshot is not None and isinstance(snapshot.get("checkpoint_path"), Path):
        checkpoint_match, checkpoint_match_mode = _checkpoint_matches_expected(
            snapshot["checkpoint_path"],
            checkpoint_path,
        )
        if checkpoint_match:
            capture_pct = 100.0 * float(snapshot["capture_rate"])

    print("Selected seed stats (human mode):")
    print(
        f"  run={run_dir.name} seed={seed if seed is not None else 'n/a'} checkpoint={checkpoint_path.name}"
    )
    print(
        "  training_reward="
        f"final={_format_optional_float(final_reward)} "
        f"tail{tail_window}={_format_optional_float(tail_mean_reward)} "
        f"best={_format_optional_float(best_reward)}"
    )
    print(
        "  capture_snapshot="
        f"matched={checkpoint_match} "
        f"match_mode={checkpoint_match_mode} "
        f"capture_pct={_format_optional_float(capture_pct, digits=2)}"
    )


def _candidate_run_dirs(learner: str, runs_root: Path) -> list[Path]:
    return candidate_run_dirs(runs_root, learner)


def _latest_checkpoint_for_learner(learner: str, runs_root: Path) -> Path:
    run_dirs = _candidate_run_dirs(learner, runs_root)
    if not run_dirs:
        raise FileNotFoundError(
            f"No run folders found for learner '{learner}' in {runs_root}."
        )

    run_dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    for run_dir in run_dirs:
        checkpoint = _latest_checkpoint_in_run(run_dir)
        if checkpoint is not None:
            return checkpoint

    raise FileNotFoundError(
        "No checkpoint files found. Run training with checkpoint saving enabled, for example:\n"
        f"py -3.11 benchmarl_setup\\run_pacman_benchmarl.py --algorithm {learner} --checkpoint-at-end"
    )


def _best_checkpoint_for_learner(
    learner: str,
    runs_root: Path,
    selection_metric: str = "reward",
) -> Path:
    if selection_metric not in CHECKPOINT_BEST_METRICS:
        raise ValueError(
            f"Unsupported best selection metric: {selection_metric}. "
            f"Allowed: {list(CHECKPOINT_BEST_METRICS)}"
        )

    run_dirs = _candidate_run_dirs(learner, runs_root)
    if not run_dirs:
        raise FileNotFoundError(
            f"No run folders found for learner '{learner}' in {runs_root}."
        )

    scored_runs = []
    capture_match_count = 0
    capture_identity_match_count = 0
    for run_dir in run_dirs:
        checkpoint = _latest_checkpoint_in_run(run_dir)
        if checkpoint is None:
            continue
        if selection_metric == "capture_rate":
            snapshot = _capture_snapshot_for_run(run_dir)
            snapshot_match_mode = "none"
            capture_rate = float("-inf")
            if snapshot is not None and isinstance(snapshot.get("checkpoint_path"), Path):
                matches_checkpoint, snapshot_match_mode = _checkpoint_matches_expected(
                    snapshot["checkpoint_path"],
                    checkpoint,
                )
                if matches_checkpoint:
                    capture_rate = float(snapshot["capture_rate"])
            has_checkpoint_match = capture_rate != -float("inf")
            if has_checkpoint_match:
                capture_match_count += 1
                if snapshot_match_mode == "identity":
                    capture_identity_match_count += 1
            score = (1.0 if has_checkpoint_match else 0.0, capture_rate, run_dir.stat().st_mtime)
        else:
            snapshot = None
            snapshot_match_mode = "none"
            score = _score_run_for_selection(run_dir)
        scored_runs.append((score, checkpoint, run_dir, snapshot, snapshot_match_mode))

    if not scored_runs:
        raise FileNotFoundError(
            "No checkpoint files found. Run training with checkpoint saving enabled, for example:\n"
            f"py -3.11 benchmarl_setup\\run_pacman_benchmarl.py --algorithm {learner} --checkpoint-at-end"
        )

    if selection_metric == "capture_rate" and capture_match_count == 0:
        raise FileNotFoundError(
            "No checkpoint-coupled capture metrics were found for capture-rate selection. "
            "Each run needs evaluation_report_live_capture.csv with checkpoint_path matching the "
            "latest checkpoint in that run (absolute path or run+checkpoint identity match). "
            "Recompute snapshots or use --checkpoint-best-metric reward."
        )

    scored_runs.sort(key=lambda item: item[0], reverse=True)
    best_score, best_checkpoint, best_run_dir, best_snapshot, best_snapshot_match_mode = scored_runs[0]
    if selection_metric == "capture_rate":
        capture_text = "nan" if best_score[1] == -float("inf") else f"{best_score[1]:.4f}"
        snapshot_checkpoint = (
            str(best_snapshot["checkpoint_path"]) if best_snapshot and best_snapshot.get("checkpoint_path") else ""
        )
        snapshot_path = str(best_snapshot["report_path"]) if best_snapshot else ""
        snapshot_mtime = (
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(best_snapshot["report_mtime"])))
            if best_snapshot and best_snapshot.get("report_mtime")
            else ""
        )
        checkpoint_match = (
            bool(best_snapshot)
            and isinstance(best_snapshot.get("checkpoint_path"), Path)
            and _checkpoint_matches_expected(best_snapshot["checkpoint_path"], best_checkpoint)[0]
        )
        print(
            "Best-run selection: "
            f"run={best_run_dir.name} metric=capture_rate capture_rate={capture_text} "
            f"matched_runs={capture_match_count}/{len(scored_runs)} "
            f"identity_matched_runs={capture_identity_match_count}/{capture_match_count} "
            f"checkpoint_match={checkpoint_match} "
            f"checkpoint_match_mode={best_snapshot_match_mode} "
            f"capture_source={snapshot_path} capture_source_mtime={snapshot_mtime} "
            f"capture_checkpoint={snapshot_checkpoint}"
        )
    else:
        print(
            "Best-run selection: "
            f"run={best_run_dir.name} metric=reward "
            f"tail_mean={best_score[0]:.4f} best_single={best_score[1]:.4f}"
        )
    return best_checkpoint


def _unwrap_pacman_env(env):
    current = env
    for _ in range(12):
        if hasattr(current, "_env"):
            return current._env
        if hasattr(current, "base_env"):
            current = current.base_env
            continue
        break
    return current


def _tensor_to_int_list(tensor: torch.Tensor) -> list[int]:
    flat = tensor.detach().cpu().reshape(-1)
    return [int(x) for x in flat.tolist()]


def _tensor_to_float_list(tensor: torch.Tensor) -> list[float]:
    flat = tensor.detach().cpu().reshape(-1)
    return [float(x) for x in flat.tolist()]


def _to_json_position(value) -> list[int] | None:
    if value is None:
        return None
    if isinstance(value, (tuple, list)) and len(value) == 2:
        return [int(value[0]), int(value[1])]
    return None


def _to_json_position_list(values) -> list[list[int]]:
    out: list[list[int]] = []
    for value in values or ():
        converted = _to_json_position(value)
        if converted is not None:
            out.append(converted)
    return out


def _to_json_float_map(values) -> dict[str, float]:
    if not values:
        return {}
    return {str(key): float(val) for key, val in values.items()}


def _to_json_reward_info(values: dict[str, float]) -> dict[str, float]:
    return {str(key): float(val) for key, val in values.items()}


def _to_json_int(value, default: int = 0) -> int:
    if value is None:
        return int(default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _build_ascii_step_diagnostics(
    raw_env,
    *,
    step: int,
    learner: str,
    done: bool,
    action_info: dict[str, str],
    reward_info: dict[str, float],
) -> dict:
    context = getattr(raw_env, "last_reward_context", None)
    reward_breakdown = _to_json_float_map(getattr(raw_env, "last_team_reward_breakdown", {}))
    reward_categories = _to_json_float_map(getattr(raw_env, "last_reward_category_totals", {}))

    if context is not None:
        pacman_position = _to_json_position(getattr(context, "pacman_position", None))
        pacman_previous_position = _to_json_position(getattr(context, "pacman_previous_position", None))
        pacman_visible = bool(getattr(context, "pacman_visible", False))
        visible_positions = _to_json_position_list(getattr(context, "visible_pacman_positions", ()))
        capture_happened = bool(getattr(context, "capture_happened", False))
        timeout_happened = bool(getattr(context, "timeout_happened", False))
        pacman_win_happened = bool(getattr(context, "pacman_win_happened", False))
        pellets_before = _to_json_int(getattr(context, "pellets_before", 0), default=0)
        pellets_remaining = _to_json_int(getattr(context, "pellets_remaining", 0), default=0)
        pellets_eaten_this_step = _to_json_int(getattr(context, "pellets_eaten_this_step", 0), default=0)
        context_step_count = _to_json_int(getattr(context, "step_count", step), default=step)
        context_max_steps = _to_json_int(
            getattr(context, "max_steps", getattr(raw_env, "max_steps", 0)),
            default=0,
        )
        ghost_transitions = tuple(getattr(context, "ghosts", ()))
    else:
        pacman_position = _to_json_position(getattr(getattr(raw_env, "pacman", None), "current_position", None))
        pacman_previous_position = _to_json_position(getattr(getattr(raw_env, "pacman", None), "prev_position", None))
        pacman_visible = False
        visible_positions = []
        capture_happened = bool(raw_env._is_capture_state())
        timeout_happened = bool(getattr(raw_env, "step_count", 0) >= getattr(raw_env, "max_steps", 0) and not capture_happened)
        pacman_win_happened = False
        pellets_before = 0
        pellets_remaining = 0
        pellets_eaten_this_step = 0
        context_step_count = _to_json_int(getattr(raw_env, "step_count", step), default=step)
        context_max_steps = _to_json_int(getattr(raw_env, "max_steps", 0), default=0)
        ghost_transitions = ()

    ghost_state: dict[str, dict[str, object]] = {}
    if ghost_transitions:
        for ghost in ghost_transitions:
            ghost_id = str(getattr(ghost, "ghost_id", "unknown"))
            ghost_state[ghost_id] = {
                "previous_position": _to_json_position(getattr(ghost, "previous_position", None)),
                "current_position": _to_json_position(getattr(ghost, "current_position", None)),
                "action": getattr(ghost, "action", None),
                "invalid_move": bool(getattr(ghost, "invalid_move", False)),
            }
    else:
        for ghost in getattr(raw_env, "ghosts", []):
            ghost_id = str(getattr(ghost, "id", "unknown"))
            ghost_state[ghost_id] = {
                "previous_position": _to_json_position(getattr(ghost, "prev_position", None)),
                "current_position": _to_json_position(getattr(ghost, "current_position", None)),
                "action": None,
                "invalid_move": bool(getattr(ghost, "invalid_move", False)),
            }

    return {
        "step": int(step),
        "learner": learner,
        "done": bool(done),
        "env_step_count": context_step_count,
        "env_max_steps": context_max_steps,
        "action_by_ghost": {str(key): str(value) for key, value in action_info.items()},
        "reward_by_ghost": _to_json_reward_info(reward_info),
        "pacman_position": pacman_position,
        "pacman_previous_position": pacman_previous_position,
        "pacman_visible": pacman_visible,
        "visible_pacman_positions": visible_positions,
        "last_pacman_sighting_position": _to_json_position(getattr(raw_env, "last_pacman_sighting_position", None)),
        "last_pacman_sighting_step": _to_json_int(
            getattr(raw_env, "last_pacman_sighting_step", -1),
            default=-1,
        ),
        "capture_happened": capture_happened,
        "timeout_happened": timeout_happened,
        "pacman_win_happened": pacman_win_happened,
        "pellets_before": pellets_before,
        "pellets_remaining": pellets_remaining,
        "pellets_eaten_this_step": pellets_eaten_this_step,
        "ghost_state": ghost_state,
        "reward_breakdown": reward_breakdown,
        "reward_categories": reward_categories,
    }


def classify_outcome(raw_env, step: int, max_steps: int) -> str:
    """Win-rate outcome label derived from the *same* predicates as
    ``_build_final_result``, so the headless harness and the renderer can never
    disagree about who won.

    Returns one of:
      - ``"ghosts"``  -> a ghost captured Pacman (the only ghost win),
      - ``"pacman"``  -> the env reached its own time limit with Pacman alive,
      - ``"timeout"`` -> the runner step cap was hit without an env-terminal.
    """
    if raw_env._is_capture_state():
        return "ghosts"
    if not raw_env.agents and raw_env.step_count >= raw_env.max_steps:
        return "pacman"
    return "timeout"


def _build_final_result(
    raw_env,
    *,
    step: int,
    run_max_steps: int,
    total_reward: float,
    elapsed_seconds: float,
) -> dict:
    outcome = classify_outcome(raw_env, step, run_max_steps)
    if outcome == "ghosts":
        title = "Ghosts win"
        reason = "Pacman was captured."
    elif outcome == "pacman":
        title = "Pacman wins"
        reason = "Pacman survived until the environment time limit."
    elif step >= run_max_steps:
        title = "Run stopped"
        reason = "The runner max-step limit was reached before the episode terminated."
    else:
        title = "Episode finished"
        reason = "The run ended without an active terminal condition."

    return {
        "title": title,
        "reason": reason,
        "steps": step,
        "max_steps": run_max_steps,
        "total_reward": total_reward,
        "elapsed_seconds": elapsed_seconds,
    }


def _set_global_ghost_view_size(view_size: int) -> None:
    from custom_environment.env import pacman_environment as pacman_env_module

    pacman_env_module.GHOST_VIEW_SIZE = int(view_size)


def _extract_view_size_from_hparams(checkpoint_path: Path) -> int | None:
    run_dir = checkpoint_path.parent.parent
    hparams_path = run_dir / run_dir.name / "texts" / "hparams0.txt"
    if not hparams_path.exists():
        return None

    content = hparams_path.read_text(encoding="utf-8", errors="ignore")
    marker = "'ghost_view_size':"
    idx = content.find(marker)
    if idx < 0:
        return None

    tail = content[idx + len(marker):]
    digits = []
    for ch in tail:
        if ch.isdigit():
            digits.append(ch)
            continue
        if digits:
            break
    if not digits:
        return None

    value = int("".join(digits))
    if value > 0 and value % 2 == 1:
        return value
    return None


def _infer_view_size_from_checkpoint_weights(checkpoint_path: Path) -> int | None:
    try:
        try:
            payload = torch.load(
                checkpoint_path,
                map_location="cpu",
                weights_only=True,
            )
        except TypeError:
            payload = torch.load(checkpoint_path, map_location="cpu")
    except Exception:
        return None

    candidates: list[int] = []

    def _visit(node) -> None:
        if torch.is_tensor(node):
            if node.ndim == 2:
                in_dim = int(node.shape[1])
                root = int(math.isqrt(in_dim))
                if root * root == in_dim and root % 2 == 1 and 3 <= root <= 15:
                    candidates.append(root)
            return
        if isinstance(node, dict):
            for value in node.values():
                _visit(value)
            return
        if isinstance(node, (list, tuple)):
            for value in node:
                _visit(value)

    _visit(payload)
    if not candidates:
        return None

    counts = Counter(candidates)
    return counts.most_common(1)[0][0]


def _resolve_checkpoint_view_size(
    checkpoint_path: Path,
    explicit_view_size: int | None,
) -> int | None:
    if explicit_view_size is not None:
        return int(explicit_view_size)

    value = _extract_view_size_from_hparams(checkpoint_path)
    if value is not None:
        return value

    return _infer_view_size_from_checkpoint_weights(checkpoint_path)


def _effective_pacman_stage(raw_env) -> str:
    current_stage_getter = getattr(raw_env, "_curriculum_stage", None)
    if callable(current_stage_getter):
        return str(current_stage_getter()).strip().lower()
    return str(getattr(raw_env, "pacman_difficulty", "")).strip().lower()


def _force_hard_pacman_for_eval(raw_env, checkpoint_path: Path) -> None:
    pacman_difficulty = str(getattr(raw_env, "pacman_difficulty", "")).strip().lower()
    pacman_curriculum = str(getattr(raw_env, "pacman_curriculum", "off")).strip().lower()
    pacman_random_action_prob = float(getattr(raw_env, "pacman_random_action_prob", 0.0))
    pacman_safe_distance = getattr(raw_env, "pacman_safe_distance", None)
    previous_stage = _effective_pacman_stage(raw_env)

    raw_env.pacman_difficulty = "hard"
    raw_env.pacman_curriculum = "off"
    raw_env.pacman_random_action_prob = 0.0
    raw_env.pacman_safe_distance = None
    if hasattr(raw_env, "_build_pacman_policy") and callable(raw_env._build_pacman_policy):
        raw_env._pacman_policy = raw_env._build_pacman_policy()

    effective_stage = _effective_pacman_stage(raw_env)
    if effective_stage != "hard":
        raise ValueError(
            "Failed to force hard Pacman for evaluation. "
            f"checkpoint={checkpoint_path} effective_stage={effective_stage!r}."
        )

    print(
        "Pacman eval mode: forced hard stage from checkpoint config "
        f"(checkpoint={checkpoint_path}, previous_difficulty={pacman_difficulty!r}, "
        f"previous_curriculum={pacman_curriculum!r}, "
        f"previous_random_action_prob={pacman_random_action_prob}, "
        f"previous_safe_distance={pacman_safe_distance!r}, "
        f"previous_effective_stage={previous_stage!r})."
    )


def _assert_effective_hard_pacman(raw_env, checkpoint_path: Path) -> None:
    effective_stage = _effective_pacman_stage(raw_env)
    if effective_stage == "hard":
        return
    raise ValueError(
        "Checkpoint is not currently in hard Pacman stage. "
        f"checkpoint={checkpoint_path} effective_stage={effective_stage!r}. "
        "Use --allow-non-hard-checkpoint to evaluate this checkpoint without forcing hard mode."
    )


def run_episode(
    learner: str,
    delay: float,
    max_steps: int,
    checkpoint: Path | None,
    runs_root: Path,
    checkpoint_select: str,
    checkpoint_best_metric: str,
    show_reward_breakdown: bool,
    render_mode: str,
    tile_size: int,
    fps: int,
    screenshot_out: Path | None,
    show_observations: bool,
    ghost_view_size: int | None,
    reward_id: str,
    requested_device: str,
    allow_cpu_fallback: bool,
    ascii_step_json: bool,
    allow_non_hard_checkpoint: bool,
) -> None:
    learner = normalize_algorithm(learner)
    resolved_device, resolution_reason = resolve_device(
        requested_device=requested_device,
        allow_cpu_fallback=allow_cpu_fallback,
    )
    reward_root = runs_root / reward_id
    if not reward_root.exists() and reward_id == "current":
        reward_root = runs_root  # Legacy layout before reward strategies.
    runs_root_for_device = reward_root / device_label(resolved_device)

    if checkpoint is not None:
        checkpoint_path = checkpoint
    elif checkpoint_select == "best":
        checkpoint_path = _best_checkpoint_for_learner(
            learner,
            runs_root_for_device,
            selection_metric=checkpoint_best_metric,
        )
    else:
        checkpoint_path = _latest_checkpoint_for_learner(learner, runs_root_for_device)
    print(f"Using checkpoint: {checkpoint_path}")
    print(
        "Eval device selection | "
        f"requested={requested_device} | resolved={resolved_device} | "
        f"cuda_available={torch.cuda.is_available()} | reason={resolution_reason}"
    )
    print(f"Runs root for checkpoint discovery: {runs_root_for_device}")
    if render_mode == "human":
        _print_selected_seed_stats(checkpoint_path)

    resolved_view_size = _resolve_checkpoint_view_size(checkpoint_path, ghost_view_size)
    if resolved_view_size is not None:
        _set_global_ghost_view_size(resolved_view_size)
        print(f"Using ghost view size: {resolved_view_size}x{resolved_view_size}")

    experiment = Experiment.reload_from_file(
        str(checkpoint_path),
        experiment_patch={
            "evaluation": False,
            "render": False,
            "loggers": [],
            "sampling_device": resolved_device,
            "train_device": resolved_device,
            "buffer_device": resolved_device,
        },
    )

    env = experiment.test_env
    raw_env = _unwrap_pacman_env(env)
    # Keep the SAME observation encoding the checkpoint was trained with. Forcing
    # this off here zeroed out the shared-memory bearing channel (the directional
    # signal the policy uses to pursue Pacman outside its local view), producing an
    # out-of-distribution observation that made trained ghosts wander instead of
    # chase. Training always runs with this enabled (True), so eval must match.
    raw_env.render_mode = None if render_mode == "ascii" else render_mode
    raw_env.tile_size = tile_size
    raw_env.fps = fps
    raw_env.show_observations = show_observations
    if allow_non_hard_checkpoint:
        print(
            "Pacman eval mode: keeping checkpoint-defined difficulty/curriculum "
            "(--allow-non-hard-checkpoint)."
        )
    else:
        _force_hard_pacman_for_eval(raw_env, checkpoint_path)
    agent_ids = list(getattr(raw_env, "possible_agents", []))

    total_reward = 0.0
    done = False
    step = 0
    last_frame = None
    last_action_info = None
    last_reward_info = None
    final_result = None

    try:
        try:
            with torch.no_grad(), set_exploration_type(ExplorationType.DETERMINISTIC):
                tensordict = env.reset()
                start_time = time.perf_counter()

                if render_mode == "ascii":
                    print("Pacman Environment (episode start):")
                    print(render_ascii(raw_env.global_view))
                    print()
                    print("Legend: #=Wall, G=Ghost, P=Pacman, X=Captured, <space>=Empty")
                else:
                    frame = raw_env.render(
                        learner=learner,
                        total_reward=total_reward,
                        done=done,
                    )
                    if render_mode == "rgb_array":
                        last_frame = frame
                    if screenshot_out is not None and render_mode != "rgb_array":
                        last_frame = raw_env.capture_frame(
                            learner=learner,
                            total_reward=total_reward,
                            done=done,
                        )

                while not done and step < max_steps:
                    step += 1

                    tensordict = experiment.policy(tensordict)
                    action_tensor = tensordict.get(("ghost", "action"))
                    action_values = _tensor_to_int_list(action_tensor)

                    transition = env.step(tensordict)
                    next_td = transition.get("next")

                    reward_tensor = next_td.get(("ghost", "reward"))
                    reward_values = _tensor_to_float_list(reward_tensor)
                    total_reward += float(sum(reward_values))

                    action_info = {
                        agent_ids[i] if i < len(agent_ids) else f"ghost_{i+1}": ACTION_NAME.get(action_values[i], str(action_values[i]))
                        for i in range(len(action_values))
                    }
                    reward_info = {
                        agent_ids[i] if i < len(agent_ids) else f"ghost_{i+1}": reward_values[i]
                        for i in range(len(reward_values))
                    }
                    last_action_info = action_info
                    last_reward_info = reward_info

                    done = bool(next_td.get("done").item())

                    if render_mode == "ascii":
                        print()
                        print(f"Step {step} | learner={learner} | actions={action_info}")
                        print(render_ascii(raw_env.global_view))
                        print(f"rewards={reward_info} done={done}")
                        if ascii_step_json:
                            payload = _build_ascii_step_diagnostics(
                                raw_env,
                                step=step,
                                learner=learner,
                                done=done,
                                action_info=action_info,
                                reward_info=reward_info,
                            )
                            print(json.dumps(payload, sort_keys=True))
                    else:
                        frame = raw_env.render(
                            learner=learner,
                            total_reward=total_reward,
                            done=done,
                            last_action_by_agent=action_info,
                            last_reward_by_agent=reward_info,
                        )
                        if render_mode == "rgb_array":
                            last_frame = frame
                        print(
                            f"Step {step} | learner={learner} | actions={action_info} "
                            f"| rewards={reward_info} | done={done}"
                        )
                        if screenshot_out is not None and render_mode != "rgb_array":
                            last_frame = raw_env.capture_frame(
                                learner=learner,
                                total_reward=total_reward,
                                done=done,
                                last_action_by_agent=action_info,
                                last_reward_by_agent=reward_info,
                            )

                    if show_reward_breakdown:
                        breakdown = getattr(raw_env, "last_team_reward_breakdown", None)
                        if breakdown is not None:
                            print(f"reward_breakdown={breakdown}")

                    if delay > 0:
                        time.sleep(delay)

                    tensordict = step_mdp(
                        transition,
                        reward_keys=env.reward_keys,
                        action_keys=env.action_keys,
                        done_keys=env.done_keys,
                    )

                final_result = _build_final_result(
                    raw_env,
                    step=step,
                    run_max_steps=max_steps,
                    total_reward=total_reward,
                    elapsed_seconds=time.perf_counter() - start_time,
                )
                final_done = done or step >= max_steps

                if render_mode != "ascii":
                    frame = raw_env.render(
                        learner=learner,
                        total_reward=total_reward,
                        done=final_done,
                        last_action_by_agent=last_action_info,
                        last_reward_by_agent=last_reward_info,
                        final_result=final_result,
                    )
                    if render_mode == "rgb_array":
                        last_frame = frame
                    if screenshot_out is not None and render_mode != "rgb_array":
                        last_frame = raw_env.capture_frame(
                            learner=learner,
                            total_reward=total_reward,
                            done=final_done,
                            last_action_by_agent=last_action_info,
                            last_reward_by_agent=last_reward_info,
                            final_result=final_result,
                        )
                    if render_mode == "human":
                        raw_env.wait_for_close(
                            learner=learner,
                            total_reward=total_reward,
                            done=final_done,
                            last_action_by_agent=last_action_info,
                            last_reward_by_agent=last_reward_info,
                            final_result=final_result,
                        )
        finally:
            if screenshot_out is not None and last_frame is not None:
                save_rgb_frame(last_frame, screenshot_out)
                print(f"Saved screenshot: {screenshot_out}")
    finally:
        raw_env.close()
        experiment.close()

    print()
    result_title = final_result["title"] if final_result is not None else "unknown"
    print(
        f"Episode finished | learner={learner} | steps={step} "
        f"| total_reward={total_reward:.3f} | done={done} | result={result_title}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render one full Pacman episode using a trained learner checkpoint."
    )
    parser.add_argument(
        "--learner",
        "--algo",
        dest="learner",
        choices=["iql", "vdn", "qmix", "qmixlocal", "qmixglobal"],
        required=True,
        help="Learner whose trained checkpoint should control the ghosts.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.25,
        help="Seconds between rendered steps.",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=200,
        help="Maximum number of environment steps for the episode.",
    )
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=PROJECT_ROOT / "benchmarl_setup" / "runs",
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
        "--ghost-view-size",
        type=int,
        default=None,
        help="Odd local observation width/height for ghosts. Useful for legacy checkpoints.",
    )
    parser.add_argument(
        "--reward-id",
        type=str,
        default="current",
        help="Reward strategy folder used for checkpoint discovery.",
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=None,
        help="Optional explicit checkpoint path (.pt). If omitted, latest for learner is used.",
    )
    parser.add_argument(
        "--checkpoint-select",
        choices=["best", "latest"],
        default="best",
        help="How to select checkpoint when --checkpoint is not provided.",
    )
    parser.add_argument(
        "--checkpoint-best-metric",
        choices=list(CHECKPOINT_BEST_METRICS),
        default="capture_rate",
        help=(
            "Metric used when --checkpoint-select best is active: reward uses training scalars; "
            "capture_rate uses evaluation_report_live_capture.csv when available."
        ),
    )
    parser.add_argument(
        "--show-reward-breakdown",
        action="store_true",
        help="Print per-step team reward term breakdown from the environment.",
    )
    parser.add_argument(
        "--ascii-step-json",
        action="store_true",
        help=(
            "When --render-mode ascii is active, print one JSON diagnostics object per step "
            "with capture, visibility, positions, and reward decomposition fields."
        ),
    )
    parser.add_argument(
        "--render-mode",
        choices=["ascii", "human", "rgb_array"],
        default="human",
        help=(
            "Render output mode: ascii is a simple terminal grid, "
            "human opens the Pygame window, rgb_array returns image frames."
        ),
    )
    parser.add_argument(
        "--tile-size",
        type=int,
        default=28,
        help="Tile size in pixels for Pygame rendering.",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=12,
        help="Target frames per second for human Pygame rendering.",
    )
    parser.add_argument(
        "--screenshot-out",
        type=Path,
        default=None,
        help="Optional PNG path for the last rendered frame.",
    )
    parser.add_argument(
        "--hide-observations",
        action="store_true",
        help="Disable the translucent local-observation overlays in Pygame renders.",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        help="Compute device for policy/eval tensors: auto, cpu, cuda, cuda:<index>.",
    )
    parser.add_argument(
        "--allow-cpu-fallback",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Fall back to CPU when CUDA is requested but unavailable.",
    )
    parser.add_argument(
        "--allow-non-hard-checkpoint",
        action="store_true",
        help=(
            "Disable default hard-forcing in eval replay and keep the checkpoint's "
            "original Pacman difficulty/curriculum behavior."
        ),
    )
    args = parser.parse_args()
    normalized_learner = normalize_algorithm(args.learner)
    if normalized_learner not in SUPPORTED_ALGORITHMS:
        raise ValueError(
            f"Unsupported learner: {args.learner}. Allowed: {list(SUPPORTED_ALGORITHMS)}"
        )

    maze_runs_root = runs_root_for_maze(args.runs_root, args.maze)
    _configure_warning_filters()

    run_episode(
        learner=normalized_learner,
        delay=args.delay,
        max_steps=args.max_steps,
        checkpoint=args.checkpoint,
        runs_root=maze_runs_root,
        checkpoint_select=args.checkpoint_select,
        checkpoint_best_metric=args.checkpoint_best_metric,
        show_reward_breakdown=args.show_reward_breakdown,
        render_mode=args.render_mode,
        tile_size=args.tile_size,
        fps=args.fps,
        screenshot_out=args.screenshot_out,
        show_observations=not args.hide_observations,
        ghost_view_size=args.ghost_view_size,
        reward_id=args.reward_id,
        requested_device=args.device,
        allow_cpu_fallback=args.allow_cpu_fallback,
        ascii_step_json=args.ascii_step_json,
        allow_non_hard_checkpoint=args.allow_non_hard_checkpoint,
    )


if __name__ == "__main__":
    main()
