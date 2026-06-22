"""Contract tests for pluggable, environment-independent rewards."""

from dataclasses import FrozenInstanceError

import pytest

from custom_environment.env.rewards import (
    DEFAULT_REWARD_CLASS,
    GhostTransition,
    RewardContext,
    RewardResult,
    RewardTerm,
    load_reward_strategy,
)
from custom_environment.env.rewards.current import CurrentTeamReward
from my_rewards.movement_bonus import StrongerMovementReward


def _context() -> RewardContext:
    ghost = GhostTransition(
        ghost_id="ghost_1",
        previous_position=(1, 1),
        current_position=(1, 2),
        action=1,
        invalid_move=False,
        local_observation=((5, 5, 5), (2, 3, 4), (5, 2, 5)),
    )
    return RewardContext(
        step_count=1,
        max_steps=200,
        board_shape=(3, 5),
        wall_positions=frozenset({(0, 0)}),
        ghosts=(ghost,),
        pacman_previous_position=(1, 4),
        pacman_position=(1, 3),
        pacman_visible=True,
        visible_pacman_positions=((1, 3),),
        pellets_before=3,
        pellets_remaining=2,
        total_pellets=4,
        capture_happened=False,
        timeout_happened=False,
        pacman_win_happened=False,
    )


def test_context_is_immutable_and_tracks_pellet_delta():
    context = _context()
    assert context.pellets_eaten_this_step == 1
    with pytest.raises(FrozenInstanceError):
        context.step_count = 2
    with pytest.raises(AttributeError):
        context.wall_positions.add((2, 2))


def test_result_aggregates_terms_and_categories():
    result = RewardResult(
        (
            RewardTerm("movement", 0.5),
            RewardTerm("movement", 0.25),
            RewardTerm("capture", 10.0, "terminal"),
        )
    )
    assert result.total == 10.75
    assert result.breakdown == {"movement": 0.75, "capture": 10.0}
    assert result.category_totals == {"shaping": 0.75, "terminal": 10.0}


def test_default_loader_returns_current_strategy():
    strategy = load_reward_strategy(DEFAULT_REWARD_CLASS)
    assert isinstance(strategy, CurrentTeamReward)
    assert strategy.strategy_id == "current"


def test_instance_loader_gives_each_environment_independent_state():
    original = CurrentTeamReward()
    first = load_reward_strategy(original)
    second = load_reward_strategy(original)
    assert first is not original
    assert second is not original
    assert first is not second


@pytest.mark.parametrize("value", ["missing_colon", ":Missing", "module:"])
def test_loader_rejects_malformed_import_paths(value):
    with pytest.raises(ValueError):
        load_reward_strategy(value)


def test_current_strategy_reset_clears_episode_history():
    strategy = CurrentTeamReward()
    context = _context()
    strategy.reset(context)
    first = strategy.compute(context)
    strategy.compute(context)
    strategy.reset(context)
    repeated_first = strategy.compute(context)
    assert first.breakdown == repeated_first.breakdown


def test_stronger_movement_variant_changes_only_one_weight():
    baseline = CurrentTeamReward().weights
    variant = StrongerMovementReward().weights
    assert variant.valid_move == 0.10
    assert baseline.valid_move == 0.05
    for field_name in baseline.__dataclass_fields__:
        if field_name != "valid_move":
            assert getattr(variant, field_name) == getattr(baseline, field_name)


def test_reversal_penalty_applies_on_first_opposite_move():
    strategy = CurrentTeamReward()

    def make_context(step_count: int, previous: tuple[int, int], current: tuple[int, int]) -> RewardContext:
        ghost = GhostTransition(
            ghost_id="ghost_1",
            previous_position=previous,
            current_position=current,
            action=0,
            invalid_move=False,
            local_observation=((1, 1, 1), (1, 1, 1), (1, 1, 1)),
        )
        return RewardContext(
            step_count=step_count,
            max_steps=200,
            board_shape=(5, 5),
            wall_positions=frozenset(),
            ghosts=(ghost,),
            pacman_previous_position=(4, 4),
            pacman_position=(4, 4),
            pacman_visible=False,
            visible_pacman_positions=(),
            pellets_before=1,
            pellets_remaining=1,
            total_pellets=1,
            capture_happened=False,
            timeout_happened=False,
            pacman_win_happened=False,
        )

    strategy.reset(make_context(step_count=0, previous=(2, 2), current=(2, 2)))

    forward = strategy.compute(make_context(step_count=1, previous=(2, 2), current=(2, 3)))
    reverse = strategy.compute(make_context(step_count=2, previous=(2, 3), current=(2, 2)))

    assert "repeated_direction_reversal" not in forward.breakdown
    assert reverse.breakdown["repeated_direction_reversal"] == pytest.approx(-0.02)


