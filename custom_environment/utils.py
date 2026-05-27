import numpy as np
from collections import deque
from custom_environment.env.domain.enum import Observation

DIRECTIONS = [(1, 0), (-1, 0), (0, 1), (0, -1)]


class Graph:
    def __init__(self, map: np.ndarray):
        self._map = map

    def bfs_target_search(self,
        initial_state: tuple[int, int],
        target_state: tuple[int, int]
    ) -> list[tuple[int, int]] | None:
        visited = set()
        parent = {}
        queue = deque([initial_state])
        visited.add(initial_state)

        while queue:
            state = queue.popleft()
            if state == target_state:
                return self._build_path(parent, target_state)

            for neighbor in self._get_neighbors(state):
                if neighbor not in visited:
                    visited.add(neighbor)
                    parent[neighbor] = state
                    queue.append(neighbor)

        return None

    def _get_neighbors(
        self, state: tuple[int, int]
    ) -> list[tuple[int, int]]:
        neighbors = []
        for direction in DIRECTIONS:
            new_coord_x = state[0] + direction[0]
            new_coord_y = state[1] + direction[1]
            if self._map[new_coord_x][new_coord_y] != Observation.WALL:
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
