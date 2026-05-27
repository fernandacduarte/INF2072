from dataclasses import dataclass


@dataclass
class Agent:
    id: str # Petting zoo uses string identifiers for agents
    current_position: tuple[int, int]