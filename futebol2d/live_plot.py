"""
Module: live_plot.py
Purpose: Live plotting of training progress (mean and std of rewards) for IQL, VDN, and QMIX across multiple seeds.
- Designed for use in multi-seed experiments.
- Plots are updated online as training progresses.
- Separate from plot.py (for post-hoc analysis).

Usage:
    from live_plot import LivePlotter
    plotter = LivePlotter(algorithms=['iql', 'vdn', 'qmix'])
    plotter.update('iql', episode, rewards_list)  # Call after each episode/seed
    plotter.update('vdn', episode, rewards_list)
    plotter.update('qmix', episode, rewards_list)
    plotter.show(block=False)  # To display the plot window

"""
import matplotlib.pyplot as plt
from matplotlib import colors as mcolors
import numpy as np
from collections import defaultdict

class LivePlotter:
    def __init__(self, algorithms):
        self.algorithms = algorithms
        self.fig, self.ax = plt.subplots()
        self.reward_history = {alg: defaultdict(list) for alg in algorithms}  # alg -> seed -> rewards
        self.lines = {}
        self.episodes = None
        self._init_plot()

    def _set_curve(self, alg, mean, std=None):
        """Set or refresh one algorithm curve and optional std shading."""
        episodes = np.arange(1, len(mean) + 1)
        self.lines[alg].set_data(episodes, mean)

        if hasattr(self, f'_fill_{alg}'):
            getattr(self, f'_fill_{alg}').remove()

        if std is not None:
            line_color = self.lines[alg].get_color()
            shade_color = self._lighten_color(line_color, amount=0.65)
            fill = self.ax.fill_between(
                episodes,
                mean - std,
                mean + std,
                color=shade_color,
                alpha=0.35,
            )
            setattr(self, f'_fill_{alg}', fill)

        self.ax.relim()
        self.ax.autoscale_view()
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

    def _lighten_color(self, color, amount=0.6):
        """Return a lighter tint of a matplotlib color by blending toward white."""
        rgb = np.array(mcolors.to_rgb(color), dtype=np.float32)
        white = np.array([1.0, 1.0, 1.0], dtype=np.float32)
        tinted = rgb + (white - rgb) * amount
        return tuple(np.clip(tinted, 0.0, 1.0))

    def _init_plot(self):
        self.ax.set_title('Multi-Seed Training: Mean ± Std Reward')
        self.ax.set_xlabel('Episode')
        self.ax.set_ylabel('Reward')
        for alg in self.algorithms:
            (line,) = self.ax.plot([], [], label=alg.upper())
            self.lines[alg] = line
        self.ax.legend()
        plt.ion()
        plt.show(block=False)

    def update(self, alg, episode, rewards, seed=0):
        """
        Update plot with new rewards for a given algorithm and seed.
        Args:
            alg (str): Algorithm name ('iql', 'vdn', 'qmix')
            episode (int): Current episode number
            rewards (list): List of rewards up to current episode for this seed
            seed (int): Seed index (default 0)
        """
        self.reward_history[alg][seed] = rewards
        # Determine max episode length so far
        max_len = max(len(r) for s in self.reward_history[alg].values() for r in [s])
        self.episodes = np.arange(1, max_len + 1)
        # Gather all seeds' rewards for this algorithm
        all_rewards = []
        for s in self.reward_history[alg].values():
            if len(s) < max_len:
                # Pad with nan for unfinished seeds
                s = list(s) + [np.nan] * (max_len - len(s))
            all_rewards.append(s)
        all_rewards = np.array(all_rewards)
        mean = np.nanmean(all_rewards, axis=0)
        std = np.nanstd(all_rewards, axis=0)
        self._set_curve(alg, mean, std)

    def set_reference_curve(self, alg, mean_rewards, std_rewards=None):
        """Display a precomputed multiseed curve for an algorithm."""
        mean = np.array(mean_rewards, dtype=np.float32)
        std = None
        if std_rewards is not None:
            std = np.array(std_rewards, dtype=np.float32)
        self._set_curve(alg, mean, std)

    def show(self, block=True):
        plt.ioff()
        plt.show(block=block)

    def close(self):
        """Close the live plot window without blocking execution."""
        plt.close(self.fig)
