"""Pluggable reward strategies for the Pacman environment."""

from custom_environment.env.rewards.base import (
    GhostTransition,
    RewardContext,
    RewardResult,
    RewardStrategy,
    RewardTerm,
)
from custom_environment.env.rewards.current import (
    CaptureV0ImproveLegalMovesIncreaseTerminalRewardsReverseAction,
    CaptureV0PurePotentialShaping,
    CaptureV0Reward,
    CurrentGitTeamReward,
    CurrentTeamReward,
    CurrentWithOverlapOrSameCorridor,
)
from custom_environment.env.rewards.loader import (
    DEFAULT_REWARD_CLASS,
    load_reward_strategy,
    reward_class_path,
)

__all__ = [
    "DEFAULT_REWARD_CLASS",
    "CaptureV0ImproveLegalMovesIncreaseTerminalRewardsReverseAction",
    "CaptureV0PurePotentialShaping",
    "CaptureV0Reward",
    "CurrentGitTeamReward",
    "CurrentTeamReward",
    "CurrentWithOverlapOrSameCorridor",
    "GhostTransition",
    "RewardContext",
    "RewardResult",
    "RewardStrategy",
    "RewardTerm",
    "load_reward_strategy",
    "reward_class_path",
]
