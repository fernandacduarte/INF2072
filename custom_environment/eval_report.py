import argparse
import csv
import random
import sys
from pathlib import Path

import numpy as np
import torch

from benchmarl.experiment import Experiment
from torchrl.envs.utils import ExplorationType, set_exploration_type, step_mdp

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from benchmarl_setup.algorithm_utils import (
    SUPPORTED_ALGORITHMS,
    SUPPORTED_MAZES,
    candidate_run_dirs,
    normalize_algorithm,
    runs_root_for_maze,
)
from custom_environment.eval import (
    _best_checkpoint_for_learner,
    _latest_checkpoint_for_learner,
    _resolve_checkpoint_view_size,
    _set_global_ghost_view_size,
    _unwrap_pacman_env,
)


def _select_checkpoint(
    learner: str,
    runs_root: Path,
    checkpoint_select: str,
    explicit_checkpoint: Path | None,
) -> Path:
    if explicit_checkpoint is not None:
        return explicit_checkpoint
    if checkpoint_select == "best":
        return _best_checkpoint_for_learner(learner, runs_root)
    return _latest_checkpoint_for_learner(learner, runs_root)


def _resolve_runs_root_for_learner(
    base_runs_root: Path,
    learner: str,
    device_label_selector: str,
) -> Path:
    selector = device_label_selector.strip().lower()

    if selector != "auto":
        selected_root = base_runs_root / selector
        if candidate_run_dirs(selected_root, learner):
            return selected_root
        if candidate_run_dirs(base_runs_root, learner):
            return base_runs_root
        raise FileNotFoundError(
            f"No run folders found for learner '{learner}' in {selected_root} or {base_runs_root}."
        )

    if candidate_run_dirs(base_runs_root, learner):
        return base_runs_root

    candidate_roots: list[Path] = []
    if base_runs_root.exists():
        for child in sorted(base_runs_root.iterdir()):
            if not child.is_dir():
                continue
            if candidate_run_dirs(child, learner):
                candidate_roots.append(child)

    if not candidate_roots:
        raise FileNotFoundError(
            f"No run folders found for learner '{learner}' in {base_runs_root} "
            "or any direct device subfolder."
        )

    if len(candidate_roots) == 1:
        selected = candidate_roots[0]
        print(f"Auto-selected runs root for learner={learner}: {selected}")
        return selected

    selected = max(candidate_roots, key=lambda p: p.stat().st_mtime)
    print(
        "Auto-selected newest runs root for "
        f"learner={learner}: {selected} "
        f"(candidates: {', '.join(str(p.name) for p in candidate_roots)})"
    )
    return selected


def _run_eval_episodes(
    checkpoint_path: Path,
    learner: str,
    episodes: int,
    max_steps: int,
    seed_base: int,
    ghost_view_size: int | None,
    verbose: bool,
) -> dict[str, float | int | str]:
    resolved_view_size = _resolve_checkpoint_view_size(checkpoint_path, ghost_view_size)
    if resolved_view_size is not None:
        _set_global_ghost_view_size(resolved_view_size)

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
    raw_env.render_mode = None

    episode_returns: list[float] = []
    episode_steps: list[int] = []
    ghost_wins = 0
    pacman_wins = 0

    try:
        with torch.no_grad(), set_exploration_type(ExplorationType.DETERMINISTIC):
            for episode_idx in range(episodes):
                episode_seed = seed_base + episode_idx
                random.seed(episode_seed)
                np.random.seed(episode_seed)
                torch.manual_seed(episode_seed)

                tensordict = env.reset()
                done = False
                step = 0
                total_reward = 0.0

                while not done and step < max_steps:
                    step += 1
                    tensordict = experiment.policy(tensordict)
                    transition = env.step(tensordict)
                    next_td = transition.get("next")

                    reward_tensor = next_td.get(("ghost", "reward"))
                    reward_values = reward_tensor.detach().cpu().reshape(-1).tolist()
                    # Team reward is broadcast to all ghosts; use mean to avoid N-ghost inflation.
                    step_reward = float(np.mean(reward_values)) if reward_values else 0.0
                    total_reward += step_reward

                    done = bool(next_td.get("done").item())
                    tensordict = step_mdp(
                        transition,
                        reward_keys=env.reward_keys,
                        action_keys=env.action_keys,
                        done_keys=env.done_keys,
                    )

                captured = bool(raw_env._is_capture_state())
                if captured:
                    ghost_wins += 1
                else:
                    pacman_wins += 1

                episode_returns.append(total_reward)
                episode_steps.append(step)

                if verbose:
                    outcome = "ghost_win" if captured else "pacman_win"
                    print(
                        f"Episode {episode_idx + 1}/{episodes} "
                        f"| learner={learner} | return={total_reward:.3f} "
                        f"| steps={step} | outcome={outcome}"
                    )
    finally:
        raw_env.close()
        experiment.close()

    returns_np = np.asarray(episode_returns, dtype=np.float64)
    steps_np = np.asarray(episode_steps, dtype=np.float64)

    return {
        "learner": learner,
        "checkpoint_path": str(checkpoint_path),
        "episodes": int(episodes),
        "ghost_win_rate": float(ghost_wins / episodes),
        "pacman_win_rate": float(pacman_wins / episodes),
        "mean_episode_return": float(np.mean(returns_np)),
        "std_episode_return": float(np.std(returns_np)),
        "median_episode_return": float(np.median(returns_np)),
        "mean_steps": float(np.mean(steps_np)),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate one or more trained checkpoints and report win rate and episode return."
    )
    parser.add_argument(
        "--learner",
        "--algo",
        dest="learner",
        choices=["iql", "vdn", "qmix", "qmixlocal", "qmixglobal"],
        default=None,
        help="Optional single learner to evaluate.",
    )
    parser.add_argument(
        "--algorithms",
        type=str,
        default="iql,vdn,qmixlocal,qmixglobal",
        help="Comma-separated learners to evaluate when --learner is not provided.",
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
        "--device-label",
        type=str,
        default="auto",
        help=(
            "Runs subfolder label inside <runs-root>/<maze> (for example: cpu, cuda). "
            "Use 'auto' to detect runs in <maze> directly or in one-level device subfolders."
        ),
    )
    parser.add_argument(
        "--checkpoint-select",
        choices=["best", "latest"],
        default="best",
        help="Checkpoint selection mode when --checkpoint is not provided.",
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=None,
        help="Optional explicit checkpoint path (.pt). Only valid with --learner.",
    )
    parser.add_argument(
        "--episodes",
        type=int,
        default=30,
        help="Number of deterministic episodes per checkpoint.",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=200,
        help="Maximum environment steps per episode.",
    )
    parser.add_argument(
        "--seed-base",
        type=int,
        default=0,
        help="Base seed used to create deterministic per-episode seeds.",
    )
    parser.add_argument(
        "--ghost-view-size",
        type=int,
        default=None,
        help="Odd local observation width/height for ghosts. Useful for legacy checkpoints.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional CSV output path for the report.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-episode outcomes.",
    )
    return parser.parse_args()


