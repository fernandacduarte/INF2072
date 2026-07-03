"""Smoke tests for the R1 positive-control battery launcher (plan-000034)."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from benchmarl_setup.run_r1_positive_control import build_condition_command


def _value_after(command, flag):
    return command[command.index(flag) + 1]


def _common_kwargs(**overrides):
    base = dict(
        algorithms="iql,vdn,qmixglobal",
        seeds="0,1,2,3,4",
        max_frames=60000,
        eval_episodes=40,
        save_folder="/tmp/r1/condition",
    )
    base.update(overrides)
    return base


def test_condition_p_pins_truly_random_opponent_full_obs():
    cmd = build_condition_command("P", **_common_kwargs())
    # Truly-random opponent in isolation.
    assert "--pacman-curriculum" in cmd and _value_after(cmd, "--pacman-curriculum") == "off"
    assert "--pacman-random-action-prob" in cmd
    assert _value_after(cmd, "--pacman-random-action-prob") == "1.0"
    # Sparse reward (no orbit term) and a populated DV.
    assert _value_after(cmd, "--reward-ids") == "capture_v0"
    assert _value_after(cmd, "--eval-episodes") == "40"
    assert _value_after(cmd, "--seeds") == "0,1,2,3,4"
    # Full observability: the local-view flag must be absent.
    assert "--ghost-view-size" not in cmd


def test_condition_c_uses_curriculum():
    cmd = build_condition_command("C", **_common_kwargs())
    assert _value_after(cmd, "--pacman-curriculum") == "easy-medium-hard"
    assert "--pacman-curriculum-max-frames" in cmd
    # No fixed random-prob override under the curriculum (stages drive difficulty).
    assert "--pacman-random-action-prob" not in cmd


def test_matched_local_view_applies_to_both_arms():
    p_cmd = build_condition_command("P", **_common_kwargs(ghost_view_size=5))
    c_cmd = build_condition_command("C", **_common_kwargs(ghost_view_size=5))
    assert _value_after(p_cmd, "--ghost-view-size") == "5"
    assert _value_after(c_cmd, "--ghost-view-size") == "5"


def test_unknown_condition_rejected():
    with pytest.raises(ValueError):
        build_condition_command("Z", **_common_kwargs())
