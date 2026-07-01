# Communication 000047 | ACD | 2026-07-01 13:01 UTC | Academicos (pares de pesquisa e professores)

> Publico-alvo: pares de pesquisa e professores em aprendizado por reforco multiagente (MARL), disciplina INF2072 (PUC-Rio). Registro academico; termos consagrados de RL/MARL mantidos em ingles conforme a norma da area.

---

## 1. Visao geral do trabalho

Este trabalho investiga **design de reward** para perseguicao cooperativa (cooperative pursuit) em um ambiente Pacman multiagente customizado. O ambiente implementa a interface **PettingZoo AEC**; os fantasmas (ghosts) sao agentes cooperativos que compartilham um sinal de reward de equipe (joint reward). Os algoritmos avaliados sao **IQL, VDN e QMIX**, treinados via **BenchMARL** (sobre TorchRL).

O objetivo especifico deste branch (`capture_v0_pure_potential_shaping`) e fazer os fantasmas efetivamente **perseguirem e capturarem** um Pacman dificil e evasivo -- ou seja, resolver um problema de **pursuit-evasion**, e nao apenas de coleta de reward. Ate o marco descrito aqui, o comportamento de perseguicao (following) nunca havia sido observado.

### Setup experimental

- **Agentes:** 2 fantasmas cooperativos (joint reward), Pacman como adversario controlado por politica fixa.
- **Ambiente:** labirinto ciclico de aproximadamente 20x20 celulas.
- **Captura:** por co-localizacao (`capture_radius = 0`) -- um fantasma precisa ocupar a mesma celula do Pacman.
- **Adversario (evader):** politica BFS `defense-first` (survival primeiro, coleta de pellets secundaria), com `safe_distance = 3`. O Pacman **move primeiro** a cada passo, o que lhe da vantagem estrutural de fuga.
- **Observabilidade:** parcial (POMDP) -- cada fantasma ve apenas sua vizinhanca local.
- **Regime CTDE** (Centralized Training, Decentralized Execution): o sinal de reward de treino le a posicao **verdadeira** do Pacman (via distancia BFS), mas as politicas em execucao observam apenas a visao local e nunca acessam essa distancia.

A narrativa a seguir esta organizada em duas etapas: uma tentativa fundamentada em **Potential-Based Reward Shaping (PBRS)** que falhou de modo diagnosticavel, e uma correcao subsequente que produziu perseguicao emergente.

---

## 2. Etapa 1 -- Tentativas com Potential-Based Reward Shaping (PBRS)

### 2.1 Hipotese e design

A hipotese inicial era que uma perseguicao densa poderia ser induzida por **potential-based reward shaping** no sentido classico de **Ng, Harada e Russell (1999)**, cuja garantia central e a **invariancia de politica**: adicionar um termo de shaping da forma `F = gamma * Phi(s') - Phi(s)` preserva a politica otima do MDP original.

A estrategia implementada (`CaptureV0PurePotentialShaping`) usa a forma telescopica episodica **nao descontada** `F = Phi(s') - Phi(s)`, com potencial `Phi = -alpha * mean_BFS_dist`, `alpha = 0.7`, tomando a **media** da distancia BFS sobre **todos** os fantasmas. Os terminais sao esparsos: `+100` na captura (`GET_PACMAN`), `-100` em timeout, `-100` quando o Pacman come todos os pellets; alem de um custo por passo `timestep = -0.05`.

Duas escolhas de design foram deliberadas, cada uma corrigindo um modo de falha observado empiricamente:

- **(a) Telescoping exato (gamma = 1).** Com `gamma = 1`, a soma cumulativa do shaping ao longo de um episodio e exatamente `Phi(fim) - Phi(inicio)`, ou seja, **independente do caminho**. Qualquer oscilacao no lugar (in-place) resulta em soma exatamente zero. Ja um shaping descontado `gamma * Phi(s') - Phi(s)` com `Phi <= 0` paga `(1 - gamma) * (-Phi) > 0` por ciclo de vaivem -- um lucro parasita que uma politica gulosa passou a **farmar** em vez de capturar.
- **(b) Distancia media (mean), nao minima (min).** Sob um reward de equipe compartilhado, um potencial baseado em `min` so responde ao fantasma mais proximo; os demais recebem um reward que nao conseguem influenciar, ficam sem gradiente e estacionam em cantos. A media recompensa **cada** fantasma por se aproximar, de modo que a equipe converge e cerca o Pacman -- que e exatamente a coordenacao que motiva o projeto.

A verificacao formal (research-000038) confirmou que a implementacao e **PBRS puro**: apenas o delta `Phi(s') - Phi(s)` entra no reward; o potencial absoluto nunca e somado diretamente.

