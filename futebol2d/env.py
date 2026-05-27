"""
Environment module for cooperative multi-agent football game.

SimpleFootballEnv is a grid-world where N agents cooperate to move a ball and score.
Agents share a single reward signal that encourages teamwork.
"""
import numpy as np
import random  # Add this import for defender speed randomness


class SimpleFootballEnv:
    """
    Minimal cooperative football-like grid environment.

    N agents cooperate to score in the rightmost goal area (goal column).
        The team uses a shaped shared reward to improve sample efficiency:
            - strong bonus for scoring,
            - small step penalty,
            - dense progress bonus as the ball moves right,
            - pass bonus if possession moves forward,
            - failed shot and timeout penalties.

    Environment State:
      - grid_shape: (height, width) tuple defining grid dimensions
      - n_agents: number of cooperative agents
      - agent_pos: (n_agents, 2) array of agent [row, col] positions
      - defender_pos: (2,) array of defender [row, col] position
      - ball_pos: (2,) array of ball [row, col] position
      - ball_holder: index (0 to n_agents-1) of agent currently holding ball
      - step_count: number of steps taken in current episode

    Observations (per agent):
      - own position (normalized): [row/height, col/width]
      - all other agents' positions (normalized): [(n_agents-1)*2 floats]
      - ball position (normalized): [row/height, col/width]
      - defender position (normalized): [row/height, col/width]
      - possession flag: 1.0 if agent holds ball, 0.0 otherwise
      - possession-changed flag and remaining-steps ratio
      - Total obs_dim = 2*n_agents + 5

    Actions (discrete, 0-5):
      - 0: stay (no movement)
      - 1: move up (row -= 1)
      - 2: move down (row += 1)
      - 3: move left (col -= 1)
      - 4: move right (col += 1)
      - 5: shoot (score if ball-holder is in rightmost column)
    """

    @staticmethod
    def compute_grid_shape(n_agents):
        """
        Compute a heuristic grid size from number of agents.

        The heuristic keeps 2-agent behavior close to the original (5x6),
        while growing height/width as teams get larger.
        """
        if n_agents < 1:
            raise ValueError("n_agents must be >= 1")

        height = max(5, int(np.ceil(np.sqrt(4 * n_agents + 8))))
        width = max(6, height + 1, int(np.ceil(1.5 * n_agents + 3)))
        return (height, width)

    def __init__(self, grid_shape=None, n_agents=2, n_defenders=1, max_steps=50, reward_weights=None,
                 random_start_holder=True):  # New: randomize initial ball holder for better agent coverage
        """
        Initialize the football environment.

        Args:
            grid_shape (tuple|None): (height, width) of the grid world. If None,
                uses a heuristic based on n_agents.
            n_agents (int): Number of cooperative agents. Default 2.
            n_defenders (int): Number of defender entities. Default 1.
            max_steps (int): Maximum steps per episode. Default 50.
            reward_weights (dict): Optional reward shaping coefficients.
            random_start_holder (bool): If True, sample the initial ball holder uniformly
                on reset. This improves role coverage during training.
        """
        if n_agents < 1:
            raise ValueError("n_agents must be >= 1")
        if n_defenders < 0:
            raise ValueError("n_defenders must be >= 0")
        # Store grid dimensions (used for normalization and boundary checks)
        self.grid_shape = grid_shape if grid_shape is not None else self.compute_grid_shape(n_agents)
        # Maximum episode length (episode ends after this many steps)
        self.max_steps = max_steps
        # Number of agents in the environment
        self.n_agents = n_agents
        # Number of defenders in the environment
        self.n_defenders = n_defenders
        # Number of discrete actions each agent can take
        self.action_dim = 6
        # Whether to randomize which agent starts with the ball each episode
        # This helps all agents learn ball-holder behavior, not just agent 0
        self.random_start_holder = random_start_holder
        # Reward shaping coefficients (kept configurable for ablation studies)
        default_reward_weights = {
            "goal": 1.5,
            "step": -0.005,
            "progress": 0.15,
            "shoot_fail": -0.03,
            "defender_contact": -0.05,
            "forward_pass": 0.04,
            "backward_pass": -0.02,
            "timeout": -0.2,
        }
        self.reward_weights = default_reward_weights
        if reward_weights is not None:
            self.reward_weights.update(reward_weights)
        # Human-readable action names for debugging and visualization
        self.action_names = ["stay", "up", "down", "left", "right", "shoot"]
        # Initialize environment state (agent positions, ball, episode flags)
        self.reset()

    def _ball_progress(self):
        """Return normalized horizontal ball progress in [0, 1]."""
        width = self.grid_shape[1]
        if width <= 1:
            return 0.0
        return float(self.ball_pos[1]) / float(width - 1)

    def _pass_reward(self, previous_holder):
        """Reward forward possession changes and penalize backward ones."""
        if previous_holder == self.ball_holder:
            return 0.0

        previous_col = int(self.agent_pos[previous_holder][1])
        new_col = int(self.agent_pos[self.ball_holder][1])
        if new_col > previous_col:
            return self.reward_weights["forward_pass"]
        if new_col < previous_col:
            return self.reward_weights["backward_pass"]
        return 0.0

    def reset(self):
        """
        Reset the environment to initial state.

        Agents and ball start at random, non-overlapping positions.
        The ball is assigned to a random agent, and placed at their position.

        Returns:
            list: Observations for each agent (obs_dim floats each).
        """
        self.step_count = 0
        height, width = self.grid_shape

        total_entities = self.n_agents + self.n_defenders
        if total_entities > height * width:
            raise ValueError(
                f"grid_shape={self.grid_shape} does not have enough cells for "
                f"n_agents={self.n_agents} and n_defenders={self.n_defenders}"
            )

        # Sample unique random positions for all agents and defenders.
        all_cells = [(r, c) for r in range(height) for c in range(width)]
        chosen = np.random.choice(len(all_cells), total_entities, replace=False)
        self.agent_pos = np.array([all_cells[i] for i in chosen[: self.n_agents]], dtype=np.int32)
        self.defender_pos = np.array([all_cells[i] for i in chosen[self.n_agents :]], dtype=np.int32)

        # Randomly select initial ball holder
        self.ball_holder = int(np.random.randint(self.n_agents))
        # Assist-required scoring: at least one possession change must happen before goals count.
        self.possession_changed = False
        # Place ball at the initial holder's position
        self.ball_pos = self.agent_pos[self.ball_holder].copy()
        # Lane-block state for rendering and movement constraints.
        self.defender_blocking = False
        self.defender_blocked_col = None
        self.blocking_defender = None
        # Episode is not finished at initialization
        self.done = False
        # Return initial observations for all agents
        return self._get_obs()

    def _get_obs(self):
        """
        Construct observation vectors for all agents.

        Each agent receives:
          1. Own normalized position (2 floats)
          2. All other agents' normalized positions (2*(n_agents-1) floats)
          3. Ball normalized position (2 floats)
          4. Defender normalized position (2 floats)
          5. Ball possession indicator (1 float: 1.0 if holding, 0.0 otherwise)
          6. Possession change flag (1 float: 1.0 if possession changed, 0.0 otherwise)
          7. Remaining steps normalized (1 float: remaining_steps / max_steps)

        Returns:
            list: Observations, one per agent. Each obs is a 1D float32 array.
        """
        obs = []
        # Convert grid shape to float32 for normalization (prevents int division)
        grid_shape_f32 = np.array(self.grid_shape, dtype=np.float32)
        remaining_steps = (self.max_steps - self.step_count) / self.max_steps
        possession_flag = np.array([1.0 if self.possession_changed else 0.0], dtype=np.float32)

        # Construct observation for each agent
        for i in range(self.n_agents):
            # Agent i's own position, normalized to [0, 1] range
            own = self.agent_pos[i] / grid_shape_f32
            
            # All other agents' positions, normalized to [0, 1] range
            # Concatenate all positions except agent i's own (to avoid observing self twice)
            other_positions = [self.agent_pos[j] / grid_shape_f32 for j in range(self.n_agents) if j != i]
            if other_positions:
                all_others = np.concatenate(other_positions, axis=0)
            else:
                all_others = np.array([], dtype=np.float32)
            
            # Ball position, normalized to [0, 1] range
            ball = self.ball_pos / grid_shape_f32
            # Defender positions (all defenders), normalized to [0, 1] range
            if self.n_defenders > 0:
                defenders = (self.defender_pos / grid_shape_f32).reshape(-1)
            else:
                defenders = np.array([], dtype=np.float32)
            
            # Possession flag: 1.0 if this agent holds ball, 0.0 otherwise
            has_ball = np.array([1.0 if self.ball_holder == i else 0.0], dtype=np.float32)
            
            # Concatenate all observation components and ensure float32 dtype
            agent_obs = np.concatenate(
                [own, all_others, ball, defenders, has_ball, possession_flag, [remaining_steps]],
                axis=0,
            ).astype(np.float32)
            obs.append(agent_obs)
        
        return obs

    def render(self, mode="human"):
        """
        Render the current environment state as a text grid.

        Displays a grid where:
          - '.' is empty cell
          - '|' is the goal column (rightmost, where agents shoot)
          - 'D' is the defender
          - '0', '1', ... are agents without ball
          - '0*', '1*', ... are agents holding the ball
          - 'X' indicates collision (multiple entities in one cell)

        Args:
            mode (str): Rendering mode. Default "human" prints to stdout.

        Returns:
            str: Text representation of the grid.
        """
        # Unpack grid dimensions for rendering
        height, width = self.grid_shape
        
        # Create empty grid filled with empty cells ('.')
        grid = [["." for _ in range(width)] for _ in range(height)]

        # Mark rightmost column as goal area with '|' symbol
        for row in range(height):
            if grid[row][width - 1] == ".":
                grid[row][width - 1] = "|"

        # Draw active blocked lane across the full column.
        if self.defender_blocking and self.defender_blocked_col is not None:
            block_col = int(self.defender_blocked_col)
            for row in range(height):
                if grid[row][block_col] == ".":
                    grid[row][block_col] = "#"

        # Place agents on grid based on their current positions
        for agent_id, pos in enumerate(self.agent_pos):
            # Extract row and column coordinates
            row, col = pos.tolist()
            # Default symbol is agent ID (0, 1, 2, ...)
            symbol = f"{agent_id}"
            
            # Add '*' suffix if agent currently holds the ball
            if self.ball_holder == agent_id:
                symbol = f"{agent_id}*"
            
            # Mark collision ('X') only when another entity is already present.
            # Background markers ('.', '|', '#') are not entities.
            if grid[row][col] not in {".", "|", "#"}:
                symbol = "X"
            
            # Place symbol in grid at agent's position
            grid[row][col] = symbol

        # Place defenders (D) on grid.
        for d_row, d_col in self.defender_pos.tolist():
            if grid[d_row][d_col] not in {".", "|", "#"}:
                grid[d_row][d_col] = "X"
            else:
                grid[d_row][d_col] = "D"

        # Format grid rows as right-aligned strings with padding for readability
        lines = [" ".join(f"{cell:>2}" for cell in row) for row in grid]
        render_text = "\n".join(lines)

        # Print to stdout if human mode
        if mode == "human":
            # Print the grid visualization
            print("\n" + render_text)
            # Print current state information
            print(
                f"step={self.step_count} ball_holder={self.ball_holder} "
                f"ball_pos={tuple(self.ball_pos)} defender_pos={self.defender_pos.tolist()}"
            )
            if self.defender_blocking and self.defender_blocked_col is not None:
                print(f"blocked_col={int(self.defender_blocked_col)}")
            # Print action reference for debugging
            print(f"actions: {self.action_names}")
        
        return render_text

    def step(self, actions):
        """
        Execute one environment step with given actions.

        All agents act simultaneously. Ball transfer happens if agent moves to ball location.
                Reward is shared and shaped for better credit assignment:
                    - per-step cost,
                    - ball progress term,
                    - pass shaping,
                    - score bonus,
                    - failed-shot and timeout penalties.

        Args:
            actions (list): Action index (0-5) for each agent in order.

        Returns:
            tuple: (observations, rewards, dones, info)
              - observations: List of observation arrays for each agent
              - rewards: List of shared reward (same for all agents since cooperative)
              - dones: List of done flags (same for all agents)
              - info: Dict with extra info (e.g., 'score': bool indicating if goal scored)
        """
        # Safety check: ensure episode is not already finished
        if self.done:
            raise RuntimeError("Episode has finished. Call reset() first.")

        # Increment step counter
        self.step_count += 1
        # Track previous state for dense shaping terms
        previous_holder = self.ball_holder
        previous_progress = self._ball_progress()
        # Start with a small step cost to encourage shorter episodes
        reward = self.reward_weights["step"]

        # Random lane block for this step (active while agents move).
        self.defender_blocking = self.n_defenders > 0 and random.random() < 0.2
        if self.defender_blocking:
            self.blocking_defender = int(np.random.randint(self.n_defenders))
            self.defender_blocked_col = int(self.defender_pos[self.blocking_defender][1])
        else:
            self.blocking_defender = None
            self.defender_blocked_col = None

        # Apply all agents' movements simultaneously
        for agent_id, action in enumerate(actions):
            self._apply_action(agent_id, action)

        # Update ball position and handle ball possession transfers
        self._resolve_ball_possession()
        scored = self._check_score(actions)

        # Defender moves as before, now for each defender.
        for defender_id in range(self.n_defenders):
            self._move_defender(defender_id)
            if random.random() < 0.3:
                self._move_defender(defender_id)

        if self._holder_touched_by_any_defender():
            reward += self.reward_weights["defender_contact"]
        # Dense shaping term: reward positive progress of the ball to goal column
        progress_delta = self._ball_progress() - previous_progress
        reward += self.reward_weights["progress"] * progress_delta
        # Encourage useful passes that move the ball forward
        reward += self._pass_reward(previous_holder)

        # Check if team scored a goal
        if scored:
            reward += self.reward_weights["goal"]
            self.done = True
        # Check if episode reached maximum length (timeout)
        elif self.step_count >= self.max_steps:
            reward += self.reward_weights["timeout"]
            self.done = True
        else:
            # Penalize failed shots to avoid blind shooting from bad positions.
            if actions[previous_holder] == 5:
                reward += self.reward_weights["shoot_fail"]

        # Get next observations for all agents
        obs = self._get_obs()
        # All agents share the same reward (cooperative multi-agent learning)
        rewards = [reward] * self.n_agents
        # All agents share the same done flag
        dones = [self.done] * self.n_agents
        # Extra information about episode outcome
        info = {"score": scored}
        
        return obs, rewards, dones, info

    def _apply_action(self, agent_id, action):
        """
        Apply a single agent's action to update its position.

        Actions 1-4 cause movement in cardinal directions; action 5 (shoot) is handled elsewhere.
        Positions are clamped to grid boundaries to prevent out-of-bounds.

        Args:
            agent_id (int): Index of agent (0 to n_agents-1)
            action (int): Action code (0-5, see class docstring)
        """
        # Initialize movement vector as zero (no movement by default)
        move = np.array([0, 0], dtype=np.int32)
        
        # Map action index to movement direction
        if action == 1:
            # Action 1: move up (row decreases)
            move = np.array([-1, 0], dtype=np.int32)
        elif action == 2:
            # Action 2: move down (row increases)
            move = np.array([1, 0], dtype=np.int32)
        elif action == 3:
            # Action 3: move left (col decreases)
            move = np.array([0, -1], dtype=np.int32)
        elif action == 4:
            # Action 4: move right (col increases)
            move = np.array([0, 1], dtype=np.int32)
        elif action == 5:
            # Action 5: shoot (no movement, handled elsewhere)
            move = np.array([0, 0], dtype=np.int32)

        # Apply movement for movement actions only (actions 1-4)
        if action in [1, 2, 3, 4]:
            # Calculate new position by adding movement vector
            new_pos = self.agent_pos[agent_id] + move
            # Define grid boundaries (inclusive)
            min_coords = np.array([0, 0], dtype=np.int32)
            max_coords = np.array(self.grid_shape, dtype=np.int32) - 1
            # Defender lane block: prevent entering/crossing defender's column if blocking
            if hasattr(self, 'defender_blocking') and self.defender_blocking and self.defender_blocked_col is not None:
                old_col = self.agent_pos[agent_id][1]
                new_col = new_pos[1]
                block_col = self.defender_blocked_col
                # If agent would enter or cross the blocked column, cancel movement
                if (old_col != block_col and new_col == block_col) or (old_col == block_col and new_col != block_col):
                    return  # skip movement
            self.agent_pos[agent_id] = np.minimum(np.maximum(new_pos, min_coords), max_coords)

    def _resolve_ball_possession(self):
        """
        Update ball position and transfer possession if needed.

        Ball follows the ball-holder. If another agent moves to ball location,
        that agent becomes the new ball-holder (steal mechanics).
        """
        # Get current ball holder's position
        holder_pos = self.agent_pos[self.ball_holder]
        
        # Update ball position to match holder's current position
        if not np.array_equal(self.ball_pos, holder_pos):
            self.ball_pos = holder_pos.copy()

        # Check if another agent is at ball location (ball stealing mechanic)
        for i in range(self.n_agents):
            # Skip the current ball holder (can't steal from self)
            if i != self.ball_holder and np.array_equal(self.agent_pos[i], self.ball_pos):
                # Transfer ball to agent i
                self.ball_holder = i
                self.possession_changed = True
                # Break to avoid reassigning to multiple agents in same step
                break

    def _move_defender(self, defender_id):
        """Move one defender one cell toward the current ball holder (greedy chase)."""
        if self.n_defenders == 0:
            return

        holder_pos = self.agent_pos[self.ball_holder]
        delta = holder_pos - self.defender_pos[defender_id]
        move = np.array([0, 0], dtype=np.int32)

        # Prioritize the axis with greater distance for a direct chase.
        if abs(int(delta[1])) > abs(int(delta[0])):
            move[1] = int(np.sign(delta[1]))
        elif int(delta[0]) != 0:
            move[0] = int(np.sign(delta[0]))
        elif int(delta[1]) != 0:
            move[1] = int(np.sign(delta[1]))

        min_coords = np.array([0, 0], dtype=np.int32)
        max_coords = np.array(self.grid_shape, dtype=np.int32) - 1
        new_pos = self.defender_pos[defender_id] + move
        self.defender_pos[defender_id] = np.minimum(np.maximum(new_pos, min_coords), max_coords)

    def _holder_touched_by_any_defender(self):
        """Return True if any defender is on the ball-holder tile."""
        if self.n_defenders == 0:
            return False
        holder_tile = self.agent_pos[self.ball_holder]
        return bool(np.any(np.all(self.defender_pos == holder_tile, axis=1)))

    def _check_score(self, actions):
        """
        Check if the team scored a goal.

        Scoring requires:
          1. Ball holder performs shoot action (action 5)
          2. Ball holder is in rightmost column (col == width - 1)

        Args:
            actions (list): Action indices for all agents in order

        Returns:
            bool: True if goal scored, False otherwise
        """
        # If no ball holder, scoring is impossible
        if self.ball_holder is None:
            return False

        # Assist-required rule: at least one possession change must have happened this episode.
        if not self.possession_changed:
            return False
        
        # Check if ball holder chose shoot action (action 5)
        if actions[self.ball_holder] != 5:
            return False

        # Any defender blocks shots when on the ball-holder's tile.
        if self._holder_touched_by_any_defender():
            return False
        
        # Get ball holder's current position
        agent_x, agent_y = self.agent_pos[self.ball_holder]
        
        # Score if agent is in rightmost column (goal column)
        return agent_y == self.grid_shape[1] - 1
