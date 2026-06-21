"""Headless batch evaluation for the Pacman MARL reward study.

Loads each algorithm's trained checkpoint(s) and rolls out N deterministic
episodes on a FIXED eval-seed sequence, so every reward variant is judged on the
same Pacman random streams (a paired comparison enabled by the env-owned RNG).

Why this exists: the only thing BenchMARL logs is *reward*, but reward stops
being comparable the moment a reward term is edited. This harness measures the
TRUE objective instead:

  - capture_rate          PRIMARY decision metric (% episodes ending in capture)
  - time-to-capture       efficiency tiebreaker (steps in successful episodes)
  - return / breakdown    DIAGNOSTIC ONLY (the breadcrumb-farming fingerprint)

It mirrors the rollout machinery in custom_environment/eval.py but aggregates
over many episodes instead of rendering one. Capture vs timeout is read straight
from the unwrapped env (capture = `_is_capture_state()`, timeout = step budget
exhausted), matching eval.py's `_build_final_result`.
"""

import argparse
import csv
import random
import re
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean, median, stdev

import torch

from benchmarl.experiment import Experiment
from torchrl.envs.utils import ExplorationType, set_exploration_type, step_mdp

# Ensure workspace root is importable when running this file by path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from benchmarl_setup.algorithm_utils import (
    SUPPORTED_ALGORITHMS,
    candidate_run_dirs,
    normalize_algorithm,
)
from benchmarl_setup.device_utils import resolve_device
from benchmarl_setup.pacman_benchmarl_task import register_pacman_task


# --- Run/checkpoint discovery (mirrors small helpers in eval.py / summarize) ---

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
    with reward_file.open("r", newline="") as f:
        for row in csv.reader(f):
            if len(row) < 2:
                continue
            try:
                values.append(float(row[1]))
            except ValueError:
                continue
    if not values:
        return float("-inf")
    n = min(window, len(values))
    return sum(values[-n:]) / float(n)


