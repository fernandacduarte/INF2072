from pathlib import Path
import sys
import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from custom_environment.env.pacman_environment import PacManEnvironment
from custom_environment.env.domain.constant import Action
from pettingzoo.test import parallel_api_test
from custom_environment.utils import create_grid


if __name__ == "__main__":
    env = PacManEnvironment(global_view=create_grid())
    # Test petting zoo parallel API compliance
    parallel_api_test(env, num_cycles=1000)


def test_action_enum_values_match_discrete_indices():
    assert Action.MOVE_RIGHT.value == 0
    assert Action.MOVE_LEFT.value == 1
    assert Action.MOVE_UP.value == 2
    assert Action.MOVE_DOWN.value == 3


@pytest.mark.parametrize("token,expected", [(0, Action.MOVE_RIGHT), (1, Action.MOVE_LEFT), (2, Action.MOVE_UP), (3, Action.MOVE_DOWN)])
def test_decode_action_accepts_only_zero_based_indices(token, expected):
    assert PacManEnvironment._decode_action(token) == expected


@pytest.mark.parametrize("token", [-1, 4, 99])
def test_decode_action_rejects_out_of_range_indices(token):
    with pytest.raises(ValueError, match=r"Expected int in \[0, 3\]"):
        PacManEnvironment._decode_action(token)


def test_observation_contains_shared_memory_row():
    env = PacManEnvironment(global_view=create_grid())
    observations, _ = env.reset()
    first_agent = env.possible_agents[0]
    observation = observations[first_agent]

    assert observation.shape == (env.view_size + 1, env.view_size)
    assert observation.dtype == np.float32
    shared_row = observation[-1]
    assert np.all(shared_row >= -1.0)
    assert np.all(shared_row <= 1.0)
    assert shared_row[0] in (0.0, 1.0)

    env.close()
