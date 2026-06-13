---
name: reflect
description: "On-demand reflection anchored on specific plans, research reports, or other artifacts. I summarize the artifacts you choose, ask what stands out, and record your reflection."
argument-hint: "[--telemetry [--since 30d] [--skill <name>] [--dry-run]] | [--deep [scope] [--since 30d]]"
compatibility: "Designed for Claude Code with the SEJA harness"
metadata:
  last-updated: 2026-04-12 02:12 UTC
  version: 2.0.0
  category: analysis
  context_budget: standard
  eager_references:
    - project/conventions.md
    - general/constraints.md
  references:
    - project/conventions.md
    - general/constraints.md
    - general/shared-definitions.md
    - general/skill-graph.md
    - general/coding-standards.md
---

> Overview: see [./SKILL-quickguide.md](./SKILL-quickguide.md)

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--telemetry` | No | Switch to statistical telemetry mining mode (legacy V1 flow). |
| `--deep` | No | Switch to deep reflection mode with visualization and narrative. |
| `--scope <keyword>` | No | Free-text scope keyword for `--deep` mode. Filters by skill name, brief text, tags, filenames. |
| `--since <duration>` | No | Time window for `--telemetry` or `--deep` mode. Accepts ISO datetime or `Nd` suffix. Default: `30d`. |
| `--skill <name>` | No | Filter telemetry to a single skill in `--telemetry` mode. |
| `--dry-run` | No | Print report to stdout without writing to disk (applies to `--telemetry` mode). |

# Reflect

Output folder: `${REFLECTIONS_DIR}` (see project/conventions.md)
Filename pattern: `reflection-<id>-<truncated short title slug>.md` (6-digit zero-padded ID)
Header pattern: `# Reflection <id> | <current datetime> | <short title>` (macro-index regex requires this exact shape)

## Mode detection

