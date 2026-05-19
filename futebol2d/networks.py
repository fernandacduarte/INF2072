import torch
import torch.nn as nn


class MLP(nn.Module):
    def __init__(self, input_dim, output_dim, hidden_dims=(64, 64), activation=nn.ReLU):
        super().__init__()
        layers = []
        last_dim = input_dim
        for hidden_dim in hidden_dims:
            layers.append(nn.Linear(last_dim, hidden_dim))
            layers.append(activation())
            last_dim = hidden_dim
        layers.append(nn.Linear(last_dim, output_dim))
        self.model = nn.Sequential(*layers)

    def forward(self, x):
        return self.model(x)


class AgentQNetwork(nn.Module):
    def __init__(self, obs_dim, n_actions, hidden_dim=64):
        super().__init__()
        self.net = MLP(obs_dim, n_actions, hidden_dims=(hidden_dim, hidden_dim))

    def forward(self, obs):
        return self.net(obs)


class QMIXMixer(nn.Module):
    def __init__(self, state_dim, n_agents, mixing_hidden_dim=32):
        super().__init__()
        self.n_agents = n_agents
        self.hyper_w1 = nn.Linear(state_dim, n_agents * mixing_hidden_dim)
        self.hyper_b1 = nn.Linear(state_dim, mixing_hidden_dim)
        self.hyper_w2 = nn.Linear(state_dim, mixing_hidden_dim)
        self.hyper_b2 = nn.Sequential(nn.Linear(state_dim, mixing_hidden_dim), nn.ReLU(), nn.Linear(mixing_hidden_dim, 1))

    def forward(self, agent_qs, state):
        batch_size = agent_qs.size(0)
        w1 = torch.abs(self.hyper_w1(state)).view(batch_size, self.n_agents, -1)
        b1 = self.hyper_b1(state).view(batch_size, 1, -1)
        hidden = torch.relu(torch.bmm(agent_qs.unsqueeze(1), w1) + b1)
        w2 = torch.abs(self.hyper_w2(state)).view(batch_size, -1, 1)
        b2 = self.hyper_b2(state).view(batch_size, 1, 1)
        y = torch.bmm(hidden, w2) + b2
        return y.view(batch_size, -1)
