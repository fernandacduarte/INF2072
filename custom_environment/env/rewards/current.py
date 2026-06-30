"""The pre-refactor shared team reward, isolated as a strategy."""

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


@dataclass(frozen=True, slots=True)
class CaptureV0Weights:
    get_pacman: float = 45.0
    pacman_timeout_win: float = -40.0
    pacman_win_pellets: float = -45.0
    timestep: float = -0.015
    pacman_legal_moves_reduced: float = 1.0
    # potential_shaping_alpha: float = 0.9
    # potential_shaping_clip: float = 1.2
    # enter_recently_unvisited_tile: float = 0.03
    # reveal_unseen_local_cells: float = 0.01
    # valid_move: float = 0.02
    # invalid_move: float = -0.1
    # stay_still: float = -0.05
    # recently_unvisited_window: int = 12


class CaptureV0Reward(CurrentGitTeamReward):
    """Sparse capture-focused reward with minimal shaping."""

    strategy_id = "capture_v0"

    def __init__(self, weights: CaptureV0Weights | None = None) -> None:
        self.weights = weights or CaptureV0Weights()
        # self._last_potential: float | None = None
        # self._seen_local_cells: dict[str, set[Position]] = {}
        # self._last_tile_visit_step: dict[str, dict[Position, int]] = {}

    def reset(self, initial_context: RewardContext) -> None:
        _ = initial_context

    def compute(self, context: RewardContext) -> RewardResult:
        w = self.weights
        terms = [RewardTerm("timestep", w.timestep)]

        if context.capture_happened:
            terms.append(RewardTerm("GET_PACMAN", w.get_pacman, "terminal"))

        # min_distance = self._minimum_distance(context)
        # if min_distance is not None:
        #     potential = -w.potential_shaping_alpha * float(min_distance)
        #     if self._last_potential is not None:
        #         delta = potential - self._last_potential
        #         clipped = max(-w.potential_shaping_clip, min(w.potential_shaping_clip, delta))
        #         terms.append(RewardTerm("potential_shaping", clipped))
        #     self._last_potential = potential

        if context.pacman_visible:
            previous_legal_moves = self._count_pacman_legal_moves(
                context.pacman_previous_position,
                context.board_shape,
                context.wall_positions,
            )
            current_legal_moves = self._count_pacman_legal_moves(
                context.pacman_position,
                context.board_shape,
                context.wall_positions,
            )
            if current_legal_moves < previous_legal_moves:
                terms.append(
                    RewardTerm(
                        "pacman_legal_moves_reduced",
                        w.pacman_legal_moves_reduced,
                    )
                )

        # for ghost in context.ghosts:
        #     moved = ghost.previous_position != ghost.current_position
        #     if not moved:
        #         value = w.invalid_move if ghost.invalid_move else w.stay_still
        #         name = "invalid_move" if ghost.invalid_move else "stay_still"
        #         terms.append(RewardTerm(name, value))
        #     else:
        #         terms.append(RewardTerm("valid_move", w.valid_move))
        #         if (
        #             not context.pacman_visible
        #             and self._is_recently_unvisited(ghost, context.step_count)
        #         ):
        #             terms.append(
        #                 RewardTerm(
        #                     "recently_unvisited_tile",
        #                     w.enter_recently_unvisited_tile,
        #                 )
        #             )
        #
        #     if (
        #         not context.pacman_visible
        #         and self._reveals_unseen_cells(ghost, context.ghost_view_radius)
        #     ):
        #         terms.append(
        #             RewardTerm(
        #                 "reveal_unseen_local_cells",
        #                 w.reveal_unseen_local_cells,
        #             )
        #         )

        if context.timeout_happened:
            terms.append(RewardTerm("PACMAN_TIMEOUT_WIN", w.pacman_timeout_win, "terminal"))
        if context.pacman_win_happened:
            terms.append(RewardTerm("PACMAN_WIN_PALLETS", w.pacman_win_pellets, "terminal"))

        return RewardResult(tuple(terms))

    @staticmethod
    def _count_pacman_legal_moves(
        position: Position,
        board_shape: tuple[int, int],
        wall_positions: frozenset[Position],
    ) -> int:
        rows, cols = board_shape
        x, y = position
        legal_moves = 0
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if not (0 <= nx < rows and 0 <= ny < cols):
                continue
            if (nx, ny) in wall_positions:
                continue
            legal_moves += 1
        return legal_moves


