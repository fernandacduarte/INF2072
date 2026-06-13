---
designer_description: "When you touch anything under your frontend source tree, I'm the path-scoped rule that surfaces the lenses your project cares about here -- user experience, accessibility, visual design, and responsiveness -- and points you at the frontend and testing sections of your standards so the UI your users actually see keeps its agreed shape."
---

# Template: .claude/rules/frontend.md

> Copy to `.claude/rules/frontend.md` and customize for your project.

```yaml
---
paths:
  - "${FRONTEND_DIR}/src/**"
---
```

# Frontend Rules

When editing files under these paths:

- **Review questions**: see `.claude/references/general/review-perspectives/ux.md`, `.claude/references/general/review-perspectives/a11y.md`, `.claude/references/general/review-perspectives/vis.md`, `.claude/references/general/review-perspectives/resp.md` -- P0 questions are the critical checks.
- **Full conventions**: see `project/standards.md §§ Frontend and Testing` -- stack-specific rules.

## Perspective Alignment

This rule is governed by: **UX** (user experience), **A11Y** (accessibility), **VIS** (visual design), **RESP** (responsive design).
