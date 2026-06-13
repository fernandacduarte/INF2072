---
designer_description: "When you need the harness's governance guardrails -- skill and agent count justification, authoring patterns for SKILL.md siblings and mode factoring, the file-maintainer classification summary, the codebase-vs-workspace split, and private-only content conventions -- I'm the single reference that codifies them so structural decisions stay consistent across edits."
---

# Harness Governance

## Skill Authoring Patterns

Maintainer-facing conventions for structuring SKILL.md bodies. These are applied per-skill (opt-in), not enforced across the whole harness. Each pattern has a runtime-contract invariant that keeps agent-visible behavior unchanged.

### Sibling `SKILL-rationale.md` pattern

A maintainer-only companion file next to `SKILL.md` that holds advisory/plan citations and architectural-decision prose stripped from the SKILL.md body during editorial compression.

- **When to adopt**: after editorial compression, a SKILL.md's body still carries `>= 3` advisory or plan citations (e.g., `See advisory-000441`, `plan-NNNNNN`) or multi-paragraph architectural-decision prose that the agent does not need at runtime. The `skill_body_length` plugin in `check_docs.py` surfaces citation-drift warnings as an early signal.
- **What goes there**: advisory citations (e.g., `See advisory-000441`), `plan-NNNNNN` references, architectural-decision blocks, rationale for design choices, historical context, notes on rejected alternatives that shaped the current shape.
- **What does NOT go there**: executional instructions (those stay in `SKILL.md`), templates (those go to `.claude/references/template/`), schemas the agent consumes at runtime.
- **Runtime contract**: `SKILL-rationale.md` is NOT added to any `metadata.references` entry in the SKILL.md frontmatter; pre-skill does NOT load it; it is maintainer-only. Call-graph generation ignores it; `/check preflight` and friends do not read it.
- **Maintenance discipline**: when rationale changes, authors edit both `SKILL.md` (the one-line pointer, if present) and `SKILL-rationale.md` (the body). The pointer and the rationale are version-controlled together; do not update one without the other.
- **Pointer format (optional)**: the SKILL.md may carry a single-line pointer at the top of the body (immediately below the Arguments table): `> Rationale for design choices and historical context: see `SKILL-rationale.md` in this directory.` The pointer is optional -- skills whose body carries zero residual citations after compression do not need it.
- **Edge case**: a skill without a `## Rationale` footer today is still a valid sibling-file candidate if its numbered step bodies carry citation drift; in that case the sibling file holds the extracted citations and architectural context, and the pointer anchors the SKILL.md body to the sibling.

### Script rationale sibling pattern

A maintainer-facing companion file next to a Python script in `.claude/skills/scripts/` that holds private artifact citations and historical design context stripped from the script body.

- **When to adopt**: when a synced production script would otherwise carry a specific private artifact citation such as `plan-NNNNNN`, `advisory-NNNNNN`, or `research-NNNNNN` in comments, docstrings, or help text. Tests, `scripts/priv/`, and generated migration fixtures are out of scope.
- **What goes there**: one entry per artifact ID or tightly-related ID cluster. Each entry starts with the artifact ID in bold and contains a one-paragraph summary of what changed and why the script is marked by it, written so public consumers do not need access to the private artifact.
- **What does NOT go there**: executable instructions, import requirements, runtime configuration, schemas, or examples that the script needs to display to users.
- **Runtime contract**: `<script>-rationale.md` is NOT imported, parsed, or referenced by Python logic. It is synced with the script and must therefore be self-contained, with no dependency on private `_output/` files to understand the design choice.
- **Pointer format (mandatory when a sibling exists)**: the Python script carries one module-level comment immediately after the module docstring: `# Rationale for design choices and historical context: see <script>-rationale.md in this directory.`
- **Maintenance discipline**: new private artifact citations go into the sibling, not into `.py` bodies. A concise citation-free code comment may remain where the rationale affects a nearby constant or branch. `TRANSITION plan-NNNNNN` anchors may remain inline when the artifact ID is part of a retirement-window marker tied to a specific field definition.

### Sibling `SKILL-quickguide.md` pattern

A designer-facing companion file next to `SKILL.md` that holds the Quick Guide narrative (What / Example / When to use / Next step) stripped from the SKILL.md body during plan-000466's harness-wide extraction.

