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


def _best_seed_row(eval_csv_path):
    """Return best-seed row from a multiseed eval CSV using eval-time ranking."""
    rows = []
    with open(eval_csv_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            rows.append(row)

    if not rows:
        raise ValueError(f"Empty multiseed eval file: {eval_csv_path}")

    # Keep same priority used by evaluator to avoid mismatched seed selection.
    def row_key(row):
        return (
            float(row.get("score_rate", 0.0)),
            float(row.get("eval_mean_reward", -1e9)),
            float(row.get("train_last20_mean", -1e9)),
        )

    return max(rows, key=row_key)


def resolve_best_seed_training_files(runs_dir):
    """
    Resolve best-seed training CSV for IQL/VDN/QMIX from multiseed eval reports.

    Args:
        runs_dir (str): Folder containing multiseed eval and per-seed training outputs.

    Returns:
        tuple: (files, labels, seeds)
    """
    runs_path = Path(runs_dir)
    algos = ["iql", "vdn", "qmix"]

    files = []
    labels = []
    seeds = []

    for algo in algos:
        eval_csv = runs_path / f"{algo}_multiseed_eval.csv"
        if not eval_csv.exists():
            raise FileNotFoundError(f"Missing multiseed eval CSV: {eval_csv}")

        best = _best_seed_row(eval_csv)
        seed = int(best["seed"])
        training_csv = runs_path / f"{algo}_seed{seed}_training.csv"
        if not training_csv.exists():
            raise FileNotFoundError(
                f"Best-seed training CSV not found for {algo.upper()}: {training_csv}"
            )

        files.append(str(training_csv))
        labels.append(f"{algo.upper()} (best seed {seed})")
        seeds.append(seed)

    return files, labels, seeds


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


def running_mean(values):
    """Return per-episode running mean of a 1D array."""
    values = np.asarray(values, dtype=np.float64)
    return np.cumsum(values) / np.arange(1, len(values) + 1)


def plot_best_seed_mean_reward(runs_dir, save_path=None):
    """
    Plot running mean reward curves for the best seed of each algorithm.

    Best seed is selected from each `{algo}_multiseed_eval.csv`.

    Args:
        runs_dir (str): Folder containing run artifacts.
        save_path (str | None): Optional output path for figure image.
    """
    files, labels, _ = resolve_best_seed_training_files(runs_dir)

    plt.figure(figsize=(10, 5))
    for path, label in zip(files, labels):
        episodes, rewards, _ = load_training_csv(path)
        mean_rewards = running_mean(rewards)
        plt.plot(episodes, mean_rewards, label=label)

    plt.xlabel("Episode")
    plt.ylabel("Mean reward")
    plt.title("Best-seed mean reward comparison")
    plt.legend()
    plt.grid(True)

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Saved best-seed mean-reward figure to {save_path}")

    plt.show()


def plot_average_eval_metrics_table(runs_dir, save_path=None):
    """
    Generate a table image with average evaluation metrics across seeds.

    Reads each `{algo}_multiseed_eval.csv` and computes algorithm-level means for:
      - eval_mean_reward
      - eval_std_reward
      - score_rate

    Args:
        runs_dir (str): Folder containing multiseed eval CSV files.
        save_path (str | None): Optional output path for table image.
    """
    runs_path = Path(runs_dir)
    algos = ["iql", "vdn", "qmix"]
    rows = []

    for algo in algos:
        eval_csv = runs_path / f"{algo}_multiseed_eval.csv"
        if not eval_csv.exists():
            raise FileNotFoundError(f"Missing multiseed eval CSV: {eval_csv}")

        eval_means = []
        eval_stds = []
        score_rates = []

        with open(eval_csv, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                eval_means.append(float(row["eval_mean_reward"]))
                eval_stds.append(float(row["eval_std_reward"]))
                score_rates.append(float(row["score_rate"]))

        if not eval_means:
            raise ValueError(f"Empty multiseed eval file: {eval_csv}")

        rows.append([
            algo.upper(),
            f"{np.mean(eval_means):.3f}",
            f"{np.mean(eval_stds):.3f}",
            f"{np.mean(score_rates):.3f}",
        ])

    col_labels = [
        "Algorithm",
        "Mean Reward (avg)",
        "Std Reward (avg)",
        "Score Rate (avg)",
    ]

    fig, ax = plt.subplots(figsize=(9, 2.7))
    ax.axis("off")
    ax.set_title("Average Evaluation Metrics (across 10 seeds)", pad=12)

    table = ax.table(
        cellText=rows,
        colLabels=col_labels,
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.35)

    if save_path is None:
        save_path = runs_path / "average_eval_metrics_table.png"

    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    print(f"Saved average evaluation metrics table to {save_path}")
    plt.show()


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

        table_save_path = Path(args.runs_dir) / "average_eval_metrics_table.png"
        plot_average_eval_metrics_table(args.runs_dir, save_path=str(table_save_path))

        # In multiseed auto mode, also compare running mean reward for best seed per algorithm.
        if args.seed is None:
            best_seed_save_path = Path(save_path).with_name(
                Path(save_path).stem + "_best_seed_mean" + Path(save_path).suffix
            )
            plot_best_seed_mean_reward(args.runs_dir, save_path=str(best_seed_save_path))
    else:
        # Manual mode fallback for backwards compatibility.
        if not args.files:
            raise ValueError("Provide CSV files manually or use --runs-dir for automatic comparison mode.")

        # Validate label count
        if args.labels and len(args.labels) != len(args.files):
            raise ValueError("Number of labels must match number of files")

        # Create plots
        plot_training(args.files, labels=args.labels, window=args.window, save_path=args.save)
