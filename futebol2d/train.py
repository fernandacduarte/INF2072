import argparse
import csv
import os
import random

import numpy as np
import torch

from futebol2d.algos import IQLLearner, VDNLearner, QMIXLearner, ReplayBuffer
from futebol2d.env import SimpleFootballEnv


def make_learner(name, obs_dim, n_actions, n_agents, state_dim, device):
    if name == "iql":
        return IQLLearner(obs_dim, n_actions, n_agents, device=device)
    if name == "vdn":
        return VDNLearner(obs_dim, n_actions, n_agents, device=device)
    if name == "qmix":
        return QMIXLearner(obs_dim, n_actions, n_agents, state_dim, device=device)
    raise ValueError(f"Unknown learner: {name}")


def save_training_csv(path, rewards, epsilons):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, mode="w", newline="", encoding="utf-8") as csv_file:
        fieldnames = ["episode", "reward", "epsilon"]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for episode, (reward, epsilon) in enumerate(zip(rewards, epsilons), start=1):
            writer.writerow({"episode": episode, "reward": reward, "epsilon": epsilon})


def run_training(algorithm, episodes, device, n_agents=2, output_csv=None, output_model=None):
    env = SimpleFootballEnv(n_agents=n_agents)
    obs_dim = len(env.reset()[0])
    n_actions = env.action_dim
    n_agents = env.n_agents
    state_dim = obs_dim * n_agents
    learner = make_learner(algorithm, obs_dim, n_actions, n_agents, state_dim, device)
    buffer = ReplayBuffer(capacity=10000, n_agents=n_agents, obs_dim=obs_dim)

    epsilon = 0.5
    epsilon_decay = 0.995
    min_epsilon = 0.05
    batch_size = 32
    target_update = 100

    rewards = []
    epsilons = []
    for episode in range(1, episodes + 1):
        obs = env.reset()
        episode_reward = 0.0
        done = False
        episode_epsilon = epsilon

        while not done:
            actions = learner.act(obs, epsilon)
            next_obs, reward, dones, _ = env.step(actions)
            buffer.push(obs, actions, reward[0], next_obs, dones[0])
            obs = next_obs
            episode_reward += reward[0]
            done = dones[0]

            if len(buffer) >= batch_size:
                batch = buffer.sample(batch_size)
                learner.update(batch)

        rewards.append(episode_reward)
        epsilons.append(episode_epsilon)
        epsilon = max(min_epsilon, epsilon * epsilon_decay)

        if episode % 20 == 0:
            avg_reward = np.mean(rewards[-20:])
            print(f"{algorithm.upper()} episode {episode}/{episodes} avg_reward={avg_reward:.3f} epsilon={epsilon:.3f}")

        if episode % target_update == 0 and hasattr(learner, "_sync_targets"):
            learner._sync_targets()

    if output_csv is None:
        output_csv = f"{algorithm}_training.csv"
    save_training_csv(output_csv, rewards, epsilons)
    print(f"Saved training log to {output_csv}")

    if output_model is None:
        output_model = f"{algorithm}_model.pth"
    learner.save(output_model)
    print(f"Saved trained model to {output_model}")

    return rewards, epsilons


def main():
    parser = argparse.ArgumentParser(description="Train IQL, VDN, or QMIX on a simple football game")
    parser.add_argument("--algo", choices=["iql", "vdn", "qmix"], default="iql")
    parser.add_argument("--episodes", type=int, default=300)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--n-agents", type=int, default=2, help="Number of agents in the environment")
    parser.add_argument("--output-csv", default=None,
                        help="Path to save training results as a CSV file")
    parser.add_argument("--save-model", default=None,
                        help="Path to save the trained model checkpoint")
    args = parser.parse_args()

    random.seed(0)
    np.random.seed(0)
    torch.manual_seed(0)

    run_training(args.algo, args.episodes, args.device, n_agents=args.n_agents, output_csv=args.output_csv, output_model=args.save_model)


if __name__ == "__main__":
    main()