- **When to adopt**: every user-invocable skill. Internal lifecycle hooks (`pre-skill`, `post-skill`) have no Quick Guide and get no sibling.
- **What goes there**: designer-facing narrative -- the What / Example / When to use / Next step sections and any tightly related notes (e.g., terminology callouts). The sibling body IS the Quick Guide; no `## Quick Guide` H2 heading is re-introduced inside the sibling.
- **What does NOT go there**: executional instructions (those stay in `SKILL.md`), YAML frontmatter, `metadata.references` entries, or any content the agent consumes at runtime.
- **Runtime contract**: `SKILL-quickguide.md` is NOT added to any `metadata.references` entry in the SKILL.md frontmatter; pre-skill does NOT load it during the normal budget-eval/ref-load stages; it is loaded only on demand by (a) the pre-skill `help` stage when a skill is invoked with `--help`, and (b) `/help <skill>` Layer 2. Both paths go through the shared `load_quickguide(skill_dir)` helper at `.claude/skills/scripts/load_quickguide.py`, which is the single file-path source of truth.
- **Pointer format (mandatory)**: SKILL.md carries a blockquote pointer line within the first 15 non-blank body lines (after frontmatter), outside any fenced code block, containing the literal token `SKILL-quickguide.md`. The migration script's canonical form is `> Overview: see [./SKILL-quickguide.md](./SKILL-quickguide.md)`. Benign prose drift (alternate wording, different link-label capitalization) is permitted within the structural envelope. The `quickguide-pointer-compliance` scanner in `check_docs.py` enforces the shape; missing or malformed pointers fail preflight.
- **Enforcement asymmetry vs. `SKILL-rationale.md`**: the `SKILL-rationale.md` pointer is optional free-text (maintainer-only file; rationale content drift is low-stakes). The `SKILL-quickguide.md` pointer is mandatory and structurally enforced because it is the discoverability anchor for designers opening SKILL.md cold -- without the pointer, a contributor scanning the file has no signal that the narrative lives elsewhere. The asymmetry is intentional.
- **Maintenance discipline**: wording changes go in the sibling; executional changes go in SKILL.md. Example snippets in the sibling that mention CLI arguments must be kept in sync with `## Arguments` in SKILL.md when argument signatures change.
- **Consumers**: the shared `load_quickguide()` helper is called by `generate_call_graph.py` (node descriptions) and `check_docs.py` (harness-integrity + pointer-compliance scanners). The pre-skill `help` stage and `/help` Layer 2 replicate the loader's behavior in agent prose.
- **Migration tool**: `.claude/skills/scripts/priv/migrate_quickguide.py` performs the one-shot extraction and is idempotent. It lives in `priv/` (harness-dev only) and is not shipped to consumers.

### Common Steps pattern

A body-restructuring recipe for mode-heavy SKILL.md files that factor shared execution across modes into a single `## Common Steps (all modes)` block. Applied to `/plan`, `/check`, and `/explain` in plan-000458 steps 4-6.

- **Recipe**:
  (a) Extract `C1`-`CN` labeled entries for execution patterns that run across every mode (pre-skill invocation, ID reservation, artifact-header shape, post-skill invocation, shared finalization behavior).
  (b) Fold pre-existing shared top-level H2 sections (e.g., `## Stack Filtering`, `## Definitions per type`) INTO `## Common Steps` as labeled entries or sub-sections rather than keeping them parallel.
  (c) Emit per-mode delta tables ( `| Step | Common? | Delta |` ) only for modes with `>= 50%` Common-Step reuse.
  (d) Use one-sentence reuse-summary prefixes (`Reuses C1, C3; then:`) for modes with lower reuse.
  (e) Pick exactly one mode as the reference-prose mode that carries the full shared finalization behavior other modes point to by name.
  (f) Never emit a delta table for the reference-prose mode -- the reference IS the prose; a delta table to itself is pure overhead.
- **Applicability threshold**: the pattern yields diminishing returns below ~280 body lines. Structural overhead of the `## Common Steps` block (H2 + four-to-six labeled entries + optional sub-sections) is ~15 lines, so a mode-heavy skill needs at least ~30 lines of repeated shared-step prose across modes for the factoring to net positive. Below the threshold, skip the `## Common Steps` H2 and apply only the reuse-summary-prefix pattern (or skip the factoring entirely).
- **Runtime contract**: body-only restructuring. YAML frontmatter, Quick Guide, and Arguments table stay byte-identical. No change to `metadata.references`, no change to agent dispatch, no change to verbatim `Run /<skill>` invocation phrasings (those stay intact for call-graph detection).
- **Regression fence**: `grep -c "Same as Mode" <SKILL.md>` returns 0 after factoring. The `skill_body_length` plugin's mode-stub detector fires at `>2` `Same as Mode` occurrences per file as a drift signal during future edits.

### Mode factoring pattern

