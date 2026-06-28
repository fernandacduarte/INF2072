"""Tests for the relative-bearing shared-memory feature (research-000024 FR4).

The ghost observation's shared-memory row must encode Pacman's position *relative*
to each ghost (a directional vector), not as an absolute board coordinate the
ghost cannot act on without knowing its own position.
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from custom_environment.env.pacman_environment import PacManEnvironment
from custom_environment.utils import parse_layout


# 3x9 grid: rows=3 (row_den=2), cols=9 (col_den=8).
LAYOUT = [
    "%%%%%%%%%",
    "%P...G.G%",
    "%%%%%%%%%",
]


def _make_env() -> PacManEnvironment:
    env = PacManEnvironment(global_view=parse_layout(LAYOUT))
    env.reset()
    return env


def test_shared_memory_encodes_relative_bearing():
    env = _make_env()
    rows, cols = env.global_view.shape
    row_den, col_den = float(rows - 1), float(cols - 1)

    # Pacman seen at (1, 7); a ghost at (1, 1) is left of and level with it.
    features = env._shared_memory_features(
        any_visible=True, seen_positions=[(1, 7)], ghost_position=(1, 1)
    )
    assert features[0] == 1.0  # visible flag
    assert features[1] == pytest.approx((1 - 1) / row_den)  # same row -> 0
    assert features[2] == pytest.approx((7 - 1) / col_den)  # Pacman to the right -> +


def test_bearing_is_per_ghost_not_shared():
    env = _make_env()
    seen = [(1, 7)]
    near = env._shared_memory_features(any_visible=True, seen_positions=seen, ghost_position=(1, 6))
    far = env._shared_memory_features(any_visible=True, seen_positions=seen, ghost_position=(1, 1))
    # Same Pacman sighting, different ghosts -> different bearings (the whole point).
    assert far[2] > near[2]
    assert near[2] == pytest.approx((7 - 6) / float(env.global_view.shape[1] - 1))


def test_bearing_sign_points_toward_pacman():
    env = _make_env()
    cols = env.global_view.shape[1]
    col_den = float(cols - 1)
    # Pacman to the LEFT of the ghost -> negative column bearing.
    left = env._shared_memory_features(any_visible=True, seen_positions=[(1, 2)], ghost_position=(1, 6))
    assert left[2] == pytest.approx((2 - 6) / col_den)
    assert left[2] < 0.0


def test_no_sighting_gives_neutral_bearing_and_max_staleness():
    env = _make_env()
    env.last_pacman_sighting_position = None
    env.last_pacman_sighting_step = None
    features = env._shared_memory_features(
        any_visible=False, seen_positions=[], ghost_position=(1, 1)
    )
    assert features[0] == 0.0  # not visible
    assert features[1] == pytest.approx(0.0)  # neutral bearing
    assert features[2] == pytest.approx(0.0)
    assert features[3] == pytest.approx(1.0)  # max staleness flags "no info"


def test_observation_shape_unchanged():
    env = _make_env()
    obs = env._get_observation(env.ghosts[0])["observation"]
    assert obs.shape == (env.view_size + 1, env.view_size)
