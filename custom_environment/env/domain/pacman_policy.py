"""Deterministic, defense-first Pacman policy.

Survival is the primary objective; eating pellets is strictly secondary. Each
step the policy scores Pacman's legal moves with a lexicographic key:

    (1) safety  -- the BFS distance from the destination cell to the nearest
        ghost, capped at ``PACMAN_SAFE_DISTANCE``. Higher is safer. Capping
        means that once Pacman is "safe enough" the extra distance stops
        mattering, so it does not flee forever.
    (2) pellet progress -- how close the destination cell is to the nearest
        remaining pellet. Only ever breaks ties between equally-safe moves.

Because safety is the first key, Pacman always prefers the move that keeps it
furthest from ghosts; it pursues pellets only among moves that are already at
the safety cap. This makes "flee the ghosts" dominate "grab pellets" without an
explicit state machine: when threatened, the safety term separates the moves and
defense wins; when safe, all moves share the capped safety and pellets decide.

Two multi-source BFS flood-fills per step (from all ghosts, and from all
pellets) make the scoring O(R*C) regardless of pellet count.

Design rationale: research-000006 / plan-000007 (defense-first revision).
"""

from collections import deque

import numpy as np

from custom_environment.env.domain.constant import (
    Action,
    Observation,
    PACMAN_SAFE_DISTANCE,
)


# Movement deltas paired with the Action that produces them. Matrix coordinates:
# x = row, y = column (matches PacManEnvironment._execute_action).
_MOVES: list[tuple[tuple[int, int], Action]] = [
    ((0, 1), Action.MOVE_RIGHT),
    ((0, -1), Action.MOVE_LEFT),
    ((-1, 0), Action.MOVE_UP),
    ((1, 0), Action.MOVE_DOWN),
]

_INF = float("inf")


class PacmanPolicy:
    """Defense-first Pacman controller.

    Pure function of the observable world state: it never mutates the grid or
    the pellet mask, and holds no cross-step state, so the same instance is safe
    to reuse across episodes (the environment still creates a fresh one per
    ``reset()`` for clarity).
    """

    # The safety cap, exposed as an attribute so experiments can tune defensive
    # conservatism without touching the constant.
    safe_distance: int = PACMAN_SAFE_DISTANCE

    def choose_action(
        self,
        global_view: np.ndarray,
        pellet_mask: np.ndarray | None,
        ghost_positions: list[tuple[int, int]],
        pacman_pos: tuple[int, int],
    ) -> Action:
        """Return the next Pacman move: maximize safety first, pellets second.

        Falls back to a random valid action only when Pacman has no legal move
        (fully boxed in), so the environment never stalls.
        """
        # Distance from every passable cell to the nearest ghost / nearest
        # pellet, each via a single multi-source BFS.
        ghost_dist = self._multi_source_bfs(global_view, ghost_positions)
        pellet_dist = self._multi_source_bfs(
            global_view, self._pellet_cells(pellet_mask)
        )

        x, y = pacman_pos
        rows, cols = global_view.shape

        best_action: Action | None = None
        best_key: tuple[int, float] | None = None
        for (dx, dy), action in _MOVES:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < rows and 0 <= ny < cols):
                continue
            # Pacman may legally enter EMPTY cells. Stepping onto a GHOST cell is
            # suicide and onto a WALL is blocked, so both are excluded.
            if global_view[nx, ny] != Observation.EMPTY.value:
                continue

            cell = (nx, ny)
            # Safety: distance to nearest ghost, capped. No ghosts reachable ->
            # maximally safe.
            safety = min(ghost_dist.get(cell, _INF), self.safe_distance)
            # Pellet progress: closer to a pellet is better, so negate distance.
            progress = -pellet_dist.get(cell, _INF)
            key = (safety, progress)

            if best_key is None or key > best_key:
                best_key = key
                best_action = action

        if best_action is None:
            return Action.choose_random()
        return best_action

    # -- Helpers -----------------------------------------------------------

    @staticmethod
    def _pellet_cells(
        pellet_mask: np.ndarray | None,
    ) -> list[tuple[int, int]]:
        """Coordinates of all cells that still hold a pellet."""
        if pellet_mask is None:
            return []
        return [(int(r), int(c)) for r, c in np.argwhere(pellet_mask)]

    @staticmethod
    def _multi_source_bfs(
        global_view: np.ndarray,
        sources: list[tuple[int, int]],
    ) -> dict[tuple[int, int], int]:
        """BFS distance from every passable cell to the nearest source.

        All sources start at distance 0 and expand simultaneously; walls are
        impassable. Returns an empty map when there are no sources (callers read
        missing keys as infinitely far).
        """
        rows, cols = global_view.shape
        distances: dict[tuple[int, int], int] = {}
        queue: deque[tuple[int, int]] = deque()
        for src in sources:
            sx, sy = src
            if 0 <= sx < rows and 0 <= sy < cols and src not in distances:
                distances[src] = 0
                queue.append(src)

        while queue:
            x, y = queue.popleft()
            base = distances[(x, y)]
            for (dx, dy), _action in _MOVES:
                nx, ny = x + dx, y + dy
                neighbor = (nx, ny)
                if not (0 <= nx < rows and 0 <= ny < cols):
                    continue
                if neighbor in distances:
                    continue
                if global_view[nx, ny] == Observation.WALL.value:
                    continue
                distances[neighbor] = base + 1
                queue.append(neighbor)
        return distances
