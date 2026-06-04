# Copilot Instructions

## Projeto
- Este repositorio contem um ambiente Pacman multiagente com PettingZoo e integracao com BenchMARL.
- Algoritmos principais: IQL, VDN e QMIX.
- Script de treino principal: `benchmarl_setup/run_pacman_benchmarl.py`.
- Script de avaliacao principal: `custom_environment/eval.py`.

## Regras de edicao
- Preserve observacao local dos fantasmas (visao 3x3).
- Compartilhamento permitido entre fantasmas: apenas ultima posicao avistada do Pacman e passo do avistamento.
- Evite mudancas grandes sem necessidade; prefira patches pequenos e focados.
- Nao quebre CLI existente sem atualizar `README.md`.
- Sempre que alterar comportamento (recompensa, treino, avaliacao, flags), atualize `README.md`.
- Todos os comentarios em codigo devem ser escritos em ingles.

## Sistema de recompensa (diretriz)
- O reward e compartilhado por time (um escalar por passo para todos os fantasmas).
- Preserve os termos de recompensa e penalidade documentados no `README.md`.
- Evite criar caminhos para farming de reward (ex.: flicker de visibilidade, loops de reversao).
- Se adicionar novo termo, inclua no `reward_breakdown` e documente no `README.md`.

## Treino e avaliacao
- Treino deve suportar parametros por CLI e checkpoint ao final.
- Avaliacao deve permitir escolher checkpoint `best` ou `latest`.
- Em diagnostico, manter opcao para imprimir `reward_breakdown` por passo.

## Qualidade e validacao
- Antes de finalizar uma mudanca, verificar erros de sintaxe/import nos arquivos alterados.
- Se possivel, validar com um ciclo curto de treino/eval ou ao menos conferir caminhos e argumentos.
- Ao criar novos scripts utilitarios, documentar uso no `README.md` com exemplos de comando.
