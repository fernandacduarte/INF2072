---
designer_description: "When /plan --light generates a lightweight proposal for a small, surgical change, I'm the canonical proposal skeleton (What / Why / Files / Verify / Risks / checkbox plus a compact 2-3-perspective Review block) that the skill renders into a proposal-<id>-*.md file under ${PROPOSALS_DIR}."
---

# Template: Lightweight Proposal

Canonical shape referenced by: `.claude/skills/plan/SKILL.md` Lightweight Proposal Workflow step 3.

## Proposal shape

```markdown
# Proposal <id> | <prefix><scope> | <datetime> | <short title>
plan_format_version: 1

## What
<one-paragraph description of the change>

## Why
<motivation -- what problem this solves>

## Files
<list of files to create/modify/delete, with one-line description of each change>

## Verify
<single verification criterion>

## Risks
<potential issues or side effects, or "None identified">

- [ ] Done
```

## Review block (quick inline review, 2-3 perspectives, always include SEC if code changes are involved)

```markdown
## Review (Light)
- SEC: <Adopted/N/A -- one line>
- <perspective>: <Adopted/N/A -- one line>
```
