"""Tests for the scripted greedy-pursuit ghost policy (plan-000036 Step 1)."""

import numpy as np

from custom_environment.env.domain.constant import Action, Observation
from custom_environment.env.domain.ghost_pursuit_policy import GhostPursuitPolicy


def _open_grid(rows: int, cols: int) -> np.ndarray:
    """Wall-bordered open room filled with EMPTY interior cells."""
    grid = np.full((rows, cols), Observation.EMPTY.value, dtype=np.int64)
    grid[0, :] = Observation.WALL.value
    grid[-1, :] = Observation.WALL.value
    grid[:, 0] = Observation.WALL.value
    grid[:, -1] = Observation.WALL.value
    return grid


def _delta(action: Action) -> tuple[int, int]:
    return {
        Action.MOVE_RIGHT: (0, 1),
        Action.MOVE_LEFT: (0, -1),
        Action.MOVE_UP: (-1, 0),
        Action.MOVE_DOWN: (1, 0),
    }[action]


def test_chosen_action_moves_one_cell_closer():
    grid = _open_grid(7, 7)
    pacman = (1, 1)
    ghost = (5, 5)
    grid[pacman] = Observation.PAC_MAN.value
    grid[ghost] = Observation.GHOST.value

    policy = GhostPursuitPolicy()
    actions = policy.choose_actions(grid, [ghost], pacman)

    dx, dy = _delta(actions[0])
    new_pos = (ghost[0] + dx, ghost[1] + dy)
    # Manhattan distance to Pacman must strictly decrease in an open room.
    before = abs(ghost[0] - pacman[0]) + abs(ghost[1] - pacman[1])
    after = abs(new_pos[0] - pacman[0]) + abs(new_pos[1] - pacman[1])
    assert after == before - 1


def test_two_ghosts_never_choose_the_same_destination():
    grid = _open_grid(7, 7)
    pacman = (1, 3)
    # Two ghosts on adjacent cells that would both prefer the same next cell
    # toward Pacman; anti-clumping must split them.
    ghost_a = (5, 3)
    ghost_b = (5, 4)
    grid[pacman] = Observation.PAC_MAN.value
    grid[ghost_a] = Observation.GHOST.value
    grid[ghost_b] = Observation.GHOST.value

    policy = GhostPursuitPolicy()
    actions = policy.choose_actions(grid, [ghost_a, ghost_b], pacman)

    dest_a = (ghost_a[0] + _delta(actions[0])[0], ghost_a[1] + _delta(actions[0])[1])
    dest_b = (ghost_b[0] + _delta(actions[1])[0], ghost_b[1] + _delta(actions[1])[1])
    assert dest_a != dest_b


def test_boxed_ghost_returns_a_valid_action():
    # Ghost fully walled in: policy must still return an Action, not raise.
    grid = _open_grid(5, 5)
    ghost = (2, 2)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        grid[ghost[0] + dx, ghost[1] + dy] = Observation.WALL.value
    grid[ghost] = Observation.GHOST.value
    pacman = (1, 1)  # unreachable, behind walls

    policy = GhostPursuitPolicy()
    actions = policy.choose_actions(grid, [ghost], pacman)
    assert isinstance(actions[0], Action)
