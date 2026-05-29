"""
Training script for multi-agent reinforcement learning football game.

This module handles the training loop for IQL, VDN, and QMIX algorithms,
including:
  - Environment initialization
  - Experience collection and batching
  - Model updates and training
  - CSV logging of rewards and epsilon schedules
  - Model checkpointing

Run with: python -m train --algo iql --episodes 300 --device cuda
"""
import argparse
import csv
import os
import random

import numpy as np
import torch

from algos import IQLLearner, VDNLearner, QMIXLearner, ReplayBuffer
from env import SimpleFootballEnv

# Live plotting (optional)
try:
    from live_plot import LivePlotter
except ImportError:
    LivePlotter = None


ALGORITHM_ORDER = ["iql", "vdn", "qmix"]


def parse_grid_shape(text):
    """Parse grid shape from '<height>x<width>' into a tuple."""
    if text is None:
        return None
    lowered = text.lower().replace(" ", "")
    parts = lowered.split("x")
    if len(parts) != 2:
        raise ValueError("grid shape must use format <height>x<width>, e.g. 6x9")
    height = int(parts[0])
    width = int(parts[1])
    if height < 2 or width < 2:
        raise ValueError("grid shape must have height >= 2 and width >= 2")
    return (height, width)


def append_live_progress(path, algorithm, seed, episode, reward):
    """Append one live training event to shared progress file."""
    if not path:
        return
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, mode="a", encoding="utf-8") as handle:
        handle.write(f"{algorithm},{seed},{episode},{reward}\n")


def get_overlay_algorithms(current_algorithm):
    """Return algorithms to overlay in live plot up to and including current one."""
    if current_algorithm not in ALGORITHM_ORDER:
        return [current_algorithm]
    idx = ALGORITHM_ORDER.index(current_algorithm)
    return ALGORITHM_ORDER[: idx + 1]


def load_multiseed_summary(path):
    """Load episode mean/std reward arrays from a multiseed summary CSV."""
    means = []
    stds = []
    with open(path, mode="r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            means.append(float(row["mean_reward"]))
            stds.append(float(row["std_reward"]))
    return means, stds


def set_global_seed(seed):
    """Set Python, NumPy, and PyTorch random seeds for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

def make_learner(name, obs_dim, n_actions, n_agents, state_dim, device, lr=0.001):
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
        return IQLLearner(obs_dim, n_actions, n_agents, lr=lr, device=device)
    if name == "vdn":
        # Value Decomposition Networks: sum-based factorization
        return VDNLearner(obs_dim, n_actions, n_agents, lr=lr, device=device)
    if name == "qmix":
        # QMIX: learnable mixing network with monotonicity
        return QMIXLearner(obs_dim, n_actions, n_agents, state_dim, lr=lr, device=device)
    raise ValueError(f"Unknown learner: {name}")


def get_training_hyperparams(algorithm):
    """Return algorithm-specific training hyperparameters."""
    # Defaults used by IQL/VDN.
    params = {
        "lr": 0.001,
        "epsilon_decay": 0.995,
        "min_epsilon": 0.05,
        "target_update": 100,
    }

    # QMIX stability tuning:
    # 1) slower epsilon decay + higher floor for persistent exploration,
    # 2) more frequent target synchronization,
    # 3) lower learning rate to reduce optimization variance.
    if algorithm == "qmix":
        params.update(
            {
                "lr": 0.0003,
                "epsilon_decay": 0.998,
                "min_epsilon": 0.10,
                "target_update": 50,
            }
        )

    return params


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


def save_multiseed_curve_csv(path, reward_curves):
    """
    Save per-episode reward statistics (mean, std, min, max) aggregated across seeds.
    Each row is one episode, columns are statistics over all seeds.
    """
    reward_array = np.array(reward_curves, dtype=np.float32)
    means = reward_array.mean(axis=0)
    stds = reward_array.std(axis=0)
    mins = reward_array.min(axis=0)
    maxs = reward_array.max(axis=0)

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, mode="w", newline="", encoding="utf-8") as csv_file:
        fieldnames = ["episode", "mean_reward", "std_reward", "min_reward", "max_reward"]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for episode in range(1, reward_array.shape[1] + 1):
            idx = episode - 1
            writer.writerow(
                {
                    "episode": episode,
                    "mean_reward": float(means[idx]),
                    "std_reward": float(stds[idx]),
                    "min_reward": float(mins[idx]),
                    "max_reward": float(maxs[idx]),
                }
            )


def save_multiseed_eval_csv(path, seed_results):
    """
    Save per-seed evaluation metrics and artifact paths for multi-seed runs.
    Each row is one seed, columns are metrics and file paths.
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, mode="w", newline="", encoding="utf-8") as csv_file:
        fieldnames = [
            "seed",
            "eval_mean_reward",
            "eval_std_reward",
            "score_rate",
            "train_last20_mean",
            "training_csv",
            "model_path",
        ]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for result in seed_results:
            writer.writerow(result)


