#!/usr/bin/env python3
"""Decisive reward A/B runner (plan-000031).

Runs the statistically-valid A/B the PBRS claim needs (constitution Q3): at each
Pacman-randomness point ``p in {0.25, 0.50, 0.75}`` it trains BOTH reward arms --
the matched sparse control (``capture_v0_sparse_control``) and PBRS
(``capture_v0_pure_potential_shaping``) -- over >=5 seeds, via the existing
``run_benchmark.py`` training path.

Why a wrapper at all: ``run_benchmark.py`` keys its output paths by
maze/reward/device only -- never by ``p`` -- so two points sharing one
``--save-folder`` would co-mingle. This wrapper gives each ``p`` its own
``<save-root>/p_<p>/`` folder (the only disambiguator) and records an auditable
``ab_manifest.csv`` (git commit + dirty flag, C1).

Held constant across all points (only ``p`` and the reward arm vary):
``--pacman-curriculum off``, ``--pacman-difficulty hard``, ``--randomize-spawns``,
frames, epsilon schedule, maze, and the two reward ids. With curriculum off, the
``hard`` difficulty fixes the Pacman heuristic (``pure_random=False``,
``safe_distance=PACMAN_SAFE_DISTANCE``) and ``p`` is the sole varying axis: the
fraction of steps Pacman acts randomly instead of evasively.

Examples
--------
    # Preview the full command matrix without training:
    python benchmarl_setup/run_reward_ab.py --dry-run

    # Run the decisive A/B on GPU:
    python benchmarl_setup/run_reward_ab.py --devices cuda
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUN_BENCHMARK = PROJECT_ROOT / "benchmarl_setup" / "run_benchmark.py"
MANIFEST_NAME = "ab_manifest.csv"
MANIFEST_FIELDS = [
    "p",
    "evasiveness",
    "reward_ids",
    "algorithms",
    "seeds",
    "max_frames",
    "eval_episodes",
    "save_folder",
    "status",
    "git_commit",
    "git_dirty",
    "timestamp_utc",
]

DEFAULT_POINTS = "0.25,0.50,0.75"
DEFAULT_ALGORITHMS = "iql,vdn,qmixglobal"
DEFAULT_SEEDS = "0,1,2,3,4"
DEFAULT_REWARD_IDS = "capture_v0_sparse_control,capture_v0_pure_potential_shaping"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the decisive reward A/B (matched sparse control vs PBRS).",
    )
    parser.add_argument(
        "--points",
        type=str,
        default=DEFAULT_POINTS,
        help="Comma-separated Pacman random-action probabilities to sweep (each in [0,1]).",
    )
    parser.add_argument("--algorithms", type=str, default=DEFAULT_ALGORITHMS)
    parser.add_argument("--seeds", type=str, default=DEFAULT_SEEDS)
    parser.add_argument(
        "--reward-ids",
        type=str,
        default=DEFAULT_REWARD_IDS,
        help="Comma-separated reward ids for the two A/B arms (control first, PBRS second).",
    )
    parser.add_argument("--max-frames", type=int, default=60000)
    parser.add_argument(
        "--checkpoint-interval",
        type=int,
        default=10000,
        help="Periodic checkpoint frames; also drives live-capture snapshots for the sample-efficiency curve.",
    )
    parser.add_argument("--eval-episodes", type=int, default=40)
    parser.add_argument(
        "--save-root",
        type=str,
        default=str((PROJECT_ROOT / "benchmarl_setup" / "runs" / "ab").resolve()),
        help="Root for A/B outputs; each point writes under <save-root>/p_<p>/.",
    )
    parser.add_argument("--maze", type=str, default="pinklike3")
    parser.add_argument(
        "--devices",
        type=str,
        default="cpu",
        help="Comma-separated compute devices forwarded to run_benchmark.py (e.g. cpu, cuda).",
    )
    parser.add_argument(
        "--epsilon-anneal-ratio",
        type=float,
        default=0.5,
        help="Forwarded to run_benchmark.py (lower = longer low-epsilon phase, stabler curve).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the full per-point command matrix without launching any training.",
    )
    return parser.parse_args(argv)


def _parse_points(raw: str) -> list[float]:
    """Parse and validate the comma-separated p sweep (each in [0, 1])."""
    points: list[float] = []
    for token in (part.strip() for part in raw.split(",")):
        if not token:
            continue
        try:
            value = float(token)
        except ValueError as exc:
            raise ValueError(f"Invalid point {token!r}: not a number.") from exc
        if not (0.0 <= value <= 1.0):
            raise ValueError(f"Point p={value} is outside [0, 1].")
        points.append(value)
    if not points:
        raise ValueError("--points must contain at least one value in [0, 1].")
    return points


def _require_nonempty_csv(raw: str, name: str) -> str:
    if not [part for part in (p.strip() for p in raw.split(",")) if part]:
        raise ValueError(f"--{name} must contain at least one value.")
    return raw


def _point_folder(save_root: Path, p: float) -> Path:
    # str(float) drops the trailing zero so p=0.50 -> p_0.5 (stable folder names).
    return save_root / f"p_{p}"


def build_command(p: float, args: argparse.Namespace) -> list[str]:
    """Build the run_benchmark.py command training BOTH reward arms at one point."""
    save_folder = _point_folder(Path(args.save_root), p)
    return [
        sys.executable,
        str(RUN_BENCHMARK),
        "--algorithms",
        args.algorithms,
        "--reward-ids",
        args.reward_ids,
        "--seeds",
        args.seeds,
        "--max-frames",
        str(args.max_frames),
        "--pacman-curriculum",
        "off",
        "--pacman-difficulty",
        "hard",
        "--pacman-random-action-prob",
        str(p),
        "--randomize-spawns",
        "--checkpoint-interval",
        str(args.checkpoint_interval),
        "--eval-episodes",
        str(args.eval_episodes),
        "--checkpoint-at-end",
        "--epsilon-anneal-ratio",
        str(args.epsilon_anneal_ratio),
        "--maze",
        args.maze,
        "--devices",
        args.devices,
        "--save-folder",
        str(save_folder),
    ]


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(PROJECT_ROOT), text=True
        ).strip()
    except Exception:
        return "unknown"


def _git_dirty() -> bool:
    try:
        out = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=str(PROJECT_ROOT), text=True
        )
        return bool(out.strip())
    except Exception:
        return False


def _append_manifest_row(manifest_path: Path, row: dict[str, object]) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not manifest_path.exists()
    with manifest_path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    points = _parse_points(args.points)
    _require_nonempty_csv(args.seeds, "seeds")
    _require_nonempty_csv(args.algorithms, "algorithms")
    _require_nonempty_csv(args.reward_ids, "reward-ids")

    save_root = Path(args.save_root)
    manifest_path = save_root / MANIFEST_NAME
    commit = _git_commit()
    dirty = _git_dirty()

    print(f"Decisive reward A/B | git {commit[:10]}{' (dirty)' if dirty else ''}")
    print(f"  arms: {args.reward_ids}")
    print(f"  algorithms: {args.algorithms} | seeds: {args.seeds} | maze: {args.maze}")
    print(f"  points (p): {', '.join(str(p) for p in points)}")
    print()

    failed_points: list[float] = []
    for p in points:
        evasiveness = 1.0 - p
        save_folder = _point_folder(save_root, p)
        command = build_command(p, args)
        print(f"[p={p}] evasiveness e=1-p={evasiveness:.2f} -> {save_folder}")
        print("  " + " ".join(command))
        if args.dry_run:
            continue
        result = subprocess.run(command, cwd=str(PROJECT_ROOT))
        status = "ok" if result.returncode == 0 else f"failed(exit={result.returncode})"
        _append_manifest_row(
            manifest_path,
            {
                "p": p,
                "evasiveness": evasiveness,
                "reward_ids": args.reward_ids,
                "algorithms": args.algorithms,
                "seeds": args.seeds,
                "max_frames": args.max_frames,
                "eval_episodes": args.eval_episodes,
                # Stored relative to the manifest's own directory (the save-root) so
                # the plotter resolves it portably regardless of absolute location.
                "save_folder": save_folder.name,
                "status": status,
                "git_commit": commit,
                "git_dirty": dirty,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            },
        )
        if result.returncode != 0:
            # A single point's job failure (e.g. a crashed seed/algorithm) must not
            # abort the whole sweep -- record it and keep going so the other points
            # still produce data. run_benchmark already tolerates per-job failures.
            failed_points.append(p)
            print(
                f"WARNING: run_benchmark returned exit {result.returncode} at p={p}; "
                "continuing to the next point.",
                file=sys.stderr,
            )

    if not args.dry_run:
        print(f"\nManifest written to {manifest_path}")
        if failed_points:
            print(
                f"NOTE: {len(failed_points)}/{len(points)} point(s) had job failures: "
                f"{', '.join(str(p) for p in failed_points)}. Their eval outputs may be "
                "missing (run_benchmark skips paired eval when any job fails).",
                file=sys.stderr,
            )
    # Non-zero only if EVERY point failed; partial success is still a usable sweep.
    return 1 if (failed_points and len(failed_points) == len(points)) else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
