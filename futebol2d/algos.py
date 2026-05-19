import random
from collections import deque

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from futebol2d.networks import AgentQNetwork, QMIXMixer


class ReplayBuffer:
    def __init__(self, capacity, n_agents, obs_dim):
        self.capacity = capacity
        self.n_agents = n_agents
        self.obs_dim = obs_dim
        self.buffer = deque(maxlen=capacity)

    def push(self, obs, actions, reward, next_obs, done):
        self.buffer.append((obs, actions, reward, next_obs, done))

    def sample(self, batch_size):
        batch = random.sample(self.buffer, batch_size)
        obs, actions, rewards, next_obs, dones = zip(*batch)
        obs = np.array(obs, dtype=np.float32)
        actions = np.array(actions, dtype=np.int64)
        rewards = np.array(rewards, dtype=np.float32).reshape(batch_size, 1)
        next_obs = np.array(next_obs, dtype=np.float32)
        dones = np.array(dones, dtype=np.float32).reshape(batch_size, 1)
        return obs, actions, rewards, next_obs, dones

    def __len__(self):
        return len(self.buffer)


class IQLLearner:
    def __init__(self, obs_dim, n_actions, n_agents, lr=0.001, gamma=0.99, device="cpu"):
        self.n_agents = n_agents
        self.gamma = gamma
        self.device = device
        self.q_networks = [AgentQNetwork(obs_dim, n_actions).to(device) for _ in range(n_agents)]
        self.target_networks = [AgentQNetwork(obs_dim, n_actions).to(device) for _ in range(n_agents)]
        self.optimizers = [optim.Adam(net.parameters(), lr=lr) for net in self.q_networks]
        IQLLearner._sync_targets(self)

    def _sync_targets(self):
        for target, net in zip(self.target_networks, self.q_networks):
            target.load_state_dict(net.state_dict())

    def update(self, batch):
        obs, actions, rewards, next_obs, dones = batch
        batch_size = obs.shape[0]
        losses = []
        for agent_id in range(self.n_agents):
            obs_agent = torch.tensor(obs[:, agent_id, :], device=self.device)
            next_obs_agent = torch.tensor(next_obs[:, agent_id, :], device=self.device)
            actions_agent = torch.tensor(actions[:, agent_id], device=self.device)
            q_values = self.q_networks[agent_id](obs_agent)
            q_value = q_values.gather(1, actions_agent.unsqueeze(1)).squeeze(1)
            with torch.no_grad():
                next_q = self.target_networks[agent_id](next_obs_agent)
                next_value = next_q.max(1)[0]
            reward_tensor = torch.tensor(rewards[:, 0], dtype=torch.float32, device=self.device)
            done_tensor = torch.tensor(dones[:, 0], dtype=torch.float32, device=self.device)
            target = reward_tensor + self.gamma * next_value * (1 - done_tensor)
            loss = nn.functional.mse_loss(q_value, target)
            self.optimizers[agent_id].zero_grad()
            loss.backward()
            self.optimizers[agent_id].step()
            losses.append(loss.item())
        return np.mean(losses)

    def act(self, obs, epsilon):
        actions = []
        for agent_id in range(self.n_agents):
            if random.random() < epsilon:
                actions.append(random.randrange(self.q_networks[agent_id].net.model[-1].out_features))
            else:
                obs_agent = torch.tensor(obs[agent_id], dtype=torch.float32, device=self.device).unsqueeze(0)
                q_values = self.q_networks[agent_id](obs_agent)
                actions.append(int(q_values.argmax().item()))
        return actions

    def state_dict(self):
        return {
            "q_networks": [net.state_dict() for net in self.q_networks],
        }

    def load_state_dict(self, state):
        for net, net_state in zip(self.q_networks, state["q_networks"]):
            net.load_state_dict(net_state)
        self._sync_targets()

    def save(self, path):
        torch.save(self.state_dict(), path)

    @classmethod
    def load_from_checkpoint(cls, path, obs_dim, n_actions, n_agents, device="cpu"):
        learner = cls(obs_dim, n_actions, n_agents, device=device)
        state = torch.load(path, map_location=device)
        learner.load_state_dict(state)
        return learner


