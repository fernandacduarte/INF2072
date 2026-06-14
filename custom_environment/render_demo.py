"""Run a random-policy Pacman episode for renderer testing."""

from __future__ import annotations

import argparse
import random
import sys
import time
from pathlib import Path

import numpy as np

# Ensure workspace root is importable when running this file by path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from custom_environment.env.pacman_environment import PacManEnvironment
from custom_environment.env.domain.constant import Observation
from custom_environment.utils import create_grid


SYMBOLS = {
    Observation.CAPUTRED.value: "X",
    Observation.EMPTY.value: " ",
    Observation.GHOST.value: "G",
    Observation.PAC_MAN.value: "P",
    Observation.WALL.value: "#",
}

ACTION_NAME = {
    0: "RIGHT",
    1: "LEFT",
    2: "UP",
    3: "DOWN",
}


def render_ascii(grid: np.ndarray) -> str:
    lines = []
    for row in grid:
        lines.append("".join(SYMBOLS.get(int(cell), "?") for cell in row))
    return "\n".join(lines)


def save_rgb_frame(frame: np.ndarray, output_path: Path) -> None:
    try:
        import pygame
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Pygame is required to save render screenshots. Install dependencies with "
            "`python -m pip install -r requirements.txt`."
        ) from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    surface = pygame.surfarray.make_surface(np.transpose(frame, (1, 0, 2)))
    pygame.image.save(surface, str(output_path))


def _random_actions(env: PacManEnvironment) -> dict[str, int]:
    return {agent: int(env.action_space(agent).sample()) for agent in env.agents}


def _build_final_result(
    env: PacManEnvironment,
    *,
    step: int,
    run_max_steps: int,
    total_reward: float,
    elapsed_seconds: float,
) -> dict:
    if env._is_capture_state():
        title = "Ghosts win"
        reason = "Pacman was captured."
    elif not env.agents and env.step_count >= env.max_steps:
        title = "Pacman wins"
        reason = "Pacman survived until the environment time limit."
    elif step >= run_max_steps:
        title = "Run stopped"
        reason = "The runner max-step limit was reached before the episode terminated."
    else:
        title = "Episode finished"
        reason = "The run ended without an active terminal condition."

    return {
        "title": title,
        "reason": reason,
        "steps": step,
        "max_steps": run_max_steps,
        "total_reward": total_reward,
        "elapsed_seconds": elapsed_seconds,
    }


