# Communication 000051 | EVL | 2026-07-02 03:53 UTC | Evaluators

**Para:** Fernanda e Erick (apresentacao amanha)
**Objetivo:** 1 slide para apresentar o Potential-Based Reward Shaping (PBRS) e como ele foi explorado neste projeto.
**Publico da apresentacao:** avaliador/professor (foco em rigor, decisoes justificadas e o que funcionou / nao funcionou).

---

## O slide (conteudo pronto para projetar)

> O arquivo `communication-000051-evaluators.html` e o slide 16:9 pronto para abrir no navegador e projetar (F11 = tela cheia). O texto abaixo e a mesma mensagem em Markdown, para editar ou colar em PowerPoint/Marp.

### Titulo

**Potential-Based Reward Shaping (PBRS): como exploramos e por que pivotamos**

### Conclusao (topo do slide -- respeita o tempo do avaliador)

Implementamos PBRS "de livro" (Ng, Harada & Russell, 1999) para ensinar os fantasmas a **perseguir** o Pacman *sem* enviesar a politica otima. Um **A/B decisivo** (>=5 seeds) mostrou que, contra um Pacman evasor "hard", o PBRS exato soma **~zero** ao longo do episodio -> a politica fica **passiva**. A propria garantia que torna o PBRS "seguro" (invariancia de politica) preservou a passividade que queriamos corrigir. **Duas mudancas destravaram a perseguicao:** (A) o *reward* -- pivo para um *closing reward* persistente; e (B) o **regime de treino** -- mais aleatoriedade no inicio para dar sinal cedo.

### 1. O que e PBRS

