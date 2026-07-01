from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from benchmarl_setup.algorithm_utils import epsilon_at_frame, training_exploration_schedule


def test_training_schedule_is_shared_across_algorithms_and_mazes():
    max_frames = 60000
    expected = {
        "epsilon_schedule_mode": "global",
        "epsilon_schedule_source": "global_default",
        "epsilon_init": 1.0,
        "epsilon_end": 0.1,
        "epsilon_anneal_ratio": 0.95,
        "epsilon_anneal_frames": int(max_frames * 0.95),
        "max_frames": max_frames,
    }

    algorithms = ("iql", "vdn", "qmixlocal", "qmixglobal", "qmix")
    mazes = ("default", "pinklike", "pinklike3")

    for algorithm in algorithms:
        for maze in mazes:
            assert training_exploration_schedule(algorithm, maze, max_frames) == expected


def test_training_schedule_curriculum_piecewise_values():
    max_frames = 60000
    expected = {
        "epsilon_schedule_mode": "curriculum_piecewise",
        "epsilon_schedule_source": "curriculum_default",
        "epsilon_init": 1.0,
        "epsilon_end": 0.08,
        "epsilon_anneal_ratio": 0.95,
        "epsilon_anneal_frames": max_frames,
        "max_frames": max_frames,
        "epsilon_stage_boundary_1": max_frames // 3,
        "epsilon_stage_boundary_2": (2 * max_frames) // 3,
        "epsilon_stage_decay_fraction": 0.4,
        "epsilon_easy_init": 1.0,
        "epsilon_easy_end": 0.08,
        "epsilon_medium_init": 0.65,
        "epsilon_medium_end": 0.08,
        "epsilon_hard_init": 0.55,
        "epsilon_hard_end": 0.08,
    }

    algorithms = ("iql", "vdn", "qmixlocal", "qmixglobal", "qmix")
    mazes = ("default", "pinklike", "pinklike3")

    for algorithm in algorithms:
        for maze in mazes:
            assert (
                training_exploration_schedule(
                    algorithm,
                    maze,
                    max_frames,
                    pacman_curriculum="easy-medium-hard",
                )
                == expected
            )


def test_training_schedule_mixed_curriculum_piecewise_values():
    max_frames = 60000
    expected = {
        "epsilon_schedule_mode": "curriculum_piecewise",
        "epsilon_schedule_source": "curriculum_default",
        "epsilon_init": 1.0,
        "epsilon_end": 0.08,
        "epsilon_anneal_ratio": 0.95,
        "epsilon_anneal_frames": max_frames,
        "max_frames": max_frames,
        "epsilon_stage_boundary_1": max_frames // 3,
        "epsilon_stage_boundary_2": (2 * max_frames) // 3,
        "epsilon_stage_decay_fraction": 0.4,
        "epsilon_easy_init": 1.0,
        "epsilon_easy_end": 0.08,
        "epsilon_medium_init": 0.65,
        "epsilon_medium_end": 0.08,
        "epsilon_hard_init": 0.55,
        "epsilon_hard_end": 0.08,
    }

    algorithms = ("iql", "vdn", "qmixlocal", "qmixglobal", "qmix")
    mazes = ("default", "pinklike", "pinklike3")

    for algorithm in algorithms:
        for maze in mazes:
            assert (
                training_exploration_schedule(
                    algorithm,
                    maze,
                    max_frames,
                    pacman_curriculum="mixed-easy-medium-hard",
                )
                == expected
            )


def test_training_schedule_rejects_invalid_algorithm():
    try:
        training_exploration_schedule("invalid_algo", "default", 1000)
    except ValueError as error:
        assert "Unsupported algorithm" in str(error)
    else:
        raise AssertionError("Expected ValueError for unsupported algorithm")


def test_training_schedule_rejects_invalid_curriculum_mode():
    try:
        training_exploration_schedule(
            "iql",
            "default",
            1000,
            pacman_curriculum="invalid_curriculum",
        )
    except ValueError as error:
        assert "Unsupported pacman_curriculum" in str(error)
    else:
        raise AssertionError("Expected ValueError for invalid pacman_curriculum")


def test_epsilon_at_frame_curriculum_stage_decay_plateau_points():
    max_frames = 60000
    schedule = training_exploration_schedule(
        "iql",
        "pinklike3",
        max_frames,
        pacman_curriculum="easy-medium-hard",
    )

    b1 = int(schedule["epsilon_stage_boundary_1"])
    b2 = int(schedule["epsilon_stage_boundary_2"])
    decay_fraction = float(schedule["epsilon_stage_decay_fraction"])

    easy_decay_end = int(b1 * decay_fraction)
    medium_span = b2 - b1
    medium_decay_end = int(b1 + medium_span * decay_fraction)
    hard_span = max_frames - b2
    hard_decay_end = int(b2 + hard_span * decay_fraction)

    assert abs(epsilon_at_frame(0, schedule) - 1.0) < 1e-9
    assert abs(epsilon_at_frame(easy_decay_end, schedule) - 0.08) < 1e-9
    assert abs(epsilon_at_frame(easy_decay_end + 100, schedule) - 0.08) < 1e-9

    assert abs(epsilon_at_frame(b1, schedule) - 0.65) < 1e-9
    assert abs(epsilon_at_frame(medium_decay_end, schedule) - 0.08) < 1e-9
    assert abs(epsilon_at_frame(medium_decay_end + 100, schedule) - 0.08) < 1e-9

    assert abs(epsilon_at_frame(b2, schedule) - 0.55) < 1e-9
    assert abs(epsilon_at_frame(hard_decay_end, schedule) - 0.08) < 1e-9
    assert abs(epsilon_at_frame(hard_decay_end + 100, schedule) - 0.08) < 1e-9
    assert abs(epsilon_at_frame(max_frames, schedule) - 0.08) < 1e-9


def test_training_schedule_curriculum_respects_cli_override_values():
    max_frames = 60000
    schedule = training_exploration_schedule(
        "iql",
        "pinklike3",
        max_frames,
        pacman_curriculum="easy-medium-hard",
        anneal_ratio=0.5,
        epsilon_init=0.9,
        epsilon_end=0.05,
    )

    assert schedule["epsilon_schedule_mode"] == "global"
    assert schedule["epsilon_schedule_source"] == "global_cli_override"
    assert abs(float(schedule["epsilon_init"]) - 0.9) < 1e-9
    assert abs(float(schedule["epsilon_end"]) - 0.05) < 1e-9
    assert abs(float(schedule["epsilon_anneal_ratio"]) - 0.5) < 1e-9
    assert int(schedule["epsilon_anneal_frames"]) == int(max_frames * 0.5)