def evaluate_greedy_policy(learner, n_agents, n_defenders=1, grid_shape=None, episodes=20):
    """
    Evaluate a trained policy with greedy actions (epsilon=0.0).
    Returns mean/std reward and score rate over multiple episodes.
    """
    env = SimpleFootballEnv(n_agents=n_agents, n_defenders=n_defenders, grid_shape=grid_shape)
    episode_rewards = []
    score_count = 0

    for _ in range(episodes):
        obs = env.reset()
        done = False
        total_reward = 0.0
        info = {"score": False}

        while not done:
            actions = learner.act(obs, epsilon=0.0)
            obs, rewards, dones, info = env.step(actions)
            total_reward += rewards[0]
            done = dones[0]

        episode_rewards.append(total_reward)
        if info.get("score", False):
            score_count += 1

    return {
        "eval_mean_reward": float(np.mean(episode_rewards)),
        "eval_std_reward": float(np.std(episode_rewards)),
        "score_rate": float(score_count / episodes) if episodes > 0 else 0.0,
    }


def run_training(algorithm,
                 episodes,
                 device,
                 n_agents=2,
                 n_defenders=1,
                 grid_shape=None,
                 output_csv=None,
                 output_model=None,
                 seed=0,
                 eval_episodes=20,
                 live_plotter=None,
                 live_progress_path=None):
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
    # Seed all random generators for reproducible runs.
    set_global_seed(seed)  # Ensure reproducibility for each run

    # Initialize environment with specified number of agents
    env = SimpleFootballEnv(n_agents=n_agents, n_defenders=n_defenders, grid_shape=grid_shape)
    # Get observation dimension from environment
    obs_dim = len(env.reset()[0])
    # Get number of actions
    n_actions = env.action_dim
    # Get number of agents from environment
    n_agents = env.n_agents
    # Calculate state dimension (flattened all agent observations)
    state_dim = obs_dim * n_agents
    
    # Algorithm-specific hyperparameters (QMIX gets dedicated stability settings).
    hparams = get_training_hyperparams(algorithm)

    # Create learner based on algorithm
    learner = make_learner(algorithm,
                           obs_dim,
                           n_actions,
                           n_agents,
                           state_dim,
                           device,
                           lr=hparams["lr"])
    # Create replay buffer for experience storage
    buffer = ReplayBuffer(capacity=10000, n_agents=n_agents, obs_dim=obs_dim)

    # Exploration schedule parameters
    epsilon = 0.5  # Initial exploration probability
    epsilon_decay = hparams["epsilon_decay"]  # Decay rate per episode
    min_epsilon = hparams["min_epsilon"]  # Minimum exploration probability
    batch_size = 32  # Training batch size
    target_update = hparams["target_update"]  # Update target networks every N episodes

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
        # Always publish progress so a separate live-plot process can visualize all algorithms.
        append_live_progress(live_progress_path, algorithm, seed, episode, episode_reward)
        # Live plot update (if enabled)
        if live_plotter is not None:
            # In single-process mode, keep local updates fast.
            live_plotter.update(algorithm, episode, rewards, seed=seed)
            # In multi-process mode, refresh from shared progress file to include other algorithms.
            live_plotter.update_from_progress_file(live_progress_path)
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

    # Evaluate the trained model using greedy policy (no exploration)
    eval_metrics = evaluate_greedy_policy(learner,
                                          n_agents=n_agents,
                                          n_defenders=n_defenders,
                                          grid_shape=grid_shape,
                                          episodes=eval_episodes)
    print(
        "Eval "
        f"mean_reward={eval_metrics['eval_mean_reward']:.3f} "
        f"std={eval_metrics['eval_std_reward']:.3f} "
        f"score_rate={eval_metrics['score_rate']:.3f}"
    )

    # Return all relevant results for aggregation in multi-seed mode
    return {
        "rewards": rewards,
        "epsilons": epsilons,
        "seed": seed,
        "output_csv": output_csv,
        "output_model": output_model,
        **eval_metrics,
    }


