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
