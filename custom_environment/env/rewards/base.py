"""Stable, environment-independent interfaces for reward implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal


Position = tuple[int, int]
RewardCategory = Literal["shaping", "terminal"]


@dataclass(frozen=True, slots=True)
class GhostTransition:
    """Read-only facts about one ghost's latest transition."""

    ghost_id: str
    previous_position: Position
    current_position: Position
    action: int | None
    invalid_move: bool
    local_observation: tuple[tuple[int, ...], ...]


@dataclass(frozen=True, slots=True)
class RewardContext:
    """Immutable game snapshot supplied to a reward strategy.

    It deliberately contains values rather than references to the live environment,
    agents, or NumPy arrays. Reward experiments therefore cannot mutate game state.
    """

    step_count: int
    max_steps: int
    board_shape: tuple[int, int]
    wall_positions: frozenset[Position]
    ghosts: tuple[GhostTransition, ...]
    pacman_previous_position: Position
    pacman_position: Position
    pacman_visible: bool
    visible_pacman_positions: tuple[Position, ...]
    pellets_before: int
    pellets_remaining: int
    total_pellets: int
    capture_happened: bool
    timeout_happened: bool
    pacman_win_happened: bool

    @property
    def pellets_eaten_this_step(self) -> int:
        return max(0, self.pellets_before - self.pellets_remaining)


@dataclass(frozen=True, slots=True)
class RewardTerm:
    name: str
    value: float
    category: RewardCategory = "shaping"


@dataclass(frozen=True, slots=True)
class RewardResult:
    """Reward output with an auditable decomposition."""

    terms: tuple[RewardTerm, ...]

    @property
    def total(self) -> float:
        return float(sum(term.value for term in self.terms))

    @property
    def breakdown(self) -> dict[str, float]:
        values: dict[str, float] = {}
        for term in self.terms:
            values[term.name] = values.get(term.name, 0.0) + float(term.value)
        return values

    @property
    def category_totals(self) -> dict[str, float]:
        values = {"shaping": 0.0, "terminal": 0.0}
        for term in self.terms:
            values[term.category] += float(term.value)
        return values


class RewardStrategy(ABC):
    """Base class for an episode-scoped shared-team reward."""

    strategy_id: str

    @abstractmethod
    def reset(self, initial_context: RewardContext) -> None:
        """Clear episode-local state."""

    @abstractmethod
    def compute(self, context: RewardContext) -> RewardResult:
        """Compute the reward for exactly one completed environment step."""