def run_multi_seed_training(
    algorithm,
    episodes,
    device,
    n_agents,
    n_defenders,
    grid_shape,
    seeds,
    output_dir,
    eval_episodes,
    live_plot=False,
):
    """
    Run training and evaluation across multiple seeds.
    For each seed, saves per-seed logs and models, then aggregates results.
    """
    os.makedirs(output_dir, exist_ok=True)
    live_progress_path = os.path.join(output_dir, "live_progress.csvl")

    all_rewards = []  # List of per-seed reward curves
    seed_results = []  # List of per-seed evaluation metrics

    # Initialize live plotter if requested
    live_plotter = None
    if live_plot and LivePlotter is not None:
        # In multi-process mode we want to display all algorithms as they train.
        live_plotter = LivePlotter(algorithms=ALGORITHM_ORDER)
        # Plotting owner starts a fresh shared stream for this run.
        with open(live_progress_path, mode="w", encoding="utf-8") as handle:
            handle.write("")

        # Preload previously trained algorithms (if their summaries exist).
        for previous_algorithm in ALGORITHM_ORDER:
            if previous_algorithm == algorithm:
                continue

            summary_path = os.path.join(output_dir, f"{previous_algorithm}_multiseed_summary.csv")
            if not os.path.exists(summary_path):
                print(
                    f"Live plot overlay: {summary_path} not found; "
                    f"skipping {previous_algorithm.upper()}."
                )
                continue

            mean_rewards, std_rewards = load_multiseed_summary(summary_path)
            live_plotter.set_reference_curve(previous_algorithm, mean_rewards, std_rewards)

        # Pull any progress already written by concurrently running processes.
        live_plotter.update_from_progress_file(live_progress_path)

    for seed in seeds:
        # Generate unique output file names for each seed
        output_csv = os.path.join(output_dir, f"{algorithm}_seed{seed}_training.csv")
        output_model = os.path.join(output_dir, f"{algorithm}_seed{seed}_model.pth")
        # Run training and evaluation for this seed
        result = run_training(
            algorithm=algorithm,
            episodes=episodes,
            device=device,
            n_agents=n_agents,
            n_defenders=n_defenders,
            grid_shape=grid_shape,
            output_csv=output_csv,
            output_model=output_model,
            seed=seed,
            eval_episodes=eval_episodes,
            live_plotter=live_plotter,
            live_progress_path=live_progress_path,
        )
        all_rewards.append(result["rewards"])
        seed_results.append(
            {
                "seed": result["seed"],
                "eval_mean_reward": result["eval_mean_reward"],
                "eval_std_reward": result["eval_std_reward"],
                "score_rate": result["score_rate"],
                "train_last20_mean": float(np.mean(result["rewards"][-20:])),
                "training_csv": result["output_csv"],
                "model_path": result["output_model"],
            }
        )

    # Save aggregate statistics across all seeds
    summary_curve_path = os.path.join(output_dir, f"{algorithm}_multiseed_summary.csv")
    summary_eval_path = os.path.join(output_dir, f"{algorithm}_multiseed_eval.csv")
    save_multiseed_curve_csv(summary_curve_path, all_rewards)
    save_multiseed_eval_csv(summary_eval_path, seed_results)
    print(f"Saved multiseed reward summary to {summary_curve_path}")
    print(f"Saved multiseed eval summary to {summary_eval_path}")

    # Close live plot at the end to avoid blocking additional CLI runs.
    if live_plotter is not None:
        live_plotter.close()
    return summary_curve_path, summary_eval_path


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
    # Number of defenders
    parser.add_argument("--n-defenders", type=int, default=1,
                        help="Number of defenders in the environment")
    # Optional custom grid size override
    parser.add_argument("--grid-shape", default=None,
                        help="Optional grid size override as <height>x<width>. "
                             "If omitted, a heuristic based on --n-agents is used")
    # Base random seed
    parser.add_argument("--seed", type=int, default=0,
                        help="Base random seed")
    # Number of seeds for repeated runs
    parser.add_argument("--n-seeds", type=int, default=1,
                        help="Number of sequential seeds to run (starting from --seed)")
    # Greedy evaluation episodes after each training run
    parser.add_argument("--eval-episodes", type=int, default=20,
                        help="Number of greedy evaluation episodes per trained model")
    # Output directory for run artifacts
    parser.add_argument("--output-dir", default=".",
                        help="Directory to store logs, models, and multiseed summaries")
    # Output CSV path
    parser.add_argument("--output-csv", default=None,
                        help="Path to save training results as a CSV file")
    # Output model path
    parser.add_argument("--save-model", default=None,
                        help="Path to save the trained model checkpoint")

    # Live plot flag
    parser.add_argument("--live-plot", action="store_true",
                        help="Enable live plotting of rewards during training (multi-seed only)")
    # Parse command-line arguments
    args = parser.parse_args()
    grid_shape = parse_grid_shape(args.grid_shape) if args.grid_shape else None

    # If only one seed, run a single experiment (default behavior)
    if args.n_seeds <= 1:
        output_csv = args.output_csv or os.path.join(args.output_dir, f"{args.algo}_training.csv")
        output_model = args.save_model or os.path.join(args.output_dir, f"{args.algo}_model.pth")
        live_progress_path = os.path.join(args.output_dir, "live_progress.csvl")
        live_plotter = None
        if args.live_plot and LivePlotter is not None:
            live_plotter = LivePlotter(algorithms=ALGORITHM_ORDER)
            # Plotting owner starts a fresh shared stream for this run.
            with open(live_progress_path, mode="w", encoding="utf-8") as handle:
                handle.write("")
            live_plotter.update_from_progress_file(live_progress_path)
        run_training(
            args.algo,
            args.episodes,
            args.device,
            n_agents=args.n_agents,
            n_defenders=args.n_defenders,
            grid_shape=grid_shape,
            output_csv=output_csv,
            output_model=output_model,
            seed=args.seed,
            eval_episodes=args.eval_episodes,
            live_plotter=live_plotter,
            live_progress_path=live_progress_path,
        )
        if live_plotter is not None:
            live_plotter.close()
    else:
        # Multi-seed mode: run a sweep of seeds and aggregate results
        if args.output_csv or args.save_model:
            print("Ignoring --output-csv and --save-model in multiseed mode; per-seed names are auto-generated.")
        seeds = list(range(args.seed, args.seed + args.n_seeds))
        run_multi_seed_training(
            algorithm=args.algo,
            episodes=args.episodes,
            device=args.device,
            n_agents=args.n_agents,
            n_defenders=args.n_defenders,
            grid_shape=grid_shape,
            seeds=seeds,
            output_dir=args.output_dir,
            eval_episodes=args.eval_episodes,
            live_plot=args.live_plot,
        )


if __name__ == "__main__":
    main()
