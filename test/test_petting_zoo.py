from pathlib import Path
import sys
import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from custom_environment.env.pacman_environment import PacManEnvironment
from custom_environment.env.domain.constant import Action, Observation
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
    payload = observations[first_agent]
    observation = payload["observation"]
    action_mask = payload["action_mask"]

    assert observation.shape == (env.view_size + 1, env.view_size)
    assert observation.dtype == np.float32
    shared_row = observation[-1]
    assert np.all(shared_row >= -1.0)
    assert np.all(shared_row <= 1.0)
    assert shared_row[0] in (0.0, 1.0)
    assert action_mask.shape == (4,)
    assert np.issubdtype(action_mask.dtype, np.integer)
    assert np.all(np.isin(action_mask, [0, 1]))
    assert int(action_mask.sum()) >= 1

    env.close()


def test_execute_action_prevents_ghost_out_of_bounds_wraparound():
    env = PacManEnvironment(global_view=create_grid())
    env.reset()

    ghost = env.ghosts[0]
    ghost.current_position = (0, 0)
    ghost.prev_position = (0, 0)
    ghost.invalid_move = False

    env.global_view[0, 0] = Observation.GHOST.value
    env.global_view[0, -1] = Observation.EMPTY.value

    env._execute_action(ghost, Action.MOVE_LEFT)

    assert ghost.current_position == (0, 0)
    assert ghost.invalid_move is True
    assert env.global_view[0, 0] == Observation.GHOST.value
    assert env.global_view[0, -1] == Observation.EMPTY.value

    env.close()


def test_execute_action_prevents_pacman_out_of_bounds_wraparound():
    env = PacManEnvironment(global_view=create_grid())
    env.reset()

    pacman = env.pacman
    pacman.current_position = (0, 0)
    pacman.prev_position = (0, 0)

    env.global_view[0, 0] = Observation.PAC_MAN.value
    env.global_view[0, -1] = Observation.EMPTY.value

    env._execute_action(pacman, Action.MOVE_LEFT)

    assert pacman.current_position == (0, 0)
    assert env.global_view[0, 0] == Observation.PAC_MAN.value
    assert env.global_view[0, -1] == Observation.EMPTY.value

    env.close()