### 2.2 A falha, diagnosticada causalmente (research-000035)

Contra um evader quase-perfeito que mantem a distancia de equipe aproximadamente **constante**, a soma telescopica colapsa para aproximadamente zero. O resultado e **pressao de perseguicao liquida nula** ao longo do episodio.

Simultaneamente, o terminal de captura `+100` quase nunca dispara: dois fantasmas de mesma velocidade em um labirinto ciclico **nao conseguem forcar** a captura de um evader `defense-first`. Trata-se de um teto estrutural de pursuit-evasion (cop-number / endgame), documentado em research-000033.

Assim, o sinal dominante remanescente e o `timestep = -0.05` por passo somado ao `-100` de timeout. A licao racional que o agente aprende e: *"perco -100 de qualquer forma; entao minimizo o custo por passo"* -- o que produz **passividade**. Os fantasmas nunca aprenderam a seguir.

Fatores secundarios contribuintes (registrados para transparencia metodologica):

- **Mismatch de desconto (discount mismatch):** a invariancia de Ng-Harada-Russell exige o `gamma` do proprio **learner** (`gamma = 0.99`), mas o shaping usou `gamma = 1` para eliminar o oscillation-farming. O termo ficou, portanto, nem limpamente invariante nem um driver forte de comportamento.
- **MLP sem memoria sob observabilidade parcial (POMDP):** uma rede feedforward nao tem memoria quando o Pacman sai do campo de visao.
- **Substrato de hyperparameters fraco:** replay buffer de 10k, update-to-data ratio de aproximadamente 6-10, piso de epsilon em 0.10 e cerca de 60k frames -- claramente subtreinado.

### 2.3 O reframe conceitual (insight central)

Contra um evader quase-perfeito, **capture rate e ao mesmo tempo o sinal de treino errado e a metrica de sucesso errada**.

E ha um ponto teorico mais profundo. A virtude central do PBRS -- **invariancia de politica** -- e exatamente o que **preservou a passividade**. Por construcao, um shaping invariante nao pode alterar a politica otima; logo, ele **nao podia** fabricar o vies de perseguicao (pursuit bias) de que efetivamente precisavamos. A propriedade que torna o PBRS teoricamente atraente e a propriedade que o tornou inutil neste regime.

---

## 3. Etapa 2 -- Nova politica de reward (capture_v0_closing) + correcoes de substrato

### 3.1 Design da closing reward

A nova estrategia (`CaptureV0ClosingReward`) implementa uma **closing reward persistente e nao-telescopica**:

```
closing_reward = closing_weight * clip(prev_dist - cur_dist, -clip, +clip)
```

sobre a distancia BFS **media** (mean) da equipe ao Pacman, com `closing_weight = 2.0` e `closing_clip = 2.0`.

O ponto de design e explicito: essa reward **nao** e potential-based, portanto **nao telescopa** ao longo do episodio. A equipe e paga a cada passo em que se aproxima e cobrada a cada passo em que recua. Uma oscilacao no lugar continua somando aproximadamente zero (celulas positivas e negativas se cancelam), e o `clip` limita qualquer tentativa de orbit-farming (risco RC4, research-000022).

O enquadramento teorico deve ser tornado explicito: esta estrategia **troca a invariancia de politica do PBRS por um pursuit bias explicito** -- que e precisamente o objetivo, ja que foi a invariancia que preservou a passividade que se busca corrigir. Isso implementa diretamente a recomendacao R2 de research-000035.

Um pequeno **termo de containment** (`pacman_legal_moves_reduced = 0.5`) recompensa a reducao do numero de movimentos legais do Pacman enquanto ele esta visivel -- ou seja, empurra o Pacman (herding) para cantos e becos sem saida. E este termo que **converte perseguicao em captura** contra um evader. Mantem-se os mesmos terminais esparsos `+100/-100`. Novamente **mean** (nao min), para que todo fantasma receba gradiente; `closing_weight = 2.0` compensa a escala por fantasma reduzida a metade no caso de 2 fantasmas.

### 3.2 Correcoes de substrato (research-000042 -> plan-000043, agora defaults no codigo)

| Hyperparameter | Antes | Depois | Motivacao |
|---|---|---|---|
| Replay buffer | 10k | 25k | Buffer totalmente aquecido antes do primeiro gradient step |
| Optimizer steps (por coleta) | 10 | 4 | Update-to-data ratio de 10:1 -> 4:1 |
| Init-random-frames | 5k | 25k | Preenchimento inicial adequado do buffer |
| Epsilon-anneal-ratio | 0.95 | 0.70 | Mais frames de exploitation |
| Epsilon-end | 0.10 | 0.05 | Frames de exploitation elevados de ~3k para ~18k do budget |

