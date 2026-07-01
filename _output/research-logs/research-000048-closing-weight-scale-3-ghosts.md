# Research 000048 | fernanda-INF2072 | 2026-07-01 13:31 UTC | closing_weight scale calibration for 3 ghosts (pinklike3)

tags: reward-shaping, marl-credit-assignment, reproducibility, experimental-validity, capture-v0-closing

## User Brief

A closing reward `CaptureV0ClosingReward` usa `closing_weight=2.0` com um comentario que diz compensar a escala "halved (2 ghosts)", mas o maze default agora e `pinklike3` (3 fantasmas). Com a distancia mean-BFS sobre N fantasmas, fechar 1 celula reduz a distancia rastreada por 1/N, entao a escala do sinal de closing depende de N (1/2 para 2 ghosts, 1/3 para 3 ghosts). A calibracao de `closing_weight=2.0` esta correta/intencional para o default de 3 fantasmas? O sinal de closing esta sub ou superponderado em relacao aos terminais +100/-100, ao timestep -0.05 e ao termo de containment 0.5? Isso importa para o resultado de ~80% de captura do IQL e para o benchmark final?

## Agent Interpretation

Analisar quantitativamente como a escala do termo de closing (`closing_weight * clip(prev_mean - cur_mean, -clip, +clip)`, com `mean` sobre a distancia BFS dos fantasmas alcancaveis) depende do numero N de fantasmas; verificar se `closing_weight=2.0` -- calibrado originalmente para N=2 -- permanece adequado sob o default atual `pinklike3` (N=3); avaliar o balanco do sinal contra os demais termos do reward; e determinar o impacto pratico sobre o resultado observado (~80% de captura do IQL) e sobre a validade do benchmark final IQL/VDN/QMIX. As conclusoes abaixo passaram por um `research-reviewer` adversarial, que corrigiu varios pontos da analise inicial (ver Q&A).

## Files Reviewed

- `custom_environment/env/rewards/current.py` -- `CaptureV0ClosingReward` (linhas 872-994), `CaptureV0ClosingRewardWeights` (872-890); comentario obsoleto em 882-883 e docstring 914; `_mean_distance` sobre alcancaveis (937-950); `compute` (952-994).
- `custom_environment/env/pacman_environment.py` -- broadcast do reward compartilhado (linhas 430-432: `rewards[ghost.id] = float(team_reward)`).
- `custom_environment/utils.py` -- `PINKLIKE_LAYOUT` (2 'G', linha 151) vs `PINKLIKE_LAYOUT3` (3 'G', linha 194); registro de mazes (290-294).
- `Makefile` -- `MAZE ?= pinklike3`, `REWARD_ID = capture_v0_closing`.
- git `ae4da68` -- troca de default `pinklike` -> `pinklike3` acoplada a "adiciona nova classe de reward".

---

## Q&A Log

### Q1: `closing_weight=2.0` esta calibrado para o default de 3 fantasmas? O sinal esta sub/superponderado? Importa para o ~80% e para o benchmark final?

**Resposta curta:** O valor `2.0` **NAO** esta calibrado para 3 fantasmas -- o comentario e a docstring assumem explicitamente N=2, e sob N=3 o sinal de closing por passo que o IQL efetivamente consome fica **~33% mais fraco** do que o pretendido (0.667 em vez de 1.0 por fantasma que fecha 1 celula). Isso e uma **subponderacao leve, real** (nao apenas um comentario obsoleto), mas **nao quebra** o resultado: o ~80% e evidencia de que o valor atual funciona bem o suficiente. Para o benchmark final, o `closing_weight` **nao** e o maior risco -- os riscos dominantes sao (a) consistencia de maze entre seeds e (b) vies na comparacao entre algoritmos, ambos detalhados abaixo.

---

#### 1. Mecanica da escala (por que depende de N)

O reward e um **escalar de equipe unico**, transmitido identico a todos os fantasmas (`pacman_environment.py:430-432`). O termo de closing e:

```
closing = closing_weight * clip(prev_mean - cur_mean, -closing_clip, +closing_clip)
```

com `closing_weight = 2.0`, `closing_clip = 2.0`, e `mean` = distancia BFS media sobre os fantasmas **alcancaveis**.

- **Um fantasma fecha 1 celula (demais parados):** `delta_mean = 1/N` -> closing = `2.0/N`.
  - N=2 -> **1.0**; N=3 -> **0.667** (~33% abaixo do alvo de calibracao original).