@dataclass(frozen=True, slots=True)
class CaptureV0ImproveLegalMovesIncreaseTerminalRewardsReverseActionWeights:
    get_pacman: float = 100.0
    pacman_timeout_win: float = -100.0
    pacman_win_pellets: float = -100.0
    timestep: float = -0.01
    pacman_legal_moves_delta: float = 0.2
    reverse_action: float = -0.02


class CaptureV0ImproveLegalMovesIncreaseTerminalRewardsReverseAction(CaptureV0Reward):
    """Capture-v0 variant with smoother legal-move shaping and reverse-action penalty."""

    strategy_id = "capture_v0_improve_legal_moves_increase_terminal_rewards_reverse_action"

    def __init__(
        self,
        weights: CaptureV0ImproveLegalMovesIncreaseTerminalRewardsReverseActionWeights | None = None,
    ) -> None:
        self.weights = weights or CaptureV0ImproveLegalMovesIncreaseTerminalRewardsReverseActionWeights()
        self._last_action_by_ghost: dict[str, int | None] = {}

    def reset(self, initial_context: RewardContext) -> None:
        self._last_action_by_ghost = {
            ghost.ghost_id: ghost.action for ghost in initial_context.ghosts
        }

    def compute(self, context: RewardContext) -> RewardResult:
        w = self.weights
        terms = [RewardTerm("timestep", w.timestep)]

        if context.capture_happened:
            terms.append(RewardTerm("GET_PACMAN", w.get_pacman, "terminal"))

        if context.pacman_visible:
            previous_legal_moves = self._count_pacman_legal_moves(
                context.pacman_previous_position,
                context.board_shape,
                context.wall_positions,
            )
            current_legal_moves = self._count_pacman_legal_moves(
                context.pacman_position,
                context.board_shape,
                context.wall_positions,
            )
            legal_delta = float(previous_legal_moves - current_legal_moves)
            if legal_delta != 0.0:
                terms.append(
                    RewardTerm(
                        "pacman_legal_moves_delta",
                        w.pacman_legal_moves_delta * legal_delta,
                    )
                )

        for ghost in context.ghosts:
            previous_action = self._last_action_by_ghost.get(ghost.ghost_id)
            current_action = ghost.action
            if (
                previous_action is not None
                and current_action is not None
                and self._is_reverse_action(previous_action, current_action)
            ):
                terms.append(RewardTerm("reverse_action", w.reverse_action))
            self._last_action_by_ghost[ghost.ghost_id] = current_action

        if context.timeout_happened:
            terms.append(RewardTerm("PACMAN_TIMEOUT_WIN", w.pacman_timeout_win, "terminal"))
        if context.pacman_win_happened:
            terms.append(RewardTerm("PACMAN_WIN_PALLETS", w.pacman_win_pellets, "terminal"))

        return RewardResult(tuple(terms))

    @staticmethod
    def _is_reverse_action(previous_action: int, current_action: int) -> bool:
        reverse_action_by_action = {
            0: 1,  # RIGHT -> LEFT
            1: 0,  # LEFT -> RIGHT
            2: 3,  # UP -> DOWN
            3: 2,  # DOWN -> UP
        }
        return reverse_action_by_action.get(previous_action) == current_action


@dataclass(frozen=True, slots=True)
class CaptureV0ImproveStrategiesWeights:
    get_pacman: float = 100.0
    pacman_timeout_win: float = -100.0
    pacman_win_pellets: float = -100.0
    timestep: float = -0.01
    pacman_legal_moves_delta: float = 0.2
    reverse_action: float = -0.02


