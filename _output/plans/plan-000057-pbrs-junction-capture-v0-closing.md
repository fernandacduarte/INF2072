# Plan 000057 | FEATURE-B | 2026-07-02 11:51 | Junção PBRS + capture_v0_closing | Review: light
plan_format_version: 1

## User Brief

como seria a junção do pbrs da politica de reward atual ?

## Agent Interpretation

**Problem**: O projeto tem duas famílias de shaping por distância que hoje são mutuamente exclusivas -- o PBRS telescópico puro (`capture_v0_pure_potential_shaping`, policy-invariant mas que anula ~zero contra um Pacman evasivo) e o closing persistente atual (`capture_v0_closing`, viés de perseguição explícito, ~80% de captura com IQL). O brief pergunta como seria a junção das duas: um variant que mantenha a política de reward atual e reintroduza o termo PBRS por cima.

**Approach**: Criar um novo strategy `capture_v0_closing_pbrs` (classe `CaptureV0ClosingPBRS`) que herda `CaptureV0ClosingReward` inalterado -- mesmos pesos de closing/containment/terminais/timestep, seguindo o padrão de isolamento A/B já usado por `CaptureV0ClosingShaped` -- e adiciona o termo PBRS `F = Phi(s') - Phi(s)` com `Phi = -alpha * meanBFS` (alpha=0.7, o mesmo do variant puro) e telescoping exato (gamma=1, escolha empírica anterior que evita farming por oscilação). A mesma métrica mean-BFS já computada pelo closing é reaproveitada (zero BFS extra por passo).

Nota de honestidade matemática que o plano torna explícita (docstring + teste dedicado): com gamma=1, `F = alpha * (d_prev - d_cur)` -- ou seja, o termo PBRS é exatamente um "closing" **sem clip** de peso alpha. Dentro de `|delta| <= closing_clip` a junção equivale a subir `closing_weight` de 2.0 para 2.7; fora do clip, o PBRS continua pagando proporcionalmente e, cumulativamente, o componente PBRS soma `Phi(end) - Phi(start)` (invariante de política) enquanto o componente closing carrega o viés persistente de perseguição. O A/B contra `capture_v0_closing` isola, portanto, o efeito do gradiente extra não-clipado e policy-invariant -- e não "PBRS vs closing", que já foi decidido (research-000035).

## Files

- `custom_environment/env/rewards/current.py` (modify) -- seam no `CaptureV0ClosingReward` + novo variant
- `custom_environment/env/rewards/loader.py` (modify) -- registro do id `capture_v0_closing_pbrs`
- `test/test_closing_pbrs_reward.py` (create) -- testes do variant combinado

## Best Practices

- Padrão de isolamento A/B do projeto: pesos-base idênticos ao arm de controle para que a única variável seja o termo adicionado (mesmo racional de `CaptureV0SparseControl` e `CaptureV0ClosingShaped`).
- PBRS na forma Ng/Harada/Russell (1999); gamma=1 (telescoping exato) conforme falha empírica documentada no docstring de `CaptureV0PurePotentialShaping` (gamma<1 paga `(1-gamma)*(-Phi)` por ciclo de vai-e-vem, que a política greedy farmava).
- Sinal centralizado de treino (CTDE): distâncias leem a posição verdadeira do Pacman; as políticas dos fantasmas seguem observando só a visão local.
- Constituição Q1 (todo termo aparece no breakdown auditável via `RewardTerm`), Q2 (suite de testes passa antes de commit), T4 (nenhuma seed hardcoded -- o variant é só função de reward).
- Reuso de computação: uma única passada de BFS por passo alimenta closing e PBRS.

## Steps

### Step 1: Expor a distância média do passo em CaptureV0ClosingReward
Em `CaptureV0ClosingReward` (`custom_environment/env/rewards/current.py`), armazenar a mean-BFS calculada em `compute()` num atributo `self._step_mean_distance: float | None` (None quando nenhum fantasma alcança o Pacman), inicializado em `__init__` e limpo em `reset()`. Nenhuma mudança de comportamento -- é só um seam para subclasses reaproveitarem a distância do passo corrente sem refazer BFS.
- **Files**: custom_environment/env/rewards/current.py (modify)
- **References**: project/standards.md § Backend
- **Interface**: `CaptureV0ClosingReward._step_mean_distance: float | None` -- setado a cada `compute()` com a mean-BFS do passo (None se inalcançável)
- **Verify**: `py -3.11 -m pytest test/test_closing_reward.py` passa sem alteração nos testes
- **Tests**: coberto pelos testes existentes de `test/test_closing_reward.py` (sem mudança de comportamento) e pelos novos testes do Step 4
- [ ] Done

