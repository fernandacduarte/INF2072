import numpy as np
from collections import deque
from custom_environment.env.domain.constant import Observation

DIRECTIONS = [(1, 0), (-1, 0), (0, 1), (0, -1)]


class Graph:
    def __init__(self, map: np.ndarray):
        self._map = map

    def _get_neighbors(
        self, state: tuple[int, int]
    ) -> list[tuple[int, int]]:
        neighbors = []
        for direction in DIRECTIONS:
            new_coord_x = state[0] + direction[0]
            new_coord_y = state[1] + direction[1]
            # Limita vizinhos ao patch local 3x3
            if 0 <= new_coord_x < 3 and 0 <= new_coord_y < 3:
                if self._map[new_coord_x][new_coord_y] != Observation.WALL.value:
                    neighbors.append((new_coord_x, new_coord_y))

        return neighbors

    @staticmethod
    def _build_path(
        parent: dict[tuple[int, int], tuple[int, int]],
        target_state: tuple[int, int]
    ) -> list[tuple[int, int]]:
        path = []
        current_state = target_state
        while current_state:
            path.append(current_state)
            current_state = parent.get(current_state)

        return path


def create_grid(size: int = 20) -> np.ndarray:
    # Initialize an empty grid
    grid = np.full((size, size), Observation.EMPTY.value, dtype=np.uint8)

    # Build walls on the perimeter
    grid[0, :] = Observation.WALL.value
    grid[-1, :] = Observation.WALL.value
    grid[:, 0] = Observation.WALL.value
    grid[:, -1] = Observation.WALL.value

    # Build internal walls
    wall_height = 1
    wall_width = 3
    free_row_space = 1
    free_column_space = 1

    row = 2
    while row + wall_width - 1 < size - 1:
        col = 2
        while col + wall_height - 1 < size - 1:
            grid[row, col:col+wall_width] = Observation.WALL.value
            col += wall_width + free_column_space
        row += wall_height + free_row_space

    return grid
