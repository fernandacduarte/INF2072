# QA Log | plan-000057 | 2026-07-02 12:00 UTC | Junção PBRS + capture_v0_closing

## Brief

como seria a junção do pbrs da politica de reward atual ?

## Q&A Log

**Q1 (agent -> user)**: Plano plan-000057 (junção PBRS + capture_v0_closing) gerado e revisado. O que fazer agora? (Implement now / Commit plan / Revise plan)

**A1 (user)**: Revise plan -- com a diretiva: "vamos fazer uma rodada mais simples possivel, talvez testar em um maze menor com menos rodadas. quero executar em 15 min no máximo. 1 seed só para ver o potencial".

**Resolução**: Plan Amendment (iteration 1) -- adicionados Step 6 (pilot: 1 seed, 100k frames, ~14 min medidos no run 2883b22f) e Step 7 (comparação de capture-rate por checkpoint vs baseline pareado capture_v0_closing de 100k frames). Sobre "maze menor": não existe maze menor no registry (default/pinklike/pinklike3, todos 20x20); o teto de 15 min é atingível no próprio pinklike3, o que preserva comparabilidade com o baseline existente.

**Q2 (agent -> user)**: Plano emendado com o pilot de ~14 min (1 seed, 100k frames) + leitura vs baseline. Executar agora? (Implement now / Commit plan / Revise plan)

**A2 (user)**: Implement now.

## Notes

- Near-colinearidade documentada no plano: com gamma=1, o termo PBRS equivale a um closing sem clip de peso alpha (0.7); dentro do clip a junção = closing_weight efetivo 2.7. O A/B isola o componente extra não-clipado e policy-invariant.
- Pilot de 1 seed é exploratório e não-reportável (constituição Q3 exige >=5 seeds).
