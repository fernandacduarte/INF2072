"""
Plotting utility for visualizing training results.

Loads both single-seed training CSV files and multi-seed summary CSV files
to compare learning curves across different algorithms (IQL, VDN, QMIX).

Generates two plots:
    1. Reward curves:
         - Single-seed input: moving average reward
         - Multi-seed input: mean reward with mean +/- std shading
    2. Epsilon schedules for single-seed inputs only

Usage:
    python -m plot iql_training.csv vdn_training.csv qmix_training.csv \\
        --labels IQL VDN QMIX --window 20 --save comparison.png
"""
import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def resolve_auto_compare_files(runs_dir, seed=None):
    """
    Resolve default comparison files for IQL/VDN/QMIX from a runs folder.

    Args:
        runs_dir (str): Folder containing training outputs.
        seed (int | None): If None, use multiseed summaries; otherwise use seed-specific training CSVs.

    Returns:
        tuple: (files, labels, default_save_name)
    """
    runs_path = Path(runs_dir)
    algos = ["iql", "vdn", "qmix"]
    labels = [algo.upper() for algo in algos]

    if seed is None:
        files = [runs_path / f"{algo}_multiseed_summary.csv" for algo in algos]
        default_save_name = runs_path / "compare_multiseed.png"
    else:
        files = [runs_path / f"{algo}_seed{seed}_training.csv" for algo in algos]
        default_save_name = runs_path / f"compare_seed{seed}.png"

    missing = [str(path) for path in files if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Could not find expected comparison CSV files:\n"
            + "\n".join(missing)
            + "\nCheck your --runs-dir and seed selection."
        )

    return [str(path) for path in files], labels, str(default_save_name)


def detect_csv_type(path):
    """Detect whether CSV is single-seed training or multiseed summary."""
    with open(path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        fieldnames = reader.fieldnames or []

    training_cols = {"episode", "reward", "epsilon"}
    multiseed_cols = {"episode", "mean_reward", "std_reward"}

    if training_cols.issubset(set(fieldnames)):
        return "training"
    if multiseed_cols.issubset(set(fieldnames)):
        return "multiseed"

    raise ValueError(
        f"Unsupported CSV format for {path}. Expected training columns {sorted(training_cols)} "
        f"or multiseed columns {sorted(multiseed_cols)}. Found: {fieldnames}"
    )


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


def load_multiseed_summary_csv(path):
    """
    Load multi-seed reward summary.

    Expected CSV format:
      episode,mean_reward,std_reward,min_reward,max_reward

    Args:
        path (str): Path to multiseed summary CSV file

    Returns:
        tuple: (episodes_array, mean_rewards_array, std_rewards_array)
    """
    episodes = []
    mean_rewards = []
    std_rewards = []

    with open(path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            episodes.append(int(row["episode"]))
            mean_rewards.append(float(row["mean_reward"]))
            std_rewards.append(float(row["std_reward"]))

    return np.array(episodes), np.array(mean_rewards), np.array(std_rewards)


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
    
    has_training_input = False

    # ============ PLOT 1: REWARD CURVES ============
    # Create figure with 10x5 inch size
    plt.figure(figsize=(10, 5))
    
    # Plot reward curve for each input file (training or multiseed summary)
    for path, label in zip(files, labels):
        csv_type = detect_csv_type(path)

        if csv_type == "training":
            has_training_input = True
            # Single-seed: smooth noisy curve with moving average.
            episodes, rewards, _ = load_training_csv(path)
            avg_rewards = moving_average(rewards, window)
            plt.plot(episodes[: len(avg_rewards)], avg_rewards, label=label)
        else:
            # Multi-seed: show mean and uncertainty band.
            episodes, mean_rewards, std_rewards = load_multiseed_summary_csv(path)
            avg_mean = moving_average(mean_rewards, window)
            avg_std = moving_average(std_rewards, window)
            x = episodes[: len(avg_mean)]
            line, = plt.plot(x, avg_mean, label=label)
            color = line.get_color()
            plt.fill_between(x, avg_mean - avg_std, avg_mean + avg_std, color=color, alpha=0.2)
    
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

    # ============ PLOT 2: EPSILON SCHEDULES (single-seed only) ============
    if has_training_input:
        # Create second figure for epsilon decay (10x4 inches)
        plt.figure(figsize=(10, 4))

        # Plot epsilon only for single-seed training CSVs.
        for path, label in zip(files, labels):
            if detect_csv_type(path) != "training":
                continue
            episodes, _, epsilons = load_training_csv(path)
            plt.plot(episodes, epsilons, label=label)

        # Formatting for epsilon plot
        plt.xlabel("Episode")
        plt.ylabel("Epsilon")
        plt.title("Exploration schedule (single-seed inputs)")
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
    else:
        print("No single-seed training CSV input detected: skipping epsilon plot.")


if __name__ == "__main__":
    """Command-line interface for plotting training results."""
    # Create argument parser
    parser = argparse.ArgumentParser(description="Plot training results from saved CSV files")
    # Input files (manual mode)
    parser.add_argument("files", nargs="*",
                        help="One or more CSV files to compare (manual mode)")
    # Automatic comparison mode based on run folder
    parser.add_argument("--runs-dir", default=None,
                        help="Runs folder for automatic IQL/VDN/QMIX comparison")
    # In automatic mode, omit --seed to use all-seed summaries
    parser.add_argument("--seed", type=int, default=None,
                        help="Seed index for automatic mode (omit for multiseed summaries)")
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

    # Automatic mode: only runs folder + optional seed selection.
    if args.runs_dir is not None:
        if args.files:
            raise ValueError("Do not pass positional files with --runs-dir.")
        if args.labels is not None:
            raise ValueError("Do not pass --labels with --runs-dir; labels are fixed to IQL/VDN/QMIX.")

        files, labels, default_save = resolve_auto_compare_files(args.runs_dir, seed=args.seed)
        save_path = args.save if args.save else default_save
        plot_training(files, labels=labels, window=args.window, save_path=save_path)
    else:
        # Manual mode fallback for backwards compatibility.
        if not args.files:
            raise ValueError("Provide CSV files manually or use --runs-dir for automatic comparison mode.")

        # Validate label count
        if args.labels and len(args.labels) != len(args.files):
            raise ValueError("Number of labels must match number of files")

        # Create plots
        plot_training(args.files, labels=args.labels, window=args.window, save_path=args.save)
