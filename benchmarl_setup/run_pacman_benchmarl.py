import argparse
from pathlib import Path
import sys
import warnings

import torch

from benchmarl.algorithms import IqlConfig, QmixConfig, VdnConfig
from benchmarl.experiment import Experiment, ExperimentConfig
from benchmarl.models import MlpConfig

# Ensure workspace root is importable when this file is run by path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from benchmarl_setup.pacman_benchmarl_task import PacmanTask, register_pacman_task
from custom_environment.env.rewards import (
    load_reward_strategy,
)
from custom_environment.env.rewards.loader import reward_class_from_id
from benchmarl_setup.algorithm_utils import (
    SUPPORTED_MAZES,
    normalize_algorithm,
    qmix_uses_global_state,
    runs_root_for_maze,
    training_exploration_schedule,
)
from benchmarl_setup.device_utils import resolve_device


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


def _algorithm_config(name: str):
    algorithm = normalize_algorithm(name)
    if algorithm == "iql":
        return IqlConfig.get_from_yaml()
    if algorithm == "vdn":
        return VdnConfig.get_from_yaml()
    if algorithm in ("qmixlocal", "qmixglobal"):
        return QmixConfig.get_from_yaml()
    raise ValueError(f"Unsupported algorithm: {name}")


def _tune_shared_experiment(
    experiment_config,
    algorithm: str,
    max_frames: int,
    maze: str,
    pacman_curriculum: str,
    epsilon_anneal_ratio: float = 0.95,
    epsilon_init: float | None = None,
    epsilon_end: float | None = None,
) -> None:
    """Apply one shared exploration/optimization schedule across MARL algorithms."""
    schedule = training_exploration_schedule(
        algorithm,
        maze,
        max_frames,
        pacman_curriculum=pacman_curriculum,
        anneal_ratio=float(epsilon_anneal_ratio),
        epsilon_init=epsilon_init,
        epsilon_end=epsilon_end,
    )
    overrides = {
        "exploration_eps_init": schedule["epsilon_init"],
        "exploration_eps_end": schedule["epsilon_end"],
        "exploration_anneal_frames": schedule["epsilon_anneal_frames"],
        "lr": 1e-4,
        "gamma": 0.99,
    }
    for name, value in overrides.items():
        if hasattr(experiment_config, name):
            setattr(experiment_config, name, value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run BenchMARL on custom Pacman.")
    parser.add_argument(
        "--algorithm",
        type=str,
        default="iql",
        choices=["iql", "vdn", "qmix", "qmixlocal", "qmixglobal"],
        help="MARL algorithm to run.",
    )
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--max-frames",
        type=int,
        default=60000,
        help="Total collected frames. Default raised to a convergence-scale budget (plan-000008); pass a smaller value for smoke runs.",
    )
    parser.add_argument("--frames-per-batch", type=int, default=200)
    parser.add_argument("--optimizer-steps", type=int, default=10)
    parser.add_argument("--train-batch-size", type=int, default=128)
    parser.add_argument("--memory-size", type=int, default=10000)
    parser.add_argument(
        "--init-random-frames",
        type=int,
        default=5000,
        help="Initial random interaction frames before learning starts.",
    )
    parser.add_argument("--grid-size", type=int, default=20)
    parser.add_argument(
        "--ghost-view-size",
        type=int,
        default=None,
        help="Odd local observation width/height for ghosts (for example 3 or 5).",
    )
    parser.add_argument(
        "--maze",
        type=str,
        default="default",
        choices=SUPPORTED_MAZES,
        help="Maze layout to train on.",
    )
    parser.add_argument(
        "--reward-class",
        type=str,
        default=None,
        help="Reward implementation as module:Class (must be a zero-argument RewardStrategy).",
    )
    parser.add_argument(
        "--reward-id",
        type=str,
        default="current",
        help=(
            "Reward strategy id alias (for example: current, current_git, current_with_overlap_or_same_corridor). "
            "Ignored when --reward-class is provided."
        ),
    )
    parser.add_argument(
        "--pacman-difficulty",
        type=str,
        default="hard",
        choices=["easy", "medium", "hard"],
        help="Fixed Pacman controller strength when --pacman-curriculum=off.",
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
        help="Override safety cap used by Pacman heuristic (default uses policy preset).",
    )
    parser.add_argument(
        "--pacman-curriculum",
        type=str,
        default="off",
        choices=["off", "easy-medium-hard", "mixed-easy-medium-hard"],
        help=(
            "Curriculum schedule applied over frames. In curriculum modes, each "
            "stage also samples ghost spawn modes with the same stage profile "
            "(easy 70/30/0, medium 40/40/20, hard 20/40/40)."
        ),
    )
    parser.add_argument(
        "--pacman-curriculum-max-frames",
        type=int,
        default=0,
        help="Frame budget used to complete the curriculum schedule.",
    )
    parser.add_argument(
        "--pacman-curriculum-frame-offset",
        type=int,
        default=0,
        help="Global frame offset used for curriculum when run is part of a benchmark matrix.",
    )
    parser.add_argument(
        "--randomize-spawns",
        action=argparse.BooleanOptionalAction,
        default=False,
        help=(
            "Randomize Pacman/ghost spawn cells each episode so the policy cannot "
            "memorize a fixed route to a fixed start cell and must pursue reactively. "
            "When curriculum is enabled, spawn mode sampling is curriculum-driven "
            "regardless of this toggle."
        ),
    )
    parser.add_argument(
        "--randomize-spawns-min-distance",
        type=int,
        default=4,
        help="Minimum ghost->Pacman BFS clearance enforced when randomizing spawns.",
    )
    parser.add_argument(
        "--save-folder",
        type=str,
        default=str((PROJECT_ROOT / "benchmarl_setup" / "runs").resolve()),
        help="Base runs directory. Training output is stored under <save-folder>/<maze>.",
    )
    parser.add_argument(
        "--save-folder-includes-maze",
        action="store_true",
        help="Treat --save-folder as the final output root (do not append <maze>).",
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
        help="Save a checkpoint at the end of training.",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        help="Compute device for sampling/training/buffer: auto, cpu, cuda, cuda:<index>.",
    )
    parser.add_argument(
        "--allow-cpu-fallback",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Fall back to CPU when CUDA is requested but unavailable.",
    )
    parser.add_argument(
        "--epsilon-init",
        type=float,
        default=None,
        help=(
            "Optional exploration epsilon start value. Must be passed together with "
            "--epsilon-end and --epsilon-anneal-ratio."
        ),
    )
    parser.add_argument(
        "--epsilon-end",
        type=float,
        default=None,
        help=(
            "Optional exploration epsilon end value. Must be passed together with "
            "--epsilon-init and --epsilon-anneal-ratio."
        ),
    )
    parser.add_argument(
        "--epsilon-anneal-ratio",
        type=float,
        default=None,
        help=(
            "Optional anneal fraction in (0,1]. Must be passed together with "
            "--epsilon-init and --epsilon-end to activate explicit epsilon override."
        ),
    )
    return parser.parse_args()


