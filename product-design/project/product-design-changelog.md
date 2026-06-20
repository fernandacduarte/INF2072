# AS-BUILT CONCEPTUAL DESIGN CHANGELOG — fernanda-INF2072

<!-- maintained-by: Agent (post-skill); append-only -->

---

| Date | Plan | Change | Description |
|------|------|--------|-------------|
| 2026-06-13 | - | initial | Design documentation created via `/design` |
| 2026-06-19 | plan-000003 | Added | Pallet-win mechanic: `Reward.PACMAN_WIN_PALLETS`, per-episode `_total_pallets` tracking, pallet-exhaustion truncation in `step()`, and `pallets_remaining_norm` in the global state. Source: agent (post-skill). |
| 2026-06-20 | plan-000007 | Added | Deterministic safety-aware Pacman policy: `PacmanPolicy` (BFS flood-fill pellet seeking + ghost danger-zone hard exclusion + SEEKING_PELLET→FLEEING→COOLDOWN state machine), `PACMAN_DANGER_RADIUS` constant, and env wiring replacing `Action.choose_random()`. Source: agent (post-skill). |
| 2026-06-20 | plan-000007 | Changed | Revised `PacmanPolicy` to defense-first: stateless lexicographic move scoring `(safety, pellet_progress)` via two multi-source BFS passes; replaced `PACMAN_DANGER_RADIUS = 3` with `PACMAN_SAFE_DISTANCE = 5`; survival now strictly dominates pellet collection. Survives 8/8 episodes vs both random and actively-chasing ghosts (was caught at step 35 before). Source: agent (post-skill). |
