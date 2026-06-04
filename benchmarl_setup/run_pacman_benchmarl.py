import argparse
from pathlib import Path
import sys
from typing import Any

from benchmarl.algorithms import IqlConfig, QmixConfig, VdnConfig
from benchmarl.experiment import Experiment, ExperimentConfig
from benchmarl.models import MlpConfig
import torch

# Ensure workspace root is importable when this file is run by path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from benchmarl_setup.pacman_benchmarl_task import PacmanTask, register_pacman_task


def _algorithm_config(name: str):
    if name == "iql":
        return IqlConfig.get_from_yaml()
    if name == "vdn":
        return VdnConfig.get_from_yaml()
    if name == "qmix":
        return QmixConfig.get_from_yaml()
    raise ValueError(f"Unsupported algorithm: {name}")


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (float, int)):
        return float(value)
    if isinstance(value, torch.Tensor):
        if value.numel() == 0:
            return None
        return float(value.detach().cpu().reshape(-1)[0].item())
    if hasattr(value, "item"):
        try:
            return float(value.item())
        except Exception:
            return None
    return None


def _extract_frames_from_log_payload(payload: Any) -> int | None:
    if payload is None:
        return None
    if isinstance(payload, dict):
        for key in (
            "counters/current_frames",
            "counters_current_frames",
            "current_frames",
            "total_frames",
            "frames",
        ):
            if key in payload:
                value = _to_float(payload[key])
                return int(value) if value is not None else None
    return None


def _try_get_live_epsilon(experiment: Experiment) -> float | None:
    candidates = [
        ("algorithm", "exploration_module", "eps"),
        ("algorithm", "exploration_module", "epsilon"),
        ("_algorithm", "exploration_module", "eps"),
        ("_algorithm", "exploration_module", "epsilon"),
        ("policy", "exploration_module", "eps"),
        ("policy", "exploration_module", "epsilon"),
        ("_policy", "exploration_module", "eps"),
        ("_policy", "exploration_module", "epsilon"),
    ]

    for path in candidates:
        current = experiment
        ok = True
        for attr in path:
            if not hasattr(current, attr):
                ok = False
                break
            current = getattr(current, attr)
        if not ok:
            continue
        value = _to_float(current)
        if value is not None:
            return value

    return None


def _install_live_epsilon_logging(
    experiment: Experiment,
    enabled: bool,
    log_every_frames: int,
) -> None:
    if not enabled:
        return

    state = {
        "last_print_frame": -10**18,
        "fallback_counter": 0,
    }

    def maybe_print(frames: int | None) -> None:
        epsilon = _try_get_live_epsilon(experiment)
        if epsilon is None:
            return

        if frames is None:
            state["fallback_counter"] += 1
            if state["fallback_counter"] % 10 == 0:
                print(f"[epsilon] value={epsilon:.6f}")
            return

        if frames - state["last_print_frame"] >= log_every_frames:
            state["last_print_frame"] = frames
            print(f"[epsilon] frames={frames} value={epsilon:.6f}")

    # Wrap internal logging methods that are typically called each iteration.
    for method_name in ("_log", "_log_dict", "log"):
        original = getattr(experiment, method_name, None)
        if original is None or not callable(original):
            continue

        def _make_wrapper(orig_func):
            def _wrapped(*args, **kwargs):
                result = orig_func(*args, **kwargs)
                payload = None
                if args:
                    payload = args[0]
                if payload is None and "log_dict" in kwargs:
                    payload = kwargs["log_dict"]
                if payload is None and "data" in kwargs:
                    payload = kwargs["data"]
                frames = _extract_frames_from_log_payload(payload)
                maybe_print(frames)
                return result

            return _wrapped

        setattr(experiment, method_name, _make_wrapper(original))

    # One immediate print so users can verify hook is active.
    initial_eps = _try_get_live_epsilon(experiment)
    if initial_eps is not None:
        print(f"[epsilon] initial={initial_eps:.6f}")
    else:
        print(
            "[epsilon] live epsilon source not found on experiment internals; "
            "training will continue without per-iteration epsilon prints."
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run BenchMARL on custom Pacman.")
    parser.add_argument(
        "--algorithm",
        type=str,
        default="iql",
        choices=["iql", "vdn", "qmix"],
        help="MARL algorithm to run.",
    )
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-frames", type=int, default=5000)
    parser.add_argument("--frames-per-batch", type=int, default=200)
    parser.add_argument("--optimizer-steps", type=int, default=10)
    parser.add_argument("--train-batch-size", type=int, default=128)
    parser.add_argument("--memory-size", type=int, default=10000)
    parser.add_argument(
        "--init-random-frames",
        type=int,
        default=1000,
        help="Initial random interaction frames before learning starts.",
    )
    parser.add_argument("--number-ghosts", type=int, default=2)
    parser.add_argument("--grid-size", type=int, default=20)
    parser.add_argument(
        "--save-folder",
        type=str,
        default=str((PROJECT_ROOT / "benchmarl_setup" / "runs").resolve()),
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
        "--print-epsilon",
        action="store_true",
        help="Print live exploration epsilon during training when available in BenchMARL internals.",
    )
    parser.add_argument(
        "--epsilon-log-interval-frames",
        type=int,
        default=1000,
        help="Minimum frame interval between epsilon prints when --print-epsilon is enabled.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    save_root = Path(args.save_folder)
    save_root.mkdir(parents=True, exist_ok=True)

    full_task_name = register_pacman_task()
    print(f"Registered task: {full_task_name}")

    task = PacmanTask.PACMAN.get_task(
        config={
            "max_cycles": 200,
            "number_ghosts": args.number_ghosts,
            "grid_size": args.grid_size,
        }
    )

    algorithm_config = _algorithm_config(args.algorithm)
    model_config = MlpConfig.get_from_yaml()
    model_config.num_feature_dims = 2
    experiment_config = ExperimentConfig.get_from_yaml()

    # Keep defaults deterministic and light for local experimentation.
    experiment_config.sampling_device = "cpu"
    experiment_config.train_device = "cpu"
    experiment_config.buffer_device = "cpu"
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

    experiment = Experiment(
        task=task,
        algorithm_config=algorithm_config,
        model_config=model_config,
        seed=args.seed,
        config=experiment_config,
    )

    _install_live_epsilon_logging(
        experiment=experiment,
        enabled=args.print_epsilon,
        log_every_frames=args.epsilon_log_interval_frames,
    )

    experiment.run()


if __name__ == "__main__":
    main()
