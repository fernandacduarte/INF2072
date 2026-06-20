---
designer_description: "When you are maintaining /plan and need the backstory -- why the --roadmap mode has three sub-modes, why plan IDs must not be pre-reserved, the Decision-point rationale convention origin, roadmap finalization policy -- I am the sibling file that holds the rationale so SKILL.md can stay tight on execution instructions."
---

# Plan rationale

Maintainer-only context for `plan/SKILL.md`. NOT loaded at runtime (no entry in `metadata.references`, the sync tool and call-graph generator both ignore this file). Edit both files when rationale changes.

## Rationale footer (from plan-000451)

The pre-existing `## Rationale` footer block that the SKILL.md body carried prior to plan-000458 step 9:

> Historical references and design decisions for maintainers: advisory-000292 and plan-000294 seeded the Decision-point rationale convention; plan-000341 added the Artifact-link convention; plan-000408 reshaped the `implement` pending entry handoff; plan-000411 refined the roadmap workflow.

Each citation unpacked:

- **advisory-000292 + plan-000294** -- seeded the Decision-point rationale convention (`Recommended when ... / NOT recommended when ...` phrasing on every AskUserQuestion option or text-based decision-point option). The convention is now encoded as Common Step C4; the canonical rule lives in `general/constraints.md`. `/plan` is one of several skills that apply C4 across modes; `/check`, `/explain`, `/seja-setup`, and `/research` also cite the convention when presenting decision-point options.
- **plan-000341** -- added the Artifact-link convention that shapes the `# <Kind> <id> | <prefix><scope> | <current datetime> | <short title>` header format referenced by Common Step C3. Later plans reshaped the header (adding `Review: <depth>` for plans, the `source: advisory-<id>` suffix for advisory-sourced plans, the metacomm `METACOMM |` insertion, and the `plan_format_version: 1` follow-line) but did not touch the base shape.
- **plan-000408** -- reshaped the `implement` pending entry handoff: post-skill (step 2g.iv and step 7h) files an `implement` entry at `/plan` completion and closes it at `/implement` rename. The skill body no longer needs to cite this plan because the lifecycle lives in post-skill; /plan's responsibility is limited to producing the plan artifact and invoking C6 (post-skill) at the right time.
- **plan-000411** -- refined the roadmap workflow shape: separated Mode 1 (auto-generate), Mode 2 (from spec file), and Mode 3 (blank spec) into distinct sub-flows, introduced the `qa_engaged` tracker for finalization branching, and added the inline-invocation clarification (per-plan invocations generated inside a roadmap run skip their own step 7/8 so the roadmap owns the commit).

## Mode-factoring history

The `--roadmap` workflow carries three sub-modes because roadmap generation has three distinct authoring starting points, and each has a different reference-file reading pattern that cannot be collapsed into a single prose:

- **Mode 1 (Auto-generate from project references)** -- `/design` has populated `project/product-design-as-intended.md` (and optionally `product-design-as-coded.md`) and the roadmap falls out of a delta analysis between as-coded and as-intended. This is the default modern path. Introduced as the primary roadmap flow in the earliest roadmap iteration; plan-000411 refined the reference-file reading checklist (step 2) and the requirements-extraction pass (step 2b, added when REQ markers landed).
- **Mode 2 (From spec file)** -- the user has a manual `roadmap-spec.md` draft (authored offline, possibly produced earlier via Mode 3) and the roadmap parser compiles it into the roadmap summary. This path exists so that human-authored control can precede auto-decomposition when project references are not yet canonical or when the user wants to adjust classifications/dependencies before plans are generated.
- **Mode 3 (Generate blank spec)** -- the user wants a spec skeleton to edit offline, then invoke Mode 2 later. Mode 3 is a pure scaffolding utility: it copies `.claude/references/template/roadmap-spec.md` to `<target>/specs/roadmap-spec-<datetime>.md` and exits. Hence Mode 3 skips every Common Step (no pre-skill, no ID reserve, no post-skill -- the output is a local artifact the user fills in offline).

