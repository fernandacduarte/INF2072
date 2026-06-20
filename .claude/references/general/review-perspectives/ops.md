---
designer_description: "When the reviewer is asked to look at what you built through operations eyes, I'm the checklist that tells it what to watch for -- environment parity across dev/staging/production, health-check depth, logging and alerting, deployment and rollback safety, SLO and error-budget impact, secrets handling, and on-call runbook coverage -- so the change survives not just the merge but the next 3 a.m. incident."
tier: Deep-dive
---

# OPS — Operations / DevOps

## Essential

- [P0] Will this work correctly across development, staging, and production environments?
- [P0] Does the health check endpoint verify all critical dependencies (DB, Redis, external services)?
- [P0] Is there a documented disaster recovery and rollback procedure?
- [P0] Are error budgets defined, and does this change risk breaching any SLO target that would trigger a deployment freeze?
- [P0] Is there a runbook covering escalation paths, communication templates, and severity classification for on-call?
- [P0] Are all secrets injected at runtime from a centralized vault (not baked into images or env-var literals), with automatic rotation?

## Deep-dive

- [P1] Does this change affect Docker builds, environment variables, or deployment scripts?
- [P1] Are health checks, logging, and monitoring addressed, with a log-aggregation and alerting system in place?
- [P1] Are SLOs/SLAs defined with corresponding monitoring dashboards?
- [P1] Are deployment strategies (blue-green, canary) defined for zero-downtime releases?
- [P1] Are pod resource requests/limits, HPA thresholds, and disruption budgets correctly configured, and is every infrastructure change in version-controlled IaC with a plan/apply gate (no manual drift)?
- [P1] Are distributed traces correlated with logs/metrics via consistent identifiers, with dashboards covering the four golden signals (latency, traffic, errors, saturation)?
- [P1] Can the pipeline roll back automatically on health-check failure, with idempotent stages (retries produce no duplicate side effects)?
- [P2] Is cost impact of new or resized resources estimated, with tagging policies enforced for attribution, and are service-to-service paths secured with mTLS and least-privilege network/mesh rules?
- [P2] Has the service been subjected to controlled failure injection (pod kills, latency spikes, dependency outages) to validate graceful degradation?
