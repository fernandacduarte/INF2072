---
designer_description: "I'm your project's immutable principles -- the non-negotiable lines on identity, architecture, quality, security, and compliance that every skill and agent loads before anything else, and that nothing else in your references can override. When a proposal would cross one of these lines, it is blocked here before it ever reaches a plan or a commit."
---

# TEMPLATE - PROJECT CONSTITUTION

> **How to use this template:** Copy this file to `project/constitution.md` and fill in the values for your project. This file declares immutable principles that override all other guidance. Agents must never violate these without explicit user override.
>
> The constitution is loaded first by pre-skill, before conventions or any other reference file. Rules here take precedence over everything else.
>
> Each section contains HTML comments with examples. Delete the comments once you have filled in your own principles. Rows with `{{...}}` are placeholders -- replace them or remove unused rows.

---

## Project Identity

<!-- Example: Acme Payments API -- A PCI-compliant payment processing service that handles merchant transactions for the Acme platform. -->
<!-- Example: UrbanPlan -- An open-data civic engagement tool that helps residents visualize proposed zoning changes in their neighbourhood. -->
<!-- Example: Helix CMS -- A headless content management system optimized for multi-tenant SaaS deployments. -->

{{PROJECT_NAME}} -- {{one-sentence project mission}}.

{{Optional: describe the primary users or audience for this project}}.

---

## Technical Principles

<!-- Non-negotiable architectural decisions. These are hard rules, not aspirations. -->
<!-- Example: All data mutations go through the service layer -- no direct model access from API routes. Rationale: ensures business logic is testable and HTTP-agnostic. -->
<!-- Example: Every public API endpoint returns a consistent response envelope via response builders. Rationale: frontend relies on predictable response shape. -->
<!-- Example: No raw SQL outside of migration files -- all queries go through the ORM. Rationale: prevents SQL injection and ensures schema consistency. -->

| # | Principle | Rationale |
|---|-----------|-----------|
| T1 | {{technical principle}} | {{why this rule exists}} |
| T2 | {{technical principle}} | {{why this rule exists}} |
| T3 | {{technical principle}} | {{why this rule exists}} |

---

## Quality Principles

<!-- Quality gates that cannot be bypassed. -->
<!-- Example: No code ships without automated tests covering the primary path. Rationale: regression prevention is non-negotiable. -->
<!-- Example: All user-facing text must be internationalized -- no hardcoded strings. Rationale: multi-language support is a core requirement. -->
<!-- Example: Accessibility (WCAG AA) is required for all interactive elements. Rationale: legal compliance and inclusive design. -->

| # | Principle | Rationale |
|---|-----------|-----------|
| Q1 | {{quality principle}} | {{why this standard matters}} |
| Q2 | {{quality principle}} | {{why this standard matters}} |

---

## Security Invariants

<!-- Security rules that must never be relaxed without explicit sign-off. -->
<!-- Example: All endpoints require authentication unless explicitly marked public in the route decorator. Rationale: secure by default. -->
<!-- Example: PII must be encrypted at rest and masked in non-production environments. Rationale: GDPR/compliance requirement. -->
<!-- Example: No secrets in source code -- all credentials come from environment variables or a secrets manager. Rationale: prevents credential leaks. -->

| # | Invariant | Rationale |
|---|-----------|-----------|
| S1 | {{security invariant}} | {{why this cannot be relaxed}} |
| S2 | {{security invariant}} | {{why this cannot be relaxed}} |

---

## Compliance Requirements

<!-- Regulatory, contractual, or policy obligations. Leave empty if none apply. -->
<!-- Example: User data must not leave the EU region. Regulation: GDPR data residency. -->
<!-- Example: Audit logs must be retained for 7 years. Regulation: SOC 2 compliance. -->
<!-- Example: All third-party dependencies must be reviewed for licence compatibility before adoption. Policy: corporate open-source policy. -->

| # | Requirement | Regulation/Contract |
|---|-------------|---------------------|
| C1 | {{compliance requirement}} | {{regulation or policy}} |
| C2 | {{compliance requirement}} | {{regulation or policy}} |

---

## Enforcement

- These principles are loaded into every agent context via pre-skill.
- `/check validate` verifies conformance against the agent-facing constraints derived from this document.
- Violations discovered during `/check review` or `/check preflight` are classified as **blocking** -- they must be resolved before commit.
- To amend this constitution, the change must be explicitly approved by the project lead and documented in the changelog below.

---

## Changelog

<!-- Record amendments here. The constitution should change rarely. -->

### v1 -- {{YYYY-MM-DD HH:MM UTC}}
- Initial constitution created via `/design`.