Factoring rationale (why three, not one): Mode 1 and Mode 2 share steps 7-10 (decision point -> plan generation -> finalization -> execution instructions) but diverge on steps 1-6 (Mode 1 reads project references and decomposes the delta into work items; Mode 2 parses a pre-filled spec and validates it). Collapsing Mode 2 into Mode 1 would require the spec-parsing path to re-implement the decomposition loop; keeping them separate lets Mode 2 point to Mode 1 as the single source of truth for the shared finalization behavior (steps 7-10 in Mode 2 === Mode 1 steps 8-11 by reference). Mode 3 is a separate mode rather than a `--blank-spec` sub-flag on Mode 2 because it runs no lifecycle (no ID, no pre/post-skill) and its output is not a roadmap artifact; conflating it with Mode 2 would force Mode 2 to branch on empty input.

## Do-not-pre-reserve-plan-IDs reasoning

The rule one-liner in SKILL.md reads:

> **Anti-pattern -- do not pre-reserve plan IDs.** `/plan` reserves its own ID when invoked (C2 applies per plan); never call `reserve_id.py --type plan` up front for downstream items.

The failure-mode explanation (stripped from SKILL.md body during plan-000458 step 9 to keep the body tight):

When a roadmap generates N plans across multiple waves, those plans may execute out of order (Wave 0 completes sequentially; Wave 1 in parallel; Wave 2 starts only after Wave 1 lands). If the roadmap pre-reserves IDs up front for all N items -- say plan-000500 through plan-000510 -- and then one Wave 1 item stalls while Wave 2 items land first, the directory ordering and ID ordering diverge: plan-000507 (a late-landing Wave 1 item) sits on disk next to plan-000510 (an early-landing Wave 2 item), and the historical reading order (plan-NNNNNN sorted numerically) no longer matches the implementation order. Cross-references written during the stall window (e.g., "see plan-000507 for the prerequisite migration") can be invalidated if plan-000507 is ultimately not needed (the stalled item gets absorbed into another plan) because the ID was burned without being used.

The fix: each /plan invocation reserves its own ID via C2 (inside step 9 of Mode 1 when plans are generated inline). The roadmap's Plan column starts as `plan-TBD` and is filled with the real ID after `/plan` completes. If a generated plan is discarded before commit, no ID is burned; if a plan is never generated (Wave 2 and later), no ID is reserved. The IDs-as-they-are-assigned ordering always matches the actual implementation ordering.

Exception (recorded in the SKILL.md body): generating full plans eagerly via the step 9 decision point is fine. Those plans are real /plan invocations that each call C2; they can be discarded (by selecting `Revise plan` at their per-plan step 7 equivalent) before any ID is burned. The anti-pattern is specifically about calling `reserve_id.py --type plan` outside of a /plan invocation.

## Decision-point rationale convention origin

The `Recommended when ... / NOT recommended when ...` phrasing used for every AskUserQuestion option in /plan (and throughout the harness) comes from advisory-000292 and was operationalized in plan-000294. The canonical rule now lives in `general/constraints.md`; /plan applies it via Common Step C4.

Prior phrasing ("Right when ... / Wrong when ...") was rejected during the advisory because it prescribed a binary correctness judgment when the real signal is suitability-for-context. The current phrasing is intentionally weaker than a command and stronger than a suggestion -- it frames each option as a tool with a known use case, and the user selects based on their situation. The "NOT recommended when" arm is not the logical negation of "Recommended when"; it calls out the specific situations where the option is a poor fit, even if the main `Recommended when` trigger also applies.

Downstream: `/check`, `/explain`, `/seja-setup`, `/research`, and `/implement` all apply the same phrasing when presenting decision-point options. Consistency across skills is what makes the convention recognizable -- a user who has seen the pattern once in /plan knows what it means in /check's interactive modes.

