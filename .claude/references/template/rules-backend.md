---
designer_description: "When you touch any file under your backend source tree, I'm the path-scoped rule that reminds you which review perspectives matter here -- security, database, and architecture by default -- and points you at the sections of your project standards that codify the conventions this code must respect before the diff leaves your hands."
---

# Template: .claude/rules/backend.md

> Copy to `.claude/rules/backend.md` and customize for your project.

```yaml
---
paths:
  - "${BACKEND_DIR}/**"
---
```

# Backend Rules

When editing files under these paths:

- **Review questions**: see `.claude/references/general/review-perspectives/sec.md`, `.claude/references/general/review-perspectives/db.md`, `.claude/references/general/review-perspectives/arch.md` -- P0 questions are the critical checks.
- **Full conventions**: see `project/standards.md § Backend` -- stack-specific rules.

## Perspective Alignment

This rule is governed by: **SEC** (security), **DB** (database), **ARCH** (architecture).
