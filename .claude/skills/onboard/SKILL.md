---
name: onboard
description: "Generate a tailored onboarding plan for a new team member based on their role and expertise level."
argument-hint: "<role-family> <expertise-level> [name] [--area <focus-area>] [--format md|html|both] [--all] [--all-levels <role>] [--all-roles <level>] [--batch <spec-list>]"
compatibility: "Designed for Claude Code with the SEJA harness"
metadata:
  last-updated: 2026-03-28 18:45 UTC
  version: 1.0.0
  category: utility
  context_budget: standard
  references:
    - general/onboarding.md
    - project/product-design-as-coded.md
    - general/shared-definitions.md
    - general/report-conventions.md
---

> Overview: see [./SKILL-quickguide.md](./SKILL-quickguide.md)

# Onboard

Generate a tailored onboarding plan for a new project team member.

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `<role-family>` | Yes | Role family: `builder` / `shaper` / `guardian` (or tags `BLD` / `SHP` / `GRD`). Combinations allowed. Not required if `--all`, `--all-levels`, or `--all-roles` is used |
| `<expertise-level>` | Yes | Expertise level: `L1`-`L3` or aliases `contributor` / `junior` / `mid` / `expert` / `senior` / `leader` / `staff` / `lead`. Not required if `--all`, `--all-levels`, or `--all-roles` is used |
| `[name]` | No | Name of the new team member for personalization |
| `--area <focus>` | No | Focus area: `backend`, `frontend`, `api`, `auth`, `payments`, etc. |
| `--format <type>` | No | Output format: `md`, `html`, or `both`. Default: `both` |
| `--all` | No | Generate onboarding plans for all role x level combinations (9 plans: 3 roles x 3 levels) |
| `--all-levels <role>` | No | Generate plans for all levels of a single role family (3 plans) |
| `--all-roles <level>` | No | Generate plans for all role families at a single level (3 plans) |
| `--batch <specs>` | No | Generate multiple onboarding plans in parallel. Semicolon-separated specs |

If arguments are missing (and not in batch or --all mode), ask the user interactively.

## Definitions

Output folder: `${ONBOARDING_PLANS_DIR}/<YYYY-MM-DD>` where `<YYYY-MM-DD>` is the current UTC date.
Filename pattern: `onboarding-<id>-<name-or-role-slug>.md` (6-digit zero-padded ID)

All plans generated on the same date share the same date folder, regardless of role or level. Plans generated on different dates live in different folders, creating a versioned history of onboarding material.

Example directory structure:
```
${ONBOARDING_PLANS_DIR}/
├── 2026-03-28/
│   ├── onboarding-000012-alice-bld-l1.md
│   ├── onboarding-000012-alice-bld-l1.html
│   ├── onboarding-000013-bob-shp-l2.md
│   ├── onboarding-000013-bob-shp-l2.html
│   ├── onboarding-000014-grd-l1.md
│   └── onboarding-000014-grd-l1.html
├── 2026-04-15/
│   ├── onboarding-000021-carol-bld-l1.md
│   ├── onboarding-000021-carol-bld-l1.html
│   ├── onboarding-000022-dave-bld+grd-l3.md
│   └── onboarding-000022-dave-bld+grd-l3.html
```

When both formats are generated, the `.md` and `.html` files share the same ID and slug. Use `--format md` or `--format html` to produce only one of the two.

The sequential ID is globally unique across all artifact types (6-digit, zero-padded). Reserve it by running `python .claude/skills/scripts/reserve_id.py --type onboarding --title '<name-or-role-slug>'` before writing any content.

## Batch Mode

When `--batch`, `--all`, `--all-levels`, or `--all-roles` is provided, generate multiple onboarding plans **in parallel** using the Agent tool.

This mode follows the [Batch Execution Pattern](../../../.claude/references/general/batch-execution-pattern.md). See that reference for the canonical 6-phase orchestration pattern. Below are the skill-specific parameters.

### Batch Triggers

| Flag | Combinations | Description |
|------|-------------|-------------|
| `--all` | 9 (3 roles x 3 levels) | All single-role combinations: BLD-L1 through GRD-L3 |
| `--all-levels <role>` | 3 | All levels for one role: `<role>-L1`, `<role>-L2`, `<role>-L3` |
| `--all-roles <level>` | 3 | All roles for one level: `BLD-<level>`, `SHP-<level>`, `GRD-<level>` |
| `--batch <specs>` | N | Explicit semicolon-separated spec list (see below) |

For `--all`, `--all-levels`, and `--all-roles`, the spec list is auto-generated from the enumerated combinations. Each auto-generated spec uses `<role> <level>` format with no name or area (e.g., `builder L1`). The `--format` flag applies to all generated plans.

### Batch Spec Format

The spec list is a semicolon-separated list of individual onboarding specs:

```
--batch "builder L1 Alice --area backend; shaper L2 Bob; guardian L1; builder+guardian L3 Carol"
```

Each spec follows the same format as the single-plan arguments: `<role-family> <expertise-level> [name] [--area <focus-area>]`.

### Batch Execution

