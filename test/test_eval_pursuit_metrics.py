"""Tests for the pursuit-acquisition eval metrics (plan-000036 Step 3)."""

import math

from custom_environment.eval_report import _aggregate_episodes


def _episode(*, steps: int, visible_steps: int, time_to_first_contact: float) -> dict:
    """Minimal EpisodeResult with the fields _aggregate_episodes reads."""
    return {
        "captured": False,
        "timeout": True,
        "pellet_win": False,
        "evaluation_cutoff": False,
        "steps": steps,
        "team_return": 0.0,
        "reward_breakdown": {},
        "category_totals": {"shaping": 0.0, "terminal": 0.0},
        "visible_steps": visible_steps,
        "newly_spotted_count": 0,
        "pursuit_fraction": 0.0,
        "time_to_first_contact": time_to_first_contact,
    }


def test_time_to_first_contact_mean_is_surfaced():
    # Two episodes: first sight at 0.1 and 0.3 of the budget -> mean 0.2.
    episodes = [
        _episode(steps=100, visible_steps=50, time_to_first_contact=0.1),
        _episode(steps=100, visible_steps=10, time_to_first_contact=0.3),
    ]
    agg = _aggregate_episodes(episodes)
    assert math.isclose(agg["time_to_first_contact_mean"], 0.2, rel_tol=1e-9)


def test_visible_fraction_matches_visible_steps_over_steps():
    episodes = [
        _episode(steps=100, visible_steps=40, time_to_first_contact=0.05),
        _episode(steps=100, visible_steps=60, time_to_first_contact=0.05),
    ]
    agg = _aggregate_episodes(episodes)
    # frac_steps_visible is the mean of per-episode visible/steps = mean(0.4, 0.6).
    assert math.isclose(agg["frac_steps_visible"], 0.5, rel_tol=1e-9)


def test_never_seen_pacman_scores_worst_latency():
    # time_to_first_contact == 1.0 represents "never sighted".
    episodes = [_episode(steps=200, visible_steps=0, time_to_first_contact=1.0)]
    agg = _aggregate_episodes(episodes)
    assert math.isclose(agg["time_to_first_contact_mean"], 1.0, rel_tol=1e-9)
