import argparse
import csv
import math
import time
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


def _best_checkpoint_for_learner(learner: str, runs_root: Path) -> Path:
    run_dirs = _candidate_run_dirs(learner, runs_root)
    if not run_dirs:
        raise FileNotFoundError(
            f"No run folders found for learner '{learner}' in {runs_root}."
        )

    scored_runs = []
    for run_dir in run_dirs:
        checkpoint = _latest_checkpoint_in_run(run_dir)
        if checkpoint is None:
            continue
        score = _score_run_for_selection(run_dir)
        scored_runs.append((score, checkpoint, run_dir))

    if not scored_runs:
        raise FileNotFoundError(
            "No checkpoint files found. Run training with checkpoint saving enabled, for example:\n"
            f"py -3.11 benchmarl_setup\\run_pacman_benchmarl.py --algorithm {learner} --checkpoint-at-end"
        )

    scored_runs.sort(key=lambda item: item[0], reverse=True)
    best_score, best_checkpoint, best_run_dir = scored_runs[0]
    print(
        "Best-run selection: "
        f"run={best_run_dir.name} tail_mean={best_score[0]:.4f} best_single={best_score[1]:.4f}"
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


def _build_final_result(
    raw_env,
    *,
    step: int,
    run_max_steps: int,
    total_reward: float,
    elapsed_seconds: float,
) -> dict:
    if raw_env._is_capture_state():
        title = "Ghosts win"
        reason = "Pacman was captured."
    elif not raw_env.agents and raw_env.step_count >= raw_env.max_steps:
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


def run_episode(
    learner: str,
    delay: float,
    max_steps: int,
    checkpoint: Path | None,
    runs_root: Path,
    checkpoint_select: str,
    show_reward_breakdown: bool,
    render_mode: str,
    tile_size: int,
    fps: int,
    screenshot_out: Path | None,
    show_observations: bool,
    ghost_view_size: int | None,
) -> None:
    learner = normalize_algorithm(learner)

    if checkpoint is not None:
        checkpoint_path = checkpoint
    elif checkpoint_select == "best":
        checkpoint_path = _best_checkpoint_for_learner(learner, runs_root)
    else:
        checkpoint_path = _latest_checkpoint_for_learner(learner, runs_root)
    print(f"Using checkpoint: {checkpoint_path}")

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
        },
    )

    env = experiment.test_env
    raw_env = _unwrap_pacman_env(env)
    raw_env.render_mode = None if render_mode == "ascii" else render_mode
    raw_env.tile_size = tile_size
    raw_env.fps = fps
    raw_env.show_observations = show_observations
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
        "--seed",
        type=int,
        default=None,
        help="Deprecated placeholder (kept for CLI compatibility).",
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
        "--show-reward-breakdown",
        action="store_true",
        help="Print per-step team reward term breakdown from the environment.",
    )
    parser.add_argument(
        "--render-mode",
        choices=["ascii", "human", "rgb_array"],
        default="ascii",
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
    args = parser.parse_args()
    normalized_learner = normalize_algorithm(args.learner)
    if normalized_learner not in SUPPORTED_ALGORITHMS:
        raise ValueError(
            f"Unsupported learner: {args.learner}. Allowed: {list(SUPPORTED_ALGORITHMS)}"
        )

    maze_runs_root = runs_root_for_maze(args.runs_root, args.maze)

    run_episode(
        learner=normalized_learner,
        delay=args.delay,
        max_steps=args.max_steps,
        checkpoint=args.checkpoint,
        runs_root=maze_runs_root,
        checkpoint_select=args.checkpoint_select,
        show_reward_breakdown=args.show_reward_breakdown,
        render_mode=args.render_mode,
        tile_size=args.tile_size,
        fps=args.fps,
        screenshot_out=args.screenshot_out,
        show_observations=not args.hide_observations,
        ghost_view_size=args.ghost_view_size,
    )


if __name__ == "__main__":
    main()
