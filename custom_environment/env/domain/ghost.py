import numpy as np
from dataclasses import dataclass, field
from custom_environment.env.domain.agent import Agent


@dataclass
class Ghost(Agent):
    view: np.ndarray | None = None  # Current NxN local observation centered on the ghost (N = GHOST_VIEW_SIZE)
    prev_position: tuple[int, int] | None = None  # Position at previous step (movement/stall checks)
    invalid_move: bool = False  # True when the latest action was blocked (wall/occupied cell)
    last_move_direction: tuple[int, int] | None = None  # Last movement vector (dx, dy)
    reverse_streak: int = 0  # Number of consecutive direction reversals for anti-loop penalty
    seen_local_cells: set[tuple[int, int]] = field(default_factory=set)  # Global coordinates revealed by local FOV so far
    last_tile_visit_step: dict[tuple[int, int], int] = field(default_factory=dict)  # Last step index when each tile was visited