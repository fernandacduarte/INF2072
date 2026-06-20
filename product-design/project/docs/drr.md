---
freshness: on-decision
diataxis: reference
---

# DESIGN RATIONALE RECORDS — fernanda-INF2072

> Captures the "why" behind significant design decisions. Prevents future contributors from undoing decisions without understanding the context. Each DRR has a stable D-NNN ID.
>
> For the authoritative list of decisions, see `product-design/project/product-design-as-intended.md ## Decisions`.

---

## Index

| ID | Title | Status | Date |
|----|-------|--------|------|
| D-001 | Use BenchMARL as the RL framework | proposed | 2026-06-13 |
| D-002 | PettingZoo as the environment interface | proposed | 2026-06-13 |

---

## How to Add a Decision

1. Add a `### D-NNN:` entry to `product-design/project/product-design-as-intended.md ## Decisions`
2. Update the index table above
3. Run `/reflect` to record your reasoning

## Decision Shape

Each entry follows the DRR (Design Rationale Record) shape:

- **Context**: What forces are at play; what alternatives were considered
- **Decision**: The chosen direction, stated in the active voice
- **Consequences**: What becomes easier; what becomes harder; follow-up work
- **Supersedes** (optional): D-NNN of the superseded decision