def test_two_step_cycle_penalty_applies_on_a_b_a_pattern():
    strategy = CurrentTeamReward()

    def make_context(step_count: int, previous: tuple[int, int], current: tuple[int, int]) -> RewardContext:
        ghost = GhostTransition(
            ghost_id="ghost_1",
            previous_position=previous,
            current_position=current,
            action=0,
            invalid_move=False,
            local_observation=((1, 1, 1), (1, 1, 1), (1, 1, 1)),
        )
        return RewardContext(
            step_count=step_count,
            max_steps=200,
            board_shape=(5, 5),
            wall_positions=frozenset(),
            ghosts=(ghost,),
            pacman_previous_position=(4, 4),
            pacman_position=(4, 4),
            pacman_visible=False,
            visible_pacman_positions=(),
            pellets_before=1,
            pellets_remaining=1,
            total_pellets=1,
            capture_happened=False,
            timeout_happened=False,
            pacman_win_happened=False,
        )

    strategy.reset(make_context(step_count=0, previous=(2, 2), current=(2, 2)))
    strategy.compute(make_context(step_count=1, previous=(2, 2), current=(2, 3)))
    reverse = strategy.compute(make_context(step_count=2, previous=(2, 3), current=(2, 2)))

    assert reverse.breakdown["repeated_direction_reversal"] == pytest.approx(-0.02)
    assert reverse.breakdown["two_step_cycle"] == pytest.approx(-0.03)


def test_overlap_penalty_applies_to_adjacent_opposite_direction_pair():
    strategy = CurrentTeamReward()

    def make_context(step_count: int, ghosts: tuple[GhostTransition, GhostTransition]) -> RewardContext:
        return RewardContext(
            step_count=step_count,
            max_steps=200,
            board_shape=(6, 6),
            wall_positions=frozenset(),
            ghosts=ghosts,
            pacman_previous_position=(5, 5),
            pacman_position=(5, 5),
            pacman_visible=False,
            visible_pacman_positions=(),
            pellets_before=1,
            pellets_remaining=1,
            total_pellets=1,
            capture_happened=False,
            timeout_happened=False,
            pacman_win_happened=False,
        )

    reset_context = make_context(
        0,
        (
            GhostTransition("ghost_1", (2, 1), (2, 1), 0, False, ((1,),)),
            GhostTransition("ghost_2", (2, 4), (2, 4), 0, False, ((1,),)),
        ),
    )
    strategy.reset(reset_context)

    moved_context = make_context(
        1,
        (
            GhostTransition("ghost_1", (2, 1), (2, 2), 0, False, ((1,),)),
            GhostTransition("ghost_2", (2, 4), (2, 3), 1, False, ((1,),)),
        ),
    )
    result = strategy.compute(moved_context)

    assert result.breakdown["overlap_or_same_corridor"] == pytest.approx(-0.05)


def test_overlap_penalty_scales_with_multiple_offending_pairs():
    strategy = CurrentTeamReward()

    def make_context(step_count: int, ghosts: tuple[GhostTransition, ...]) -> RewardContext:
        return RewardContext(
            step_count=step_count,
            max_steps=200,
            board_shape=(6, 8),
            wall_positions=frozenset(),
            ghosts=ghosts,
            pacman_previous_position=(5, 7),
            pacman_position=(5, 7),
            pacman_visible=False,
            visible_pacman_positions=(),
            pellets_before=1,
            pellets_remaining=1,
            total_pellets=1,
            capture_happened=False,
            timeout_happened=False,
            pacman_win_happened=False,
        )

    strategy.reset(
        make_context(
            0,
            (
                GhostTransition("ghost_1", (2, 1), (2, 1), 0, False, ((1,),)),
                GhostTransition("ghost_2", (2, 2), (2, 2), 0, False, ((1,),)),
                GhostTransition("ghost_3", (2, 3), (2, 3), 0, False, ((1,),)),
            ),
        )
    )

    moved_context = make_context(
        1,
        (
            GhostTransition("ghost_1", (2, 1), (2, 2), 0, False, ((1,),)),
            GhostTransition("ghost_2", (2, 2), (2, 3), 0, False, ((1,),)),
            GhostTransition("ghost_3", (2, 3), (2, 4), 0, False, ((1,),)),
        ),
    )
    result = strategy.compute(moved_context)

    # Three pairs violate same-row/same-direction distance<=2:
    # (ghost_1, ghost_2), (ghost_2, ghost_3), (ghost_1, ghost_3).
    assert result.breakdown["overlap_or_same_corridor"] == pytest.approx(-0.15)
