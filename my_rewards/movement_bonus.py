"""Example reward experiment that changes exactly one current-system weight."""

from custom_environment.env.rewards.current import (
    CurrentRewardWeights,
    CurrentTeamReward,
)


class StrongerMovementReward(CurrentTeamReward):
    """Current reward with VALID_MOVE increased from 0.01 to 0.10."""

    strategy_id = "valid-move-010"

    def __init__(self) -> None:
        super().__init__(CurrentRewardWeights(valid_move=0.10))
