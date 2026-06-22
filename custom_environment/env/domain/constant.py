import random
from enum import Enum, auto


class Observation(Enum):
    CAPUTRED = auto()
    EMPTY = auto()
    GHOST = auto()
    PAC_MAN = auto()
    WALL = auto()

class Action(Enum):
    MOVE_RIGHT = auto()
    MOVE_LEFT = auto()
    MOVE_UP = auto()
    MOVE_DOWN = auto()

    @classmethod
    def choose_random(cls) -> 'Action':
        """Get a random action"""
        return random.choice(list(cls))


# Deprecated compatibility view for older experiments and teammates' branches.
# New reward implementations must keep their values in their RewardStrategy class;
# the environment itself no longer imports or evaluates this enum.
from custom_environment.env.rewards.current import CurrentRewardWeights

_CURRENT_REWARD_WEIGHTS = CurrentRewardWeights()


class Reward(Enum):
    GET_PACMAN = _CURRENT_REWARD_WEIGHTS.get_pacman
    PACMAN_TIMEOUT_WIN = _CURRENT_REWARD_WEIGHTS.pacman_timeout_win
    PACMAN_WIN_PALLETS = _CURRENT_REWARD_WEIGHTS.pacman_win_pellets
    NEWLY_SPOTTED = _CURRENT_REWARD_WEIGHTS.newly_spotted
    DISTANCE_DECREASE = 0.5  # Deprecated; retained for import compatibility.
    DISTANCE_INCREASE = -0.5  # Deprecated; retained for import compatibility.
    CURRENTLY_VISIBLE = _CURRENT_REWARD_WEIGHTS.currently_visible
    ENTER_RECENTLY_UNVISITED_TILE = _CURRENT_REWARD_WEIGHTS.enter_recently_unvisited_tile
    REVEAL_UNSEEN_LOCAL_CELLS = _CURRENT_REWARD_WEIGHTS.reveal_unseen_local_cells
    VALID_MOVE = _CURRENT_REWARD_WEIGHTS.valid_move
    INVALID_MOVE = _CURRENT_REWARD_WEIGHTS.invalid_move
    STAY_STILL = _CURRENT_REWARD_WEIGHTS.stay_still
    REPEATED_DIRECTION_REVERSAL = _CURRENT_REWARD_WEIGHTS.repeated_direction_reversal
    GHOST_OVERLAP_OR_SAME_CORRIDOR = _CURRENT_REWARD_WEIGHTS.overlap_or_same_corridor
    TIMESTEP_PENALTY = _CURRENT_REWARD_WEIGHTS.timestep


POTENTIAL_SHAPING_ALPHA = _CURRENT_REWARD_WEIGHTS.potential_shaping_alpha

# Defense-first safety target for the PacmanPolicy: the BFS distance (in cells)
# Pacman tries to keep between itself and the nearest ghost. Survival is the
# primary objective — Pacman only pursues pellets among moves that preserve at
# least this much clearance; pellet collection is strictly secondary. The value
# also caps the safety score, so once Pacman is this far from every ghost it
# stops running and starts eating. See plan-000007 / research-000006.
PACMAN_SAFE_DISTANCE = 3
