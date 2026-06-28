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
from custom_environment.env.rewards.current import (
    CaptureV0ImproveLegalMovesIncreaseTerminalRewardsReverseAction,
    CaptureV0PurePotentialShaping,
    CaptureV0Reward,
    CurrentGitTeamReward,
    CurrentTeamReward,
    CurrentWithOverlapOrSameCorridor,
)
from custom_environment.env.rewards.loader import reward_class_from_id
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
        ghost_view_radius=1,
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


def test_loader_resolves_capture_v0_id():
    strategy = load_reward_strategy(reward_class_from_id("capture_v0"))
    assert isinstance(strategy, CaptureV0Reward)
    assert strategy.strategy_id == "capture_v0"


def test_loader_resolves_capture_v0_improved_id():
    strategy = load_reward_strategy(
        reward_class_from_id(
            "capture_v0_improve_legal_moves_increase_terminal_rewards_reverse_action"
        )
    )
    assert isinstance(strategy, CaptureV0ImproveLegalMovesIncreaseTerminalRewardsReverseAction)
    assert (
        strategy.strategy_id
        == "capture_v0_improve_legal_moves_increase_terminal_rewards_reverse_action"
    )


def test_capture_v0_rewards_reduced_visible_pacman_legal_moves():
    strategy = CaptureV0Reward()

    ghost = GhostTransition(
        ghost_id="ghost_1",
        previous_position=(2, 2),
        current_position=(2, 2),
        action=0,
        invalid_move=False,
        local_observation=((1, 1, 1), (1, 1, 1), (1, 1, 1)),
    )
    context = RewardContext(
        step_count=10,
        max_steps=200,
        board_shape=(4, 4),
        ghost_view_radius=1,
        wall_positions=frozenset({(0, 2), (1, 3)}),
        ghosts=(ghost,),
        pacman_previous_position=(1, 1),
        pacman_position=(1, 2),
        pacman_visible=True,
        visible_pacman_positions=((1, 2),),
        pellets_before=1,
        pellets_remaining=1,
        total_pellets=1,
        capture_happened=False,
        timeout_happened=False,
        pacman_win_happened=False,
    )

    strategy.reset(context)
    result = strategy.compute(context)
    assert result.breakdown["pacman_legal_moves_reduced"] == pytest.approx(1.0)


def test_capture_v0_improved_uses_smooth_legal_delta_and_reverse_action_penalty():
    strategy = CaptureV0ImproveLegalMovesIncreaseTerminalRewardsReverseAction()

    initial_ghost = GhostTransition(
        ghost_id="ghost_1",
        previous_position=(2, 2),
        current_position=(2, 2),
        action=0,
        invalid_move=False,
        local_observation=((1, 1, 1), (1, 1, 1), (1, 1, 1)),
    )
    initial_context = RewardContext(
        step_count=0,
        max_steps=200,
        board_shape=(4, 4),
        ghost_view_radius=1,
        wall_positions=frozenset({(0, 2), (1, 3)}),
        ghosts=(initial_ghost,),
        pacman_previous_position=(1, 1),
        pacman_position=(1, 1),
        pacman_visible=False,
        visible_pacman_positions=(),
        pellets_before=1,
        pellets_remaining=1,
        total_pellets=1,
        capture_happened=False,
        timeout_happened=False,
        pacman_win_happened=False,
    )
    strategy.reset(initial_context)

    ghost = GhostTransition(
        ghost_id="ghost_1",
        previous_position=(2, 2),
        current_position=(2, 1),
        action=1,
        invalid_move=False,
        local_observation=((1, 1, 1), (1, 1, 1), (1, 1, 1)),
    )
    context = RewardContext(
        step_count=1,
        max_steps=200,
        board_shape=(4, 4),
        ghost_view_radius=1,
        wall_positions=frozenset({(0, 2), (1, 3)}),
        ghosts=(ghost,),
        pacman_previous_position=(1, 1),
        pacman_position=(1, 2),
        pacman_visible=True,
        visible_pacman_positions=((1, 2),),
        pellets_before=1,
        pellets_remaining=1,
        total_pellets=1,
        capture_happened=False,
        timeout_happened=False,
        pacman_win_happened=False,
    )

    result = strategy.compute(context)
    # legal_delta = 3 - 2 = 1, reward = 0.2 * 1
    assert result.breakdown["pacman_legal_moves_delta"] == pytest.approx(0.2)
    # previous action 0 (RIGHT), current action 1 (LEFT) => reverse penalty
    assert result.breakdown["reverse_action"] == pytest.approx(-0.02)


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
    assert baseline.valid_move == 0.03
    for field_name in baseline.__dataclass_fields__:
        if field_name != "valid_move":
            assert getattr(variant, field_name) == getattr(baseline, field_name)


