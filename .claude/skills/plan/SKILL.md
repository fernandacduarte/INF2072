---
name: plan
description: "Make a plan to add a feature, fix a bug, or refactor code. Supports metacomm framing for design-intent briefs."
argument-hint: "<brief> [--review <light|standard|deep>] [--framing metacomm] [--light] [--plan | --roadmap [--from-spec <path>] [--auto] [--only-unimplemented]]"
compatibility: "Designed for Claude Code with the SEJA harness"
metadata:
  last-updated: 2026-03-29 00:15 UTC
  version: 1.0.0
  plan_format_version: 1
  category: planning
  context_budget: heavy
  eager_references:
    - project/product-design-as-coded.md
    - project/product-design-as-intended.md
    - general/report-conventions.md
    - general/coding-standards.md
    - general/review-perspectives-index.md
  references:
    - project/product-design-as-coded.md
    - project/product-design-as-intended.md
    - project/conventions.md
    - general/report-conventions.md
    - general/coding-standards.md
    - project/standards.md
    - project/security-checklists.md
    - project/design-standards.md
    - general/review-perspectives.md
    - general/review-perspectives-index.md
    - general/review-log-template.md
    - template/plan-step.md
    - template/roadmap-summary.md
    - template/proposal.md
---

> Overview: see [./SKILL-quickguide.md](./SKILL-quickguide.md)

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `<brief>` | Yes | Description of the task to plan (feature, bug fix, refactor) |
| `--light` | No | Generate a lightweight proposal instead of a full plan |
| `--plan` | No | Force single-plan mode (skip auto-detection) |
| `--roadmap` | No | Generate a full product roadmap with dependency-aware execution waves |
| `--from-spec <path>` | No | Parse roadmap from a pre-filled spec file. Use with `--roadmap` |
| `--auto` | No | Auto-generate roadmap from project reference files. Use with `--roadmap` |
| `--only-unimplemented` | No | Scope the roadmap's requirements-extraction pass to REQ items whose section lacks a `STATUS: implemented` / `STATUS: established` marker (legacy uppercase `STATUS: IMPLEMENTED` also honored). Use with `--roadmap --auto`. Useful on established projects where a fresh roadmap should cover only the open-item delta. |
| `--framing metacomm` | No | Frame the brief as a designer's metacommunication message (I/you phrasing) |
| `--review <level>` | No | Override complexity-gated review depth. Valid: `light`, `standard`, `deep` |

# Make a plan

> Rationale for design choices and historical context: see `SKILL-rationale.md` in this directory.

> **`/seja-setup`** scaffolds topology-WHAT (stack, directory layout, CLAUDE.md, rules, smoke-test infra). **`/design`** defines design-intent-WHAT and WHY (entities, permissions, metacomm, personas, standards, constitution). **`/plan`** defines HOW to build it and WHY those hows. Setup creates, design refines, plan schedules.

## Design Guard

Before planning, verify `project/conventions.md` exists in `product-design/`. If missing, stop and tell the user: "No project design found. Run `/design` first to define your project's stack, conventions, and domain model." If present, proceed.

If there are no arguments, ask for the brief.

## Mode Detection

