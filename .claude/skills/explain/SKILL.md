---
name: explain
description: "Explains behavior, code, data model, architecture, or spec drift with visual diagrams and analogies."
argument-hint: "<architecture|behavior|behavior-evolution|code|data-model|spec-drift> [brief]"
compatibility: "Designed for Claude Code with the SEJA harness"
metadata:
  last-updated: 2026-03-28 12:40 UTC
  version: 1.1.0
  category: analysis
  context_budget: standard
  eager_references:
    - general/shared-definitions.md
    - general/report-conventions.md
  references:
    - project/product-design-as-coded.md
    - project/product-design-as-intended.md
    - general/shared-definitions.md
    - general/report-conventions.md
---

> Overview: see [./SKILL-quickguide.md](./SKILL-quickguide.md)

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `architecture [brief]` | -- | Explain system architecture, component relationships, and design choices |
| `behavior [brief]` | -- | Explain emergent behavior from a user's perspective |
| `behavior-evolution [brief]` | -- | Explain current behavior AND how it evolved over time |
| `code [brief]` | -- | Explain how code works, aimed at junior developers |
| `data-model [brief]` | -- | Explain data model, pitfalls, and refactoring opportunities |
| `spec-drift [scope]` | -- | Compare as-coded and as-intended design specs, with optional sync. Scope: `all`, `conceptual-design`, `metacomm`, `--promote`, `--scope since-plan plan-NNNNNN` |

> One type is required. Types are mutually exclusive.

> Rationale for design choices and historical context: see `SKILL-rationale.md` in this directory.

# Explain

If there are no arguments, ask for a user brief.

If the explanation type (architecture, behavior, behavior-evolution, code, data-model, or spec-drift) is not specified or cannot be inferred from the brief, use the AskUserQuestion tool (fallback: numbered text list) to ask which kind of explanation they want:
- "1. Architecture -- system architecture, component relationships, and design choices"
- "2. Behavior -- emergent behavior and pitfalls from a user's perspective"
- "3. Behavior evolution -- current behavior AND how it evolved over time"
- "4. Code -- how code works, aimed at junior developers being onboarded"
- "5. Data model -- data model, pitfalls, and refactoring opportunities"
- "6. Spec drift -- drift between as-coded and as-intended design specs, then optionally sync"

## Common Steps (all modes)

- **C1 Pre-skill**: run `/pre-skill "explain" $ARGUMENTS`.
- **C2 Reserve ID, output path, header**: 6-digit zero-padded IDs via `python .claude/skills/scripts/reserve_id.py --type <type> --title '<short title>'`; output path from `project/conventions.md`; header `# <Type Label> <id> | <prefix><scope> | <current datetime> | <short title>`. Per-type parameters in the Type dispatch table below.
- **C3 Save report**: per `.claude/references/general/report-conventions.md`. Fields: *header* (C2 pattern); *user brief* (+ scope if any); *agent interpretation*; *files*; *explanation* (per-mode sections below). *files* splits -- data-model: *creation files* + *client files*; behavior-evolution: *current implementation files* + *plan files*; architecture: *structural files* + *implementation files*.
- **C4 Post-skill**: run `/post-skill <id>` to commit, file pending actions, and close. Spec-drift Phase 3a/3b each end with C4; the sync-No branch ends with C4 immediately after the drift report.

### Type dispatch table (C2)

| Type | Output dir | Reserve-id type | Filename | Header label | Default scope | Notes |
|------|-----------|-----------------|----------|--------------|---------------|-------|
| behavior | `${EXPLAINED_BEHAVIORS_DIR}` | `behavior` | `behavior-<id>-<slug>.md` | `Behavior` | required | dispatched to `explanation-generator` agent |
| behavior-evolution | `${BEHAVIOR_EVOLUTION_DIR}` | `evolution` | `evolution-<id>-<slug>.md` | `Behavior Evolution` | required | dispatched to `evolution-explainer` agent |
| code | `${EXPLAINED_CODE_DIR}` | `dev-onboarding` | `dev-onboarding-<id>-<slug>.md` | `Dev-Onboarding` | required | dispatched to `explanation-generator` agent |
| data-model | `${EXPLAINED_DATA_MODEL_DIR}` | `data-model` | `data-model-<id>-<slug>.md` | `Data Model` | entire DB if unscoped | dispatched to `explanation-generator` agent |
| architecture | `${EXPLAINED_ARCHITECTURE_DIR}` | `architecture` | `architecture-<id>-<slug>.md` | `Architecture` | entire system if unscoped | dispatched to `architecture-explainer` agent |
| spec-drift | `${RESEARCH_DIR}` | `research` | `research-<id>-<slug>.md` | `Research` | `all` (default), `conceptual-design`, `metacomm`, `--promote`, `--promote --apply-markers plan-NNNNNN` | dispatched to `.claude/skills/_internal/explain/spec-drift/SKILL.md` |

### Voice and framing (per type)

- **behavior / data-model**: conversational, user-centered (roles, goals, activities, UI, interactions); multiple analogies for complex concepts. data-model: include dependencies when scoped.
- **behavior-evolution**: same user-centered voice as behavior, but tell the *story* of how the feature reached its current state via plan history.
- **code**: conversational, aimed at junior developers learning the stack; multiple analogies.
- **architecture**: aimed at onboarding developers; focus on the *why* and trade-offs, not absolute truths; multiple analogies. Include dependencies when scoped.
- **spec-drift**: combines drift analysis and optional sync (replaces the former `/spec` skill). Two-phase promote workflow in Step C.

## Per-mode content (reuses C1-C4)

### spec-drift

If mode is `spec-drift`: load design-spec references on demand -- read and inject `product-design/product-design-as-intended.md` and `product-design/product-design-as-coded.md` (skip silently if absent -- workspace mode).

Read `.claude/skills/_internal/explain/spec-drift/SKILL.md` via the Read tool and execute its instructions inline as part of this skill's flow.

### behavior

Launch the `explanation-generator` agent via the Agent tool (subagent_type=`explanation-generator`) with inputs: mode=`behavior`, user_brief=`<user_brief>`, output_path=`<resolved output_path>`, artifact_id=`<reserved id>`. Wait for completion, then apply C4 (post-skill `<id>`).

### code

Launch the `explanation-generator` agent via the Agent tool (subagent_type=`explanation-generator`) with inputs: mode=`code`, user_brief=`<user_brief>`, output_path=`<resolved output_path>`, artifact_id=`<reserved id>`. Wait for completion, then apply C4 (post-skill `<id>`).

### data-model

Launch the `explanation-generator` agent via the Agent tool (subagent_type=`explanation-generator`) with inputs: mode=`data-model`, user_brief=`<user_brief>`, output_path=`<resolved output_path>`, artifact_id=`<reserved id>`. Wait for completion, then apply C4 (post-skill `<id>`).

### behavior-evolution

Launch the `evolution-explainer` agent via the Agent tool (subagent_type=`evolution-explainer`) with inputs: user_brief=`<user_brief>`, output_path=`<resolved output_path>`, artifact_id=`<reserved id>`. Wait for completion, then apply C4 (post-skill `<id>`).

### architecture

Launch the `architecture-explainer` agent via the Agent tool (subagent_type=`architecture-explainer`) with inputs: user_brief=`<user_brief>`, output_path=`<resolved output_path>`, artifact_id=`<reserved id>`, scope=`<scope if provided>`. Wait for completion, then apply C4 (post-skill `<id>`).