A selection framework for how a mode-heavy wrapper skill factors its per-mode work. Three dispatches exist in the harness; pick per-mode, not per-skill -- one wrapper can mix all three.

- **Dispatch A -- Wrapper > subagent.** The mode's work runs in an isolated context via the Agent tool. Examples: `/document` > `document-generator`; `/communicate` > `communication-generator`; `/onboard` > `onboarding-generator`; `/check review` > `code-reviewer`; `/explain` behavior/code/data-model modes > `explanation-generator`; `/explain` architecture mode > `architecture-explainer`; `/explain` behavior-evolution mode > `evolution-explainer`.
  - **When to adopt**: mode is self-contained (all inputs at dispatch, no mid-flight parent coordination); stable I/O contract (prompt in > artifact/findings out); context isolation is valuable (tool-call volume would bloat parent, or parallel execution wanted); no interactive loops mid-flight.
  - **Governance**: new agents must pass the single-responsibility test in the Agent Count governance section below.

- **Dispatch B -- Wrapper > inlined internal skill.** The mode's instructions live in a separate SKILL.md under `.claude/skills/_internal/<wrapper>/<mode>/`. The wrapper reads the internal's SKILL.md and executes its steps as inlined prose in the parent's flow. The internal's frontmatter carries `metadata.internal: true`; the body opens with a marker line declaring "this is an inlined worker; execute these instructions as part of the caller's flow". First example: `/plan` > `_internal/plan/standard/SKILL.md`, `_internal/plan/light/SKILL.md`, `_internal/plan/roadmap/SKILL.md` (plan-000475). The internals carry mode-specific steps 2-N and reference the wrapper's Common Steps table by label; the wrapper orchestrates pre-skill, Design Guard, Mode Detection, Common Steps, Framing, and Dispatch. The internals intentionally omit `metadata.references` and `metadata.eager_references` — pre-skill reads these from the wrapper only.
  - **When to adopt**: mode is interactive (`AskUserQuestion` loops, user branching mid-flight); produces multiple artifacts coordinated with the parent's post-skill finalization; needs visible presence in the parent transcript; the wrapper SKILL.md has grown past the point where the Common Steps pattern keeps it tractable, and mode sections carry substantial prose sharing no common logic.
  - **Anti-pattern**: do not use when the mode is agent-shaped (forgoes context isolation) or when the mode prose is under ~30 lines (extraction overhead exceeds payoff).
  - **Runtime contract**: the internal's SKILL.md is NOT listed as a user-invocable skill discovery root; the underscore-prefixed directory excludes it from skill enumeration. Pre-skill does NOT load it directly. The wrapper reads the internal via the Read tool (not the Skill tool), so lifecycle hooks fire once (wrapper only). Call-graph generation follows the parent > internal edge via the wrapper's explicit Read reference.

- **Dispatch C -- Inlined mode prose (status quo).** The mode's steps live in the wrapper's SKILL.md under a `### Mode: <name>` heading. Factored via the Common Steps pattern when shared execution exists across modes. Examples: `/check preflight` (orchestrates parallel Dispatch A agents from inlined prose), `/check validate`, `/check smoke`, `/check docs`, `/check telemetry`, `/plan` standard/light/roadmap.
  - **When to adopt**: mode is short (< ~30 lines of prose), or a pure script wrapper / pure orchestration dispatcher, or the Common Steps pattern already captures enough reuse to keep the wrapper tractable.

- **Selection order**: evaluate A first, then B, then default to C. Most modes land in A or C; B is the narrow case that exists to keep mode-heavy wrappers tractable when neither fits.

- **Runtime contract (all three)**: the wrapper remains the single lifecycle-hook owner -- `/pre-skill` and `/post-skill` are invoked by the wrapper, not by the mode. No dispatch fires lifecycle hooks twice. Dispatch A delegates via Agent tool (isolated context); Dispatch B inlines via Read tool (shared context); Dispatch C needs no delegation (already inline).

- **Maintenance discipline**: when promoting a mode from C > A or C > B, the wrapper SKILL.md loses the mode's prose and gains a one-paragraph dispatch block. The extracted prose moves verbatim (A: into the agent prompt; B: into the internal SKILL.md body) with no semantic change in the first commit -- behavior-preserving refactor first, content revisions later.

### Parallel worktree execution

Roadmap wave execution (Wave 1+) uses Claude Code's `isolation: "worktree"` Agent parameter to run independent plans in parallel git worktrees. The pattern extends the batch execution pattern's "bookend lifecycle hooks" principle to code-producing subagents.

