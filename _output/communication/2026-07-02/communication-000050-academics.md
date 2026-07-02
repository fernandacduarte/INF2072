<!-- Communication 000050 | ACD | 2026-07-02 03:55 UTC | Academicos (professor de RL) -->
---
marp: true
paginate: true
---

# Pursuit cooperativo num Pacman multiagente
### O problema e o setup

**Objetivo:** fazer fantasmas cooperativos efetivamente PERSEGUIREM (following) um evader dificil -- nao apenas coletar reward. Following nunca havia sido observado.

- Ambiente Pacman customizado, interface **PettingZoo AEC**; labirinto ciclico ~20x20.
- Fantasmas = agentes cooperativos com **joint reward**; algoritmos **IQL / VDN / QMIX** via **BenchMARL** (TorchRL).
- Regime **CTDE**, observabilidade parcial (**POMDP**); reward de treino le a distancia BFS verdadeira, politicas em execucao veem so a visao local.
- Captura por **co-localizacao** (`capture_radius = 0`).
- Evader: Pacman `defense-first` (BFS survival-first, `safe_distance = 3`) que **move primeiro** -- vantagem estrutural de fuga.

Branch: `capture_v0_pure_potential_shaping`

---

## Etapa 1 -- PBRS e por que falhou (insight central)

**Potential-Based Reward Shaping** (Ng, Harada & Russell 1999), forma telescopica episodica nao descontada:

`F = Phi(s') - Phi(s)`,  com  `Phi = -alpha * mean_BFS_dist` (`alpha = 0.7`, media sobre os fantasmas). Terminais esparsos: `+100` captura, `-100` timeout/pellets, `-0.05` por passo.

- Contra um evader que mantem a distancia ~constante, a **soma telescopica colapsa para ~0** => pressao de perseguicao liquida nula.
- A captura `+100` quase nunca dispara: **2 fantasmas** de mesma velocidade nao forcam captura -- teto estrutural de pursuit-evasion (cop-number).
- Sinal dominante remanescente = `-0.05/passo` + `-100` de timeout => o agente aprende **passividade** ("perco -100 de qualquer jeito; minimizo custo").

**Insight teorico:** a **invariancia de politica** do PBRS -- sua virtude -- e exatamente o que **preservou a passividade**. Um shaping invariante NAO pode fabricar o pursuit bias necessario.

---

## Etapa 2 -- closing reward + resultado + metodologia

Nova reward persistente e **nao-telescopica** (`CaptureV0ClosingReward`):

`closing_reward = closing_weight * clip(prev_dist - cur_dist, -c, +c)` sobre mean BFS, `closing_weight = 2.0`.

- Troca **deliberadamente** a invariancia por um **pursuit bias explicito** (R2 de research-000035). Paga a cada passo de aproximacao; oscilar no lugar ainda soma ~0; `clip` barra orbit-farming.
- **Containment** (`pacman_legal_moves_reduced = 0.5`): herding para cantos -- converte perseguicao em captura.
- **3o fantasma** (maze `pinklike3`): torna a captura mecanicamente atingivel.
- Substrato corrigido: buffer 10k->25k, UTD 10->4, epsilon-end 0.10->0.05; **1M frames**.

**Resultado: IQL atinge ~80% de capture rate; following finalmente emerge.**

**Honestidade:** ~80% e UM algoritmo (IQL) sob UMA config -- nao o agregado multi-seed. Benchmark segue D-003: >=5 seeds, media +/- 95% CI, estimadores rliable/IQM + bootstrap, teste-t bicaudal, greedy eval desacoplado (Papoudakis 2021, Agarwal 2021). Estado: commit `43caa91`.
