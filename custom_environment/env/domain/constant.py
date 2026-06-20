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

class Reward(Enum):
    GET_PACMAN                     =  20.0  # Terminal reward to encourage successful Pacman capture
    PACMAN_TIMEOUT_WIN             = -20.0  # Penalizes the team if it fails to capture before timeout
    PACMAN_WIN_PALLETS             = -20.0  # Penalizes the team if Pacman eats every pallet and wins
    NEWLY_SPOTTED                  =   1.0  # Bonus for regaining visual contact after an unseen period
    DISTANCE_DECREASE              =   0.3  # Encourages reducing the team's minimum distance to the known target
    DISTANCE_INCREASE              =  -0.3  # Discourages moves that increase distance from the target
    CURRENTLY_VISIBLE              =   0.2  # Rewards keeping Pacman visible to sustain tracking
    ENTER_RECENTLY_UNVISITED_TILE  =   0.08 # Encourages spatial exploration outside recently visited paths
    REVEAL_UNSEEN_LOCAL_CELLS      =   0.05 # Encourages revealing new cells in local field of view
    VALID_MOVE                     =   0.01 # Small bonus to favor valid movement and avoid inertia
    INVALID_MOVE                   =  -0.08 # Penalizes blocked movement attempts (wall/occupied cell)
    STAY_STILL                     =  -0.03 # Penalizes staying still to reduce stagnation
    REPEATED_DIRECTION_REVERSAL    =  -0.02 # Penalizes repeated reversals to prevent ping-pong loops
    GHOST_OVERLAP_OR_SAME_CORRIDOR =  -0.05 # Discourages overlap and redundant corridor following
    TIMESTEP_PENALTY               =  -0.01 # Per-step cost to encourage faster captures


# Defense-first safety target for the PacmanPolicy: the BFS distance (in cells)
# Pacman tries to keep between itself and the nearest ghost. Survival is the
# primary objective — Pacman only pursues pellets among moves that preserve at
# least this much clearance; pellet collection is strictly secondary. The value
# also caps the safety score, so once Pacman is this far from every ghost it
# stops running and starts eating. See plan-000007 / research-000006.
PACMAN_SAFE_DISTANCE = 5