def _latest_checkpoint(run_dir: Path) -> Path | None:
    checkpoints_dir = run_dir / "checkpoints"
    if not checkpoints_dir.exists():
        return None
    files = sorted(
        checkpoints_dir.glob("checkpoint_*.pt"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return files[0] if files else None


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


def _select_runs(
    algorithm: str,
    runs_root: Path,
    train_seeds: set[int] | None,
    checkpoint_select: str,
) -> list[tuple[int | None, Path, Path]]:
    """Pick one checkpoint per training seed (best tail reward, or latest)."""
    by_seed: dict[int | None, tuple[float, Path, Path]] = {}
    for run_dir in candidate_run_dirs(runs_root, algorithm):
        checkpoint = _latest_checkpoint(run_dir)
        if checkpoint is None:
            continue
        seed = _extract_train_seed(run_dir)
        if train_seeds is not None and seed not in train_seeds:
            continue
        score = (
            _tail_mean_reward(run_dir)
            if checkpoint_select == "best"
            else run_dir.stat().st_mtime
        )
        previous = by_seed.get(seed)
        if previous is None or score > previous[0]:
            by_seed[seed] = (score, run_dir, checkpoint)
    return [
        (seed, run_dir, checkpoint)
        for seed, (_, run_dir, checkpoint) in sorted(
            by_seed.items(), key=lambda kv: (kv[0] is None, kv[0])
        )
    ]


# --- Single-episode rollout and aggregation ---

def _run_episode(experiment, env, raw_env, eval_seed: int, max_steps: int) -> dict:
    # Pin Pacman's random walk for this episode so every variant sees the same
    # stream (paired comparison). reset() below carries no seed, so this sticks.
    if getattr(raw_env, "_rng", None) is None:
        raw_env._rng = random.Random(eval_seed)
    else:
        raw_env._rng.seed(eval_seed)

    td = env.reset()
    steps = 0
    team_return = 0.0
    breakdown: dict[str, float] = defaultdict(float)
    category_totals: dict[str, float] = defaultdict(float)
    visible_steps = 0
    newly_spotted_count = 0
    done = False

    while not done and steps < max_steps:
        steps += 1
        td = experiment.policy(td)
        transition = env.step(td)
        next_td = transition.get("next")

        # Team reward is broadcast identically to each ghost; mean de-duplicates.
        reward_tensor = next_td.get(("ghost", "reward"))
        team_return += float(reward_tensor.reshape(-1).mean().item())

        for key, value in raw_env.last_team_reward_breakdown.items():
            breakdown[key] += float(value)
        for key, value in raw_env.last_reward_category_totals.items():
            category_totals[key] += float(value)
        context = raw_env.last_reward_context
        if context is not None and context.pacman_visible:
            visible_steps += 1
        if raw_env.last_team_reward_breakdown.get("newly_spotted", 0.0) != 0.0:
            newly_spotted_count += 1

        done = bool(next_td.get("done").item())
        td = step_mdp(
            transition,
            reward_keys=env.reward_keys,
            action_keys=env.action_keys,
            done_keys=env.done_keys,
        )

    captured = bool(raw_env._is_capture_state())
    timeout = (not captured) and raw_env.step_count >= raw_env.max_steps
    # team_return already includes all terminal terms. Category totals come from
    # the selected strategy, so evaluation never infers semantics from magnitudes.

    return {
        "captured": captured,
        "timeout": timeout,
        "steps": steps,
        "team_return": team_return,
        "breakdown": dict(breakdown),
        "category_totals": dict(category_totals),
        "visible_steps": visible_steps,
        "newly_spotted_count": newly_spotted_count,
    }


def _aggregate(episodes: list[dict]) -> dict:
    n = len(episodes)
    captures = [e for e in episodes if e["captured"]]
    steps_to_capture = [e["steps"] for e in captures]

    frac_visible, newly_counts, shaping_returns, terminal_returns = [], [], [], []
    for e in episodes:
        steps = max(e["steps"], 1)
        frac_visible.append(float(e.get("visible_steps", 0)) / float(steps))
        newly_counts.append(float(e.get("newly_spotted_count", 0)))
        categories = e.get("category_totals", {})
        terminal_returns.append(float(categories.get("terminal", 0.0)))
        shaping_returns.append(float(categories.get("shaping", 0.0)))

    def _mean(xs):
        return mean(xs) if xs else float("nan")

    return {
        "n_episodes": n,
        "capture_rate": (len(captures) / n) if n else float("nan"),
        "mean_steps_to_capture": _mean(steps_to_capture),
        "median_steps_to_capture": median(steps_to_capture) if steps_to_capture else float("nan"),
        "mean_steps_all": _mean([e["steps"] for e in episodes]),
        "mean_return": _mean([e["team_return"] for e in episodes]),
        "frac_steps_visible": _mean(frac_visible),
        "mean_newly_spotted_count": _mean(newly_counts),
        "mean_shaping_return": _mean(shaping_returns),
        "mean_terminal_return": _mean(terminal_returns),
    }


def evaluate(
    algorithms: list[str],
    runs_root: Path,
    episodes: int,
    eval_seed_base: int,
    train_seeds: set[int] | None,
    checkpoint_select: str,
    max_steps: int,
    device: str,
    out: Path,
) -> list[dict]:
    rows: list[dict] = []
    pooled: dict[tuple[str, str], list[dict]] = defaultdict(list)

    for algorithm in algorithms:
        selected = _select_runs(algorithm, runs_root, train_seeds, checkpoint_select)
        if not selected:
            print(f"[{algorithm}] no checkpoints found under {runs_root} -- skipping.")
            continue

        for train_seed, run_dir, checkpoint in selected:
            experiment = Experiment.reload_from_file(
                str(checkpoint),
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
            raw_env.render_mode = None

            episode_results: list[dict] = []
            try:
                with torch.no_grad(), set_exploration_type(ExplorationType.DETERMINISTIC):
                    for i in range(episodes):
                        episode_results.append(
                            _run_episode(experiment, env, raw_env, eval_seed_base + i, max_steps)
                        )
            finally:
                raw_env.close()
                experiment.close()

            stats = _aggregate(episode_results)
            pooled[("current", algorithm)].extend(episode_results)
            row = {
                "reward_id": "current",
                "reward_class": "",
                "algorithm": algorithm,
                "train_seed": "" if train_seed is None else str(train_seed),
                "run_dir": run_dir.name,
                "checkpoint": checkpoint.name,
                **{k: stats[k] for k in stats},
            }
            rows.append(row)
            print(
                f"[{algorithm}] seed={row['train_seed'] or '?'} "
                f"capture_rate={stats['capture_rate']:.3f} "
                f"mean_steps_to_capture={stats['mean_steps_to_capture']:.1f} "
                f"frac_visible={stats['frac_steps_visible']:.3f} "
                f"newly_spotted={stats['mean_newly_spotted_count']:.2f} "
                f"(n={stats['n_episodes']})"
            )

    by_algorithm = _by_algorithm_summary(rows, pooled)
    _write_csv(rows, out)
    _write_algorithm_csv(by_algorithm, out.with_name(f"{out.stem}_by_algorithm{out.suffix}"))
    _print_summary(by_algorithm)
    return rows


def evaluate_jobs(
    jobs_paths: list[Path],
    episodes: int,
    eval_seed_base: int,
    max_steps: int,
    device: str,
    out: Path,
) -> list[dict]:
    """Evaluate the exact final checkpoint recorded for each successful matrix job."""

    jobs: list[dict] = []
    for jobs_path in jobs_paths:
        if not jobs_path.exists():
            raise FileNotFoundError(f"Benchmark jobs CSV not found: {jobs_path}")
        with jobs_path.open("r", newline="", encoding="utf-8") as handle:
            jobs.extend(csv.DictReader(handle))

    rows: list[dict] = []
    pooled: dict[tuple[str, str], list[dict]] = defaultdict(list)
    seen: set[tuple[str, str, str, str]] = set()
    for job in jobs:
        if (job.get("returncode") or "1").strip() != "0":
            continue
        reward_id = (job.get("reward_id") or "current").strip()
        reward_class = (job.get("reward_class") or "").strip()
        algorithm = normalize_algorithm((job.get("algorithm") or "").strip())
        train_seed = (job.get("seed") or "").strip()
        run_dir_name = (job.get("run_dir") or "").strip()
        save_folder = Path((job.get("save_folder") or "").strip())
        key = (reward_id, algorithm, train_seed, run_dir_name)
        if not run_dir_name or key in seen:
            continue
        seen.add(key)

        run_dir = save_folder / run_dir_name
        checkpoint = _latest_checkpoint(run_dir)
        if checkpoint is None:
            raise FileNotFoundError(f"No final checkpoint found for benchmark job: {run_dir}")

        experiment = Experiment.reload_from_file(
            str(checkpoint),
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
        raw_env.render_mode = None
        actual_reward_id = getattr(raw_env, "reward_strategy_id", "current")
        if actual_reward_id != reward_id:
            raw_env.close()
            experiment.close()
            raise ValueError(
                f"Checkpoint reward mismatch for {run_dir}: jobs CSV says "
                f"{reward_id!r}, checkpoint restored {actual_reward_id!r}."
            )

        episode_results: list[dict] = []
        try:
            with torch.no_grad(), set_exploration_type(ExplorationType.DETERMINISTIC):
                for index in range(episodes):
                    episode_results.append(
                        _run_episode(
                            experiment,
                            env,
                            raw_env,
                            eval_seed_base + index,
                            max_steps,
                        )
                    )
        finally:
            raw_env.close()
            experiment.close()

        stats = _aggregate(episode_results)
        pooled[(reward_id, algorithm)].extend(episode_results)
        rows.append(
            {
                "reward_id": reward_id,
                "reward_class": reward_class,
                "algorithm": algorithm,
                "train_seed": train_seed,
                "run_dir": run_dir_name,
                "checkpoint": checkpoint.name,
                **stats,
            }
        )
        print(
            f"[{reward_id}/{algorithm}] seed={train_seed or '?'} "
            f"capture_rate={stats['capture_rate']:.3f} "
            f"mean_steps_to_capture={stats['mean_steps_to_capture']:.1f} "
            f"(n={stats['n_episodes']})"
        )

    summary = _by_algorithm_summary(rows, pooled)
    _write_csv(rows, out)
    _write_algorithm_csv(summary, out.with_name(f"{out.stem}_by_variant{out.suffix}"))
    _print_summary(summary)
    return rows


def _write_csv(rows: list[dict], out: Path) -> None:
    fieldnames = [
        "reward_id", "reward_class", "algorithm", "train_seed", "run_dir", "checkpoint", "n_episodes",
        "capture_rate", "mean_steps_to_capture", "median_steps_to_capture",
        "mean_steps_all", "mean_return", "frac_steps_visible",
        "mean_newly_spotted_count", "mean_shaping_return", "mean_terminal_return",
    ]
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            formatted = dict(row)
            for key, value in row.items():
                if isinstance(value, float):
                    formatted[key] = f"{value:.6f}"
            writer.writerow(formatted)
    print(f"\nWrote {len(rows)} rows to: {out}")


def _safe_mean(values: list[float]) -> float:
    clean = [v for v in values if v == v]  # drop NaN
    return mean(clean) if clean else float("nan")


def _safe_std(values: list[float]) -> float:
    # Sample std (ddof=1) across training seeds -- the genuine unit of variation.
    clean = [v for v in values if v == v]  # drop NaN (seeds with no captures)
    return stdev(clean) if len(clean) >= 2 else float("nan")


def _fmt_pm(mean_value: float, std_value: float, precision: int) -> str:
    if mean_value != mean_value:
        return "nan"
    if std_value != std_value:
        return f"{mean_value:.{precision}f}±  -  "
    return f"{mean_value:.{precision}f}±{std_value:.{precision}f}"


def _by_algorithm_summary(
    rows: list[dict], pooled: dict[tuple[str, str], list[dict]]
) -> list[dict]:
    """Aggregate per-seed rows into one record per algorithm.

    Decision metrics (capture rate, time-to-capture) get mean +/- sample std
    ACROSS training seeds: the seeds are the genuine unit of variation, so
    pooling all 500 episodes would understate the uncertainty (episodes within a
    seed share one policy and are correlated). Diagnostics keep pooled estimates.
    """
    rows_by_algorithm: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        rows_by_algorithm[(row["reward_id"], row["algorithm"])].append(row)

    summary: list[dict] = []
    for reward_id, algorithm in sorted(rows_by_algorithm):
        algo_rows = rows_by_algorithm[(reward_id, algorithm)]
        if not algo_rows:
            continue
        capture_rates = [float(r["capture_rate"]) for r in algo_rows]
        steps_to_capture = [float(r["mean_steps_to_capture"]) for r in algo_rows]
        pooled_stats = _aggregate(pooled.get((reward_id, algorithm), []))
        summary.append(
            {
                "reward_id": reward_id,
                "algorithm": algorithm,
                "n_seeds": len(algo_rows),
                "n_episodes_total": pooled_stats["n_episodes"],
                "capture_rate_mean": _safe_mean(capture_rates),
                "capture_rate_std": _safe_std(capture_rates),
                "time_to_capture_mean": _safe_mean(steps_to_capture),
                "time_to_capture_std": _safe_std(steps_to_capture),
                "n_capturing_seeds": sum(1 for v in steps_to_capture if v == v),
                "frac_steps_visible": pooled_stats["frac_steps_visible"],
                "mean_newly_spotted_count": pooled_stats["mean_newly_spotted_count"],
                "mean_return": pooled_stats["mean_return"],
            }
        )
    return summary


def _write_algorithm_csv(summary: list[dict], path: Path) -> None:
    fieldnames = [
        "reward_id", "algorithm", "n_seeds", "n_episodes_total",
        "capture_rate_mean", "capture_rate_std",
        "time_to_capture_mean", "time_to_capture_std", "n_capturing_seeds",
        "frac_steps_visible", "mean_newly_spotted_count", "mean_return",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for record in summary:
            formatted = dict(record)
            for key, value in record.items():
                if isinstance(value, float):
                    formatted[key] = f"{value:.6f}"
            writer.writerow(formatted)
    print(f"Wrote {len(summary)} algorithm rows to: {path}")


def _print_summary(summary: list[dict]) -> None:
    print(
        "\nAcross-seed summary (capture_rate is the decision metric; "
        "mean ± sample std over training seeds):"
    )
    print(
        f"{'reward':<16} {'algorithm':<12} {'seeds':>5} {'eps':>5} {'capture_rate':>15} "
        f"{'time_to_capture':>17} {'visible%':>9} {'newly#':>7} {'return':>9}"
    )
    for record in summary:
        capture = _fmt_pm(record["capture_rate_mean"], record["capture_rate_std"], 3)
        t2cap = _fmt_pm(record["time_to_capture_mean"], record["time_to_capture_std"], 1)
        print(
            f"{record['reward_id']:<16} {record['algorithm']:<12} {record['n_seeds']:>5d} {record['n_episodes_total']:>5d} "
            f"{capture:>15} {t2cap:>17} "
            f"{record['frac_steps_visible']*100:>8.1f}% {record['mean_newly_spotted_count']:>7.2f} "
            f"{record['mean_return']:>9.2f}"
        )
    print(
        "\nRead: high visible% + high newly# + LOW capture = breadcrumb farming. "
        "Capture up with time_to_capture down = real improvement. "
        "A capture_rate gain matters when it clears the across-seed std."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Headless capture-rate / farming-diagnostic evaluation for trained Pacman policies."
    )
    parser.add_argument(
        "--algorithms",
        type=str,
        default="iql,vdn,qmixlocal,qmixglobal",
        help="Comma-separated algorithms to evaluate.",
    )
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=PROJECT_ROOT / "benchmarl_setup" / "runs",
        help="Root containing run dirs. For benchmark runs use runs/<device> (e.g. runs/cpu).",
    )
    parser.add_argument(
        "--jobs-path",
        type=Path,
        nargs="+",
        default=None,
        help="One or more benchmark jobs CSVs; evaluate their exact final checkpoints together.",
    )
    parser.add_argument("--episodes", type=int, default=100, help="Eval episodes per training seed.")
    parser.add_argument(
        "--eval-seed-base",
        type=int,
        default=0,
        help="First eval seed; episode i uses eval_seed_base + i (shared across all variants).",
    )
    parser.add_argument(
        "--train-seeds",
        type=str,
        default="",
        help="Optional comma-separated training seeds to include (default: all found).",
    )
    parser.add_argument(
        "--checkpoint-select",
        choices=["best", "latest"],
        default="best",
        help="Per training seed, pick the best-tail-reward run or the most recent.",
    )
    parser.add_argument("--max-steps", type=int, default=200, help="Max env steps per episode.")
    parser.add_argument(
        "--out",
        type=Path,
        default=PROJECT_ROOT / "benchmarl_setup" / "runs" / "eval_metrics.csv",
        help="Output CSV path.",
    )
    parser.add_argument("--device", type=str, default="cpu", help="Compute device for eval.")
    parser.add_argument(
        "--allow-cpu-fallback",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Fall back to CPU when the requested accelerator is unavailable.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    algorithms = [normalize_algorithm(a) for a in args.algorithms.split(",") if a.strip()]
    invalid = [a for a in algorithms if a not in SUPPORTED_ALGORITHMS]
    if invalid:
        raise ValueError(f"Unsupported algorithm(s): {invalid}. Allowed: {list(SUPPORTED_ALGORITHMS)}")

    train_seeds = None
    if args.train_seeds.strip():
        train_seeds = {int(s) for s in args.train_seeds.split(",") if s.strip()}

    resolved_device, reason = resolve_device(
        requested_device=args.device, allow_cpu_fallback=args.allow_cpu_fallback
    )
    print(f"Eval device | requested={args.device} resolved={resolved_device} | {reason}")

    # Make the custom task importable/registered before reloading checkpoints.
    register_pacman_task()

    if args.jobs_path is not None:
        evaluate_jobs(
            jobs_paths=args.jobs_path,
            episodes=args.episodes,
            eval_seed_base=args.eval_seed_base,
            max_steps=args.max_steps,
            device=resolved_device,
            out=args.out,
        )
    else:
        evaluate(
            algorithms=algorithms,
            runs_root=args.runs_root,
            episodes=args.episodes,
            eval_seed_base=args.eval_seed_base,
            train_seeds=train_seeds,
            checkpoint_select=args.checkpoint_select,
            max_steps=args.max_steps,
            device=resolved_device,
            out=args.out,
        )


if __name__ == "__main__":
    main()