## Wave design principles

Extracted from SKILL.md during plan-000458 step 9. The Mode 1 steps 3-5 already encode the operative rules (Layer decomposition table in step 3, Waves list in step 5, Technical/Design classification in step 4); this section restates the same material as maintainer-class design rationale, which does not belong in the agent-facing body.

### Migration safety (critical)

Alembic migrations form a linear chain. Therefore:
- **Wave 0 must be sequential**: only one plan at a time creates migrations.
- Order clusters by FK dependency (referenced entities first).
- Alternative: group all models + migrations into a single large plan.

### Parallelism boundaries

| Wave | Parallelizable? | Constraint |
|------|----------------|------------|
| 0 -- Foundation | No (sequential) | Migration chain is linear |
| 1 -- Services/API | Yes, per resource | Each resource independent once models exist |
| 2 -- Frontend | Yes, per page | Each page independent once APIs exist |
| 3 -- Cross-cutting | Limited | Shared files (i18n JSONs, auth config, routing) |
| 4 -- Testing/polish | Yes, per suite | E2E, a11y, docs are independent |

### Classification heuristic

| Primary concern | Classification | Planned via | Examples |
|----------------|---------------|-------------|----------|
| What the system does internally | Technical | `/plan` | Models, migrations, services, API endpoints, validation |
| What the user sees and experiences | Design | `/plan --framing metacomm` | Page UX, onboarding, empty states, navigation flow, error feedback |

Design items are phrased as metacommunication messages: "When you [context], I want you to [experience/action], because I know you [rationale]."

## Roadmap finalization policy

Mode 1 step 10 (and Mode 2 step 9, which reuses it) branches on the `qa_engaged` flag:

- `qa_engaged == false` -- auto-commit the roadmap summary + generated plans in a single commit via post-skill with the roadmap ID. No user prompt. Rationale: simple accept/confirm answers do not constitute Q&A, and interrupting the happy path with a "commit now?" prompt trains users to click through without reading. The auto-commit path assumes the draft-review step (Mode 1 step 6-7 / Mode 2 step 6) has already caught issues; if the user had concerns, they would have set `qa_engaged = true` by revising items or asking clarifying questions.
- `qa_engaged == true` -- use AskUserQuestion with three options (Commit all now / Keep uncommitted for review / Revise further) phrased per C4. Rationale: Q&A engagement means the user has already shown they care about specific details; giving them an explicit commit decision respects that engagement and avoids assuming their revisions are done.

The `qa_engaged` tracker is set to `true` when the user (a) modifies the work item list (add/remove/reorder/reclassify/dep adjustments), (b) requests plan revision mid-stream, or (c) asks clarifying questions that change the roadmap or a plan. The tracker is intentionally conservative: a confirm/accept answer does not flip the flag, because those answers are part of the happy path. This design was refined through plan-000411 based on observed user behavior.

## Dispatch B application (plan-000475)

`/plan` is the first operational example of the `Mode factoring pattern` Dispatch B recipe documented in `.claude/references/general/harness-governance.md § Skill Authoring Patterns > Mode factoring pattern`.

Why Dispatch B was selected over Dispatch A: all three `/plan` modes carry mid-flight interactive loops (standard step-7 AskUserQuestion, `--light` execute-now prompt, `--roadmap` Mode 1 steps 6/7/9/10 AskUserQuestions). Subagent context isolation would force marshalling every interactive turn through the Agent tool, defeating the interactive flow and complicating artifact-coordination with the parent's post-skill finalization.

Why Dispatch B was selected over Dispatch C alone: the wrapper body was at 419 lines, past the ~280-line threshold at which the Common Steps pattern nets positive on its own. The three modes shared no logic beyond C1-C6 (already factored out).

