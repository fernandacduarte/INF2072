---
recommended: true
depends_on: [all]
freshness: immutable-once-accepted
diataxis: explanation
description: "Design Rationale Record format with status tracking, numbering convention, and index template."
designer_description: "When /document generates a Design Rationale Record, I'm the template that shapes the context, decision, consequences, and status-tracking sections using your plan's Docs: fields and the decision the diff encodes, so the why behind a significant dedsign choice is captured in the record future developers will read before they try to undo it."
---

# TEMPLATE -- DESIGN RATIONALE RECORDS (DRRs)

> **How to use this template:** Create a `docs/drr/` directory in your project. Use this format for every significant software design decision. A DRR captures the *why* behind a decision so future developers don't undo it without understanding the trade-offs.

## File Organization

| Path | Purpose |
|------|---------|
| `docs/drr/` | All DRR files |
| `docs/drr/INDEX.md` | DRR index (auto-maintained or manual) |
| `docs/drr/drr-NNNNNN-<slug>.md` | Individual DRR files |

## DRR Format

```markdown
# DRR-NNNNNN: {{Decision Title}}

- **Status**: {{Proposed | Accepted | Deprecated | Superseded by DRR-MMMM}}
- **Date**: {{YYYY-MM-DD HH:MM UTC}}
- **Deciders**: {{who was involved in the decision}}

## Context

{{What is the issue? What forces are at play? What problem needs solving?
Include relevant constraints, requirements, and prior art.}}

## Decision

{{`CHANGE:` or `NEW:` decision: What are we proposing or have agreed to?
State it as an imperative: "We will use X for Y."}}

## Consequences

- `+` {{Benefit 1}}
- `+` {{Benefit 2}}
- `-` {{Trade-off 1}}
- `-` {{Trade-off 2}}
- `0` {{Side effect that is neither positive nor negative}}

## Rejected Alternatives

### Alternative {{NN, zero-padded sequential number}}

{{ Proposal }}

- `+` {{ Pro 1 }}
- `+` {{ Pro 2 }}
- `-` {{ Con 1 - if main reason to reject, format in boldface }}
- `-` {{ Con 2 - if main reason to reject, format in boldface }}

```

## DRR Index Template

```markdown
# Design Rationale Records

| # | Title | Status | Date |
|---|-------|--------|------|
| [DRR-0001](drr-000001-<slug>.md) | {{title}} | Accepted | {{YYYY-MM-DD HH:MM UTC}} |
```

## Numbering Convention

- DRRs are identified by unique, sequential, 6-digit, zero-padded numbers: DRR-000001, DRR-000002, etc.

## When to Write a DRR

- Choosing a framework, library, or tool
- Defining a software design pattern (including UX, UI, or architecture -- )
- Comparing UX or UI alternative solutions
- Making a significant trade-off (performance vs. simplicity, consistency vs. availability)
- Changing an established pattern
- Deciding NOT to do something

## Migration Hint

> If your project has design rationale buried in documentation prose, extract each distinct decision into its own DRR. Look for phrases like "we chose X because", "the reason for", "we decided to", "the trade-off is".

## Freshness Policy

DRRs are immutable once Accepted. DO NOT edit accepted DRRs -- instead, create a new DRR that supersedes the old one. Update status to 'Superseded by DRR-NNNNNN'.
