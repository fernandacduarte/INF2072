"""Deterministic, reward-aware evaluation reports for trained Pacman policies."""

from __future__ import annotations

import argparse
import csv
import random
import re
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any

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
from benchmarl_setup.device_utils import resolve_device
from benchmarl_setup.pacman_benchmarl_task import register_pacman_task
from custom_environment.eval import (
    _best_checkpoint_for_learner,
    _latest_checkpoint_for_learner,
    _resolve_checkpoint_view_size,
    _set_global_ghost_view_size,
    _unwrap_pacman_env,
)


ReportValue = float | int | str
EpisodeResult = dict[str, Any]


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
            if child.is_dir() and candidate_run_dirs(child, learner):
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

    selected = max(candidate_roots, key=lambda path: path.stat().st_mtime)
    print(
        "Auto-selected newest runs root for "
        f"learner={learner}: {selected} "
        f"(candidates: {', '.join(path.name for path in candidate_roots)})"
    )
    return selected


def _reward_runs_root(maze_runs_root: Path, reward_id: str) -> Path:
    reward_root = maze_runs_root / reward_id
    if reward_root.exists():
        return reward_root
    if reward_id == "current":
        return maze_runs_root  # Legacy layout from before reward strategies.
    raise FileNotFoundError(
        f"Reward strategy folder {reward_root} does not exist."
    )


def _scalars_dir(run_dir: Path) -> Path | None:
    nested = run_dir / run_dir.name / "scalars"
    if nested.exists():
        return nested
    direct = run_dir / "scalars"
    return direct if direct.exists() else None


def _tail_mean_reward(run_dir: Path, window: int = 20) -> float:
    scalars_dir = _scalars_dir(run_dir)
    if scalars_dir is None:
        return float("-inf")
    reward_file = scalars_dir / "collection_reward_reward_mean.csv"
    if not reward_file.exists():
        return float("-inf")

    values: list[float] = []
    with reward_file.open("r", newline="", encoding="utf-8") as handle:
        for row in csv.reader(handle):
            if len(row) < 2:
                continue
            try:
                values.append(float(row[1]))
            except ValueError:
                continue
    if not values:
        return float("-inf")
    return mean(values[-min(window, len(values)) :])