class CaptureV0ImproveStrategies(CaptureV0Reward):
    """Working copy of the reverse-action variant for iterating on strategy shaping."""

    strategy_id = "capture_v0_improve_strategies"

    def __init__(
        self,
        weights: CaptureV0ImproveStrategiesWeights | None = None,
    ) -> None:
        self.weights = weights or CaptureV0ImproveStrategiesWeights()
        self._last_action_by_ghost: dict[str, int | None] = {}

    def reset(self, initial_context: RewardContext) -> None:
        self._last_action_by_ghost = {
            ghost.ghost_id: ghost.action for ghost in initial_context.ghosts
        }

    def compute(self, context: RewardContext) -> RewardResult:
        w = self.weights
        terms = [RewardTerm("timestep", w.timestep)]

        if context.capture_happened:
            terms.append(RewardTerm("GET_PACMAN", w.get_pacman, "terminal"))

        if context.pacman_visible:
            previous_legal_moves = self._count_pacman_legal_moves(
                context.pacman_previous_position,
                context.board_shape,
                context.wall_positions,
            )
            current_legal_moves = self._count_pacman_legal_moves(
                context.pacman_position,
                context.board_shape,
                context.wall_positions,
            )
            legal_delta = float(previous_legal_moves - current_legal_moves)
            if legal_delta != 0.0:
                terms.append(
                    RewardTerm(
                        "pacman_legal_moves_delta",
                        w.pacman_legal_moves_delta * legal_delta,
                    )
                )

        for ghost in context.ghosts:
            previous_action = self._last_action_by_ghost.get(ghost.ghost_id)
            current_action = ghost.action
            if (
                previous_action is not None
                and current_action is not None
                and self._is_reverse_action(previous_action, current_action)
            ):
                terms.append(RewardTerm("reverse_action", w.reverse_action))
            self._last_action_by_ghost[ghost.ghost_id] = current_action

        if context.timeout_happened:
            terms.append(RewardTerm("PACMAN_TIMEOUT_WIN", w.pacman_timeout_win, "terminal"))
        if context.pacman_win_happened:
            terms.append(RewardTerm("PACMAN_WIN_PALLETS", w.pacman_win_pellets, "terminal"))

        return RewardResult(tuple(terms))

    @staticmethod
    def _is_reverse_action(previous_action: int, current_action: int) -> bool:
        reverse_action_by_action = {
            0: 1,  # RIGHT -> LEFT
            1: 0,  # LEFT -> RIGHT
            2: 3,  # UP -> DOWN
            3: 2,  # DOWN -> UP
        }
        return reverse_action_by_action.get(previous_action) == current_action


@dataclass(frozen=True, slots=True)
class CaptureV0PurePotentialShapingWeights:
    get_pacman: float = 100.0
    pacman_timeout_win: float = -100.0
    pacman_win_pellets: float = -100.0
    # Stronger than the bare -0.01 so that standing still always carries a real
    # cost: with exact (gamma=1) telescoping an in-place oscillation nets zero
    # shaping, leaving only this penalty, so camping near Pacman is unprofitable.
    timestep: float = -0.05
    potential_shaping_alpha: float = 0.7