def main() -> None:
    _configure_warning_filters()
    args = parse_args()
    if not (0.0 <= float(args.pacman_random_action_prob) <= 1.0):
        raise ValueError("--pacman-random-action-prob must be in [0,1].")
    if int(args.pacman_curriculum_max_frames) < 0:
        raise ValueError("--pacman-curriculum-max-frames must be >= 0.")
    if int(args.pacman_curriculum_frame_offset) < 0:
        raise ValueError("--pacman-curriculum-frame-offset must be >= 0.")
    epsilon_override_count = sum(
        value is not None
        for value in (
            args.epsilon_init,
            args.epsilon_end,
            args.epsilon_anneal_ratio,
        )
    )
    if epsilon_override_count not in {0, 3}:
        raise ValueError(
            "Explicit epsilon override requires all three flags together: "
            "--epsilon-init, --epsilon-end, --epsilon-anneal-ratio."
        )
    if epsilon_override_count == 3 and not (
        0.0 <= float(args.epsilon_end) <= float(args.epsilon_init) <= 1.0
    ):
        raise ValueError("--epsilon values must satisfy 0 <= epsilon-end <= epsilon-init <= 1")
    resolved_epsilon_anneal_ratio = (
        float(args.epsilon_anneal_ratio)
        if args.epsilon_anneal_ratio is not None
        else 0.95
    )
    if not (0.0 < resolved_epsilon_anneal_ratio <= 1.0):
        raise ValueError("--epsilon-anneal-ratio must be in (0, 1].")
    algorithm = normalize_algorithm(args.algorithm)
    resolved_reward_class = (
        str(args.reward_class).strip()
        if args.reward_class is not None and str(args.reward_class).strip()
        else reward_class_from_id(args.reward_id)
    )
    reward_strategy = load_reward_strategy(resolved_reward_class)
    resolved_device, resolution_reason = resolve_device(
        requested_device=args.device,
        allow_cpu_fallback=args.allow_cpu_fallback,
    )

    if args.save_folder_includes_maze:
        save_root = Path(args.save_folder)
    else:
        save_root = runs_root_for_maze(Path(args.save_folder), args.maze)
    save_root.mkdir(parents=True, exist_ok=True)

    full_task_name = register_pacman_task()
    print(f"Registered task: {full_task_name}")
    print(
        "Reward strategy | "
        f"id={reward_strategy.strategy_id} | class={resolved_reward_class}"
    )
    print(
        "Device selection | "
        f"requested={args.device} | resolved={resolved_device} | "
        f"cuda_available={torch.cuda.is_available()} | reason={resolution_reason}"
    )

    task_config = {
        "max_cycles": 200,
        "grid_size": args.grid_size,
        "map_name": args.maze,
        "include_global_state": qmix_uses_global_state(algorithm),
        "shared_memory_in_observation_enabled": True,
        "reward_class": resolved_reward_class,
        "reward_id": reward_strategy.strategy_id,
        "pacman_difficulty": args.pacman_difficulty,
        "pacman_random_action_prob": float(args.pacman_random_action_prob),
        "pacman_safe_distance": args.pacman_safe_distance,
        "pacman_curriculum": args.pacman_curriculum,
        "pacman_curriculum_max_frames": int(args.pacman_curriculum_max_frames),
        "pacman_curriculum_frame_offset": int(args.pacman_curriculum_frame_offset),
        "randomize_spawns": bool(args.randomize_spawns),
        "randomize_spawns_min_distance": int(args.randomize_spawns_min_distance),
    }
    if args.ghost_view_size is not None:
        task_config["ghost_view_size"] = int(args.ghost_view_size)

    task = PacmanTask.PACMAN.get_task(config=task_config)

    algorithm_config = _algorithm_config(algorithm)
    model_config = MlpConfig.get_from_yaml()
    model_config.num_feature_dims = 2
    experiment_config = ExperimentConfig.get_from_yaml()

    # Keep defaults deterministic and light for local experimentation.
    experiment_config.sampling_device = resolved_device
    experiment_config.train_device = resolved_device
    experiment_config.buffer_device = resolved_device
    experiment_config.prefer_continuous_actions = False
    experiment_config.parallel_collection = False
    experiment_config.loggers = ["csv"]
    experiment_config.render = False
    experiment_config.evaluation = False

    experiment_config.max_n_frames = args.max_frames
    experiment_config.max_n_iters = None

    experiment_config.off_policy_n_envs_per_worker = 1
    experiment_config.off_policy_collected_frames_per_batch = args.frames_per_batch
    experiment_config.off_policy_n_optimizer_steps = args.optimizer_steps
    experiment_config.off_policy_train_batch_size = args.train_batch_size
    experiment_config.off_policy_memory_size = args.memory_size
    experiment_config.off_policy_init_random_frames = args.init_random_frames

    experiment_config.save_folder = str(save_root)
    experiment_config.checkpoint_interval = args.checkpoint_interval
    experiment_config.checkpoint_at_end = args.checkpoint_at_end
    if hasattr(experiment_config, "keep_checkpoints_num"):
        if args.checkpoint_interval > 0:
            periodic_count = (args.max_frames + args.checkpoint_interval - 1) // args.checkpoint_interval
            expected_total = periodic_count + (1 if args.checkpoint_at_end else 0)
            keep_target = max(1, int(expected_total))
            current_keep = int(getattr(experiment_config, "keep_checkpoints_num", 0) or 0)
            experiment_config.keep_checkpoints_num = max(current_keep, keep_target)

    # Apply one shared schedule so common hyperparameters stay aligned.
    _tune_shared_experiment(
        experiment_config,
        algorithm,
        args.max_frames,
        args.maze,
        args.pacman_curriculum,
        resolved_epsilon_anneal_ratio,
        epsilon_init=args.epsilon_init,
        epsilon_end=args.epsilon_end,
    )

    experiment = Experiment(
        task=task,
        algorithm_config=algorithm_config,
        model_config=model_config,
        seed=args.seed,
        config=experiment_config,
    )

    experiment.run()


if __name__ == "__main__":
    main()
