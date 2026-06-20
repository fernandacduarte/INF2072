"""Live Pygame run that continues until Pacman eats every pellet.

Lifts the env's 200-step truncation so the defense-first Pacman can clear the
whole board. Random ghosts (like render_demo). Temp helper for plan-000007.
"""

import sys
import time
import random
import argparse
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from custom_environment.env.pacman_environment import PacManEnvironment
from custom_environment.utils import build_maze

ACTION_NAME = {0: "RIGHT", 1: "LEFT", 2: "UP", 3: "DOWN"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--delay", type=float, default=0.10)
    ap.add_argument("--maze", default="pinklike")
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--cap", type=int, default=20000)
    args = ap.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)

    env = PacManEnvironment(
        global_view=build_maze(name=args.maze, size=20),
        render_mode="human", tile_size=28, fps=12, show_observations=True,
    )
    env.max_steps = args.cap  # lift the 200-step truncation
    env.reset(seed=args.seed)
    start = int(env._pellet_mask.sum())

    total = 0.0
    step = 0
    env.render(learner="PacmanPolicy (clear-the-board)", total_reward=total, done=False)

    while env.agents and step < args.cap:
        step += 1
        actions = {a: int(env.action_space(a).sample()) for a in env.agents}
        _, rewards, terms, truncs, _ = env.step(actions)
        total += float(sum(rewards.values()))
        remaining = int(env._pellet_mask.sum())
        env.render(
            learner=f"clear-the-board | pellets {start - remaining}/{start}",
            total_reward=total,
            done=not env.agents,
            last_action_by_agent={a: ACTION_NAME.get(v, str(v)) for a, v in actions.items()},
            last_reward_by_agent=rewards,
        )
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
    env.wait_for_close(
        learner="clear-the-board",
        total_reward=total,
        done=True,
        final_result=outcome,
    )
    env.close()


if __name__ == "__main__":
    main()
