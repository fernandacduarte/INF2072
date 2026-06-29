# Communication 000030 | EVL | 2026-06-29 00:00 UTC | Avaliador (Professor da disciplina)

## Visao geral do projeto

Este projeto investiga coordenacao multi-agente em um ambiente Pacman customizado, no qual fantasmas cooperativos (baseline IQL, mais VDN e QMIX) precisam aprender a capturar um Pacman evasivo. A implementacao usa BenchMARL sobre TorchRL e segue o paradigma CTDE (Centralized Training, Decentralized Execution): no treino ha informacao centralizada, mas na execucao cada fantasma observa apenas uma janela parcial local 11x11. O trabalho relatado aqui foi conduzido na branch `capture_v0_pure_potential_shaping` e tem como foco uma investigacao de *desenho de reward*: que sinal de recompensa de fato induz perseguicao coordenada.

## O problema

Os fantasmas nao estavam aprendendo a perseguir o Pacman. Na avaliacao, em vez de fechar a distancia, eles vagavam pelo labirinto, ficavam encurralados em cantos, ou paravam imoveis proximos uns dos outros. O comportamento de captura coordenada simplesmente nao emergia. Isso reposicionou a pergunta de pesquisa: o gargalo nao era a escolha de algoritmo (IQL vs VDN vs QMIX), mas o *sinal de recompensa* que esses algoritmos estavam recebendo. A questao virou: qual reward de fato produz perseguicao coordenada sob observabilidade parcial?

## Diagnostico

A analise profunda do benchmark `pinklike3 / qmixglobal / seed 0` (research-000012, research-000024) mostrou que o reward esparso ativo praticamente nao oferecia sinal por passo apontando na direcao do Pacman:

- O termo terminal de captura (+100) disparava em apenas ~36% dos episodios.
- Os termos densos eram quase nulos ou contraproducentes. O termo `pacman_legal_moves_delta` tinha media de +0.0018 por passo e so disparava nos ~16% de passos em que o Pacman estava visivel. O termo `reverse_action` tinha media de -0.056 por passo, ou seja, era ANTI-perseguicao: penalizava exatamente as reversoes de juncao que uma caca em labirinto exige.
- O Pacman fica invisivel em ~84% dos passos, dado o campo de visao parcial 11x11. Sem nenhum gradiente de distancia, o QMIX estabilizava cedo: a curva de captura em treino ficava plana em ~26-36% ao longo de todos os 100k frames. Esse plato e a assinatura de um reward com sinal insuficiente (signal-starved), e nao de subtreinamento.
- Uma iteracao anterior do reward chegou a criar um otimo local literal de "ficar parado": uma penalidade de distancia baseada em avistamento desatualizado tornava o movimento aleatorio pior, em valor esperado, do que nao fazer nada. Os fantasmas, racionalmente, congelavam. O retorno medio degradava de -26 para -45 ao longo do treino.

Em resumo: os agentes nao aprendiam a perseguir porque nada no reward por passo os ensinava onde o Pacman estava nem recompensava aproximar-se dele.

## Ajustes no sistema de rewards

A partir do diagnostico, foram feitos os seguintes ajustes de engenharia sobre a base esparsa `capture_v0`:

- **Reintroducao de Potential-Based Reward Shaping (PBRS) puro**, criando a variante `capture_v0_pure_potential_shaping`. O potencial e `Phi = -alfa * (distancia dos fantasmas ao Pacman via BFS)`, com um termo de shaping telescopico somado a cada passo. Pela formulacao de Ng, Harada e Russell (1999), PBRS e *comprovadamente policy-invariant*: ele apenas reposiciona no tempo *onde* a recompensa chega, acelerando a atribuicao de credito sem alterar a politica otima. Esta e a principal alegacao metodologica do trabalho e e defensavel no relatorio.
- **Remocao da penalidade `reverse_action`**. Ela e baseada em acao/historico, quebra a invariancia de PBRS e pune perseguicao legitima em labirinto.
- **Enquadramento por informacao privilegiada (CTDE)**. O potencial le a posicao verdadeira do Pacman no simulador, mas isso ocorre *somente no treino*. As politicas dos fantasmas continuam observando apenas a janela parcial local 11x11 na execucao e nao usam nenhuma informacao privilegiada. Esse ponto e declarado explicitamente para antecipar a critica de que "os fantasmas trapaceiam": sob CTDE, usar o estado verdadeiro no sinal de treino e legitimo, desde que a politica executavel nao dependa dele.
- **Randomizacao de spawn por episodio** e uma **correcao de casamento de observacao na avaliacao**, para garantir avaliacao consistente com o treino.
- **Curriculum learning**: a dificuldade do Pacman aumenta de facil para medio para dificil ao longo do treino.
- **Bearing relativo ao Pacman** codificado na observacao de memoria compartilhada dos fantasmas.
- A selecao do checkpoint "best" passou a usar **taxa de captura** em vez de recompensa.

