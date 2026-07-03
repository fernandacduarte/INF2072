"""Scripted greedy-pursuit ghost policy (upper-bound pursuer).

This is the mirror image of ``PacmanPolicy``: where Pacman flees the nearest
ghost, each ghost here steps along its BFS-shortest path *toward* Pacman's
current cell. It needs no training, so it provides an empirical *ceiling* on
the capture rate any learned ghost team could achieve under the same dynamics
(``custom_environment/ceiling_eval.py``). A learned policy that stalls far
below this ceiling is leaving capture on the table; a ceiling that is itself
low means capture is structurally hard (see research-000033 / research-000035).

The pursuit is greedy, not game-theoretically optimal: each ghost takes the
legal move that most reduces its own BFS distance to Pacman. A simple
anti-clumping rule keeps two ghosts from collapsing onto the same next cell so
the team spreads to cut off escape routes rather than single-filing down one
corridor.

Pure function of the observable world state: it holds no cross-step state, so a
single instance is safe to reuse across episodes.
"""

from collections import deque

import numpy as np

from custom_environment.env.domain.constant import Action, Observation


# Movement deltas paired with the Action that produces them. Matrix coordinates:
# x = row, y = column (matches PacManEnvironment._execute_action and PacmanPolicy).
_MOVES: list[tuple[tuple[int, int], Action]] = [
    ((0, 1), Action.MOVE_RIGHT),
    ((0, -1), Action.MOVE_LEFT),
    ((-1, 0), Action.MOVE_UP),
    ((1, 0), Action.MOVE_DOWN),
]

_INF = float("inf")


class GhostPursuitPolicy:
    """Greedy BFS pursuit controller for the whole ghost team."""

    def choose_actions(
        self,
        global_view: np.ndarray,
        ghost_positions: list[tuple[int, int]],
        pacman_pos: tuple[int, int],
    ) -> list[Action]:
        """Return one action per ghost, in the order of ``ghost_positions``.

        Each ghost picks the legal move minimizing BFS distance to Pacman. A
        ghost with no legal move (fully boxed) gets a random action so the
        environment never stalls. Anti-clumping: two ghosts never commit to the
        same destination cell -- the later ghost falls back to its next-best
        legal step (or stays put if none remains).
        """
        # Single multi-source-free BFS flood-fill *from Pacman* gives every cell's
        # distance to Pacman in O(R*C); each ghost then reads its neighbours.
        distance_to_pacman = self._bfs_from(global_view, pacman_pos)

        claimed_cells: set[tuple[int, int]] = set()
        actions: list[Action] = []
        for position in ghost_positions:
            action = self._choose_one(
                global_view, position, distance_to_pacman, claimed_cells
            )
            actions.append(action)
        return actions

    # -- Helpers -----------------------------------------------------------

    def _choose_one(
        self,
        global_view: np.ndarray,
        position: tuple[int, int],
        distance_to_pacman: dict[tuple[int, int], int],
        claimed_cells: set[tuple[int, int]],
    ) -> Action:
        legal = self._legal_actions(global_view, position)
        if not legal:
            return Action.choose_random()

        x, y = position
        # Rank legal moves by resulting BFS distance to Pacman (closer is better);
        # skip cells another ghost already claimed this step (anti-clumping).
        ranked: list[tuple[float, Action, tuple[int, int]]] = []
        for action in legal:
            dx, dy = _action_to_delta(action)
            cell = (x + dx, y + dy)
            dist = distance_to_pacman.get(cell, _INF)
            ranked.append((dist, action, cell))
        ranked.sort(key=lambda item: item[0])

        for _dist, action, cell in ranked:
            if cell not in claimed_cells:
                claimed_cells.add(cell)
                return action

        # Every closer cell is already claimed: take the best move anyway rather
        # than freezing (claim it so a third ghost still avoids it).
        best_action, best_cell = ranked[0][1], ranked[0][2]
        claimed_cells.add(best_cell)
        return best_action

    @staticmethod
    def _legal_actions(
        global_view: np.ndarray,
        position: tuple[int, int],
    ) -> list[Action]:
        rows, cols = global_view.shape
        x, y = position
        actions: list[Action] = []
        for (dx, dy), action in _MOVES:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < rows and 0 <= ny < cols):
                continue
            # Ghosts may enter empty cells or the cell Pacman occupies (capture).
            if global_view[nx, ny] in (
                Observation.EMPTY.value,
                Observation.PAC_MAN.value,
            ):
                actions.append(action)
        return actions

    @staticmethod
    def _bfs_from(
        global_view: np.ndarray,
        source: tuple[int, int],
    ) -> dict[tuple[int, int], int]:
        """BFS distance from ``source`` to every passable cell.

        Walls are impassable. The source cell (Pacman) is included at distance 0
        even though it is painted PAC_MAN rather than EMPTY, so a ghost standing
        adjacent reads distance 1 toward it.
        """
        rows, cols = global_view.shape
        sx, sy = source
        distances: dict[tuple[int, int], int] = {}
        if not (0 <= sx < rows and 0 <= sy < cols):
            return distances
        distances[source] = 0
        queue: deque[tuple[int, int]] = deque([source])
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


def _action_to_delta(action: Action) -> tuple[int, int]:
    for (dx, dy), candidate in _MOVES:
        if candidate == action:
            return dx, dy
    raise ValueError(f"Unknown action: {action!r}")
