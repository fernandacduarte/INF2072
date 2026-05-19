"""
Training script for multi-agent reinforcement learning football game.

This module handles the training loop for IQL, VDN, and QMIX algorithms,
including:
  - Environment initialization
  - Experience collection and batching
  - Model updates and training
  - CSV logging of rewards and epsilon schedules
  - Model checkpointing

Run with: python -m futebol2d.train --algo iql --episodes 300 --device cuda
"""
import argparse
import csv
import os
import random

import numpy as np
import torch

from futebol2d.algos import IQLLearner, VDNLearner, QMIXLearner, ReplayBuffer
from futebol2d.env import SimpleFootballEnv


def make_learner(name, obs_dim, n_actions, n_agents, state_dim, device):
    """
    Factory function to create appropriate learner based on algorithm name.

    Args:
        name (str): Algorithm name ("iql", "vdn", or "qmix")
        obs_dim (int): Observation dimension
        n_actions (int): Number of actions
        n_agents (int): Number of agents
        state_dim (int): Global state dimension (for QMIX)
        device (str): "cpu" or "cuda"

    Returns:
        Learner: IQLLearner, VDNLearner, or QMIXLearner instance
    """
    if name == "iql":
        # Independent Q-Learning: simple baseline
        return IQLLearner(obs_dim, n_actions, n_agents, device=device)
    if name == "vdn":
        # Value Decomposition Networks: sum-based factorization
        return VDNLearner(obs_dim, n_actions, n_agents, device=device)
    if name == "qmix":
        # QMIX: learnable mixing network with monotonicity
        return QMIXLearner(obs_dim, n_actions, n_agents, state_dim, device=device)
    raise ValueError(f"Unknown learner: {name}")


def save_training_csv(path, rewards, epsilons):
    """
    Save training history (rewards and epsilon values) to CSV file.

    CSV format:
      episode, reward, epsilon
      1, 0.5, 0.5
      2, -0.001, 0.498
      ...

    Args:
        path (str): Output file path
        rewards (list): Episode rewards
        epsilons (list): Epsilon values for each episode
    """
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    
    # Write CSV file
    with open(path, mode="w", newline="", encoding="utf-8") as csv_file:
        # Define column names
        fieldnames = ["episode", "reward", "epsilon"]
        # Create CSV writer
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        # Write header row
        writer.writeheader()
        # Write data rows (enumerate starts at 1 for 1-indexed episodes)
        for episode, (reward, epsilon) in enumerate(zip(rewards, epsilons), start=1):
            writer.writerow({"episode": episode, "reward": reward, "epsilon": epsilon})