def run_demo(
    *,
    render_mode: str,
    max_steps: int,
    delay: float,
    tile_size: int,
    fps: int,
    grid_size: int,
    number_ghosts: int,
    seed: int | None,
    screenshot_out: Path | None,
    show_observations: bool,
) -> None:
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    env = PacManEnvironment(
        global_view=create_grid(size=grid_size),
        number_ghosts=number_ghosts,
        render_mode=None if render_mode == "ascii" else render_mode,
        tile_size=tile_size,
        fps=fps,
        show_observations=show_observations,
    )

    observations, infos = env.reset(seed=seed)
    del observations, infos

    total_reward = 0.0
    done = False
    step = 0
    last_frame = None
    last_action_info = None
    last_reward_info = None
    start_time = time.perf_counter()
    final_result = None

    try:
        if render_mode == "ascii":
            print("Pacman random-policy demo (episode start):")
            print(render_ascii(env.global_view))
            print()
            print("Legend: #=Wall, G=Ghost, P=Pacman, X=Captured, <space>=Empty")
        else:
            frame = env.render(
                learner="random",
                total_reward=total_reward,
                done=done,
            )
            if render_mode == "rgb_array":
                last_frame = frame
            if screenshot_out is not None and render_mode != "rgb_array":
                last_frame = env.capture_frame(
                    learner="random",
                    total_reward=total_reward,
                    done=done,
                )

        while env.agents and not done and step < max_steps:
            step += 1
            actions = _random_actions(env)
            observations, rewards, terminations, truncations, infos = env.step(actions)
            del observations, terminations, truncations, infos

            total_reward += float(sum(rewards.values()))
            done = not env.agents
            action_info = {
                agent: ACTION_NAME.get(action, str(action))
                for agent, action in actions.items()
            }
            last_action_info = action_info
            last_reward_info = rewards

            if render_mode == "ascii":
                print()
                print(f"Step {step} | learner=random | actions={action_info}")
                print(render_ascii(env.global_view))
                print(f"rewards={rewards} done={done}")
            else:
                frame = env.render(
                    learner="random",
                    total_reward=total_reward,
                    done=done,
                    last_action_by_agent=action_info,
                    last_reward_by_agent=rewards,
                )
                if render_mode == "rgb_array":
                    last_frame = frame
                print(f"Step {step} | learner=random | actions={action_info} | rewards={rewards} | done={done}")
                if screenshot_out is not None and render_mode != "rgb_array":
                    last_frame = env.capture_frame(
                        learner="random",
                        total_reward=total_reward,
                        done=done,
                        last_action_by_agent=action_info,
                        last_reward_by_agent=rewards,
                    )

            if delay > 0:
                time.sleep(delay)

        final_result = _build_final_result(
            env,
            step=step,
            run_max_steps=max_steps,
            total_reward=total_reward,
            elapsed_seconds=time.perf_counter() - start_time,
        )
        final_done = done or step >= max_steps

        if render_mode != "ascii":
            frame = env.render(
                learner="random",
                total_reward=total_reward,
                done=final_done,
                last_action_by_agent=last_action_info,
                last_reward_by_agent=last_reward_info,
                final_result=final_result,
            )
            if render_mode == "rgb_array":
                last_frame = frame
            if screenshot_out is not None and render_mode != "rgb_array":
                last_frame = env.capture_frame(
                    learner="random",
                    total_reward=total_reward,
                    done=final_done,
                    last_action_by_agent=last_action_info,
                    last_reward_by_agent=last_reward_info,
                    final_result=final_result,
                )
            if render_mode == "human":
                env.wait_for_close(
                    learner="random",
                    total_reward=total_reward,
                    done=final_done,
                    last_action_by_agent=last_action_info,
                    last_reward_by_agent=last_reward_info,
                    final_result=final_result,
                )
    finally:
        if screenshot_out is not None and last_frame is not None:
            save_rgb_frame(last_frame, screenshot_out)
            print(f"Saved screenshot: {screenshot_out}")
        env.close()

    print()
    result_title = final_result["title"] if final_result is not None else "unknown"
    print(
        f"Demo finished | steps={step} | total_reward={total_reward:.3f} "
        f"| done={done} | result={result_title}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Pacman with random ghost actions to test rendering."
    )
    parser.add_argument(
        "--render-mode",
        choices=["ascii", "human", "rgb_array"],
        default="human",
        help=(
            "Render output mode: ascii is a simple terminal grid, "
            "human opens the Pygame window, rgb_array returns image frames."
        ),
    )
    parser.add_argument("--max-steps", type=int, default=200)
    parser.add_argument("--delay", type=float, default=0.0)
    parser.add_argument("--tile-size", type=int, default=28)
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--grid-size", type=int, default=20)
    parser.add_argument("--number-ghosts", type=int, default=2)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument(
        "--screenshot-out",
        type=Path,
        default=None,
        help="Optional PNG path for the last rendered frame.",
    )
    parser.add_argument(
        "--hide-observations",
        action="store_true",
        help="Disable the translucent local-observation overlays in Pygame renders.",
    )
    args = parser.parse_args()

    run_demo(
        render_mode=args.render_mode,
        max_steps=args.max_steps,
        delay=args.delay,
        tile_size=args.tile_size,
        fps=args.fps,
        grid_size=args.grid_size,
        number_ghosts=args.number_ghosts,
        seed=args.seed,
        screenshot_out=args.screenshot_out,
        show_observations=not args.hide_observations,
    )


if __name__ == "__main__":
    main()
