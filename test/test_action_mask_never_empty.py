"""A boxed-in ghost must never produce an all-zero action mask.

An all-zero mask makes masked epsilon-greedy sampling draw from a zero
distribution and crashes training (CUDA device-side assert `input[0] != 0`).
The mask must always have at least one allowed action.
"""

from custom_environment.env.domain.constant import Observation
from custom_environment.env.pacman_environment import PacManEnvironment
from custom_environment.utils import parse_layout

_LAYOUT = [
    "######",
    "#GG.P#",
    "##.###",
    "######",
]


def test_boxed_ghost_mask_is_not_all_zero():
    env = PacManEnvironment(parse_layout(_LAYOUT), render_mode=None)
    env.reset(seed=0)
    # Box ghost_1 at (1,1): up/left/down are walls, right is the second ghost.
    env.ghosts[0].current_position = (1, 1)
    env.ghosts[1].current_position = (1, 2)
    env.global_view[1, 1] = Observation.GHOST.value
    env.global_view[1, 2] = Observation.GHOST.value

    mask = env._build_action_mask(env.ghosts[0])
    assert int(mask.sum()) > 0  # never all-zero
    assert int(mask.sum()) == 4  # boxed -> all-ones fallback


def test_open_ghost_mask_reflects_real_legal_moves():
    # A ghost with one open neighbour keeps a *specific* (not all-ones) mask.
    env = PacManEnvironment(parse_layout(_LAYOUT), render_mode=None)
    env.reset(seed=0)
    env.ghosts[0].current_position = (1, 1)
    env.ghosts[1].current_position = (1, 3)  # move ghost 2 away so (1,2) is open
    env.global_view[1, 1] = Observation.GHOST.value
    env.global_view[1, 2] = Observation.EMPTY.value
    env.global_view[1, 3] = Observation.GHOST.value

    mask = env._build_action_mask(env.ghosts[0])
    assert 0 < int(mask.sum()) < 4  # only the open neighbour(s) allowed
