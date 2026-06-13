---
name: communicate
description: "Generate tailored communication material for a specific audience segment."
argument-hint: "<audience> [--format md|html|both] [--all] [--source <advisory-file>]"
compatibility: "Designed for Claude Code with the SEJA harness"
metadata:
  last-updated: 2026-03-30 00:00 UTC
  version: 1.1.0
  category: utility
  context_budget: standard
  references:
    - general/communication.md
    - project/product-design-as-coded.md
    - general/shared-definitions.md
    - general/report-conventions.md
---

> Overview: see [./SKILL-quickguide.md](./SKILL-quickguide.md)

# Communicate

Generate tailored communication material for a specific stakeholder audience segment.

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `<audience>` | Yes | Target audience segment: `evaluator(s)` / `client(s)` / `end-user(s)` / `academic(s)`, or tags `EVL` / `CLT` / `USR` / `ACD`. Not required if `--all` is used |
| `--format <type>` | No | Output format: `md`, `html`, or `both`. Default: `both` |
| `--all` | No | Generate material for all audience segments in parallel |
| `--source <file>` | No | Path to existing advisory or markdown file to reformat for the target audience |
| `--deep` | No | Include Deep-dive content sections |

If the audience is missing and `--all` is not set, present an interactive menu.

## Definitions

Output folder: `${COMMUNICATION_DIR}/<YYYY-MM-DD>` where `<YYYY-MM-DD>` is the current UTC date.
Filename pattern: `communication-<id>-<audience-slug>.<ext>`

All material generated on the same date shares the same date folder. Material generated on different dates lives in different folders, creating a versioned history.

Example directory structure:
```
${COMMUNICATION_DIR}/
├── 2026-03-28/
│   ├── index.md
│   ├── index.html
│   ├── communication-000012-evaluators.md
│   ├── communication-000012-evaluators.html
│   ├── communication-000013-clients/
│   │   ├── index.md
│   │   ├── index.html
│   │   ├── product-vision.md
│   │   ├── product-vision.html
│   │   ├── status-reporting.md
│   │   └── status-reporting.html
│   ├── communication-000014-end-users.md
│   └── communication-000014-end-users.html
├── 2026-04-15/
│   ├── index.md
│   ├── index.html
│   ├── communication-000021-academics.md
│   ├── communication-000021-academics.html
│   ├── communication-000022-evaluators.md
│   └── communication-000022-evaluators.html
```

When the content for a single audience naturally splits into distinct topics (e.g., a product vision and a status reporting template for clients), create a subfolder named `communication-<id>-<audience-slug>/` containing an `index.md` that links to the individual topic files. All files within the subfolder get both `.md` and `.html` versions. Use a single file when the content forms a cohesive narrative.

The sequential ID is globally unique across all artifact types (6-digit, zero-padded). Reserve it by running `python .claude/skills/scripts/reserve_id.py --type communication --title '<audience-slug>'` before writing any content.

## Batch Mode

When `--all` is provided, generate material for all 4 active audience segments in parallel.

This mode follows the [Batch Execution Pattern](../../../.claude/references/general/batch-execution-pattern.md). See that reference for the canonical 6-phase orchestration pattern. Below are the skill-specific parameters.

### Batch Execution

1. Run /pre-skill once for the entire batch.
2. Reserve IDs for all 4 audiences upfront: `python .claude/skills/scripts/reserve_id.py --type communication --title '<audience-slug>'` once per audience.
3. Compute the date folder path: `${COMMUNICATION_DIR}/<YYYY-MM-DD>` (UTC). Create the folder if it does not exist.
4. Launch one `communication-generator` agent per audience in parallel (using the prompt from `.claude/agents/communication-generator.md`). Each agent receives:
   - The resolved audience tag and audience file path
   - The Diataxis mapping file path
   - Project context file paths (conceptual design, conventions, communication style)
   - The assigned ID and output file path
   - The format flag and deep flag
5. Collect results and verify all files (both `.md` and `.html`) were written. On partial failure, the user can re-run `/communicate <failed-audience>` individually.
6. Run /post-skill once for the entire batch.

## Skill-specific Instructions

1. Run /pre-skill "communicate" $ARGUMENTS to add general instructions to the context window.

2. **Parse arguments and resolve audience:**

   Map aliases to canonical tags:
   - `evaluator` / `evaluators` -> EVL
   - `client` / `clients` -> CLT
   - `end-user` / `end-users` -> USR
   - `academic` / `academics` -> ACD

   If the audience is not provided and `--all` is not set, use the AskUserQuestion tool to ask which audience segment (if AskUserQuestion is not available, present as a numbered text list), with these options:
   - "1. Evaluator (EVL) -- CTO, tech lead, engineering manager assessing adoption"
   - "2. Client (CLT) -- Project commissioner, business owner, funding partner of the product"
   - "3. End User (USR) -- Person using the software built with the harness"
   - "4. Academic (ACD) -- Researcher in semiotic engineering, HCI, AI-assisted development"

   If in **batch mode** (`--all`), skip to the Batch Execution flow above.

3. **Determine output path:**

   Compute the date folder: `${COMMUNICATION_DIR}/<YYYY-MM-DD>` (current UTC date). Create it if it does not exist.
   Reserve the next global ID by running `python .claude/skills/scripts/reserve_id.py --type communication --title '<audience-slug>'`. Use the returned 6-digit ID.

4. **Launch generator agent:**

   Launch the `communication-generator` agent (Agent tool, subagent_type=`general-purpose`, using the prompt from `.claude/agents/communication-generator.md`) with the following context:
   - `audience_tag`: the resolved canonical tag (EVL/CLT/USR/ACD)
   - `audience_file_path`: `.claude/references/general/communication/<audience>.md`
   - `diataxis_mapping_path`: `.claude/references/general/communication/diataxis-mapping.md`
   - `project_context`: paths to `product-design/product-design-as-coded.md`, `product-design/conventions.md` (or template fallback), `product-design/communication-style.md` (or template fallback)
   - `output_path`: the full path computed in step 3
   - `output_id`: the reserved ID from step 3
   - `format`: the `--format` flag value (default: `both`)
   - `deep`: whether `--deep` was passed
   - `source_file_path`: the `--source` file path if provided, or null

   After the agent returns, verify that the expected output file(s) exist. Display a brief result summary to the user (audience, output path).

5. **Date-folder index:**

   After writing the output, check whether the date folder (`${COMMUNICATION_DIR}/<YYYY-MM-DD>`) contains more than one communication artifact (files or subfolders). If it does, create or update an `index.md` at the root of the date folder that lists all artifacts with relative links. The index should include a title (`# Communications -- <YYYY-MM-DD>`) and a bullet list with each artifact's ID, audience, and link. Generate the HTML version of the index according to the `--format` flag (same rules as the agent's output step).

   If the date folder contains only one artifact, skip the index -- it adds no navigational value.

6. Run /post-skill <id>.
