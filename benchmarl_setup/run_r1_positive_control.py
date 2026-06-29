"""R1 positive-control sanity battery launcher (plan-000034, source research-000032).

Decides whether the ~40% capture-rate "ceiling against a random Pacman" is a
*confound* or a *genuine learning limit* BEFORE any hyperparameter sweep.

It runs two conditions over the existing ``run_benchmark.py`` harness, changing
only the opponent/curriculum axis:

* **Condition P (positive control)** -- the *truly random* opponent in isolation:
  ``--pacman-curriculum off --pacman-random-action-prob 1.0``, full observability
  (no ``--ghost-view-size``), sparse ``capture_v0`` reward (no orbit term). At
  ``p=1.0`` the Pacman ignores its flee heuristic and moves uniformly at random,
  so the research-000022 RC2 (oscillation saddle) and RC3 (safe-distance cordon)
  artifacts are auto-neutralized; only RC4 (orbit reward) matters and is removed
  by the sparse reward-id.
* **Condition C (the suspect)** -- the curriculum-on config the team has been
  running: ``--pacman-curriculum easy-medium-hard``.

Both conditions enable the **paired objective evaluation** (``--eval-episodes``),
which ``run_benchmark.py`` runs *checkpoint-native* (it appends
``--allow-non-hard-checkpoint``), so capture_rate reflects the **training**
opponent. This is deliberately different from the live-capture liveplot eval,
which is *hard-forced* and is the source of the misleading 40% the team observed.
Read the verdict with ``summarize_r1.py`` (it parses the checkpoint-native
``reward_eval_*`` CSVs, never the hard-forced ``evaluation_report_live_capture*``
files).

Decision rule (see ``summarize_r1.verdict``):
* Condition P jumps well above 40% -> the ceiling was a confound; fix the
  framing/eval and **skip** the sweep.
* Condition P also sits ~40% -> a genuine learning limit; the scalar UTD-axis
  sweep (research-000032 R4) is justified.
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUN_BENCHMARK_PATH = PROJECT_ROOT / "benchmarl_setup" / "run_benchmark.py"

# The two conditions of the battery. Only the opponent/curriculum axis differs.
CONDITIONS = ("P", "C")

MANIFEST_FIELDNAMES = [
    "condition",
    "algorithms",
    "seeds",
    "max_frames",
    "eval_episodes",
    "reward_id",
    "pacman_curriculum",
    "pacman_random_action_prob",
    "ghost_view_size",
    "maze",
    "devices",
    "save_folder",
    "git_commit",
]


def git_commit() -> str:
    """Short HEAD commit hash for provenance (constitution C1). Empty on failure."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        return out.stdout.strip()
    except OSError:
        return ""


