---
designer_description: "When you touch anything under your end-to-end test suite, I'm the path-scoped rule that flags the review lenses that apply here -- testability, user experience, and accessibility -- and points you at the testing section of your standards so the browser-level tests stay faithful to the flows real users walk through."
---

# Template: .claude/rules/e2e.md

> Copy to `.claude/rules/e2e.md` and customize for your project.

```yaml
---
paths:
  - "e2e/**"
---
```

# E2E Test Rules

When editing files under these paths:

- **Review questions**: see `.claude/references/general/review-perspectives/test.md`, `.claude/references/general/review-perspectives/ux.md`, `.claude/references/general/review-perspectives/a11y.md` -- P0 questions are the critical checks.
- **Full conventions**: see `project/standards.md § Testing > 3` -- stack-specific rules.

## Perspective Alignment

This rule is governed by: **TEST** (testability), **UX** (user experience), **A11Y** (accessibility).
