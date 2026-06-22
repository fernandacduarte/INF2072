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

# Action and Observation enums for actions and cell types.
from custom_environment.env.domain.constant import (
    Action,
    Observation,
)

# Ghost: class for ghost agents
from custom_environment.env.domain.ghost import Ghost

# PacMan: class for pacman agent
from custom_environment.env.domain.pacman import PacMan

# PacmanPolicy: deterministic safety-aware Pacman controller (replaces random)
from custom_environment.env.domain.pacman_policy import PacmanPolicy

# MazeSpec: map-authored layout (grid + spawns + pellet mask); spec_from_grid: back-compat wrapper
from custom_environment.utils import MazeSpec, spec_from_grid

from custom_environment.env.rewards import (
    GhostTransition,
    RewardContext,
    RewardStrategy,
    load_reward_strategy,
    reward_class_path,
)

from collections import deque


# 3 -> 3x3, 5 -> 5x5, 7 -> 7x7. Change this single value to resize the ghosts'
# local observation for all trainings. Off-grid cells (near the map border) are
# padded with WALL, so the maze never needs to change when this value changes.
GHOST_VIEW_SIZE = 5


# Main environment class following PettingZoo parallel interface.
class PacManEnvironment(ParallelEnv):  # Main environment class
    # Metadata advertised by the environment.
    metadata = {
        # Canonical name for the environment (used by PettingZoo)
        "name": "pacman_environment_v0",
        # Supported render modes.
        "render_modes": ["human", "rgb_array"],
    }

    # Constructor receives the world grid and number of ghost agents.
    def __init__(
        self,  # The environment instance
        global_view,  # A MazeSpec, or a raw grid array (back-compat)
        number_ghosts: int = 2,  # Deprecated: ghost count now comes from the map's spawns
        render_mode: str | None = None,  # Optional visual render mode
        tile_size: int = 28,  # Tile size in pixels for Pygame rendering
        fps: int = 12,  # Target frames per second for human rendering
        show_observations: bool = True,  # Whether to tint each ghost's local view in visual renders
        ghost_view_size: int | None = None,  # Optional override for local observation size
        reward_strategy: str | RewardStrategy | None = None,
    ):
        if render_mode is not None and render_mode not in self.metadata["render_modes"]:
            raise ValueError(
                f"Unsupported render_mode={render_mode!r}. "
                f"Expected one of {self.metadata['render_modes']} or None."
            )

        # Ghost local field-of-view geometry (see GHOST_VIEW_SIZE at module top).
        view_size = GHOST_VIEW_SIZE if ghost_view_size is None else int(ghost_view_size)
        if view_size < 1 or view_size % 2 == 0:
            raise ValueError(
                f"ghost_view_size must be a positive odd integer, got {view_size}"
            )
        self.view_size = view_size
        self.view_radius = view_size // 2

        # Accept a MazeSpec, or wrap a raw grid array with legacy spawns (back-compat).
        spec = global_view if isinstance(global_view, MazeSpec) else spec_from_grid(global_view)

        # Map-authored spawns and cosmetic pellet layer.
        self.ghost_spawns = [tuple(pos) for pos in spec.ghost_spawns]
        self.pacman_spawn = tuple(spec.pacman_spawn)
        self._base_pellet_mask = np.array(spec.pellet_mask, copy=True)

        # Agent IDs are derived from the number of ghost spawns declared in the map.
        self.possible_agents = [f"ghost_{i+1}" for i in range(len(self.ghost_spawns))]
        # Keep an immutable base map and reset from it every episode.
        self._base_grid = np.array(spec.grid, copy=True)
        self.global_view = np.array(spec.grid, copy=True)
        self._wall_map = (self._base_grid == Observation.WALL.value).astype(np.float32)
        self._reward_wall_positions = frozenset(
            (int(row), int(col))
            for row, col in np.argwhere(self._wall_map == 1.0)
        )

        # List of Ghost objects (populated on reset)
        self.ghosts = []
        # PacMan object (populated on reset)
        self.pacman = None

        # Episode-level controls and shared observation memory.
        self.max_steps = 200
        self.step_count = 0
        self.last_pacman_sighting_position = None
        self.last_pacman_sighting_step = None
        self.last_team_reward_breakdown = {}
        self.last_reward_category_totals = {"shaping": 0.0, "terminal": 0.0}
        self.last_reward_context = None
        self.last_reward_result = None
        self.reward_strategy = load_reward_strategy(reward_strategy)
        self.reward_strategy_id = self.reward_strategy.strategy_id
        self.reward_strategy_class = reward_class_path(self.reward_strategy)

        rows, cols = self.global_view.shape
        # +8 trailing scalars: 4 pacman-memory + team_min_dist + step + remaining + pallets_remaining
        self._state_dim = (rows * cols) + (3 * len(self.possible_agents)) + 8
        self._state_space = Box(low=-1.0, high=1.0, shape=(self._state_dim,), dtype=np.float32)

        # Rendering configuration. The Pygame renderer is imported lazily so
        # headless training does not initialize graphics.
        self.render_mode = render_mode
        self.tile_size = int(tile_size)
        self.fps = int(fps)
        self.show_observations = bool(show_observations)
        self._renderer = None
        # Episode-level pallet count, set on reset(); guards state() before first reset.
        self._total_pallets = 0
        self._pellet_mask = self._build_initial_pellet_mask()

        # Deterministic Pacman controller; reset per episode to clear its state
        # machine. Replaces the former Action.choose_random() policy.
        self._pacman_policy = PacmanPolicy()

    # Reset environment and return initial per-agent observation/info dicts.
    def reset(self, seed: int = None, options: dict = None):
        # Copy agent list for PettingZoo's active agent tracking
        self.agents = copy(self.possible_agents)
        # Restore clean grid state to avoid carrying over mutated cells across episodes.
        self.global_view = np.array(self._base_grid, copy=True)

        # Reset shared episode memory.
        self.step_count = 0
        # Fresh Pacman controller so its flee/cooldown state does not leak
        # across episodes.
        self._pacman_policy = PacmanPolicy()
        self.last_pacman_sighting_position = None
        self.last_pacman_sighting_step = None
        self.last_team_reward_breakdown = {}
        self.last_reward_category_totals = {"shaping": 0.0, "terminal": 0.0}
        self.last_reward_context = None
        self.last_reward_result = None

        # --- Spawn ghosts at the map-authored spawn cells ---
        self.ghosts = [
            Ghost(id=f"ghost_{i+1}", current_position=pos)
            for i, pos in enumerate(self.ghost_spawns)
        ]
        # Place ghosts on the grid
        for ghost in self.ghosts:
            x, y = ghost.current_position  # Unpack position
            self.global_view[x, y] = Observation.GHOST.value  # Mark as ghost

        # --- Spawn Pacman at the map-authored spawn cell ---
        self.pacman = PacMan(id="pacman", current_position=self.pacman_spawn)
        self.global_view[*self.pacman.current_position] = Observation.PAC_MAN.value
        self._reset_visual_pellets()
        # Capture the per-episode pallet count (after spawn cells are cleared) so
        # step() can detect the "Pacman ate everything" win condition.
        self._total_pallets = int(self._pellet_mask.sum()) if self._pellet_mask is not None else 0

        # --- Build initial observations and info dicts for all ghosts ---
        observations = {ghost.id: self._get_observation(ghost) for ghost in self.ghosts}
        initial_context = self._build_reward_context(
            actions={},
            pellets_before=self._remaining_pellets(),
            capture_happened=False,
            timeout_happened=False,
            pacman_win_happened=False,
        )
        self.reward_strategy.reset(initial_context)
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

        pellets_before = self._remaining_pellets()

        # Move Pacman first using the deterministic safety-aware policy: it
        # seeks the nearest safe pellet and flees ghosts within danger range.
        ghost_positions = [ghost.current_position for ghost in self.ghosts]
        pacman_action = self._pacman_policy.choose_action(
            self.global_view,
            self._pellet_mask,
            ghost_positions,
            self.pacman.current_position,
        )
        self._execute_action(self.pacman, pacman_action)

        # Then apply each ghost action received from the learning policy.
        # Use ghost ids instead of dict iteration order to avoid agent-action mismatches.
        decoded_actions = {}
        for ghost in self.ghosts:
            if ghost.id not in actions:
                raise KeyError(f"Missing action for ghost '{ghost.id}'. Received keys: {list(actions.keys())}")
            action = self._decode_action(actions[ghost.id])
            decoded_actions[ghost.id] = action
            self._execute_action(ghost, action)

        # One environment transition completed.
        self.step_count += 1

        # Update local observation for all ghosts after movement.
        for ghost in self.ghosts:
            observations[ghost.id] = self._get_observation(ghost)

        capture_happened = self._is_capture_state()
        timeout_happened = (self.step_count >= self.max_steps) and (not capture_happened)

        # Pacman wins by eating every pallet on the board. Capture takes priority,
        # so this outcome only applies when the ghosts did not catch Pacman.
        pallets_all_eaten = (
            self._pellet_mask is not None
            and self._total_pallets > 0
            and int(self._pellet_mask.sum()) == 0
        )
        pacman_win_happened = pallets_all_eaten and not capture_happened
        game_over_happened = bool(capture_happened or timeout_happened or pacman_win_happened)

        any_visible, seen_positions = self._collect_visible_pacman_positions()
        if any_visible:
            self.last_pacman_sighting_position = seen_positions[0]
            self.last_pacman_sighting_step = self.step_count

        reward_context = self._build_reward_context(
            actions=decoded_actions,
            pellets_before=pellets_before,
            capture_happened=capture_happened,
            timeout_happened=timeout_happened,
            pacman_win_happened=pacman_win_happened,
            visible_pacman_positions=seen_positions,
        )
        reward_result = self.reward_strategy.compute(reward_context)
        team_reward = reward_result.total
        self.last_reward_context = reward_context
        self.last_reward_result = reward_result
        self.last_team_reward_breakdown = reward_result.breakdown
        self.last_reward_category_totals = reward_result.category_totals

        # Shared reward is broadcast to every ghost.
        for ghost in self.ghosts:
            rewards[ghost.id] = float(team_reward)
            terminations[ghost.id] = game_over_happened
            truncations[ghost.id] = False
            infos[ghost.id] = {
                "last_pacman_sighting_position": self.last_pacman_sighting_position,
                "last_pacman_sighting_step": self.last_pacman_sighting_step,
                "reward_breakdown": dict(self.last_team_reward_breakdown),
                "reward_categories": dict(self.last_reward_category_totals),
                "reward_strategy_id": self.reward_strategy_id,
            }

        # If episode ended, clear active agents list according to PettingZoo convention.
        if any(terminations.values()):
            self.agents = []

        # Return full transition tuple expected by ParallelEnv step API.
        return observations, rewards, terminations, truncations, infos

    # Close hook for optional renderer resources.
    def close(self):
        if self._renderer is not None:
            self._renderer.close()
            self._renderer = None

    def render(
        self,
        *,
        learner: str | None = None,
        total_reward: float | None = None,
        done: bool = False,
        last_action_by_agent: dict[str, str] | None = None,
        last_reward_by_agent: dict[str, float] | None = None,
        final_result: dict | None = None,
    ):
        if self.render_mode is None:
            return None

        return self._render_scene(
            render_mode=self.render_mode,
            learner=learner,
            total_reward=total_reward,
            done=done,
            last_action_by_agent=last_action_by_agent,
            last_reward_by_agent=last_reward_by_agent,
            final_result=final_result,
        )

    def capture_frame(
        self,
        *,
        learner: str | None = None,
        total_reward: float | None = None,
        done: bool = False,
        last_action_by_agent: dict[str, str] | None = None,
        last_reward_by_agent: dict[str, float] | None = None,
        final_result: dict | None = None,
    ):
        return self._render_scene(
            render_mode="rgb_array",
            learner=learner,
            total_reward=total_reward,
            done=done,
            last_action_by_agent=last_action_by_agent,
            last_reward_by_agent=last_reward_by_agent,
            final_result=final_result,
        )

    def wait_for_close(
        self,
        *,
        learner: str | None = None,
        total_reward: float | None = None,
        done: bool = False,
        last_action_by_agent: dict[str, str] | None = None,
        last_reward_by_agent: dict[str, float] | None = None,
        final_result: dict | None = None,
    ) -> None:
        if self.render_mode != "human":
            return

        renderer = self._get_renderer()
        while not renderer.is_closed:
            self._render_scene(
                render_mode="human",
                learner=learner,
                total_reward=total_reward,
                done=done,
                last_action_by_agent=last_action_by_agent,
                last_reward_by_agent=last_reward_by_agent,
                final_result=final_result,
            )

    def _render_scene(
        self,
        *,
        render_mode: str,
        learner: str | None,
        total_reward: float | None,
        done: bool,
        last_action_by_agent: dict[str, str] | None,
        last_reward_by_agent: dict[str, float] | None,
        final_result: dict | None,
    ):
        if render_mode not in self.metadata["render_modes"]:
            raise ValueError(
                f"Unsupported render_mode={render_mode!r}. "
                f"Expected one of {self.metadata['render_modes']}."
            )

        renderer = self._get_renderer()
        return renderer.render(
            self.global_view,
            self._pellet_mask,
            render_mode=render_mode,
            ghosts=self.ghosts,
            pacman=self.pacman,
            step_count=self.step_count,
            max_steps=self.max_steps,
            learner=learner,
            total_reward=total_reward,
            done=done,
            last_action_by_agent=last_action_by_agent,
            last_reward_by_agent=last_reward_by_agent,
            final_result=final_result,
        )

    # Cache observation spaces because they are static by agent ID.
    @functools.lru_cache(maxsize=None)
    # Return observation space for one agent.
    def observation_space(self, agent: AgentID):
        """
        Returns the partial information available for the given agent.
        A local view of a (view_size x view_size) grid centered on the agent's
        position (view_size = GHOST_VIEW_SIZE), with the following encoded values:
            (1) Capture;
            (2) Empty;
            (3) Ghost;
            (4) PAC-MAN;
            (5) Wall.
        """
        # Encoded values span [1, 5], with uint8 storage.
        return Box(low=1, high=5, shape=(self.view_size, self.view_size), dtype=np.uint8)

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

    # Return centralized state for value factorization methods (for example qmixglobal).
    def state(self) -> np.ndarray:
        return self._build_global_state()

    # Define state space for PettingZoo wrappers that request return_state=True.
    @property
    def state_space(self):
        return self._state_space

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
            if isinstance(agent, Ghost):
                agent.last_move_direction = (new_x - x, new_y - y)
            # Clear old position on the grid.
            self.global_view[x, y] = Observation.EMPTY.value
            if isinstance(agent, PacMan):
                self._consume_visual_pellet(agent.current_position)

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

    def _get_renderer(self):
        if self._renderer is None:
            from custom_environment.env.rendering import PacmanRenderer

            self._renderer = PacmanRenderer(
                tile_size=self.tile_size,
                fps=self.fps,
                caption="Pacman MARL",
                show_observations=self.show_observations,
            )
        else:
            self._renderer.show_observations = self.show_observations
        return self._renderer

    def _build_initial_pellet_mask(self) -> np.ndarray | None:
        if self._base_pellet_mask.ndim != 2:
            return None
        return np.array(self._base_pellet_mask, copy=True)

    def _reset_visual_pellets(self) -> None:
        self._pellet_mask = self._build_initial_pellet_mask()
        if self._pellet_mask is None:
            return

        for ghost in self.ghosts:
            self._consume_visual_pellet(ghost.current_position)
        if self.pacman is not None:
            self._consume_visual_pellet(self.pacman.current_position)

    def _consume_visual_pellet(self, position: tuple[int, int]) -> None:
        if self._pellet_mask is None:
            return

        row, col = position
        rows, cols = self._pellet_mask.shape
        if 0 <= row < rows and 0 <= col < cols:
            self._pellet_mask[row, col] = False

    # Normalize action tokens to Action enum.
    @staticmethod
    def _decode_action(action) -> Action:
        if isinstance(action, Action):
            return action

        action_int = int(action)
        # Ghost actions follow Gym Discrete(4): integers in [0, 3].
        if 0 <= action_int < len(Action):
            return Action(action_int)
        raise ValueError(f"Invalid action token for ghost policy: {action}. Expected int in [0, 3].")

    # Compute the (view_size x view_size) local observation for one ghost.
    def _get_observation(self, ghost: Ghost) -> np.ndarray:
        # Read ghost position and view geometry.
        x, y = ghost.current_position
        r, size = self.view_radius, self.view_size
        rows, cols = self.global_view.shape
        # Fixed-shape patch; off-grid cells (near the border) are padded with WALL,
        # so a corner ghost sees impassable space beyond the map.
        patch = np.full((size, size), Observation.WALL.value, dtype=self.global_view.dtype)
        # Window in global coords, clamped to the grid to avoid negative-index wrap.
        x0, y0 = x - r, y - r
        sx0, sy0 = max(x0, 0), max(y0, 0)
        sx1, sy1 = min(x + r + 1, rows), min(y + r + 1, cols)
        # Copy the in-bounds overlap into the correctly offset slice of the patch.
        patch[sx0 - x0:sx1 - x0, sy0 - y0:sy1 - y0] = self.global_view[sx0:sx1, sy0:sy1]
        ghost.view = patch
        # Return local view.
        return ghost.view

    def _remaining_pellets(self) -> int:
        return int(self._pellet_mask.sum()) if self._pellet_mask is not None else 0

    def _build_reward_context(
        self,
        *,
        actions: dict[str, Action],
        pellets_before: int,
        capture_happened: bool,
        timeout_happened: bool,
        pacman_win_happened: bool,
        visible_pacman_positions: list[tuple[int, int]] | None = None,
    ) -> RewardContext:
        if visible_pacman_positions is None:
            _, visible_pacman_positions = self._collect_visible_pacman_positions()

        ghost_transitions = []
        for ghost in self.ghosts:
            previous = ghost.prev_position or ghost.current_position
            local_observation = tuple(
                tuple(int(value) for value in row)
                for row in np.asarray(ghost.view)
            )
            action = actions.get(ghost.id)
            ghost_transitions.append(
                GhostTransition(
                    ghost_id=ghost.id,
                    previous_position=tuple(previous),
                    current_position=tuple(ghost.current_position),
                    action=None if action is None else int(action.value),
                    invalid_move=bool(ghost.invalid_move),
                    local_observation=local_observation,
                )
            )

        pacman_previous = getattr(self.pacman, "prev_position", None)
        if pacman_previous is None:
            pacman_previous = self.pacman.current_position
        visible_positions = tuple(tuple(position) for position in visible_pacman_positions)
        return RewardContext(
            step_count=int(self.step_count),
            max_steps=int(self.max_steps),
            board_shape=tuple(int(value) for value in self.global_view.shape),
            wall_positions=self._reward_wall_positions,
            ghosts=tuple(ghost_transitions),
            pacman_previous_position=tuple(pacman_previous),
            pacman_position=tuple(self.pacman.current_position),
            pacman_visible=bool(visible_positions),
            visible_pacman_positions=visible_positions,
            pellets_before=int(pellets_before),
            pellets_remaining=self._remaining_pellets(),
            total_pellets=int(self._total_pallets),
            capture_happened=bool(capture_happened),
            timeout_happened=bool(timeout_happened),
            pacman_win_happened=bool(pacman_win_happened),
        )

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
            r = self.view_radius
            global_pos = (ghost_x + (local_x - r), ghost_y + (local_y - r))
            seen_positions.append(global_pos)
        return len(seen_positions) > 0, seen_positions

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

    def _build_global_state(self) -> np.ndarray:
        rows, cols = self.global_view.shape
        max_steps = max(1, int(self.max_steps))
        grid_norm = float(max(rows + cols, 1))

        # 1) Static wall map.
        wall_map_flat = self._wall_map.reshape(-1).astype(np.float32)

        # 2) Normalized ghost positions.
        ghost_positions_norm = []
        row_den = float(max(rows - 1, 1))
        col_den = float(max(cols - 1, 1))
        for ghost in self.ghosts:
            gx, gy = ghost.current_position
            ghost_positions_norm.extend([float(gx) / row_den, float(gy) / col_den])

        # 3) Team-level pacman memory target.
        any_visible, seen_positions = self._collect_visible_pacman_positions()
        target_position = seen_positions[0] if any_visible else self.last_pacman_sighting_position

        pacman_visible_now = 1.0 if any_visible else 0.0
        if target_position is None:
            target_x_norm = -1.0
            target_y_norm = -1.0
            steps_since_last_seen_norm = 1.0
        else:
            target_x_norm = float(target_position[0]) / row_den
            target_y_norm = float(target_position[1]) / col_den
            if any_visible or self.last_pacman_sighting_step is None:
                steps_since_last_seen_norm = 0.0
            else:
                since_last_seen = max(0, self.step_count - int(self.last_pacman_sighting_step))
                steps_since_last_seen_norm = min(float(since_last_seen) / float(max_steps), 1.0)

        # 4) Per-ghost distance to current target memory.
        ghost_to_target_dist_norm = []
        if target_position is None:
            ghost_to_target_dist_norm = [1.0 for _ in self.ghosts]
        else:
            for ghost in self.ghosts:
                dist = self._bfs_distance(ghost.current_position, target_position)
                if dist is None:
                    ghost_to_target_dist_norm.append(1.0)
                else:
                    ghost_to_target_dist_norm.append(min(float(dist) / grid_norm, 1.0))

        # 5) Team min distance summary.
        team_min_dist_norm = min(ghost_to_target_dist_norm) if ghost_to_target_dist_norm else 1.0

        # 6) Episode progress features.
        step_fraction = min(float(self.step_count) / float(max_steps), 1.0)
        remaining_fraction = 1.0 - step_fraction

        # 7) Board-clearance signal: fraction of pallets still on the board, so
        # coordinating agents (VDN/QMIX) can see how close Pacman is to winning.
        pallets_remaining_norm = (
            float(int(self._pellet_mask.sum())) / float(max(1, self._total_pallets))
            if self._pellet_mask is not None and self._total_pallets > 0
            else 1.0
        )

        state_vector = np.asarray(
            wall_map_flat.tolist()
            + ghost_positions_norm
            + [
                pacman_visible_now,
                target_x_norm,
                target_y_norm,
                steps_since_last_seen_norm,
            ]
            + ghost_to_target_dist_norm
            + [team_min_dist_norm, step_fraction, remaining_fraction]
            + [pallets_remaining_norm],
            dtype=np.float32,
        )

        return state_vector

    # Termination is handled centrally in step() to support capture and timeout.
