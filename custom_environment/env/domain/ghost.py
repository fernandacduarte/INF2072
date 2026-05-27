import numpy as np
from dataclasses import dataclass
from custom_environment.env.domain.agent import Agent


@dataclass
class Ghost(Agent):
    last_distance: int | None = None
    view: np.ndarray | None = None