"""Live Pygame demo that runs until Pacman eats every pellet.

Lifts the environment's 200-step truncation so the defense-first Pacman has time
to clear the whole board, then renders the episode in a Pygame window. Ghosts
move randomly (same as ``render_demo.py``); the Pacman uses the deterministic
``PacmanPolicy``.

Usage:
    python custom_environment/run_until_clear.py --delay 0.10 --seed 11
"""

import sys
import time
import random
import argparse
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from custom_environment.env.pacman_environment import PacManEnvironment
from custom_environment.utils import build_maze

ACTION_NAME = {0: "RIGHT", 1: "LEFT", 2: "UP", 3: "DOWN"}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render a Pacman episode until every pellet is eaten."
    )
    parser.add_argument("--delay", type=float, default=0.10, help="Seconds between frames.")
    parser.add_argument("--maze", default="pinklike", choices=["default", "pinklike", "pinklike3"])
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--grid-size", type=int, default=20)
    parser.add_argument("--cap", type=int, default=20000, help="Safety step cap.")
    parser.add_argument(
        "--render-mode", default="human", choices=["human", "ascii"],
        help="human opens a Pygame window; ascii prints to the terminal.",
    )
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)

    render_mode = None if args.render_mode == "ascii" else "human"
    env = PacManEnvironment(
        global_view=build_maze(name=args.maze, size=args.grid_size),
        render_mode=render_mode, tile_size=28, fps=12, show_observations=True,
    )
    env.max_steps = args.cap  # lift the 200-step truncation
    env.reset(seed=args.seed)
    start = int(env._pellet_mask.sum())

    total = 0.0
    step = 0
    if render_mode == "human":
        env.render(learner="PacmanPolicy (clear-the-board)", total_reward=total, done=False)

    while env.agents and step < args.cap:
        step += 1
        actions = {a: int(env.action_space(a).sample()) for a in env.agents}
        _, rewards, terms, truncs, _ = env.step(actions)
        total += float(sum(rewards.values()))
        remaining = int(env._pellet_mask.sum())
        eaten = start - remaining
        if render_mode == "human":
            env.render(
                learner=f"clear-the-board | pellets {eaten}/{start}",
                total_reward=total,
                done=not env.agents,
                last_action_by_agent={a: ACTION_NAME.get(v, str(v)) for a, v in actions.items()},
                last_reward_by_agent=rewards,
            )
        else:
            print(f"step {step} | pellets {eaten}/{start} | reward {total:.2f}")
        if remaining == 0:
            outcome = {"title": "Pacman wins", "reason": "Every pellet eaten."}
            break
        if any(terms.values()):
            outcome = {"title": "Ghosts win", "reason": "Pacman was captured."}
            break
        if args.delay > 0:
            time.sleep(args.delay)
    else:
        outcome = {"title": "Run stopped", "reason": "Step cap reached."}

    remaining = int(env._pellet_mask.sum())
    outcome.update({"steps": step, "max_steps": args.cap, "total_reward": total})
    print(f"Finished | {outcome['title']} | steps={step} | pellets eaten={start - remaining}/{start}")
    if render_mode == "human":
        env.wait_for_close(
            learner="clear-the-board", total_reward=total, done=True, final_result=outcome,
        )
    env.close()


if __name__ == "__main__":
    main()
