import numpy as np


class SimpleFootballEnv:
    """Minimal cooperative football-like grid environment.

    Two agents cooperate to score in the rightmost goal area.
    Both agents observe their own position, teammate position, ball position,
    and whether they hold the ball.
    """

    def __init__(self, grid_shape=(5, 6), max_steps=50):
        self.grid_shape = grid_shape
        self.max_steps = max_steps
        self.n_agents = 2
        self.action_dim = 6
        self.reset()

    def reset(self):
        self.step_count = 0
        height, width = self.grid_shape
        self.agent_pos = np.array([[0, 0], [1, 0]], dtype=np.int32)
        self.ball_pos = np.array([0, 0], dtype=np.int32)
        self.ball_holder = 0
        self.done = False
        return self._get_obs()

    def _get_obs(self):
        obs = []
        for i in range(self.n_agents):
            own = self.agent_pos[i] / np.array(self.grid_shape, dtype=np.float32)
            teammate = self.agent_pos[1 - i] / np.array(self.grid_shape, dtype=np.float32)
            ball = self.ball_pos / np.array(self.grid_shape, dtype=np.float32)
            has_ball = np.array([1.0 if self.ball_holder == i else 0.0], dtype=np.float32)
            obs.append(np.concatenate([own, teammate, ball, has_ball], axis=0))
        return obs

    def step(self, actions):
        if self.done:
            raise RuntimeError("Episode has finished. Call reset() first.")

        self.step_count += 1
        reward = 0.0

        for agent_id, action in enumerate(actions):
            self._apply_action(agent_id, action)

        self._resolve_ball_possession()

        if self._check_score(actions):
            reward = 1.0
            self.done = True
        elif self.step_count >= self.max_steps:
            reward = 0.0
            self.done = True
        else:
            reward = -0.001

        obs = self._get_obs()
        rewards = [reward] * self.n_agents
        dones = [self.done] * self.n_agents
        info = {"score": reward > 0}
        return obs, rewards, dones, info

    def _apply_action(self, agent_id, action):
        move = np.array([0, 0], dtype=np.int32)
        if action == 1:
            move = np.array([-1, 0], dtype=np.int32)
        elif action == 2:
            move = np.array([1, 0], dtype=np.int32)
        elif action == 3:
            move = np.array([0, -1], dtype=np.int32)
        elif action == 4:
            move = np.array([0, 1], dtype=np.int32)
        elif action == 5:
            move = np.array([0, 0], dtype=np.int32)

        if action in [1, 2, 3, 4]:
            new_pos = self.agent_pos[agent_id] + move
            min_coords = np.array([0, 0], dtype=np.int32)
            max_coords = np.array(self.grid_shape, dtype=np.int32) - 1
            self.agent_pos[agent_id] = np.minimum(np.maximum(new_pos, min_coords), max_coords)

    def _resolve_ball_possession(self):
        holder_pos = self.agent_pos[self.ball_holder]
        if not np.array_equal(self.ball_pos, holder_pos):
            self.ball_pos = holder_pos.copy()

        for i in range(self.n_agents):
            if i != self.ball_holder and np.array_equal(self.agent_pos[i], self.ball_pos):
                self.ball_holder = i
                break

    def _check_score(self, actions):
        if self.ball_holder is None:
            return False
        if actions[self.ball_holder] != 5:
            return False
        agent_x, agent_y = self.agent_pos[self.ball_holder]
        return agent_y == self.grid_shape[1] - 1
