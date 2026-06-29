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


# --------------------------------------------------------------------------- #
# Step 5 -- A/B sweep runner
# --------------------------------------------------------------------------- #

from benchmarl_setup import run_reward_ab  # noqa: E402


def test_ab_build_command_carries_both_arms_and_constant_knobs(tmp_path):
    args = run_reward_ab.parse_args(["--save-root", str(tmp_path)])
    joined = " ".join(run_reward_ab.build_command(0.25, args))
    assert "capture_v0_sparse_control,capture_v0_pure_potential_shaping" in joined
    assert "--pacman-curriculum off" in joined
    assert "--pacman-difficulty hard" in joined
    assert "--pacman-random-action-prob 0.25" in joined
    assert "--randomize-spawns" in joined
    assert "--checkpoint-at-end" in joined
    assert "p_0.25" in joined


def test_ab_dry_run_lists_three_points(tmp_path, capsys):
    rc = run_reward_ab.main(["--dry-run", "--save-root", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 0
    for folder in ("p_0.25", "p_0.5", "p_0.75"):
        assert folder in out
    # Each of the three points trains both arms in one command.
    assert out.count("capture_v0_sparse_control,capture_v0_pure_potential_shaping") >= 3
    # Dry-run launches no training and writes no manifest.
    assert not (tmp_path / "ab_manifest.csv").exists()


def test_ab_rejects_point_out_of_range():
    with pytest.raises(ValueError):
        run_reward_ab._parse_points("1.5")
    with pytest.raises(ValueError):
        run_reward_ab._parse_points("")


# --------------------------------------------------------------------------- #
# Step 6 -- aggregator + comparison plotter
# --------------------------------------------------------------------------- #

import csv as _csv  # noqa: E402

from benchmarl_setup import plot_reward_ab  # noqa: E402

_CONTROL = "capture_v0_sparse_control"
_PBRS = "capture_v0_pure_potential_shaping"
_VARIANT_HEADER = [
    "reward_id", "learner", "capture_rate_mean", "capture_rate_std",
    "time_to_capture_mean", "pursuit_fraction_mean", "pursuit_fraction_std",
]


def _write_point(point_dir: Path, *, control_capture_curve, pbrs_capture_curve):
    """Create a point's by-variant CSV + live_progress.csvl under a maze subdir."""
    maze_dir = point_dir / "pinklike3"
    maze_dir.mkdir(parents=True, exist_ok=True)
    with (maze_dir / "reward_eval_host_by_variant.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = _csv.DictWriter(fh, fieldnames=_VARIANT_HEADER)
        writer.writeheader()
        writer.writerow({"reward_id": _CONTROL, "learner": "iql", "capture_rate_mean": 0.10,
                         "capture_rate_std": 0.03, "time_to_capture_mean": 80.0,
                         "pursuit_fraction_mean": 0.30, "pursuit_fraction_std": 0.05})
        writer.writerow({"reward_id": _PBRS, "learner": "iql", "capture_rate_mean": 0.12,
                         "capture_rate_std": 0.04, "time_to_capture_mean": 70.0,
                         "pursuit_fraction_mean": 0.60, "pursuit_fraction_std": 0.06})
    lines = ["#meta,note=fixture"]
    for reward_id, curve in ((_CONTROL, control_capture_curve), (_PBRS, pbrs_capture_curve)):
        for step, (frame, capture) in enumerate(curve, start=1):
            lines.append(f"iql@{reward_id}@cpu,0,{step},{frame},{capture},0.0")
    (maze_dir / "live_progress_host.csvl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _make_ab_fixture(tmp_path: Path) -> Path:
    manifest = tmp_path / "ab_manifest.csv"
    rows = []
    for p in (0.25, 0.5):
        point_dir = tmp_path / f"p_{p}"
        # Control capture stays low (never reaches threshold 0.3 -> NaN ftt);
        # PBRS climbs past 0.3 (defined ftt).
        _write_point(
            point_dir,
            control_capture_curve=[(10000, 0.05), (30000, 0.08), (60000, 0.10)],
            pbrs_capture_curve=[(10000, 0.10), (30000, 0.35), (60000, 0.55)],
        )
        # Store save_folder relative to the manifest's directory, exactly as
        # run_reward_ab.py writes it (regression for the doubled-path bug where the
        # plotter resolved a CWD-relative folder against the manifest dir).
        rows.append({"p": p, "evasiveness": 1 - p, "save_folder": f"p_{p}"})
    with manifest.open("w", newline="", encoding="utf-8") as fh:
        writer = _csv.DictWriter(fh, fieldnames=["p", "evasiveness", "save_folder"])
        writer.writeheader()
        writer.writerows(rows)
    return manifest


def test_plot_reward_ab_builds_table_and_figures(tmp_path):
    manifest = _make_ab_fixture(tmp_path)
    out_prefix = tmp_path / "reward_ab"
    rc = plot_reward_ab.main(["--manifest", str(manifest), "--out-prefix", str(out_prefix)])
    assert rc == 0

    table_csv = tmp_path / "reward_ab.csv"
    assert table_csv.exists()
    with table_csv.open(newline="", encoding="utf-8") as fh:
        rows = list(_csv.DictReader(fh))
    assert rows  # non-empty
    for column in ("capture_rate_mean", "pursuit_fraction_mean", "aulc", "frames_to_threshold"):
        assert column in rows[0]

    # At least the capture_rate and pursuit panels exist (>=2 PNGs).
    pngs = list(tmp_path.glob("reward_ab_*.png"))
    assert len(pngs) >= 2


def test_plot_reward_ab_never_reaching_threshold_is_nan(tmp_path):
    manifest = _make_ab_fixture(tmp_path)
    out_prefix = tmp_path / "reward_ab"
    plot_reward_ab.main(["--manifest", str(manifest), "--out-prefix", str(out_prefix)])
    with (tmp_path / "reward_ab.csv").open(newline="", encoding="utf-8") as fh:
        rows = list(_csv.DictReader(fh))
    control_rows = [r for r in rows if r["reward_id"] == _CONTROL]
    assert control_rows
    for row in control_rows:
        value = float(row["frames_to_threshold"])
        assert value != value  # NaN, not inf or a number
    # PBRS reaches the threshold -> defined frames_to_threshold.
    pbrs_rows = [r for r in rows if r["reward_id"] == _PBRS]
    assert any(float(r["frames_to_threshold"]) == float(r["frames_to_threshold"]) for r in pbrs_rows)
