"""
Multi-agent reinforcement learning algorithms.

This module implements three cooperative MARL algorithms:
  - IQL (Independent Q-Learning): Simple baseline, no explicit coordination
  - VDN (Value Decomposition Networks): Q-values sum over agents
  - QMIX: State-dependent mixing via hypernetwork

Key concepts:
  - ReplayBuffer: Experience buffer for batch training
  - Cooperative learning: All agents share reward signal
  - Target networks: Stabilize learning with delayed Q-value updates
  - Epsilon-greedy: Exploration strategy with decaying epsilon
"""
import random
from collections import deque

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from networks import AgentQNetwork, QMIXMixer

class ReplayBuffer:
    """
    Experience replay buffer for off-policy learning.

    Stores transitions (obs, action, reward, next_obs, done) and supports
    uniform random sampling for batch training. Helps decorrelate samples
    and improve stability of off-policy learning.

    Maximum capacity is enforced with a deque (FIFO if full).
    """

    def __init__(self, capacity, n_agents, obs_dim):
        """
        Initialize replay buffer.

        Args:
            capacity (int): Maximum number of transitions to store
            n_agents (int): Number of agents (used for shape validation)
            obs_dim (int): Observation dimension per agent
        """
        self.capacity = capacity  # Maximum buffer size
        self.n_agents = n_agents  # Number of agents
        self.obs_dim = obs_dim  # Observation dimension
        # Use deque with maxlen for automatic FIFO eviction when full
        self.buffer = deque(maxlen=capacity)

    def push(self, obs, actions, reward, next_obs, done):
        """
        Add a transition to the buffer.

        Args:
            obs (list): Current observations [obs_0, obs_1, ...]
            actions (list): Actions taken [a_0, a_1, ...]
            reward (float): Shared reward signal
            next_obs (list): Next observations [obs'_0, obs'_1, ...]
            done (bool): Whether episode terminated
        """
        # Store entire transition tuple in buffer
        self.buffer.append((obs, actions, reward, next_obs, done))

    def sample(self, batch_size):
        """
        Sample random batch from buffer.

        Converts Python lists to numpy arrays for batch processing.
        All agents' data stacked along axis 0 for vectorized operations.

        Args:
            batch_size (int): Number of transitions to sample

        Returns:
            tuple: (obs, actions, rewards, next_obs, dones) as numpy arrays
              - obs: (batch_size, n_agents, obs_dim)
              - actions: (batch_size, n_agents)
              - rewards: (batch_size, 1)
              - next_obs: (batch_size, n_agents, obs_dim)
              - dones: (batch_size, 1)
        """
        # Sample batch_size random indices from buffer
        batch = random.sample(self.buffer, batch_size)
        # Unzip transitions: list of tuples → tuple of lists
        obs, actions, rewards, next_obs, dones = zip(*batch)
        
        # Convert to numpy arrays with appropriate dtypes
        obs = np.array(obs, dtype=np.float32)  # Observations
        actions = np.array(actions, dtype=np.int64)  # Action indices
        rewards = np.array(rewards, dtype=np.float32).reshape(batch_size, 1)  # Rewards as column vector
        next_obs = np.array(next_obs, dtype=np.float32)  # Next observations
        dones = np.array(dones, dtype=np.float32).reshape(batch_size, 1)  # Dones as column vector
        
        return obs, actions, rewards, next_obs, dones

    def __len__(self):
        """Return current buffer size."""
        return len(self.buffer)


