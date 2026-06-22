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
_STRATEGY_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


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
