---
designer_description: "When you touch any migration file in your project, I'm the path-scoped rule that surfaces the database and security review lenses and points you at the migrations section of your backend standards, so schema changes ship with the idempotency, reversibility, and safety properties your project has agreed on before they ever reach a live database."
---

# Template: .claude/rules/migrations.md

> Copy to `.claude/rules/migrations.md` and customize for your project.

```yaml
---
paths:
  - "${MIGRATIONS_DIR}/**"
---
```

# Migration Rules

When editing files under these paths:

- **Review questions**: see `.claude/references/general/review-perspectives/db.md`, `.claude/references/general/review-perspectives/sec.md` -- P0 questions are the critical checks.
- **Full conventions**: see `project/standards.md § Backend > 6` -- stack-specific rules.

## Perspective Alignment

This rule is governed by: **DB** (database), **SEC** (security).
