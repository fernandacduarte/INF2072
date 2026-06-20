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
    # Retuned (plan-000008) for a sharper pursuit->capture gradient so IQL ghosts
    # learn to win: capture dominates, the approach signal is denser/symmetric,
    # and distractor exploration bonuses are trimmed so they no longer compete
    # with pursuit once Pacman's location is known. Signs are unchanged, so the
    # terminal-penalty smoke tests stay valid.
    GET_PACMAN                     =  30.0  # Terminal capture reward; raised so capture dominates all shaping noise
    PACMAN_TIMEOUT_WIN             = -20.0  # Penalizes the team if it fails to capture before timeout
    PACMAN_WIN_PALLETS             = -20.0  # Penalizes the team if Pacman eats every pallet and wins
    NEWLY_SPOTTED                  =   1.0  # Bonus for regaining visual contact after an unseen period
    DISTANCE_DECREASE              =   0.5  # Denser approach gradient: reward reducing min distance to the target
    DISTANCE_INCREASE              =  -0.5  # Symmetric penalty for moves that increase distance from the target
    CURRENTLY_VISIBLE              =   0.3  # Stronger incentive to keep Pacman visible and sustain tracking
    ENTER_RECENTLY_UNVISITED_TILE  =   0.05 # Trimmed exploration bonus so it does not compete with active pursuit
    REVEAL_UNSEEN_LOCAL_CELLS      =   0.03 # Trimmed local-reveal bonus to keep pursuit the dominant signal
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
