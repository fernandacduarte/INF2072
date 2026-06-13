---
name: research
description: "Answer questions about the codebase, architecture, or design decisions, logging Q&A pairs. With --inventory, catalog codebase elements matching a pattern."
argument-hint: "<question or topic> [--inventory <pattern>] [--deep]"
compatibility: "Designed for Claude Code with the SEJA harness"
metadata:
  last-updated: 2026-05-01 13:22 UTC
  version: 1.2.0
  category: analysis
  context_budget: standard
  eager_references:
    - project/product-design-as-coded.md
  references:
    - project/product-design-as-coded.md
    - project/product-design-as-intended.md
    - general/shared-definitions.md
    - general/report-conventions.md
    - general/review-perspectives.md
    - template/docs/drr.md
---

> Overview: see [./SKILL-quickguide.md](./SKILL-quickguide.md)

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `<question or topic>` | Yes | The question or topic to get advice on |
| `--inventory <pattern>` | No | Switch to inventory mode: catalog all codebase elements matching the pattern |
| `--deep` | No | Activate structured expert council debate for high-stakes decisions |

# Research

If there are no arguments, ask the user what they need advice on.

## Mode Detection

If `--inventory` is present, run the **Inventory workflow**; the brief is everything after `--inventory`. If `--deep` is present, set the deep-dive flag for the Research workflow and strip `--deep` from the brief (activates the expert council debate in step 5).

---

## Inventory Workflow

Output folder: `${INVENTORIES_DIR}` (see project/conventions.md). Filename pattern: `inventory-<id>-<truncated short title slug>.md` (6-digit zero-padded ID).

If there is no brief after `--inventory`, ask for the brief.

1. Run /pre-skill "research" $ARGUMENTS[0].

2. Reserve the next global ID: `python .claude/skills/scripts/reserve_id.py --type inventory --title '<short title>'`.

3. Search the source code for all elements mentioned in the brief, including related enumerations, constants, CSS classes, files, and other relevant elements.

3. Save the information to the output file, including:
- *header*: `# Inventory <id> | <prefix><scope> | <current datetime> | <short title>`
- *user brief*, *agent interpretation*, *files* -- per .claude/references/general/report-conventions.md
- *inventory*: no predefined structure here

4. Output the inventory id.

5. Run /post-skill <id> with `skip_qa_log: true` (inventory mode has no Q&A). See `.claude/skills/post-skill/SKILL.md` step 3 for the `skip_qa_log` contract.

---

## Research Workflow (default)

### Definitions

Output folder: `${RESEARCH_DIR}` (see project/conventions.md). Filename pattern: `research-<id>-<truncated short title slug>.md` (6-digit zero-padded ID).

### Skill-specific Instructions

1. Run /pre-skill "research" $ARGUMENTS[0].

2. Reserve the next global ID: `python .claude/skills/scripts/reserve_id.py --type research --title '<short title>'`.

3. **Load references on demand** from the "Available references" list emitted by pre-skill:
   - `project/product-design-as-intended.md` when comparing current vs. target design
   - `general/shared-definitions.md` when domain terminology is ambiguous
   - `general/report-conventions.md` before writing the research report
   - `general/review-perspectives.md` before evaluating from multiple perspectives

4. Research the question thoroughly, interviewing the user about every aspect until you have a complete understanding of their question, goals, constraints, and context. If necessary, read the codebase, architecture docs, design docs, and any other relevant files. Use Read, Search, and WebSearch without asking for authorization. If brief if about finding solutions, Search/WebSearch for relevant existing and analogous solutions. 

5. **Expert analysis** -- evaluate from multiple perspectives.
   - **Standard mode** (no `--deep`): Launch the `research-reviewer` agent (Agent tool, subagent_type=`research-reviewer`) with the question, context files, and review depth. Use its perspective-by-perspective output as input to step 6.
   - **Deep-dive mode** (`--deep`): Launch the `council-debate` agent (subagent_type=`council-debate`) with the question, selected council members, and context. It runs a 2-round structured debate across a 5-7 member council. Request brief-specific roles based on the question's domain (e.g., Agentic AI expert for agent questions, Data engineer for data pipeline questions). Use its synthesis as input to step 6. Council member and debate-format details live in `.claude/agents/council-debate.md`.

6. **Perspective synthesis** -- evaluate the question against all applicable perspectives from `general/review-perspectives.md`. In deep-dive mode, map each expert's positions to the relevant perspectives. For each relevant perspective, justify recommendations with pros and cons. Search the web for established and emerging best practices and incorporate them.

7. Answer the user's question with clear, actionable recommendations.

