---
name: plan-light-internal
description: "Inlined worker for /plan --light lightweight proposal mode. Not user-invocable."
compatibility: "Designed for Claude Code with the SEJA harness"
metadata:
  internal: true
  category: internal
  version: 1.0.0
---

> This is an inlined worker; execute these instructions as part of the caller's flow. The wrapper at .claude/skills/plan/SKILL.md has already run C1 (pre-skill) and the Design Guard; execute the steps below and invoke C6 (post-skill) at the end per the mode's own step 8.

> Used when `--light` is present. Skip the standard workflow above.

## Overview

Minimal change proposal for small, surgical modifications. No multi-step decomposition, no multi-phase review. For changes too small to warrant a full plan but worth tracking.

### Delta table (steps 1-6)

| Step | Common? | Delta |
|---|---|---|
| 1. Pre-skill | C1 | -- |
| 2. Reserve ID | C2 | `--type proposal`. |
| 3. Generate proposal | C3 | Shape per `.claude/references/template/proposal.md`, plus the Review (Light) block described there. |
| 4. Quick review | -- | Unique: inline 2-3 perspective scan; always include SEC for code changes. Record per the Review (Light) block in `template/proposal.md`. |
| 5. Save proposal | -- | Unique: save to `${PROPOSALS_DIR}/proposal-<id>-<slug>.md`. |
| 6. Execute-now prompt | C4 + C6 | Ask "Execute this proposal now?"; if yes, execute inline (no subagent orchestration for single-change proposals), mark checkbox done, then run /post-skill <id>. If no, run /post-skill <id>. |
