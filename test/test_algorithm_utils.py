from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from benchmarl_setup.algorithm_utils import training_exploration_schedule


def test_training_schedule_is_shared_across_algorithms_and_mazes():
    max_frames = 60000
    expected = {
        "epsilon_schedule_mode": "global",
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
        "epsilon_init": 1.0,
        "epsilon_end": 0.08,
        "epsilon_anneal_ratio": 1.0,
        "epsilon_anneal_frames": max_frames,
        "max_frames": max_frames,
        "epsilon_stage_boundary_1": max_frames // 3,
        "epsilon_stage_boundary_2": (2 * max_frames) // 3,
        "epsilon_easy_init": 1.0,
        "epsilon_easy_end": 0.25,
        "epsilon_medium_init": 0.65,
        "epsilon_medium_end": 0.20,
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