- **Todos os N fantasmas fecham 1 celula (coordenado):** `delta_mean = 1.0` -> closing = **2.0** (independente de N). Nota: 2.0 e exatamente o teto do clip -- qualquer passo em que a media caia mais de 1.0 celula (ex.: Pacman corre para dentro do grupo) e **cortado** e o excesso descartado.

O comentario do codigo (882-883) revela a intencao original: *"mean decrease ~= 0.5 per ghost step vs 1.0 for min... closing_weight=2.0"* -- isto e, com N=2, um fantasma fechando da `delta=0.5`, e `2.0*0.5 = 1.0` para igualar o antigo reward baseado em `min` (peso 1.0). **O alvo de calibracao e N=2.** Para restaurar exatamente esse alvo sob N=3 seria preciso `closing_weight = 3.0` (`3.0 * 1/3 = 1.0`).

#### 2. Por que a subponderacao importa para o IQL (e nao e neutralizada pela "invariancia do somatorio")

A analise inicial argumentava que o **somatorio episodico** do closing telescopa para `2.0 * d0` e seria N-invariante. O `research-reviewer` **refutou** essa defesa em dois pontos:

- **O clip quebra o telescoping.** O somatorio so iguala `2.0*(d0 - d_final)` se nenhum `|delta|` por passo exceder `closing_clip = 2.0`. Mas o clip foi **projetado para atuar** (anti-farming / risco de orbita RC4, research-000022), e o Pacman **move primeiro** a cada passo, dobrando a variacao possivel da distancia num unico passo. Logo o cumulativo e **dependente do caminho** e geralmente `<= 2.0*d0`, nao uma identidade limpa.
- **`d0` e uma media, portanto levemente dependente de N** (a geometria de spawn do 3o fantasma altera a media inicial). "Aproximadamente estavel em escala para uma distribuicao de spawn fixa" e defensavel; "N-invariante" nao e.

E, decisivo: o **IQL bootstrapa no reward de equipe por passo** `r_t`, nao no somatorio episodico. A quantidade que o alvo TD consome e o escalar por passo -- que vale `2.0/N` para o movimento de um unico fantasma. Portanto a diluicao de ~33% em N=3 incide exatamente sobre o sinal que dirige o aprendizado, reduzindo o SNR contra o `timestep = -0.05` e o ruido de clip/reverse. A invariancia do somatorio e real, mas **nao resgata** o SNR por passo. (Isto e a classica diluicao de credito por reward compartilhado: mais agentes -> contribuicao marginal individual menor.)

#### 3. Balanco de magnitude vs os demais termos (corrigido)

Num episodio de `max_steps = 200`:

| Termo | Magnitude | Observacao |
|---|---|---|
| `timestep` | -0.05/passo -> **-10.0** no total | piso de custo |
| `closing` | 0.667 (1 fantasma) ate 2.0 (coordenado, no teto do clip) por passo | **positivo so quando a equipe liquida-fecha**; contra evader perfeito que mantem distancia, soma ~0 (motivacao do design) |
| `pacman_legal_moves_reduced` | +0.5/passo, **sem clip**, quando Pacman visivel e perde saidas | **mesma ordem do closing**; pode acumular dezenas de pontos ao acuar (herding). Omiti-lo subestima o balanco |
| terminais | **+-100** | dominam |

Numa **captura bem-sucedida**, o closing cumulativo fica na ordem de `~2.0 * dist_media_inicial` (~+16..+30 num maze 20x20) -- valor de *episodio de sucesso*, nao um piso. O balanco geral (closing + containment entre `timestep` e os terminais) permanece sensato e a **conclusao de "bem balanceado" sobrevive** -- desde que se conte o containment, que a analise inicial havia omitido.

#### 4. Impacto no ~80% e no benchmark final

