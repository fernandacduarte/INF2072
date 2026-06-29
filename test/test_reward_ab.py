"""Tests for the decisive reward A/B (plan-000031).

Covers the matched sparse control reward, the seed-pinned Pacman RNG, the
pursuit_fraction eval metric, and the A/B runner / plotter tooling. The reward
and metric tests reuse the 1xN-corridor fixture pattern from
``test_reward_strategies.py`` (BFS distance == |ghost_col - pacman_col|).
"""

from pathlib import Path
import subprocess
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from custom_environment.env.domain.constant import Action
from custom_environment.env.pacman_environment import PacManEnvironment
from custom_environment.env.rewards import (
    GhostTransition,
    RewardContext,
    CaptureV0PurePotentialShaping,
    CaptureV0SparseControl,
    load_reward_strategy,
)
from custom_environment.env.rewards.loader import reward_class_from_id
from custom_environment.utils import parse_layout


# --------------------------------------------------------------------------- #
# Shared fixtures
# --------------------------------------------------------------------------- #

def _ctx(
    ghost_col: int,
    pacman_col: int,
    *,
    step_count: int = 1,
    capture_happened: bool = False,
    timeout_happened: bool = False,
    pacman_win_happened: bool = False,
) -> RewardContext:
    """One ghost on a 1xN corridor (no walls): BFS distance == |ghost - pacman|."""
    ghost = GhostTransition(
        ghost_id="ghost_1",
        previous_position=(0, ghost_col),
        current_position=(0, ghost_col),
        action=0,
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


# --------------------------------------------------------------------------- #
# Step 2 -- matched sparse control reward (weight-lock + term set)
# --------------------------------------------------------------------------- #

def test_control_is_weight_locked_to_pbrs_arm():
    """The two arms must share identical terminal + timestep weights so the only
    difference is the shaping term (confound control)."""
    control = CaptureV0SparseControl().weights
    pbrs = CaptureV0PurePotentialShaping().weights
    assert control.get_pacman == pbrs.get_pacman == pytest.approx(100.0)
    assert control.pacman_timeout_win == pbrs.pacman_timeout_win == pytest.approx(-100.0)
    assert control.pacman_win_pellets == pbrs.pacman_win_pellets == pytest.approx(-100.0)
    assert control.timestep == pbrs.timestep == pytest.approx(-0.05)


def test_control_emits_no_potential_shaping_term():
    """On a mid-episode step the control emits only timestep; PBRS adds shaping."""
    control = CaptureV0SparseControl()
    control.reset(_ctx(0, 5))
    pbrs = CaptureV0PurePotentialShaping()
    pbrs.reset(_ctx(0, 5))

    # Two steps so PBRS has a prior potential and emits a telescoping term.
    control.compute(_ctx(0, 5, step_count=1))
    pbrs.compute(_ctx(0, 5, step_count=1))
    control_breakdown = control.compute(_ctx(1, 5, step_count=2)).breakdown
    pbrs_breakdown = pbrs.compute(_ctx(1, 5, step_count=2)).breakdown

    assert "potential_shaping" not in control_breakdown
    assert set(control_breakdown) == {"timestep"}
    assert "potential_shaping" in pbrs_breakdown


def test_control_emits_capture_and_terminal_terms():
    control = CaptureV0SparseControl()
    control.reset(_ctx(4, 5))
    capture = control.compute(_ctx(5, 5, step_count=1, capture_happened=True))
    assert capture.breakdown["GET_PACMAN"] == pytest.approx(100.0)

    control.reset(_ctx(0, 5))
    timeout = control.compute(_ctx(0, 5, step_count=1, timeout_happened=True))
    assert timeout.breakdown["PACMAN_TIMEOUT_WIN"] == pytest.approx(-100.0)
    assert "potential_shaping" not in timeout.breakdown


# --------------------------------------------------------------------------- #
# Step 3 -- registration / loader resolution
# --------------------------------------------------------------------------- #

def test_loader_resolves_sparse_control_id():
    strategy = load_reward_strategy(reward_class_from_id("capture_v0_sparse_control"))
    assert isinstance(strategy, CaptureV0SparseControl)
    assert strategy.strategy_id == "capture_v0_sparse_control"


# --------------------------------------------------------------------------- #
# Step 1 -- seed-pinned Pacman RNG reproducibility
# --------------------------------------------------------------------------- #

# 11-wide corridor: Pacman left, ghost pinned at the right wall. Ghosts are
# scripted MOVE_RIGHT (invalid at the wall -> they hold position), so no capture
# can occur within the short rollout and only Pacman's stochastic motion varies.
_REPRO_LAYOUT = [
    "%%%%%%%%%%%",
    "%P.......G%",
    "%%%%%%%%%%%",
]


def _pacman_positions_for_seed(seed: int, steps: int = 5) -> list[tuple[int, int]]:
    env = PacManEnvironment(
        global_view=parse_layout(_REPRO_LAYOUT),
        pacman_difficulty="hard",
        pacman_random_action_prob=0.5,
        pacman_curriculum="off",
        randomize_spawns=False,
    )
    env.reset(seed=seed)
    positions = []
    for _ in range(steps):
        actions = {ghost.id: Action.MOVE_RIGHT for ghost in env.ghosts}
        env.step(actions)
        positions.append(tuple(env.pacman.current_position))
    return positions


def test_seed_pinned_pacman_rng_is_reproducible():
    """Two envs reset with the same seed and p=0.5 produce identical Pacman
    trajectories under an identical ghost-action script (T4)."""
    first = _pacman_positions_for_seed(7)
    second = _pacman_positions_for_seed(7)
    assert first == second


def test_seed_pinned_pacman_rng_differs_across_seeds():
    """Different seeds should generally yield different stochastic trajectories
    (guards against the reseed being a no-op that ignores the seed)."""
    a = _pacman_positions_for_seed(7)
    b = _pacman_positions_for_seed(123)
    assert a != b


# --------------------------------------------------------------------------- #
# Step 4 -- pursuit_fraction eval metric
# --------------------------------------------------------------------------- #

from custom_environment.eval_report import (  # noqa: E402
    REPORT_FIELDS,
    VARIANT_FIELDS,
    _aggregate_episodes,
    _build_variant_summary,
    _pursuit_fraction_from_distances,
)


def test_pursuit_fraction_monotonic_approach_is_one():
    assert _pursuit_fraction_from_distances([5.0, 4.0, 3.0, 2.0, 1.0]) == 1.0


def test_pursuit_fraction_monotonic_retreat_is_zero():
    assert _pursuit_fraction_from_distances([1.0, 2.0, 3.0, 4.0, 5.0]) == 0.0


def test_pursuit_fraction_skips_undefined_steps():
    # None steps are skipped, not compared across the gap: 4->3 closing, 3->2 closing.
    assert _pursuit_fraction_from_distances([4.0, None, 3.0, 2.0]) == 1.0
    # No comparable pair -> NaN.
    result = _pursuit_fraction_from_distances([None, 5.0])
    assert result != result  # NaN


def _episode(pursuit_fraction: float, *, captured: bool = False, steps: int = 10):
    return {
        "captured": captured,
        "timeout": not captured,
        "pellet_win": False,
        "evaluation_cutoff": False,
        "steps": steps,
        "team_return": 1.0,
        "reward_breakdown": {},
        "category_totals": {"shaping": 0.0, "terminal": 0.0},
        "visible_steps": 5,
        "newly_spotted_count": 0,
        "pursuit_fraction": pursuit_fraction,
    }


def test_aggregate_emits_pursuit_columns_in_report_fields():
    agg = _aggregate_episodes([_episode(1.0), _episode(0.0)])
    assert agg["pursuit_fraction_mean"] == pytest.approx(0.5)
    assert "pursuit_fraction_mean" in REPORT_FIELDS
    assert "pursuit_fraction_std" in REPORT_FIELDS


def test_variant_summary_emits_pursuit_columns():
    # Two per-seed rows for one variant; each row carries its pursuit_fraction_mean.
    rows = [
        {"reward_id": "capture_v0_sparse_control", "learner": "iql", "reward_class": "x",
         "capture_rate": 0.4, "mean_steps_to_capture": 50.0, "pursuit_fraction_mean": 0.6},
        {"reward_id": "capture_v0_sparse_control", "learner": "iql", "reward_class": "x",
         "capture_rate": 0.5, "mean_steps_to_capture": 60.0, "pursuit_fraction_mean": 0.8},
    ]
    pooled = {
        ("capture_v0_sparse_control", "iql"): [_episode(0.6, captured=True), _episode(0.8)],
    }
    summary = _build_variant_summary(rows, pooled)
    assert len(summary) == 1
    assert summary[0]["pursuit_fraction_mean"] == pytest.approx(0.7)
    assert "pursuit_fraction_mean" in VARIANT_FIELDS
    assert "pursuit_fraction_std" in VARIANT_FIELDS