- **When used**: roadmap mode (`/implement --roadmap <id>`), Wave 1+ plans whose `Files:` lists do not overlap (including call-graph edge check). Wave 0 is always sequential (migration chain safety).
- **Isolation model**: each plan runs in a `general-purpose` subagent with `isolation: "worktree"`. The Agent tool creates a temporary git worktree per plan; the subagent commits within its worktree branch.
- **Deferred-write contract**: worktree subagents operate in worktree mode (see `/implement` Definitions table) -- they skip `pre-skill` brief-log and `post-skill` entirely, writing only per-plan files (progress file, plan status, source code). Shared mutable state (`pending.jsonl`, `briefs.md`, `INDEX.md`, `telemetry.jsonl`) is updated post-merge by the orchestrator via `/post-skill --deferred`, serialized on the main branch.
- **Merge protocol**: after all worktree agents complete, the orchestrator merges results sequentially in plan-ID order. For each: rebase onto current HEAD; fast-forward merge on success; pause for user resolution on conflict (resolve, skip, or abort wave). Sequential rebase produces linear history compatible with `git bisect`.
- **Rollback semantics**: `pre-wave-<N>-<roadmap-id>` branch created before each wave. On abort: `git checkout pre-wave-<N>-<roadmap-id>`. Completed plans are preserved; only the current wave is rolled back.
- **Failure modes**: single-plan FAILED does not abort the wave (logged, not merged). Merge conflicts pause for user resolution. Worktree cleanup retries with exponential backoff (2s/4s/8s) on Windows locked-file failures; persistent orphans are logged for manual cleanup.
- **Health check**: `check_worktree_health.py` detects orphaned worktrees; wired into `/check health`.

## Governance

### Skill Count
New skills must justify that their functionality cannot be a mode of an existing skill. The `/check` consolidation (10 modes in one skill) is the model to follow for skills that share a common execution pattern. Skills serving distinct communicative purposes may justify independent existence when they meet 3 or more of these 4 criteria: (a) distinct user intent and mental model, (b) disjoint reference sets, (c) incompatible execution topology, (d) different output strategy. Current count: 16 skills (14 user-facing + 2 internal lifecycle hooks).

### Agent Count
New agents must justify that their domain is distinct from existing agents. Agents follow single-responsibility principle across three roles:
- **Evaluator**: each reviews one type of artifact through one lens (code diffs, plans, design decisions, debates, validation scripts, test suites, migrations).
- **Generator**: each produces one type of artifact from well-defined inputs (communication material, onboarding plans, documentation). Invoked by thin-skill wrappers, not directly by users.
- **Executor**: dynamically constructed by `/implement` auto mode (not standalone prompt files).
Current count: 16 agents (9 evaluator + 7 generator).

