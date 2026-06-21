"""Run the small deterministic training on the reward-refactor branch."""

from __future__ import annotations

import os
import shutil
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
RUN_ROOT = OUTPUT_ROOT / "refactored"
DEFAULT_REWARD = "custom_environment.env.rewards.current:CurrentTeamReward"


def main() -> None:
    runner = PROJECT_ROOT / "benchmarl_setup" / "run_pacman_benchmarl.py"
    if not runner.exists():
        raise SystemExit("Run this script from the INF2072 project root.")
    if "--reward-class" not in runner.read_text(encoding="utf-8"):
        raise SystemExit("This checkout does not contain the reward refactor.")
    if RUN_ROOT.exists():
        raise SystemExit(
            f"Refusing to mix runs: {RUN_ROOT} already exists. "
            "Delete or rename it before repeating the experiment."
        )
    RUN_ROOT.mkdir(parents=True)

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
        "--reward-class", DEFAULT_REWARD,
        "--save-folder", str(RUN_ROOT),
        "--save-folder-includes-maze",
        "--no-checkpoint-at-end",
    ]
    metadata = RUN_ROOT / "regression_metadata.txt"
    branch = subprocess.run(
        ["git", "branch", "--show-current"],
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
    metadata.write_text(
        f"branch={branch}\npython={sys.executable}\ncommand={' '.join(command)}\n",
        encoding="utf-8",
    )
    (RUN_ROOT / "working_tree.patch").write_text(
        subprocess.run(
            ["git", "diff", "HEAD"],
            check=True,
            text=True,
            capture_output=True,
        ).stdout,
        encoding="utf-8",
    )

    print(f"Output: {RUN_ROOT}")
    print("Command:", " ".join(command))
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)

    tools_dir = OUTPUT_ROOT / "tools"
    tools_dir.mkdir(exist_ok=True)
    scripts_dir = Path(__file__).resolve().parent
    for filename in (
        "run_main_reward_regression.py",
        "compare_reward_regression.py",
    ):
        shutil.copy2(scripts_dir / filename, tools_dir / filename)

    print("\nRefactored run complete.")
    print(f"After switching to main, run: {sys.executable} {tools_dir / 'run_main_reward_regression.py'}")


if __name__ == "__main__":
    main()