class VDNLearner(IQLLearner):
    def __init__(self, obs_dim, n_actions, n_agents, lr=0.001, gamma=0.99, device="cpu"):
        super().__init__(obs_dim, n_actions, n_agents, lr, gamma, device)

    def update(self, batch):
        obs, actions, rewards, next_obs, dones = batch
        batch_size = obs.shape[0]
        obs_agent = torch.tensor(obs.reshape(batch_size * self.n_agents, -1), device=self.device)
        next_obs_agent = torch.tensor(next_obs.reshape(batch_size * self.n_agents, -1), device=self.device)
        actions_agent = torch.tensor(actions.reshape(batch_size * self.n_agents), device=self.device)

        q_values = torch.cat([self.q_networks[i](obs_agent[i::self.n_agents]) for i in range(self.n_agents)], dim=0)
        q_taken = q_values.gather(1, actions_agent.unsqueeze(1)).squeeze(1)

        with torch.no_grad():
            next_q_values = torch.cat([
                self.target_networks[i](next_obs_agent[i::self.n_agents]) for i in range(self.n_agents)
            ], dim=0)
            next_max = next_q_values.view(self.n_agents, batch_size, -1).max(dim=2)[0]
            next_total = next_max.sum(dim=0)

        current_total = q_taken.view(self.n_agents, batch_size).sum(dim=0)
        reward_tensor = torch.tensor(rewards[:, 0], dtype=torch.float32, device=self.device)
        done_tensor = torch.tensor(dones[:, 0], dtype=torch.float32, device=self.device)
        target = reward_tensor + self.gamma * next_total * (1 - done_tensor)
        loss = nn.functional.mse_loss(current_total, target)
        for opt in self.optimizers:
            opt.zero_grad()
        loss.backward()
        for opt in self.optimizers:
            opt.step()
        return loss.item()


class QMIXLearner(VDNLearner):
    def __init__(self, obs_dim, n_actions, n_agents, state_dim, lr=0.001, gamma=0.99, device="cpu"):
        super().__init__(obs_dim, n_actions, n_agents, lr, gamma, device)
        self.mixer = QMIXMixer(state_dim, n_agents).to(device)
        self.target_mixer = QMIXMixer(state_dim, n_agents).to(device)
        self.optimizer = optim.Adam(list(self.mixer.parameters()) + [p for net in self.q_networks for p in net.parameters()], lr=lr)
        self._sync_targets()

    def _sync_targets(self):
        super()._sync_targets()
        self.target_mixer.load_state_dict(self.mixer.state_dict())

    def state_dict(self):
        state = super().state_dict()
        state["mixer"] = self.mixer.state_dict()
        return state

    def load_state_dict(self, state):
        super().load_state_dict(state)
        self.mixer.load_state_dict(state["mixer"])
        self.target_mixer.load_state_dict(state["mixer"])

    def save(self, path):
        torch.save(self.state_dict(), path)

    @classmethod
    def load_from_checkpoint(cls, path, obs_dim, n_actions, n_agents, state_dim, device="cpu"):
        learner = cls(obs_dim, n_actions, n_agents, state_dim, device=device)
        state = torch.load(path, map_location=device)
        learner.load_state_dict(state)
        return learner

    def update(self, batch):
        obs, actions, rewards, next_obs, dones = batch
        batch_size = obs.shape[0]
        obs_tensor = torch.tensor(obs.reshape(batch_size * self.n_agents, -1), device=self.device)
        next_obs_tensor = torch.tensor(next_obs.reshape(batch_size * self.n_agents, -1), device=self.device)
        actions_agent = torch.tensor(actions.reshape(batch_size * self.n_agents), device=self.device)

        q_values = [self.q_networks[i](obs_tensor[i::self.n_agents]) for i in range(self.n_agents)]
        q_taken = torch.stack([
            q_values[i].gather(1, actions_agent[i::self.n_agents].unsqueeze(1)).squeeze(1)
            for i in range(self.n_agents)
        ], dim=1)

        state = torch.tensor(obs.reshape(batch_size, -1), device=self.device)
        total_q = self.mixer(q_taken, state).squeeze(1)

        with torch.no_grad():
            next_q_values = [self.target_networks[i](next_obs_tensor[i::self.n_agents]) for i in range(self.n_agents)]
            next_max = torch.stack([q.max(dim=1)[0] for q in next_q_values], dim=1)
            next_state = torch.tensor(next_obs.reshape(batch_size, -1), device=self.device)
            next_total_q = self.target_mixer(next_max, next_state).squeeze(1)
        reward_tensor = torch.tensor(rewards[:, 0], dtype=torch.float32, device=self.device)
        done_tensor = torch.tensor(dones[:, 0], dtype=torch.float32, device=self.device)
        target = reward_tensor + self.gamma * next_total_q * (1 - done_tensor)
        loss = nn.functional.mse_loss(total_q, target)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        return loss.item()
