import numpy as np
from dataclasses import dataclass
from custom_environment.env.domain.agent import Agent


@dataclass
class Ghost(Agent):
    view: np.ndarray | None = None  # Current NxN local observation centered on the ghost (N = GHOST_VIEW_SIZE)
    prev_position: tuple[int, int] | None = None  # Position at previous step (movement/stall checks)
    invalid_move: bool = False  # True when the latest action was blocked (wall/occupied cell)
    last_move_direction: tuple[int, int] | None = None  # Mechanical movement vector used by rendering
