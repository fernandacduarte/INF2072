from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from custom_environment.utils import build_maze, is_connected, parse_layout
from custom_environment.env.domain.constant import Observation
from custom_environment.env.pacman_environment import PacManEnvironment


MAZES = ["default", "pinklike"]


@pytest.mark.parametrize("maze", MAZES)
def test_maze_shape_and_border(maze: str) -> None:
    grid = build_maze(maze).grid
    assert grid.shape == (20, 20)
    assert (grid[0, :] == Observation.WALL.value).all()
    assert (grid[-1, :] == Observation.WALL.value).all()
    assert (grid[:, 0] == Observation.WALL.value).all()
    assert (grid[:, -1] == Observation.WALL.value).all()


@pytest.mark.parametrize("maze", MAZES)
def test_map_declares_spawns(maze: str) -> None:
    spec = build_maze(maze)
    # Both 20x20 maps declare exactly two ghosts and one pacman.
    assert len(spec.ghost_spawns) == 2
    assert isinstance(spec.pacman_spawn, tuple)
    # Every spawn cell must be an open (non-wall) cell.
    assert spec.grid[spec.pacman_spawn] == Observation.EMPTY.value
    for spawn in spec.ghost_spawns:
        assert spec.grid[spawn] == Observation.EMPTY.value
    # Spawn cells carry no pellet underneath.
    assert not spec.pellet_mask[spec.pacman_spawn]
    for spawn in spec.ghost_spawns:
        assert not spec.pellet_mask[spawn]


@pytest.mark.parametrize("maze", MAZES)
def test_maze_has_cosmetic_pellets(maze: str) -> None:
    assert build_maze(maze).pellet_mask.sum() > 0


@pytest.mark.parametrize("maze", MAZES)
def test_maze_is_fully_connected(maze: str) -> None:
    assert is_connected(build_maze(maze).grid)


def test_unknown_maze_name_raises() -> None:
    with pytest.raises(ValueError):
        build_maze("does_not_exist")


def test_parse_layout_rejects_missing_pacman() -> None:
    with pytest.raises(ValueError):
        parse_layout(["%%%%", "%G.%", "%%%%"])  # has a ghost but no pacman


@pytest.mark.parametrize("maze", MAZES)
def test_pettingzoo_parallel_api_compliance(maze: str) -> None:
    from pettingzoo.test import parallel_api_test

    env = PacManEnvironment(global_view=build_maze(maze))
    parallel_api_test(env, num_cycles=200)
