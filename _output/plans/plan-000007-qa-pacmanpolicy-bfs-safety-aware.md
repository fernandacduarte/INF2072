# QA Log — plan-000007 | PacmanPolicy BFS safety-aware pellet maximization

**Brief:** implement a deterministic PacmanPolicy class that replaces Action.choose_random() with a BFS flood-fill pellet-maximization policy with ghost danger-zone hard exclusion and a reactive flee state machine (SEEKING_PELLET → FLEEING → COOLDOWN). Source: research-000006

---

## Q&A

### Q1: Quem é o agente principal — Pacman ou fantasmas?

O usuário esclareceu que está competindo **a favor do Pacman** ("foda-se os fantasmas", "Pacman must survive"). O objetivo é dar ao Pacman uma política determinística inteligente que sobreviva contra os fantasmas RL, não treinar os fantasmas contra um Pacman difícil.

**Decisão:** Manter a estrutura atual (fantasmas = agentes RL), mas substituir o Pacman aleatório por uma `PacmanPolicy` determinística com busca de pellets segura e fuga reativa. A pressão de sobrevivência do Pacman é o objetivo central.

### Q2: Qual algoritmo de pathfinding?

Conforme research-000006, BFS flood-fill (não A*) com modelo de hard exclusion das zonas de perigo dos fantasmas. Máquina de estados com COOLDOWN para evitar oscilação.

**Decisão:** Plano 000007 aprovado com "Implement now".