1. Parse the spec list into individual onboarding specs.
2. Run /pre-skill once for the entire batch.
3. Reserve IDs for all specs upfront: `python .claude/skills/scripts/reserve_id.py --type onboarding --title '<name-or-role-slug>'` once per spec.
4. Compute the date folder path: `${ONBOARDING_PLANS_DIR}/<YYYY-MM-DD>` (UTC). Create the folder if it does not exist.
5. Launch one `onboarding-generator` agent per spec in parallel (using the prompt from `.claude/agents/onboarding-generator.md`). Each agent receives:
   - The resolved role tags and level for its spec
   - Role family file path(s) and expertise level file path
   - Project context file paths (conceptual design, conventions)
   - The assigned ID and output file path
   - Name and area if provided
   - `format`: the top-level `--format` flag value (default: `both`). This is a single top-level flag, not a per-spec option -- all specs in the batch share the same format.
6. Collect results and verify all files were written. On partial failure, the user can re-run `/onboard` for just the failed specs individually.
7. Run /post-skill once for the entire batch.

### Batch Interaction

If a batch spec is incomplete (e.g., missing level), resolve all incomplete specs with the user before launching any agents.

## Skill-specific Instructions

1. Run /pre-skill "onboard" $ARGUMENTS to add general instructions to the context window.

2. **Parse arguments and resolve role/level:**

   Map aliases to canonical tags:
   - Role: `builder` -> BLD, `shaper` -> SHP, `guardian` -> GRD
   - Level: `contributor` -> L1, `junior` -> L1, `mid` -> L1, `expert` -> L2, `senior` -> L2, `leader` -> L3, `staff` -> L3, `lead` -> L3

   If `--all` is provided: skip interactive prompts, enumerate all 9 combinations (BLD-L1, BLD-L2, BLD-L3, SHP-L1, SHP-L2, SHP-L3, GRD-L1, GRD-L2, GRD-L3), and go to the Batch Execution flow.

   If `--all-levels <role>` is provided: resolve the role, enumerate L1-L3 for that role (3 combinations), and go to the Batch Execution flow.

   If `--all-roles <level>` is provided: resolve the level, enumerate BLD/SHP/GRD for that level (3 combinations), and go to the Batch Execution flow.

   If the role family is not provided or cannot be inferred (and no `--all` variant is used), use the AskUserQuestion tool to ask (if AskUserQuestion is not available, present as a numbered text list), with these options:
   - "1. Builder (BLD) -- Developer, DevOps, infra engineer"
   - "2. Shaper (SHP) -- Product designer, product manager, UX researcher, analyst"
   - "3. Guardian (GRD) -- QA, security, tech lead, engineering manager"
   - "4. Builder + Guardian -- Tech lead who codes, security-focused developer"
   - "5. Shaper + Builder -- Designer or PM using AI tools directly (writing prompts, reviewing plans, working alongside code)"

   If the expertise level is not provided or cannot be inferred (and no `--all` variant is used), use the AskUserQuestion tool to ask (if AskUserQuestion is not available, present as a numbered text list), with these options:
   - "1. L1 Contributor -- Junior to mid-level, individual contributor (0-5 years)"
   - "2. L2 Expert -- Senior, deep expertise, needs trade-off context (5-10 years)"
   - "3. L3 Leader -- Staff/Principal/Manager, strategic or people influence (10+ years)"

   Resolve the `--format` flag to one of `md`, `html`, or `both`. Default to `both` when the flag is absent. If the value is not one of those three, emit a one-line error ("Invalid --format value: expected md, html, or both") and abort.

   If in **batch mode** (`--batch`, `--all`, `--all-levels`, or `--all-roles`), skip to the Batch Execution flow above.

3. **Determine output path:**

   Compute the date folder: `${ONBOARDING_PLANS_DIR}/<YYYY-MM-DD>` (current UTC date). Create it if it does not exist.
   Reserve the next global ID by running `python .claude/skills/scripts/reserve_id.py --type onboarding --title '<name-or-role-slug>'`. Use the returned 6-digit ID.

4. **Launch generator agent:**

   Launch the `onboarding-generator` agent (Agent tool, subagent_type=`general-purpose`, using the prompt from `.claude/agents/onboarding-generator.md`) with the following context:
   - `role_tags`: the resolved canonical tag(s) (e.g., "BLD", "BLD+GRD")
   - `level`: the resolved level (L1-L5)
   - `name`: the team member's name (if provided)
   - `area`: the focus area (if `--area` was passed)
   - `role_file_paths`: `.claude/references/general/onboarding/<role>.md` for each role tag
   - `level_file_path`: `.claude/references/general/onboarding/<level>.md`
   - `project_context`: paths to `product-design/product-design-as-coded.md`, `product-design/conventions.md` (or template fallback)
   - `output_path`: the full path computed in step 3
   - `output_id`: the reserved ID from step 3
   - `format`: the `--format` flag value (default: `both`)

   After the agent returns, verify that the expected output file exists. Display a brief result summary to the user (role/level, name, output path).

5. Run /post-skill <id>.