def build_condition_command(
    condition: str,
    *,
    algorithms: str,
    seeds: str,
    max_frames: int,
    eval_episodes: int,
    save_folder: str,
    reward_id: str = "capture_v0",
    maze: str = "default",
    devices: str = "cpu",
    ghost_view_size: int | None = None,
) -> list[str]:
    """Compose the ``run_benchmark.py`` invocation for one battery condition.

    Condition P pins the truly-random opponent in isolation; Condition C runs the
    easy-medium-hard curriculum. Everything else (reward, observability, frames,
    seeds, eval protocol) is held identical so the comparison is clean.
    """
    if condition not in CONDITIONS:
        raise ValueError(f"Unknown condition {condition!r}; expected one of {CONDITIONS}.")

    command = [
        sys.executable,
        str(RUN_BENCHMARK_PATH),
        "--algorithms",
        algorithms,
        "--reward-ids",
        reward_id,
        "--seeds",
        seeds,
        "--max-frames",
        str(max_frames),
        "--eval-episodes",
        str(eval_episodes),
        "--maze",
        maze,
        "--devices",
        devices,
        "--save-folder",
        save_folder,
        "--checkpoint-at-end",
    ]

    if condition == "P":
        # Truly-random opponent in isolation; full observability.
        command += ["--pacman-curriculum", "off", "--pacman-random-action-prob", "1.0"]
    else:  # condition == "C"
        # The curriculum config under suspicion.
        command += [
            "--pacman-curriculum",
            "easy-medium-hard",
            "--pacman-curriculum-max-frames",
            str(max_frames),
        ]

    # Full observability is the default (ghost_view_size unset). Only add the
    # flag when explicitly matching a local-view training regime on BOTH arms.
    if ghost_view_size is not None:
        command += ["--ghost-view-size", str(ghost_view_size)]

    return command


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    """Write the auditable battery manifest (constitution C1/T4)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote R1 manifest: {path}")


def _manifest_row(
    condition: str,
    args: argparse.Namespace,
    save_folder: str,
    commit: str,
) -> dict[str, str]:
    return {
        "condition": condition,
        "algorithms": args.algorithms,
        "seeds": args.seeds,
        "max_frames": str(args.max_frames),
        "eval_episodes": str(args.eval_episodes),
        "reward_id": args.reward_id,
        "pacman_curriculum": "off" if condition == "P" else "easy-medium-hard",
        "pacman_random_action_prob": "1.0" if condition == "P" else "",
        "ghost_view_size": "" if args.ghost_view_size is None else str(args.ghost_view_size),
        "maze": args.maze,
        "devices": args.devices,
        "save_folder": save_folder,
        "git_commit": commit,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--algorithms",
        type=str,
        default="iql,vdn,qmixglobal",
        help="Comma-separated algorithms (default: iql,vdn,qmixglobal).",
    )
    parser.add_argument(
        "--seeds",
        type=str,
        default="0,1,2,3,4",
        help="Comma-separated seeds (>=5 per constitution Q3).",
    )
    parser.add_argument("--max-frames", type=int, default=60000)
    parser.add_argument(
        "--eval-episodes",
        type=int,
        default=40,
        help="Paired objective-eval episodes per checkpoint (must be >0 for a DV).",
    )
    parser.add_argument("--reward-id", type=str, default="capture_v0")
    parser.add_argument("--maze", type=str, default="default")
    parser.add_argument(
        "--devices",
        type=str,
        default="cpu",
        help="Comma-separated compute devices (use cuda when a GPU is available).",
    )
    parser.add_argument(
        "--ghost-view-size",
        type=int,
        default=None,
        help="Optional local view; default full observability (unset). Applied to BOTH arms.",
    )
    parser.add_argument(
        "--save-folder",
        type=str,
        default=str((PROJECT_ROOT / "benchmarl_setup" / "runs" / "r1").resolve()),
        help="Base output root; each condition writes under <save-folder>/condition_<P|C>.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the commands and write the manifest without launching training.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.eval_episodes <= 0:
        raise SystemExit("--eval-episodes must be > 0 (else the DV comes out empty).")

    base = Path(args.save_folder)
    commit = git_commit()
    manifest_rows: list[dict[str, str]] = []
    commands: list[tuple[str, list[str]]] = []

    for condition in CONDITIONS:
        save_folder = str((base / f"condition_{condition}").resolve())
        command = build_condition_command(
            condition,
            algorithms=args.algorithms,
            seeds=args.seeds,
            max_frames=args.max_frames,
            eval_episodes=args.eval_episodes,
            save_folder=save_folder,
            reward_id=args.reward_id,
            maze=args.maze,
            devices=args.devices,
            ghost_view_size=args.ghost_view_size,
        )
        commands.append((condition, command))
        manifest_rows.append(_manifest_row(condition, args, save_folder, commit))

    write_manifest(base / "r1_manifest.csv", manifest_rows)

    for condition, command in commands:
        print(f"\n=== Condition {condition} ===")
        print(" ".join(command))
        if not args.dry_run:
            completed = subprocess.run(command, check=False)
            if completed.returncode != 0:
                print(f"Condition {condition} failed (returncode={completed.returncode}).")
                return completed.returncode

    if args.dry_run:
        print("\nDry run: no training launched.")
    else:
        print(
            "\nBoth conditions complete. Read the verdict with:\n"
            f"  {sys.executable} benchmarl_setup/summarize_r1.py "
            f"--p-folder {base / 'condition_P'} --c-folder {base / 'condition_C'}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
