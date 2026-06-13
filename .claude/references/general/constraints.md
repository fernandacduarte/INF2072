---
designer_description: "When you want to know the non-negotiable guardrails every skill operates under -- UTF-8 only, no invented data, no nondeterminism unless asked, no placeholder implementations, no silent feature creep in auto mode -- I'm the reference that spells them out, along with the decision-point rationale convention that keeps every AskUserQuestion honest about when each option is and is not recommended."
---

# GENERAL - CONSTRAINTS

- Whenever writing, editing, or revising agent-facing instructions, be as concise as possible.
- Do not compress human-facing prose unless specifically directed to do so by the user.
- Prefer named sections and paragraphs to numbered ones, except when ordering is essential (e.g. execution steps).
- All files must be UTF-8 encoded.
- All lines end in CRLF.
- For English texts, use US English spelling.
- Do not invent data.
- Do not generate agent-dependent or nondeterministic behavior unless explicitly requested.
- Do not use ANSI code in generated code or reports.
- Do not reduce existing test coverage. When modifying code that has tests, update or extend the tests to maintain coverage.
- Do not implement placeholder or simplistic implementations.
- If you come across an opportunity to add a desirable but unessential feature based on similar products or best practices, describe the proposal, provide pros and cons, and ask the user. When working autonomously, as in `auto` or `bypassPermissions` mode, do not add unessential features.

## Decision-point rationale convention

**Rule.** Every recommendation or `AskUserQuestion` in SEJA carries explicit rationale for each option. The harness is a proposer; the designer is the decider. No option may be pre-accepted by framing alone.

**Format.** Each option's description contains 1-2 lines: *"Recommended when ..."* (why this option fits) and *"NOT recommended when ..."* (when it would be unsuitable). An optional `(more: <link>)` footer links to a relevant advisory, plan, or concepts section for substantial rationale. Total description per option: up to 3 lines before the link. Always use "Recommended when" / "NOT recommended when" phrasing -- never "Right when" / "Wrong when".

### Short-form rationale allowance

The two-line "Recommended when ... / NOT recommended when ..." form remains the baseline, but a one-line "Recommended when ..." form is permitted when the option's trade-off is obvious -- i.e., when the "NOT recommended when" clause would merely restate the inverse of the "Recommended when" clause or would flag a situation no designer would mistake. The short form is an author judgment call; when in doubt, keep the two-line form.

**Use the short form** when the option is the default, safe, or otherwise self-evident:
- `**Auto-run now** -- Recommended when you want this done in the same session.`
- `**Skip** -- Recommended when the change is not ready to commit yet.`
- `**Continue** -- Recommended when the current state is the intended outcome.`

**Keep the two-line form** when the trade-off is non-obvious or the downside of each option is itself informative:
- `**Implement now** -- Recommended when the plan has been reviewed and you are ready to proceed in this session. NOT recommended when you want to review the plan offline or share it with others first.`
- `**Defer for later review** -- Recommended when the implementation looks right but you want a cool-down period before committing to markers. NOT recommended when the candidates are trivially correct and deferring is pure procrastination.`

The `(Recommended)` label policy above applies identically to both forms: the recommendation must carry the specific reason it is recommended in this context.

**Recommended-label policy.** The label `(Recommended)` is permitted when and only when the option's description includes the *specific reason* the option is recommended *in this context*. A bare `(Recommended)` without contextual reasoning is a convention violation. When no option has a clear contextual preference, omit the label.

**Rationale for the rationale.** I adopted this convention after advisory-000292 identified that auto-accepting recommendations undermines reflective practice. Reflection-in-action requires the user to pause and consider before clicking; rationale that earns the recommendation is what makes that pause productive. Without this convention, the harness would embody doctrinal delivery rather than reflective collaboration.

**Enforcement.** This convention is currently enforced by author discipline. A `check_docs.py` plugin scanner `decision_point_rationale_compliance` is a candidate follow-up to audit SKILL.md `AskUserQuestion` blocks at CI time.

See advisory-000292 (A3) and plan-000294 for the origin and rationale of this convention.

## Artifact-link convention for decision points

**Rule.** When outputting recommendations or posing questions (for instance, via  `AskUserQuestion`), if they reference or are related to one or more already-generated artifact files, output a compact **Files for review** block immediately before the question. This lets the user open and review the artifact(s) before answering.

**Format.**

```
**Files for review:**
- [plan-000042-add-tagging.md](_output/plans/plan-000042-add-tagging.md)
- [advisory-000038-auth-middleware.md](_output/advisory-logs/advisory-000038-auth-middleware.md)
```

