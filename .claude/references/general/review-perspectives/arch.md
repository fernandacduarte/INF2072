---
designer_description: "When the reviewer is asked to look at what you built through architecture eyes, I'm the checklist that tells it what to watch for -- layer boundaries, separation of concerns, dependency direction, bounded-context respect, failure-mode resilience, and whether the shape you chose is the simplest that meets the requirement -- so structural erosion gets caught at review time instead of at the next refactor."
tier: Essential
---

# ARCH — Architecture

## Essential

- [P0] Does this follow established layer boundaries (API / service / model), avoiding circular dependencies and preserving separation of concerns?
- [P0] Are bounded contexts explicitly defined, with aggregate boundaries respected and no domain leakage across contexts?
- [P0] Under partitions or partial failures, does the system preserve its consistency/availability guarantees per its CAP/PACELC trade-offs?

## Deep-dive

- [P1] Is the solution the simplest that meets the requirement, with feature flags available for safe incremental rollouts?
- [P1] Are error tracking and failure categorization centralized (e.g., Sentry, custom aggregation)?
- [P1] Does the service boundary align with a single business capability, with versioned inter-service contracts for independent deployability?
- [P1] Are state-changing operations captured as domain events, with a strategy for ordering, idempotency, and schema evolution?
- [P1] Are infrastructure concerns (networking, storage, compute scaling) decoupled from application logic through platform abstractions?
- [P1] Are module boundaries enforced at build time (visibility rules, dependency constraints), and is the dependency graph acyclic after this change?
- [P1] Has the failure mode been tested under adverse conditions (dependency outage, resource exhaustion, clock skew), with circuit breakers, bulkheads, or retry budgets in place?
- [P2] Is the caching strategy documented -- what is cached, TTL, invalidation triggers?
- [P2] Has technical debt introduced or resolved been catalogued, with a payoff timeline tied to roadmap items?
- [P2] If this touches legacy components, is there a strangler-fig or anti-corruption layer isolating new code from legacy coupling?
- [P2] **Consistency** (CDN): Do similar architectural patterns (error handling, DI, config) use similar structures across modules?
- [P2] **Role-expressiveness** (CDN): Can a developer infer a module's responsibility from its name, location, and public interface?
- [P2] **Error-proneness** (CDN): Does the architecture invite structural mistakes (wrong-layer logic, easy cycles)?
- [P2] **Hidden dependencies** (CDN): Are cross-module dependencies, shared state, and implicit contracts visible or documented?
- [P2] **Viscosity** (CDN): How much effort to make a change that respects the architecture vs. taking a shortcut?
- [P3] Can the core design be explained via fundamental trade-offs (latency vs. throughput, consistency vs. availability, coupling vs. autonomy) with explicit justification?