class CaptureV0PurePotentialShaping(CaptureV0Reward):
    """Sparse capture base + pure potential-based reward shaping (PBRS).

    Adds the Ng/Harada/Russell (1999) telescoping term, in its undiscounted
    episodic form ``F = Phi(s') - Phi(s)`` with ``Phi = -alpha * min_ghost_dist``,
    the BFS distance of the *nearest* ghost to Pacman.

    Three deliberate choices, each fixing a failure mode observed empirically
    (research-000024 follow-ups):

    * **Exact telescoping (gamma = 1).** The cumulative shaping over an episode
      then equals ``Phi(end) - Phi(start)`` regardless of path, so any in-place
      oscillation nets exactly zero. A discounted ``gamma*Phi(s') - Phi(s)`` with
      ``Phi <= 0`` instead pays ``(1-gamma)*(-Phi) > 0`` per back-and-forth cycle,
      which a greedy policy farmed rather than capturing.
    * **Mean distance over ALL ghosts** (not ``min``, and not "two nearest"). With
      a shared team reward, a ``min`` potential only responds to the single nearest
      ghost, so the other ghosts receive a reward they cannot influence, get no
      gradient, and park in corners -- leaving a lone pursuer that a perfectly
      evading Pacman simply keeps at ``safe_distance`` forever. The mean rewards
      *every* ghost for closing in, so the team converges and surrounds Pacman
      (the coordination this project is about). It is also smooth, unlike the
      discontinuous "two nearest" metric.

    ``Phi`` reads Pacman's true position even when it is not visible to the ghosts.
    This is a centralized, training-time reward signal (CTDE): the executing ghost
    policies still observe only their partial local view and never see this distance.

    No movement, visibility, or ``reverse_action`` terms are emitted. ``Phi``
    shrinks toward 0 as the team closes in (0 only when every ghost sits on Pacman);
    timeout is left untouched (no Phi-zeroing).
    """

    strategy_id = "capture_v0_pure_potential_shaping"

    def __init__(
        self,
        weights: CaptureV0PurePotentialShapingWeights | None = None,
    ) -> None:
        self.weights = weights or CaptureV0PurePotentialShapingWeights()
        self._last_potential: float | None = None

    def reset(self, initial_context: RewardContext) -> None:
        _ = initial_context
        self._last_potential = None

    def compute(self, context: RewardContext) -> RewardResult:
        w = self.weights
        terms = [RewardTerm("timestep", w.timestep)]

        if context.capture_happened:
            terms.append(RewardTerm("GET_PACMAN", w.get_pacman, "terminal"))

        mean_distance = self._mean_distance(context)
        if mean_distance is not None:
            potential = -w.potential_shaping_alpha * float(mean_distance)
            if self._last_potential is not None:
                terms.append(
                    RewardTerm("potential_shaping", potential - self._last_potential)
                )
            self._last_potential = potential

        if context.timeout_happened:
            terms.append(RewardTerm("PACMAN_TIMEOUT_WIN", w.pacman_timeout_win, "terminal"))
        if context.pacman_win_happened:
            terms.append(RewardTerm("PACMAN_WIN_PALLETS", w.pacman_win_pellets, "terminal"))

        return RewardResult(tuple(terms))

    def _mean_distance(self, context: RewardContext) -> float | None:
        """Mean BFS distance of all reachable ghosts to Pacman.

        Rewards every ghost for closing in (so the team coordinates a surround),
        unlike ``min`` which only the nearest ghost can influence.
        """
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
        if not reachable:
            return None
        return sum(reachable) / len(reachable)


class CaptureV0PurePotentialShapingPellets(CaptureV0PurePotentialShaping):
    """Pure potential shaping variant with a per-pellet Pacman penalty."""

    strategy_id = "capture_v0_pure_potential_shaping_pellets"

    def compute(self, context: RewardContext) -> RewardResult:
        result = super().compute(context)
        pellets_eaten = int(context.pellets_eaten_this_step)
        if pellets_eaten <= 0:
            return result
        return RewardResult(
            result.terms
            + (
                RewardTerm(
                    "pacman_eats_pellet",
                    -0.5 * float(pellets_eaten),
                ),
            )
        )

