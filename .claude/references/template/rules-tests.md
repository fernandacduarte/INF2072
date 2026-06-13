---
designer_description: "When you touch any unit or integration test file in your project, I'm the path-scoped rule that flags the testability and developer-experience lenses and points you at the testing section of your standards, so your tests stay readable, deterministic, and a genuine safety net for the code they cover rather than a chore that ships alongside it."
---

# Template: .claude/rules/tests.md

> Copy to `.claude/rules/tests.md` and customize for your project.

```yaml
---
paths:
  - "**/*.test.*"
  - "${BACKEND_DIR}/tests/**"
---
```

# Test File Rules

When editing files under these paths:

- **Review questions**: see `.claude/references/general/review-perspectives/test.md`, `.claude/references/general/review-perspectives/dx.md` -- P0 questions are the critical checks.
- **Full conventions**: see `project/standards.md § Testing` -- stack-specific rules.

## Perspective Alignment

This rule is governed by: **TEST** (testability), **DX** (developer experience).