def _resolve_algorithms(args: argparse.Namespace) -> list[str]:
    if args.learner is not None:
        algorithms = [normalize_algorithm(args.learner)]
    else:
        algorithms = [normalize_algorithm(item) for item in args.algorithms.split(",") if item.strip()]

    if not algorithms:
        raise ValueError("At least one learner must be provided.")

    invalid = [name for name in algorithms if name not in SUPPORTED_ALGORITHMS]
    if invalid:
        raise ValueError(f"Unsupported learner(s): {invalid}. Allowed: {list(SUPPORTED_ALGORITHMS)}")

    return algorithms


def _write_report_csv(rows: list[dict[str, float | int | str]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "learner",
        "checkpoint_path",
        "episodes",
        "ghost_win_rate",
        "pacman_win_rate",
        "mean_episode_return",
        "std_episode_return",
        "median_episode_return",
        "mean_steps",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()

    if args.episodes < 1:
        raise ValueError("--episodes must be >= 1")
    if args.max_steps < 1:
        raise ValueError("--max-steps must be >= 1")

    algorithms = _resolve_algorithms(args)

    if args.checkpoint is not None and len(algorithms) != 1:
        raise ValueError("--checkpoint can only be used with a single learner (--learner).")

    maze_runs_root = runs_root_for_maze(args.runs_root, args.maze)

    report_rows: list[dict[str, float | int | str]] = []
    for learner in algorithms:
        learner_runs_root = _resolve_runs_root_for_learner(
            base_runs_root=maze_runs_root,
            learner=learner,
            device_label_selector=args.device_label,
        )
        checkpoint_path = _select_checkpoint(
            learner=learner,
            runs_root=learner_runs_root,
            checkpoint_select=args.checkpoint_select,
            explicit_checkpoint=args.checkpoint,
        )
        print(f"Evaluating learner={learner} checkpoint={checkpoint_path}")

        summary = _run_eval_episodes(
            checkpoint_path=checkpoint_path,
            learner=learner,
            episodes=args.episodes,
            max_steps=args.max_steps,
            seed_base=args.seed_base,
            ghost_view_size=args.ghost_view_size,
            verbose=args.verbose,
        )
        report_rows.append(summary)

    print("\nDeterministic evaluation summary:")
    for row in report_rows:
        print(
            f"- {row['learner']}: episodes={row['episodes']} "
            f"ghost_win_rate={row['ghost_win_rate']:.3f} "
            f"mean_episode_return={row['mean_episode_return']:.3f} "
            f"std_episode_return={row['std_episode_return']:.3f} "
            f"mean_steps={row['mean_steps']:.1f}"
        )

    out_path = args.out
    if out_path is None:
        out_path = maze_runs_root / "evaluation_report.csv"
    _write_report_csv(report_rows, out_path)
    print(f"Saved report: {out_path}")


if __name__ == "__main__":
    main()
