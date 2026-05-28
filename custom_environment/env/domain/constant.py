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
    GET_PACMAN = 50
    MOVE_TOWARDS_PACMAN = 10
    MOVE_AWAY_PACMAN = -10
    PACMAN_GOT_COIN = -5
    UNSEEN_PACMAN = -5