### Step 2: Adicionar CaptureV0ClosingPBRSWeights e CaptureV0ClosingPBRS
Em `custom_environment/env/rewards/current.py`, criar dataclass `CaptureV0ClosingPBRSWeights` copiando verbatim os campos de `CaptureV0ClosingRewardWeights` (get_pacman=100, pacman_timeout_win=-100, pacman_win_pellets=-100, timestep=-0.05, closing_weight=2.0, closing_clip=2.0, pacman_legal_moves_reduced=0.5) mais `potential_shaping_alpha: float = 0.7`. Criar `CaptureV0ClosingPBRS(CaptureV0ClosingReward)` com `strategy_id = "capture_v0_closing_pbrs"`:
- `compute()`: chama `super().compute(context)`; lê `self._step_mean_distance`; se não-None, `potential = -alpha * dist`; se `self._last_potential is not None`, anexa `RewardTerm("potential_shaping", potential - self._last_potential)`; atualiza `_last_potential`. Quando a distância é None, não emite termo nem atualiza o potencial.
- `reset()`: chama `super().reset()` e limpa `self._last_potential = None`.
- Docstring: registrar (a) gamma=1 telescoping exato e por quê; (b) a near-colinearidade -- com gamma=1 o termo PBRS é um closing sem clip de peso alpha; dentro do clip a junção equivale a closing_weight efetivo 2.7; o A/B contra `capture_v0_closing` isola o componente extra não-clipado e policy-invariant; (c) sinal CTDE de treino (lê posição verdadeira do Pacman).
- **Files**: custom_environment/env/rewards/current.py (modify)
- **References**: project/standards.md § Backend
- **Depends on**: Step 1
- **Interface**: `CaptureV0ClosingPBRS(CaptureV0ClosingReward)`, `strategy_id = "capture_v0_closing_pbrs"`, construível sem argumentos; emite termos `closing` e `potential_shaping` no mesmo passo
- **Verify**: `py -3.11 -m pytest test/test_closing_pbrs_reward.py` (Step 4) passa
- **Tests**: Step 4 (comportamento observável: fechar 1 célula emite closing=+2.0 e potential_shaping=+0.7)
- [ ] Done

### Step 3: Registrar o id no loader
Em `custom_environment/env/rewards/loader.py`, adicionar em `_REWARD_CLASS_BY_ID` a entrada `"capture_v0_closing_pbrs": "custom_environment.env.rewards.current:CaptureV0ClosingPBRS"`, mantendo a ordem/estilo das entradas vizinhas.
- **Files**: custom_environment/env/rewards/loader.py (modify)
- **References**: project/standards.md § Backend
- **Depends on**: Step 2
- **Interface**: `reward_class_from_id("capture_v0_closing_pbrs")` retorna o class-path do novo variant
- **Verify**: `py -3.11 -c "from custom_environment.env.rewards.loader import reward_class_from_id; print(reward_class_from_id('capture_v0_closing_pbrs'))"` imprime o class-path
- **Tests**: Step 4 inclui teste de resolução do id via loader
- [ ] Done

### Step 4: Testes do variant combinado
Criar `test/test_closing_pbrs_reward.py` espelhando o harness de corredor 1xN de `test/test_closing_reward.py` (BFS = |diferença de coluna|). Casos, todos com `pacman_visible=False` para isolar os termos de distância:
1. `test_registered_id_resolves` -- `reward_class_from_id("capture_v0_closing_pbrs")` resolve e `load_reward_strategy` retorna instância de `CaptureV0ClosingPBRS`.
2. `test_both_terms_emitted_on_closing` -- fechar 1 célula emite `closing = +1*closing_weight (=2.0)` E `potential_shaping = +1*alpha (=0.7)` no mesmo `compute()`.
3. `test_pbrs_telescopes_over_path` -- num trajeto multi-passo (ex.: colunas 10 -> 9 -> 10 -> 8), a soma dos termos `potential_shaping` é `alpha * (d_inicial - d_final)` independente da rota (= 0.7*2), enquanto a soma dos `closing` também neta o líquido do trajeto -- documenta o telescoping.
4. `test_oscillation_nets_zero_on_both_terms` -- vai-e-vem em torno da mesma célula neta ~0 tanto em `closing` quanto em `potential_shaping` (tolerância 1e-9).
5. `test_large_jump_clips_closing_but_not_pbrs` -- salto de 19 células: `closing` clipado em `closing_clip*closing_weight (=4.0)`, `potential_shaping` paga o delta cheio (`0.7*19`) -- documenta o componente não-clipado da junção.
6. `test_reset_clears_potential_state` -- após `reset()`, o primeiro `compute()` não emite `potential_shaping` (baseline novo).
- **Files**: test/test_closing_pbrs_reward.py (create)
- **References**: project/standards.md § Testing
- **Depends on**: Step 3
- **Interface**: N/A
- **Verify**: `py -3.11 -m pytest test/test_closing_pbrs_reward.py` passa (6 testes)
- **Tests**: este step cria os testes
- [ ] Done

