import argparse
import time

import torch

from futebol2d.algos import IQLLearner, VDNLearner, QMIXLearner
from futebol2d.env import SimpleFootballEnv


def make_learner(name, obs_dim, n_actions, n_agents, state_dim, device):
    if name == "iql":
        return IQLLearner(obs_dim, n_actions, n_agents, device=device)
    if name == "vdn":
        return VDNLearner(obs_dim, n_actions, n_agents, device=device)
    if name == "qmix":
        return QMIXLearner(obs_dim, n_actions, n_agents, state_dim, device=device)
    raise ValueError(f"Unknown learner: {name}")


def evaluate(algorithm, model_path, device, n_agents=2, episodes=1, delay=0.5):
    env = SimpleFootballEnv(n_agents=n_agents)
    obs_dim = len(env.reset()[0])
    n_actions = env.action_dim
    n_agents = env.n_agents
    state_dim = obs_dim * n_agents

    learner = make_learner(algorithm, obs_dim, n_actions, n_agents, state_dim, device)
    if model_path is None:
        raise ValueError("A model checkpoint path is required for evaluation.")

    if algorithm == "qmix":
        learner = QMIXLearner.load_from_checkpoint(model_path, obs_dim, n_actions, n_agents, state_dim, device=device)
    else:
        learner = learner.load_from_checkpoint(model_path, obs_dim, n_actions, n_agents, device=device)

    for episode in range(1, episodes + 1):
        obs = env.reset()
        done = False
        total_reward = 0.0
        step = 0

        print(f"\n=== Episode {episode} ===")
        env.render()

        while not done:
            actions = learner.act(obs, epsilon=0.0)
            obs, rewards, dones, info = env.step(actions)
            total_reward += rewards[0]
            done = dones[0]
            step += 1

            env.render()
            print(f"step={step} actions={actions} reward={rewards[0]:.3f} done={done}")
            if delay > 0:
                time.sleep(delay)

        print(f"Episode {episode} finished: total_reward={total_reward:.3f} steps={step} score={info.get('score', False)}")


def main():
    parser = argparse.ArgumentParser(description="Evaluate a trained football agent and render gameplay")
    parser.add_argument("--algo", choices=["iql", "vdn", "qmix"], required=True)
    parser.add_argument("--model-path", required=True, help="Path to the saved model checkpoint")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--n-agents", type=int, default=2, help="Number of agents in the environment")
    parser.add_argument("--episodes", type=int, default=1)
    parser.add_argument("--delay", type=float, default=0.5, help="Seconds between rendered steps")
    args = parser.parse_args()

    evaluate(args.algo, args.model_path, args.device, n_agents=args.n_agents, episodes=args.episodes, delay=args.delay)


if __name__ == "__main__":
    main()
