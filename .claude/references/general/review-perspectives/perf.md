---
designer_description: "When the reviewer is asked to look at what you built through performance eyes, I'm the checklist that tells it what to watch for -- N+1 queries, unbounded loops, missing indexes, cache strategy, bundle weight, and how the change holds up under realistic concurrency and peak load -- so you hear back where the code will slow down before users do."
tier: Deep-dive
---

# PERF — Performance

## Essential

- [P0] Are there N+1 queries, unbounded loops, or missing database indexes?
- [P0] Will this degrade under realistic load (concurrent users, large datasets)?
- [P0] Are queries using appropriate indexes, with slow-query logs reviewed for full scans or lock contention?
- [P0] Has the system been profiled under sustained peak load to identify throughput ceilings and graceful degradation paths?
- [P0] Are shared-state access patterns free of lock contention, with thread pools / async queues sized to avoid saturation?

## Deep-dive

- [P1] Are expensive operations cached, paginated, or deferred appropriately?
- [P1] Are HTTP cache headers (`Cache-Control`, `ETag`, `Last-Modified`) set on read-heavy endpoints, and is app-level caching (Redis, in-memory) used for expensive queries?
- [P1] Are critical-path resources minimized, with CLS and LCP within acceptable thresholds?
- [P1] Are cacheable assets served from edge locations, with invalidation scoped to avoid stale content?
- [P1] Are object lifetimes and allocations reviewed for GC pressure, leaks, or unbounded growth in long-lived collections?
- [P1] Are round-trips minimized via batching, connection reuse (keep-alive, HTTP/2), and payload compression?
- [P1] Are mobile constraints addressed (CPU/GPU budgets, battery, 3G/LTE variability)?
- [P2] Are frontend bundle sizes monitored against a performance budget, and are prefetch/preload hints used for predictable navigation paths?
- [P2] Are latency percentiles (p50, p95, p99) tracked per endpoint, with SLO-breach alerts rather than averages?
- [P2] Is there a capacity model mapping traffic growth to resources, with auto-scaling validated against realistic demand curves?