def _latest_checkpoint(run_dir: Path) -> Path | None:
    checkpoints_dir = run_dir / "checkpoints"
    if not checkpoints_dir.exists():
        return None
    checkpoints = sorted(
        checkpoints_dir.glob("checkpoint_*.pt"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return checkpoints[0] if checkpoints else None


def _run_dir_for_checkpoint(checkpoint: Path) -> Path:
    return checkpoint.parent.parent


def _extract_train_seed(run_dir: Path) -> int | None:
    hparams = run_dir / run_dir.name / "texts" / "hparams0.txt"
    if not hparams.exists():
        return None
    match = re.search(
        r"^seed:\s*(\d+)\s*$",
        hparams.read_text(encoding="utf-8", errors="ignore"),
        flags=re.MULTILINE,
    )
    return int(match.group(1)) if match else None


def _select_runs_by_train_seed(
    learner: str,
    runs_root: Path,
    train_seeds: set[int],
    checkpoint_select: str,
) -> list[tuple[int, Path, Path]]:
    selected: dict[int, tuple[float, Path, Path]] = {}
    for run_dir in candidate_run_dirs(runs_root, learner):
        checkpoint = _latest_checkpoint(run_dir)
        seed = _extract_train_seed(run_dir)
        if checkpoint is None or seed is None or seed not in train_seeds:
            continue
        score = (
            _tail_mean_reward(run_dir)
            if checkpoint_select == "best"
            else run_dir.stat().st_mtime
        )
        previous = selected.get(seed)
        if previous is None or score > previous[0]:
            selected[seed] = (score, run_dir, checkpoint)
    return [
        (seed, run_dir, checkpoint)
        for seed, (_, run_dir, checkpoint) in sorted(selected.items())
    ]


def _seed_episode(raw_env: Any, episode_seed: int) -> None:
    random.seed(episode_seed)
    np.random.seed(episode_seed)
    torch.manual_seed(episode_seed)
    if getattr(raw_env, "_rng", None) is None:
        raw_env._rng = random.Random(episode_seed)
    else:
        raw_env._rng.seed(episode_seed)


def _run_episode(
    experiment: Any,
    env: Any,
    raw_env: Any,
    episode_seed: int,
    max_steps: int,
) -> EpisodeResult:
    _seed_episode(raw_env, episode_seed)

    tensordict = env.reset()
    done = False
    steps = 0
    team_return = 0.0
    reward_breakdown: dict[str, float] = defaultdict(float)
    category_totals: dict[str, float] = defaultdict(float)
    visible_steps = 0
    newly_spotted_count = 0
    timeout = False
    pellet_win = False

    while not done and steps < max_steps:
        steps += 1
        tensordict = experiment.policy(tensordict)
        transition = env.step(tensordict)
        next_td = transition.get("next")

        reward_tensor = next_td.get(("ghost", "reward"))
        reward_values = reward_tensor.detach().cpu().reshape(-1).tolist()
        # Team reward is broadcast to every ghost; mean avoids N-ghost inflation.
        team_return += float(np.mean(reward_values)) if reward_values else 0.0

        for key, value in raw_env.last_team_reward_breakdown.items():
            reward_breakdown[key] += float(value)
        for key, value in raw_env.last_reward_category_totals.items():
            category_totals[key] += float(value)

        context = raw_env.last_reward_context
        if context is not None:
            visible_steps += int(context.pacman_visible)
            timeout = timeout or bool(context.timeout_happened)
            pellet_win = pellet_win or bool(context.pacman_win_happened)
        if raw_env.last_team_reward_breakdown.get("newly_spotted", 0.0) != 0.0:
            newly_spotted_count += 1

        done = bool(next_td.get("done").item())
        tensordict = step_mdp(
            transition,
            reward_keys=env.reward_keys,
            action_keys=env.action_keys,
            done_keys=env.done_keys,
        )

    captured = bool(raw_env._is_capture_state())
    # A simultaneous final-step pellet clear is classified as a pellet win, not a timeout.
    timeout = timeout and not pellet_win
    evaluation_cutoff = not done and not captured and not timeout and not pellet_win
    return {
        "captured": captured,
        "timeout": timeout,
        "pellet_win": pellet_win,
        "evaluation_cutoff": evaluation_cutoff,
        "steps": steps,
        "team_return": team_return,
        "reward_breakdown": dict(reward_breakdown),
        "category_totals": dict(category_totals),
        "visible_steps": visible_steps,
        "newly_spotted_count": newly_spotted_count,
    }


def _safe_mean(values: list[float]) -> float:
    clean = [value for value in values if value == value]
    return mean(clean) if clean else float("nan")


def _safe_std(values: list[float]) -> float:
    clean = [value for value in values if value == value]
    return stdev(clean) if len(clean) >= 2 else float("nan")


def _aggregate_episodes(episodes: list[EpisodeResult]) -> dict[str, float | int]:
    count = len(episodes)
    captures = [episode for episode in episodes if episode["captured"]]
    steps_to_capture = [float(episode["steps"]) for episode in captures]
    returns = [float(episode["team_return"]) for episode in episodes]
    all_steps = [float(episode["steps"]) for episode in episodes]

    visible_fractions: list[float] = []
    newly_spotted_counts: list[float] = []
    shaping_returns: list[float] = []
    terminal_returns: list[float] = []
    for episode in episodes:
        steps = max(int(episode["steps"]), 1)
        visible_fractions.append(float(episode["visible_steps"]) / float(steps))
        newly_spotted_counts.append(float(episode["newly_spotted_count"]))
        categories = episode["category_totals"]
        shaping_returns.append(float(categories.get("shaping", 0.0)))
        terminal_returns.append(float(categories.get("terminal", 0.0)))

    capture_rate = len(captures) / count if count else float("nan")
    timeout_rate = (
        sum(bool(episode["timeout"]) for episode in episodes) / count
        if count
        else float("nan")
    )
    pellet_win_rate = (
        sum(bool(episode["pellet_win"]) for episode in episodes) / count
        if count
        else float("nan")
    )
    cutoff_rate = (
        sum(bool(episode["evaluation_cutoff"]) for episode in episodes) / count
        if count
        else float("nan")
    )

    return {
        "episodes": count,
        "ghost_win_rate": capture_rate,
        "pacman_win_rate": timeout_rate + pellet_win_rate,
        "mean_episode_return": _safe_mean(returns),
        "std_episode_return": float(np.std(returns)) if returns else float("nan"),
        "median_episode_return": median(returns) if returns else float("nan"),
        "mean_steps": _safe_mean(all_steps),
        # Capture rate is the fraction of episodes in which a ghost caught Pacman.
        "capture_rate": capture_rate,
        # Timeout rate is the fraction ending because Pacman survived the time limit.
        "timeout_rate": timeout_rate,
        # Pellet-win rate is the fraction ending because Pacman cleared all pellets.
        "pellet_win_rate": pellet_win_rate,
        # Evaluation-cutoff rate counts episodes stopped by this CLI's step budget.
        "evaluation_cutoff_rate": cutoff_rate,
        # Mean steps to capture measures capture speed over successful episodes only.
        "mean_steps_to_capture": _safe_mean(steps_to_capture),
        # Median steps to capture is the robust midpoint capture time.
        "median_steps_to_capture": (
            median(steps_to_capture) if steps_to_capture else float("nan")
        ),
        # Visible-step fraction measures how consistently ghosts tracked Pacman.
        "frac_steps_visible": _safe_mean(visible_fractions),
        # Newly-spotted count measures average reacquisitions of Pacman's location.
        "mean_newly_spotted_count": _safe_mean(newly_spotted_counts),
        # Shaping return is the mean non-terminal reward contribution per episode.
        "mean_shaping_return": _safe_mean(shaping_returns),
        # Terminal return is the mean win/loss reward contribution per episode.
        "mean_terminal_return": _safe_mean(terminal_returns),
    }


def _evaluate_checkpoint(
    checkpoint_path: Path,
    learner: str,
    episodes: int,
    max_steps: int,
    seed_base: int,
    ghost_view_size: int | None,
    verbose: bool,
    device: str,
    expected_reward_id: str | None,
) -> tuple[dict[str, ReportValue], list[EpisodeResult]]:
    resolved_view_size = _resolve_checkpoint_view_size(checkpoint_path, ghost_view_size)
    if resolved_view_size is not None:
        _set_global_ghost_view_size(resolved_view_size)

    experiment = Experiment.reload_from_file(
        str(checkpoint_path),
        experiment_patch={
            "evaluation": False,
            "render": False,
            "loggers": [],
            "sampling_device": device,
            "train_device": device,
            "buffer_device": device,
        },
    )
    env = experiment.test_env
    raw_env = _unwrap_pacman_env(env)
    raw_env.shared_memory_in_observation_enabled = False
    raw_env.render_mode = None
    actual_reward_id = str(getattr(raw_env, "reward_strategy_id", "current"))
    actual_reward_class = str(getattr(raw_env, "reward_strategy_class", ""))

    if expected_reward_id is not None and actual_reward_id != expected_reward_id:
        raw_env.close()
        experiment.close()
        raise ValueError(
            f"Checkpoint reward mismatch for {checkpoint_path}: expected "
            f"{expected_reward_id!r}, restored {actual_reward_id!r}."
        )

    episode_results: list[EpisodeResult] = []
    try:
        with torch.no_grad(), set_exploration_type(ExplorationType.DETERMINISTIC):
            for episode_index in range(episodes):
                episode_result = _run_episode(
                    experiment=experiment,
                    env=env,
                    raw_env=raw_env,
                    episode_seed=seed_base + episode_index,
                    max_steps=max_steps,
                )
                episode_results.append(episode_result)
                if verbose:
                    if episode_result["captured"]:
                        outcome = "ghost_win"
                    elif episode_result["timeout"]:
                        outcome = "pacman_timeout_win"
                    elif episode_result["pellet_win"]:
                        outcome = "pacman_pellet_win"
                    else:
                        outcome = "evaluation_cutoff"
                    print(
                        f"Episode {episode_index + 1}/{episodes} | learner={learner} "
                        f"| return={episode_result['team_return']:.3f} "
                        f"| steps={episode_result['steps']} | outcome={outcome}"
                    )
    finally:
        raw_env.close()
        experiment.close()

    summary: dict[str, ReportValue] = {
        # Reward ID identifies the reward implementation used by the checkpoint.
        "reward_id": actual_reward_id,
        # Reward class records the import path restored from the checkpoint.
        "reward_class": actual_reward_class,
        "learner": learner,
        "checkpoint_path": str(checkpoint_path),
        **_aggregate_episodes(episode_results),
    }
    return summary, episode_results


def _build_variant_summary(
    rows: list[dict[str, ReportValue]],
    pooled: dict[tuple[str, str], list[EpisodeResult]],
) -> list[dict[str, ReportValue]]:
    rows_by_variant: dict[tuple[str, str], list[dict[str, ReportValue]]] = defaultdict(list)
    for row in rows:
        rows_by_variant[(str(row["reward_id"]), str(row["learner"]))].append(row)

    result: list[dict[str, ReportValue]] = []
    for reward_id, learner in sorted(rows_by_variant):
        variant_rows = rows_by_variant[(reward_id, learner)]
        capture_rates = [float(row["capture_rate"]) for row in variant_rows]
        capture_times = [float(row["mean_steps_to_capture"]) for row in variant_rows]
        pooled_stats = _aggregate_episodes(pooled[(reward_id, learner)])
        result.append(
            {
                "reward_id": reward_id,
                "reward_class": str(variant_rows[0].get("reward_class", "")),
                "learner": learner,
                # Seed count is the number of independently trained policies compared.
                "n_seeds": len(variant_rows),
                # Total episodes is the pooled evaluation sample size for this variant.
                "n_episodes_total": int(pooled_stats["episodes"]),
                # Capture-rate mean averages policy success rates across training seeds.
                "capture_rate_mean": _safe_mean(capture_rates),
                # Capture-rate std measures policy variability across training seeds.
                "capture_rate_std": _safe_std(capture_rates),
                # Time-to-capture mean averages successful capture speed across seeds.
                "time_to_capture_mean": _safe_mean(capture_times),
                # Time-to-capture std measures capture-speed variability across seeds.
                "time_to_capture_std": _safe_std(capture_times),
                # Capturing-seed count shows how many trained policies captured at least once.
                "n_capturing_seeds": sum(value == value for value in capture_times),
                # Timeout rate is the pooled fraction of episodes won by surviving the timer.
                "timeout_rate": float(pooled_stats["timeout_rate"]),
                # Pellet-win rate is the pooled fraction won by clearing all pellets.
                "pellet_win_rate": float(pooled_stats["pellet_win_rate"]),
                # Cutoff rate is the pooled fraction stopped by the evaluation step budget.
                "evaluation_cutoff_rate": float(pooled_stats["evaluation_cutoff_rate"]),
                # Visible-step fraction is pooled tracking consistency across episodes.
                "frac_steps_visible": float(pooled_stats["frac_steps_visible"]),
                # Newly-spotted count is pooled average Pacman-location reacquisition.
                "mean_newly_spotted_count": float(
                    pooled_stats["mean_newly_spotted_count"]
                ),
                # Mean return is diagnostic because reward scales can differ by strategy.
                "mean_episode_return": float(pooled_stats["mean_episode_return"]),
                # Shaping return is the pooled mean non-terminal reward contribution.
                "mean_shaping_return": float(pooled_stats["mean_shaping_return"]),
                # Terminal return is the pooled mean terminal reward contribution.
                "mean_terminal_return": float(pooled_stats["mean_terminal_return"]),
            }
        )
    return result


REPORT_FIELDS = [
    "reward_id",
    "reward_class",
    "learner",
    "train_seed",
    "run_dir",
    "checkpoint_path",
    "episodes",
    "ghost_win_rate",
    "pacman_win_rate",
    "mean_episode_return",
    "std_episode_return",
    "median_episode_return",
    "mean_steps",
    "capture_rate",
    "timeout_rate",
    "pellet_win_rate",
    "evaluation_cutoff_rate",
    "mean_steps_to_capture",
    "median_steps_to_capture",
    "frac_steps_visible",
    "mean_newly_spotted_count",
    "mean_shaping_return",
    "mean_terminal_return",
]

VARIANT_FIELDS = [
    "reward_id",
    "reward_class",
    "learner",
    "n_seeds",
    "n_episodes_total",
    "capture_rate_mean",
    "capture_rate_std",
    "time_to_capture_mean",
    "time_to_capture_std",
    "n_capturing_seeds",
    "timeout_rate",
    "pellet_win_rate",
    "evaluation_cutoff_rate",
    "frac_steps_visible",
    "mean_newly_spotted_count",
    "mean_episode_return",
    "mean_shaping_return",
    "mean_terminal_return",
]


def _write_csv(rows: list[dict[str, ReportValue]], path: Path, fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved report: {path}")


def _print_summary(rows: list[dict[str, ReportValue]]) -> None:
    print("\nDeterministic evaluation summary:")
    for row in rows:
        capture = float(row["capture_rate_mean"])
        capture_std = float(row["capture_rate_std"])
        capture_text = f"{capture:.3f}"
        if capture_std == capture_std:
            capture_text += f"±{capture_std:.3f}"
        capture_time = float(row["time_to_capture_mean"])
        capture_time_text = "nan" if capture_time != capture_time else f"{capture_time:.1f}"
        print(
            f"- {row['reward_id']}/{row['learner']}: seeds={row['n_seeds']} "
            f"episodes={row['n_episodes_total']} capture_rate={capture_text} "
            f"time_to_capture={capture_time_text} "
            f"visible={float(row['frac_steps_visible']):.3f} "
            f"mean_return={float(row['mean_episode_return']):.3f}"
        )


def _evaluate_direct(args: argparse.Namespace, device: str) -> tuple[
    list[dict[str, ReportValue]],
    dict[tuple[str, str], list[EpisodeResult]],
    Path,
]:
    algorithms = _resolve_algorithms(args)
    if args.checkpoint is not None and len(algorithms) != 1:
        raise ValueError("--checkpoint can only be used with a single learner (--learner).")

    maze_runs_root = runs_root_for_maze(args.runs_root, args.maze)
    reward_runs_root = (
        None
        if args.checkpoint is not None
        else _reward_runs_root(maze_runs_root, args.reward_id)
    )
    rows: list[dict[str, ReportValue]] = []
    pooled: dict[tuple[str, str], list[EpisodeResult]] = defaultdict(list)

    for learner in algorithms:
        selections: list[tuple[int | None, Path, Path]]
        if args.checkpoint is not None:
            run_dir = _run_dir_for_checkpoint(args.checkpoint)
            selections = [(_extract_train_seed(run_dir), run_dir, args.checkpoint)]
        else:
            assert reward_runs_root is not None
            learner_runs_root = _resolve_runs_root_for_learner(
                base_runs_root=reward_runs_root,
                learner=learner,
                device_label_selector=args.device_label,
            )
            if args.train_seeds:
                selections = _select_runs_by_train_seed(
                    learner=learner,
                    runs_root=learner_runs_root,
                    train_seeds=args.train_seeds,
                    checkpoint_select=args.checkpoint_select,
                )
                missing = args.train_seeds - {seed for seed, _, _ in selections}
                if missing:
                    raise FileNotFoundError(
                        f"No checkpoints found for learner={learner}, "
                        f"training seeds={sorted(missing)}."
                    )
            else:
                checkpoint = _select_checkpoint(
                    learner=learner,
                    runs_root=learner_runs_root,
                    checkpoint_select=args.checkpoint_select,
                    explicit_checkpoint=None,
                )
                run_dir = _run_dir_for_checkpoint(checkpoint)
                selections = [(_extract_train_seed(run_dir), run_dir, checkpoint)]

        for train_seed, run_dir, checkpoint in selections:
            print(f"Evaluating learner={learner} checkpoint={checkpoint}")
            row, episode_results = _evaluate_checkpoint(
                checkpoint_path=checkpoint,
                learner=learner,
                episodes=args.episodes,
                max_steps=args.max_steps,
                seed_base=args.seed_base,
                ghost_view_size=args.ghost_view_size,
                verbose=args.verbose,
                device=device,
                expected_reward_id=args.reward_id,
            )
            row["train_seed"] = "" if train_seed is None else train_seed
            row["run_dir"] = run_dir.name
            rows.append(row)
            pooled[(str(row["reward_id"]), learner)].extend(episode_results)
    return rows, pooled, maze_runs_root


def _evaluate_jobs(args: argparse.Namespace, device: str) -> tuple[
    list[dict[str, ReportValue]],
    dict[tuple[str, str], list[EpisodeResult]],
]:
    jobs: list[dict[str, str]] = []
    for jobs_path in args.jobs_path:
        if not jobs_path.exists():
            raise FileNotFoundError(f"Benchmark jobs CSV not found: {jobs_path}")
        with jobs_path.open("r", newline="", encoding="utf-8") as handle:
            jobs.extend(csv.DictReader(handle))

    allowed_algorithms = set(_resolve_algorithms(args))
    rows: list[dict[str, ReportValue]] = []
    pooled: dict[tuple[str, str], list[EpisodeResult]] = defaultdict(list)
    seen: set[tuple[str, str, str, str]] = set()

    for job in jobs:
        if (job.get("returncode") or "1").strip() != "0":
            continue
        reward_id = (job.get("reward_id") or "current").strip()
        learner = normalize_algorithm((job.get("algorithm") or "").strip())
        if learner not in allowed_algorithms:
            continue
        train_seed = (job.get("seed") or "").strip()
        if args.train_seeds and (
            not train_seed or int(train_seed) not in args.train_seeds
        ):
            continue
        run_dir_name = (job.get("run_dir") or "").strip()
        save_folder_text = (job.get("save_folder") or "").strip()
        key = (reward_id, learner, train_seed, run_dir_name)
        if not run_dir_name or not save_folder_text or key in seen:
            continue
        seen.add(key)

        run_dir = Path(save_folder_text) / run_dir_name
        checkpoint = _latest_checkpoint(run_dir)
        if checkpoint is None:
            raise FileNotFoundError(f"No final checkpoint found for benchmark job: {run_dir}")

        print(
            f"Evaluating reward={reward_id} learner={learner} "
            f"seed={train_seed or '?'} checkpoint={checkpoint}"
        )
        row, episode_results = _evaluate_checkpoint(
            checkpoint_path=checkpoint,
            learner=learner,
            episodes=args.episodes,
            max_steps=args.max_steps,
            seed_base=args.seed_base,
            ghost_view_size=args.ghost_view_size,
            verbose=args.verbose,
            device=device,
            expected_reward_id=reward_id,
        )
        row["train_seed"] = train_seed
        row["run_dir"] = run_dir_name
        rows.append(row)
        pooled[(reward_id, learner)].extend(episode_results)

    return rows, pooled


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate trained checkpoints with reward-aware objective metrics."
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
        default="default",
        choices=SUPPORTED_MAZES,
        help="Maze subfolder under --runs-root.",
    )
    parser.add_argument(
        "--reward-id",
        default="current",
        help="Reward strategy folder used for checkpoint discovery.",
    )
    parser.add_argument(
        "--device-label",
        default="auto",
        help="Stored-run device folder (auto, cpu, cuda, cuda_0, and similar).",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        help="Compute device used for evaluation.",
    )
    parser.add_argument(
        "--allow-cpu-fallback",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Fall back to CPU when the requested accelerator is unavailable.",
    )
    parser.add_argument(
        "--jobs-path",
        type=Path,
        nargs="+",
        default=None,
        help="Benchmark jobs CSV file(s) whose exact successful runs should be evaluated.",
    )
    parser.add_argument(
        "--train-seeds",
        default="",
        help="Optional comma-separated training seeds; selects one checkpoint per seed.",
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
        help="Optional explicit checkpoint path. Only valid with one learner.",
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
        "--eval-seed-base",
        dest="seed_base",
        type=int,
        default=0,
        help="First deterministic evaluation seed, shared across all checkpoints.",
    )
    parser.add_argument(
        "--ghost-view-size",
        type=int,
        default=None,
        help="Odd local observation width/height for legacy checkpoints.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional detailed CSV output path.",
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
        algorithms = [
            normalize_algorithm(item)
            for item in args.algorithms.split(",")
            if item.strip()
        ]
    if not algorithms:
        raise ValueError("At least one learner must be provided.")
    invalid = [name for name in algorithms if name not in SUPPORTED_ALGORITHMS]
    if invalid:
        raise ValueError(
            f"Unsupported learner(s): {invalid}. Allowed: {list(SUPPORTED_ALGORITHMS)}"
        )
    return algorithms


def _parse_train_seeds(value: str) -> set[int]:
    return {int(item) for item in value.split(",") if item.strip()}


def main() -> None:
    args = parse_args()
    if args.episodes < 1:
        raise ValueError("--episodes must be >= 1")
    if args.max_steps < 1:
        raise ValueError("--max-steps must be >= 1")
    if args.jobs_path is not None and args.checkpoint is not None:
        raise ValueError("--checkpoint cannot be combined with --jobs-path.")
    args.train_seeds = _parse_train_seeds(args.train_seeds)
    if args.checkpoint is not None and args.train_seeds:
        raise ValueError("--train-seeds cannot be combined with --checkpoint.")

    resolved_device, reason = resolve_device(
        requested_device=args.device,
        allow_cpu_fallback=args.allow_cpu_fallback,
    )
    print(f"Eval device | requested={args.device} resolved={resolved_device} | {reason}")
    register_pacman_task()

    if args.jobs_path is not None:
        rows, pooled = _evaluate_jobs(args, resolved_device)
        default_out = PROJECT_ROOT / "benchmarl_setup" / "runs" / "evaluation_report.csv"
    else:
        rows, pooled, maze_runs_root = _evaluate_direct(args, resolved_device)
        default_out = maze_runs_root / "evaluation_report.csv"

    if not rows:
        raise FileNotFoundError("No matching successful checkpoints were found to evaluate.")

    output_path = args.out or default_out
    variant_rows = _build_variant_summary(rows, pooled)
    _write_csv(rows, output_path, REPORT_FIELDS)
    variant_path = output_path.with_name(
        f"{output_path.stem}_by_variant{output_path.suffix or '.csv'}"
    )
    _write_csv(variant_rows, variant_path, VARIANT_FIELDS)
    _print_summary(variant_rows)


if __name__ == "__main__":
    main()
