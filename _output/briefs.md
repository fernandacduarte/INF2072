# Briefs

Execution log of all skill invocations.

---

STARTED | 2026-07-02 03:53 UTC | communicate | 1 slide HTML com gráfico do resultado do treino, plotando estatísticas dos 5 seeds (benchmark pinklike3 capture_v0_closing) + levantar com UI/UX o que o gráfico precisa ter

DONE | 2026-07-02 03:57 UTC | STARTED | 2026-07-02 03:49 UTC | communicate | to Fernanda e Erick: como foi explorado o potential-based reward shaping (PBRS); 1 slide para apresentar amanhã

DONE | 2026-07-02 03:57 UTC | STARTED | 2026-07-02 03:48 UTC | communicate | 3 slides para falar sobre o necessário para o professor de RL entender o que fizemos

DONE | 2026-07-02 02:36 UTC | STARTED | 2026-07-02 02:30 UTC | communicate | exportar o necessário para colegas reproduzirem a avaliação (make eval-latest / eval.py iql pinklike3 capture_v0_closing, capture_rate=0.70, checkpoint_1000000.pt)

DONE | 2026-07-01 13:36 UTC | STARTED | 2026-07-01 13:31 UTC | research | closing_weight=2.0 esta calibrado para o default de 3 fantasmas (pinklike3)? a escala mean-BFS depende de N (1/2 vs 1/3); sinal de closing sub/superponderado vs terminais/timestep/containment; importa para o ~80% do IQL e o benchmark final?

DONE | 2026-07-01 13:11 UTC | STARTED | 2026-07-01 13:01 UTC | communicate | o trabalho que foi feito aqui nesta branch para meus colegas e professores. quero dividir nas 2 principais etapas: tentativas com potential reward shaping e a nova politica de reward recente, que agora fez o iql ter uma taxa de captura de quase 80% depois de 1M frames

DONE | 2026-07-01 04:10 UTC | STARTED | 2026-07-01 04:05 UTC | research | check current makefile presets. i want to run a full benchmark with the new parameters weve explored in last research.

DONE | 2026-06-30 22:13 UTC | STARTED | 2026-06-30 22:11 UTC | research | how PACMAN_RANDOM_ACTION_PROB and EVASIVENESS are being used and how affect make pipeline

DONE | 2026-06-30 22:14 UTC | STARTED | 2026-06-30 22:01 UTC | reflect | what is implemented and how can i test ?

DONE | 2026-06-30 21:49 UTC | STARTED | 2026-06-30 21:44 UTC | implement | 43 | PLAN | 000043

DONE | 2026-06-30 21:39 UTC | STARTED | 2026-06-30 21:23 UTC | research | tunning hyperparameters of iql

DONE | 2026-06-30 21:22 UTC | STARTED | 2026-06-30 21:17 UTC | research | is there any way to give a iql net a memory ?

STARTED | 2026-06-30 20:58 UTC | research | como implementar um sistema de reward que a política seja que os ghosts aprendam a perseguir?

DONE | 2026-06-30 18:19 UTC | STARTED | 2026-06-30 18:17 UTC | research | Minha dúvida é se estamos calculando os shaping rewards só com a técnica do PBRS, ou se estamos somando esses valores direto na função de rewards também

DONE | 2026-06-30 00:49 UTC | STARTED | 2026-06-30 00:43 UTC | research | boas práticas de benchmarking com o paper Papoudakis_2021.pdf

DONE | 2026-06-29 21:39 UTC | STARTED | 2026-06-29 21:30 UTC | implement | 000036 | PLAN | 000036

DONE | 2026-06-29 21:27 UTC | STARTED | 2026-06-29 20:38 UTC | plan | source: research-000035 — Make ghosts visibly pursue/follow hard Pacman in three phased levers (L1 diagnostic gate, L2 persistent closing reward, L3 adjacency capture) | PLAN | 000036

DONE | 2026-06-29 18:04 UTC | STARTED | 2026-06-29 18:00 UTC | research | assuming hard pacman, how can we improve the learning and make the ghosts follow the pacman? we did not see this yet

DONE | 2026-06-29 15:25 UTC | STARTED | 2026-06-29 15:20 UTC | implement | 000034 | PLAN | 000034

DONE | 2026-06-29 15:13 UTC | STARTED | 2026-06-29 15:10 UTC | plan | source: research-000032 — R1 positive-control sanity battery: isolate the truly-random condition (curriculum off, random-prob 1.0, full obs, artifacts neutralized) + greedy ε=0 capture-rate eval to decide confound vs genuine HP limit before any sweep | PLAN | 000034

DONE | 2026-06-29 15:06 UTC | STARTED | 2026-06-29 14:56 UTC | research | seens like we are stuck on reward shaping. liveplot shows a 40% ceiling on win rate for a totally random pacman on curriculum learning. for a random pacman the capture rate should be 100%

DONE | 2026-06-29 01:47 UTC | STARTED | 2026-06-29 01:23 UTC | implement | 000031 — Decisive A/B benchmark: matched sparse control vs PBRS | PLAN | 000031

DONE | 2026-06-29 01:21 UTC | STARTED | 2026-06-29 00:52 UTC | plan | Executar o benchmark decisivo do estudo de rewards: desenho A/B (esparso capture_v0 sem shaping vs capture_v0_pure_potential_shaping com PBRS), >=5 seeds conforme constituicao Q3, metrica de perseguicao, framing sample-efficiency. Fonte research-000024 (R5) / research-000028. | PLAN | 000031