The three internal SKILL.md files under `.claude/skills/_internal/plan/{standard,light,roadmap}/` carry mode-specific steps 2-N and reference the wrapper's Common Steps table (C1-C6) by label. The internals intentionally omit `metadata.references` and `metadata.eager_references` -- pre-skill's ref-load stage reads these only from the wrapper's frontmatter; declaring them on internals would be dead fields creating drift risk.

Lifecycle-hook ownership invariant: `/pre-skill` and `/post-skill` fire exactly once per invocation, from the wrapper. Internals carry `metadata.internal: true` and a marker-line blockquote as the first body line declaring the inlined-worker contract.

Nested invocation: the roadmap internal invokes the standard internal per work item by reading `.claude/skills/_internal/plan/standard/SKILL.md` via the Read tool (not the Skill tool). The standard internal's step 1 "Apply C1" is a label reference to the wrapper's already-completed C1, not a re-invocation. The "Inline-invocation clarification" in roadmap Mode 1 step 9 instructs callers to skip the standard internal's steps 7 and 8 when invoked inline; suppression is caller-side prose-driven, zero mechanism.

## Citation index

Short list of plans and advisories referenced from /plan's execution rules or historical context:

- `advisory-000292` -- Decision-point rationale convention seed (`Recommended when / NOT recommended when` phrasing). Applied harness-wide.
- `plan-000294` -- operationalized the Decision-point rationale convention in the harness.
- `plan-000341` -- Artifact-link convention; shaped the C3 header format.
- `plan-000408` -- `implement` pending entry handoff (/plan completion files entry; /implement rename closes it).
- `plan-000411` -- roadmap workflow refinement (Mode 1 / 2 / 3 factoring, `qa_engaged` tracker, inline-invocation clarification).
- `plan-000451` -- editorial compression of /plan SKILL.md body (and 7 other skills); left the `## Rationale` footer intact for a follow-up extraction.
- `plan-000458` -- this plan; step 4 added Common Steps factoring (reducing /plan body from 423 to 403 lines); step 9 extracted the Rationale footer and maintainer prose into this sibling file.
- `plan-000475` -- first operational Dispatch B application; extracted /plan standard / light / roadmap workflows into `_internal/plan/<mode>/SKILL.md` worker files; wrapper body reduced from 419 to 122 lines; established the internal-skill frontmatter-omission convention (references/eager_references are wrapper-owned).

New plan/advisory references added to /plan rules (or moved into this file) should extend this index.

## Historical compression passes

The /plan SKILL.md body has been compressed in two editorial passes:

- **plan-000451 step 4** -- editorial compression of 8 SKILL.md bodies including /plan. Removed duplicated prose, tightened multi-paragraph architectural notes, and preserved the `## Rationale` footer intact. Brought /plan body to 423 lines.
- **plan-000458 step 4** -- Common Steps factoring (extracted C1-C6 shared execution steps, collapsed Mode 1 / Mode 2 / Mode 3 delta tables into one-sentence reuse summaries, dropped the Standard-workflow self-delta-table). Brought /plan body to 403 lines.
- **plan-000458 step 9** -- this extraction. Moved the `## Rationale` footer, the anti-pattern failure-mode example, and the Mode-factoring history into this sibling file; added a one-line pointer at the top of the SKILL.md body.
- **plan-000475 step 4** -- Applied Mode factoring pattern Dispatch B to /plan. Wrapper dropped from 419 lines to 122 lines. Three internal SKILL.md worker files created under `_internal/plan/{standard,light,roadmap}/`; mode-specific workflow prose moved verbatim (allowed edits: H1/H2 drops, frontmatter addition, marker-line blockquote addition, Amendment 2.3 disambiguation parentheticals in roadmap Mode 1 step 9).

Future compression passes should consider this file first: if a section grows beyond its pull-weight (e.g., a new anti-pattern failure-mode) the SKILL.md one-liner points here and the detail lands below, not in the SKILL.md body.
