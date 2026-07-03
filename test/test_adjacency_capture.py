"""Tests for flag-gated adjacency capture (plan-000036 Steps 7, 9)."""

from custom_environment.env.pacman_environment import PacManEnvironment
from custom_environment.utils import parse_layout

# Small connected open room: two ghost spawns ('G'), one Pacman spawn ('P').
_LAYOUT = [
    "%%%%%%%",
    "%G   G%",
    "%     %",
    "%   P %",
    "%%%%%%%",
]


def _make_env(capture_radius: int) -> PacManEnvironment:
    env = PacManEnvironment(
        parse_layout(_LAYOUT),
        render_mode=None,
        pacman_difficulty="hard",
        capture_radius=capture_radius,
    )
    env.reset(seed=0)
    return env


def test_radius_one_captures_adjacent_ghost():
    env = _make_env(capture_radius=1)
    # Place Pacman and one ghost on adjacent open cells (BFS distance 1).
    env.pacman.current_position = (2, 3)
    env.ghosts[0].current_position = (2, 4)
    assert env._is_capture_state() is True


def test_radius_zero_does_not_capture_adjacent_ghost():
    env = _make_env(capture_radius=0)
    env.pacman.current_position = (2, 3)
    env.ghosts[0].current_position = (2, 4)  # adjacent but not co-located
    # Move the second ghost away so only the adjacency case is under test.
    env.ghosts[1].current_position = (1, 1)
    assert env._is_capture_state() is False


def test_radius_zero_still_captures_on_co_location():
    env = _make_env(capture_radius=0)
    env.pacman.current_position = (2, 3)
    env.ghosts[0].current_position = (2, 3)  # exact co-location
    assert env._is_capture_state() is True


def test_capture_radius_default_is_zero():
    env = PacManEnvironment(parse_layout(_LAYOUT), render_mode=None)
    assert env.capture_radius == 0


def test_negative_capture_radius_rejected():
    try:
        PacManEnvironment(parse_layout(_LAYOUT), render_mode=None, capture_radius=-1)
    except ValueError:
        return
    raise AssertionError("expected ValueError for negative capture_radius")