DONE | 2026-06-29 00:41 UTC | STARTED | 2026-06-29 00:33 UTC | communicate | para o professor da disciplina o estudo feito aqui nesta branch. ajustes no sistema de rewards e os nosso findings até agora relacionados a tentativa de tunar o sistema de rewards.

STARTED | 2026-06-29 00:32 UTC | plan | Implement the evasive-Pacman benchmark protocol from research-000028: seed-pin fix, sweep wrapper, aggregator/plotter, scripted-pursuit ceiling, randomize-spawns on

DONE | 2026-06-29 00:27 UTC | STARTED | 2026-06-29 00:11 UTC | research | bolar protocolo de teste / pipelines de benchmark para apresentação final: o quão evasivo o Pacman precisa ser para os fantasmas pararem de aprender a capturá-lo

DONE | 2026-06-28 23:57 UTC | STARTED | 2026-06-28 23:54 UTC | research | what happened with the code that was at the main branch and was merged here

DONE | 2026-06-27 22:06 UTC | STARTED | 2026-06-27 22:00 UTC | implement | plan-000025 | PLAN | 000025

DONE | 2026-06-27 21:59 UTC | STARTED | 2026-06-27 21:57 UTC | plan | Reintroduce pure potential-based reward shaping (PBRS) as a new reward variant on the sparse capture_v0 base, per research-000024 | PLAN | 000025

DONE | 2026-06-27 21:43 UTC | STARTED | 2026-06-27 21:34 UTC | research | ive ran benchmark and when eval-latest the ghosts are not following pacman. We need to tune the reward system. im studiyng the potency reward shapping. lets think about reintroducing it. but first lets do a deep evaluation on last benchmark results

DONE | 2026-06-20 22:50 UTC | STARTED | 2026-06-20 22:37 UTC | research | there is something strange when i run eval. the ghosts stop and the pac man move back and forth to be in the visible range of the phantom. but the pac man does not enter in the visible range more, nor get other pellets | RESEARCH | 000022

DONE | 2026-06-20 23:54 UTC | STARTED | 2026-06-20 21:31 UTC | implement | plan-000021 | PLAN | 000021

DONE | 2026-06-20 21:29 UTC | STARTED | 2026-06-20 21:24 UTC | plan | reward tunning from research 12 | PLAN | 000021

DONE | 2026-06-20 20:11 UTC | STARTED | 2026-06-20 20:10 UTC | implement | plan-000019 | PLAN | 000019

---

DONE | 2026-06-20 20:09 UTC | STARTED | 2026-06-20 20:07 UTC | plan | add --device cuda into Makefile goals | PLAN | 000019

---

DONE | 2026-06-20 19:48 UTC | STARTED | 2026-06-20 19:41 UTC | research | pacman policy after --maze feature

---

DONE | 2026-06-20 19:35 UTC | STARTED | 2026-06-20 19:32 UTC | research | after merge that introduced maze options and multiple folders output make liveplot stopped working

---

DONE | 2026-06-20 19:10 UTC | STARTED | 2026-06-20 19:06 UTC | plan | will not use this win-rate eval strategy. remove it from code | PLAN | 000014

---

DONE | 2026-06-20 16:29 UTC | STARTED | 2026-06-20 16:25 UTC | research | current reward system and impact into training. ghosts not learning, stay still near each other after eval

DONE | 2026-06-20 16:26 UTC | STARTED | 2026-06-20 16:22 UTC | plan | add feat to live plot: win rate and other metrics | PLAN | 000011

DONE | 2026-06-20 15:11 UTC | STARTED | 2026-06-20 15:09 UTC | research | parse readme and create a comprehensive tutorial on how to run benchmark training

DONE | 2026-06-20 14:23 UTC | STARTED | 2026-06-20 03:27 UTC | implement | 000008 | PLAN | 000008

DONE | 2026-06-20 03:25 UTC | STARTED | 2026-06-20 03:19 UTC | plan | implementr iql learning to win against pacman | PLAN | 000008

DONE | 2026-06-20 02:10 UTC | STARTED | 2026-06-20 02:05 UTC | implement | 000007 | PLAN | 000007

---

DONE | 2026-06-20 02:04 UTC | STARTED | 2026-06-20 02:01 UTC | plan | PacmanPolicy BFS flood-fill safety-aware pellet maximization | PLAN | 000007

---

DONE | 2026-06-20 01:52 UTC | STARTED | 2026-06-20 01:48 UTC | research | algoritm do pacman: utiliza diversos pathfinder estrela para maximizar o ganho de palets. se um caminho tiver um potencial de encontrar fantasmas, seu valor deve ser penalizado fazendo com que o pacman escolha os caminhos absolutamente seguros priorizando o maximo de ganho dentre estes. se durante um caminho o pacman encontrar um fantasma com colisao potencial, ele deve recalcular sua rota para o ponto mais seguro possivel e entao disparar novamente o algoritmo de maximizacao de pellets com maxima seguranca.

---

DONE | 2026-06-19 14:34 UTC | STARTED | 2026-06-19 14:27 UTC | implement | 3 | PLAN | 000003

---

DONE | 2026-06-19 14:25 UTC | STARTED | 2026-06-19 14:21 UTC | research | update plan 3 with newly added merge commits from main

---

DONE | 2026-06-15 17:04 UTC | STARTED | 2026-06-15 16:38 UTC | plan | source: research-000001 | PLAN | 000003

---

DONE | 2026-06-13 19:10 UTC | STARTED | 2026-06-13 19:02 UTC | research | this codebase in order to understand how it works and the reward system. my current goals is implement a pallet system ( the poiints, coins that the pacman eats throughout the game ) and update the reward system in order to account for this new mechanic ( if the pacman eats all pallets the pacman win

---

