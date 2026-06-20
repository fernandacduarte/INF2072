from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from custom_environment.env.domain.constant import Reward
from custom_environment.env.pacman_environment import PacManEnvironment
from custom_environment.utils import parse_layout


TEST_LAYOUT = [
    "%%%%%%%%%",
    "%G     G%",
    "%       %",
    "%   P   %",
    "%       %",
    "%%%%%%%%%",
]


def _make_environment() -> PacManEnvironment:
    env = PacManEnvironment(parse_layout(TEST_LAYOUT))
    env.reset()
    # Keep Pacman out of view so the per-ghost freeze logic is the focus.
    env._collect_visible_pacman_positions = lambda: (False, [])
    return env


def _freeze_all_ghosts_in_place(env: PacManEnvironment) -> None:
    for ghost in env.ghosts:
        ghost.prev_position = ghost.current_position


def test_freeze_escalation_grows_with_consecutive_stalls() -> None:
    env = _make_environment()
    n = len(env.ghosts)

    # Step 1: every ghost stays in place (prev == current, no movement).
    _freeze_all_ghosts_in_place(env)
    env._compute_team_reward(capture_happened=False)
    first = env.last_team_reward_breakdown["freeze_escalation"]

    # Step 2: still frozen -> the freeze penalty must get strictly more negative.
    _freeze_all_ghosts_in_place(env)
    env._compute_team_reward(capture_happened=False)
    second = env.last_team_reward_breakdown["freeze_escalation"]

    assert first < 0.0
    assert second < first  # escalates (strictly more negative)
    assert first == pytest.approx(n * Reward.FREEZE_ESCALATION.value * 1)
    assert second == pytest.approx(n * Reward.FREEZE_ESCALATION.value * 2)


def test_freeze_escalation_is_capped() -> None:
    env = _make_environment()
    n = len(env.ghosts)

    last = None
    for _ in range(env.max_freeze_escalation_steps + 5):
        _freeze_all_ghosts_in_place(env)
        env._compute_team_reward(capture_happened=False)
        last = env.last_team_reward_breakdown["freeze_escalation"]

    expected = n * Reward.FREEZE_ESCALATION.value * env.max_freeze_escalation_steps
    assert last == pytest.approx(expected)


def test_moving_resets_freeze_escalation() -> None:
    env = _make_environment()

    # Build up a stall streak first.
    _freeze_all_ghosts_in_place(env)
    env._compute_team_reward(capture_happened=False)
    assert all(ghost.stall_streak == 1 for ghost in env.ghosts)

    # Now both ghosts move; the freeze term must disappear and the streak reset.
    env.ghosts[0].prev_position = (1, 1)
    env.ghosts[0].current_position = (2, 1)
    env.ghosts[1].prev_position = (1, 7)
    env.ghosts[1].current_position = (2, 7)
    env._compute_team_reward(capture_happened=False)

    assert "freeze_escalation" not in env.last_team_reward_breakdown
    assert all(ghost.stall_streak == 0 for ghost in env.ghosts)
