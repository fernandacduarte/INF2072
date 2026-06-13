---
designer_description: "When you evaluate a plan, a diff, or an architectural decision, I'm the reference that defines the sixteen domain lenses -- security, performance, architecture, accessibility, and the rest -- their Essential vs Deep-dive tiers, the two-stage load protocol that keeps context lean, the Adopted/Deferred/N/A status vocabulary, and the rules for resolving conflicts when two perspectives pull the review in opposite directions."
---

# FRAMEWORK - REVIEW PERSPECTIVES

> Domain-based review checklist ensuring structured, deterministic coverage across engineering and design concerns. Replaces ad-hoc "simulate a council" instructions (advisory-0005, plan-0283).

---

## How to Use

Evaluate changes against each applicable perspective and record tag + status: **Adopted** (evaluated; concerns addressed), **Deferred** (evaluated; not addressed -- state why with pros/cons), or **N/A** (does not apply). If deferring only for scope, ask whether to include it.

### Loading Perspectives

Each perspective under `general/review-perspectives/` has two tiers: **Essential** (3-7 P0 critical/blocking questions, always evaluated, load for `standard` context or default shortlist) and **Deep-dive** (8-12 P1-P4 questions for thorough review, load for `heavy` context, explicit deep-dive, or primary-focus perspectives). Questions are priority-classified (`[P0]` critical through `[P4]` informational) and sorted by priority; under time/context pressure, focus P0-P1 first.

### Two-Stage Loading

To avoid bulk-loading all 16 files:

1. **Load the index** (`general/review-perspectives-index.md`, <600 tokens).
2. **Select 4-6 perspectives** via the **Perspective Shortcuts by Plan Prefix** table below, or manually by change content.
3. **Load only the selected** `review-perspectives/<tag>.md` files.

Consumers (`/plan`, `/check review`) follow this protocol unless depth is **Deep** and all perspectives are needed.

### Resolving Perspective Conflicts

On conflict (e.g., PERF vs SEC), remark it and resolve:

1. **SEC wins by default** -- unless the user explicitly accepts the risk.
2. **A11Y is non-negotiable** -- never traded against visual design or performance.
3. **Document the trade-off** -- record both the chosen approach and the deferred concern with rationale.
4. **Ask when unclear** -- for non-default conflicts (e.g., PERF vs DX), ask the user.

---

## Engineering Perspectives

| Tag | Name | File |
|-----|------|------|
| SEC | Security | [sec.md](review-perspectives/sec.md) |
| PERF | Performance | [perf.md](review-perspectives/perf.md) |
| DB | Database | [db.md](review-perspectives/db.md) |
| API | API Design | [api.md](review-perspectives/api.md) |
| ARCH | Architecture | [arch.md](review-perspectives/arch.md) |
| DX | Developer Experience | [dx.md](review-perspectives/dx.md) |
| I18N | Internationalization | [i18n.md](review-perspectives/i18n.md) |
| TEST | Testability | [test.md](review-perspectives/test.md) |
| OPS | Operations / DevOps | [ops.md](review-perspectives/ops.md) |
| COMPAT | Compatibility | [compat.md](review-perspectives/compat.md) |
| DATA | Data Integrity & Privacy | [data.md](review-perspectives/data.md) |

## Design Perspectives

| Tag | Name | File |
|-----|------|------|
| UX | User Experience | [ux.md](review-perspectives/ux.md) |
| A11Y | Accessibility | [a11y.md](review-perspectives/a11y.md) |
| VIS | Visual Design | [vis.md](review-perspectives/vis.md) |
| RESP | Responsive Design | [resp.md](review-perspectives/resp.md) |
| MICRO | Microinteractions | [micro.md](review-perspectives/micro.md) |

---

## Perspective Shortcuts by Plan Prefix

Default shortlists by plan prefix and scope. Add up to 2 extra perspectives if plan content warrants it.

| Prefix-Scope | Default Perspectives |
|--------------|---------------------|
| `FIX-B` / `REFACTOR-B` | SEC, DB, ARCH, TEST, PERF, DX |
| `FIX-F` / `REFACTOR-F` | UX, A11Y, VIS, TEST, I18N, RESP |
| `FIX-X` / `REFACTOR-X` | SEC, DB, API, ARCH, UX, A11Y, I18N, TEST |
| `FEATURE-B` | SEC, DB, API, ARCH, TEST, PERF |
| `FEATURE-F` | UX, A11Y, VIS, RESP, I18N, TEST, MICRO |
| `FEATURE-X` | SEC, DB, API, ARCH, UX, A11Y, I18N, TEST |
| `REDESIGN-B` | ARCH, DB, SEC, TEST, PERF, DX |
| `REDESIGN-F` | UX, A11Y, VIS, RESP, MICRO, I18N, TEST |
| `REDESIGN-X` | ARCH, UX, A11Y, SEC, DB, API, I18N, TEST |
| `TEST-B` | TEST, DB, ARCH, DX |
| `TEST-F` | TEST, UX, A11Y, DX |
| `TEST-X` | TEST, DB, ARCH, UX, A11Y, DX |
| `DOCUMENT-B` / `DOCUMENT-F` / `DOCUMENT-X` | DX, COMPAT, ARCH |
| `CHORE-O` / `DOCUMENT-O` | DX, OPS, COMPAT |
| `CHORE-B` / `CHORE-F` / `CHORE-X` | DX, OPS, COMPAT, TEST |