7b. **Prepare telemetry `advisory_decisions` and `research_decisions`** (dual-key during the transition window; TRANSITION (plan-000468): both keys carry identical payload, `research_decisions` is the canonical forward key, retired at advisory-000448 Rec 5's 6-month legacy-folder revisit). For each HIGH or MEDIUM recommendation, emit one entry: `{"topic": "<short topic>", "decision": "<recommendation text truncated to 120 chars>", "priority": "high|medium|low"}`. Populate both keys with the same list. This is carried to post-skill's telemetry flush (step 8b). Set both to `[]` if no actionable recommendations.

8. Save a report to the output file, including:
   - *header*: `# Research <id> | <prefix><scope> | <current datetime> | <short title>`
   - *tags*: on a line after the header (and after any `source:` or `spawned:` lines), add `tags: <comma-separated lowercase kebab-case slugs>`. Derive 2-5 tags from: (a) topic, (b) affected components, (c) perspectives evaluated (e.g., `security`, `architecture`, `ux`). See `general/report-conventions.md` § Research tags.
   - *user brief*, *agent interpretation*, *files* -- per .claude/references/general/report-conventions.md
   - *Q&A log*: the initial question and answer (verbatim), numbered sequentially
   - *recommendations summary*: concise list of all actionable recommendations
8b. Output a link to the output file.

9. Run /post-skill <id> with `skip_qa_log: true` to mark DONE and commit the report. /research owns the Q&A record (step 8 embeds it; step 11 appends follow-ups), so a companion qa-log would drift. See `.claude/skills/post-skill/SKILL.md` step 3 for the `skip_qa_log` contract.

9b. **Decision-extract proposals** -- detect whether this session involved design decisions and, if so, offer to create structured D-NNN entries.

   **When to trigger** -- ANY of:

   | Condition | Example |
   |---|---|
   | (a) HIGH-priority recs involving architecture, design patterns, or governance | "Adopt event-sourcing for X" |
   | (b) Q&A contains explicit trade-off discussion | "we chose X over Y because..." |
   | (c) User asked a design-choice question | "should we do X or Y?" |

   **When to skip**: purely informational research, `--inventory` queries, or how-to questions with no design choice.

   **Proposal shape** (DRR-shaped; see `template/docs/drr.md` for the full DRR template):

   ```
   ### D-NEXT: <title>

   **Context**: <what prompted the decision>
   **Decision**: <what was decided>
   **Consequences**: <expected impact>
   **Rejected Alternatives**: <rejected options and why>
   ```

   Use `D-NEXT` as the placeholder ID; `apply_marker.py --marker DECISION_APPEND` assigns the real D-NNN ID on approval.

   **Proposal flow** (when triggered):

   1. For each detected design decision, draft a D-NNN entry using the proposal shape above.

   1b. Render the before/after diff preview before each proposal's AskUserQuestion. Read the last 2 `### D-NNN:` entries from `product-design/product-design-as-intended.md`'s `## Decisions` section as the *before* context; render `(no prior decisions)` if empty, or `(no design-intent file yet -- D-NNN entries require running /design first)` if the file is missing. One diff block per proposal. Diff rendering rules:
      - Unified-diff conventions: leading space = unchanged, leading `+` = added. No `-` lines (DECISION_APPEND is strictly append-only).
      - Do not abbreviate the proposed entry text; the designer must see it in full.
      - For multiple D-NNN proposals, render one diff block per proposal; each gets its own AskUserQuestion.

   2. Present each proposal via AskUserQuestion with three options. Reference the diff block in the question text:
      - **Create now** -- Recommended when the decision rationale is fresh and the research clearly resolved a design question.
      - **Defer** -- Recommended when you want to review the wording later. NOT recommended when the entry will get stale before you return to it.
      - **Skip** -- Recommended when the research was informational, not decisional.

   3. On **Create now**: if `product-design/product-design-as-intended.md` exists and is Human (markers)-classified, invoke:
      ```
      python .claude/skills/scripts/apply_marker.py \
        --file product-design/product-design-as-intended.md \
        --id D-NEXT --marker DECISION_APPEND \
        --value "<draft text>" --plan manual \
        --note "from <source-id>"
      ```
      If the file is missing, inform the user D-NNN entries require `/design` first.

   4. On **Defer**: invoke:
      ```
      python .claude/skills/scripts/pending.py add \
        --type create-decision-entry \
        --source <source-id> \
        --description "<draft D-NNN entry text>"
      ```

10. Present the recommendations summary:
   - **Execute now** -- Recommended when the recommendations are clear and you want to proceed in this session. Run /plan and then /implement; pass the research ID so the plan records `source: research-<id>`. NOT recommended when the plan should be reviewed offline before execution.
   - **Plan only** -- Recommended when you want a concrete plan to review before committing to implementation. Run /plan; pass the research ID so the plan records `source: research-<id>`.
   - **Refine research** -- Recommended when the recommendations need more research or user feedback. Returns to step 4.
   - **Save and commit** -- Recommended when the research is complete as-is.

11. Run post-skill.

12. If the user has follow-up questions, continue the Q&A:
    - Answer each follow-up with clear, actionable recommendations.
    - After each answer, ask if they have more questions.
    - On conclusion, update the report file (preserving original content, with markers for new/refined/revoked/superseded content), append the follow-up Q&A pairs verbatim, and add a new recommendations summary (preserving the original).
    - Commit the updated report.
