"""Import-path loading and validation for reward classes."""

from __future__ import annotations

import importlib
import inspect
import re
from copy import deepcopy

from custom_environment.env.rewards.base import RewardStrategy


DEFAULT_REWARD_CLASS = (
    "custom_environment.env.rewards.current:CurrentTeamReward"
)
_REWARD_CLASS_BY_ID = {
    "capture_v0": "custom_environment.env.rewards.current:CaptureV0Reward",
    "capture_v0_improve_legal_moves_increase_terminal_rewards_reverse_action": (
        "custom_environment.env.rewards.current:CaptureV0ImproveLegalMovesIncreaseTerminalRewardsReverseAction"
    ),
    "capture_v0_improve_strategies": (
        "custom_environment.env.rewards.current:CaptureV0ImproveStrategies"
    ),
    "capture_v0_pure_potential_shaping": (
        "custom_environment.env.rewards.current:CaptureV0PurePotentialShaping"
    ),
    "capture_v0_sparse_control": (
        "custom_environment.env.rewards.current:CaptureV0SparseControl"
    ),
    "capture_merge_potential_shaping": (
        "custom_environment.env.rewards.current:CaptureMergePotentialShaping"
    ),
    "capture_merge": (
        "custom_environment.env.rewards.current:CaptureMerge"
    ),
    "capture_v0_pure_potential_shaping_pellets": (
        "custom_environment.env.rewards.current:CaptureV0PurePotentialShapingPellets"
    ),
    "capture_v0_pure_potential_shaping_pellets_fast_capture_bonus": (
        "custom_environment.env.rewards.current:CaptureV0PurePotentialShapingPelletsFastCaptureBonus"
    ),
    "current_git": "custom_environment.env.rewards.current:CurrentGitTeamReward",
    "current": "custom_environment.env.rewards.current:CurrentTeamReward",
    "current_with_overlap_or_same_corridor": (
        "custom_environment.env.rewards.current:CurrentWithOverlapOrSameCorridor"
    ),
}
_STRATEGY_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def reward_class_from_id(strategy_id: str) -> str:
    key = str(strategy_id).strip()
    if not key:
        raise ValueError("Reward id cannot be empty.")
    class_path = _REWARD_CLASS_BY_ID.get(key)
    if class_path is None:
        known = ", ".join(sorted(_REWARD_CLASS_BY_ID.keys()))
        raise ValueError(
            f"Unknown reward id {key!r}. Known ids: {known}. "
            "Use --reward-class/--reward-classes to pass a custom module:Class path."
        )
    return class_path


def reward_class_path(strategy: RewardStrategy) -> str:
    cls = type(strategy)
    return f"{cls.__module__}:{cls.__qualname__}"


def _validate_strategy(strategy: RewardStrategy, class_path: str) -> RewardStrategy:
    strategy_id = getattr(strategy, "strategy_id", "")
    if not isinstance(strategy_id, str) or not _STRATEGY_ID_RE.fullmatch(strategy_id):
        raise ValueError(
            f"Reward class {class_path!r} must define a strategy_id matching "
            "[a-z0-9][a-z0-9_-]*."
        )
    return strategy


def load_reward_strategy(
    reward: str | RewardStrategy | None = None,
) -> RewardStrategy:
    """Create/validate a strategy from ``module:Class`` or accept an instance."""

    if isinstance(reward, RewardStrategy):
        class_path = reward_class_path(reward)
        try:
            owned_strategy = deepcopy(reward)
        except Exception as exc:
            raise TypeError(
                f"Reward instance {class_path!r} must be deepcopy-compatible so each "
                "environment owns independent episode state."
            ) from exc
        return _validate_strategy(owned_strategy, class_path)

    class_path = DEFAULT_REWARD_CLASS if reward is None else str(reward).strip()
    if class_path.count(":") != 1:
        raise ValueError(
            f"Invalid reward class {class_path!r}; expected 'module:Class'."
        )
    module_name, class_name = class_path.split(":", 1)
    if not module_name or not class_name:
        raise ValueError(
            f"Invalid reward class {class_path!r}; expected 'module:Class'."
        )

    module = importlib.import_module(module_name)
    target = module
    for part in class_name.split("."):
        target = getattr(target, part)
    if not inspect.isclass(target) or not issubclass(target, RewardStrategy):
        raise TypeError(f"Reward class {class_path!r} must subclass RewardStrategy.")
    try:
        strategy = target()
    except TypeError as exc:
        raise TypeError(
            f"Reward class {class_path!r} must be constructible without arguments."
        ) from exc
    return _validate_strategy(strategy, class_path)
