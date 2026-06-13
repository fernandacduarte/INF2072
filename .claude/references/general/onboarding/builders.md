---
designer_description: "When you run /onboard for a builder -- a frontend, backend, full-stack, mobile, DevOps, or data engineer joining your team -- I'm the role layer the onboarding-generator combines with the new hire's level to shape their plan into the code-facing essentials: architecture overview, coding standards, local environment, CI/CD pipeline, branch and PR workflow, and the AI-assisted development norms they are expected to work within."
---

# BLD — Builders

> Developers, DevOps engineers, and infrastructure engineers who write, deploy, and maintain code.

## Roles

- Frontend, backend, full-stack, or mobile developer
- DevOps / infrastructure engineer
- Data / ML engineer

## Layer 1 — Role-Specific Onboarding Content

### Essential (all Builders must cover)

- **Architecture overview**: layers, component boundaries, data flow, deployment topology. Run `/explain architecture` if missing.
- **Coding conventions**: `project/standards.md §§ Backend and Frontend`; path-scoped rules in `.claude/rules/`.
- **Development environment**: clone, install deps, env vars, database setup, first test run. Target: clone-to-passing-tests under 5 minutes.
- **CI/CD pipeline**: build, test, lint, deploy stages -- triggering, reading failures, deploying.
- **Branching and PR workflow**: branch naming, commit conventions, PR template, review expectations.
- **AI-assisted development workflow**: sanctioned tools, effective use, reviewing AI-generated code, when output needs human judgment.

### Deep-dive (load for thorough onboarding or when Builder is the primary role)

- **Dependency map, data model**: third-party libraries, internal shared packages, external integrations; entity relationships, naming conventions, migration workflow (run `/explain data-model` if missing).
- **Testing strategy**: unit/integration/e2e boundaries, coverage expectations, writing and running tests. See `project/standards.md § Testing`.
- **Error handling**: propagation across layers, logging conventions, error response formats.
- **Performance and security**: known bottlenecks, caching, query optimization; auth flow, input validation, secrets management.

## Recommended First Tasks by Level

| Level | First Task | Goal |
|-------|-----------|------|
| L1 Contributor | Fix a well-scoped bug (newcomer) or implement a small feature (practitioner) | Build confidence, learn conventions and PR workflow |
| L2 Expert | Review and improve an existing module | Understand design decisions, propose improvements |
| L3 Leader | Audit a cross-cutting concern (Strategist) or lead a planning session (Manager) | Map system-wide patterns or understand team dynamics |

## Key Reference Files

- `project/standards.md § Backend` (if backend role)
- `project/standards.md § Frontend` (if frontend role)
- `.claude/rules/backend.md`, `.claude/rules/frontend.md` (path-scoped rules)
- `project/product-design-as-coded.md § Conceptual Design` (current system design)
- `general/review-perspectives/dx.md` (developer experience standards)