### Step 5: Suite completa (constituição Q2)
Rodar `py -3.11 -m pytest test/` e confirmar que toda a suite passa (nenhuma regressão nos variants existentes, em especial `test_closing_reward.py`, `test_reward_strategies.py`, `test_reward_ab.py`, `test_reward_calibration.py`).
- **Files**: test/ (read-only)
- **References**: project/standards.md § Testing
- **Depends on**: Step 4
- **Interface**: N/A
- **Verify**: exit code 0 na suite completa
- **Tests**: N/A (execução da suite, sem código novo)
- [ ] Done

### Step 6: Pilot exploratório de ~14 min (1 seed, 100k frames)
Rodar o treino-piloto do variant combinado no maze padrão:

```
make benchmark ALGOS=iql SEEDS=0 FRAMES=100000 REWARD_ID=capture_v0_closing_pbrs CHECKPOINT_INTERVAL=5000
```

Dimensionamento medido nesta máquina (CUDA): o run existente `iql_pacman_mlp__2883b22f_26_06_30-19_40_55` (capture_v0_closing, pinklike3) treinou 100k frames em ~13m44s (19:40:55 -> 19:54:39), gerando checkpoint e capture-rate greedy a cada 5k frames automaticamente. 100k frames cabe no teto de 15 min; se a máquina estiver ocupada, reduzir para `FRAMES=60000` (precedente R1_FRAMES). Manter pinklike3 (nenhum maze menor existe no registry; ficar no mesmo maze preserva a comparabilidade direta com o baseline). Este pilot é exploratório -- 1 seed NÃO é reportável (constituição Q3 exige >=5 seeds para resultados citados).
- **Files**: benchmarl_setup/runs/pinklike3/capture_v0_closing_pbrs/ (output gerado; nenhum fonte modificado)
- **References**: project/constitution.md (Q3 -- pilot não-reportável)
- **Depends on**: Step 5
- **Interface**: N/A
- **Verify**: run dir criado em `benchmarl_setup/runs/pinklike3/capture_v0_closing_pbrs/cuda/`, com `checkpoints/` e `evaluation_report_live_capture_checkpoint_*.csv`, sem exceções no stdout
- **Tests**: N/A (execução de treino, sem código novo)
- [ ] Done

### Step 7: Leitura rápida do potencial vs baseline
Comparar a curva de capture-rate por checkpoint do pilot (Step 6) contra o baseline pareado já existente `benchmarl_setup/runs/pinklike3/capture_v0_closing/cuda/iql_pacman_mlp__2883b22f_26_06_30-19_40_55` (capture_v0_closing, mesmos 100k frames, mesmo maze): ler os `evaluation_report_live_capture_checkpoint_*.csv` de ambos os runs e tabular capture-rate em 25k/50k/75k/100k lado a lado. Registrar um veredito de 1 parágrafo (sinal promissor / neutro / pior que o baseline) na seção `## Reflection` deste plano. A decisão de escalar para o benchmark completo de 5 seeds fica com o pesquisador.
- **Files**: benchmarl_setup/runs/pinklike3/ (read-only), _output/plans/plan-000057-pbrs-junction-capture-v0-closing.md (append Reflection)
- **References**: project/constitution.md (Q3)
- **Depends on**: Step 6
- **Interface**: N/A
- **Verify**: tabela comparativa apresentada ao usuário e veredito registrado no plano
- **Tests**: N/A (análise de resultados)
- [ ] Done

## Review Log

**Review depth:** Light
**Deep-dive budget:** 0/6 used

Depth resolution: auto=light (5 action steps, 3 arquivos), floor=light (MINIMUM_REVIEW_DEPTH), flag=none -> effective light. Phase 1 only.

### Phase 1 -- Perspective Scan (2026-07-02 11:51 UTC)

