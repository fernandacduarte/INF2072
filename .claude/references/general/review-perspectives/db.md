---
designer_description: "When the reviewer is asked to look at what you built through database eyes, I'm the checklist that tells it what to watch for -- migration safety and reversibility, referential integrity, constraint enforcement, index coverage, connection-pool and replication health, and backup/restore discipline -- so schema changes land without breaking older app versions or losing data on rollback."
tier: Essential
---

# DB — Database

## Essential

- [P0] Are schema changes backward-compatible and migration-safe (idempotent)?
- [P0] Are backup/restore procedures automated with tested recovery, and is RPO/RTO validated via restore drills (point-in-time, cross-region)?
- [P0] Are connection-pool sizes, statement timeouts, and idle-connection reaping tuned for production concurrency and failover?
- [P0] Does the replication topology handle split-brain, with read-replica lag monitored and traffic auto-redirected on excessive lag?
- [P0] Are credentials auto-rotated, network access least-privilege, and sensitive columns encrypted at rest and masked in non-production?

## Deep-dive

- [P1] Are FK constraints, cascades, and soft delete filters correctly applied?
- [P1] Does the health check verify database responsiveness (not a static status)?
- [P1] Is test environment parity maintained (same DB engine for unit and integration tests)?
- [P1] Do critical queries have covering indexes with guardrails against full-table scans, and does ORM-generated SQL match intended plans with N+1 detection in CI?
- [P1] Is the data model normalized appropriately, with denormalization trade-offs documented and consistency ownership clear?
- [P1] Are migrations versioned, reversible, and tested against production-sized data to catch lock contention and long-running ALTERs?
- [P1] Are slow-query logs, lock-wait metrics, and pool saturation surfaced in dashboards with SLO-tied alerts?
- [P2] Are ORM queries efficient (joins, eager/lazy loading)?
- [P2] For time-series or append-heavy workloads, are partitioning and retention/rollup policies defined to prevent unbounded growth?
