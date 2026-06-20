---
designer_description: "When you run /onboard for a guardian -- a QA, security, release, or compliance engineer, or a tech lead or manager wearing the quality-and-governance hat -- I'm the role layer the onboarding-generator combines with the new hire's level to shape their plan into the oversight essentials: the 16-perspective review framework, test strategy and coverage expectations, security policies, quality gates, incident response, and the code-review process they are expected to run."
---

# GRD — Guardians

> QA engineers, security engineers, tech leads, and engineering managers who ensure quality, alignment, and governance.

## Roles

- Quality (QA / Test engineer)
- Security & compliance (Security engineer, Compliance officer)
- Leadership (Tech lead, Engineering manager, Release manager)

## Layer 1 — Role-Specific Onboarding Content

### Essential (all Guardians must cover)

- **Review perspective framework**: The structured review system (`general/review-perspectives.md`) -- 16 perspectives, priority tiers (Essential/Deep-dive), conflict resolution. The Guardian's primary tool.
- **Test strategy and coverage**: Unit/integration/e2e boundaries, coverage thresholds, how to run and interpret tests, and gap identification. Validation scripts in `.claude/skills/scripts/`.
- **Security policies**: Authn/authz model, input validation, secrets management, dependency auditing. Key reference: `general/review-perspectives/sec.md`.
- **Quality gates and CI/CD**: Per-commit checks, merge blockers, deployment approval workflow.
- **Incident response**: Detection, escalation, resolution, postmortem process.
- **Code review process**: Expectations, turnaround, required approvals, feedback norms. Use `/check review` for structured reviews.

### Deep-dive (load for thorough onboarding or when Guardian is the primary role)

- **Compliance requirements**: Regulatory obligations (GDPR, SOC 2, HIPAA, etc.), audit trails, data retention.
- **Technical debt inventory**: Known debt, severity, payoff timelines tied to roadmap.
- **Performance baselines**: SLAs/SLOs, load-test results, known bottlenecks, monitoring dashboards.
- **Governance and approval processes**: Approvers, escalation paths, change advisory board.
- **Team health metrics**: Velocity, cycle time, deployment frequency, DORA metrics.
- **Cross-team dependencies**: Upstream/downstream teams, API contracts, SLA agreements.

## Recommended First Tasks by Level

| Level | First Task | Goal |
|-------|-----------|------|
| L1 Contributor | Write tests for an untested module (newcomer) or run `/check validate` and triage (practitioner) | Learn the test framework or current quality state |
| L2 Expert | Conduct a structured code review using `/check review` | Learn the review perspective framework in practice |
| L3 Leader | Audit security posture (Strategist) or review team development process (Manager) | Map security boundaries or understand team dynamics |

## Key Reference Files

- `general/review-perspectives.md` (review framework index)
- `general/review-perspectives/sec.md` (security perspective)
- `general/review-perspectives/test.md` (testability perspective)
- `general/review-perspectives/dx.md` (developer experience perspective)
- `general/review-perspectives/data.md` (data integrity & privacy perspective)
- `.claude/skills/scripts/` (validation and analysis scripts)
- `.claude/agents/code-reviewer.md` (code review agent prompt)