class CaptureV0PurePotentialShapingPelletsFastCaptureBonus(
    CaptureV0PurePotentialShapingPellets
):
    """Pellet-penalty PBRS variant with a time-decayed capture bonus."""

    strategy_id = "capture_v0_pure_potential_shaping_pellets_fast_capture_bonus"

    def compute(self, context: RewardContext) -> RewardResult:
        result = super().compute(context)
        if not context.capture_happened:
            return result

        max_episode_steps = int(context.max_steps)
        steps_elapsed = int(context.step_count)
        if max_episode_steps <= 0:
            bonus_multiplier = 0.0
        else:
            progress = float(steps_elapsed) / float(max_episode_steps)
            progress = min(max(progress, 0.0), 1.0)
            bonus_multiplier = 1.0 - progress

        return RewardResult(
            result.terms
            + (
                RewardTerm(
                    "fast_get_pacman_bonus",
                    20.0 * bonus_multiplier,
                ),
            )
        )


class CaptureV0SparseControl(CaptureV0PurePotentialShaping):
    """Matched sparse control for the PBRS A/B (plan-000031).

    Byte-identical to ``CaptureV0PurePotentialShaping`` except the
    ``potential_shaping`` term is omitted: it emits only ``timestep`` plus the
    sparse terminals (``GET_PACMAN`` / ``PACMAN_TIMEOUT_WIN`` /
    ``PACMAN_WIN_PALLETS``). It deliberately **reuses
    ``CaptureV0PurePotentialShapingWeights`` unchanged** so the terminal
    magnitudes (+/-100) and the ``timestep`` cost (-0.05) cannot drift between
    the two arms -- the only difference between control and PBRS is the shaping
    term, which is the precondition for a causal sample-efficiency claim.
    """

    strategy_id = "capture_v0_sparse_control"

    def __init__(
        self,
        weights: CaptureV0PurePotentialShapingWeights | None = None,
    ) -> None:
        # Same weights dataclass as the PBRS arm (no new dataclass) -> weight-locked.
        self.weights = weights or CaptureV0PurePotentialShapingWeights()
        self._last_potential: float | None = None

    def reset(self, initial_context: RewardContext) -> None:
        _ = initial_context
        self._last_potential = None

    def compute(self, context: RewardContext) -> RewardResult:
        w = self.weights
        terms = [RewardTerm("timestep", w.timestep)]

        if context.capture_happened:
            terms.append(RewardTerm("GET_PACMAN", w.get_pacman, "terminal"))

        # No potential_shaping term -- this is the sparse control arm.

        if context.timeout_happened:
            terms.append(RewardTerm("PACMAN_TIMEOUT_WIN", w.pacman_timeout_win, "terminal"))
        if context.pacman_win_happened:
            terms.append(RewardTerm("PACMAN_WIN_PALLETS", w.pacman_win_pellets, "terminal"))

        return RewardResult(tuple(terms))


@dataclass(frozen=True, slots=True)
class CaptureMergePotentialShapingWeights:
    # Terminal/timestep/potential terms aligned with CaptureV0PurePotentialShaping.
    get_pacman: float = 100.0
    pacman_timeout_win: float = -100.0
    pacman_win_pellets: float = -100.0
    timestep: float = -0.05
    potential_shaping_alpha: float = 0.7
    # Visibility/exploration/motion terms aligned with CurrentRewardWeights.
    newly_spotted: float = 1.0
    currently_visible: float = 0.2
    enter_recently_unvisited_tile: float = 0.15
    reveal_unseen_local_cells: float = 0.03
    invalid_move: float = -0.08
    stay_still: float = -0.03
    repeated_direction_reversal: float = -0.04
    two_step_cycle: float = -0.06
    recently_unvisited_window: int = 10
    newly_spotted_min_unseen_steps: int = 6
    # Fast-capture and pellet terms aligned with pellet/fast bonus variants.
    pacman_eats_pellet: float = -0.5
    fast_get_pacman_bonus_scale: float = 20.0


@dataclass(frozen=True, slots=True)
class CaptureMerge2Weights(CaptureMergePotentialShapingWeights):
    # Stronger anti-loop pressure.
    repeated_direction_reversal: float = -0.10
    two_step_cycle: float = -0.18
    # Slightly stronger PBRS pull for pursuit.
    potential_shaping_alpha: float = 1.0
    # Penalize visible-but-stalled behavior after a short grace window.
    no_progress_visible: float = -0.05
    no_progress_visible_grace_steps: int = 2


