"""Reward-calibration tests (plan-000021 / research-000012 R4).

Locks in the property that the team reward rewards *pursuit*: under the live
reward function, a ghost moving one BFS-cell toward the true Pacman position
must score higher than staying still, and higher than moving one cell away.

This guards against the stay-still trap (research-000012 RC1), where a stale
last-sighting distance term made inaction better in expectation than moving.

Setup: one ghost ("mover") is placed on a mid-corridor *pivot* cell that has
both a closer and a farther walkable neighbor relative to the true Pacman; the
other ghost is parked at its (far) spawn so the team-minimum distance is always
defined by the mover. Ghost views are not recomputed between the staged
transition and the reward call, so visibility terms are identical across the
scenarios we compare and cancel out -- the comparison isolates the movement +
potential-shaping contribution.
"""

from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from custom_environment.env.pacman_environment import PacManEnvironment
from custom_environment.env.domain.constant import (
    Observation,
)
from custom_environment.utils import create_grid

SEED = 0


def _make_env():
    env = PacManEnvironment(global_view=create_grid())
    env.reset(seed=SEED)
    return env


def _walkable_neighbors(env, position, exclude):
    """Walkable 4-neighbors of `position`, excluding walls, Pacman's cell, and
    any cell in `exclude` (e.g. occupied ghost cells)."""
    rows, cols = env.global_view.shape
    x, y = position
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = x + dx, y + dy
        if not (0 <= nx < rows and 0 <= ny < cols):
            continue
        if env.global_view[nx, ny] == Observation.WALL.value:
            continue
        if (nx, ny) == env.pacman.current_position:
            continue  # stepping onto Pacman is a capture, not a pursuit step
        if (nx, ny) in exclude:
            continue
        yield (nx, ny)


def _find_pivot(env, occupied):
    """A walkable cell (BFS distance >= 2 to true Pacman) that has both a neighbor
    one cell closer and a neighbor one cell farther. Returns (cell, distance) or
    (None, None). `occupied` cells (the parked ghost) are avoided."""
    target = env.pacman.current_position
    rows, cols = env.global_view.shape
    for x in range(rows):
        for y in range(cols):
            cell = (x, y)
            if env.global_view[x, y] == Observation.WALL.value:
                continue
            if cell == target or cell in occupied:
                continue
            d = env._bfs_distance(cell, target)
            if d is None or d < 2:
                continue
            nbr_dists = {
                env._bfs_distance(n, target)
                for n in _walkable_neighbors(env, cell, occupied)
            }
            if (d - 1) in nbr_dists and (d + 1) in nbr_dists:
                return cell, d
    return None, None


def _setup_pivot_env():
    """Fresh env with ghost[0] relocated to a pivot cell and the remaining ghost
    parked far away. Returns (env, mover, pivot, pivot_distance) or skips when the
    deterministic map has no usable pivot."""
    env = _make_env()
    mover = env.ghosts[0]
    parked = {g.current_position for g in env.ghosts[1:]}
    pivot, dist = _find_pivot(env, parked)
    if pivot is None:
        pytest.skip("deterministic map has no mid-corridor pivot cell")

    # Sanity: the parked ghost must stay farther than the pivot's reachable range,
    # so the team-minimum distance is governed by the mover throughout.
    for g in env.ghosts[1:]:
        gd = env._bfs_distance(g.current_position, env.pacman.current_position)
        if gd is None or gd <= dist + 1:
            pytest.skip("parked ghost too close to govern the team minimum")

    env.global_view[mover.current_position] = Observation.EMPTY.value
    env.global_view[pivot] = Observation.GHOST.value
    mover.current_position = pivot
    return env, mover, pivot, dist


def _reward_for_move(env, mover, dest, base_dist):
    """Prime the potential baseline at `base_dist`, apply a single transition
    (mover -> dest, or stay when dest equals the current cell), return the reward."""
    for ghost in env.ghosts:
        ghost.prev_position = ghost.current_position  # default: stayed
    baseline = env._build_reward_context(
        actions={},
        pellets_before=env._remaining_pellets(),
        capture_happened=False,
        timeout_happened=False,
        pacman_win_happened=False,
    )
    env.reward_strategy.compute(baseline)
    if dest != mover.current_position:
        old = mover.current_position
        mover.prev_position = old
        env.global_view[old] = Observation.EMPTY.value
        env.global_view[dest] = Observation.GHOST.value
        mover.current_position = dest
    transition = env._build_reward_context(
        actions={},
        pellets_before=env._remaining_pellets(),
        capture_happened=False,
        timeout_happened=False,
        pacman_win_happened=False,
    )
    return env.reward_strategy.compute(transition).total


def _scenario_reward(move):
    """Evaluate one of 'toward' | 'away' | 'stay' on a fresh pivot env."""
    env, mover, pivot, dist = _setup_pivot_env()
    if move == "stay":
        dest = pivot
    else:
        wanted = dist - 1 if move == "toward" else dist + 1
        occupied = {g.current_position for g in env.ghosts if g is not mover}
        dest = next(
            (n for n in _walkable_neighbors(env, pivot, occupied)
             if env._bfs_distance(n, env.pacman.current_position) == wanted),
            None,
        )
        assert dest is not None, f"pivot guaranteed a '{move}' neighbor"
    return _reward_for_move(env, mover, dest, dist)


def test_move_toward_pacman_beats_staying():
    reward_toward = _scenario_reward("toward")
    reward_stay = _scenario_reward("stay")
    assert reward_toward > reward_stay, (
        f"expected move-toward ({reward_toward}) > stay-still ({reward_stay})"
    )


def test_move_toward_beats_move_away():
    reward_toward = _scenario_reward("toward")
    reward_away = _scenario_reward("away")
    assert reward_toward > reward_away, (
        f"expected move-toward ({reward_toward}) > move-away ({reward_away})"
    )
