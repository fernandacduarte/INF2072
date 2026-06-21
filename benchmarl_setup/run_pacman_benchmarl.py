import argparse
from pathlib import Path
import sys

import torch

from benchmarl.algorithms import IqlConfig, QmixConfig, VdnConfig
from benchmarl.experiment import Experiment, ExperimentConfig
from benchmarl.models import MlpConfig

# Ensure workspace root is importable when this file is run by path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from benchmarl_setup.pacman_benchmarl_task import PacmanTask, register_pacman_task
from benchmarl_setup.algorithm_utils import (
    SUPPORTED_MAZES,
    normalize_algorithm,
    qmix_uses_global_state,
    runs_root_for_maze,
)
from benchmarl_setup.device_utils import resolve_device


def _algorithm_config(name: str):
    algorithm = normalize_algorithm(name)
    if algorithm == "iql":
        return IqlConfig.get_from_yaml()
    if algorithm == "vdn":
        return VdnConfig.get_from_yaml()
    if algorithm in ("qmixlocal", "qmixglobal"):
        return QmixConfig.get_from_yaml()
    raise ValueError(f"Unsupported algorithm: {name}")


def _tune_iql_experiment(experiment_config, max_frames: int) -> None:
    """Apply IQL-specific exploration/optimization tuning for convergence (plan-000008).

    These fields have no CLI flags, so overriding them here cannot conflict with
    user-supplied arguments. Each attribute is guarded with ``hasattr`` to stay
    robust to BenchMARL field renames. Only the IQL path calls this; VDN/QMIX
    keep BenchMARL's stock schedule.
    """
    overrides = {
        # Anneal epsilon from full exploration down to a small floor over most of
        # the budget so the team explores early then commits to a pursuit policy.
        "exploration_eps_init": 1.0,
        "exploration_eps_end": 0.05,
        "exploration_anneal_frames": int(max_frames * 0.8),
        # A slightly higher LR than the stock 5e-5 speeds convergence at this scale.
        "lr": 1e-4,
        # Standard discount for episodic pursuit.
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
        default=2000,
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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    algorithm = normalize_algorithm(args.algorithm)
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
        "Device selection | "
        f"requested={args.device} | resolved={resolved_device} | "
        f"cuda_available={torch.cuda.is_available()} | reason={resolution_reason}"
    )

    task_config = {
        "max_cycles": 200,
        "grid_size": args.grid_size,
        "map_name": args.maze,
        "include_global_state": qmix_uses_global_state(algorithm),
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

    # IQL-only convergence tuning; VDN/QMIX keep BenchMARL's stock schedule.
    if algorithm == "iql":
        _tune_iql_experiment(experiment_config, args.max_frames)

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