def test_team_potential_rewards_coordinated_progress_more_than_solo_progress():
    def make_context(
        step_count: int,
        prev_positions: tuple[tuple[int, int], tuple[int, int]],
        current_positions: tuple[tuple[int, int], tuple[int, int]],
    ) -> RewardContext:
        ghosts = (
            GhostTransition(
                ghost_id="ghost_1",
                previous_position=prev_positions[0],
                current_position=current_positions[0],
                action=0,
                invalid_move=False,
                local_observation=((1, 1, 1), (1, 1, 1), (1, 1, 1)),
            ),
            GhostTransition(
                ghost_id="ghost_2",
                previous_position=prev_positions[1],
                current_position=current_positions[1],
                action=0,
                invalid_move=False,
                local_observation=((1, 1, 1), (1, 1, 1), (1, 1, 1)),
            ),
        )
        return RewardContext(
            step_count=step_count,
            max_steps=200,
            board_shape=(5, 5),
            ghost_view_radius=1,
            wall_positions=frozenset(),
            ghosts=ghosts,
            pacman_previous_position=(2, 2),
            pacman_position=(2, 2),
            pacman_visible=False,
            visible_pacman_positions=(),
            pellets_before=1,
            pellets_remaining=1,
            total_pellets=1,
            capture_happened=False,
            timeout_happened=False,
            pacman_win_happened=False,
        )

    baseline_prev = ((0, 0), (4, 4))
    baseline_curr = ((0, 0), (4, 4))

    # Solo progress: ghost_1 moves one step closer; ghost_2 stays.
    solo_strategy = CurrentTeamReward()
    solo_strategy.reset(make_context(0, baseline_prev, baseline_curr))
    solo_strategy.compute(make_context(0, baseline_prev, baseline_curr))
    solo_result = solo_strategy.compute(
        make_context(
            1,
            prev_positions=baseline_curr,
            current_positions=((1, 0), (4, 4)),
        )
    )

    # Coordinated progress: both ghosts move one step closer.
    coord_strategy = CurrentTeamReward()
    coord_strategy.reset(make_context(0, baseline_prev, baseline_curr))
    coord_strategy.compute(make_context(0, baseline_prev, baseline_curr))
    coord_result = coord_strategy.compute(
        make_context(
            1,
            prev_positions=baseline_curr,
            current_positions=((1, 0), (3, 4)),
        )
    )

    solo_potential = solo_result.breakdown["potential_shaping"]
    coord_potential = coord_result.breakdown["potential_shaping"]

    assert solo_potential > 0.0
    assert coord_potential > solo_potential


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
            ghost_view_radius=1,
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
    assert reverse.breakdown["repeated_direction_reversal"] == pytest.approx(-0.05)


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
            ghost_view_radius=1,
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

    assert reverse.breakdown["repeated_direction_reversal"] == pytest.approx(-0.05)
    assert reverse.breakdown["two_step_cycle"] == pytest.approx(-0.08)