## Principal achado: reward farming em PBRS

O achado intelectualmente mais importante deste ciclo (research-000024, follow-up) e que a *primeira* versao de PBRS que entregamos, embora "gama-correta" no papel, continha uma brecha de reward farming que a politica aprendeu a explorar.

A avaliacao headless mostrou o sintoma: nenhuma captura em 80 passos, mesmo com o Pacman visivel em 75% do tempo e parado a ~3 celulas de distancia. Todos os fantasmas colapsavam em uma oscilacao de 2 celulas, indo e voltando entre duas posicoes.

O diagnostico expoe a sutileza. Com o shaping telescopico descontado `F = gama*Phi(s') - Phi(s)`, gama = 0.99, e `Phi = -alfa * dist <= 0` (sempre negativo), um ciclo de ida e volta rende `(1 - gama) * (-Phi) > 0`. Ou seja, o fator gama que adicionamos *para* preservar a invariancia de politica acabou criando um subsidio de acampamento por ciclo: +0.19 por ciclo, com acumulado de +17.5 ao longo de 80 passos e zero capturas. Pior: capturar ENCERRARIA esse fluxo lucrativo de shaping, entao a politica gulosa convergia para um otimo local de "cercar e acampar" (herd-and-camp).

A licao e precisa e citavel: **PBRS e policy-invariant em teoria, mas o desconto por gama combinado com um potencial estritamente negativo e com truncamento/timeout quebra essa invariancia na pratica**. O telescopio precisa ser desenhado de modo que oscilacao no mesmo lugar renda exatamente zero.

**Correcao entregue**: telescopio com gama = 1 exato, `F = Phi(s') - Phi(s)`, sobre um *minimo suave* da distancia dos fantasmas (o minimo suave remove uma descontinuidade no ponto em que muda qual fantasma e o mais proximo). Alem disso, a penalidade de `timestep` foi reforcada para -0.05, de modo que acampar fique estritamente negativo. Verificacao: um acampamento de 80 passos que antes rendia +50.1 agora rende -3.30. Um teste de regressao (`test_pure_pbrs_in_place_oscillation_cannot_be_farmed`) protege essa propriedade contra reintroducao acidental.

| Cenario (acampamento de 80 passos, sem captura) | Retorno de shaping |
|---|---|
| PBRS descontado (gama = 0.99, Phi negativo) | +50.1 |
| PBRS gama = 1 + minimo suave + timestep -0.05 | -3.30 |

## Algoritmos e parametros (configuracao de RL)

Esta secao documenta todos os algoritmos de RL e todos os parametros que afetam reward e aprendizado, incluindo os knobs parametrizados no Makefile. Os controles de maior impacto do ponto de vista de reinforcement learning estao destacados em negrito.

### A. Algoritmos

Todos os algoritmos sao value-based, off-policy, da familia DQN, com exploracao epsilon-greedy. Diferem apenas em como (ou se) os valores Q individuais dos fantasmas sao combinados durante o treino.

| Algoritmo | Coordenacao | Descricao |
|---|---|---|
| **IQL** (Independent Q-Learning) | nenhuma (baseline) | cada fantasma aprende seu proprio Q de forma independente |
| **VDN** (Value Decomposition Networks) | critico fatorado | Q conjunto = soma dos Q individuais |
| **QMIX** | mixing network monotonica | mistura monotonica nao-linear dos Q individuais; duas variantes no codigo: `qmixlocal` (mixer so com estado local) e `qmixglobal` (mixer com estado global, e o algoritmo principal usado nos experimentos) |

