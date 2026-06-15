import os
from pathlib import Path
import sys

import numpy as np

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from custom_environment.env.pacman_environment import PacManEnvironment
from custom_environment.utils import create_grid


def _has_color(frame: np.ndarray, color: tuple[int, int, int], tolerance: int = 8) -> bool:
    target = np.array(color, dtype=np.int16)
    pixels = frame.astype(np.int16)
    distance = np.abs(pixels - target).sum(axis=2)
    return bool(np.any(distance <= tolerance))


def test_rgb_array_render_smoke() -> None:
    env = PacManEnvironment(
        global_view=create_grid(),
        render_mode="rgb_array",
        tile_size=20,
        fps=10,
    )
    try:
        env.reset()
        frame = env.render()

        assert isinstance(frame, np.ndarray)
        assert frame.shape == (20 * 20 + 54, 20 * 20, 3)
        assert frame.dtype == np.uint8
        assert _has_color(frame, (255, 221, 0), tolerance=20)
        assert _has_color(frame, (0, 120, 255), tolerance=20)
        assert _has_color(frame, (255, 45, 70), tolerance=20)

        env.close()
        env.close()
    finally:
        env.close()


def test_observation_overlay_tints_visible_cells() -> None:
    env_with_overlay = PacManEnvironment(
        global_view=create_grid(),
        render_mode="rgb_array",
        tile_size=20,
        fps=10,
        show_observations=True,
    )
    env_without_overlay = PacManEnvironment(
        global_view=create_grid(),
        render_mode="rgb_array",
        tile_size=20,
        fps=10,
        show_observations=False,
    )
    try:
        env_with_overlay.reset()
        env_without_overlay.reset()

        frame_with_overlay = env_with_overlay.render()
        frame_without_overlay = env_without_overlay.render()

        assert isinstance(frame_with_overlay, np.ndarray)
        assert isinstance(frame_without_overlay, np.ndarray)
        # Initial ghost_1 sees cell row=1, col=2. This sample avoids the pellet dot and agent sprite.
        sample_y = 1 * 20 + 3
        sample_x = 2 * 20 + 3
        assert not np.array_equal(
            frame_with_overlay[sample_y, sample_x],
            frame_without_overlay[sample_y, sample_x],
        )
    finally:
        env_with_overlay.close()
        env_without_overlay.close()


def test_final_result_render_smoke() -> None:
    env = PacManEnvironment(
        global_view=create_grid(),
        render_mode="rgb_array",
        tile_size=20,
        fps=10,
    )
    try:
        env.reset()
        frame = env.render(
            learner="test",
            total_reward=12.34,
            done=True,
            final_result={
                "title": "Ghosts win",
                "reason": "Pacman was captured.",
                "steps": 7,
                "max_steps": 200,
                "total_reward": 12.34,
                "elapsed_seconds": 1.25,
            },
        )

        assert isinstance(frame, np.ndarray)
        assert frame.shape == (20 * 20 + 54, 20 * 20, 3)
        assert frame.dtype == np.uint8
    finally:
        env.close()


def test_capture_frame_returns_rgb_array_without_changing_render_mode() -> None:
    env = PacManEnvironment(
        global_view=create_grid(),
        render_mode="human",
        tile_size=20,
        fps=10,
    )
    try:
        env.reset()
        frame = env.capture_frame()

        assert env.render_mode == "human"
        assert isinstance(frame, np.ndarray)
        assert frame.shape == (20 * 20 + 54, 20 * 20, 3)
        assert frame.dtype == np.uint8
    finally:
        env.close()


if __name__ == "__main__":
    test_rgb_array_render_smoke()
    test_observation_overlay_tints_visible_cells()
    test_final_result_render_smoke()
    test_capture_frame_returns_rgb_array_without_changing_render_mode()
    print("Passed rendering smoke test")
