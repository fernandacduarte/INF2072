import numpy as np

from copy import copy
from pettingzoo import ParallelEnv
from pettingzoo.utils.env import AgentID
from gymnasium.spaces import Box, Discrete

from custom_environment.env.domain.agent import Agent
from custom_environment.env.domain.constant import Action, Observation, Reward
from custom_environment.env.domain.ghost import Ghost
from custom_environment.env.domain.pacman import PacMan
from custom_environment.utils import Graph


class PacManEnvironment(ParallelEnv):
    metadata = {
        "name": "pacman_environment_v0",
        "render_modes": ["human", "rgb_array"],
    }

    def __init__(
        self,
        global_view: np.ndarray,
        number_ghosts: int = 2
    ):
        # Petting zoo uses string identifiers for agents
        self.possible_agents = [f"ghost_{ghost}" for ghost in range(number_ghosts)]
        self.global_view =  global_view

        self.ghosts = []
        self.pacman = None

    def reset(self, seed: int = None, options: dict = None):
        self.agents = copy(self.possible_agents)
        self.ghosts = [
            Ghost(id="ghost_1", current_position=(2,2)),
            Ghost(id="ghost_2", current_position=(2,19))
        ]
        self.pacman = PacMan(id="pacman", current_position=(19,10))

        observations = {ghost.id: self._get_observation(ghost) for ghost in self.ghosts}
        infos = {ghost.id: {} for ghost in self.ghosts}

        return observations, infos

    def step(self, actions):
        """
        Takes in an action for each agent and should return the
        - observations;
        - rewards;
        - terminations;
        - truncations;
        - infos.
        They are dicts where each dict looks like {agent_1: item_1, agent_2: item_2}
        """
        observations = {}
        rewards = {}
        terminations = {}
        truncations = {}
        infos = {}

        self._execute_action(self.pacman, Action.choose_random())

        for ghost, action in actions.items():
            self._execute_action(ghost, action)

        # New insights are only obtained after all actions are done
        for ghost in self.ghosts:
            observations[ghost.id] = self._get_observation(ghost)
            rewards[ghost.id] = self._get_reward(ghost, self.pacman).value
            terminations[ghost.id] = self._get_termination(ghost)
            truncations[ghost.id] = False
            infos[ghost.id] = {}

        if any(terminations.values()) or all(truncations.values()):
            self.agents = []

        return observations, rewards, terminations, truncations, infos

    def close(self):
        pass

    def observation_space(self, agent: AgentID):
        """
        Returns the partial information available for the given agent.
        A local view of a 3x3 grid centered on the agent's position,
        with the following encoded values:
            (1) Capture;
            (2) Empty;
            (3) Ghost;
            (4) PAC-MAN;
            (5) Wall.
        """
        #low and high are the possible values in the grid encoding
        return Box(low=1, high=5, shape=(3, 3), dtype=np.uint8)

    def action_space(self, agent: AgentID):
        """
        Returns four different possible actions for a given agent:
            (1) Move right;
            (2) Move left;
            (3) Move up;
            (4) Move down.
        """
        return Discrete(4)

    def _execute_action(self, agent: Agent, action: Action):
        x, y = agent.current_position
        new_x = x
        new_y = y

        if action == Action.MOVE_RIGHT.value:
            new_x = x + 1
        elif action == Action.MOVE_LEFT.value:
            new_x = x - 1
        elif action == Action.MOVE_UP.value:
            new_y = y + 1
        else:
            new_y = y - 1

        if (
            self.global_view[new_x, new_y] == Observation.EMPTY.value
            or self.global_view[new_x, new_y] == Observation.PAC_MAN.value
        ):
            agent.current_position = (new_x, new_y)
            self.global_view[x, y] = Observation.EMPTY.value

            if self.global_view[new_x, new_y] == Observation.PAC_MAN.value:
                self.global_view[new_x, new_y] = Observation.CAPUTRED.value
            else:
                self.global_view[new_x, new_y] = Observation.GHOST.value

    def _get_observation(self, ghost: Ghost) -> np.ndarray:
        x, y = ghost.current_position
        # Boundaries are ok since they are walls and the ghosts won't be able to move there
        ghost.view = self.global_view[x - 1 : x + 2, y - 1 : y + 2]
        return ghost.view

    @staticmethod
    def _get_reward(ghost: Ghost, pacman: PacMan) -> Reward:
        if ghost.current_position == pacman.current_position:
            return Reward.GET_PACMAN

        if not np.any(ghost.view == Observation.PAC_MAN):
            ghost.last_distance = None
            return Reward.UNSEEN_PACMAN

        graph = Graph(ghost.view)
        path_pacman = graph.bfs_target_search(ghost.current_position, pacman.current_position)
        current_distance = len(path_pacman)
        last_distance = ghost.last_distance

        if not last_distance or current_distance < last_distance:
            reward = Reward.MOVE_TOWARDS_PACMAN
        else:
            reward = Reward.MOVE_AWAY_PACMAN

        ghost.last_distance = current_distance

        return reward

    @staticmethod
    def _get_termination(ghost: Ghost) -> bool:
        return np.any(ghost.view == Observation.CAPUTRED)