If `--deep` is present in the arguments, route to the [Deep workflow](#deep-workflow---deep) below. If `--telemetry` is present, route to the [Telemetry workflow](#telemetry-workflow---telemetry). Otherwise, run the conversational workflow.

## Conversational workflow (default)

### Skill-specific Instructions

1. Run `/pre-skill "reflect" $ARGUMENTS` to add general instructions to the context window.

2. Reserve the next global ID by running `python .claude/skills/scripts/reserve_id.py --type reflection --title '<short title synthesized from scope>'`. Capture the returned 6-digit ID.

3. **Step A -- Pick scope.** Ask the user via AskUserQuestion which artifacts to reflect on. Each option carries rationale per the Decision-point rationale convention in `.claude/references/general/constraints.md`:

   > "What would you like to reflect on?"

   Options:
   - **Recent plans** -- I list the last 5-10 plans from `${PLANS_DIR}` by mtime and you pick one or more. Recommended when you just finished a block of implementation work and want to step back. NOT recommended when your question is about a *sequence* of decisions rather than a single plan.
   - **Recent research** -- I list the last 5-10 research reports from `${RESEARCH_DIR}` and `${ADVISORY_DIR}` (historical) by mtime and you pick one or more. Recommended when you want to re-examine a design decision after seeing how it played out. NOT recommended when the research has not yet been implemented.
   - **A specific artifact by ID** -- you give me an ID (e.g., `plan-000295`, `research-000300`, `advisory-000300`) and I pull it. Recommended when you already know which artifact the reflection is about. NOT recommended when you are casting around for a topic.
   - **A time window** -- you give me a date range; I list all artifacts in that window grouped by type. Recommended when you want to reflect on a *period* (e.g., "last week"). NOT recommended when the period is shorter than a single session.
   - **Free-form** -- no artifact anchor; I give you an empty note. Recommended when the thing you want to reflect on is not yet in any artifact. NOT recommended when there is an artifact you could point at -- anchored reflections are easier to find later.

4. **Resolve the selection to artifact IDs.**

   - **Recent plans / Recent research**: List the last 10 files in the corresponding directory(ies) by mtime. For Recent research, scan both `${RESEARCH_DIR}` and `${ADVISORY_DIR}` (historical). Present them as a numbered text list (not AskUserQuestion -- the user may want to pick multiple). Capture their selection as a list of artifact IDs.
   - **A specific artifact by ID**: Prompt the user for the ID(s) via plain text. Parse the response into artifact IDs.
   - **A time window**: Prompt for start/end dates via plain text. Glob `${OUTPUT_DIR}/**/*.md`, filter by mtime, group by type, present the list, and let the user pick.
   - **Free-form**: No artifact resolution needed. Skip to Step C with an empty summary.

5. **Step B -- Summarize chosen artifacts.** Run `python .claude/skills/reflect/summarize_artifacts.py <id1> <id2> ...` to produce the narrative summary block. Capture the stdout output. Present it to the user so they can see what they are reflecting on.

6. **Step C -- Reflection prompt.** Ask the user one open-ended question via plain text (NOT AskUserQuestion -- reflection cannot be multiple choice):

   > "What stands out when you look at these now that you did not see when you wrote them?"

   Capture the user's free-text response verbatim.

7. **Step D -- Write the reflection file.** Compose a report at `${REFLECTIONS_DIR}/reflection-<id>-<slug>.md` with:

   ```markdown
   # Reflection <id> | <current datetime> | <short title>

   ## Artifacts reflected on

   <bullet list from summarize_artifacts.py output, with clickable markdown links>

   ## Summary

   <narrative summaries from Step B>

   ## Reflection

   <user's free-text response from Step C, verbatim>

   ## Follow-ups

   <open questions for future investigation, if any>
   ```

8. Run `/post-skill <reflection-id>` to commit the reflection report.

## Strictly non-prescriptive rule

`/reflect` writes observations and the user's own words, not prescriptions. The skill never writes "you should", "consider changing X", "we recommend", or similar. This convention is enforced by a test in `test_generate_reflection_report.py` that scans the generated report for forbidden substrings. The `--deep` narrative output is also covered: past-tense only, no "you should" / "consider" / "we recommend", ends with the "What to do with this" hand-off paragraph pointing to `/research`.

---

## Deep workflow (--deep)

> Deep reflection mode. Reads telemetry and briefs within a time window, optionally filtered by a scope keyword, and produces an event matrix visualization, a transition graph, and a practice evolution narrative.

### Skill-specific Instructions

1. Run `/pre-skill "reflect" $ARGUMENTS` to add general instructions to the context window.

2. Reserve the next global ID by running `python .claude/skills/scripts/reserve_id.py --type reflection --title '<short title synthesized from scope>'`. Capture the returned 6-digit ID.

3. Parse arguments: `--deep [scope] [--since <duration>]`. Scope is an optional free-text keyword; `--since` accepts `Nd` or ISO datetime (default: `30d`).

4. Run scope resolution:

   ```text
   python .claude/skills/reflect/reflect_deep_scope.py \
       --scope <keyword> \
       --since <duration> \
       --briefs <briefs_path> \
       --telemetry <telemetry_path> \
       --output-dir <output_dir>
   ```

   Capture the `ScopeResult` JSON from stdout.

5. Present scope resolution summary to user: match counts by provenance, total records in window, date range. If zero matches, ask user to refine scope (do not proceed with empty data).

6. Run the event matrix visualization:

   ```text
   python .claude/skills/reflect/reflect_event_matrix.py \
       --input <filtered_window_json> \
       --output-prefix ${REFLECTIONS_DIR}/reflection-<id>-event-matrix \
       --scope <label> \
       --date-range <start>,<end>
   ```

   Writes `${REFLECTIONS_DIR}/reflection-<id>-event-matrix.{vl.json,svg,html}`.

7. Run the transition graph visualization:

   ```text
   python .claude/skills/reflect/reflect_transition_graph.py \
       --input <filtered_window_json> \
       --output-prefix ${REFLECTIONS_DIR}/reflection-<id>-transitions \
       --scope <label> \
       --date-range <start>,<end>
   ```

   Writes `${REFLECTIONS_DIR}/reflection-<id>-transitions.{dot,svg,html}`.

8. Compose the practice evolution narrative from the filtered data. Use past-tense chronicle form. Include anchored markdown links `[<artifact-id>](<relative-path>)` to referenced output files. End with the "What to do with this" hand-off paragraph pointing to `/research`.

9. Write `${REFLECTIONS_DIR}/reflection-<id>-<slug>.md` with:

   ```markdown
   # Reflection <id> | <current datetime> | <short title>

   ## Scope and window

   <scope keyword, date range, match counts by provenance>

   ## Event matrix

   [event-matrix.html](reflection-<id>-event-matrix.html) | [event-matrix.svg](reflection-<id>-event-matrix.svg)

   ## Transition graph

   [transitions.html](reflection-<id>-transitions.html) | [transitions.svg](reflection-<id>-transitions.svg)

   ## Practice evolution

   <past-tense narrative from step 8>

   ## Companion files

   <bullet list of all companion visualization files with relative links>
   ```

10. Run `/post-skill <reflection-id>` to commit the reflection report.

---

## Telemetry workflow (--telemetry)

> Statistical telemetry mining mode. Reads `${OUTPUT_DIR}/telemetry.jsonl` and surfaces patterns via five analysis primitives. This is the original V1 flow from plan-000295, preserved as an opt-in secondary mode.

### Skill-specific Instructions

1. Run `/pre-skill "reflect" $ARGUMENTS` to add general instructions to the context window.

2. Reserve the next global ID by running `python .claude/skills/scripts/reserve_id.py --type reflection --title '<short title synthesized from the window>'`. Capture the returned 6-digit ID.

3. Parse arguments:
   - Resolve `--since`: accept either an ISO datetime or a relative `Nd` suffix (`30d`, `14d`, `7d`). Default: `30d`.
   - Resolve `--skill`: optional single-skill filter.
   - Resolve `--dry-run`: boolean flag.

4. Load the telemetry window: read `${OUTPUT_DIR}/telemetry.jsonl`, filter by `timestamp >= <resolved since cutoff>`, and optionally filter by `skill == <name>`. Load the corresponding briefs map from `${BRIEFS_FILE}` so the stuck-loops primitive can compute Jaccard similarity over brief text.

5. **V1 note -- `user_revised_output` is not computed in V1**: this field exists on every telemetry record (written as `null` by post-skill) to reserve its shape for a future measurement. V1 does **not** populate the field. The `reflect_revision_rate` primitive reads the window, sees that no record has a non-null value, and degrades gracefully with the documented reason. Leave the window untouched and move on to step 6.

6. Invoke the orchestrator with the reserved ID:

   ```text
   python .claude/skills/reflect/generate_reflection_report.py \
       --since <resolved since> \
       --reflection-id <reserved id> \
       --title "<synthesized title>" \
       [--skill-filter <name>] \
       [--dry-run]
   ```

   - Exit 0 on success; prints the output path on write, or the report body when `--dry-run`.
   - Exit 2 on argument errors.

   Always omit `--out` so the orchestrator writes to `${REFLECTIONS_DIR}/reflection-<id>-<slug>.md` by default.

7. If `--dry-run` was requested, stop here and surface the composed report body to the user without writing to disk or committing.

8. If not `--dry-run`, confirm that the file landed at the expected path. Read the first line back to verify the H1 header matches `# Reflection <id> | <datetime> | <title>`.

9. Run `/post-skill <reflection-id>` to commit the reflection report.

## V1 analysis primitives

Each primitive lives in `.claude/skills/scripts/` and exposes an `analyze(window, ...)` function. The orchestrator embeds each primitive's observation sentences verbatim into the report body.

- **Sequence mining** -- `reflect_sequence_mining.py`
- **Duration anomalies** -- `reflect_duration_anomalies.py`
- **Revision rate** -- `reflect_revision_rate.py` (V1 always degrades; `user_revised_output` not yet computed)
- **Stuck loops** -- `reflect_stuck_loops.py`
- **Decision reversals** -- `reflect_decision_reversals.py`

## Output location

Reports land at `${REFLECTIONS_DIR}/reflection-<id>-<slug>.md`. `generate_macro_index.py` picks up the new report automatically on post-skill step 8's commit pipeline. The macro-index scanner is anchored on the H1 regex `^#\s+Reflection\s+(\d+)\s*\|\s*([\d\-: UTC]+)\s*\|\s*(.+)`, so the header shape must not be edited.
