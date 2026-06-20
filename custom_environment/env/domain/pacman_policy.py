"""Deterministic, safety-aware Pacman policy.

Replaces the environment's random Pacman with a goal-directed agent whose
objective is *survival while eating pellets*. The policy runs a single BFS
flood-fill per decision (O(R*C), independent of pellet count) and routes Pacman
along ghost-free corridors toward the nearest reachable pellet. When a ghost
comes within ``PACMAN_DANGER_RADIUS`` BFS cells, the policy abandons the pellet
goal, flees to the cell that maximizes the minimum distance to any ghost, then
holds that safe heading for a short cooldown before resuming the hunt.

A three-state machine (SEEKING_PELLET -> FLEEING -> COOLDOWN) governs the
behavior; the COOLDOWN state prevents oscillation at the danger-radius boundary.

Design rationale: research-000006 / plan-000007.
"""

from collections import deque
from enum import Enum, auto

import numpy as np

from custom_environment.env.domain.constant import (
    Action,
    Observation,
    PACMAN_DANGER_RADIUS,
)


# Movement deltas paired with the Action that produces them. Matrix coordinates:
# x = row, y = column (matches PacManEnvironment._execute_action).
_MOVES: list[tuple[tuple[int, int], Action]] = [
    ((0, 1), Action.MOVE_RIGHT),
    ((0, -1), Action.MOVE_LEFT),
    ((-1, 0), Action.MOVE_UP),
    ((1, 0), Action.MOVE_DOWN),
]


class _State(Enum):
    """Behavioral mode of the Pacman policy state machine."""

    SEEKING_PELLET = auto()  # Navigate toward the nearest safe pellet.
    FLEEING = auto()         # Move toward the safest reachable cell.
    COOLDOWN = auto()        # Hold a safe heading for a few steps post-flee.


