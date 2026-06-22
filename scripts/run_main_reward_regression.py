"""Run the matching small training on pre-refactor main."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path.cwd()
OUTPUT_ROOT = Path(
    os.environ.get(
        "REWARD_REGRESSION_ROOT",
        str(Path(tempfile.gettempdir()) / "inf2072_reward_regression"),
    )
)
RUN_ROOT = OUTPUT_ROOT / "main"


def main() -> None:
    runner = PROJECT_ROOT / "benchmarl_setup" / "run_pacman_benchmarl.py"
    if not runner.exists():
        raise SystemExit("Run this script from the INF2072 project root.")
    branch = subprocess.run(
        ["git", "branch", "--show-current"],
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
    if branch != "main":
        raise SystemExit(f"Expected branch 'main', but current branch is {branch!r}.")
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
    if status:
        raise SystemExit("The main worktree is modified; commit/stash changes before the baseline run.")
    if RUN_ROOT.exists():
        raise SystemExit(
            f"Refusing to mix runs: {RUN_ROOT} already exists. "
            "Delete or rename it before repeating the experiment."
        )
    RUN_ROOT.mkdir(parents=True)

    # Deliberately identical to the refactored command except that old main does
    # not understand --reward-class and uses its built-in reward implementation.
    command = [
        sys.executable,
        str(runner),
        "--algorithm", "iql",
        "--seed", "17",
        "--max-frames", "4000",
        "--frames-per-batch", "200",
        "--optimizer-steps", "2",
        "--train-batch-size", "64",
        "--memory-size", "2000",
        "--init-random-frames", "400",
        "--maze", "default",
        "--device", "cpu",
        "--save-folder", str(RUN_ROOT),
        "--save-folder-includes-maze",
        "--no-checkpoint-at-end",
    ]
    metadata = RUN_ROOT / "regression_metadata.txt"
    metadata.write_text(
        f"branch={branch}\npython={sys.executable}\ncommand={' '.join(command)}\n",
        encoding="utf-8",
    )

    print(f"Output: {RUN_ROOT}")
    print("Command:", " ".join(command))
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)

    comparator = Path(__file__).resolve().with_name("compare_reward_regression.py")
    print("\nMain run complete.")
    print(f"Compare with: {sys.executable} {comparator}")


if __name__ == "__main__":
    main()
