# Research 000038 | fernanda-INF2072 | 2026-06-30 18:19 UTC | PBRS vs direct reward shaping

tags: reward-shaping, pbrs, potential-based, capture-v0, reward-function

**User brief:** Minha dúvida é se estamos calculando os shaping rewards só com a técnica do PBRS, ou se estamos somando esses valores direto na função de rewards também

**Agent interpretation:** Verificar se o term `potential_shaping` emitido por `CaptureV0PurePotentialShaping` é o delta `Φ(s') − Φ(s)` (PBRS puro) ou o valor absoluto do potencial `Φ(s')` somado diretamente na recompensa.

**Files consulted:**
- `custom_environment/env/rewards/current.py` — implementação das estratégias de recompensa
- `custom_environment/env/rewards/base.py` — interfaces `RewardResult`, `RewardTerm`
- `custom_environment/env/pacman_environment.py` — consumo do `RewardResult.total`

---

## Q&A Log

**Q1:** Minha dúvida é se estamos calculando os shaping rewards só com a técnica do PBRS, ou se estamos somando esses valores direto na função de rewards também.

**A1:**

Estamos usando **PBRS puro** — o delta `Φ(s') − Φ(s)` é o que entra na recompensa, não o valor absoluto do potencial.

### Código relevante — `CaptureV0PurePotentialShaping.compute()` (current.py:828–849)

```python
mean_distance = self._mean_distance(context)
if mean_distance is not None:
    potential = -w.potential_shaping_alpha * float(mean_distance)   # Phi(s')
    if self._last_potential is not None:
        terms.append(
            RewardTerm("potential_shaping", potential - self._last_potential)  # Phi(s') - Phi(s)
        )
    self._last_potential = potential
```

O que é emitido como `RewardTerm("potential_shaping", ...)` é **`potential − self._last_potential`**, i.e., **`Φ(s') − Φ(s)`**.

Onde `Φ(s) = −alpha × mean_distance`.

O valor absoluto `Φ(s')` **nunca é somado diretamente** — só a variação (delta) entra nos termos de recompensa.

### Como o total chega ao agente

Em `pacman_environment.py:423–424`:

```python
reward_result = self.reward_strategy.compute(reward_context)
team_reward = reward_result.total  # soma de todos os RewardTerm.value
```

O `total` é a soma de:
- `timestep` = −0.05 (todo passo)
- `GET_PACMAN` = +100 (terminal, se capturou)
- **`potential_shaping` = `Φ(s') − Φ(s)`** (PBRS delta, quando distância é mensurável)
- `PACMAN_TIMEOUT_WIN` = −100 (terminal, timeout)
- `PACMAN_WIN_PALLETS` = −100 (terminal, Pacman come todos os pellets)

### Por que importa

| Abordagem | Fórmula | Efeito cumulativo no episódio |
|---|---|---|
| **PBRS puro (o que fazemos)** | `Φ(s') − Φ(s)` | Telescopa para `Φ(terminal) − Φ(inicial)` — independe do caminho |
| **Potencial direto (NÃO fazemos)** | `Φ(s')` a cada passo | Acumula o valor absoluto — recompensa densa, não invariante |

O telescoping garante que oscilações no lugar (fantasma parado perto do Pacman) acumulam exatamente **zero** de shaping ao longo do episódio — o fantasma só ganha shaping de verdade ao fechar distância. Isso é discutido explicitamente no docstring da classe (current.py:782–813): "any in-place oscillation nets exactly zero."

---

## Recommendations Summary

1. **[INFORMATIONAL]** O cálculo atual está correto: é PBRS puro (`Φ(s') − Φ(s)`), não soma direta do potencial. Nenhuma ação necessária.
