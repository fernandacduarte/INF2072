"""Tests for the R1 decision-readout verdict + CSV parsing (plan-000034)."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from benchmarl_setup.summarize_r1 import read_capture_rates, verdict


def test_verdict_confound_when_random_opponent_is_learnable():
    msg = verdict({"iql": [95, 97, 96]}, {"iql": [39, 41, 40]})
    assert "CONFOUND" in msg


def test_verdict_genuine_when_random_opponent_also_plateaus():
    msg = verdict({"iql": [38, 41, 40]}, {"iql": [39, 41, 40]})
    assert "GENUINE" in msg


def test_verdict_inconclusive_when_no_p_rows():
    msg = verdict({}, {"iql": [40]})
    assert "INCONCLUSIVE" in msg


def test_read_capture_rates_prefers_checkpoint_native_and_skips_live_capture(tmp_path):
    maze = tmp_path / "default" / "iql_run"
    maze.mkdir(parents=True)
    # Checkpoint-native paired-eval aggregate (the file we WANT to read).
    (maze / "reward_eval_host_by_variant.csv").write_text(
        "learner,capture_rate_mean,capture_rate_std\niql,0.96,0.01\n",
        encoding="utf-8",
    )
    # Hard-forced live-capture aggregate (must be IGNORED even though it matches by_variant).
    (maze / "evaluation_report_live_capture_checkpoint_60000_by_variant.csv").write_text(
        "learner,capture_rate_mean,capture_rate_std\niql,0.40,0.02\n",
        encoding="utf-8",
    )
    rates = read_capture_rates(tmp_path)
    assert rates == {"iql": [96.0]}  # fraction promoted to percent; live-capture excluded


def test_read_capture_rates_falls_back_to_per_seed_rows(tmp_path):
    maze = tmp_path / "default" / "vdn_run"
    maze.mkdir(parents=True)
    (maze / "reward_eval_host.csv").write_text(
        "learner,train_seed,capture_rate\nvdn,0,0.90\nvdn,1,0.80\n",
        encoding="utf-8",
    )
    rates = read_capture_rates(tmp_path)
    assert rates == {"vdn": [90.0, 80.0]}