class IQLLearner:
    """
    Independent Q-Learning (IQL) for multi-agent cooperative tasks.

    Each agent learns its own Q-network using the shared reward signal.
    Agents act independently with no explicit communication or coordination.

    Pros:
      - Simple to implement
      - Scales linearly with number of agents
      - No coordination overhead

    Cons:
      - Ignores team structure
      - Non-stationary environment (teammates change behavior)
      - No knowledge sharing between agents

    Architecture:
      - n_agents separate Q-networks
      - Separate target networks for stability
      - Separate optimizers per agent
    """

    def __init__(self, obs_dim, n_actions, n_agents, lr=0.001, gamma=0.99, device="cpu"):
        """
        Initialize IQL learner.

        Args:
            obs_dim (int): Observation dimension
            n_actions (int): Number of actions
            n_agents (int): Number of agents
            lr (float): Learning rate. Default 0.001.
            gamma (float): Discount factor. Default 0.99.
            device (str): "cpu" or "cuda"
        """
        self.n_agents = n_agents  # Number of agents
        self.gamma = gamma  # Discount factor for future rewards
        self.device = device  # Computation device
        
        # Create separate Q-network for each agent
        self.q_networks = [AgentQNetwork(obs_dim, n_actions).to(device) for _ in range(n_agents)]
        # Create separate target networks for stability (updated periodically)
        self.target_networks = [AgentQNetwork(obs_dim, n_actions).to(device) for _ in range(n_agents)]
        # Create separate optimizer for each agent's Q-network
        self.optimizers = [optim.Adam(net.parameters(), lr=lr) for net in self.q_networks]
        
        # Initialize target networks with same weights as Q-networks
        IQLLearner._sync_targets(self)

    def _sync_targets(self):
        """Copy weights from Q-networks to target networks."""
        # For each agent, copy Q-network weights to target network
        for target, net in zip(self.target_networks, self.q_networks):
            target.load_state_dict(net.state_dict())

    def update(self, batch):
        """
        Update all agents' Q-networks using batch of transitions.

        For each agent:
          1. Compute Q-value for taken action: Q(s,a)
          2. Compute target using target network: r + gamma * max_a' Q_target(s',a')
          3. Compute MSE loss and backpropagate
          4. Update Q-network

        Args:
            batch (tuple): (obs, actions, rewards, next_obs, dones) from ReplayBuffer

        Returns:
            float: Mean loss across all agents
        """
        obs, actions, rewards, next_obs, dones = batch  # Unpack batch
        batch_size = obs.shape[0]  # Get batch size
        losses = []  # Accumulate losses for averaging
        
        # Update each agent independently
        for agent_id in range(self.n_agents):
            # Extract agent's observations and actions from batch
            obs_agent = torch.tensor(obs[:, agent_id, :], device=self.device)
            next_obs_agent = torch.tensor(next_obs[:, agent_id, :], device=self.device)
            actions_agent = torch.tensor(actions[:, agent_id], device=self.device)
            
            # Forward pass: get Q-values for current state
            q_values = self.q_networks[agent_id](obs_agent)  # Shape: (batch_size, n_actions)
            # Select Q-values for taken actions
            q_value = q_values.gather(1, actions_agent.unsqueeze(1)).squeeze(1)  # Shape: (batch_size,)
            
            # Compute target Q-values using target network (stops gradient)
            with torch.no_grad():
                next_q = self.target_networks[agent_id](next_obs_agent)  # Shape: (batch_size, n_actions)
                next_value = next_q.max(1)[0]  # Take max over actions: (batch_size,)
            
            # Compute target = r + gamma * max_a' Q_target(s', a') * (1 - done)
            # (1 - done) masks out terminal states
            reward_tensor = torch.tensor(rewards[:, 0], dtype=torch.float32, device=self.device)
            done_tensor = torch.tensor(dones[:, 0], dtype=torch.float32, device=self.device)
            target = reward_tensor + self.gamma * next_value * (1 - done_tensor)
            
            # Compute MSE loss between Q-values and targets
            loss = nn.functional.mse_loss(q_value, target)
            
            # Backpropagation
            self.optimizers[agent_id].zero_grad()  # Clear old gradients
            loss.backward()  # Compute gradients
            self.optimizers[agent_id].step()  # Update weights
            
            # Record loss for this agent
            losses.append(loss.item())
        
        # Return average loss across all agents
        return np.mean(losses)

    def act(self, obs, epsilon):
        """
        Select actions for all agents using epsilon-greedy strategy.

        With probability epsilon: random action (exploration)
        With probability 1-epsilon: argmax Q-value (exploitation)

        Args:
            obs (list): Observations for each agent
            epsilon (float): Probability of exploration

        Returns:
            list: Action index for each agent
        """
        actions = []
        # Select action for each agent
        for agent_id in range(self.n_agents):
            # Epsilon-greedy: random action with probability epsilon
            if random.random() < epsilon:
                # Random action from [0, n_actions)
                actions.append(random.randrange(self.q_networks[agent_id].net.model[-1].out_features))
            else:
                # Greedy action: argmax Q-value
                obs_agent = torch.tensor(obs[agent_id], dtype=torch.float32, device=self.device).unsqueeze(0)
                q_values = self.q_networks[agent_id](obs_agent)  # Shape: (1, n_actions)
                actions.append(int(q_values.argmax().item()))  # Get argmax as Python int
        
        return actions

    def state_dict(self):
        """Return model weights for checkpointing."""
        return {
            "q_networks": [net.state_dict() for net in self.q_networks],
        }

    def load_state_dict(self, state):
        """Load model weights from checkpoint."""
        for net, net_state in zip(self.q_networks, state["q_networks"]):
            net.load_state_dict(net_state)
        self._sync_targets()

    def save(self, path):
        """Save model checkpoint to file."""
        torch.save(self.state_dict(), path)

    @classmethod
    def load_from_checkpoint(cls, path, obs_dim, n_actions, n_agents, device="cpu"):
        """Load model from checkpoint file."""
        learner = cls(obs_dim, n_actions, n_agents, device=device)
        state = torch.load(path, map_location=device)
        learner.load_state_dict(state)
        return learner


