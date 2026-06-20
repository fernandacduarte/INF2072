# Research 000006 | INF2072/fernanda | 2026-06-20 01:51 UTC | Pacman safety-aware pellet-maximization policy

tags: algorithm-design, pathfinding, marl-training-signal, pacman-policy, curriculum-learning

**User brief:** algoritm do pacman: utiliza diversos pathfinder estrela para maximizar o ganho de palets. se um caminho tiver um potencial de encontrar fantasmas, seu valor deve ser penalizado fazendo com que o pacman escolha os caminhos absolutamente seguros priorizando o maximo de ganho dentre estes. se durante um caminho o pacman encontrar um fantasma com colisao potencial, ele deve recalcular sua rota para o ponto mais seguro possivel e entao disparar novamente o algoritmo de maximizacao de pellets com maxima seguranca.

**Agent interpretation:** Design and evaluate a deterministic Pacman policy (not an RL agent) that replaces the current `Action.choose_random()` at `pacman_environment.py:197`. The policy uses pathfinding to maximize pellet collection, penalizes or rejects paths that pass through ghost danger zones, and reactively flees to the safest reachable cell when a ghost comes within collision range — then re-runs pellet maximization.

**Files read:**
- `custom_environment/env/pacman_environment.py` — environment step logic, `_bfs_distance()`, Pacman action dispatch (line 197)
- `custom_environment/env/domain/constant.py` — `Action`, `Observation`, `Reward` enums
- `custom_environment/env/domain/pacman.py` — `PacMan` dataclass (currently empty wrapper)
- `product-design/project/product-design-as-coded.md` — as-coded state

---

## Q&A Log

### Q1

**Question:** Projetar e avaliar um algoritmo de Pacman com A* para maximização de pellets com penalidade de segurança (evitar fantasmas) e comportamento reativo de fuga.

**Answer:**

#### 1. Algoritmo correto: BFS ou Dijkstra, não A*

Em um grid uniforme (custo 1 por movimento), A* reduz-se a BFS com overhead adicional de cálculo de heurística. A escolha do algoritmo depende diretamente de como a zona de perigo dos fantasmas é modelada:

| Modelo de Perigo | Algoritmo Correto | Complexidade |
|---|---|---|
| **Hard exclusion** — células adjacentes a fantasmas = paredes | **BFS** | O(R×C) |
| **Soft penalty** — células de risco têm custo elevado (ex: 10×) | **Dijkstra** | O(R×C × log(R×C)) |

A* é correto mas desnecessário para este grid: no modelo hard exclusion o grafo é não-ponderado (BFS é ótimo), e no modelo soft penalty a heurística de Manhattan pode subestimar o custo real causando expansões desnecessárias. **Recomendação: usar BFS (hard exclusion) como ponto de partida.**

#### 2. Seleção eficiente de pellet-alvo: flood-fill, não BFS por pellet

O design proposto executa um BFS separado do Pacman até cada pellet. Para P pellets e grid R×C isso é O(P × R×C) por step — desnecessário.

**Alternativa correta (flood-fill):**
1. Executar um único BFS a partir da posição do Pacman, preenchendo um `distance_map[row][col]` para todas as células alcançáveis.
2. Para cada pellet em `_pellet_mask`, o custo de caminho é simplesmente `distance_map[pellet_row][pellet_col]` — leitura O(1).
3. Selecionar o pellet com menor custo (ou maior valor normalizado por custo se pellets tiverem pesos diferentes).

Complexidade total: **O(R×C)** independente do número de pellets. O `_bfs_distance()` já implementado na linha 629 de `pacman_environment.py` pode ser reutilizado ou adaptado.

#### 3. Modelagem da zona de perigo

```
PACMAN_DANGER_RADIUS = 3  # células de BFS distância do Pacman a cada fantasma
```

A cada step, antes de executar o BFS de pellet:
- Coletar posições de todos os fantasmas via `global_view` (células com `Observation.GHOST.value`)
- Marcar como "bloqueadas" todas as células a BFS distância ≤ `DANGER_RADIUS` de qualquer fantasma
- No BFS do Pacman, tratar células marcadas como paredes (hard exclusion) **ou** atribuir custo elevado (soft penalty)

Raio de 3 células dá ao Pacman 1 step de margem além do `view_radius = 2` dos fantasmas — legível e simétrico com a geometria do ambiente.

#### 4. Máquina de estados para comportamento reativo

