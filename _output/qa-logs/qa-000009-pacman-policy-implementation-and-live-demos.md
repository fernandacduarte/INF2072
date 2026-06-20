# QA 000009 | 2026-06-20 14:29 UTC | Pacman policy implementation and live demos

**Brief:** Pesquisa, planejamento, implementação e verificação visual ao vivo da `PacmanPolicy` determinística (defense-first) — Pacman que sobrevive aos fantasmas e limpa o tabuleiro de pellets.

---

## Q1
`/research` — algoritmo do Pacman: usa pathfinding (A*) para maximizar ganho de pellets, penalizando caminhos com potencial de encontrar fantasmas; recalcula rota para o ponto mais seguro ao detectar colisão potencial e então redispara a maximização de pellets com máxima segurança.

## A1
Produzi a pesquisa **research-000006**. Conclusões principais:
- **BFS (hard exclusion)** é o algoritmo correto, não A* — em grid de custo uniforme, A* reduz a BFS com overhead de heurística.
- **Flood-fill único** O(R×C) em vez de um BFS por pellet.
- Modelagem de zona de perigo com `PACMAN_DANGER_RADIUS`; máquina de estados `SEEKING_PELLET → FLEEING → COOLDOWN`.
- Alerta de **curriculum shock**: treinar fantasmas do zero contra um Pacman ótimo pode colapsar o sinal de RL.
Lançado o agente `research-reviewer` (review depth standard). Relatório commitado.

## Q2
"mas eh isso que eu quero. eu estou competindo contra os fantasmas" / "foda-se os fantasmas" / "Pacman must survive"

## A2
Esclareci o objetivo: o Pacman é o agente principal e precisa **sobreviver** contra os fantasmas RL. Mantida a estrutura (fantasmas = RL), substituindo apenas o Pacman aleatório por uma política determinística focada em sobrevivência.

## Q3
"sure, go ahead my friend" — gerar o plano.

## A3
Gerei o **plan-000007** (`/plan`, review light, 4 steps): adicionar `PACMAN_DANGER_RADIUS` em `constant.py`; criar `PacmanPolicy` (BFS flood-fill + máquina de estados); conectar em `pacman_environment.py:197`; smoke test. Plano commitado.

## Q4
(via AskUserQuestion) "Implement now" + troca de modelo para Opus.

## A4
Executei `/implement 000007` em modo manual (4/4 steps). Criados `pacman_policy.py` e `test/test_pacman_policy.py`; modificados `constant.py` e `pacman_environment.py`. Verificação: 12/12 testes executáveis passam; PettingZoo `parallel_api_test` (1000 ciclos) passa. **Detalhe de ambiente:** o `.venv` tem numpy/pettingzoo/gymnasium/pygame mas **não tem pytest nem pip** — testes rodados chamando as funções diretamente. Commitado + as-coded alignment.

## Q5
"como eu testo?" / "como vejo o jogo rodando" / "como eu faco pra executar o jogo no pygame"

## A5
Expliquei as formas de testar: (1) demo ASCII no terminal sem dependências; (2) janela Pygame `--render-mode human`; (3) suíte de testes (com aviso de que pytest não está instalado no `.venv`). Forneci os comandos exatos via `.venv\Scripts\python.exe` e via `py -3.11`, incluindo troubleshooting de `ExecutionPolicy`.

## Q6
"executa" / "quero ver" — rodar o jogo de fato.

## A6
Expliquei por que não consigo abrir a janela interativa do Pygame de forma visível (shell não-interativo, janela abriria no meu contexto sem display visível, `wait_for_close` trava o tool). Entreguei artefatos visuais: PNGs renderizados (headless via `SDL_VIDEODRIVER=dummy`) e um **GIF animado** de um episódio completo. Mostrei 3 frames (start/meio/fim) evidenciando o Pacman mantendo distância dos fantasmas.

## Q7
"pq diabos vc nao consegue abrir a janela do pygame?"

## A7
Respondi os 3 motivos somados: (1) terminais não-interativos sem display visível para o usuário; (2) `wait_for_close` em loop infinito trava o tool; (3) sem acesso ao desktop do usuário. Estratégia: gerar artefatos que ele abre.

## Q8
"executa" (novamente, insistindo na janela ao vivo).

## A8
Lancei `render_demo.py --render-mode human` **em background** (`run_in_background`) — descobri que a janela **de fato aparece na tela do usuário** quando rodada assim. Primeira run (policy seek-pellet original): **Ghosts win** — Pacman capturado no step 35.

## Q9
"po, mas perdeu" / "faca a ai priorizar a defesa (fugir dos fantasmas) e em segundo plano maximizar a captura de pellets" / "quero executar de fato"

## A9
A `PacmanPolicy` foi revisada para **defense-first**: scoring lexicográfico stateless `(safety, pellet_progress)` via dois multi-source BFS (de todos os fantasmas e de todos os pellets); `PACMAN_DANGER_RADIUS = 3` substituído por `PACMAN_SAFE_DISTANCE = 5`; sobrevivência domina estritamente a coleta de pellets. Relançado ao vivo: **Pacman wins** — sobreviveu 200/200 steps.

## Q10
"denovo" / "de novo que eu curti" / "de novo, mto divertido"

## A10
Rodei várias demos ao vivo da versão defense-first:
- 2 fantasmas, 200 steps → **Pacman wins** (sobreviveu).
- seed 11, defense-first → **Pacman wins** (sobreviveu).
- `--number-ghosts 4` (ignorado; mapa pinklike define 2 spawns) → **Pacman wins**.

## Q11
"roda de novo... deixe rodar ate consumir todos os pellets"

## A11
Verifiquei headless que o defense-first **zera todos os 161 pellets** (283-572 steps, nunca capturado). Criei `run_until_clear.py` (eleva o `max_steps` de 200) e rodei ao vivo:
- seed 11 → **Pacman wins, 161/161 pellets** em 377 steps.
- seed 42 → **Pacman wins, 161/161** em 420 steps.
- seed 99 (delay 0.08) → lançado.

## Q12
"finalize a skiill e salve qa-log"

## A12
Invoquei `/qa-log` e gerei este registro (qa-000009).

---

## Notas técnicas relevantes para sessões futuras

- **Ambiente:** usar `g:\NAS\ANDREY\puc\doutourado\2026.1\INF2072\fernanda-INF2072\.venv\Scripts\python.exe`. Tem numpy 2.4.5, pettingzoo, gymnasium, pygame-ce 2.5.7, Pillow 12.2.0 — **mas não tem pytest nem pip**. Para rodar testes sem pytest: importar as funções `test_*` e chamá-las direto.
- **Janela Pygame ao vivo:** lançar `render_demo.py --render-mode human` com `run_in_background: true` faz a janela aparecer na tela do usuário; sem background, `wait_for_close` trava.
- **Render headless:** `SDL_VIDEODRIVER=dummy` + `env.capture_frame(...)` para PNG/GIF.
- **Truncação:** o ambiente trunca em `env.max_steps = 200`; para limpar o tabuleiro inteiro, elevar `env.max_steps` após criar o env.
- A `PacmanPolicy` final é **defense-first stateless** (ver `pacman_policy.py` e a entrada de as-coded). Trabalho posterior (plan-000008) mediu o baseline IQL em 0% de win rate contra esse Pacman.