Shortlist FEATURE-B: SEC, DB, API, ARCH, TEST, PERF. Adicionada DX: variants de reward são artefatos de pesquisa lidos por terceiros (relatório do curso), então a legibilidade do docstring sobre a near-colinearidade importa.

| Perspective | Status | Concern |
|-------------|--------|---------|
| SEC | N/A | Sem novas entradas externas; id validado pelo regex existente do loader |
| DB | N/A | Sem banco de dados |
| API | N/A | Sem API web; interface `RewardStrategy` intocada |
| ARCH | Adopted | Subclasse segue o padrão de variants existente; seam `_step_mean_distance` evita refazer BFS e mantém o acoplamento dentro do mesmo módulo |
| DX | Adopted | Docstring do Step 2 registra gamma=1, near-colinearidade e o que o A/B isola |
| TEST | Adopted | Step 4 espelha o harness existente e cobre telescoping, clip assimétrico e reset |
| PERF | Adopted | Uma única passada de BFS por passo alimenta closing e PBRS (Step 1) |
| UX / A11Y / VIS / RESP / MICRO / I18N / OPS / COMPAT / DATA | N/A | Fora do shortlist; CLI de pesquisa sem superfície de UI |

### Conflict Check (iteration 1)

No inter-perspective conflicts detected.

### Execution Metrics

| Metric | Value |
|--------|-------|
| Deep-dives used | 0/6 |
| Iterations completed | 1/3 |
| Perspectives shortlisted | 7 |
| Perspectives Adopted | 4 |
| Perspectives Deferred (with rationale) | 0 |
| Convergence reason | all resolved (Phase 1 only, Light) |

### Plan Amendment (iteration 1)

**Trigger**: revisão solicitada pelo usuário -- "vamos fazer uma rodada mais simples possivel, talvez testar em um maze menor com menos rodadas. quero executar em 15 min no máximo. 1 seed só para ver o potencial".

**Change**: adicionados Step 6 (pilot de treino: 1 seed, 100k frames, ~14 min) e Step 7 (comparação rápida de capture-rate por checkpoint contra o baseline pareado de capture_v0_closing).

**Rationale**:
- Sobre "maze menor": não existe maze menor no registry (`custom_environment/utils.py::MAZES` tem apenas default/pinklike/pinklike3, todos 20x20); criar um seria escopo novo e quebraria a comparabilidade com todos os runs existentes. O teto de 15 min é atingível no próprio pinklike3: medido, 100k frames = ~13m44s nesta máquina (run 2883b22f).
- Bônus de desenho: o run `2883b22f` é exatamente um pilot de 100k frames de `capture_v0_closing` no mesmo maze -- serve de braço de controle pareado para a leitura de potencial sem custo adicional.
- Limite de validade explícito: 1 seed é exploratório; qualquer claim reportável continua exigindo o benchmark de >=5 seeds (constituição Q3), que permanece fora dos steps deste plano.
- Complexity gate re-checado: 7 action steps -> depth auto sobe para Standard pela contagem de steps; porém Steps 6-7 são execução/análise (nenhum arquivo-fonte novo, continua em 3 arquivos de código). Mantido Light com esta justificativa registrada; nenhum novo risco de perspectiva (OPS/PERF do treino são os já aceitos pelo pipeline padrão do Makefile).

**Re-avaliação de perspectivas** (steps modificados): TEST -- inalterado (Steps 6-7 não criam código); PERF -- inalterado (pilot usa pipeline existente); ARCH -- inalterado. Nenhuma mudança de status.

## Outcomes

- Novo reward id `capture_v0_closing_pbrs` carregável por todo o pipeline existente (train/benchmark/eval/liveplot) sem mudanças além do registro no loader.
- Benchmark A/B pronto para disparar quando o pesquisador quiser (não é step deste plano -- custo de GPU): `make benchmark ALGOS=iql REWARD_ID=capture_v0_closing_pbrs` com >=5 seeds (constituição Q3), comparando contra os runs existentes de `capture_v0_closing` em `benchmarl_setup/runs/pinklike3/`.
- Interpretação pronta para o relatório: o A/B mede o efeito marginal de reintroduzir o componente telescópico (não-clipado, policy-invariant) sobre a política persistente que já atinge ~0.70-0.80 de captura -- fechando o arco narrativo PBRS -> closing -> junção.
- Decomposição auditável preservada: `potential_shaping` e `closing` aparecem separados no breakdown (Q1), permitindo plotar a contribuição de cada termo.

smoke: false
