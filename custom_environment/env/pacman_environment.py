"""Pacman multi-agent environment implementation.

This file defines the PettingZoo `ParallelEnv` where ghosts are trainable agents
and Pacman is controlled by internal random movement.
"""

# functools: for lru_cache decorator (caches space methods)
import functools

# numpy: for array operations (grid, observations, rewards)
import numpy as np

# copy: for deep copying possible_agents list on reset
from copy import copy

# ParallelEnv: PettingZoo base class for parallel (simultaneous) agent stepping
from pettingzoo import ParallelEnv

# AgentID: type alias for agent string IDs in PettingZoo
from pettingzoo.utils.env import AgentID

# Box, Discrete: Gymnasium spaces for observation/action definitions
from gymnasium.spaces import Box, Discrete

# Agent: base class for all agents (ghosts, pacman)
from custom_environment.env.domain.agent import Agent

# Action, Observation, Reward: enums for actions, cell types, and reward values
from custom_environment.env.domain.constant import Action, Observation, Reward

# Ghost: class for ghost agents
from custom_environment.env.domain.ghost import Ghost

# PacMan: class for pacman agent
from custom_environment.env.domain.pacman import PacMan

from collections import deque


# Main environment class following PettingZoo parallel interface.
class PacManEnvironment(ParallelEnv):  # Main environment class
    # Metadata advertised by the environment.
    metadata = {
        # Canonical name for the environment (used by PettingZoo)
        "name": "pacman_environment_v0",
        # Supported render modes (not used, but required by API)
        "render_modes": ["human", "rgb_array"],
    }

    # Constructor receives the world grid and number of ghost agents.
    def __init__(
        self,  # The environment instance
        global_view: np.ndarray,  # The grid (walls, empty, ghosts, pacman)
        number_ghosts: int = 2  # Number of ghost agents
    ):
        # List of agent IDs (ghost_1, ghost_2, ...)
        self.possible_agents = [f"ghost_{ghost+1}" for ghost in range(number_ghosts)]
        # Keep an immutable base map and reset from it every episode.
        self._base_grid = np.array(global_view, copy=True)
        self.global_view = np.array(global_view, copy=True)

        # List of Ghost objects (populated on reset)
        self.ghosts = []
        # PacMan object (populated on reset)
        self.pacman = None

        # Episode-level controls and shared team memory.
        self.max_steps = 200
        self.recently_unvisited_window = 10
        self.step_count = 0
        self.last_pacman_sighting_position = None
        self.last_pacman_sighting_step = None
        self.last_any_pacman_visible = False
        self.last_target_min_distance = None
        self.last_team_reward_breakdown = {}
        self.newly_spotted_min_unseen_steps = 6
        self.unseen_steps = 0

    # Reset environment and return initial per-agent observation/info dicts.
    def reset(self, seed: int = None, options: dict = None):
        # Copy agent list for PettingZoo's active agent tracking
        self.agents = copy(self.possible_agents)
        # Restore clean grid state to avoid carrying over mutated cells across episodes.
        self.global_view = np.array(self._base_grid, copy=True)

        # Reset shared episode memory.
        self.step_count = 0
        self.last_pacman_sighting_position = None
        self.last_pacman_sighting_step = None
        self.last_any_pacman_visible = False
        self.last_target_min_distance = None
        self.last_team_reward_breakdown = {}
        self.unseen_steps = self.newly_spotted_min_unseen_steps

        # --- Spawn ghosts at fixed positions (could be parameterized) ---
        self.ghosts = [
            Ghost(id="ghost_1", current_position=(1, 1)),
            Ghost(id="ghost_2", current_position=(1, 18))
        ]
        # Reset per-ghost exploration and movement memory at episode start.
        for ghost in self.ghosts:
            ghost.last_tile_visit_step = {ghost.current_position: 0}
        # Place ghosts on the grid
        for ghost in self.ghosts:
            x, y = ghost.current_position  # Unpack position
            self.global_view[x, y] = Observation.GHOST.value  # Mark as ghost

        # --- Spawn Pacman at fixed position (could be parameterized) ---
        self.pacman = PacMan(id="pacman", current_position=(18, 9))  # Bottom center
        self.global_view[*self.pacman.current_position] = Observation.PAC_MAN.value

        # --- Build initial observations and info dicts for all ghosts ---
        observations = {ghost.id: self._get_observation(ghost) for ghost in self.ghosts}
        for ghost in self.ghosts:
            self._update_seen_local_cells(ghost)
        # Build empty info dict for each ghost.
        infos = {ghost.id: {} for ghost in self.ghosts}

        # Return observations and infos as required by PettingZoo reset API.
        return observations, infos

    # Execute one simultaneous environment step.
    def step(self, actions):
        """Step all entities and return PettingZoo parallel outputs."""
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

        # Move Pacman first using internal random policy.
        self._execute_action(self.pacman, Action.choose_random())

        # Then apply each ghost action received from the learning policy.
        # Use ghost ids instead of dict iteration order to avoid agent-action mismatches.
        for ghost in self.ghosts:
            if ghost.id not in actions:
                raise KeyError(f"Missing action for ghost '{ghost.id}'. Received keys: {list(actions.keys())}")
            action = self._decode_action(actions[ghost.id])
            self._execute_action(ghost, action)

        # One environment transition completed.
        self.step_count += 1

        # Update local observation for all ghosts after movement.
        for ghost in self.ghosts:
            observations[ghost.id] = self._get_observation(ghost)

        capture_happened = self._is_capture_state()
        timeout_happened = (self.step_count >= self.max_steps) and (not capture_happened)

        team_reward = self._compute_team_reward(capture_happened)
        if timeout_happened:
            team_reward += float(Reward.PACMAN_TIMEOUT_WIN.value)

        # Shared reward is broadcast to every ghost.
        for ghost in self.ghosts:
            rewards[ghost.id] = float(team_reward)
            terminations[ghost.id] = bool(capture_happened)
            truncations[ghost.id] = bool(timeout_happened)
            infos[ghost.id] = {
                "last_pacman_sighting_position": self.last_pacman_sighting_position,
                "last_pacman_sighting_step": self.last_pacman_sighting_step,
                "reward_breakdown": dict(self.last_team_reward_breakdown),
            }

        # If episode ended, clear active agents list according to PettingZoo convention.
        if any(terminations.values()) or all(truncations.values()):
            self.agents = []

        # Return full transition tuple expected by ParallelEnv step API.
        return observations, rewards, terminations, truncations, infos

    # Close hook (no external resources to release currently).
    def close(self):
        # Intentionally empty.
        pass

    # Cache observation spaces because they are static by agent ID.
    @functools.lru_cache(maxsize=None)
    # Return observation space for one agent.
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
        # Encoded values span [1, 5], with uint8 storage.
        return Box(low=1, high=5, shape=(3, 3), dtype=np.uint8)

    # Cache action spaces because they are static by agent ID.
    @functools.lru_cache(maxsize=None)
    # Return action space for one agent.
    def action_space(self, agent: AgentID):
        """
        Returns four different possible actions for a given agent:
            (1) Move right;
            (2) Move left;
            (3) Move up;
            (4) Move down.
        """
        return Discrete(4)

    # Apply a single movement action to either a ghost or Pacman.
    def _execute_action(self, agent: Agent, action: Action):
        # Save previous position for anti-stall checks and transition tracking.
        agent.prev_position = getattr(agent, 'current_position', None)
        if isinstance(agent, Ghost):
            agent.invalid_move = False
        # Require Action enum for all calls (no int conversion inside).
        action_value = action.value

        # Read current agent position.
        x, y = agent.current_position
        # Initialize next-x with current x.
        new_x = x
        # Initialize next-y with current y.
        new_y = y

        # Movement mapping on matrix coordinates: x=row, y=column.
        if action_value == Action.MOVE_RIGHT.value:
            new_y = y + 1
        elif action_value == Action.MOVE_LEFT.value:
            new_y = y - 1
        elif action_value == Action.MOVE_UP.value:
            new_x = x - 1
        # Remaining action is treated as "move down".
        else:
            new_x = x + 1

        # Read the cell content at the proposed destination.
        target_cell = self.global_view[new_x, new_y]

        # Ghost movement rules.
        if isinstance(agent, Ghost):
            can_move = target_cell in (
                Observation.EMPTY.value,
                Observation.PAC_MAN.value,
            )
        # Pacman movement rules.
        elif isinstance(agent, PacMan):
            can_move = target_cell in (
                Observation.EMPTY.value,
                Observation.GHOST.value,
            )
        else:
            raise TypeError(f"Unsupported agent type in _execute_action: {type(agent)}")

        if can_move:
            agent.current_position = (new_x, new_y)
            # Clear old position on the grid.
            self.global_view[x, y] = Observation.EMPTY.value

            # Ghost reached Pacman, mark capture.
            if isinstance(agent, Ghost) and target_cell == Observation.PAC_MAN.value:
                self.global_view[new_x, new_y] = Observation.CAPUTRED.value
            elif isinstance(agent, PacMan) and target_cell == Observation.GHOST.value:
                self.global_view[new_x, new_y] = Observation.CAPUTRED.value
            else:
                if isinstance(agent, Ghost):
                    self.global_view[new_x, new_y] = Observation.GHOST.value
                elif isinstance(agent, PacMan):
                    self.global_view[new_x, new_y] = Observation.PAC_MAN.value
                else:
                    raise TypeError(f"Unsupported agent type in _execute_action: {type(agent)}")
        else:
            if isinstance(agent, Ghost):
                agent.invalid_move = True
            return

    # Normalize action tokens to Action enum.
    @staticmethod
    def _decode_action(action) -> Action:
        if isinstance(action, Action):
            return action

        action_int = int(action)
        # Prefer 0-based index decoding for policy outputs from Discrete(4).
        if 0 <= action_int < len(Action):
            return list(Action)[action_int]
        if any(action_int == item.value for item in Action):
            return Action(action_int)
        raise ValueError(f"Invalid action token for ghost policy: {action}")

    # Compute 3x3 local observation for one ghost.
    def _get_observation(self, ghost: Ghost) -> np.ndarray:
        # Read ghost position.
        x, y = ghost.current_position
        # Slice 3x3 centered around ghost (walls on borders prevent out-of-bounds).
        ghost.view = self.global_view[(x-1):(x+2), (y-1):(y+2)]
        # Return cached local view.
        return ghost.view

    def _compute_team_reward(self, capture_happened: bool) -> float:
        reward = float(Reward.TIMESTEP_PENALTY.value)
        breakdown = {"timestep": float(Reward.TIMESTEP_PENALTY.value)}

        def add_term(name: str, value: float):
            nonlocal reward
            reward += value
            breakdown[name] = breakdown.get(name, 0.0) + float(value)

        if capture_happened:
            add_term("GET_PACMAN", float(Reward.GET_PACMAN.value))

        any_visible, seen_positions = self._collect_visible_pacman_positions()
        if any_visible:
            current_sighting = seen_positions[0]
            if (not self.last_any_pacman_visible) and (self.unseen_steps >= self.newly_spotted_min_unseen_steps):
                add_term("newly_spotted", float(Reward.NEWLY_SPOTTED.value))
            add_term("currently_visible", float(Reward.CURRENTLY_VISIBLE.value))
            self.last_pacman_sighting_position = current_sighting
            self.last_pacman_sighting_step = self.step_count
            self.unseen_steps = 0
        else:
            self.unseen_steps += 1

        target_position = self.last_pacman_sighting_position
        if target_position is not None:
            min_distance = self._compute_min_distance_to_target(target_position)
            if min_distance is not None and self.last_target_min_distance is not None:
                if min_distance < self.last_target_min_distance:
                    add_term("distance_decrease", float(Reward.DISTANCE_DECREASE.value))
                elif min_distance > self.last_target_min_distance:
                    add_term("distance_increase", float(Reward.DISTANCE_INCREASE.value))
            self.last_target_min_distance = min_distance

        for ghost in self.ghosts:
            moved = (ghost.prev_position is not None and ghost.prev_position != ghost.current_position)
            if not moved:
                if ghost.invalid_move:
                    add_term("invalid_move", float(Reward.INVALID_MOVE.value))
                else:
                    add_term("stay_still", float(Reward.STAY_STILL.value))

            if moved:
                add_term("valid_move", float(Reward.VALID_MOVE.value))
                if self._is_recently_unvisited_tile(ghost):
                    add_term("recently_unvisited_tile", float(Reward.ENTER_RECENTLY_UNVISITED_TILE.value))
                self._update_movement_history(ghost)
                if ghost.reverse_streak >= 2:
                    reversal_factor = min(ghost.reverse_streak - 1, 4)
                    add_term(
                        "repeated_direction_reversal",
                        float(Reward.REPEATED_DIRECTION_REVERSAL.value) * float(reversal_factor),
                    )

            if self._update_seen_local_cells(ghost):
                add_term("reveal_unseen_local_cells", float(Reward.REVEAL_UNSEEN_LOCAL_CELLS.value))

        if self._has_overlap_or_same_corridor_following():
            add_term("overlap_or_same_corridor", float(Reward.GHOST_OVERLAP_OR_SAME_CORRIDOR.value))

        self.last_any_pacman_visible = any_visible
        self.last_team_reward_breakdown = breakdown
        return reward

    def _is_capture_state(self) -> bool:
        if np.any(self.global_view == Observation.CAPUTRED.value):
            return True
        return any(ghost.current_position == self.pacman.current_position for ghost in self.ghosts)

    def _collect_visible_pacman_positions(self) -> tuple[bool, list[tuple[int, int]]]:
        seen_positions = []
        for ghost in self.ghosts:
            pacman_local_positions = np.argwhere(ghost.view == Observation.PAC_MAN.value)
            if pacman_local_positions.size == 0:
                continue
            local_x, local_y = (int(pacman_local_positions[0][0]), int(pacman_local_positions[0][1]))
            ghost_x, ghost_y = ghost.current_position
            global_pos = (ghost_x + (local_x - 1), ghost_y + (local_y - 1))
            seen_positions.append(global_pos)
        return len(seen_positions) > 0, seen_positions

    def _compute_min_distance_to_target(self, target_position: tuple[int, int]) -> int | None:
        distances = []
        for ghost in self.ghosts:
            dist = self._bfs_distance(ghost.current_position, target_position)
            if dist is not None:
                distances.append(dist)
        if not distances:
            return None
        return min(distances)

    def _bfs_distance(self, start: tuple[int, int], goal: tuple[int, int]) -> int | None:
        if start == goal:
            return 0

        rows, cols = self.global_view.shape
        queue = deque([(start, 0)])
        visited = {start}

        while queue:
            (x, y), dist = queue.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < rows and 0 <= ny < cols):
                    continue
                if (nx, ny) in visited:
                    continue
                if self.global_view[nx, ny] == Observation.WALL.value:
                    continue
                if (nx, ny) == goal:
                    return dist + 1
                visited.add((nx, ny))
                queue.append(((nx, ny), dist + 1))

        return None

    def _is_recently_unvisited_tile(self, ghost: Ghost) -> bool:
        last_visit_step = ghost.last_tile_visit_step.get(ghost.current_position)
        is_recently_unvisited = (
            last_visit_step is None
            or (self.step_count - int(last_visit_step)) > self.recently_unvisited_window
        )
        ghost.last_tile_visit_step[ghost.current_position] = self.step_count
        return is_recently_unvisited

    @staticmethod
    def _get_direction(previous_position: tuple[int, int], current_position: tuple[int, int]) -> tuple[int, int]:
        return (
            current_position[0] - previous_position[0],
            current_position[1] - previous_position[1],
        )

    def _update_movement_history(self, ghost: Ghost):
        move_direction = self._get_direction(ghost.prev_position, ghost.current_position)
        last_move_direction = ghost.last_move_direction
        if last_move_direction is not None and move_direction == (-last_move_direction[0], -last_move_direction[1]):
            ghost.reverse_streak += 1
        else:
            ghost.reverse_streak = 0
        ghost.last_move_direction = move_direction

    def _update_seen_local_cells(self, ghost: Ghost) -> bool:
        revealed_new = False
        x, y = ghost.current_position
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                gx, gy = x + dx, y + dy
                if (gx, gy) not in ghost.seen_local_cells:
                    ghost.seen_local_cells.add((gx, gy))
                    revealed_new = True
        return revealed_new

    def _has_overlap_or_same_corridor_following(self) -> bool:
        # Penalize exact overlap.
        positions = [ghost.current_position for ghost in self.ghosts]
        if len(set(positions)) < len(positions):
            return True

        # Penalize ghosts that move close in same row/column with same direction.
        for i in range(len(self.ghosts)):
            for j in range(i + 1, len(self.ghosts)):
                ghost_a = self.ghosts[i]
                ghost_b = self.ghosts[j]
                if ghost_a.prev_position is None or ghost_b.prev_position is None:
                    continue
                if ghost_a.current_position == ghost_a.prev_position:
                    continue
                if ghost_b.current_position == ghost_b.prev_position:
                    continue

                dir_a = self._get_direction(ghost_a.prev_position, ghost_a.current_position)
                dir_b = self._get_direction(ghost_b.prev_position, ghost_b.current_position)
                if dir_a != dir_b:
                    continue

                same_row = ghost_a.current_position[0] == ghost_b.current_position[0]
                same_col = ghost_a.current_position[1] == ghost_b.current_position[1]
                if not (same_row or same_col):
                    continue

                distance = abs(ghost_a.current_position[0] - ghost_b.current_position[0]) + abs(ghost_a.current_position[1] - ghost_b.current_position[1])
                if distance <= 2:
                    return True

        return False

    # Termination is handled centrally in step() to support capture and timeout.
