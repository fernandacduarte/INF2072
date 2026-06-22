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
    # Retuned (plan-000008) for a sharper pursuit->capture gradient so IQL ghosts
    # learn to win: capture dominates, the approach signal is denser/symmetric,
    # and distractor exploration bonuses are trimmed so they no longer compete
    # with pursuit once Pacman's location is known. Signs are unchanged, so the
    # terminal-penalty smoke tests stay valid.
    GET_PACMAN = _CURRENT_REWARD_WEIGHTS.get_pacman  # Terminal capture reward; raised so capture dominates all shaping noise
    PACMAN_TIMEOUT_WIN = _CURRENT_REWARD_WEIGHTS.pacman_timeout_win  # Penalizes the team if it fails to capture before timeout
    PACMAN_WIN_PALLETS = _CURRENT_REWARD_WEIGHTS.pacman_win_pellets  # Penalizes the team if Pacman eats every pallet and wins
    NEWLY_SPOTTED = _CURRENT_REWARD_WEIGHTS.newly_spotted  # Bonus for regaining visual contact after an unseen period
    # DISTANCE_DECREASE/INCREASE are superseded by potential-based shaping
    # (POTENTIAL_SHAPING_ALPHA, plan-000021): the old terms fired against a STALE
    # last-sighting position and created a stay-still trap (research-000012 RC1).
    # Retained only for backward compatibility; no longer referenced by the reward.
    DISTANCE_DECREASE = 0.5  # DEPRECATED (superseded by potential shaping)
    DISTANCE_INCREASE = -0.5  # DEPRECATED (superseded by potential shaping)
    CURRENTLY_VISIBLE = _CURRENT_REWARD_WEIGHTS.currently_visible  # Stronger incentive to keep Pacman visible and sustain tracking
    ENTER_RECENTLY_UNVISITED_TILE = _CURRENT_REWARD_WEIGHTS.enter_recently_unvisited_tile  # Raised (plan-000021/R3) so EV(move) > EV(stay) where the potential gradient is flat
    REVEAL_UNSEEN_LOCAL_CELLS = _CURRENT_REWARD_WEIGHTS.reveal_unseen_local_cells  # Trimmed local-reveal bonus to keep pursuit the dominant signal
    VALID_MOVE = _CURRENT_REWARD_WEIGHTS.valid_move  # Raised (plan-000021/R3): positive anti-freeze incentive to always favor movement
    INVALID_MOVE = _CURRENT_REWARD_WEIGHTS.invalid_move  # Penalizes blocked movement attempts (wall/occupied cell)
    STAY_STILL = _CURRENT_REWARD_WEIGHTS.stay_still  # Penalizes staying still to reduce stagnation
    REPEATED_DIRECTION_REVERSAL = _CURRENT_REWARD_WEIGHTS.repeated_direction_reversal  # Penalizes repeated reversals to prevent ping-pong loops
    GHOST_OVERLAP_OR_SAME_CORRIDOR = _CURRENT_REWARD_WEIGHTS.overlap_or_same_corridor  # Discourages overlap and redundant corridor following
    TIMESTEP_PENALTY = _CURRENT_REWARD_WEIGHTS.timestep  # Per-step cost to encourage faster captures


# Potential-based reward-shaping coefficient (plan-000021 / research-000012 R1).
# Defines the team-reward potential F(s) = -POTENTIAL_SHAPING_ALPHA * min_bfs_distance
# from the ghosts to the TRUE Pacman position; the per-step shaping reward is the
# policy-invariant difference F(s') - F(s) (Ng, Harada & Russell 1999). At 0.5 a
# one-cell change in min distance yields +/-0.5, matching the magnitude of the
# former DISTANCE_DECREASE/INCREASE terms it replaces.
POTENTIAL_SHAPING_ALPHA = _CURRENT_REWARD_WEIGHTS.potential_shaping_alpha

# Defense-first safety target for the PacmanPolicy: the BFS distance (in cells)
# Pacman tries to keep between itself and the nearest ghost. Survival is the
# primary objective — Pacman only pursues pellets among moves that preserve at
# least this much clearance; pellet collection is strictly secondary. The value
# also caps the safety score, so once Pacman is this far from every ghost it
# stops running and starts eating. See plan-000007 / research-000006.
PACMAN_SAFE_DISTANCE = 3