def test_overlap_penalty_is_disabled_for_ablation_adjacent_opposite_direction_pair():
    strategy = CurrentTeamReward()

    def make_context(step_count: int, ghosts: tuple[GhostTransition, GhostTransition]) -> RewardContext:
        return RewardContext(
            step_count=step_count,
            max_steps=200,
            board_shape=(6, 6),
            ghost_view_radius=1,
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

    assert "overlap_or_same_corridor" not in result.breakdown


def test_overlap_penalty_is_disabled_for_ablation_multiple_offending_pairs():
    strategy = CurrentTeamReward()

    def make_context(step_count: int, ghosts: tuple[GhostTransition, ...]) -> RewardContext:
        return RewardContext(
            step_count=step_count,
            max_steps=200,
            board_shape=(6, 8),
            ghost_view_radius=1,
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

    assert "overlap_or_same_corridor" not in result.breakdown


def test_overlap_penalty_enabled_variant_adjacent_opposite_direction_pair():
    strategy = CurrentWithOverlapOrSameCorridor()

    def make_context(step_count: int, ghosts: tuple[GhostTransition, GhostTransition]) -> RewardContext:
        return RewardContext(
            step_count=step_count,
            max_steps=200,
            board_shape=(6, 6),
            ghost_view_radius=1,
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

    strategy.reset(
        make_context(
            0,
            (
                GhostTransition("ghost_1", (2, 1), (2, 1), 0, False, ((1,),)),
                GhostTransition("ghost_2", (2, 4), (2, 4), 0, False, ((1,),)),
            ),
        )
    )
    result = strategy.compute(
        make_context(
            1,
            (
                GhostTransition("ghost_1", (2, 1), (2, 2), 0, False, ((1,),)),
                GhostTransition("ghost_2", (2, 4), (2, 3), 1, False, ((1,),)),
            ),
        )
    )

    assert result.breakdown["overlap_or_same_corridor"] == pytest.approx(-0.05)


def test_overlap_penalty_enabled_variant_overlapping_positions():
    strategy = CurrentWithOverlapOrSameCorridor()

    def make_context(step_count: int, ghosts: tuple[GhostTransition, GhostTransition]) -> RewardContext:
        return RewardContext(
            step_count=step_count,
            max_steps=200,
            board_shape=(6, 6),
            ghost_view_radius=1,
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

    strategy.reset(
        make_context(
            0,
            (
                GhostTransition("ghost_1", (2, 1), (2, 1), 0, False, ((1,),)),
                GhostTransition("ghost_2", (2, 2), (2, 2), 0, False, ((1,),)),
            ),
        )
    )
    result = strategy.compute(
        make_context(
            1,
            (
                GhostTransition("ghost_1", (2, 1), (2, 2), 0, False, ((1,),)),
                GhostTransition("ghost_2", (2, 2), (2, 2), 0, True, ((1,),)),
            ),
        )
    )

    assert result.breakdown["overlap_or_same_corridor"] == pytest.approx(-0.05)


def test_current_git_variant_applies_overlap_penalty_for_adjacent_opposite_direction_pair():
    strategy = CurrentGitTeamReward()

    def make_context(step_count: int, ghosts: tuple[GhostTransition, GhostTransition]) -> RewardContext:
        return RewardContext(
            step_count=step_count,
            max_steps=200,
            board_shape=(6, 6),
            ghost_view_radius=1,
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

    strategy.reset(
        make_context(
            0,
            (
                GhostTransition("ghost_1", (2, 1), (2, 1), 0, False, ((1,),)),
                GhostTransition("ghost_2", (2, 4), (2, 4), 0, False, ((1,),)),
            ),
        )
    )
    result = strategy.compute(
        make_context(
            1,
            (
                GhostTransition("ghost_1", (2, 1), (2, 2), 0, False, ((1,),)),
                GhostTransition("ghost_2", (2, 4), (2, 3), 1, False, ((1,),)),
            ),
        )
    )

    assert result.breakdown["overlap_or_same_corridor"] == pytest.approx(-0.05)


# --- Pure potential-based reward shaping (capture_v0_pure_potential_shaping) ---

ALPHA = 0.7
GAMMA = 0.99


def _pbrs_context(
    ghost_col: int,
    pacman_col: int,
    *,
    step_count: int = 1,
    capture_happened: bool = False,
    timeout_happened: bool = False,
    pacman_win_happened: bool = False,
    ghost_action: int = 0,
) -> RewardContext:
    """One ghost on a 1xN corridor (no walls), so BFS distance == |ghost_col - pacman_col|."""
    ghost = GhostTransition(
        ghost_id="ghost_1",
        previous_position=(0, ghost_col),
        current_position=(0, ghost_col),
        action=ghost_action,
        invalid_move=False,
        local_observation=((1, 1, 1),),
    )
    return RewardContext(
        step_count=step_count,
        max_steps=200,
        board_shape=(1, 12),
        ghost_view_radius=1,
        wall_positions=frozenset(),
        ghosts=(ghost,),
        pacman_previous_position=(0, pacman_col),
        pacman_position=(0, pacman_col),
        pacman_visible=False,
        visible_pacman_positions=(),
        pellets_before=1,
        pellets_remaining=1,
        total_pellets=1,
        capture_happened=capture_happened,
        timeout_happened=timeout_happened,
        pacman_win_happened=pacman_win_happened,
    )


def test_loader_resolves_pure_pbrs_id():
    strategy = load_reward_strategy(
        reward_class_from_id("capture_v0_pure_potential_shaping")
    )
    assert isinstance(strategy, CaptureV0PurePotentialShaping)
    assert strategy.strategy_id == "capture_v0_pure_potential_shaping"
    assert strategy.weights.gamma == pytest.approx(0.99)
    assert strategy.weights.potential_shaping_alpha == pytest.approx(0.7)


def test_pure_pbrs_telescoping_term():
    strategy = CaptureV0PurePotentialShaping()
    strategy.reset(_pbrs_context(0, 5))

    # First compute after reset has no prior potential -> no shaping term yet.
    first = strategy.compute(_pbrs_context(0, 5, step_count=1))  # distance 5
    assert "potential_shaping" not in first.breakdown

    # Move one tile closer (distance 4): F = gamma*Phi(s') - Phi(s).
    second = strategy.compute(_pbrs_context(1, 5, step_count=2))  # distance 4
    expected = GAMMA * (-ALPHA * 4.0) - (-ALPHA * 5.0)
    assert second.breakdown["potential_shaping"] == pytest.approx(expected)
    assert expected > 0.0  # closing distance is rewarded


def test_pure_pbrs_capture_pulse():
    strategy = CaptureV0PurePotentialShaping()
    strategy.reset(_pbrs_context(4, 5))

    strategy.compute(_pbrs_context(4, 5, step_count=1))  # distance 1 -> sets last potential
    capture = strategy.compute(
        _pbrs_context(5, 5, step_count=2, capture_happened=True)  # ghost reaches Pacman
    )

    assert capture.breakdown["GET_PACMAN"] == pytest.approx(100.0)
    # Phi(capture) = 0; pulse = gamma*0 - (-alpha*dist_before) = +alpha*1.
    assert capture.breakdown["potential_shaping"] == pytest.approx(ALPHA * 1.0)


def test_pure_pbrs_timeout_does_not_zero_potential():
    strategy = CaptureV0PurePotentialShaping()
    strategy.reset(_pbrs_context(0, 5))

    strategy.compute(_pbrs_context(0, 5, step_count=1))  # distance 5
    timeout = strategy.compute(
        _pbrs_context(1, 5, step_count=2, timeout_happened=True)  # distance 4, Pacman alive
    )

    assert timeout.breakdown["PACMAN_TIMEOUT_WIN"] == pytest.approx(-100.0)
    # Real telescoping using the actual distance, NOT a forced +alpha*dist_before pulse.
    expected = GAMMA * (-ALPHA * 4.0) - (-ALPHA * 5.0)
    assert timeout.breakdown["potential_shaping"] == pytest.approx(expected)
    assert timeout.breakdown["potential_shaping"] != pytest.approx(ALPHA * 5.0)


def test_pure_pbrs_magnitude_between_timestep_and_terminal():
    strategy = CaptureV0PurePotentialShaping()
    strategy.reset(_pbrs_context(0, 5))
    strategy.compute(_pbrs_context(0, 5, step_count=1))
    result = strategy.compute(_pbrs_context(1, 5, step_count=2))

    magnitude = abs(result.breakdown["potential_shaping"])
    assert magnitude > abs(strategy.weights.timestep)  # > 0.01
    assert magnitude < abs(strategy.weights.get_pacman)  # < 100


def test_pure_pbrs_emits_no_reverse_action_term():
    strategy = CaptureV0PurePotentialShaping()
    strategy.reset(_pbrs_context(0, 5))
    # Multi-step rollout including a direction reversal (action 0 then 1).
    rollout = [
        _pbrs_context(0, 5, step_count=1, ghost_action=0),
        _pbrs_context(1, 5, step_count=2, ghost_action=0),
        _pbrs_context(0, 5, step_count=3, ghost_action=1),  # reverse
    ]
    for context in rollout:
        breakdown = strategy.compute(context).breakdown
        assert "reverse_action" not in breakdown
