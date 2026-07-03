# QA Log | Communication 000056 | 2026-07-02 11:52 UTC | 2 slides: historia do ClosingDistance (PBRS -> capture_v0_closing)

**Brief**: 2 slides contando a estoria do Closing Distance: por que capture_v0_closing substitui a estrategia PBRS (telescoping shaping ~zero contra Pacman evasivo, causando passividade dos fantasmas) -- explicar PBRS e para onde fomos no ClosingDistance.

## Q1

/communicate -- covers: why capture_v0_closing replaces the earlier PBRS-based strategy (whose telescoping shaping netted to ~zero against an evasive Pacman, causing ghost passivity). "Preciso apresentar 2 slides contando a estoria do Closing distance. Me ajude a explicar novamente o PBRS e para onde fomos no ClosingDistance."

## A1

Ran pre-skill (brief logged; pending banner surfaced: plan-000011 open 11 days, 3 overdue periodic triggers). Gathered grounding before generation:

- `custom_environment/env/rewards/current.py`: `CaptureV0PurePotentialShaping` (PBRS: `F = Phi(s') - Phi(s)`, `Phi = -0.7 * mean_BFS_dist`, gamma=1 exact telescoping, terminals +100/-100, timestep -0.05) and `CaptureV0ClosingReward` (`closing = 2.0 * clip(prev - cur, -2, +2)` on mean BFS, non-telescoping, containment `pacman_legal_moves_reduced = 0.5`).
- Prior artifact `communication-000050-academics.md` (3-slide Marp deck with the same PBRS -> closing story).

## Q2

User (mid-task): "coloquei isso nos slides: Desenvolvimento: Nova ideia - Reward ClosingDistance / Fruto de aprendizados do PBRS / PBRS nao muda politica, so acelera o processo / Politica nao recompensava perseguicao / Ajustes nos rewards".

## A2

Incorporated the draft bullets into the generation brief, with one technical sharpening: PBRS's policy invariance is exactly what PRESERVED the passive policy (telescoping sum nets ~0 against an evader holding distance), rather than merely "not changing the policy".

## Q3

AskUserQuestion: audience? format?

## A3

User selected: audience = Academic (ACD) (professor de RL e colegas); format = markdown text only (user assembles the PowerPoint themselves).

## Q4

(Skill flow) Reserve ID and generate.

## A4

- `reserve_id.py` returned 000053, which collided with `communication-000053-training-curve-slide.html` already on disk (slides 000053-000055 had been written without INDEX registration). Advanced the counter to 000056 and backfilled INDEX.md rows for 000053-000055 pointing at the on-disk slide files.
- Launched the communication-generator agent (general-purpose) with the ground-truth facts, the user's draft bullets, and pt-BR slide-text instructions.
- Output: `_output/communication/2026-07-02/communication-000056-academics.md` -- Slide 1 "PBRS: o que e e por que falhou aqui" (6 bullets + notas do apresentador) and Slide 2 "Nova ideia: Reward ClosingDistance" (6 bullets refining the user's draft + notas do apresentador). Values verified against `current.py`; consistent with communication-000050.
- Updated the date-folder `index.md` with the 000056 entry.
