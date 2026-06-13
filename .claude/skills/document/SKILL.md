---
name: document
description: "Generate or update project documentation based on plan Docs: fields, auto-detection, or explicit type selection."
argument-hint: "<scope> [--plan <id>] [--auto-detect] [--type <readme|contextual-help|api-reference|drr|help-center|changelog>] [--since <ref>] [--full-history]"
compatibility: "Designed for Claude Code with the SEJA harness"
metadata:
  last-updated: 2026-04-01 16:42 UTC
  version: 1.0.0
  category: utility
  context_budget: standard
  references:
    - general/documentation-quality.md
    - general/report-conventions.md
---

> Overview: see [./SKILL-quickguide.md](./SKILL-quickguide.md)

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `<scope>` | Yes (unless --plan or --auto-detect) | What to document: a file path, module, feature name, or general topic |
| `--plan <id>` | No | Read Docs: fields from a plan file and generate documentation for each identified need |
| `--auto-detect` | No | Detect documentation needs from recent git changes using heuristics |
| `--type <type>` | No | Force a specific documentation type: readme, contextual-help, api-reference, drr, help-center, or changelog |
| `--since <ref>` | No | Override auto-detect bounding window. Accepts a date (`2026-04-01`), a git SHA, or `last` (since last `/document` run of any kind). Ignored by non-auto-detect modes |
| `--full-history` | No | Ignore per-doc-type bounding windows and apply the heuristic over the full recent git history (equivalent to pre-proposal behavior). Use when you want a clean-slate scan |

# Document

If there are no arguments, ask the user what they need documented.

## Mode Detection

- If `--plan` is present: read the plan file, extract all non-N/A Docs: fields, and generate documentation for each identified need.
- If `--auto-detect` is present: analyze recent git changes and apply the auto-detection heuristic to determine which documentation types are needed.
- If `--type` is present: generate the specified documentation type for the given scope.
- If bare scope only: infer the most appropriate documentation type from the scope content.

---

## Core Workflow

1. Run `/pre-skill "document" $ARGUMENTS[0]` to add general instructions to the context window.

2. Determine scope and documentation type using mode detection logic above. If `--plan`, read the plan file and collect all steps with non-N/A `Docs:` fields into a work list.

2a. **Compute per-doc-type bounding windows** (applies to `--auto-detect` only; skip for other modes):

   If `--full-history` is present, skip this step entirely (use unbounded heuristic).

   If `--since <ref>` is present, resolve it:
   - Date string (e.g., `2026-04-01`): use `git log --since="<ref>"` for all doc-types uniformly.
   - Git SHA: use `git log <ref>..HEAD` for all doc-types uniformly.
   - `last`: find the single most recent DONE `/document` row in `${BRIEFS_INDEX_FILE}` regardless of doc-type; use its Head SHA or Date as the uniform bound.

   Otherwise (default history-aware behavior):
   1. Read `${BRIEFS_INDEX_FILE}` (see project/conventions.md).
   2. For each doc-type in the auto-detection heuristic table (`api-reference`, `contextual-help`, `readme`, `drr`, `changelog`, `help-center`), scan the index for the most recent DONE row where:
      - `Skill` is `document`, AND
      - `Generated` column contains that doc-type (comma-separated match)
   3. If a matching row is found and has a non-empty `Head SHA`:
      - Check reachability: run `git merge-base --is-ancestor <head-sha> HEAD`. If reachable, use `git log <head-sha>..HEAD -- <relevant-file-patterns>` to get the change set for that doc-type's heuristic row.
      - If unreachable (rebase, squash-merge, GC'd): fall back to the row's `Date` timestamp via `git log --since="<date>"`. Annotate in the output: "SHA `<sha>` unreachable, using timestamp `<date>` as fallback."
   4. If no matching row exists for a doc-type (first run, or that type was never generated), leave the window unbounded for that type — apply the heuristic over full recent history (same as pre-proposal behavior).
   5. Print a summary of the resolved windows before proceeding:
      ```
      Auto-detect bounding windows:
        api-reference: since <sha> (2026-04-02)
        readme: since <sha> (2026-03-20)
        changelog: unbounded (no prior run)
        ...
      ```

   Pass these per-doc-type windows to the auto-detection heuristic in the next step. For each heuristic row, apply the matching window's git log filter when determining whether matching files changed.

2b. **Record document run metadata** (applies to all `/document` modes; execute after generation in step 3, before post-skill in step 4):

   1. Run `git rev-parse HEAD` to capture the current HEAD SHA (abbreviated to 10 chars).
   2. Determine the list of doc-types this run generated:
      - `--type <X>`: generated is `X`
      - `--auto-detect`: generated is the comma-separated list of doc-types the heuristic actually matched and produced
      - `--plan <id>`: generated is the comma-separated list of doc-types derived from the plan's Docs: fields
      - Bare scope: generated is the inferred doc-type
   3. Edit the current STARTED entry in `${BRIEFS_FILE}` (the one created by pre-skill for this invocation) to append: ` | SHA | <head-sha> | GENERATED | <comma-separated-types>`.

   This metadata is preserved when post-skill prepends `DONE | <datetime> |` to the same line, and is parsed by `generate_briefs_index.py` into the `Head SHA` and `Generated` columns of `${BRIEFS_INDEX_FILE}`.

3. **Launch generator agent(s):**

   Resolve the template path for each documentation type: check `product-design/docs/<type>.md` first; fall back to `.claude/references/template/docs/<type>.md`.

   **Single doc type** (bare scope, --type, or --auto-detect with one result):
   Launch the `document-generator` agent (Agent tool, subagent_type=`general-purpose`, using the prompt from `.claude/agents/document-generator.md`) with:
   - `doc_type`: the resolved documentation type
   - `scope`: the scope from arguments or auto-detection
   - `template_path`: the resolved template file path
   - `quality_guide_path`: `.claude/references/general/documentation-quality.md`
   - `project_context`: paths to `product-design/conventions.md` (or template fallback), `product-design/product-design-as-coded.md`
   - `output_path`: the appropriate project location for this doc type

   **Multiple doc types** (--plan with multiple non-N/A Docs: fields, or --auto-detect with multiple results):
   Launch one `document-generator` agent per doc type **in parallel**. Each agent receives the same structure as above, with its specific doc_type, scope, and output_path.

   After agents return, verify that expected output files exist. Display a result summary (doc types generated, output paths).

4. Run `/post-skill` to log the brief, commit, and suggest next steps.


---

## Auto-Detection Heuristic

| Change pattern | Suggested doc type |
|----------------|-------------------|
| API endpoint files (routes, controllers, schemas) changed | api-reference |
| New UI screen/component added | contextual-help |
| README-referenced features changed | readme |
| Architectural decisions made (plan review log has trade-offs) | drr |
| New user-facing features (FEATURE prefix) | changelog + help-center |
| Module files added/removed | module README (convention from standards) |

---

## Trigger Scoping Note

FEATURE and REDESIGN plans are always prompted for documentation in post-skill. FIX and CHORE plans trigger the documentation prompt only when their steps contain non-N/A Docs: fields.