O treino foi escalado para **1.000.000 de frames**. O oponente de treino usou `CURRICULUM = off`, Pacman `hard` com `PACMAN_RANDOM_ACTION_PROB = 0.2` (20% de acoes aleatorias).

### 3.3 Resultado

**O IQL atinge uma capture rate de quase 80% apos 1M de frames.** O comportamento de perseguicao/following finalmente emerge.

Este resultado valida empiricamente a predicao central do diagnostico da Etapa 1: **corrigir qualquer um dos dois lados do loop quebrado** -- uma reward de perseguicao persistente OU uma captura atingivel -- faz o following aparecer. Registra-se com precisao: **os aproximadamente 80% sao o resultado observado para um algoritmo (IQL) sob a configuracao consolidada, e nao ainda o agregado multi-seed do benchmark completo.**

---

## 4. Metodologia e reprodutibilidade

O padrao de benchmarking adotado segue a Decisao **D-003** do projeto, alinhada a **Papoudakis et al. (2021, EPyMARL)**:

- **Grade experimental:** todos os algoritmos x **>= 5 seeds** (0-4, conforme constitution Q3) x 1M frames.
- **Reporte de resultados:** media +/- **95% CI** com estimadores robustos estilo **rliable** (IQM + bootstrap CI, **Agarwal et al. 2021**), apropriados ao regime de baixo n desta area.
- **Significancia:** teste t bicaudal (`p < 0.05`) para marcar algoritmos nao significativamente diferentes do melhor.
- **Metricas:** tanto **max-return** quanto **average-return** sobre todas as avaliacoes.
- **Avaliacao:** avaliacao gulosa (greedy) fixa de N episodios, **desacoplada** da coleta de treino.

### 4.1 Gap de dificuldade treino/eval (divulgacao obrigatoria, research-000045 R1)

Treino e avaliacao usam ruidos de Pacman **diferentes**, e isso precisa ser divulgado explicitamente. Na avaliacao, `EVASIVENESS` mapeia para `random_action_prob = 1 - evasiveness`. O numero de manchete canonico usa `EVASIVENESS = 1.0` (Pacman deterministico e maximamente dificil). Declara-se essa assimetria de forma explicita para que o leitor **nao atribua** o gap de capture rate a qualidade de aprendizado quando ele decorre, em parte, da diferenca de dificuldade entre os regimes.

### 4.2 Reprodutibilidade

Todo resultado reportado cita o hash de commit git exato (constitution C1). O estado descrito neste documento corresponde ao commit `8279a5b`.

Comando de reproducao:

```
make pipeline ALGOS=iql,vdn,qmixglobal
make eval-report EVASIVENESS=1.0
```

---

## 5. Limitacoes e honestidade metodologica

- Os aproximadamente **80% sao IQL** sob **uma** configuracao consolidada; o agregado completo de 5 seeds para IQL/VDN/QMIX com intervalos de confianca e o proximo artefato.
- A closing reward **sacrifica intencionalmente** a invariancia de politica do PBRS em troca de um pursuit bias -- essa e uma escolha de design, nao uma propriedade teoricamente neutra.
- Os resultados sao para **captura por co-localizacao** (`capture_radius = 0`) no regime de evader dificil (hard-evader); a generalizacao para outros regimes nao esta demonstrada.
- **Intervalos de confianca largos sao esperados em n = 5** e serao apresentados de forma honesta (D-003), sem estreitamento artificial.

### Status epistemico das afirmacoes

| Afirmacao | Status |
|---|---|
| IQL atinge ~80% de capture rate sob a config consolidada | Suportada por evidencia (resultado observado, um algoritmo) |
| A cadeia causal da passividade na Etapa 1 (telescoping -> soma zero; captura inatingivel -> teto estrutural) | Suportada por evidencia (diagnostico research-000035/000033) |
| Closing reward + captura atingivel generaliza para VDN/QMIX | Hipotese de design (a validar pelo agregado multi-seed) |

---

## Referencias

- Ng, A. Y., Harada, D., & Russell, S. (1999). *Policy invariance under reward transformations: Theory and application to reward shaping.* ICML.
- Papoudakis, G., Christianos, F., Schafer, L., & Albrecht, S. V. (2021). *Benchmarking Multi-Agent Deep Reinforcement Learning Algorithms in Cooperative Tasks (EPyMARL).* NeurIPS Datasets and Benchmarks Track.
- Agarwal, R., Schwarzer, M., Castro, P. S., Courville, A., & Bellemare, M. G. (2021). *Deep Reinforcement Learning at the Edge of the Statistical Precipice (rliable).* NeurIPS.

*Estado de codigo: commit `8279a5b`, branch `capture_v0_pure_potential_shaping`.*
