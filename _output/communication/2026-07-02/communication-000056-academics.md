# Communication 000056 | ACD | 2026-07-02 11:50 UTC | Academicos (professor de RL e colegas)

Conteúdo de texto para 2 slides de PowerPoint. Contexto: fantasmas cooperativos (IQL/VDN/QMIX via BenchMARL) perseguindo um Pacman evasivo em ambiente PettingZoo customizado.

---

## Slide 1 -- "PBRS: o que é e por que falhou aqui"

**Título sugerido:** Etapa 1 -- Potential-Based Reward Shaping (PBRS) e por que falhou

- PBRS (Ng, Harada & Russell 1999): `F = Phi(s') - Phi(s)`, com `Phi = -0.7 * dist_BFS_media` (média sobre TODOS os fantasmas)
- `gamma = 1` (telescoping exato): shaping acumulado no episódio = `Phi(fim) - Phi(inicio)`
- Contra um Pacman evasivo que mantém a distância ~constante, essa soma colapsa para ~0
- Perseguir não rende nada acumulado; sinal dominante vira `-0.05/passo` + `-100` de timeout
- Política aprendida: passividade ("vou perder -100 de qualquer forma; minimizo o custo")
- Garantia teórica do PBRS = invariância de política: ele não pode criar o pursuit bias que faltava

**Notas do apresentador:** O PBRS foi a primeira estratégia de shaping densa: um potencial proporcional à distância BFS média dos fantasmas ao Pacman, somado aos terminais esparsos (+100 captura, -100 timeout ou pellets). A propriedade central do PBRS, provada por Ng, Harada e Russell em 1999, é a invariância de política: o shaping não altera a política ótima, apenas acelera o aprendizado dela. Aqui essa virtude virou o problema: como a soma telescópica se reduz a Phi(fim) menos Phi(início), e o Pacman evasivo mantém a distância aproximadamente constante, o retorno acumulado da perseguição era ~zero. O que sobrava era a penalidade por passo e o -100 de timeout, e a política ótima sob essa reward era, de fato, ficar parado. Ou seja, o PBRS não falhou por bug: ele preservou fielmente uma política ótima passiva. A lição é que um shaping invariante não fabrica um viés de perseguição que a reward base não contém.

---

## Slide 2 -- "Nova ideia: Reward ClosingDistance"

**Título sugerido:** Desenvolvimento -- Nova ideia: Reward ClosingDistance

- Fruto direto dos aprendizados do PBRS
- PBRS não muda a política ótima, só acelera o aprendizado -- logo preservou a passividade
- A reward acumulada não recompensava perseguição; era isso que precisava mudar
- Nova reward persistente (NÃO telescópica): `2.0 * clip(dist_ant - dist_atual, -2, +2)` sobre a média BFS
- Paga cada passo de aproximação; oscilar no lugar soma ~0; `clip` barra orbit-farming
- + containment (`+0.5` por reduzir movimentos legais do Pacman) e 3o fantasma => IQL ~80% de captura; following emerge

**Notas do apresentador:** A `CaptureV0ClosingReward` troca deliberadamente a invariância de política do PBRS por um viés explícito de perseguição: em vez de um potencial que telescopa, ela paga diretamente a redução da distância BFS média a cada passo, de forma que o ganho não cancela ao longo do episódio mesmo contra um evasor que segura a distância. Usamos a média (e não o mínimo) porque a média dá gradiente a TODOS os fantasmas; com o mínimo, o segundo fantasma não influencia a reward e estaciona num canto. O clip em +-2 impede farmar reward orbitando o Pacman, e a oscilação no lugar soma ~zero porque células positivas e negativas se cancelam. Dois complementos convertem perseguição em captura: o bônus de containment por encurralar o Pacman em células com menos saídas, e um terceiro fantasma no labirinto, que torna a captura mecanicamente atingível. Importante: as distâncias leem a posição verdadeira do Pacman apenas no treino (regime CTDE); as políticas em execução continuam vendo só a visão local parcial. O resultado de ~80% de capture rate é do IQL sob uma única configuração, não o agregado multi-seed do benchmark.

---

Fonte: reformulado a partir de `communication-000050-academics.md` (deck Marp de 3 slides, 2026-07-02); valores verificados em `custom_environment/env/rewards/current.py`.
