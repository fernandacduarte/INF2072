from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from custom_environment.env.pacman_environment import PacManEnvironment
from pettingzoo.test import parallel_api_test
from custom_environment.utils import create_grid


if __name__ == "__main__":
    env = PacManEnvironment(global_view=create_grid())
    # Test petting zoo parallel API compliance
    parallel_api_test(env, num_cycles=1000)
