# AS-BUILT CONCEPTUAL DESIGN CHANGELOG — fernanda-INF2072

<!-- maintained-by: Agent (post-skill); append-only -->

---

| Date | Plan | Change | Description |
|------|------|--------|-------------|
| 2026-06-13 | - | initial | Design documentation created via `/design` |
| 2026-06-19 | plan-000003 | Added | Pallet-win mechanic: `Reward.PACMAN_WIN_PALLETS`, per-episode `_total_pallets` tracking, pallet-exhaustion truncation in `step()`, and `pallets_remaining_norm` in the global state. Source: agent (post-skill). |
| 2026-06-20 | plan-000007 | Added | Deterministic safety-aware Pacman policy: `PacmanPolicy` (BFS flood-fill pellet seeking + ghost danger-zone hard exclusion + SEEKING_PELLET→FLEEING→COOLDOWN state machine), `PACMAN_DANGER_RADIUS` constant, and env wiring replacing `Action.choose_random()`. Source: agent (post-skill). |