- Adiciona um termo de shaping a recompensa: **F = Phi(s') - Phi(s)**.
- Teorema de Ng-Harada-Russell (1999): nessa forma telescopica, a **politica otima nao muda** (policy invariance) -- shaping "seguro", so acelera o aprendizado.
- Nosso potencial: **Phi = -alpha . dist(fantasmas, Pacman)**, com `alpha = 0.7`. Quanto mais perto a equipe, maior Phi (menos negativo).

### 2. Decisoes de design (o "como exploramos")

- **Distancia BFS MEDIA de TODOS os fantasmas** (nao o `min`). Com recompensa de equipe compartilhada, o `min` so da gradiente ao fantasma mais proximo -- os outros estacionam no canto. A **media** recompensa cada fantasma por fechar o cerco -> coordenacao.
- **Telescoping exato (gamma = 1).** A soma no episodio colapsa em `Phi(fim) - Phi(inicio)`, independente do caminho: oscilar no lugar rende **exatamente 0** -> impede "farmar" recompensa indo e voltando.
- **Sinal centralizado (CTDE).** Phi le a posicao real do Pacman em treino; as politicas executadas continuam vendo apenas a visao parcial local.
- Base esparsa: `+100` captura, `-100` timeout / vitoria-por-pellets, `timestep = -0.05`.

### 3. Validacao: A/B decisivo (constituicao Q3: >=5 seeds)

- **Braco PBRS** vs. **controle esparso identico byte-a-byte**, exceto pelo termo de shaping (`CaptureV0SparseControl`). Unica variavel: o shaping.
- Protocolo alinhado ao padrao de benchmarking adotado (Papoudakis 2021 / rliable): eval greedy fixo, metrica de perseguicao alem da taxa de captura.

### 4. Finding honesto (o que NAO funcionou -- e por que)

- Contra um evasor que mantem a distancia ~constante, a variacao liquida de Phi ao longo do episodio ~= 0 -> **recompensa cumulativa de perseguicao ~= 0**.
- Sobra o custo `timestep` + o `-100` de timeout. Licao aprendida pela rede: "perco -100 de qualquer jeito; minimizo o custo por passo" -> **passividade**.
- Bonus: *discount mismatch* -- a invariancia exige `F = gamma.Phi(s') - Phi(s)` com o gamma do learner (0.99); usamos `gamma = 1` para matar o farming por oscilacao. Trocamos invariancia limpa por pressao-de-perseguicao liquida nula.

### 5. Pivo do reward (o que passou a funcionar)

- Substituimos o PBRS por um **closing reward persistente (nao-telescopico)**: paga por **reduzir** a distancia BFS media a cada passo, com *clip* para nao virar orbit-farming.
- Abrimos mao da invariancia do PBRS em troca de um **vies explicito de perseguicao** -- que era exatamente o objetivo.
- Resultado: o IQL passou a perseguir e capturar (ordem de ~70-80% de captura apos ~1M frames), fechando o objetivo de "fazer os fantasmas seguirem o Pacman".

### 6. Setup de treino (novo, no Makefile) -- mais aleatoriedade no inicio

Sozinho, o reward nao basta: contra um evasor perfeito desde o passo 1, a captura (`+100`) quase nunca dispara, entao nem o closing reward tem o que ancorar. A solucao foi **injetar aleatoriedade cedo** no treino, para que capturas e perseguicoes acontecam e virem sinal:

- **Exploration epsilon (epsilon-greedy):** `EPSILON_ANNEAL_RATIO=0.4`, `EPSILON_END=0.05`. As acoes dos fantasmas comecam **100% aleatorias** (`epsilon=1.0`) e caem ao longo do treino -> exploracao maxima no inicio, convergencia gulosa no fim.
- **Pacman ruidoso:** `PACMAN_RANDOM_ACTION_PROB=0.2` -- o Pacman age aleatorio em 20% dos passos, tornando a presa capturavel o suficiente para a captura ancorar a perseguicao (a eval sempre forca um Pacman "hard", por design).
- **Spawns aleatorios:** `RANDOMIZE_SPAWNS=1`, `RANDOMIZE_SPAWNS_MIN_DISTANCE=4` -- posicoes iniciais sorteadas a cada episodio -> a politica nao memoriza uma rota fixa e precisa **perseguir reativamente**.

Efeito conjunto: no comeco o problema e facil e variado (captura acontece), e vai endurecendo conforme `epsilon` cai e a politica melhora -- um curriculo *implicito* que da gradiente de perseguicao desde cedo. (Base de treino: `>=5 seeds`, `1M frames`, reward `capture_v0_closing`.)

---

## Notas para quem apresenta (nao vao no slide)

- **A mensagem de 10 segundos:** "PBRS e teoricamente elegante e seguro, mas essa mesma seguranca (invariancia) o torna cego a um evasor que so mantem distancia; por isso trocamos por um sinal que paga por perseguir."
- **Se perguntarem "por que media e nao minimo":** com reward de equipe, `min` deixa os outros fantasmas sem gradiente; a media faz todos convergirem para o cerco.
- **Se perguntarem "por que gamma=1":** para impedir farmar recompensa oscilando no lugar; o custo foi perder a invariancia exata (que precisa do gamma=0.99 do learner).
- **Se perguntarem "entao o PBRS falhou?":** nao foi desperdicio -- foi um resultado negativo *controlado* (A/B com >=5 seeds) que diagnosticou a causa (net-zero contra evasor) e justificou o pivo. Isso e o rigor que o A/B compra.
- **Ligacao reward <-> setup de treino:** reforce que sao duas mudancas complementares -- o reward diz *o que* recompensar (perseguir), e o setup de treino garante que a perseguicao/captura *aconteca cedo* para haver o que recompensar. Uma sem a outra nao destrava.
- **Se perguntarem "por que Pacman aleatorio se a eval e hard?":** o ruido/exploracao e so no *treino* (bootstrap); a **avaliacao sempre forca um Pacman hard**, entao a taxa de captura reportada nao e inflada por presa facil.
- **Rastreabilidade (constituicao C1):** implementacao em `custom_environment/env/rewards/current.py` (`CaptureV0PurePotentialShaping`); diagnostico em research-000035; A/B em plan-000031; presets de treino no `Makefile` (research-000042 / research-000045).

*Fontes: custom_environment/env/rewards/current.py; Makefile; research-000024, research-000035, research-000042, research-000045; plan-000031.*
