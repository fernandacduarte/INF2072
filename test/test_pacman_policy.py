"""Smoke tests for the deterministic safety-aware Pacman policy (plan-000007).

The policy replaces the former random Pacman with a BFS flood-fill controller
that seeks the nearest safe pellet and flees ghosts within
``PACMAN_DANGER_RADIUS``. These tests build small ``MazeSpec`` layouts via
``parse_layout`` so spawns stay in bounds, then drive ``PacmanPolicy`` directly
on the resulting grid and pellet mask.
"""

from pathlib import Path
import sys

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from custom_environment.env.domain.constant import Action, Observation
from custom_environment.env.domain.pacman_policy import PacmanPolicy
from custom_environment.env.pacman_environment import PacManEnvironment
from custom_environment.utils import parse_layout


def _open_grid(rows: int, cols: int) -> np.ndarray:
    """A grid of EMPTY interior cells surrounded by a WALL border.

    Built directly (not via ``parse_layout``) so policy-only tests can omit
    ghost spawns; the policy reads ghost positions from its argument, not the
    grid.
    """
    grid = np.full((rows, cols), Observation.EMPTY.value, dtype=np.int64)
    grid[0, :] = Observation.WALL.value
    grid[-1, :] = Observation.WALL.value
    grid[:, 0] = Observation.WALL.value
    grid[:, -1] = Observation.WALL.value
    return grid


def test_seeks_adjacent_pellet_when_safe():
    """Step 2 Tests: with a pellet one cell to the right and no ghosts near,
    the policy returns MOVE_RIGHT."""
    grid = _open_grid(3, 7)  # Pacman at (1,1), open corridor to the right
    pellet_mask = np.zeros_like(grid, dtype=bool)
    pellet_mask[1, 2] = True  # pellet immediately right of Pacman

    policy = PacmanPolicy()
    action = policy.choose_action(
        global_view=grid,
        pellet_mask=pellet_mask,
        ghost_positions=[],
        pacman_pos=(1, 1),
    )
    assert action == Action.MOVE_RIGHT


def test_flees_away_from_adjacent_ghost():
    """When a ghost sits inside the danger radius, the policy moves Pacman so
    that its distance to that ghost increases (it flees)."""
    # Pacman at (1,3); ghost at (1,1) -> BFS distance 2 (<= PACMAN_DANGER_RADIUS).
    grid = _open_grid(3, 9)
    pellet_mask = np.zeros_like(grid, dtype=bool)

    policy = PacmanPolicy()
    action = policy.choose_action(
        global_view=grid,
        pellet_mask=pellet_mask,
        ghost_positions=[(1, 1)],
        pacman_pos=(1, 3),
    )
    # Fleeing from a ghost on the left means moving right (away).
    assert action == Action.MOVE_RIGHT


def test_falls_back_to_valid_action_when_no_pellets():
    """No pellets and no threat -> policy still returns an Action (random
    fallback) rather than raising."""
    grid = _open_grid(3, 5)
    pellet_mask = np.zeros_like(grid, dtype=bool)  # nothing to eat

    policy = PacmanPolicy()
    action = policy.choose_action(
        global_view=grid,
        pellet_mask=pellet_mask,
        ghost_positions=[],
        pacman_pos=(1, 1),
    )
    assert isinstance(action, Action)


def test_environment_step_cycle_runs_with_policy():
    """Integration: a full env episode steps to completion with the policy
    active and never raises."""
    layout = [
        "%%%%%%%%%",
        "%P...G.G%",
        "%%%%%%%%%",
    ]
    env = PacManEnvironment(global_view=parse_layout(layout))
    env.reset()
    for _ in range(20):
        actions = {ghost.id: Action.MOVE_LEFT for ghost in env.ghosts}
        if not env.agents:
            break
        env.step(actions)
    # Reaching here without an exception is the smoke assertion.
    assert True