- **Sobre o ~80% (IQL, pinklike3, closing_weight=2.0):** o resultado empirico e a verdade de campo. Um ~80% significa que a escala atual **funciona bem o suficiente**, independentemente de 2.0 ser teoricamente otimo. O onus da prova recai sobre uma mudanca, nao sobre o status quo.
- **Riscos reais para o benchmark (maiores que o valor de `closing_weight`):**
  1. **Consistencia de maze entre seeds (reproducibilidade).** O default mudou `pinklike` (2) -> `pinklike3` (3) junto com a classe de reward. Misturar runs de 2 e 3 fantasmas num mesmo agregado e um **confound independente do valor do peso**. Mitigante ja presente: o `run_benchmark.py` recebe um unico `--maze` por invocacao e escreve o summary sob `<save-folder>/<maze>/...` (escopo por maze). O risco remanescente e agregar **entre invocacoes** de mazes diferentes. Verificar antes de rodar.
  2. **Vies na comparacao entre algoritmos.** O IQL (sem fatoracao de valor) e o **mais exposto** a diluicao `1/N` do reward compartilhado; VDN/QMIX fatoram o valor e interagem de forma diferente com a escala. Como o proposito do benchmark e exatamente comparar IQL vs VDN vs QMIX, um reward cuja intensidade efetiva por agente escala com N pode **enviesar a propria comparacao** que se quer medir.
- **Bug latente de correcao (ortogonal ao peso):** `mean` e sobre fantasmas **alcancaveis**, entao `prev_mean` e `cur_mean` podem ser calculados sobre **denominadores diferentes** em passos consecutivos quando um fantasma fica isolado (alcancavel -> filtrado), injetando um `delta` espurio nao relacionado a movimento. Vale corrigir independentemente da questao de calibracao.

#### 5. Reconciliacao de documentacao

O `standards.md` referencia `custom_environment/pacman_env.py`, que **nao existe** -- o arquivo real e `custom_environment/env/pacman_environment.py`. Drift de documentacao a corrigir.

---

## Recommendations Summary

| # | Prioridade | Recomendacao |
|---|-----------|--------------|
| R1 | **HIGH** | **Verificar (pre-benchmark, bloqueante) que todos os seeds usam `pinklike3`.** Nao misturar runs de 2 e 3 fantasmas num mesmo agregado -- confound de reproducibilidade independente do peso. Custo zero (checar `--maze` e a pasta `<save-folder>/<maze>/`). |
| R2 | **MEDIUM** | **Nao alterar `closing_weight` antes do benchmark atual.** A ~80% e o baseline; mudar o peso invalida-o e viola a regra de nao misturar capture rates pre/pos-mudanca (constitution Q3 / D-003). |
| R3 | **MEDIUM** | **Tratar `closing_weight` como hyperparameter a varrer, em estudo separado.** Para restaurar a calibracao N=2 sob N=3, o valor equivalente e `3.0`. Fazer um A/B `2.0` vs `3.0` em `pinklike3` seguindo D-003 (>=5 seeds, IQM+CI), em vez de assumir. |
| R4 | **MEDIUM** | **Documentar/mitigar o vies entre algoritmos.** IQL e o mais exposto a diluicao `1/N`; VDN/QMIX menos. Declarar isso no relatorio e considerar normalizar o closing por N para que a comparacao nao seja confundida pela contagem de fantasmas. |
| R5 | **MEDIUM** | **Corrigir o bug latente de denominador de `mean`** (fantasmas alcancaveis variando entre passos injeta delta espurio): usar N fixo (com distancia-sentinela para inalcancaveis), fixar o denominador por episodio, ou suprimir o termo no passo em que o conjunto alcancavel muda. |
| R6 | **LOW** | **Corrigir os comentarios obsoletos** (`current.py:882-883` e docstring `914`, ambos "halved (2 ghosts)") e o drift de nome de arquivo em `standards.md` (`pacman_env.py` -> `env/pacman_environment.py`). Risco zero (so texto). |
| R7 | **LOW** | **Tornar a escala robusta a trocas de maze:** amarrar `closing_weight` a contagem de fantasmas (ex.: escala por N) ou normalizar o `delta` por `1/N`, decidindo explicitamente se a diluicao de fantasma unico e desejada (favorece aproximacao coordenada) ou nao (credito individual mais rapido). |

## Sources

- Codigo do projeto: `custom_environment/env/rewards/current.py`, `custom_environment/env/pacman_environment.py`, `custom_environment/utils.py`.
- research-000035 -- diagnostico da passividade sob PBRS e alavancas L2 (closing reward) / L3 (3o fantasma).
- research-000022 -- risco de orbita RC4 (motivacao do clip).
- D-003 / constitution Q3 -- padrao de benchmarking (>=5 seeds, IQM+CI; nao misturar capture rates pre/pos-mudanca).
- Ng, Harada & Russell (1999) -- por que o closing e deliberadamente NAO potential-based (nao telescopa).
