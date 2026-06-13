---
designer_description: "When /plan --roadmap produces the roadmap summary file, I'm the canonical shape for the header, ## Source list, ## Wave Summary tables (one per wave, with Plan and Status columns), and ## Execution Instructions block -- including the anti-pattern note that Plan column entries start as plan-TBD and are filled in only after /plan reserves the real ID."
---

# Template: Roadmap Summary File

Canonical shape referenced by: `.claude/skills/plan/SKILL.md` Roadmap Workflow (Mode 1 step 8; Mode 2 step 7).

## File shape

```markdown
# Roadmap <id> | <datetime> | <title>

## Source
- project/product-design-as-coded.md (read)
- project/product-design-as-intended.md (read)
- project/conventions.md (read)
- ... (list all files read)

## Wave Summary

### Wave 0 -- Foundation (sequential)
| # | ID | Title | Scope | Type | Plan | Status |
|---|-----|-------|-------|------|------|--------|
| 1 | user-model | User entity + migration | backend | technical | plan-TBD | pending |
| 2 | group-model | Group entity + migration | backend | technical | plan-TBD | pending |

### Wave 1 -- Services/API (parallel)
| # | ID | Title | Scope | Type | Plan | Depends on | Status |
|---|-----|-------|-------|------|------|-----------|--------|
| 3 | user-api | User CRUD API | backend | technical | plan-TBD | user-model | pending |
| 4 | group-api | Group CRUD API | backend | technical | plan-TBD | group-model | pending |

### Wave 2 -- Frontend (parallel)
| # | ID | Title | Scope | Type | Plan | Depends on | Status |
|---|-----|-------|-------|------|------|-----------|--------|
| 5 | home-page | Home page UX flow | frontend | design | plan-TBD | user-api | pending |

> The `Plan` column starts as `plan-TBD` for every row. Fill in the real ID (e.g., `plan-000042`) **only after** `/plan` has been invoked for that work item and has returned the ID it reserved. Do not pre-reserve IDs up front -- see the anti-pattern note in Mode 1 step 8.

## Execution Instructions

### Wave 0 (sequential)
Execute these plans one at a time, in order:
1. /implement XXXX (user-model)
2. /implement XXXX (group-model)

### Wave 1 (parallel -- 2 plans)
All depend on Wave 0. Execute in parallel via:
- Multiple Claude Code sessions, or
- Worktree-isolated agents from a single session

### Wave 2 (parallel -- 1 plan)
Depends on Wave 1. Execute after Wave 1 completes.
```
