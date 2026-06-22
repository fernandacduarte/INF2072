from pathlib import Path
import sys
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
