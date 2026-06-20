"""Unit tests for the win-rate harness pure helpers (plan-000008).

These cover the two checkpoint-free functions in ``custom_environment.eval``:

- ``summarize_win_rate`` -- aggregates outcome labels into counts + ghost win
  rate (the citable metric).
- ``classify_outcome`` -- maps an env's terminal state to one of
  ``"ghosts"`` / ``"pacman"`` / ``"timeout"`` using the *same* predicates as the
  renderer's ``_build_final_result`` (so the headless harness and the on-screen
  result can never disagree about who won).

A tiny ``FakeEnv`` stands in for the real environment so no trained checkpoint
or BenchMARL rollout is required.
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from custom_environment.eval import classify_outcome, summarize_win_rate


class FakeEnv:
    """Minimal stand-in exposing only what ``classify_outcome`` reads."""

    def __init__(self, capture: bool, agents: list, step_count: int, max_steps: int):
        self._capture = capture
        self.agents = agents
        self.step_count = step_count
        self.max_steps = max_steps

    def _is_capture_state(self) -> bool:
        return self._capture


# --- summarize_win_rate -------------------------------------------------------

def test_summarize_win_rate_mixed():
    # 2 of 4 episodes are ghost wins -> 0.5 win rate.
    summary = summarize_win_rate(["ghosts", "pacman", "ghosts", "timeout"])
    assert summary["episodes"] == 4
    assert summary["ghosts"] == 2
    assert summary["pacman"] == 1
    assert summary["timeout"] == 1
    assert summary["ghosts_win_rate"] == 0.5


def test_summarize_win_rate_all_ghosts():
    summary = summarize_win_rate(["ghosts", "ghosts", "ghosts"])
    assert summary["ghosts"] == 3
    assert summary["ghosts_win_rate"] == 1.0


def test_summarize_win_rate_empty_has_zero_rate():
    # No episodes must not raise ZeroDivisionError.
    summary = summarize_win_rate([])
    assert summary["episodes"] == 0
    assert summary["ghosts_win_rate"] == 0.0


# --- classify_outcome ---------------------------------------------------------

def test_classify_outcome_capture_is_ghosts_win():
    env = FakeEnv(capture=True, agents=[], step_count=37, max_steps=200)
    assert classify_outcome(env, step=37, max_steps=200) == "ghosts"


def test_classify_outcome_agents_cleared_at_max_steps_is_pacman_win():
    # No capture, agents cleared, env reached its own time limit.
    env = FakeEnv(capture=False, agents=[], step_count=200, max_steps=200)
    assert classify_outcome(env, step=200, max_steps=200) == "pacman"


def test_classify_outcome_runner_cap_without_terminal_is_timeout():
    # No capture and episode still active (agents present) when the runner cap hit.
    env = FakeEnv(capture=False, agents=["ghost_1", "ghost_2"], step_count=50, max_steps=200)
    assert classify_outcome(env, step=50, max_steps=50) == "timeout"
