import csv
import math
import sys

import pytest

from custom_environment import eval_report


def _episode(
    *,
    captured=False,
    timeout=False,
    pellet_win=False,
    evaluation_cutoff=False,
    steps=10,
    team_return=0.0,
    visible_steps=0,
    newly_spotted_count=0,
    shaping=0.0,
    terminal=0.0,
):
    return {
        "captured": captured,
        "timeout": timeout,
        "pellet_win": pellet_win,
        "evaluation_cutoff": evaluation_cutoff,
        "steps": steps,
        "team_return": team_return,
        "reward_breakdown": {},
        "category_totals": {"shaping": shaping, "terminal": terminal},
        "visible_steps": visible_steps,
        "newly_spotted_count": newly_spotted_count,
    }


def test_aggregate_episodes_reports_objective_and_reward_diagnostics():
    episodes = [
        _episode(
            captured=True,
            steps=10,
            team_return=10.0,
            visible_steps=5,
            newly_spotted_count=1,
            shaping=1.0,
            terminal=9.0,
        ),
        _episode(
            timeout=True,
            steps=20,
            team_return=-2.0,
            visible_steps=10,
            newly_spotted_count=2,
            shaping=-1.0,
            terminal=-1.0,
        ),
        _episode(evaluation_cutoff=True, steps=5),
    ]

    result = eval_report._aggregate_episodes(episodes)

    assert result["episodes"] == 3
    assert result["capture_rate"] == pytest.approx(1 / 3)
    assert result["ghost_win_rate"] == result["capture_rate"]
    assert result["pacman_win_rate"] == pytest.approx(1 / 3)
    assert result["timeout_rate"] == pytest.approx(1 / 3)
    assert result["pellet_win_rate"] == 0.0
    assert result["evaluation_cutoff_rate"] == pytest.approx(1 / 3)
    assert result["mean_steps_to_capture"] == 10.0
    assert result["median_steps_to_capture"] == 10.0
    assert result["frac_steps_visible"] == pytest.approx(1 / 3)
    assert result["mean_newly_spotted_count"] == 1.0
    assert result["mean_shaping_return"] == 0.0
    assert result["mean_terminal_return"] == pytest.approx(8 / 3)


def test_aggregate_episodes_uses_nan_capture_time_when_nothing_is_captured():
    result = eval_report._aggregate_episodes([_episode(timeout=True)])

    assert math.isnan(result["mean_steps_to_capture"])
    assert math.isnan(result["median_steps_to_capture"])


def test_variant_summary_uses_training_rows_for_uncertainty_and_pools_diagnostics():
    rows = [
        {
            "reward_id": "current",
            "reward_class": "rewards:Current",
            "learner": "iql",
            "capture_rate": 0.25,
            "mean_steps_to_capture": 12.0,
        },
        {
            "reward_id": "current",
            "reward_class": "rewards:Current",
            "learner": "iql",
            "capture_rate": 0.75,
            "mean_steps_to_capture": 8.0,
        },
    ]
    pooled = {
        ("current", "iql"): [
            _episode(captured=True, steps=12, visible_steps=6),
            _episode(timeout=True, steps=20, visible_steps=10),
        ]
    }

    summary = eval_report._build_variant_summary(rows, pooled)[0]

    assert summary["n_seeds"] == 2
    assert summary["n_episodes_total"] == 2
    assert summary["capture_rate_mean"] == 0.5
    assert summary["capture_rate_std"] == pytest.approx(1 / (2 * 2**0.5))
    assert summary["time_to_capture_mean"] == 10.0
    assert summary["time_to_capture_std"] == pytest.approx(2 * 2**0.5)
    assert summary["n_capturing_seeds"] == 2
    assert summary["frac_steps_visible"] == 0.5


def test_reward_runs_root_supports_strategy_and_legacy_layouts(tmp_path):
    strategy_root = tmp_path / "variant"
    strategy_root.mkdir()

    assert eval_report._reward_runs_root(tmp_path, "variant") == strategy_root
    assert eval_report._reward_runs_root(tmp_path, "current") == tmp_path
    with pytest.raises(FileNotFoundError):
        eval_report._reward_runs_root(tmp_path, "missing")


def test_write_csv_preserves_old_fields_and_adds_new_metrics(tmp_path):
    output = tmp_path / "report.csv"
    row = {field: "" for field in eval_report.REPORT_FIELDS}

    eval_report._write_csv([row], output, eval_report.REPORT_FIELDS)

    with output.open(newline="", encoding="utf-8") as handle:
        header = next(csv.reader(handle))
    assert "ghost_win_rate" in header
    assert "mean_episode_return" in header
    assert "capture_rate" in header
    assert "mean_steps_to_capture" in header
    assert "mean_shaping_return" in header


def test_eval_seed_base_remains_an_alias_for_seed_base(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        ["eval_report.py", "--eval-seed-base", "123"],
    )

    assert eval_report.parse_args().seed_base == 123