Framework: BenchMARL sobre TorchRL. Paradigma **CTDE** (Centralized Training, Decentralized Execution): o critico/mixer ve estado privilegiado no treino, mas as politicas dos fantasmas executam apenas com a observacao local 11x11.

### B. Hiperparametros de RL (fixos em run_pacman_benchmarl.py)

Estes sao os hiperparametros de maior impacto no aprendizado. Em especial, **gamma**, **learning rate**, **replay buffer**, **warmup** e o **schedule de epsilon** (secao C) sao os que mais influenciam a curva de aprendizado.

| Parametro | Valor | Papel em RL |
|---|---|---|
| **gamma (fator de desconto)** | **0.99** | horizonte efetivo; critico para PBRS (ver achado: com gamma<1 e potencial negativo surge o subsidio de camping; a versao final do shaping usa telescoping exato gamma=1) |
| **learning rate** | **1e-4** | passo do otimizador (Adam, padrao BenchMARL) |
| **replay buffer (memory_size)** | **10000** transicoes | amostragem off-policy |
| train_batch_size | 128 | tamanho do minibatch de atualizacao |
| frames_per_batch | 200 | frames coletados por iteracao antes de treinar |
| optimizer_steps | 10 | passos de gradiente por batch coletado |
| **init_random_frames (warmup)** | **5000** | exploracao puramente aleatoria antes de comecar a aprender |
| max_frames (orcamento default do script) | 60000 (Makefile usa 300000) | orcamento de amostras |

### C. Schedule de exploracao (epsilon-greedy)

O schedule de exploracao e RL-critico. O epsilon decai linearmente de **1.0 para 0.1**. O parametro `EPSILON_ANNEAL_RATIO` define a fracao do treino sobre a qual o epsilon anela: o default upstream e 0.95, mas **neste estudo usamos 0.5** (via Makefile), para dar a politica gananciosa uma fase low-epsilon mais longa. Esse foi um ajuste deliberado do balanco exploracao/explotacao e teve efeito pratico de **estabilizar a curva de capture rate**.

### D. Parametros do ambiente / observacao

| Parametro | Valor | Nota |
|---|---|---|
| grid_size | 20x20 | tamanho do mapa |
| ghost_view_size (observacao local) | 11x11 | parcial-observabilidade; Pacman invisivel ~84% dos passos |
| maze | pinklike3 | layout usado nos experimentos |
| PACMAN_SAFE_DISTANCE | 3 | distancia em que o Pacman BFS foge (reduzida de 5) |

### E. Knobs do Makefile (linha de comando do benchmark)

Estes sao os controles operacionais do estudo, expostos na linha de comando do benchmark. Eles determinam qual reward, qual algoritmo, quanto orcamento e sob quais condicoes de ambiente cada rodada e executada.

| Knob (Makefile) | Default | Efeito em aprendizado/reward |
|---|---|---|
| REWARD_ID | capture_v0_pure_potential_shaping | seleciona a funcao de reward (a variante PBRS deste estudo) |
| ALGOS | qmixglobal | algoritmo(s) treinados |
| **SEEDS** | 0,1,2 | **ATENCAO: abaixo do minimo de 5 sementes exigido pela constituicao (Q3); a rodada decisiva precisa de >=5** |
| FRAMES | 300000 | orcamento de treino (frames) |
| CHECKPOINT_INTERVAL | 10000 | frequencia de checkpoint; "best" e selecionado por **capture rate** (nao por reward) |
| DEVICE | cuda | dispositivo de treino |
| CURRICULUM | easy-medium-hard | curriculo de dificuldade do Pacman ao longo do treino |
| CURRICULUM_MAX_FRAMES | =FRAMES | horizonte do curriculo |
| **EPSILON_ANNEAL_RATIO** | 0.5 | fase de exploracao (ver secao C) |
| PACMAN_DIFFICULTY | hard | forca do Pacman (so vale com CURRICULUM=off; eval sempre forca hard) |
| **PACMAN_RANDOM_ACTION_PROB** | 0.0 | ruido estocastico do Pacman (so vale com CURRICULUM=off); este e o eixo do experimento dose-resposta planejado (p=1.0 aleatorio para p=0.0 deterministico) |
| RANDOMIZE_SPAWNS | 1 (on) | spawns aleatorios por episodio para forcar perseguicao reativa (impede memorizar rota fixa) |
| RANDOMIZE_SPAWNS_MIN_DISTANCE | 4 | distancia minima inicial fantasma-Pacman |

