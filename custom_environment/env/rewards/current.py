"""The pre-refactor shared team reward, isolated as a strategy."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from custom_environment.env.rewards.base import (
    GhostTransition,
    Position,
    RewardContext,
    RewardResult,
    RewardStrategy,
    RewardTerm,
)


@dataclass(frozen=True, slots=True)
class CurrentRewardWeights:
    get_pacman: float = 30.0
    pacman_timeout_win: float = -20.0
    pacman_win_pellets: float = -20.0
    newly_spotted: float = 1.0
    currently_visible: float = 0.2
    enter_recently_unvisited_tile: float = 0.15
    reveal_unseen_local_cells: float = 0.03
    valid_move: float = 0.05
    invalid_move: float = -0.08
    stay_still: float = -0.03
    repeated_direction_reversal: float = -0.04
    two_step_cycle: float = -0.06
    overlap_or_same_corridor: float = -0.05
    timestep: float = -0.01
    potential_shaping_alpha: float = 0.5
    recently_unvisited_window: int = 10
    newly_spotted_min_unseen_steps: int = 6


@dataclass(frozen=True, slots=True)
class CurrentRewardWeightsV2:
    get_pacman: float = 40.0
    pacman_timeout_win: float = -35.0
    pacman_win_pellets: float = -35.0
    newly_spotted: float = 0.5
    currently_visible: float = 0.6
    enter_recently_unvisited_tile: float = 0.03
    reveal_unseen_local_cells: float = 0.01
    valid_move: float = 0.03
    invalid_move: float = -0.08
    stay_still: float = -0.03
    repeated_direction_reversal: float = -0.05
    two_step_cycle: float = -0.08
    no_progress_visible: float = 0.0
    overlap_or_same_corridor: float = -0.05
    timestep: float = -0.01
    potential_shaping_alpha: float = 1.2
    potential_second_ghost_weight: float = 0.5
    recently_unvisited_window: int = 10
    newly_spotted_min_unseen_steps: int = 6
    no_progress_visible_grace_steps: int = 2


class CurrentGitTeamReward(RewardStrategy):
    """Reward strategy matching git baseline weights and logic."""

    strategy_id = "current_git"

    def __init__(self, weights: CurrentRewardWeights | None = None) -> None:
        self.weights = weights or CurrentRewardWeights()
        self._last_potential: float | None = None
        self._last_any_pacman_visible = False
        self._unseen_steps = self.weights.newly_spotted_min_unseen_steps
        self._last_move_direction: dict[str, Position | None] = {}
        self._reverse_streak: dict[str, int] = {}
        self._recent_positions: dict[str, deque[Position]] = {}
        self._seen_local_cells: dict[str, set[Position]] = {}
        self._last_tile_visit_step: dict[str, dict[Position, int]] = {}

    def reset(self, initial_context: RewardContext) -> None:
        self._last_potential = None
        self._last_any_pacman_visible = False
        self._unseen_steps = self.weights.newly_spotted_min_unseen_steps
        self._last_move_direction = {ghost.ghost_id: None for ghost in initial_context.ghosts}
        self._reverse_streak = {ghost.ghost_id: 0 for ghost in initial_context.ghosts}
        self._recent_positions = {
            ghost.ghost_id: deque([ghost.current_position], maxlen=2)
            for ghost in initial_context.ghosts
        }
        self._seen_local_cells = {
            ghost.ghost_id: self._local_cells(
                ghost.current_position,
                initial_context.ghost_view_radius,
            )
            for ghost in initial_context.ghosts
        }
        self._last_tile_visit_step = {
            ghost.ghost_id: {ghost.current_position: 0}
            for ghost in initial_context.ghosts
        }

    def compute(self, context: RewardContext) -> RewardResult:
        w = self.weights
        terms = [RewardTerm("timestep", w.timestep)]

        if context.capture_happened:
            terms.append(RewardTerm("GET_PACMAN", w.get_pacman, "terminal"))

        min_distance = self._minimum_distance(context)
        visibility_progress = False
        if min_distance is not None:
            potential = -w.potential_shaping_alpha * float(min_distance)
            if self._last_potential is not None:
                terms.append(
                    RewardTerm("potential_shaping", potential - self._last_potential)
                )
            if self._last_potential is None or potential > self._last_potential:
                visibility_progress = True
            self._last_potential = potential

        if context.pacman_visible:
            if (
                not self._last_any_pacman_visible
                and self._unseen_steps >= w.newly_spotted_min_unseen_steps
            ):
                terms.append(RewardTerm("newly_spotted", w.newly_spotted))
            if visibility_progress:
                terms.append(RewardTerm("currently_visible", w.currently_visible))
            self._unseen_steps = 0
        else:
            self._unseen_steps += 1

        for ghost in context.ghosts:
            moved = ghost.previous_position != ghost.current_position
            if not moved:
                value = w.invalid_move if ghost.invalid_move else w.stay_still
                name = "invalid_move" if ghost.invalid_move else "stay_still"
                terms.append(RewardTerm(name, value))
            else:
                terms.append(RewardTerm("valid_move", w.valid_move))
                if self._is_recently_unvisited(ghost, context.step_count):
                    terms.append(
                        RewardTerm(
                            "recently_unvisited_tile",
                            w.enter_recently_unvisited_tile,
                        )
                    )
                reverse_streak = self._update_movement_history(ghost)
                if reverse_streak >= 1:
                    factor = min(reverse_streak, 4)
                    terms.append(
                        RewardTerm(
                            "repeated_direction_reversal",
                            w.repeated_direction_reversal * float(factor),
                        )
                    )
                if self._is_two_step_cycle(ghost):
                    terms.append(RewardTerm("two_step_cycle", w.two_step_cycle))

            if self._reveals_unseen_cells(ghost, context.ghost_view_radius):
                terms.append(
                    RewardTerm(
                        "reveal_unseen_local_cells",
                        w.reveal_unseen_local_cells,
                    )
                )

            # Keep a short trajectory memory so the next step can detect A->B->A.
            self._recent_positions.setdefault(ghost.ghost_id, deque(maxlen=2)).append(
                ghost.current_position
            )

        pair_violations = self._count_overlap_or_same_corridor_violations(context.ghosts)
        if pair_violations > 0:
            terms.append(
                RewardTerm(
                    "overlap_or_same_corridor",
                    w.overlap_or_same_corridor * float(pair_violations),
                )
            )

        if context.timeout_happened:
            terms.append(RewardTerm("PACMAN_TIMEOUT_WIN", w.pacman_timeout_win, "terminal"))
        if context.pacman_win_happened:
            terms.append(RewardTerm("PACMAN_WIN_PALLETS", w.pacman_win_pellets, "terminal"))

        self._last_any_pacman_visible = context.pacman_visible
        return RewardResult(tuple(terms))

    @staticmethod
    def _local_cells(position: Position, radius: int) -> set[Position]:
        x, y = position
        return {
            (x + dx, y + dy)
            for dx in range(-radius, radius + 1)
            for dy in range(-radius, radius + 1)
        }

    def _reveals_unseen_cells(self, ghost: GhostTransition, view_radius: int) -> bool:
        seen = self._seen_local_cells.setdefault(ghost.ghost_id, set())
        current = self._local_cells(ghost.current_position, view_radius)
        revealed = not current.issubset(seen)
        seen.update(current)
        return revealed

    def _is_recently_unvisited(self, ghost: GhostTransition, step_count: int) -> bool:
        visits = self._last_tile_visit_step.setdefault(ghost.ghost_id, {})
        last_visit = visits.get(ghost.current_position)
        result = (
            last_visit is None
            or (step_count - int(last_visit)) > self.weights.recently_unvisited_window
        )
        visits[ghost.current_position] = step_count
        return result

    def _update_movement_history(self, ghost: GhostTransition) -> int:
        direction = self._direction(ghost.previous_position, ghost.current_position)
        last = self._last_move_direction.get(ghost.ghost_id)
        if last is not None and direction == (-last[0], -last[1]):
            self._reverse_streak[ghost.ghost_id] = self._reverse_streak.get(ghost.ghost_id, 0) + 1
        else:
            self._reverse_streak[ghost.ghost_id] = 0
        self._last_move_direction[ghost.ghost_id] = direction
        return self._reverse_streak[ghost.ghost_id]

    def _is_two_step_cycle(self, ghost: GhostTransition) -> bool:
        history = self._recent_positions.get(ghost.ghost_id)
        if history is None or len(history) < 2:
            return False
        # Detect immediate AB->A returns: previous was B and two steps ago was A.
        return ghost.current_position == history[0] and ghost.previous_position == history[1]

    @staticmethod
    def _direction(previous: Position, current: Position) -> Position:
        return current[0] - previous[0], current[1] - previous[1]

    @classmethod
    def _count_overlap_or_same_corridor_violations(
        cls, ghosts: tuple[GhostTransition, ...]
    ) -> int:
        violations = 0
        for index, ghost_a in enumerate(ghosts):
            for ghost_b in ghosts[index + 1 :]:
                if ghost_a.current_position == ghost_b.current_position:
                    violations += 1
                    continue
                if ghost_a.previous_position == ghost_a.current_position:
                    continue
                if ghost_b.previous_position == ghost_b.current_position:
                    continue
                dir_a = cls._direction(ghost_a.previous_position, ghost_a.current_position)
                dir_b = cls._direction(ghost_b.previous_position, ghost_b.current_position)
                same_row = ghost_a.current_position[0] == ghost_b.current_position[0]
                same_col = ghost_a.current_position[1] == ghost_b.current_position[1]
                if not (same_row or same_col):
                    continue
                distance = sum(
                    abs(a - b)
                    for a, b in zip(ghost_a.current_position, ghost_b.current_position)
                )
                if dir_a == dir_b and distance <= 2:
                    violations += 1
                # Also penalize adjacent ghosts ping-ponging in opposite directions.
                elif dir_a == (-dir_b[0], -dir_b[1]) and distance <= 1:
                    violations += 1
        return violations

    def _minimum_distance(self, context: RewardContext) -> int | None:
        distances = [
            self._bfs_distance(
                ghost.current_position,
                context.pacman_position,
                context.board_shape,
                context.wall_positions,
            )
            for ghost in context.ghosts
        ]
        reachable = [distance for distance in distances if distance is not None]
        return min(reachable) if reachable else None

    @staticmethod
    def _bfs_distance(
        start: Position,
        goal: Position,
        board_shape: tuple[int, int],
        walls: frozenset[Position],
    ) -> int | None:
        if start == goal:
            return 0
        rows, cols = board_shape
        queue = deque([(start, 0)])
        visited = {start}
        while queue:
            (x, y), distance = queue.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                neighbor = (x + dx, y + dy)
                if not (0 <= neighbor[0] < rows and 0 <= neighbor[1] < cols):
                    continue
                if neighbor in visited or neighbor in walls:
                    continue
                if neighbor == goal:
                    return distance + 1
                visited.add(neighbor)
                queue.append((neighbor, distance + 1))
        return None


class CurrentTeamReward(CurrentGitTeamReward):
    """Locally modified reward logic/weights without overlap/corridor penalty."""

    strategy_id = "current"

    def __init__(self, weights: CurrentRewardWeightsV2 | None = None) -> None:
        self.weights = weights or CurrentRewardWeightsV2()
        self._last_potential: float | None = None
        self._last_any_pacman_visible = False
        self._visible_no_progress_steps = 0
        self._unseen_steps = self.weights.newly_spotted_min_unseen_steps
        self._last_move_direction: dict[str, Position | None] = {}
        self._reverse_streak: dict[str, int] = {}
        self._recent_positions: dict[str, deque[Position]] = {}
        self._seen_local_cells: dict[str, set[Position]] = {}
        self._last_tile_visit_step: dict[str, dict[Position, int]] = {}

    def reset(self, initial_context: RewardContext) -> None:
        self._last_potential = None
        self._last_any_pacman_visible = False
        self._visible_no_progress_steps = 0
        self._unseen_steps = self.weights.newly_spotted_min_unseen_steps
        self._last_move_direction = {ghost.ghost_id: None for ghost in initial_context.ghosts}
        self._reverse_streak = {ghost.ghost_id: 0 for ghost in initial_context.ghosts}
        self._recent_positions = {
            ghost.ghost_id: deque([ghost.current_position], maxlen=2)
            for ghost in initial_context.ghosts
        }
        self._seen_local_cells = {
            ghost.ghost_id: self._local_cells(
                ghost.current_position,
                initial_context.ghost_view_radius,
            )
            for ghost in initial_context.ghosts
        }
        self._last_tile_visit_step = {
            ghost.ghost_id: {ghost.current_position: 0}
            for ghost in initial_context.ghosts
        }

    def compute(self, context: RewardContext) -> RewardResult:
        w = self.weights
        terms = [RewardTerm("timestep", w.timestep)]

        if context.capture_happened:
            terms.append(RewardTerm("GET_PACMAN", w.get_pacman, "terminal"))

        team_distance = self._team_distance(context)
        visibility_progress = False
        if team_distance is not None:
            potential = -w.potential_shaping_alpha * float(team_distance)
            if self._last_potential is not None:
                terms.append(
                    RewardTerm("potential_shaping", potential - self._last_potential)
                )
            if self._last_potential is None or potential > self._last_potential:
                visibility_progress = True
            self._last_potential = potential

        if context.pacman_visible:
            if (
                not self._last_any_pacman_visible
                and self._unseen_steps >= w.newly_spotted_min_unseen_steps
            ):
                terms.append(RewardTerm("newly_spotted", w.newly_spotted))
            terms.append(RewardTerm("currently_visible", w.currently_visible))
            if visibility_progress:
                self._visible_no_progress_steps = 0
            elif self._last_potential is not None:
                self._visible_no_progress_steps += 1
                if self._visible_no_progress_steps > w.no_progress_visible_grace_steps:
                    terms.append(RewardTerm("no_progress_visible", w.no_progress_visible))
            self._unseen_steps = 0
        else:
            self._visible_no_progress_steps = 0
            self._unseen_steps += 1

        for ghost in context.ghosts:
            moved = ghost.previous_position != ghost.current_position
            if not moved:
                value = w.invalid_move if ghost.invalid_move else w.stay_still
                name = "invalid_move" if ghost.invalid_move else "stay_still"
                terms.append(RewardTerm(name, value))
            else:
                terms.append(RewardTerm("valid_move", w.valid_move))
                if (
                    not context.pacman_visible
                    and self._is_recently_unvisited(ghost, context.step_count)
                ):
                    terms.append(
                        RewardTerm(
                            "recently_unvisited_tile",
                            w.enter_recently_unvisited_tile,
                        )
                    )
                reverse_streak = self._update_movement_history(ghost)
                if reverse_streak >= 1:
                    factor = min(reverse_streak, 4)
                    terms.append(
                        RewardTerm(
                            "repeated_direction_reversal",
                            w.repeated_direction_reversal * float(factor),
                        )
                    )
                if self._is_two_step_cycle(ghost):
                    terms.append(RewardTerm("two_step_cycle", w.two_step_cycle))

            if (
                not context.pacman_visible
                and self._reveals_unseen_cells(ghost, context.ghost_view_radius)
            ):
                terms.append(
                    RewardTerm(
                        "reveal_unseen_local_cells",
                        w.reveal_unseen_local_cells,
                    )
                )

            self._recent_positions.setdefault(ghost.ghost_id, deque(maxlen=2)).append(
                ghost.current_position
            )

        if context.timeout_happened:
            terms.append(RewardTerm("PACMAN_TIMEOUT_WIN", w.pacman_timeout_win, "terminal"))
        if context.pacman_win_happened:
            terms.append(RewardTerm("PACMAN_WIN_PALLETS", w.pacman_win_pellets, "terminal"))

        self._last_any_pacman_visible = context.pacman_visible
        return RewardResult(tuple(terms))

    def _team_distance(self, context: RewardContext) -> float | None:
        distances = self._reachable_distances(context)
        if not distances:
            return None
        d1 = float(distances[0])
        if len(distances) == 1:
            return d1
        d2 = float(distances[1])
        return d1 + self.weights.potential_second_ghost_weight * d2

    def _reachable_distances(self, context: RewardContext) -> list[int]:
        distances = [
            self._bfs_distance(
                ghost.current_position,
                context.pacman_position,
                context.board_shape,
                context.wall_positions,
            )
            for ghost in context.ghosts
        ]
        reachable = sorted(distance for distance in distances if distance is not None)
        return reachable


class CurrentWithOverlapOrSameCorridor(CurrentTeamReward):
    """V2 reward variant with overlap/same-corridor pair penalty enabled."""

    strategy_id = "current_with_overlap_or_same_corridor"

    def compute(self, context: RewardContext) -> RewardResult:
        result = super().compute(context)
        pair_violations = self._count_overlap_or_same_corridor_violations(context.ghosts)
        if pair_violations <= 0:
            return result
        return RewardResult(
            result.terms
            + (
                RewardTerm(
                    "overlap_or_same_corridor",
                    self.weights.overlap_or_same_corridor * float(pair_violations),
                ),
            )
        )