class CaptureMergePotentialShaping(CurrentGitTeamReward):
    """Merged sparse-PBRS reward with selected current-team shaping terms.

    Includes: terminals, timestep, PBRS potential delta (mean distance),
    visibility/exploration terms, invalid/still/reversal/cycle penalties,
    pellet penalty, and fast-capture bonus.

    Excludes: valid_move and overlap_or_same_corridor.
    """

    strategy_id = "capture_merge_potential_shaping"

    def __init__(
        self,
        weights: CaptureMergePotentialShapingWeights | None = None,
    ) -> None:
        self.weights = weights or CaptureMergePotentialShapingWeights()
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

        # PBRS potential shaping, aligned with CaptureV0PurePotentialShaping.
        mean_distance = self._mean_distance(context)
        visibility_progress = False
        if mean_distance is not None:
            potential = -w.potential_shaping_alpha * float(mean_distance)
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

            self._recent_positions.setdefault(ghost.ghost_id, deque(maxlen=2)).append(
                ghost.current_position
            )

        pellets_eaten = int(context.pellets_eaten_this_step)
        if pellets_eaten > 0:
            terms.append(
                RewardTerm(
                    "pacman_eats_pellet",
                    w.pacman_eats_pellet * float(pellets_eaten),
                )
            )

        if context.capture_happened:
            max_episode_steps = int(context.max_steps)
            steps_elapsed = int(context.step_count)
            if max_episode_steps <= 0:
                bonus_multiplier = 0.0
            else:
                progress = float(steps_elapsed) / float(max_episode_steps)
                progress = min(max(progress, 0.0), 1.0)
                bonus_multiplier = 1.0 - progress
            terms.append(
                RewardTerm(
                    "fast_get_pacman_bonus",
                    w.fast_get_pacman_bonus_scale * bonus_multiplier,
                )
            )

        if context.timeout_happened:
            terms.append(RewardTerm("PACMAN_TIMEOUT_WIN", w.pacman_timeout_win, "terminal"))
        if context.pacman_win_happened:
            terms.append(RewardTerm("PACMAN_WIN_PALLETS", w.pacman_win_pellets, "terminal"))

        self._last_any_pacman_visible = context.pacman_visible
        return RewardResult(tuple(terms))

    def _mean_distance(self, context: RewardContext) -> float | None:
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
        if not reachable:
            return None
        return sum(reachable) / len(reachable)


class CaptureMerge(CaptureMergePotentialShaping):
    """Capture-merge reward without PBRS/reversal term emission.

    This keeps all capture_merge_potential_shaping logic/state transitions but
    removes ``potential_shaping`` and reversal-related terms from the final
    emitted reward terms.
    """

    strategy_id = "capture_merge"

    def compute(self, context: RewardContext) -> RewardResult:
        result = super().compute(context)
        disabled_terms = {"potential_shaping", "repeated_direction_reversal", "reverse_action"}
        filtered_terms = tuple(
            term for term in result.terms if term.name not in disabled_terms
        )
        if len(filtered_terms) == len(result.terms):
            return result
        return RewardResult(filtered_terms)


