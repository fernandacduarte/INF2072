"""Tests for the persistent closing reward (plan-000036 Steps 4-6)."""

import math

from custom_environment.env.rewards import load_reward_strategy
from custom_environment.env.rewards.base import GhostTransition, RewardContext
from custom_environment.env.rewards.current import CaptureV0ClosingReward
from custom_environment.env.rewards.loader import reward_class_from_id


# A wide-open 1xN corridor (no walls) so BFS distance equals |column difference|.
_BOARD = (1, 30)
_WALLS: frozenset[tuple[int, int]] = frozenset()


def _ghost(col: int) -> GhostTransition:
    return GhostTransition(
        ghost_id="ghost_1",
        previous_position=(0, col),
        current_position=(0, col),
        action=None,
        invalid_move=False,
        local_observation=(),
    )


def _context(ghost_col: int, pacman_col: int) -> RewardContext:
    return RewardContext(
        step_count=1,
        max_steps=200,
        board_shape=_BOARD,
        ghost_view_radius=5,
        wall_positions=_WALLS,
        ghosts=(_ghost(ghost_col),),
        pacman_previous_position=(0, pacman_col),
        pacman_position=(0, pacman_col),
        pacman_visible=False,  # isolate the closing term from containment
        visible_pacman_positions=(),
        pellets_before=0,
        pellets_remaining=0,
        total_pellets=0,
        capture_happened=False,
        timeout_happened=False,
        pacman_win_happened=False,
    )


def _closing_term(result) -> float:
    return result.breakdown.get("closing", 0.0)


def test_registered_id_resolves():
    assert (
        reward_class_from_id("capture_v0_closing")
        == "custom_environment.env.rewards.current:CaptureV0ClosingReward"
    )
    strategy = load_reward_strategy(
        "custom_environment.env.rewards.current:CaptureV0ClosingReward"
    )
    assert isinstance(strategy, CaptureV0ClosingReward)


def test_closing_in_pays_positive():
    r = CaptureV0ClosingReward()
    r.reset(_context(ghost_col=10, pacman_col=0))  # establishes prev distance = 10
    r.compute(_context(ghost_col=10, pacman_col=0))  # first compute sets baseline
    result = r.compute(_context(ghost_col=8, pacman_col=0))  # closed 2 cells
    assert math.isclose(_closing_term(result), 2.0 * r.weights.closing_weight)


def test_backing_off_pays_negative():
    r = CaptureV0ClosingReward()
    r.reset(_context(ghost_col=8, pacman_col=0))
    r.compute(_context(ghost_col=8, pacman_col=0))  # baseline distance 8
    result = r.compute(_context(ghost_col=10, pacman_col=0))  # backed off 2 cells
    assert math.isclose(_closing_term(result), -2.0 * r.weights.closing_weight)


def test_large_jump_is_clipped():
    r = CaptureV0ClosingReward()
    r.reset(_context(ghost_col=20, pacman_col=0))
    r.compute(_context(ghost_col=20, pacman_col=0))  # baseline distance 20
    result = r.compute(_context(ghost_col=1, pacman_col=0))  # closed 19 cells
    # Clipped to closing_clip (2.0), not 19.
    assert math.isclose(_closing_term(result), r.weights.closing_clip * r.weights.closing_weight)


def test_in_place_oscillation_nets_zero():
    r = CaptureV0ClosingReward()
    r.reset(_context(ghost_col=10, pacman_col=0))
    r.compute(_context(ghost_col=10, pacman_col=0))  # baseline 10
    closing_total = 0.0
    closing_total += _closing_term(r.compute(_context(ghost_col=9, pacman_col=0)))  # -> 9 (+1)
    closing_total += _closing_term(r.compute(_context(ghost_col=10, pacman_col=0)))  # -> 10 (-1)
    assert math.isclose(closing_total, 0.0, abs_tol=1e-9)