### agentskills.io Spec Alignment
SEJA SKILL.md frontmatter follows the [agentskills.io](https://agentskills.io) universal specification. Top-level fields (`name`, `description`, `compatibility`) conform to the spec; SEJA-specific fields (`context_budget`, `eager_references`, `references`, `skip_stages`, `plan_format_version`, `questionnaire_version`) are namespaced under `metadata` to avoid conflicts with future spec fields. New skills must validate against the agentskills.io spec (enforced by `check_skill_spec.py`).

### Architectural Decisions

**Pre/post-skill monolithic pipelines**: Pre-skill (6 stages) and post-skill (13 steps) are intentionally monolithic. The full lifecycle is readable in a single file. Decomposing into micro-hooks would add file count and configuration without solving an actual problem. The `skip_stages` mechanism handles per-skill overrides. Revisit only if a stage needs independent versioning.

**Lifecycle hooks stay top-level (`.claude/skills/<name>/SKILL.md`)**: `/pre-skill` and `/post-skill` remain top-level internal hooks rather than moving under `.claude/skills/_internal/`. Wrappers invoke them by skill name (`Run /pre-skill ...`, `Run /post-skill ...`) and rely on normal skill resolution. The `_internal/` tree is reserved for non-user-invoked inlined workers that wrappers read and execute inline, not lifecycle hooks invoked through the skill dispatcher. Revisit only if runtime skill resolution explicitly supports lifecycle-hook invocation from `_internal/` without compatibility regressions.

**Git upstream-freshness check lives outside pre-skill**: Git upstream-freshness checks are not added to pre-skill. Alternative A (mandatory pre-skill stage that runs `git fetch` plus prompts to pull on every skill invocation) was rejected on four grounds: (a) `git fetch` is a network call that violates the pre-skill <150 ms budget; (b) an ask-user pull prompt breaks pre-skill's advisory-only posture; (c) `git pull` is destructive-by-composition and offering it at skill-start inverts the risk profile of CLAUDE.md's non-destructive-default protocol; (d) network-dependent stages are hard to test deterministically. The signal flows through (1) the `check-git-freshness` periodic trigger in `.claude/references/template/conventions.md`, which files a pending-ledger entry at most once per interval, and (2) the on-demand `/check freshness` mode, which runs fetch plus ahead/behind comparison in a user-initiated context. No automatic `git pull` is performed. Reference: research-000477 recommendations 1, 3, 4, 5, 7.

**Pre-skill opt-out convention**: lifecycle-workflow skills (`/plan`, `/implement`, `/check`, `/research`, `/explain`, `/document`, `/reflect`, `/onboard`, `/communicate`) invoke `/pre-skill` as their first step. Configuration and meta skills (`/seja-setup`, `/design` Initial Design modes, `/pending`, `/qa-log`, `/help`, `/post-skill`, `/pre-skill` itself) skip it. The divide is workflow-vs-infrastructure: lifecycle skills opt in because they produce logged artifacts under `_output/` and consume prior context (briefs, pending ledger, project references); configuration and meta skills opt out because they manipulate the harness itself, may run before `project/conventions.md` exists (bootstrap case), or have output topologies pre-skill's stages were not designed for. `/design` is partially mixed: the Design Update branch opts in (conventions.md exists; briefs-log and pending-check are meaningful) while the Initial Design modes (1/2/4) opt out (conventions.md is being created). New skills should pick a side explicitly. Reference: research-000461.

**Explain/document separation**: `/explain` (epistemic -- understanding existing system) and `/document` (productive -- generating documentation artifacts) remain separate skills. They have different user intents, different output topologies (`_output/explained-*` vs. project source locations), disjoint reference sets (design specs vs. doc templates), and incompatible interaction patterns (ID-reserved analysis reports vs. template-based generation). The spec-drift mode's interactive sync workflow has no analogue in any document mode. Revisit if the two skills develop shared output conventions, shared references, or if user feedback shows intent confusion. (advisory-000153)

**Onboarding/document separation**: `/onboard` (person-centric onboarding plans) and `/document` (artifact-centric project documentation) remain separate skills. Onboarding has interactive argument resolution, role-conditional project scanning, batch mode with parallel subagents, date-versioned output, and zero reference overlap with document. Onboarding implements a pedagogical framework (Dreyfus-aligned levels, role families, progressive disclosure layers), not a document template. Revisit if onboarding loses its interactive/batch capabilities or if reference sets converge. (advisory-000156)

**Auto-doc default at post-skill step 2b**: post-skill auto-runs `/document --plan <id>` after qualifying plans (FEATURE/REDESIGN, or any plan with non-N/A `Docs:` fields) via an `AskUserQuestion` whose recommended default is **Auto-run now** and whose alternative is **Skip**. Two opt-outs preserve user control: (a) `--skip-docs` on `/implement` suppresses the question entirely and goes straight to the Skip branch; (b) choosing Skip on the in-the-moment `AskUserQuestion` files an `update-documentation` pending entry so the work stays tracked. `AskUserQuestion` was chosen over a free-text "reply skip" notice because the LLM-agent runtime has no deterministic blocking read — plan-reviewer flagged this as a silent-bypass risk. Rationale: advisory-000441 rejected subsuming `/document` into `/implement` on four-criteria governance grounds but identified the step 2b prompt as the real friction behind the merger pressure; flipping the default recovers the felt win (one fewer confirmation on the common path) without collapsing the skill boundary. This decision does NOT reopen the merger question — `/document` remains a separate skill. Revisit if telemetry (`decision_points` in post-skill step 1b) shows users selecting Skip in more than 30% of runs, which would signal the default is miscalibrated. Reference: advisory-000441, plan-000444.

**Pending ledger separation (/pending vs. /check)**: `/pending` (interactive ledger curation: list/add/done/snooze/dismiss against `_output/pending.jsonl`) and `/check` (diagnostic reporting across 10 modes, each writing a `check-NNN` log) remain separate skills. They pass 4/4 on the governance test: (a) distinct intent -- action-dispatch vs. diagnostic; (b) disjoint reference sets -- `shared-definitions.md` vs. `review-perspectives/*`, `standards`, `design-standards`, `security-checklists`; (c) incompatible topology -- per-entry AskUserQuestion loop dispatching `pending.py`/`apply_marker.py` vs. agent fan-out producing a single check-log; (d) different output strategy -- append-only JSONL mutation vs. timestamped report artifact. Merging would create structural recursion with pre-skill's `pending-check` stage (which `/pending` currently skips to avoid), force a heavy-budget tax on every ledger append, and require rewriting every "run /pending" banner across pre-skill, post-skill, `/implement`, and `cut_tag.py`. `/check health` Check 9 surfaces a pending-count diagnostic as a soft link without absorbing the skill. Revisit only if `/check` grows a mutation-loop mode of its own. (advisory-000442)

**Agent single-responsibility**: Each agent operates on one type of artifact through one lens. Evaluators: `code-reviewer` reviews diffs, `plan-reviewer` reviews plans, `research-reviewer` reviews research questions and design decisions, `council-debate` runs structured debates, `standards-checker` aggregates script results, `test-runner` runs test suites, `migration-validator` validates migrations, `harness-health-evaluator` runs harness self-diagnosis across 8 built-in checks (skill system, briefs hygiene, plans hygiene, references, conventions, constitution, spec compliance, pending ledger) -- distinct from `standards-checker` (which runs validator scripts against project code) and from `code-reviewer` (which reviews diffs), `semiotic-inspector` evaluates interface communicability via SIM's three sign classes (metalinguistic, static, dynamic) -- distinct from `code-reviewer` (code perspectives) and from `research-reviewer` (design questions). Generators: `communication-generator` produces stakeholder material, `onboarding-generator` produces onboarding plans, `document-generator` produces project documentation, `test-plan-generator` produces manual test plans from a brief plus recent DONE plans -- distinct from `test-runner` (which runs automated test suites) and from `document-generator` (which produces project documentation artifacts), `explanation-generator` produces explanation reports for behavior/code/data-model modes -- invoked by the `/explain` thin-wrapper for non-interactive analysis modes. Do not merge agents or add cross-cutting responsibilities to existing agents.

**Generator-critic loops in auto mode**: `/implement` auto mode uses a bounded generator-critic loop (max 2 retries) when the code-reviewer identifies critical findings during the quality gate. Interactive (manual) mode retains advisory-only review — the user decides what to fix. Rationale: auto mode has already opted out of per-step human oversight, so automated fix attempts improve output quality without undermining user agency. The 2-iteration cap prevents runaway token consumption.

**Parallel fan-out for preflight checks**: `/check preflight` launches independent sub-checks (validate and review) as parallel Agent invocations, then synthesizes their results into a unified report. Each check writes to a unique output section to avoid conflicts. If one check fails, the other still produces results. Rationale: reduces wall-clock time for preflight checks without sacrificing completeness. The pattern applies to any future check modes that are independent and stateless.

**Q&A capture: companion-by-default with narrow inline opt-out**: post-skill emits a sibling `<prefix><id>-qa-<slug>.md` companion file collocated with the parent artifact. Parent skills opt into inline embedding via `skip_qa_log: true` only when the parent's primary content shape *is* a Q&A transcript -- currently only `/research`. Rationale: two structural reasons. (a) Maintainer-class collision -- plans are schema-fixed Agent files; design intent and ux research are `Human (markers)` enforced by `check_human_markers_only.py` and `check_changelog_append_only.py`, so an Agent-injected inline Q&A region either breaks the classification model or demands per-artifact exemptions. (b) `/reflect`'s `user_revised_output` field diffs the parent across commits to detect human edits; an Agent-written Q&A region inside the parent corrupts that signal unless `/reflect` learns a masking convention. Companion files keep the parent diff narrow and the maintainer-class boundary intact. Reference: advisory-000423.

**Meta-skills deferral**: Runtime skill generation (agents creating new SKILL.md files at runtime, per the ADK "Skill Factory" pattern) is deferred. Prerequisites for adoption: (1) agentskills.io spec compliance is enforced via automated validation (plan-000196 -- done); (2) a permission inheritance model is defined -- generated skills must inherit the permission ceiling of their parent skill; (3) constitution injection is mandatory for generated skills (cannot bypass); (4) generated skills cannot declare new file-write permissions beyond their parent's scope; (5) a "skill template" factory pattern (constrained parameters, pre-approved templates) is designed as the safe middle ground between full generation and prohibition. Revisit when prerequisites 1-4 are met. Reference: advisory-000188, council debate synthesis.

**Option A scaffolding split (/seja-setup owns topology; /design owns intent)**: Initial project scaffolding (Section 1 basic-definitions, conventions.md instantiation, brownfield stack auto-detection, CLAUDE.md generation, .claude/rules/ generation, smoke-test infrastructure) is owned by `/seja-setup`. Design intent (Section 0 metacomm, Sections 2-5+ conceptual-design / standards / UX / metacommunication, verification pass, REQ-ID assignment, product-design-as-intended.md instantiation, Design Update) is owned by `/design`. This preserves the WHAT/HOW boundary at a different cut than a /design-into-/plan merger would: /seja-setup owns topology-WHAT, /design owns design-intent-WHAT, /plan owns HOW. Stack-presence variability (API-only, frontend-only, CLI, full-stack) is handled at /seja-setup's conditional branches rather than in /design. Reference: advisory-000439 Q&A 2.

## Reference File Maintainer Summary

Quick-reference guide for agents: which files can be written to, which are read-only.
Classification values are defined in `.claude/references/general/shared-definitions.md` -- File Maintainer Classification.

### Group A -- Project-specific files (`project/`)

| File | Maintained by | Notes |
|------|---------------|-------|
| `project/constitution.md` | Human | Never agent-altered |
| `project/product-design-as-intended.md` | Human (markers) | Unified working intent (§0-§17), DRR-shaped Decisions section (`### D-NNN:` entries), §15 Designed User Journeys (JM-TB-NNN), and CHANGELOG. Markers (STATUS, ESTABLISHED, CHANGELOG_APPEND) via `apply_marker.py` only; prose remains human-authored. Enforced by `check_human_markers_only.py` and `check_changelog_append_only.py`. |
| `project/ux-research-results.md` | Human (markers) | Personas (R-P-NNN), problem scenarios (R-PS-NNN), journey observations (JM-E-NNN), and CHANGELOG. Markers via `apply_marker.py` only; §5 and CHANGELOG are append-only (enforced by `check_changelog_append_only.py`). |
| `project/product-design-as-coded.md` | Agent | Auto-updated by post-skill. Three H2 sections: Conceptual Design, Metacommunication, Journey Maps. Section boundary enforcement via `check_section_boundary_writes.py`. Unified in SEJA 2.8.4 (plan-000269). |
| `project/product-design-changelog.md` | Agent | Auto-updated by post-skill. Kept separate from product-design-as-coded.md (Phase 3 F will conditionally embed). |
| `project/conventions.md` | Human / Agent | Seeded by /design; primary human configuration file |
| Standards files (backend, frontend, testing, etc.) | Human / Agent | Seeded by /design; human-owned after generation |

> **Note**: The `Human (markers)` classification (see `.claude/references/general/shared-definitions.md` § File Maintainer Classification) is carried by `project/ux-research-results.md` since SEJA 2.8.2 (plan-000267, Phase 1 C from advisory-000264) and by `project/product-design-as-intended.md` since SEJA 2.8.3 (plan-000268, Phase 2 D from advisory-000264).

### Group B -- Harness source files (`general/`, `template/`)

Both harness authors and harness tooling (e.g., skills that generate index or summary files) may update these files.

| Path | Maintained by | Notes |
|------|---------------|-------|
| `general/*.md` | Human / Agent | Harness guidance; most files human-authored, some updated by agents |
| `template/*.md` | Human / Agent | Templates; human-authored harness source, may be updated by harness tooling |

## Codebase and workspace

`seja-priv` serves two roles in a single working tree: it is both the **codebase** that authors the harness and the **workspace** that hosts the harness's own design artifacts. The codebase/workspace separation that SEJA prescribes for consumer projects (see `/seja-setup --workspace`) applies here logically rather than physically. Contributors should know which half they are editing because edits to the codebase half propagate to downstream consumers while edits to the workspace half do not.

### The split

| Half | Paths | Propagates to public `seja` | Notes |
|------|-------|------------------------------|-------|
| Codebase | `.claude/` (skills, rules, agents, scripts), `.claude/references/general/`, `.claude/references/template/` | Yes (via `/publish`, which invokes `tools/sync_to_public.py --target` into an ephemeral temp clone) | The harness source of truth. Consumers receive these via `/seja-setup` (install and `--upgrade`). |
| Codebase (partial) | `seja-public/CHANGELOG.md`, `seja-public/README.md`, `seja-public/LICENSE`, `seja-public/TRADEMARKS.md`, `seja-public/docs/` | Yes (authored directly in the public tree; copied into the temp clone during `/publish`) | Public-facing prose that has no private counterpart. Edit in place. `CLAUDE.md` is NOT in this group -- it is generated from `./CLAUDE.md` by `sync_to_public.py` (via `ROOT_FILES`). `seja-public/.claude/` does NOT exist on disk -- it is generated ephemerally during `/publish` into a temp clone at `_output/tmp/publish-workspace/`. |
| Workspace | `_output/` (plans, roadmaps, advisory-logs, research-logs, qa-logs, reflections, proposals, pending ledger, decision digest), `.claude/skills/scripts/priv/`, private-only fragments inside shared `.md` files (guarded by priv-only-start / priv-only-end HTML-comment markers) | No (excluded by sync, or stripped) | SEJA's own design artifacts and private tooling. Iteration history and strategic context live here. |
| Harness-dev tools | `tools/publish.py`, `tools/sync_to_public.py`, `tools/cut_tag.py`, `tools/pre_publish_smoke.py`, `tools/monthly-dogfood-playbook.md` | No (not in sync scope) | Private to harness development; invoked by `/publish`, not consumed by projects. |

`/publish` orchestrates the release pipeline: it clones the public `seja` repo to `_output/tmp/publish-workspace/`, copies authored prose from `seja-public/`, runs `sync_to_public.py --target <clone>` to generate `.claude/` with `priv/` and `project/` subdirectories excluded and priv-only/pub-only markers processed in `.md` files, and syncs root-level files listed in `ROOT_FILES` (currently `CLAUDE.md`) with the same marker processing. It then runs smoke tests via `pre_publish_smoke.py --candidate <clone>`, commits, and pushes. Harness reference files (`.claude/references/general/` and `.claude/references/template/`) are included as part of `.claude/`. The temp clone is deleted after a successful push.

### Why the split is logical, not physical

Advisory 000366 evaluated moving to a physically-separated pair of repositories (workspace consumer of a standalone public `seja`) and settled on **Option A2**: keep the embedded monorepo, add release discipline, and gate public sync manually. The decisive constraints were publication-privacy-by-construction (public must show only polished evolution) and the decision that SEJA will not be open-sourced. Under those constraints, the logical split captures the pattern's intent without paying the migration cost. The ADR is recorded at `_output/adrs/adr-0001-a2-repo-structure.md`; the full discussion is in `_output/advisory-logs/advisory-000366-workspace-separation-from-seja.md`.

### Implications for contributors

- Editing codebase half → affects downstream consumers at the next release. Edit only the `seja-priv` sources (`.claude/`, `product-design/`); do NOT recreate `seja-public/.claude/` on disk. The `/publish` skill generates `.claude/` ephemerally into a temp clone (`_output/tmp/publish-workspace/`) via `sync_to_public.py --target`, so there is no on-disk mirror to hand-edit.
- Editing workspace half → visible only inside `seja-priv`. Safe to iterate, reorganize, or delete without consumer impact.
- Editing a shared `.md` file that carries priv-only markers → the codebase half is the public-visible portion (post-strip); the workspace half is the markered region. Run `python .claude/skills/scripts/priv/check_no_private_leaks.py` after the change to verify the stripper handles it correctly.
- When in doubt, check whether the file would appear in `seja-public/` after running `tools/sync_to_public.py --dry-run`.

## Private-Only Content Convention

The SEJA harness maintains a public distribution (the `seja` GitHub repo) published from `seja-priv` via the `/publish` skill. During publish, `sync_to_public.py --target` generates `.claude/` into an ephemeral temp clone, stripping private content. Some features and scripts are exclusive to the harness development repo and must not appear in the public copy.

### Partial content: conditional markers

For private-only content embedded within shared files (e.g., a `--harness` flag in a SKILL.md that also has public flags), use HTML comment markers:

```markdown
<!-- priv-only-start -->
| `--harness` | No | Harness-exclusive flag description |
<!-- priv-only-end -->
```

The sync tool's `strip_private_sections()` function removes all content between markers (inclusive) when copying `.md` files during `/publish` (via `sync_to_public.py --target` into the temp clone). Markers are invisible in rendered Markdown and self-documenting in source.

### Whole scripts: `scripts/priv/` directory

For scripts that are entirely private (no public use case), place them in `.claude/skills/scripts/priv/`. This directory is excluded from sync (`EXCLUDE_DIRS` in `sync_to_public.py`) and from `collect_source_files()` in `upgrade_harness.py`, so seeded/upgraded projects never receive these scripts.

### Validation

`priv/check_no_private_leaks.py` operates in three modes: (1) default mode scans only authored prose in `seja-public/` (top-level `*.md` and `docs/**/*.md`), (2) `--candidate DIR` runs the full leak scan against a publish workspace (used by `pre_publish_smoke.py` during `/publish`), and (3) `--staged`/`--files` for the pre-commit gate. Registered in `run_preflight_fast.py` and runs as part of `/check validate`.
