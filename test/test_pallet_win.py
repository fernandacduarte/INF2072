"""Smoke tests for the pallet-win mechanic (plan-000003).

Pacman wins when every pallet on the board is eaten. The ghost team then
receives ``Reward.PACMAN_WIN_PALLETS`` and the episode truncates, symmetric
with the existing timeout-loss outcome.

These tests build a ``MazeSpec`` via ``parse_layout`` rather than a raw grid:
the constructor's back-compat ``spec_from_grid`` path assigns out-of-bounds
legacy spawns ``(1,18)``/``(18,9)``, which would crash ``reset()`` on a small
grid. The ASCII layout keeps spawns in bounds and the pellet set controlled.
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from custom_environment.env.domain.constant import Action, Reward
from custom_environment.env.pacman_environment import PacManEnvironment
from custom_environment.utils import parse_layout


# A single connected corridor: one Pacman ('P'), two ghosts ('G'), four pellets
# ('.'). Spawn cells carry no pellet, and Pacman starts four cells from the
# nearest ghost so no single step can produce a capture.
#   %P...G.G%   -> pellets at cols 2,3,4,6 = 4 pellets
LAYOUT = [
    "%%%%%%%%%",
    "%P...G.G%",
    "%%%%%%%%%",
]
EXPECTED_PALLETS = 4


def _make_env() -> PacManEnvironment:
    return PacManEnvironment(global_view=parse_layout(LAYOUT))


def test_total_pallets_tracked_on_reset():
    """Step 2: reset() records the per-episode pallet count from the mask."""
    env = _make_env()
    env.reset()
    assert env._total_pallets == EXPECTED_PALLETS
    # Spawn cells were cleared, so the live mask matches the recorded total.
    assert int(env._pellet_mask.sum()) == EXPECTED_PALLETS


def test_state_dim_includes_pallets_feature():
    """Step 4: global state grows by one feature and matches _state_dim."""
    env = _make_env()
    env.reset()
    assert env.state().shape[0] == env._state_dim
    # All pallets present at episode start -> normalized remaining == 1.0.
    assert env.state()[-1] == 1.0


def test_pallets_remaining_norm_drops_to_zero():
    """Step 4: clearing the mask drives the trailing state feature to 0.0."""
    env = _make_env()
    env.reset()
    env._pellet_mask[:] = False
    assert env.state()[-1] == 0.0


def test_pacman_win_terminates_with_penalty():
    """Step 3: when all pallets are eaten, the episode truncates and the team
    takes the PACMAN_WIN_PALLETS penalty (capture not happening)."""
    env = _make_env()
    env.reset()

    # Eat everything, then isolate the win penalty from movement shaping so the
    # reward assertion is exact.
    env._pellet_mask[:] = False
    env._compute_team_reward = lambda capture_happened: 0.0

    # Move both ghosts away from Pacman so no capture can occur this step.
    actions = {ghost.id: Action.MOVE_LEFT for ghost in env.ghosts}
    _, rewards, terminations, truncations, _ = env.step(actions)

    assert all(truncations.values()), "pallet exhaustion must truncate the episode"
    assert not any(terminations.values()), "no capture should be flagged"
    for ghost_id in rewards:
        assert rewards[ghost_id] == Reward.PACMAN_WIN_PALLETS.value
    # PettingZoo convention: active agents cleared once the episode ends.
    assert env.agents == []