class CaptureMerge2(CaptureMergePotentialShaping):
    """Capture-merge variant tuned to reduce visible oscillation.

    Differences from ``capture_merge``:
    - Keeps ``potential_shaping`` enabled.
    - Keeps and strengthens ``repeated_direction_reversal``.
    - Strengthens ``two_step_cycle``.
    - Adds ``no_progress_visible`` after a grace window.
    """

    strategy_id = "capture_merge2"

    def __init__(self, weights: CaptureMerge2Weights | None = None) -> None:
        self.weights = weights or CaptureMerge2Weights()
        self._last_potential: float | None = None
        self._last_any_pacman_visible = False
        self._unseen_steps = self.weights.newly_spotted_min_unseen_steps
        self._last_move_direction: dict[str, Position | None] = {}
        self._reverse_streak: dict[str, int] = {}
        self._recent_positions: dict[str, deque[Position]] = {}
        self._seen_local_cells: dict[str, set[Position]] = {}
        self._last_tile_visit_step: dict[str, dict[Position, int]] = {}
        self._visible_no_progress_steps = 0

    def reset(self, initial_context: RewardContext) -> None:
        super().reset(initial_context)
        self._visible_no_progress_steps = 0

    def compute(self, context: RewardContext) -> RewardResult:
        result = super().compute(context)
        terms = result.terms

        if context.pacman_visible:
            had_progress = any(term.name == "currently_visible" for term in terms)
            if had_progress:
                self._visible_no_progress_steps = 0
            elif self._last_potential is not None:
                self._visible_no_progress_steps += 1
                if self._visible_no_progress_steps > self.weights.no_progress_visible_grace_steps:
                    terms = terms + (
                        RewardTerm("no_progress_visible", self.weights.no_progress_visible),
                    )
        else:
            self._visible_no_progress_steps = 0

        disabled_terms = {"reverse_action"}
        filtered_terms = tuple(
            term for term in terms if term.name not in disabled_terms
        )
        if len(filtered_terms) == len(terms):
            return RewardResult(terms)
        return RewardResult(filtered_terms)


@dataclass(frozen=True, slots=True)
class CaptureMerge3Weights:
    timestep: float = -0.005
    get_pacman: float = 100.0
    fast_get_pacman_bonus_scale: float = 20.0
    pacman_timeout_win: float = -100.0
    pacman_win_pellets: float = -100.0
    pacman_eats_pellet: float = -0.5
    invalid_move: float = -0.05


class CaptureMerge3(RewardStrategy):
    """Sparse capture reward with only explicit terminal/control terms.

    Enabled terms:
    - timestep
    - GET_PACMAN
    - fast_get_pacman_bonus
    - PACMAN_TIMEOUT_WIN
    - PACMAN_WIN_PELLETS
    - pacman_eats_pellet
    - invalid_move
    """

    strategy_id = "capture_merge3"

    def __init__(self, weights: CaptureMerge3Weights | None = None) -> None:
        self.weights = weights or CaptureMerge3Weights()

    def reset(self, initial_context: RewardContext) -> None:
        _ = initial_context

    def compute(self, context: RewardContext) -> RewardResult:
        w = self.weights
        terms = [RewardTerm("timestep", w.timestep)]

        if context.capture_happened:
            terms.append(RewardTerm("GET_PACMAN", w.get_pacman, "terminal"))
            max_episode_steps = int(context.max_steps)
            steps_elapsed = int(context.step_count)
            if max_episode_steps <= 0:
                bonus_multiplier = 0.0
            else:
                progress = float(steps_elapsed) / float(max_episode_steps)
                progress = min(max(progress, 0.0), 1.0)
                bonus_multiplier = 1.0 - progress
            terms.append(
                RewardTerm(
                    "fast_get_pacman_bonus",
                    w.fast_get_pacman_bonus_scale * bonus_multiplier,
                )
            )

        pellets_eaten = int(context.pellets_eaten_this_step)
        if pellets_eaten > 0:
            terms.append(
                RewardTerm(
                    "pacman_eats_pellet",
                    w.pacman_eats_pellet * float(pellets_eaten),
                )
            )

        invalid_moves = sum(1 for ghost in context.ghosts if ghost.invalid_move)
        if invalid_moves > 0:
            terms.append(RewardTerm("invalid_move", w.invalid_move * float(invalid_moves)))

        if context.timeout_happened:
            terms.append(RewardTerm("PACMAN_TIMEOUT_WIN", w.pacman_timeout_win, "terminal"))
        if context.pacman_win_happened:
            terms.append(RewardTerm("PACMAN_WIN_PELLETS", w.pacman_win_pellets, "terminal"))

        return RewardResult(tuple(terms))
