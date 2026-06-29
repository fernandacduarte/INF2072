# QA Log -- plan-000031 | Decisive A/B benchmark: matched sparse control vs PBRS

**Brief:** Executar o benchmark decisivo do estudo de rewards: desenho A/B (esparso vs esparso+PBRS), >=5 seeds conforme constituicao Q3, metrica de perseguicao, framing sample-efficiency. Fonte research-000024 (R5) / research-000028.

---

## Q&A log

### Q1: Como construir o braco de controle (esparso, sem PBRS) para um A/B causalmente limpo?

Descoberta-chave durante o planejamento: os dois reward-ids existentes NAO formam um A/B limpo. `capture_v0` (terminais +45/-40/-45, `timestep -0.015`, + termo denso `pacman_legal_moves_reduced +1.0`) e `capture_v0_pure_potential_shaping` (terminais +/-100, `timestep -0.05`, + PBRS) diferem em quatro fatores, confundindo o efeito do shaping.

**Decisao do usuario:** controle pareado novo. Adicionar `capture_v0_sparse_control` = subclasse de `CaptureV0PurePotentialShaping` reutilizando `CaptureV0PurePotentialShapingWeights` (terminais +/-100, `timestep -0.05` byte-identicos), emitindo tudo menos o termo `potential_shaping`. Assim a unica diferenca entre os bracos e o PBRS.

### Q2: Em qual regime de evasividade rodar o A/B?

**Decisao do usuario:** rodar com 25%, 50% e 75% de aleatoriedade do Pacman -> `--pacman-random-action-prob` em {0.25, 0.50, 0.75}, `--pacman-curriculum off`, `--pacman-difficulty hard`. research-000028 mostrou que `p=0` (totalmente evasivo) arrisca efeito-piso; os tres pontos interiores ficam no regime aprendivel onde a vantagem de sample-efficiency do PBRS e detectavel.

### Q3: O que significa "dificuldade hard"?

A politica do Pacman e uma heuristica determinista "defense-first" (`pacman_policy.py`): prioriza fugir do fantasma mais proximo (distancia BFS limitada por `PACMAN_SAFE_DISTANCE`) e persegue pellets so como desempate. Os niveis (`_difficulty_params`) definem `pure_random`, ruido padrao e `safe_distance`:
- easy: `pure_random=True`, safe_distance=1 -> 100% aleatorio;
- medium: `pure_random=False`, safe_distance=2, ruido 0.30;
- hard: `pure_random=False`, safe_distance=`PACMAN_SAFE_DISTANCE` (=3) -> evasor mais esperto.

**Sutileza:** com `--pacman-curriculum off`, `_build_pacman_policy` substitui o ruido padrao da dificuldade por `--pacman-random-action-prob` (nosso `p`). Logo `hard` so fixa `pure_random=False` + `safe_distance=3`; o `p` e o unico eixo que varia (fracao de passos aleatorios). safe_distance constante = sem confundir profundidade de planejamento.

### Decisoes de design (resumo)

- Metrica de perseguicao `pursuit_fraction` (fracao de passos em que a distancia BFS da equipe ao Pacman diminui) -- capture_rate sozinho nao distingue "aprendeu a perseguir" de "vagueia".
- Headline = sample-efficiency (AULC / frames-to-threshold), NAO capture_rate assintotico (PBRS e policy-invariant por construcao).
- Reusa `run_benchmark.py` (subprocess) e o seed-pin compartilhado com plan-000029.
- Review profundo (deep): adicionou Step 0 (.gitignore/provenance C1), reforcou o threading da metrica de perseguicao no CSV by-variant, e corrigiu as chamadas do loader.

---

*Plan: plan-000031.md (Review: deep). Source: research-000024.*
