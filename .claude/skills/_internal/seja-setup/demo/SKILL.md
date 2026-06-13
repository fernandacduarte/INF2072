---
name: seja-setup-demo-internal
description: "Inlined worker for /seja-setup --demo Flag. Not user-invocable."
compatibility: "Designed for Claude Code with the SEJA harness"
metadata:
  internal: true
  category: internal
  version: 1.0.0
---

> This is an inlined worker; execute these instructions as part of the caller's flow. The wrapper at `.claude/skills/seja-setup/SKILL.md` has already run the Entry-Point Routing dispatch; execute the steps below as part of the `/seja-setup` skill's flow.

This mode extends the install internal. Before executing demo-specific steps below, read and execute `.claude/skills/_internal/seja-setup/install/SKILL.md` steps 1-7 with these two modifications: (a) step 4b is skipped -- demo mode uses the pre-filled `.claude/references/template/demo/conventions.md` (see step 9); (b) step 7b Initial Commit is deferred to after step 10b of this internal.

## --demo Flag

> **Incompatible with `--workspace` and `--upgrade`.** If combined, reject with an error.

Demo mode uses `.claude/references/template/demo/conventions.md` as the pre-answered questionnaire output; Section 1 basic-definitions is **not** shown to the user. Step 4b detects `--demo` and skips the questionnaire entirely (see its inline "Skip entirely when `--demo` is active" clause). Step 9 below then copies the pre-filled demo `conventions.md` into `product-design/conventions.md`. The post-questionnaire scaffolding steps (`Scaffold-CLAUDE.md` at 7c, `Scaffold-Rules` at 7d, `Scaffold-SmokeTestInfra` at 7e) run per their usual logic against the pre-populated `conventions.md`, producing `CLAUDE.md`, rule files, and smoke-test infrastructure flavored for the TaskFlow demo stack. `Scaffold-SmokeTestInfra` is gated on backend presence as usual -- it emits files only when the demo `conventions.md` carries a non-`none` `BACKEND_FRAMEWORK`.

Runs Standard Install steps 1-7 (skipping 7b -- deferred to after step 10), then:

9. **Copy demo design files** from `.claude/references/template/demo/` (except `WALKTHROUGH.md`) into `product-design/`:
   - `conventions.md` -- TypeScript + React conventions (TaskFlow)
   - `constitution.md` -- accessibility, simplicity, test-coverage principles
   - `product-design-as-intended.md` -- Task and Category entities, task-creation and category-filtering intents

10. **Copy walkthrough**: `.claude/references/template/demo/WALKTHROUGH.md` -> `<target>/WALKTHROUGH.md`.

10b. **Initial commit (demo)**: run step 7b now so the commit includes demo files + walkthrough.

11. **Print walkthrough message**:
    > Your demo project "TaskFlow" has been set up at `<target>` with pre-filled design files.
    >
    > Open `WALKTHROUGH.md` for a guided tour of the core SEJA skills (/research, /plan, /implement, /check).
    >
    > To start fresh with your own project instead, run `/design` to replace the demo configuration.
