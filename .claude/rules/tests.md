---
paths:
  - "**/*.test.*"
  - "**/test_*.py"
  - "backend/tests/**"
designer_description: "When you add or edit a test file, I surface the P0 review questions for testability and developer experience alongside your project's testing conventions, so the suite stays fast, deterministic, and diagnostic -- tests that fail loudly when behaviour changes and stay quiet when nothing real moved, with enough signal in the failure that the next engineer does not have to re-run locally to understand it."
---

# Test File Rules

When editing files under these paths:

- **Review questions**: see `.claude/references/general/review-perspectives/test.md`, `.claude/references/general/review-perspectives/dx.md` -- P0 questions are the critical checks.
- **Full conventions**: see `project/standards.md § Testing` -- stack-specific rules.

## Perspective Alignment

This rule is governed by: **TEST** (testability), **DX** (developer experience).
