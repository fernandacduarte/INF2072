---
name: design-mode5-internal
description: "Inlined worker for /design Mode 5 (Interview-Driven). Not user-invocable."
compatibility: "Designed for Claude Code with the SEJA harness"
metadata:
  internal: true
  category: internal
  version: 1.0.0
---

> This is an inlined worker; execute these instructions as part of the caller's flow. The wrapper at `.claude/skills/design/SKILL.md` has already run the Detection Logic; execute the phases below.
>
> **Field Classification**: The Field Classification section is in the calling wrapper SKILL.md (`.claude/skills/design/SKILL.md ## Field Classification`). Phase B must iterate over EVERY field listed there; the wrapper body is already in context when this internal executes.
>
> **Phase D delegation**: Phase D resumes from step 7 (Instantiate templates) of `.claude/skills/_internal/design/questionnaire/SKILL.md`. Read that file and execute from step 7 onward using the confirmed field values from the synthesis file.

### Mode 5: Interview-Driven

Triggered when `--mode interview` is passed.

#### Phase A: Open-Ended Interview

1. **Greet and orient**: Greet the designer and explain Mode 5: this is a conversational intake -- no fixed question order, no rigid form to fill. The agent will ask open-ended questions, adapt based on answers, and signal completion when it has enough information to populate every field in the `## Field Classification` section. The designer can type `/done` at any point to signal the interview is complete.

2. **Open Q&A loop**: Ask open-ended questions covering: platform purpose, target users, domain entities, permission model, constraints, priorities, edge cases, success criteria, and any other areas relevant to the `## Field Classification` fields. Adapt question ordering and depth based on prior answers. Continue until confident about every field in `## Field Classification`.

3. **Record per-exchange triples**: For each exchange, append a triple to the transcript file (`specs/design-interview-YYYYMMDD.md`, created from `.claude/references/template/design-interview-transcript.md`):
   - `**Agent question**:` -- the question exactly as asked
   - `**User response (verbatim)**:` -- exact text of the user's answer; no paraphrase, no summary
   - `**Agent interpretation**:` -- how this answer maps to v7 fields: explicit field names and extracted values

4. **`/done` shorthand**: Accept `/done` from the designer at any point as a signal that the interview is complete. Treat it as equivalent to the agent's own completion signal.

5. **Transition**: On completion (agent confidence achieved or `/done` received), announce transition to Phase B (synthesis).

#### Phase B: Synthesis

Iterate explicitly over EVERY field listed in the `## Field Classification` section of this SKILL.md (not via a prose synthesis prompt -- enumerate each field by name):

1. For each field in `## Field Classification`, locate the relevant exchange(s) in the transcript file.
2. Assign confidence:
   - **DS** (directly-stated): the designer explicitly stated this value
   - **INF** (inferred): the agent inferred this value from context
   - **PAC** (proposed-and-confirmed): proposed by the agent, confirmed by the designer
3. Note the source exchange number(s).
4. Write the full synthesis result to `specs/design-confidence-YYYYMMDD.md` (created from `.claude/references/template/design-confidence-annotations.md`).
5. Identify gaps: fields where no answer was found and no default applies (to be resolved in Phase C).
6. Announce transition to Phase C.

Critical constraint: Phase B MUST enumerate fields from `## Field Classification` explicitly. Do not rely on a prose synthesis prompt that "knows" the fields implicitly -- this keeps the field-to-template mapping transparent and auditable when new questions are added to v7.

#### Phase C: Confirmation

1. **Security-critical mandatory confirmation** (ALL inferred fields in these sections -- no exceptions):
   - section 4 (Permission Model) of product-design-as-intended.md
   - section 10 (Validation Constants) of product-design-as-intended.md
   - Constitution invariants

   For each field tagged INF in these sections, present an `AskUserQuestion` (decision-point rationale per `.claude/references/general/constraints.md`: "Recommended when / NOT recommended when"). Do NOT proceed to Phase D until ALL security-critical fields are DS or PAC.

2. **Other inferred fields** (batched review): present remaining INF fields for designer review. Designer can confirm, edit, or leave as proposed-default. Fields left unconfirmed default to their v7 questionnaire default value (same as Mode 1 skip-to-defaults).

3. **Gap-filling**: for fields with no answer and no default, ask a single focused question per gap.

4. **D-NNN decision extraction**: detect trade-off discussions that arose during Phase A or Phase C Q&A. Offer to create D-NNN entries via `apply_marker.py --marker DECISION_APPEND` (same mechanism as /research step 9b). Requires `product-design/product-design-as-intended.md` to exist; inform user if absent.

5. Announce transition to Phase D (template instantiation -- same as Mode 1 step 7 onward).

#### Phase D -- Instantiation

Read `.claude/skills/_internal/design/questionnaire/SKILL.md` and execute from step 7 (Instantiate templates) onward, using the confirmed field values from the synthesis file at `synthesis_file` in `specs/design-in-progress.md` as the source of answers instead of questionnaire responses.

#### Interrupt-Resume Schema Extension

When a Mode 5 session is active, extend `specs/design-in-progress.md` with these fields:

- `mode: 5`
- `phase: A|B|C|D`
- `transcript_file: specs/design-interview-YYYYMMDD.md`
- `synthesis_file: specs/design-confidence-YYYYMMDD.md`
- `open_gaps: [field_name, ...]`

On re-invocation when `specs/design-in-progress.md` exists: read the `mode` field; route to that mode's phase handler (Mode 5 -> resume from the active `phase`); treat missing `mode` as `mode: 1` (backward compat for pre-Mode-5 sessions).
