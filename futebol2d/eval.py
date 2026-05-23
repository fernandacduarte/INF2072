"""
Evaluation and visualization script for trained agents.

Loads a trained model checkpoint and renders gameplay with text-based visualization.
Useful for debugging agent behavior and understanding learned strategies.

Usage:
    python -m eval --algo iql --model-path iql_model.pth \\
    --n-agents 2 --episodes 3 --delay 0.5

The script renders a text grid showing:
  - Agent positions ('0', '1', '2', ...)
  - Ball holder indicator ('*' suffix)
  - Goal area (rightmost column marked with '|')
  - Step-by-step actions and rewards
"""
import argparse
import time

import torch

from algos import IQLLearner, VDNLearner, QMIXLearner
from env import SimpleFootballEnv


def make_learner(name, obs_dim, n_actions, n_agents, state_dim, device):
    """
    Factory function to create learner for loading checkpoint.

    Args:
        name (str): Algorithm name ("iql", "vdn", "qmix")
        obs_dim (int): Observation dimension
        n_actions (int): Number of actions
        n_agents (int): Number of agents
        state_dim (int): Global state dimension (for QMIX)
        device (str): "cpu" or "cuda"

    Returns:
        Learner: IQLLearner, VDNLearner, or QMIXLearner instance
    """
    if name == "iql":
        return IQLLearner(obs_dim, n_actions, n_agents, device=device)
    if name == "vdn":
        return VDNLearner(obs_dim, n_actions, n_agents, device=device)
    if name == "qmix":
        return QMIXLearner(obs_dim, n_actions, n_agents, state_dim, device=device)
    raise ValueError(f"Unknown learner: {name}")


def evaluate(algorithm, model_path, device, n_agents=2, episodes=1, delay=0.5):
    """
    Load trained model and evaluate with rendering.

    Evaluation process:
      1. Initialize environment with specified number of agents
      2. Load trained model from checkpoint
      3. For each episode:
         a. Render initial state
         b. For each step:
            - Select greedy action (epsilon=0.0)
            - Execute action and collect reward
            - Render updated state
            - Display action and reward info
            - Wait for specified delay
         c. Display final episode results

    Args:
        algorithm (str): Algorithm name ("iql", "vdn", "qmix")
        model_path (str): Path to trained model checkpoint
        device (str): "cpu" or "cuda"
        n_agents (int): Number of agents. Default 2.
        episodes (int): Number of episodes to evaluate. Default 1.
        delay (float): Seconds to wait between steps. Default 0.5.
    """
    # Initialize environment with specified number of agents
    env = SimpleFootballEnv(n_agents=n_agents)
    # Get observation dimension from environment
    obs_dim = len(env.reset()[0])
    # Get number of actions
    n_actions = env.action_dim
    # Get number of agents from environment (should match n_agents parameter)
    n_agents = env.n_agents
    # Calculate state dimension (flattened all agent observations)
    state_dim = obs_dim * n_agents

    # Create learner instance (skeleton for loading)
    learner = make_learner(algorithm, obs_dim, n_actions, n_agents, state_dim, device)
    # Validate model path is provided
    if model_path is None:
        raise ValueError("A model checkpoint path is required for evaluation.")

    # Load trained model from checkpoint
    # Use algorithm-specific class method to ensure proper restoration
    if algorithm == "qmix":
        learner = QMIXLearner.load_from_checkpoint(model_path, obs_dim, n_actions, n_agents, state_dim, device=device)
    else:
        learner = learner.load_from_checkpoint(model_path, obs_dim, n_actions, n_agents, device=device)

    # Evaluate for specified number of episodes
    for episode in range(1, episodes + 1):
        # Reset environment and get initial observation
        obs = env.reset()
        # Episode termination flag
        done = False
        # Accumulator for episode reward
        total_reward = 0.0
        # Step counter
        step = 0

        # Print episode header
        print(f"\n=== Episode {episode} ===")
        # Render initial state
        env.render()

        # Step loop: continue until episode terminates
        while not done:
            # Select actions using greedy policy (epsilon=0.0, no exploration)
            # This evaluates the learned behavior without exploration noise
            actions = learner.act(obs, epsilon=0.0)
            # Execute actions in environment
            obs, rewards, dones, info = env.step(actions)
            # Accumulate episode reward
            total_reward += rewards[0]
            # Update done flag
            done = dones[0]
            # Increment step counter
            step += 1

            # Render updated environment state
            env.render()
            # Print action and reward information for this step
            print(f"step={step} actions={actions} reward={rewards[0]:.3f} done={done}")
            # Wait for specified delay (visual pacing for human observation)
            if delay > 0:
                time.sleep(delay)

        # Print episode summary
        # Include final reward, number of steps, and whether goal was scored
        print(f"Episode {episode} finished: total_reward={total_reward:.3f} steps={step} score={info.get('score', False)}")


def main():
    """Parse command-line arguments and run evaluation."""
    # Create argument parser
    parser = argparse.ArgumentParser(description="Evaluate a trained football agent and render gameplay")
    # Algorithm selection (required)
    parser.add_argument("--algo", choices=["iql", "vdn", "qmix"], required=True,
                        help="Learning algorithm used to train the model")
    # Model checkpoint path (required)
    parser.add_argument("--model-path", required=True,
                        help="Path to the saved model checkpoint")
    # Computation device
    parser.add_argument("--device", default="cpu",
                        help="Device to evaluate on (cpu or cuda)")
    # Number of agents
    parser.add_argument("--n-agents", type=int, default=2,
                        help="Number of agents in the environment (must match training config)")
    # Number of evaluation episodes
    parser.add_argument("--episodes", type=int, default=1,
                        help="Number of episodes to evaluate and render")
    # Delay between steps for visualization
    parser.add_argument("--delay", type=float, default=0.5,
                        help="Seconds between rendered steps (0 for no delay)")
    # Parse command-line arguments
    args = parser.parse_args()

    # Run evaluation with parsed arguments
    evaluate(args.algo, args.model_path, args.device, n_agents=args.n_agents,
             episodes=args.episodes, delay=args.delay)


if __name__ == "__main__":
    main()