Each entry is a clickable relative-path link (relative to the project root). List every artifact the user might want to review before making their choice -- the plan they are about to implement, the advisory they are about to act on, the proposal they are about to execute, etc.

**When it applies.** Any recommendation output or question to the user that references or is related to a specific, already-generated artifact file (plan, advisory, roadmap, proposal, promote-proposal, drift report, pending-action source, etc.). Examples:

- `/plan` step 7 -- the just-generated plan file
- `/plan --light` step 6 -- the just-generated proposal file
- `/research` step 9b -- the advisory report (and optionally the design-intent file receiving D-NNN entries)
- `/research` step 10 -- the advisory report
- post-skill step 6e -- the plan file and as-intended files with STATUS marker candidates
- post-skill step 11 -- the just-completed artifact
- `/explain spec-drift` Step B -- the drift report
- `/explain spec-drift` Phase 3b step 4 -- the promote-proposal file
- `/pending` step 4 -- the source artifact for the selected pending action

**When it does NOT apply.** `AskUserQuestion` instances that gather input before any artifact exists -- no files to link yet. Examples: roadmap mode selection, onboarding role/level selection, check mode selection, explain type selection, communication audience selection.

**Relationship to Decision-point rationale convention.** Both conventions apply simultaneously. The artifact-link block appears first, then the `AskUserQuestion` with rationale on each option per the Decision-point rationale convention above.

See plan-000341 for the origin and rationale of this convention.

## Context Management

- **Session length awareness**: After 8+ skill invocations in a single session, context quality may degrade. Pre-skill's `compaction-check` stage warns when this threshold is reached.
- **When to start a fresh session**: After completing a major workflow (e.g., advisory -> plan -> implement -> check), or when the agent's responses become less accurate or miss previously established context.
- **What to preserve across sessions**: Before starting a fresh session, persist key decisions, plan IDs, open issues, and any unresolved questions to the session scratchpad (`${TMP_DIR}/session-notes.md`). Use timestamped entries with category tags (DECISION, FINDING, TODO, CONTEXT).
- **Pinned anchors**: Certain reference files must never be summarized or dropped during context compaction. See the Pinned Anchors section below for the full list.

### Session Scratchpad Format

The session scratchpad (`${SESSION_NOTES_FILE}`) uses timestamped entries with category tags:

```
## YYYY-MM-DD HH:MM UTC

- DECISION: <what was decided and why>
- FINDING: <what was discovered, with file paths or plan IDs>
- TODO: <what remains to be done, with enough context to resume>
- CONTEXT: <background information needed to continue this work>
```

**When to write**: After making key architectural decisions, discovering important findings, completing major milestones, or before a session is likely to end.

**What to include**: Plan IDs, file paths, unresolved questions, key metrics, dependency relationships between tasks.

**What NOT to include**: Full file contents, verbose logs, conversation history, information already captured in plan files or briefs.

### Pinned Anchors (Non-Compactable Context)

The following reference files must survive any context compaction event. They must be re-injected after summarization or truncation and must never be abbreviated:

1. `project/constitution.md` -- immutable project principles; dropping this allows agents to bypass governance rules
2. `general/permissions.md` -- agent permission boundaries; dropping this removes authorization constraints
3. `general/constraints.md` -- behavioral constraints (this file); dropping this removes quality and safety guardrails
4. Active skill's SKILL.md instructions -- the currently executing skill's full body; dropping this causes the agent to lose its task context
5. Active plan context -- if executing a plan, the plan file content; dropping this causes the agent to lose implementation context
6. Session scratchpad (`${SESSION_NOTES_FILE}`) -- persisted decisions and findings; dropping this negates the purpose of structured note-taking

Sibling facet files are NOT pinned. `SKILL-quickguide.md` (designer-facing narrative, consumed by `/help` and the pre-skill `help` stage via the shared `load_quickguide()` helper) and `SKILL-rationale.md` (maintainer-only citations and architectural context) are sibling files that live next to a pinned SKILL.md but are not themselves pinned. Neither is on the agent executional hot path: the first is loaded only when a designer explicitly invokes `/help <skill>` or `<skill> --help`; the second is never loaded at runtime. The pointer line at the top of SKILL.md is the discoverability anchor; the sibling bodies follow the link when a designer chooses to open them.

If a compaction mechanism is implemented in the future, it must treat these files as immutable anchors that are preserved verbatim through every compaction cycle.


## If stack includes TypeScript (frontend)

- New frontend files must be TypeScript (`.ts`/`.tsx`). Existing `.js`/`.jsx` files should be converted when substantively modified.