### F. Termos da funcao de reward (variante capture_v0_pure_potential_shaping)

| Termo | Valor | Tipo |
|---|---|---|
| captura (terminal) | +100 | esparso |
| timeout / Pacman vence por pellets | -100 | esparso |
| **timestep** | **-0.05** | denso (fortalecido para tornar camping estritamente negativo) |
| **PBRS shaping** | F = Phi(s') - Phi(s), Phi = -alpha * dist_BFS_min(fantasma->Pacman), **telescoping exato gamma=1** | denso, policy-invariant |

Em sintese, os parametros mais decisivos para o aprendizado neste estudo foram gamma (e sua interacao com o PBRS), o schedule de epsilon (anneal ratio 0.5), o orcamento de frames e a escolha do reward shaping. O numero de sementes (3) permanece como a lacuna conhecida de validade, abaixo do minimo de 5 exigido pela constituicao.

## Limitacoes e validade

Sou direto sobre o que ainda nao esta provado:

- Mesmo a prova de farming, os fantasmas ainda tem dificuldade de perseguir um Pacman *altamente evasivo* (que usa evasao por BFS) a partir de observacao parcial. Um ator nao consegue perseguir um Pacman que nao ve usando apenas coordenadas absolutas. Curriculum e PBRS juntos ainda nao bastam no extremo dificil.
- O benchmark decisivo ainda nao foi rodado. O resultado `pinklike3` e de uma unica seed e nao sustenta nenhuma afirmacao causal. Conforme o principio Q3 da constituicao do projeto, sao necessarias no minimo 5 seeds, num desenho A/B (esparso vs esparso+PBRS), para uma comparacao estatisticamente valida.
- O enquadramento da hipotese tambem precisa ser correto. A afirmacao defensavel e de **eficiencia amostral** ("PBRS acelera a aquisicao de comportamento de perseguicao"), e NAO de maior taxa de captura assintotica, que a propria invariancia de politica proibe. Por isso o resultado deve ser reportado com uma metrica *especifica de perseguicao*, por exemplo a fracao de passos em que a distancia da equipe ao Pacman diminui, e nao apenas a taxa de captura.
- Reprodutibilidade segue os principios da constituicao: seeds sao explicitas via CLI (T4), nenhum seed e fixado no codigo de producao, e qualquer resultado citado no relatorio deve referenciar o hash de commit exato (C1). Os outputs vao para `benchmarl_setup/runs/` (T2).

## Proximo passo

O proximo experimento (research-000028) reenquadra a questao em aberto como um estudo limpo de *dose-resposta / limiar*, adequado para a apresentacao final: **quao evasivo o Pacman precisa ser antes de os fantasmas deixarem de aprender a captura-lo?**

O desenho usa um unico botao continuo, `--pacman-random-action-prob p`, entre dois extremos ancorados: em p = 1.0 (Pacman totalmente aleatorio) o aprendizado funciona; em p = 0.0 (evasor deterministico) o aprendizado falha. A saida e uma curva de taxa de captura versus evasividade, com uma faixa de limiar, medida para IQL, VDN e QMIX, com no minimo 5 seeds, dentro de um orcamento apertado de 1 a 2 dias de CPU. Esse desenho transforma um resultado negativo ("ainda nao perseguem bem o evasor dificil") em uma contribuicao positiva e mensuravel: a localizacao do limiar de evasividade em que a coordenacao emergente colapsa.

## Nota de encerramento

Este relatorio prioriza honestidade sobre o que ainda nao foi demonstrado. A contribuicao metodologica solida ate aqui e o diagnostico do farming em PBRS descontado e a sua correcao verificada por teste; a contribuicao empirica decisiva depende do benchmark de >=5 seeds ainda pendente. Gostaria de receber seu retorno sobre o desenho do experimento de limiar de evasividade: em particular, se a metrica de perseguicao proposta (fracao de passos em que a distancia da equipe diminui) e a faixa de p escolhida sao adequadas para sustentar a alegacao de eficiencia amostral na apresentacao final.