```
Estados:
  SEEKING_PELLET  → navegar ao pellet-alvo (BFS normal com hard exclusion)
  FLEEING         → mover para célula mais segura (máxima distância BFS de todos os fantasmas)
  COOLDOWN        → manter direção segura por N steps antes de re-avaliar

Transições:
  SEEKING → FLEEING: min(BFS distance de Pacman a qualquer fantasma) ≤ DANGER_RADIUS
  FLEEING → COOLDOWN: Pacman alcança célula-alvo de fuga
  COOLDOWN → SEEKING: N steps de cooldown expirados E nenhum fantasma no raio
```

O cooldown de 3 steps é o guard contra oscilação (Pacman alternando SEEKING/FLEEING na fronteira do raio).

**Célula-alvo de fuga:** maximizar `min(BFS distance de Pacman a cada fantasma)` sobre todas as células alcançáveis. Executar flood-fill a partir de cada posição de fantasma → ler o valor máximo do mínimo. Não usar distância Manhattan — paredes tornam-na não-confiável.

#### 5. Implicações para o sinal de treinamento RL dos fantasmas

Este é o ponto mais crítico da análise:

| Efeito do Pacman A* | Impacto no Aprendizado dos Fantasmas |
|---|---|
| Pacman evita células adjacentes a fantasmas | Fantasmas não podem "acampar" corredores; devem coordenar para bloquear rotas de fuga → **aumenta pressão por coordenação** |
| Pacman vai direto ao pellet mais próximo e seguro | Episódios sem coordenação de fantasmas terminam em PACMAN_WIN_PALLETS (-20) mais frequentemente → **sinal negativo mais forte** |
| Fuga reativa de um único fantasma | Apenas dois fantasmas coordenados conseguem bloquear → **vantagem direta de VDN/QMIX sobre IQL** |
| Política determinística | Políticas de fantasmas podem overfittar ao padrão de fuga → **mitigar com ε-random (5-10%)** |

**Risco de curriculum shock:** Se o treinamento começar do zero contra um Pacman A* completo, os fantasmas nunca recebem recompensa positiva nas primeiras iterações (Pacman sempre vence) e o sinal de aprendizado colapsa. Este é um failure mode documentado em MARL adversarial.

**Mitigação:** Iniciar com Pacman aleatório, transicionar para A* após N steps quando a recompensa dos fantasmas estabilizar positiva, ou usar soft penalty como estágio intermediário.

#### 6. Arquitetura de implementação

```python
# custom_environment/env/domain/pacman_policy.py  (novo arquivo)

class PacmanPolicy:
    """Deterministic pellet-maximizing policy with ghost avoidance."""

    DANGER_RADIUS = 3  # BFS cells
    FLEE_COOLDOWN = 3  # steps to maintain flee direction

    def choose_action(
        self,
        global_view: np.ndarray,
        pellet_mask: np.ndarray,
        ghost_positions: list[tuple[int, int]],
        pacman_pos: tuple[int, int],
    ) -> Action:
        ...
```

**Ponto de integração:** `pacman_environment.py` linha 197:
```python
# ANTES:
self._execute_action(self.pacman, Action.choose_random())

# DEPOIS:
action = self._pacman_policy.choose_action(
    self.global_view, self._pellet_mask,
    [g.current_position for g in self.ghosts],
    self.pacman.current_position,
)
self._execute_action(self.pacman, action)
```

O `PacmanPolicy` instanciado como `self._pacman_policy` em `__init__` mantém estado do autômato (estado atual, cooldown counter).

---

## Recommendations Summary

| # | Recomendação | Prioridade |
|---|---|---|
| R1 | Usar BFS (hard exclusion) em vez de A* como algoritmo base | HIGH |
| R2 | Usar flood-fill único (O(R×C)) em vez de BFS por pellet | HIGH |
| R3 | Implementar curriculum staging: iniciar com random Pacman, transicionar para A* | HIGH |
| R4 | Definir `PACMAN_DANGER_RADIUS = 3` em `constant.py` como constante configurável | MEDIUM |
| R5 | Usar BFS distance (não Manhattan) para calcular célula-alvo de fuga | MEDIUM |
| R6 | Encapsular política em `PacmanPolicy` class, não inline em `step()` | MEDIUM |
| R7 | Máquina de estados com COOLDOWN de 3 steps para evitar oscilação | MEDIUM |
| R8 | Adicionar ε=0.05 de aleatoriedade à política para evitar overfitting dos fantasmas | LOW |
| R9 | Testes unitários para: sem caminho seguro, sem pellets, corredor único de fuga | LOW |
