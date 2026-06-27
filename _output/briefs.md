# Briefs

Execution log of all skill invocations.

---

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

