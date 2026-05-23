"""
futebol2d: Multi-Agent Reinforcement Learning for Cooperative 2D Football

A PyTorch implementation of three cooperative multi-agent reinforcement learning algorithms:
  - IQL (Independent Q-Learning): Each agent learns independently with shared rewards
  - VDN (Value Decomposition Networks): Factorizes joint Q-values as sum of individual values
  - QMIX: Uses a mixing network to combine individual Q-values conditioned on global state

Environment:
  - SimpleFootballEnv: N agents on a 5x6 grid cooperate to move a ball to the goal
  
Modules:
  - env: Game environment with rendering
  - networks: Neural network architectures (MLP, AgentQNetwork, QMIXMixer)
  - algos: Learning algorithms (ReplayBuffer, IQLLearner, VDNLearner, QMIXLearner)
  - train: Training script with CSV logging and model checkpointing
  - eval: Evaluation and visualization script with rendered gameplay
  - plot: Plotting script to compare training curves from multiple runs
"""