1. **Explicit override**: `--light` -> [Lightweight Proposal Workflow](#lightweight-proposal-workflow); `--roadmap` -> [Roadmap Workflow](#roadmap-workflow); `--plan` -> standard workflow below. Skip auto-detection.

2. **Auto-detection** (neither `--plan` nor `--roadmap` present): score the brief against signals.

   | Signal | Points toward |
   |---|---|
   | Brief mentions >=3 distinct entities, resources, or features | Roadmap |
   | Brief spans >=2 architectural layers (model + API + UI) | Roadmap |
   | Brief mentions multiple pages, screens, or user flows | Roadmap |
   | Brief describes a single bug, fix, or refactor | Single plan |
   | Brief references a specific file, component, or endpoint | Single plan |
   | Brief scope fits comfortably in <=12 plan steps | Single plan |

   Majority wins.

3. **Confirmation gate**: If single plan, proceed without asking. If roadmap, present the recommendation as a quick roadmap/plan AskUserQuestion: *"This brief spans multiple entities/layers. Recommend generating a **roadmap** with dependency-aware waves rather than a single plan. Proceed with roadmap, or force a single plan?"*

## Common Steps (all modes)

Shared execution steps referenced by every mode's delta table. Each mode's step numbering stays intact; delta tables cite Common Steps by `C<n>` label.

- **C1. Pre-skill**: Run /pre-skill "plan" $ARGUMENTS[0] to load general instructions and register the brief.
- **C2. Reserve ID**: Run `python .claude/skills/scripts/reserve_id.py --type <type> --title '<short title>'`. `<type>` is `plan` (standard single-plan), `proposal` (`--light`), or `roadmap` (`--roadmap` Modes 1 and 2). Mode 3 skips this step.
- **C3. Artifact header**: Header shape `# <Kind> <id> | <prefix><scope> | <current datetime> | <short title>`. For plans, extend with ` | Review: <depth>` and follow with `plan_format_version: 1` on the next line; metacomm framing inserts `METACOMM |` after prefix-scope; advisory Q&A source adds `source: advisory-<id>`. Proposals include `plan_format_version: 1` (see `.claude/references/template/proposal.md`). Roadmaps follow `.claude/references/template/roadmap-summary.md`. Output folders: `${PLANS_DIR}`, `${PROPOSALS_DIR}`, `${ROADMAP_DIR}` (see project/conventions.md); Mode 3 writes to `<target>/specs/`.
- **C4. Decision-point rationale**: phrase every AskUserQuestion option (or text-based decision-point option) per the Decision-point rationale convention in `general/constraints.md`: `Recommended when ...` / `NOT recommended when ...`.
- **C5. Review Depth Override**: the `--review <light|standard|deep>` flag overrides complexity-gated depth. Effective depth = `max(auto, floor, flag)` with ordering `light < standard < deep`, where `auto` = complexity gate, `floor` = `MINIMUM_REVIEW_DEPTH` from `project/conventions.md` (default `light`), `flag` = `--review` value. If effective differs from auto, log: "Review depth overridden: auto=`<auto>`, floor=`<floor>`, flag=`<flag>`, effective=`<effective>`". Update the plan header's `Review:` field to match effective. Applies to the standard single-plan workflow; `--light` reviews lightly inline; `--roadmap` delegates to generated plans.
- **C6. Post-skill**: Run /post-skill <id> after the user confirms commit. For `--roadmap` Modes 1 and 2, the roadmap run owns the commit; per-plan invocations generated inline skip their own post-skill (see Mode 1 step 9).

## Framing

- **Default**: the brief is a technical description (feature, bug, refactor).
- **Metacomm** (`--framing metacomm`): the brief is a designer's metacommunication message using "I" (designer) / "you" (user) phrasing. Record the brief **verbatim** in the plan (see `general/shared-definitions.md` Verbatim rule and Phrasing rule). Interpret it as the designer telling the user what they can do, how, when, with what purpose, or why, and ensure the generated plan delivers that. All metacomm text the agent generates (summaries, intention notes, per-feature intents) must also use I/you phrasing.

See [Metacomm framing -- additional context](#metacomm-framing--additional-context) for details.

### Metacomm framing -- additional context

1. **Read existing intentions**: if `product-design/product-design-as-intended.md` exists, read it before generating the plan -- it holds per-feature metacommunication intentions.

2. **Contradiction detection**: if the new brief contradicts an existing intention (e.g., brief says "remove tagging" but an existing intention describes tagging), emit a `Metacomm contradiction` warning listing the brief's directive, the conflicting intention (quoted), and a recommendation (update the intention, or confirm the brief supersedes it).

3. **Append metacomm intention note** to the plan file:
   ```markdown
   ## Metacomm Intention
   - **Summary**: <one-sentence summary of the metacommunication message this plan implements>
   - **Source**: agent (metacomm)
   ```
   Consumed by `/explain spec-drift` or `/post-skill` to keep `project/product-design-as-intended.md` in sync.

## Dispatch

Once Mode Detection has resolved the active mode, read the corresponding internal skill's `SKILL.md` via the Read tool (not the Skill tool -- the Skill tool would re-enter dispatch and fire lifecycle hooks twice) and execute its instructions inline as part of this skill's flow. Pre-skill (C1) and the Design Guard have already run in the wrapper; the internal owns steps 2-N of its mode-specific workflow and invokes C6 (post-skill) at the end per its own step list. Internals reference the C1-C6 labels defined in the `## Common Steps (all modes)` table above and the Framing prose above; they do not re-define these.

| Mode | Internal SKILL.md path |
|------|------------------------|
| Standard single-plan (`--plan` or auto-detected single) | `.claude/skills/_internal/plan/standard/SKILL.md` |
| Lightweight proposal (`--light`) | `.claude/skills/_internal/plan/light/SKILL.md` |
| Roadmap (`--roadmap` + sub-modes 1/2/3) | `.claude/skills/_internal/plan/roadmap/SKILL.md` |
