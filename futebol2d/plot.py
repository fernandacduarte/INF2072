"""
Plotting utility for visualizing training results.

Loads training CSV files and creates plots to compare learning curves
across different algorithms (IQL, VDN, QMIX).

Generates two plots:
  1. Reward curves (moving average) for comparing sample efficiency
  2. Epsilon schedules for comparing exploration decay

Usage:
    python -m plot iql_training.csv vdn_training.csv qmix_training.csv \\
        --labels IQL VDN QMIX --window 20 --save comparison.png
"""
import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def load_training_csv(path):
    """
    Load training history from CSV file.

    Expected CSV format:
      episode,reward,epsilon
      1,0.5,0.5
      2,-0.001,0.498

    Args:
        path (str): Path to training CSV file

    Returns:
        tuple: (episodes_array, rewards_array, epsilons_array) as numpy arrays
    """
    episodes = []  # Episode numbers
    rewards = []  # Episode rewards
    epsilons = []  # Epsilon values
    
    # Read CSV file
    with open(path, newline="", encoding="utf-8") as csvfile:
        # Create CSV reader
        reader = csv.DictReader(csvfile)
        # Read each row
        for row in reader:
            # Parse episode number
            episodes.append(int(row["episode"]))
            # Parse reward
            rewards.append(float(row["reward"]))
            # Parse epsilon
            epsilons.append(float(row["epsilon"]))
    
    # Convert lists to numpy arrays for efficient operations
    return np.array(episodes), np.array(rewards), np.array(epsilons)


def moving_average(values, window=20):
    """
    Compute moving average to smooth noisy reward curves.

    Uses convolution with uniform kernel for efficient computation.

    Args:
        values (np.array): Input values to smooth
        window (int): Window size for averaging. Default 20.

    Returns:
        np.array: Smoothed values (length reduced by window-1)
    """
    # Handle edge case of window size 1
    if window <= 1:
        return values
    # Compute convolution with uniform filter: np.ones(window) / window
    # This is equivalent to sliding average
    return np.convolve(values, np.ones(window) / window, mode="valid")


def plot_training(files, labels=None, window=20, save_path=None):
    """
    Plot training curves comparing multiple algorithms.

    Creates two subplots:
      1. Reward curves (moving average) - shows sample efficiency
      2. Epsilon schedules - shows exploration decay

    Args:
        files (list): Paths to training CSV files
        labels (list): Labels for each file (default: filenames)
        window (int): Moving average window size. Default 20.
        save_path (str): Path to save figure (optional)
    """
    # Set default labels to filenames if not provided
    if labels is None:
        labels = [Path(f).stem for f in files]
    
    # ============ PLOT 1: REWARD CURVES ============
    # Create figure with 10x5 inch size
    plt.figure(figsize=(10, 5))
    
    # Plot reward curve for each training run
    for path, label in zip(files, labels):
        # Load training data from CSV
        episodes, rewards, _ = load_training_csv(path)
        # Compute moving average for smoothing
        avg_rewards = moving_average(rewards, window)
        # Plot: episodes (trimmed to match average) vs smoothed rewards
        # Note: moving_average reduces length by window-1, so trim episodes array
        plt.plot(episodes[: len(avg_rewards)], avg_rewards, label=label)
    
    # Formatting for reward plot
    plt.xlabel("Episode")
    plt.ylabel(f"Reward (moving average, window={window})")
    plt.title("Training reward comparison")
    plt.legend()
    plt.grid(True)
    
    # Save reward plot if path provided
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Saved figure to {save_path}")
    # Display plot
    plt.show()

    # ============ PLOT 2: EPSILON SCHEDULES ============
    # Create second figure for epsilon decay (10x4 inches)
    plt.figure(figsize=(10, 4))
    
    # Plot epsilon schedule for each training run
    for path, label in zip(files, labels):
        # Load training data from CSV
        episodes, _, epsilons = load_training_csv(path)
        # Plot raw epsilon values (no smoothing needed)
        plt.plot(episodes, epsilons, label=label)
    
    # Formatting for epsilon plot
    plt.xlabel("Episode")
    plt.ylabel("Epsilon")
    plt.title("Exploration schedule")
    plt.legend()
    plt.grid(True)
    
    # Save epsilon plot if path provided
    if save_path:
        # Create epsilon plot filename by inserting "_epsilon" before extension
        save_path_eps = Path(save_path).with_name(Path(save_path).stem + "_epsilon" + Path(save_path).suffix)
        plt.savefig(save_path_eps, dpi=150, bbox_inches="tight")
        print(f"Saved epsilon figure to {save_path_eps}")
    # Display plot
    plt.show()


if __name__ == "__main__":
    """Command-line interface for plotting training results."""
    # Create argument parser
    parser = argparse.ArgumentParser(description="Plot training results from saved CSV files")
    # Input files
    parser.add_argument("files", nargs="+",
                        help="One or more training CSV files to compare")
    # Custom labels
    parser.add_argument("--labels", nargs="+", default=None,
                        help="Optional labels for each file (default: filenames)")
    # Smoothing window
    parser.add_argument("--window", type=int, default=20,
                        help="Moving average window for reward smoothing")
    # Output figure path
    parser.add_argument("--save", default=None,
                        help="Optional path to save the reward plot image")
    # Parse arguments
    args = parser.parse_args()

    # Validate label count
    if args.labels and len(args.labels) != len(args.files):
        raise ValueError("Number of labels must match number of files")

    # Create plots
    plot_training(args.files, labels=args.labels, window=args.window, save_path=args.save)