class PacmanPolicy:
    """Pellet-maximizing Pacman policy with reactive ghost avoidance.

    The policy is a pure function of the observable environment state: it never
    mutates the grid or the pellet mask. A fresh instance should be created per
    episode (the environment does this on ``reset()``) so the state machine and
    cooldown counter start clean.
    """

    # Steps to hold the post-flee safe heading before re-evaluating the threat.
    FLEE_COOLDOWN = 3

    def __init__(self) -> None:
        self._state = _State.SEEKING_PELLET
        self._cooldown = 0

    def choose_action(
        self,
        global_view: np.ndarray,
        pellet_mask: np.ndarray | None,
        ghost_positions: list[tuple[int, int]],
        pacman_pos: tuple[int, int],
    ) -> Action:
        """Return the next Pacman move given the current world state.

        Falls back to a random valid action when no reachable pellet or safe
        cell exists (e.g. Pacman is boxed in), so the environment never stalls.
        """
        # Distances from Pacman over passable cells; used both for the danger
        # check and for pellet selection, so it is computed once per decision.
        dist_from_pacman = self._flood_fill(global_view, pacman_pos)

        ghost_distances = [
            dist_from_pacman[g]
            for g in ghost_positions
            if g in dist_from_pacman
        ]
        threatened = any(d <= PACMAN_DANGER_RADIUS for d in ghost_distances)

        self._advance_state(threatened)

        if self._state == _State.FLEEING:
            action = self._flee(global_view, ghost_positions, pacman_pos)
        else:
            # SEEKING_PELLET and COOLDOWN both pursue pellets; the difference is
            # only in how they transition (COOLDOWN counts down before it may
            # return to seeking). Exclude ghost danger zones from the path.
            blocked = self._danger_cells(global_view, ghost_positions)
            blocked.discard(pacman_pos)  # never block our own starting cell
            action = self._seek_pellet(
                global_view, pellet_mask, pacman_pos, blocked
            )

        if action is None:
            return Action.choose_random()
        return action

    # -- State machine -----------------------------------------------------

    def _advance_state(self, threatened: bool) -> None:
        """Apply the SEEKING_PELLET -> FLEEING -> COOLDOWN transitions."""
        if threatened:
            # A live threat always (re)starts the flee response.
            self._state = _State.FLEEING
            self._cooldown = self.FLEE_COOLDOWN
            return

        if self._state == _State.FLEEING:
            # Threat cleared this step: enter the cooldown hold.
            self._state = _State.COOLDOWN
            self._cooldown = self.FLEE_COOLDOWN
        elif self._state == _State.COOLDOWN:
            self._cooldown -= 1
            if self._cooldown <= 0:
                self._state = _State.SEEKING_PELLET
        else:
            self._state = _State.SEEKING_PELLET

    # -- Behaviors ---------------------------------------------------------

    def _seek_pellet(
        self,
        global_view: np.ndarray,
        pellet_mask: np.ndarray | None,
        pacman_pos: tuple[int, int],
        blocked: set[tuple[int, int]],
    ) -> Action | None:
        """Step toward the nearest reachable pellet along a ghost-free path."""
        if pellet_mask is None:
            return None

        # Re-run the flood-fill with danger cells excluded so the chosen pellet
        # is reachable *safely*, then pick the closest one.
        safe_dist = self._flood_fill(global_view, pacman_pos, blocked)
        nearest_pellet = None
        nearest_distance = None
        rows, cols = pellet_mask.shape
        for (row, col), distance in safe_dist.items():
            if 0 <= row < rows and 0 <= col < cols and pellet_mask[row, col]:
                if nearest_distance is None or distance < nearest_distance:
                    nearest_distance = distance
                    nearest_pellet = (row, col)

        if nearest_pellet is None:
            return None
        return self._first_step_toward(
            global_view, pacman_pos, nearest_pellet, blocked
        )

    def _flee(
        self,
        global_view: np.ndarray,
        ghost_positions: list[tuple[int, int]],
        pacman_pos: tuple[int, int],
    ) -> Action | None:
        """Step toward the reachable cell that is safest from every ghost.

        Safety of a cell = the minimum BFS distance from that cell to any
        ghost; the flee target maximizes this value. BFS distance (not Manhattan)
        is used because walls make straight-line distance unreliable in a maze.
        """
        if not ghost_positions:
            return None

        # Distance maps from each ghost over passable cells.
        ghost_maps = [self._flood_fill(global_view, g) for g in ghost_positions]
        reachable = self._flood_fill(global_view, pacman_pos)

        best_cell = None
        best_safety = None
        for cell in reachable:
            # Minimum distance to any ghost; unreachable-from-a-ghost cells are
            # treated as maximally safe.
            safety = min(
                (gm[cell] for gm in ghost_maps if cell in gm),
                default=float("inf"),
            )
            if best_safety is None or safety > best_safety:
                best_safety = safety
                best_cell = cell

        if best_cell is None or best_cell == pacman_pos:
            return None
        return self._first_step_toward(global_view, pacman_pos, best_cell)

    # -- Grid search helpers ----------------------------------------------

    def _danger_cells(
        self,
        global_view: np.ndarray,
        ghost_positions: list[tuple[int, int]],
    ) -> set[tuple[int, int]]:
        """All passable cells within PACMAN_DANGER_RADIUS of any ghost."""
        danger: set[tuple[int, int]] = set()
        for ghost in ghost_positions:
            for cell, distance in self._flood_fill(global_view, ghost).items():
                if distance <= PACMAN_DANGER_RADIUS:
                    danger.add(cell)
        return danger

    def _flood_fill(
        self,
        global_view: np.ndarray,
        start: tuple[int, int],
        blocked: set[tuple[int, int]] | None = None,
    ) -> dict[tuple[int, int], int]:
        """BFS distances from ``start`` over passable cells.

        Walls and any cell in ``blocked`` are impassable. ``start`` is always
        included at distance 0 even if it appears in ``blocked``.
        """
        rows, cols = global_view.shape
        distances = {start: 0}
        queue = deque([start])
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
                if blocked is not None and neighbor in blocked:
                    continue
                distances[neighbor] = base + 1
                queue.append(neighbor)
        return distances

    def _first_step_toward(
        self,
        global_view: np.ndarray,
        start: tuple[int, int],
        goal: tuple[int, int],
        blocked: set[tuple[int, int]] | None = None,
    ) -> Action | None:
        """The first action on a shortest ``start`` -> ``goal`` path.

        BFS with parent tracking, then walk the chain back to ``start``.
        Returns ``None`` when ``goal`` is unreachable.
        """
        if start == goal:
            return None

        rows, cols = global_view.shape
        parents: dict[tuple[int, int], tuple[int, int]] = {start: start}
        queue = deque([start])
        while queue:
            current = queue.popleft()
            if current == goal:
                break
            cx, cy = current
            for (dx, dy), _action in _MOVES:
                nx, ny = cx + dx, cy + dy
                neighbor = (nx, ny)
                if not (0 <= nx < rows and 0 <= ny < cols):
                    continue
                if neighbor in parents:
                    continue
                if global_view[nx, ny] == Observation.WALL.value:
                    continue
                if blocked is not None and neighbor in blocked:
                    continue
                parents[neighbor] = current
                queue.append(neighbor)

        if goal not in parents:
            return None

        # Walk back from goal to the cell adjacent to start.
        node = goal
        while parents[node] != start:
            node = parents[node]
        step_delta = (node[0] - start[0], node[1] - start[1])
        for (dx, dy), action in _MOVES:
            if (dx, dy) == step_delta:
                return action
        return None
