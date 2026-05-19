import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def load_training_csv(path):
    episodes = []
    rewards = []
    epsilons = []
    with open(path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            episodes.append(int(row["episode"]))
            rewards.append(float(row["reward"]))
            epsilons.append(float(row["epsilon"]))
    return np.array(episodes), np.array(rewards), np.array(epsilons)


def moving_average(values, window=20):
    if window <= 1:
        return values
    return np.convolve(values, np.ones(window) / window, mode="valid")


def plot_training(files, labels=None, window=20, save_path=None):
    if labels is None:
        labels = [Path(f).stem for f in files]
    plt.figure(figsize=(10, 5))
    for path, label in zip(files, labels):
        episodes, rewards, _ = load_training_csv(path)
        avg_rewards = moving_average(rewards, window)
        plt.plot(episodes[: len(avg_rewards)], avg_rewards, label=label)
    plt.xlabel("Episode")
    plt.ylabel(f"Reward (moving average, window={window})")
    plt.title("Training reward comparison")
    plt.legend()
    plt.grid(True)
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Saved figure to {save_path}")
    plt.show()

    plt.figure(figsize=(10, 4))
    for path, label in zip(files, labels):
        episodes, _, epsilons = load_training_csv(path)
        plt.plot(episodes, epsilons, label=label)
    plt.xlabel("Episode")
    plt.ylabel("Epsilon")
    plt.title("Exploration schedule")
    plt.legend()
    plt.grid(True)
    if save_path:
        save_path_eps = Path(save_path).with_name(Path(save_path).stem + "_epsilon" + Path(save_path).suffix)
        plt.savefig(save_path_eps, dpi=150, bbox_inches="tight")
        print(f"Saved epsilon figure to {save_path_eps}")
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot training results from saved CSV files")
    parser.add_argument("files", nargs="+", help="One or more training CSV files to compare")
    parser.add_argument("--labels", nargs="+", default=None, help="Optional labels for each file")
    parser.add_argument("--window", type=int, default=20, help="Moving average window for reward smoothing")
    parser.add_argument("--save", default=None, help="Optional path to save the reward plot image")
    args = parser.parse_args()

    if args.labels and len(args.labels) != len(args.files):
        raise ValueError("Number of labels must match number of files")

    plot_training(args.files, labels=args.labels, window=args.window, save_path=args.save)
