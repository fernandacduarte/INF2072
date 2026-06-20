---
designer_description: "When you touch any locale file, translation catalog, or i18n wiring in your project, I'm the path-scoped rule that reminds you of the internationalisation review lens and points you at the i18n section of your standards so message keys, placeholders, and locale coverage stay consistent across frontend and backend."
---

# Template: .claude/rules/i18n.md

> Copy to `.claude/rules/i18n.md` and customize for your project.

```yaml
---
paths:
  - "${FRONTEND_DIR}/src/i18n/**"
  - "${BACKEND_DIR}/translations/**"
---
```

# i18n Rules

When editing files under these paths:

- **Review questions**: see `.claude/references/general/review-perspectives/i18n.md` -- P0 questions are the critical checks.
- **Full conventions**: see `project/standards.md § i18n` -- stack-specific rules.

## Perspective Alignment

This rule is governed by: **I18N** (internationalization).