class VDNLearner(IQLLearner):
    """
    Value Decomposition Networks (VDN) for multi-agent cooperative learning.

    Extends IQL by learning to decompose joint Q-value as sum of individual Q-values:
      Q_tot = sum_i Q_i(o_i, a_i)

    This factorization encourages coordination: improving any agent's individual
    Q-value increases the joint value, promoting cooperation.

    Advantages over IQL:
      - Explicit coordination via value factorization
      - Better sample efficiency than IQL

    Limitations:
      - Assumes additive value structure
      - Cannot represent complex interactions
      - QMIX is more general

    Implementation:
      - Uses same agent Q-networks as IQL
      - Sums individual Q-values instead of treating independently
      - Updates all agents jointly based on summed value
    """

    def __init__(self, obs_dim, n_actions, n_agents, lr=0.001, gamma=0.99, device="cpu"):
        """Initialize VDN learner (inherits from IQL)."""
        super().__init__(obs_dim, n_actions, n_agents, lr, gamma, device)

    def update(self, batch):
        """
        Update agents using value decomposition.

        Key difference from IQL:
          - Sum individual Q-values: Q_tot = sum_i Q_i
          - Optimize summed value against target: r + gamma * sum_i max_a' Q_target_i(s', a')
          - All agents updated jointly with shared loss

        Args:
            batch (tuple): Batch from ReplayBuffer

        Returns:
            float: Loss value
        """
        obs, actions, rewards, next_obs, dones = batch
        batch_size = obs.shape[0]
        
        # Reshape batch for vectorized computation across agents
        obs_agent = torch.tensor(obs.reshape(batch_size * self.n_agents, -1), device=self.device)
        next_obs_agent = torch.tensor(next_obs.reshape(batch_size * self.n_agents, -1), device=self.device)
        actions_agent = torch.tensor(actions.reshape(batch_size * self.n_agents), device=self.device)

        # Forward: compute Q-values for all agents
        q_values = torch.cat([self.q_networks[i](obs_agent[i::self.n_agents]) for i in range(self.n_agents)], dim=0)
        # Extract Q-values for taken actions
        q_taken = q_values.gather(1, actions_agent.unsqueeze(1)).squeeze(1)

        # Backward: compute target using target networks
        with torch.no_grad():
            # Get target Q-values from all target networks
            next_q_values = torch.cat([
                self.target_networks[i](next_obs_agent[i::self.n_agents]) for i in range(self.n_agents)
            ], dim=0)
            # Get max Q-values per agent
            next_max = next_q_values.view(self.n_agents, batch_size, -1).max(dim=2)[0]
            # Sum over agents: total = sum_i max_a' Q_target_i
            next_total = next_max.sum(dim=0)

        # Current total: sum individual Q-values taken
        current_total = q_taken.view(self.n_agents, batch_size).sum(dim=0)
        
        # Compute target with reward and done mask
        reward_tensor = torch.tensor(rewards[:, 0], dtype=torch.float32, device=self.device)
        done_tensor = torch.tensor(dones[:, 0], dtype=torch.float32, device=self.device)
        target = reward_tensor + self.gamma * next_total * (1 - done_tensor)
        
        # Compute loss and update all agents jointly
        loss = nn.functional.mse_loss(current_total, target)
        for opt in self.optimizers:
            opt.zero_grad()
        loss.backward()
        for opt in self.optimizers:
            opt.step()
        
        return loss.item()


