"""Example reward experiment that changes exactly one current-system weight."""

from custom_environment.env.rewards.current import (
    CurrentRewardWeightsV2,
    CurrentTeamReward,
)


class StrongerMovementReward(CurrentTeamReward):
    """Current reward with VALID_MOVE increased from 0.03 to 0.10.

    Builds on the same weights class the baseline ``CurrentTeamReward`` uses
    (``CurrentRewardWeightsV2``) so the example changes exactly one weight
    relative to the current baseline.
    """

    strategy_id = "valid-move-010"

    def __init__(self) -> None:
        super().__init__(CurrentRewardWeightsV2(valid_move=0.10))