def run_training(algorithm, episodes, device, n_agents=2, output_csv=None, output_model=None):
    """
    Train an agent on the football environment.

    Training loop:
      1. Initialize environment and learner
      2. For each episode:
         a. Reset environment
         b. For each step until done:
            - Select action using epsilon-greedy
            - Execute action and collect reward
            - Store in replay buffer
            - Update learner from random batch (if buffer full)
         c. Decay epsilon
         d. Periodically sync target networks
      3. Save training logs and model checkpoint

    Args:
        algorithm (str): Algorithm name ("iql", "vdn", "qmix")
        episodes (int): Number of episodes to train
        device (str): "cpu" or "cuda"
        n_agents (int): Number of agents. Default 2.
        output_csv (str): Path to save training CSV. Default: "{algorithm}_training.csv"
        output_model (str): Path to save model checkpoint. Default: "{algorithm}_model.pth"

    Returns:
        tuple: (rewards_list, epsilons_list)
    """
    # Initialize environment with specified number of agents
    env = SimpleFootballEnv(n_agents=n_agents)
    # Get observation dimension from environment
    obs_dim = len(env.reset()[0])
    # Get number of actions
    n_actions = env.action_dim
    # Get number of agents from environment
    n_agents = env.n_agents
    # Calculate state dimension (flattened all agent observations)
    state_dim = obs_dim * n_agents
    
    # Create learner based on algorithm
    learner = make_learner(algorithm, obs_dim, n_actions, n_agents, state_dim, device)
    # Create replay buffer for experience storage
    buffer = ReplayBuffer(capacity=10000, n_agents=n_agents, obs_dim=obs_dim)

    # Exploration schedule parameters
    epsilon = 0.5  # Initial exploration probability
    epsilon_decay = 0.995  # Decay rate per episode
    min_epsilon = 0.05  # Minimum exploration probability
    batch_size = 32  # Training batch size
    target_update = 100  # Update target networks every N episodes

    rewards = []  # Record episode rewards
    epsilons = []  # Record epsilon values
    
    # Training loop over episodes
    for episode in range(1, episodes + 1):
        # Reset environment and get initial observations
        obs = env.reset()
        # Accumulator for episode reward
        episode_reward = 0.0
        # Episode termination flag
        done = False
        # Store epsilon at start of episode for logging
        episode_epsilon = epsilon

        # Step loop: continue until episode terminates
        while not done:
            # Select actions using epsilon-greedy policy
            actions = learner.act(obs, epsilon)
            # Execute actions in environment
            next_obs, reward, dones, _ = env.step(actions)
            # Store transition in replay buffer
            buffer.push(obs, actions, reward[0], next_obs, dones[0])
            # Update observation
            obs = next_obs
            # Accumulate episode reward
            episode_reward += reward[0]
            # Update done flag
            done = dones[0]

            # Train learner if buffer has enough samples
            if len(buffer) >= batch_size:
                # Sample random batch from buffer
                batch = buffer.sample(batch_size)
                # Update learner with batch
                learner.update(batch)

        # Store episode reward and epsilon for logging
        rewards.append(episode_reward)
        epsilons.append(episode_epsilon)
        # Decay epsilon for next episode (exploration decreases over time)
        epsilon = max(min_epsilon, epsilon * epsilon_decay)

        # Log progress every 20 episodes
        if episode % 20 == 0:
            # Calculate moving average of last 20 episode rewards
            avg_reward = np.mean(rewards[-20:])
            print(f"{algorithm.upper()} episode {episode}/{episodes} avg_reward={avg_reward:.3f} epsilon={epsilon:.3f}")

        # Periodically sync target networks (stabilizes learning)
        if episode % target_update == 0 and hasattr(learner, "_sync_targets"):
            learner._sync_targets()

    # Set default output CSV filename if not provided
    if output_csv is None:
        output_csv = f"{algorithm}_training.csv"
    # Save training logs to CSV
    save_training_csv(output_csv, rewards, epsilons)
    print(f"Saved training log to {output_csv}")

    # Set default output model filename if not provided
    if output_model is None:
        output_model = f"{algorithm}_model.pth"
    # Save trained model checkpoint
    learner.save(output_model)
    print(f"Saved trained model to {output_model}")

    return rewards, epsilons


def main():
    """Parse command-line arguments and run training."""
    # Create argument parser
    parser = argparse.ArgumentParser(description="Train IQL, VDN, or QMIX on a simple football game")
    # Algorithm selection
    parser.add_argument("--algo", choices=["iql", "vdn", "qmix"], default="iql",
                        help="Learning algorithm to train")
    # Training duration
    parser.add_argument("--episodes", type=int, default=300,
                        help="Number of training episodes")
    # Computation device
    parser.add_argument("--device", default="cpu",
                        help="Device to train on (cpu or cuda)")
    # Number of agents
    parser.add_argument("--n-agents", type=int, default=2,
                        help="Number of agents in the environment")
    # Output CSV path
    parser.add_argument("--output-csv", default=None,
                        help="Path to save training results as a CSV file")
    # Output model path
    parser.add_argument("--save-model", default=None,
                        help="Path to save the trained model checkpoint")
    # Parse command-line arguments
    args = parser.parse_args()

    # Set random seeds for reproducibility
    random.seed(0)  # Python random
    np.random.seed(0)  # NumPy random
    torch.manual_seed(0)  # PyTorch random

    # Run training with parsed arguments
    run_training(args.algo, args.episodes, args.device, n_agents=args.n_agents, 
                 output_csv=args.output_csv, output_model=args.save_model)


if __name__ == "__main__":
    main()