class QMIXLearner(VDNLearner):
    """
    QMIX: Monotonic Value Function Factorisation for Multi-Agent RL.

    Extends VDN with a learnable mixing network that combines agent Q-values
    using state-dependent weights. Maintains monotonicity for stable optimization.

    Key advantage over VDN:
      - More expressive than additive factorization
      - Learned mixing weights depend on global state
      - Hypernetwork ensures monotonicity (positive weights)

    Paper: "QMIX: Monotonic Value Function Factorisation for Decentralised Multi-Agent RL"
    https://arxiv.org/abs/1803.11485

    Architecture:
      - Agent Q-networks (same as IQL/VDN)
      - QMIXMixer: hypernetwork that learns mixing function
      - Separate mixer for target values (updated periodically)
    """

    def __init__(self, obs_dim, n_actions, n_agents, state_dim, lr=0.001, gamma=0.99, device="cpu"):
        """
        Initialize QMIX learner.

        Args:
            obs_dim (int): Observation dimension per agent
            n_actions (int): Number of actions
            n_agents (int): Number of agents
            state_dim (int): Global state dimension (typically obs_dim * n_agents)
            lr (float): Learning rate
            gamma (float): Discount factor
            device (str): "cpu" or "cuda"
        """
        # Initialize parent class (VDN with IQL components)
        super().__init__(obs_dim, n_actions, n_agents, lr, gamma, device)
        
        # Create mixing network (learns to combine agent Q-values)
        self.mixer = QMIXMixer(state_dim, n_agents).to(device)
        # Create target mixing network (updated periodically for stability)
        self.target_mixer = QMIXMixer(state_dim, n_agents).to(device)
        
        # Shared optimizer for all agent networks + mixer
        # This ensures joint optimization of all components
        self.optimizer = optim.Adam(
            list(self.mixer.parameters()) + 
            [p for net in self.q_networks for p in net.parameters()],
            lr=lr
        )
        
        # Synchronize target networks with current networks
        self._sync_targets()

    def _sync_targets(self):
        """Copy weights from Q-networks and mixer to target networks."""
        # Sync agent Q-network targets (inherited from VDN)
        super()._sync_targets()
        # Sync mixer target
        self.target_mixer.load_state_dict(self.mixer.state_dict())

    def state_dict(self):
        """Return all model weights for checkpointing."""
        state = super().state_dict()
        # Add mixer weights
        state["mixer"] = self.mixer.state_dict()
        return state

    def load_state_dict(self, state):
        """Load all model weights from checkpoint."""
        # Load agent networks
        super().load_state_dict(state)
        # Load mixer weights
        self.mixer.load_state_dict(state["mixer"])
        self.target_mixer.load_state_dict(state["mixer"])

    def save(self, path):
        """Save model checkpoint."""
        torch.save(self.state_dict(), path)

    @classmethod
    def load_from_checkpoint(cls, path, obs_dim, n_actions, n_agents, state_dim, device="cpu"):
        """Load model from checkpoint."""
        learner = cls(obs_dim, n_actions, n_agents, state_dim, device=device)
        state = torch.load(path, map_location=device)
        learner.load_state_dict(state)
        return learner

    def update(self, batch):
        """
        Update QMIX: optimize both agent Q-networks and mixing network.

        Process:
          1. Get individual agent Q-values from current networks
          2. Mix them using current mixer: Q_tot = mixer(Q_agents, state)
          3. Get target individual Q-values from target networks
          4. Mix them using target mixer: Q_tot_target = target_mixer(Q_agents_target, state)
          5. Compute target = r + gamma * Q_tot_target * (1 - done)
          6. Optimize MSE loss: ||Q_tot - target||^2

        Args:
            batch (tuple): Batch from ReplayBuffer

        Returns:
            float: Loss value
        """
        obs, actions, rewards, next_obs, dones = batch
        batch_size = obs.shape[0]
        
        # Reshape observations for vectorized computation
        obs_tensor = torch.tensor(obs.reshape(batch_size * self.n_agents, -1), device=self.device)
        next_obs_tensor = torch.tensor(next_obs.reshape(batch_size * self.n_agents, -1), device=self.device)
        actions_agent = torch.tensor(actions.reshape(batch_size * self.n_agents), device=self.device)

        # Forward: compute individual Q-values for all agents
        q_values = [self.q_networks[i](obs_tensor[i::self.n_agents]) for i in range(self.n_agents)]
        # Extract Q-values for taken actions
        q_taken = torch.stack([
            q_values[i].gather(1, actions_agent[i::self.n_agents].unsqueeze(1)).squeeze(1)
            for i in range(self.n_agents)
        ], dim=1)  # Shape: (batch_size, n_agents)

        # Mix individual Q-values using mixer
        state = torch.tensor(obs.reshape(batch_size, -1), device=self.device)
        total_q = self.mixer(q_taken, state).squeeze(1)  # Shape: (batch_size,)

        # Backward: compute target using target networks and target mixer
        with torch.no_grad():
            # Get target Q-values from target networks
            next_q_values = [self.target_networks[i](next_obs_tensor[i::self.n_agents]) for i in range(self.n_agents)]
            # Get max Q-values per agent
            next_max = torch.stack([q.max(dim=1)[0] for q in next_q_values], dim=1)  # Shape: (batch_size, n_agents)
            # Mix using target mixer
            next_state = torch.tensor(next_obs.reshape(batch_size, -1), device=self.device)
            next_total_q = self.target_mixer(next_max, next_state).squeeze(1)  # Shape: (batch_size,)
        
        # Compute target = r + gamma * Q_tot_target * (1 - done)
        reward_tensor = torch.tensor(rewards[:, 0], dtype=torch.float32, device=self.device)
        done_tensor = torch.tensor(dones[:, 0], dtype=torch.float32, device=self.device)
        target = reward_tensor + self.gamma * next_total_q * (1 - done_tensor)
        
        # Compute loss and update all parameters (agents + mixer)
        loss = nn.functional.mse_loss(total_q, target)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        
        return loss.item()
