"""Register pacman task for the current Python process and run a smoke check.

BenchMARL 1.5.x does not expose register_env; custom integration is done via
Task/TaskClass. This script registers pacman/pacman at runtime and validates
imports and environment instantiation.
"""

from pathlib import Path
import sys

# Ensure workspace root is importable when this file is run by path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from custom_environment.utils import create_grid
from custom_environment.env.pacman_environment import PacManEnvironment
from benchmarl_setup.pacman_benchmarl_task import register_pacman_task


def main() -> None:
    full_task_name = register_pacman_task()
    print(f"Registered task key: {full_task_name}")

    env = PacManEnvironment(global_view=create_grid())
    print("Pacman environment instantiated successfully:")
    print(env)

    import benchmarl.environments as bme

    has_register_api = hasattr(bme, "register_env")
    print(f"BenchMARL module loaded: {bme.__name__}")
    print(f"Runtime register_env API available: {has_register_api}")

    if not has_register_api:
        print("BenchMARL 1.5.x has no register_env API, which is expected.")
    print(
        "Run training with: py -3.11 benchmarl_setup\\run_pacman_benchmarl.py "
        "--algorithm iql"
    )


if __name__ == "__main__":
    main()
