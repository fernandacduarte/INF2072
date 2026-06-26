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
    CurrentGitTeamReward,
    CurrentRewardWeightsV2,
    CurrentRewardWeightsV3,
    CurrentTeamReward,
    CurrentWithOverlapOrSameCorridor,
    PursuitFirstTeamReward,
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


# --- current_v3 pursuit-first variant (plan-000028 / research-000027) ---


def _v3_context(
    *,
    step_count: int,
    ghost_prev: tuple[int, int],
    ghost_curr: tuple[int, int],
    pacman_position: tuple[int, int],
    pacman_visible: bool,
    invalid_move: bool = False,
    capture_happened: bool = False,
) -> RewardContext:
    """Single-ghost context on a 5x5 open board for v3 calibration/guardrail tests."""
    ghost = GhostTransition(
        ghost_id="ghost_1",
        previous_position=ghost_prev,
        current_position=ghost_curr,
        action=0,
        invalid_move=invalid_move,
        local_observation=((1, 1, 1), (1, 1, 1), (1, 1, 1)),
    )
    return RewardContext(
        step_count=step_count,
        max_steps=200,
        board_shape=(5, 5),
        ghost_view_radius=1,
        wall_positions=frozenset(),
        ghosts=(ghost,),
        pacman_previous_position=pacman_position,
        pacman_position=pacman_position,
        pacman_visible=pacman_visible,
        visible_pacman_positions=((pacman_position,) if pacman_visible else ()),
        pellets_before=1,
        pellets_remaining=1,
        total_pellets=1,
        capture_happened=capture_happened,
        timeout_happened=False,
        pacman_win_happened=False,
    )


def test_current_v3_registers_and_loads_with_v3_weights():
    path = reward_class_from_id("current_v3")
    assert path == "custom_environment.env.rewards.current:PursuitFirstTeamReward"
    strategy = load_reward_strategy(path)
    assert isinstance(strategy, PursuitFirstTeamReward)
    assert strategy.strategy_id == "current_v3"
    assert isinstance(strategy.weights, CurrentRewardWeightsV3)


def test_current_v3_terminal_weights_match_v2():
    v2 = CurrentRewardWeightsV2()
    v3 = CurrentRewardWeightsV3()
    assert v3.get_pacman == v2.get_pacman == 40.0
    assert v3.pacman_timeout_win == v2.pacman_timeout_win == -35.0
    assert v3.pacman_win_pellets == v2.pacman_win_pellets == -35.0


def _v3_step_reward(ghost_dest: tuple[int, int]) -> float:
    """Prime the potential baseline with the ghost at the pivot, then score a
    single transition (pivot -> dest, or stay when dest == pivot). Pacman is kept
    not-visible so visibility terms are identical across scenarios and cancel out,
    isolating the movement + potential-shaping contribution."""
    pacman = (0, 0)
    pivot = (2, 0)  # BFS distance 2 from Pacman on the open board
    strategy = PursuitFirstTeamReward()
    baseline = _v3_context(
        step_count=0, ghost_prev=pivot, ghost_curr=pivot,
        pacman_position=pacman, pacman_visible=False,
    )
    strategy.reset(baseline)
    strategy.compute(baseline)  # primes _last_potential
    transition = _v3_context(
        step_count=1, ghost_prev=pivot, ghost_curr=ghost_dest,
        pacman_position=pacman, pacman_visible=False,
    )
    return strategy.compute(transition).total


def test_current_v3_move_toward_beats_stay_and_move_away():
    reward_toward = _v3_step_reward((1, 0))  # one cell closer (dist 1)
    reward_stay = _v3_step_reward((2, 0))    # unchanged (dist 2)
    reward_away = _v3_step_reward((3, 0))    # one cell farther (dist 3)
    assert reward_toward > reward_stay, (reward_toward, reward_stay)
    assert reward_toward > reward_away, (reward_toward, reward_away)


def test_current_v3_visible_stalk_shaping_stays_below_capture_reward():
    """A 200-step Pacman-visible-every-step episode (the worst case for the
    unconditional currently_visible bonus) must accrue less non-terminal shaping
    than a single capture (get_pacman), so stalking never rivals capturing."""
    strategy = PursuitFirstTeamReward()
    pacman = (2, 2)
    cells = [(2, 0), (2, 1)]  # oscillate near Pacman, min distance 1 (never captures)
    reset_ctx = _v3_context(
        step_count=0, ghost_prev=cells[0], ghost_curr=cells[0],
        pacman_position=pacman, pacman_visible=True,
    )
    strategy.reset(reset_ctx)
    strategy.compute(reset_ctx)

    total_shaping = 0.0
    prev = cells[0]
    for step in range(1, 201):
        curr = cells[step % 2]
        result = strategy.compute(
            _v3_context(
                step_count=step, ghost_prev=prev, ghost_curr=curr,
                pacman_position=pacman, pacman_visible=True,
            )
        )
        total_shaping += result.category_totals["shaping"]
        prev = curr

    assert total_shaping < CurrentRewardWeightsV3().get_pacman, total_shaping


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
