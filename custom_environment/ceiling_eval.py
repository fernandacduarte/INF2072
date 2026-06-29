"""Scripted-pursuit capture-rate ceiling evaluator (plan-000036 Step 2).

Drives the raw PettingZoo ``PacManEnvironment`` (no BenchMARL) with the
scripted ``GhostPursuitPolicy`` against the configured Pacman, and reports the
capture rate and pursuit-quality metrics over many seeded episodes. The result
is an *upper bound* on the capture rate any learned ghost team could reach under
identical dynamics:

- Scripted ghosts cap low (~the learned rate) -> capture is **structurally hard**
  here (cop-number / co-location-capture / horizon), so a low learned rate is a
  result, not a training bug -- reward/HP tuning cannot cross it.
- Scripted ghosts hit high but learned ghosts stall -> the **learner** is leaving
  capture on the table, and reward/learning work is justified.

This answers research-000035 R1 / research-000033 R1 cheaply (minutes of CPU, no
training). It is intentionally a minimal, self-contained tool; plan-000029's
evasiveness sweep generalizes it across a Pacman-randomness dose-response.

Reproducibility: ``--seeds`` are explicit (constitution T4); each episode reseeds
the env so the Pacman controller and spawns are deterministic per seed; the git
commit is recorded in the CSV (C1). Output goes under ``benchmarl_setup/runs/``
(constitution T2).
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path
from statistics import mean, stdev

# Ensure workspace root is importable when running this file by path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from custom_environment.env.domain.ghost_pursuit_policy import GhostPursuitPolicy
from custom_environment.env.pacman_environment import PacManEnvironment
from custom_environment.eval_report import (
    _pursuit_fraction_from_distances,
    _team_mean_distance,
)
from custom_environment.utils import MAZES, build_maze

_RUNS_ROOT = PROJECT_ROOT / "benchmarl_setup" / "runs"


def _git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip()
    except Exception:
        return "unknown"


def _safe_mean(values: list[float]) -> float:
    clean = [v for v in values if v == v]
    return mean(clean) if clean else float("nan")


def _safe_std(values: list[float]) -> float:
    clean = [v for v in values if v == v]
    return stdev(clean) if len(clean) >= 2 else float("nan")


def _run_episode(env: PacManEnvironment, policy: GhostPursuitPolicy, seed: int) -> dict:
    """Run one scripted-pursuit episode; return its per-episode metrics."""
    env.reset(seed=seed)
    team_distances: list[float | None] = []
    visible_steps = 0
    steps = 0
    first_contact_step: int | None = None
    captured = False

    max_steps = int(env.max_steps)
    while steps < max_steps:
        ghost_ids = [ghost.id for ghost in env.ghosts]
        ghost_positions = [ghost.current_position for ghost in env.ghosts]
        pacman_pos = env.pacman.current_position
        actions_list = policy.choose_actions(env.global_view, ghost_positions, pacman_pos)
        actions = {gid: action.value for gid, action in zip(ghost_ids, actions_list)}

        _obs, _rewards, terminations, _truncations, _infos = env.step(actions)
        steps += 1

        context = env.last_reward_context
        if context is not None:
            team_distances.append(_team_mean_distance(context))
            if context.pacman_visible:
                visible_steps += 1
                if first_contact_step is None:
                    first_contact_step = steps
            captured = captured or bool(context.capture_happened)

        if any(terminations.values()):
            break

    denom = max(max_steps, 1)
    return {
        "captured": bool(captured or env._is_capture_state()),
        "steps": steps,
        "pursuit_fraction": _pursuit_fraction_from_distances(team_distances),
        "time_to_first_contact": (
            float(first_contact_step) / float(denom)
            if first_contact_step is not None
            else 1.0
        ),
        "visible_fraction": float(visible_steps) / float(max(steps, 1)),
        "mean_team_distance": _safe_mean(
            [d for d in team_distances if d is not None]
        ),
    }


def _build_env(args: argparse.Namespace) -> PacManEnvironment:
    spec = build_maze(args.maze, args.grid_size)
    return PacManEnvironment(
        spec,
        render_mode=None,
        ghost_view_size=args.ghost_view_size,
        pacman_difficulty=args.pacman_difficulty,
        pacman_random_action_prob=args.pacman_random_action_prob,
        pacman_safe_distance=args.pacman_safe_distance,
        capture_radius=args.capture_radius,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scripted greedy-pursuit ghost capture-rate ceiling evaluator."
    )
    parser.add_argument("--maze", default="default", choices=sorted(MAZES))
    parser.add_argument("--grid-size", type=int, default=20)
    parser.add_argument(
        "--pacman-difficulty", default="hard", choices=["easy", "medium", "hard"]
    )
    parser.add_argument("--pacman-random-action-prob", type=float, default=0.0)
    parser.add_argument("--pacman-safe-distance", type=int, default=None)
    parser.add_argument(
        "--capture-radius",
        type=int,
        default=0,
        help="Capture rule radius passed to the env (0 = co-location, the default rule).",
    )
    parser.add_argument("--ghost-view-size", type=int, default=None)
    parser.add_argument("--episodes", type=int, default=40)
    parser.add_argument(
        "--seeds",
        default="0,1,2,3,4",
        help="Comma-separated training seeds (constitution T4 / Q3 >=5).",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="CSV output path (default: benchmarl_setup/runs/ceiling_<maze>_<difficulty>.csv).",
    )
    args = parser.parse_args(argv)
    if args.episodes < 1:
        parser.error("--episodes must be >= 1")
    if args.capture_radius < 0:
        parser.error("--capture-radius must be >= 0")
    try:
        args.seed_list = [int(s) for s in str(args.seeds).split(",") if s.strip() != ""]
    except ValueError:
        parser.error("--seeds must be a comma-separated list of integers")
    if not args.seed_list:
        parser.error("--seeds must contain at least one seed")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    env = _build_env(args)
    policy = GhostPursuitPolicy()
    commit = _git_commit()

    rows: list[dict] = []
    all_capture: list[float] = []
    all_pursuit: list[float] = []
    all_ttfc: list[float] = []
    all_visible: list[float] = []
    all_distance: list[float] = []

    # Distinct episode seeds derived from each base seed so episodes within a seed
    # differ but the whole run is reproducible from --seeds.
    for base_seed in args.seed_list:
        ep_captures: list[float] = []
        ep_pursuit: list[float] = []
        ep_ttfc: list[float] = []
        ep_visible: list[float] = []
        ep_distance: list[float] = []
        for episode_index in range(args.episodes):
            episode_seed = base_seed * 100_000 + episode_index
            result = _run_episode(env, policy, episode_seed)
            ep_captures.append(1.0 if result["captured"] else 0.0)
            ep_pursuit.append(result["pursuit_fraction"])
            ep_ttfc.append(result["time_to_first_contact"])
            ep_visible.append(result["visible_fraction"])
            ep_distance.append(result["mean_team_distance"])

        row = {
            "maze": args.maze,
            "pacman_difficulty": args.pacman_difficulty,
            "capture_radius": args.capture_radius,
            "seed": base_seed,
            "episodes": args.episodes,
            "capture_rate": _safe_mean(ep_captures),
            "pursuit_fraction_mean": _safe_mean(ep_pursuit),
            "time_to_first_contact_mean": _safe_mean(ep_ttfc),
            "frac_steps_visible": _safe_mean(ep_visible),
            "mean_team_distance": _safe_mean(ep_distance),
            "git_commit": commit,
        }
        rows.append(row)
        all_capture.extend(ep_captures)
        all_pursuit.extend(ep_pursuit)
        all_ttfc.extend(ep_ttfc)
        all_visible.extend(ep_visible)
        all_distance.extend(ep_distance)
        print(
            f"seed={base_seed} capture_rate={row['capture_rate']:.3f} "
            f"pursuit={row['pursuit_fraction_mean']:.3f} "
            f"ttfc={row['time_to_first_contact_mean']:.3f} "
            f"visible={row['frac_steps_visible']:.3f}"
        )

    out_path = (
        Path(args.out)
        if args.out
        else _RUNS_ROOT / f"ceiling_{args.maze}_{args.pacman_difficulty}.csv"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(
        "\nCEILING (scripted greedy pursuit) | "
        f"maze={args.maze} difficulty={args.pacman_difficulty} "
        f"capture_radius={args.capture_radius}\n"
        f"  capture_rate        = {_safe_mean(all_capture):.3f} "
        f"(+/- {_safe_std(all_capture):.3f})\n"
        f"  pursuit_fraction    = {_safe_mean(all_pursuit):.3f}\n"
        f"  time_to_first_contact = {_safe_mean(all_ttfc):.3f}\n"
        f"  frac_steps_visible  = {_safe_mean(all_visible):.3f}\n"
        f"  mean_team_distance  = {_safe_mean(all_distance):.3f}\n"
        f"  -> {out_path}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
