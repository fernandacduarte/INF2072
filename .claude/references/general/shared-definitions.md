---
designer_description: "When a skill, plan, or artifact uses a harness-wide concept -- the metacommunication message and its first-person I / second-person you phrasing rule, the Semiotic Engineering grounding behind review perspectives and spec-drift, the File Maintainer Classification that controls who may edit what -- I'm the reference that holds the canonical definitions, so the same term means the same thing everywhere."
---

# GENERAL - SHARED DEFINITIONS

## Terminology

> Core terms for how SEJA describes itself and the actors it governs. Every skill,
> agent, plan, and reference file should use these terms consistently.

| Term | Definition | Notes |
|------|-----------|-------|
| **harness** | SEJA's category: the governance layer that constrains and shapes the model's behavior through skills, rules, references, agents, and lifecycle hooks. An agent harness is not a programming framework -- it does not provide libraries, base classes, or runtime abstractions. It provides governance, constraints, and lifecycle management. | Primary compound: "SEJA is an agent harness grounded in semiotic engineering." Use "SEJA" (proper noun) as the default reference, "the SEJA harness" when the category needs emphasis, and "agent harness" as the generic category. |
| **the agent** | Claude -- the LLM and CLI tool. Refers to the model's raw capabilities: generating code, answering questions, using tools. When a sentence describes behavior that exists without SEJA governance, use "the agent." | Example: "The agent can generate code, but without governance it skips planning and review." |
| **the harnessed agent** | The composite of Claude operating within the SEJA harness. When the harness shapes the agent's behavior -- reading the constitution, following lifecycle skills, applying review perspectives, consulting design intent before coding -- the result is the harnessed agent. | Example: "The harnessed agent plans before building, reads the constitution, and follows review perspectives." Use this term when SEJA's contribution to the behavior should be visible. |
| **subagent** | A specialized agent delegated to by the main agent via the Agent tool. Subagents run in isolated context windows with focused prompts (e.g., `code-reviewer`, `document-generator`, `harness-health-evaluator`). | Unchanged term. See `.claude/agents/` for the full inventory. |

---

## Semiotic Engineering concepts

The **metacommunication message** is a designer-to-user message conveyed throughout the system and UI. Semiotic engineering summarizes it as: "Here is my understanding of who you are, what I've learned you want or need to do, in which preferred ways, and why. This is the system that I have therefore designed for you, and this is the way you can or should use it in order to fulfill a range of purposes that fall within this vision."

**Phrasing rule (non-negotiable)**: All metacommunication messages -- in templates, project files, plans, briefs, per-feature logs, and EMT answers -- **must** use first-person "I" for the designer and second-person "you" for the user. Never use "the designer", "the system", "the user" (third-person), passive voice, or imperative mood. Applies to all sections of `project/metacomm-*.md`: global summary/vision, every EMT answer, every per-feature intent. Example: write "I designed a postpone shortcut for you because I know you tend to over-schedule" -- not "The designer provides a postpone shortcut" or "Enforce privacy with minimal friction."

**Verbatim rule**: When a user provides a metacommunication message as input (during /design, in a spec, in `project/product-design-as-intended.md`, or as a `--framing metacomm` brief), the agent must record it **exactly as written**, without summarization or editing. The designer's precise wording carries intentional nuance; paraphrasing distorts design intent.

---

## Theoretical Foundations

> SEJA is grounded in Semiotic Engineering (SemEng), a theory of HCI that treats
> human-computer interaction as computer-mediated human communication. The table below
> maps SEJA concepts to SemEng origins for intellectual traceability -- skills and
> agents do not require users to know SemEng terminology.

| SEJA Concept | SemEng Origin | Source |
|---|---|---|
| Metacommunication files (product-design-as-intended/as-coded § Metacommunication) | Metacommunication template -- abstract designer-to-user message | [SemEng-2005, Ch. 1 & 3] |
| First-person "I/you" phrasing rule | Designer's personal engagement -- designers as communicators | [SemEng-2005, Ch. 3 p.84] |
| Extended Metacommunication Template (EMT) | EMT with guiding questions per lifecycle stage (Analysis, Design, Prototype, Evaluation) | [EMT-Ethics-2021, pp.365-368] |
| Spec-drift detection (as-coded vs. as-intended) | Communicability monitoring -- tracking design-intent transmission | [SemEng-2005, Ch. 4; SemEng-Methods-2009] |
| Constitution (immutable principles) | Value inscription governance -- making implicit values explicit | [SemEng-2005, Ch. 1 pp.9-10] |
| Design -> plan -> implement -> check pipeline | Meaning propagation -- conception-to-code transforms | [SigniFYI-2016] |
| Review perspectives (16 lenses) | Communicability evaluation -- segmented multi-viewpoint analysis | [SemEng-2005, Ch. 4; SemEng-Methods-2009] |
| Council-debate agent | Formalized abductive reasoning with multiple perspectives | [SemEng-2005, Ch. 2 on abduction] |
| Pre/post-skill pipelines | Reflection in/on action -- structured reflection around each action | [SemEng-2005, Ch. 1, citing Schon 1983] |
| Behavior-evolution reconstruction | Reflection on practice -- surfacing tacit understandings | [SemEng-2005, Ch. 1, citing Schon 1983] |
| Role families (BLD/SHP/GRD) + expertise levels (L1-L5) | Multi-audience metacommunication -- segmenting the "you" | [SemEng-2005, Ch. 3 & 6] |
| _output/ infrastructure (INDEX, briefs, plans) | SigniFYIng Traces -- capture/access infrastructure | [SigniFYI-2016] |
| Conventions.md (project signification system) | Signification systems -- conventionalized expression-content pairs | [SemEng-2005, Ch. 2, citing Eco 1976] |
| Communicability review questions (UX/DX perspectives) | CEM 13 communicability utterances | [SemEng-2005, Ch. 4 pp.123-138] |
| Sign classification lens (UX perspective) | Three classes of interface signs (static, dynamic, metalinguistic) | [SemEng-2005, Ch. 4; SemEng-Methods-2009] |
| CDN review questions (API/ARCH perspectives) | Cognitive Dimensions of Notations -- 14 dimensions | [SigniFYI-2016, citing Green & Petre] |

---

## Notation Conventions

### Standards section notation

Cross-references to the unified standards files use the form `standards.md § Backend > 6`: `§ <Domain>` identifies the H2 section (Backend, Frontend, Testing, i18n for `standards.md`; UX patterns, Graphic / visual design for `design-standards.md`) and `> N` identifies the H3 subsection whose heading begins with `N.`. Original pre-2.8.1 section numbers are preserved so legacy citations like `backend-standards §6` map to `standards.md § Backend > 6` by direct substitution.

---

## Lifecycle Markers

> Inline markers tracking the lifecycle of as-intended items across registered as-intended
> files (see conventions.md As-Intended / As-Coded Registry). Defined here for consistency
> across skills and agents.
>
> **Agent rules**: agents may read markers and propose new IMPLEMENTED markers (via
> AskUserQuestion in post-skill). Agents must NEVER remove or alter an existing
> IMPLEMENTED or ESTABLISHED marker -- these are audit records.

### STATUS marker (prose sections)

Inline HTML comment immediately before the section heading -- invisible in rendered markdown, machine-parseable by agent tooling. Two schemes coexist on disk:

- **Legacy (pre-2.8.0, still supported):** single uppercase `IMPLEMENTED`, typically paired with a later `ESTABLISHED` stamp on promotion. A legacy marker without a plan ID is valid for items implemented outside the plan workflow (`manual`):
  ```markdown
  <!-- STATUS: IMPLEMENTED | plan-NNNNNN | YYYY-MM-DD -->
  ### Section Title
  ```
- **Current (2.8.0+, used by `apply_marker.py` and middle-path enforcement):** lowercase multi-value marker with state machine `proposed -> implemented -> established -> superseded`. Introduced by advisory-000264 Q3; enforced by `check_human_markers_only.py` for `Human (markers)` files:
  ```markdown
  <!-- STATUS: proposed | plan-NNNNNN | YYYY-MM-DD -->
  ### Section Title
  ```
  Plan ID and date are optional for `proposed` (initial state) and required after. Transitions are validated via `human_markers_registry.ALLOWED_MARKERS["STATUS"]["allowed_transitions"]`: `proposed -> implemented`, `implemented -> established`, `established -> superseded`. Regression (e.g., `established -> implemented`) is rejected.

Uppercase `STATUS: IMPLEMENTED` markers remain valid. The widened `_STATUS_MARKER_RE` (SEJA 2.8.3, plan-000268 Amendment A1) detects legacy markers so a Phase 3b flip REPLACES rather than stacks. New/consolidated files use the lowercase scheme; `project/product-design-as-intended.md` (since SEJA 2.8.3) is the canonical lowercase-primary Human (markers) file.

### Decision entries (DRR)

Design-intent decision entries live in `project/product-design-as-intended.md §
Decisions` under `### D-NNN: Title` headings (DRR shape (see `template/docs/drr.md` for the canonical template)). The `D-NNN` namespace is
**orthogonal to REQ-TYPE-NNN** -- separate taxonomies, never intermixed. REQ markers
trace individual requirements; Decision entries capture rationale and trade-offs behind
larger architectural choices. D-NNN entries are the capture mechanism (created by `/research` step 9b); standalone DRR files in `docs/drr/` are the publication mechanism (created by `/document --type drr`, optionally sourced from existing D-NNN entries).

Decision entries carry their own `STATUS` marker (lowercase multi-value scheme) above
the heading:

```markdown
<!-- STATUS: proposed | plan-NNNNNN | YYYY-MM-DD -->
### D-001: Use PostgreSQL as primary datastore

**Context**: ...
**Decision**: ...
**Consequences**: ...
```

`/explain spec-drift --promote` (Phase 3a) drafts DRR-shaped entries from plan metadata
for items marked `STATUS: implemented`, writing to
`_output/promote-proposals/promote-proposal-plan-<id>.md`. The designer reviews, edits
to their voice, and copies entries into `product-design-as-intended.md § Decisions`.
Phase 3b (`--apply-markers plan-<id>`) then flips STATUS markers from `implemented` to
`established` via `apply_marker.py`, using heading-only grep
(`^###\s+D-NNN(?::|\s*$)`) to verify presence without matching prose (designer-voice
preservation per advisory-000264 Q4).

### IMPLEMENTED marker (table rows)

For structured tables (e.g. journey map steps), add a Status column:

| # | ... | Status |
|---|-----|--------|
| 1 | ... | DONE (plan-000178, 2026-04-02) |
| 2 | ... | - |

### ESTABLISHED stamp

Applied when a human confirms promotion of an IMPLEMENTED item (via `/explain
spec-drift --promote` or manual curation):

```markdown
<!-- ESTABLISHED: plan-NNNNNN | YYYY-MM-DD | vX.Y.Z -->
```

The `vX.Y.Z` field is optional; projects without semver use date only:
`<!-- ESTABLISHED: plan-000178 | 2026-04-02 -->`.

In the as-intended file, the IMPLEMENTED marker is replaced with the ESTABLISHED stamp
(or the entry is removed -- both valid). Pre-2.8.3 two-file projects appended the stamp
to a separate established file instead.

---

## Requirement ID Convention

Stable, machine-parseable identifiers for design-intent requirements, enabling spec-to-plan traceability. Each marker is an HTML comment placed immediately before the heading, table row, or bullet that defines the requirement.

**Format**: `<!-- REQ-TYPE-NNN -->`

**Type prefix taxonomy**:

| Type Prefix | Design-Intent Section | Classification | Enforcement |
|------------|----------------------|---------------|-------------|
| ENT | 2. Entity Hierarchy | technical | advisory |
| PERM | 4. Permission Model | security | blocking at preflight |
| VAL | 10. Validation Constants | security | blocking at preflight |
| UX | 8. UX Patterns | ux | advisory |
| MC | 14. Per-Feature Metacomm | ux | advisory |
| JM | 15. Designed User Journeys | ux | advisory |
| I18N | 7. Localization | cross-cutting | advisory |
| DELTA | 16-17. Deltas | technical | advisory |

**Classification rule**: Security-classified requirements (PERM, VAL) must be traced by a plan step in the same wave as their parent entity. Advisory-classified requirements produce warnings but do not block.

**Plan step tracing**: Plan steps declare satisfied requirements via the `Traces` metadata field (e.g., `- **Traces**: REQ-ENT-001, REQ-PERM-003`). Coverage is verified by `check_plan_coverage.py`.

**Auto-generation**: `/design` auto-assigns REQ IDs during verification. NNN is a zero-padded 3-digit counter per type, starting at 001.

> **Footnote**: `D-NNN` (see Decision entries above) is **orthogonal** to `REQ-TYPE-NNN`. Never interpolate D-NNN into the REQ taxonomy and never write `REQ-D-NNN` collisions.

---

## File Maintainer Classification

Four-value scheme applied to all reference files in `product-design/` (principally `project/`). Used as the "Maintained by" column in `project/conventions.md` Key Files table, and summarized in `.claude/references/general/harness-governance.md`.

| Value | Meaning | Agent rule |
|-------|---------|-----------|
| **Human** | Authored and updated exclusively by humans. | Agents must NOT write. May read and propose changes via `AskUserQuestion`. |
| **Human (markers)** | Human-authored prose; agent may write fixed-format structured markers only (STATUS flags, INCORPORATED stamps, CHANGELOG append lines). | Agents write only via `apply_marker.py` after explicit `AskUserQuestion` confirmation in the same turn. Never write prose or modify text outside allowed marker patterns. Enforced by `check_human_markers_only.py` during post-skill step 6c. |
| **Agent** | Auto-maintained by agents and skills (e.g., via post-skill). | Agents read/write. Humans typically do not edit directly. |
| **Human / Agent** | Seeded by an agent (e.g., `/design`), then human-owned; both may update. Also applies to harness source files (`general/`, `template/`). | Agents may write per file's own rules. Humans are primary curators after seeding. |

---

## External Specifications

| Spec | Description | SEJA Integration |
|------|-------------|-----------------|
| **agentskills.io** | Portable AI agent skill definitions: `name` (1-64 chars, lowercase alphanumeric + hyphens), `description` (1-1024), optional `compatibility` (<=500), extensible `metadata`. | SKILL.md frontmatter follows the spec; SEJA-specific fields are under `metadata`. Validated by `check_skill_spec.py`. |

---

## Versioning

SEJA uses three version-bearing files with distinct purposes:

| File | Location | Purpose | Maintained by | When to update |
|------|----------|---------|---------------|----------------|
| `.claude/skills/VERSION` | Harness source | Authoritative harness version (semver) | Manual (developer) | Bump every release |
| `.claude/CHANGELOG.md` | Harness source | Human-readable release history | Manual (developer) | Add `## [x.y.z]` heading matching VERSION every release |
| `.seja-version` | Project root | Per-project migration watermark | Automated (`run_migrations.py`, `/seja-setup --upgrade`) | Written automatically; records the version a project was last migrated to |

**Key distinction**: `.claude/skills/VERSION` tracks what the harness IS; `.seja-version` tracks what a project has been UPGRADED TO. In the harness repo, `.seja-version` is dogfooded -- should match VERSION after each release.

**Validation**: `check_version_changelog_sync.py` keeps VERSION and CHANGELOG in sync (runs in `/check preflight`). Use `bump_version.py` to update all three files atomically.

---

## Generic Terminology

| Term | Definition | Used In |
|------|-----------|---------|
| **Soft delete** | Records marked deleted via `deleted_at` timestamp rather than physically removed; queries must filter for non-deleted records. | project/standards.md § Backend > 6 |
| **Double confirmation** | Destructive-action pattern requiring the user to type a confirmation word before enabling the action. | project/standards.md § Frontend > 11 |
| **Review perspective** | Domain-based evaluation lens (SEC, PERF, DB, etc.) applied to code, plans, or decisions per `general/review-perspectives.md`. | general/review-perspectives.md |
| **Pinned anchor** | Reference file that must survive context compaction and be re-injected verbatim after any summarization. List in `general/constraints.md` under "Pinned Anchors (Non-Compactable Context)". | general/constraints.md |

---

## If stack includes React

| Term | Definition | Used In |
|------|-----------|---------|
| **Orchestrator page** | Page-level component that owns state, effects, and business logic; delegates rendering to sub-components in `features/<domain>/`. | project/standards.md § Frontend > 1, > 2 |
| **Feature co-location** | Placing feature-specific hooks, forms, sub-components, and utils together in `features/<domain>/` rather than scattering across `hooks/`, `components/`, etc. | project/standards.md § Frontend > 1, > 20 |

## If stack includes Flask/Python

| Term | Definition | Used In |
|------|-----------|---------|
| **Three-layer architecture** | Backend pattern separating API (HTTP), Services (business logic), Models (data); services are HTTP-agnostic. | project/standards.md § Backend > 4 |
| **Service layer contract** | Services accept plain arguments, raise error subtypes, and never import framework request/response objects. | project/standards.md § Backend > 19 |
| **Response builder** | Utility functions producing consistent JSON response envelopes (success, error, paginated). | project/standards.md § Backend > 8 |

## If stack includes CSS/HTML

| Term | Definition | Used In |
|------|-----------|---------|
| **BEM** | Block Element Modifier -- CSS class naming convention for custom component classes (`block__element--modifier`). | project/standards.md § Frontend > 5 |

## If stack includes a frontend

| Term | Definition | Used In |
|------|-----------|---------|
| **Design tokens** | Centralized style primitives (colors, fonts) consumed by both the CSS framework config and app code. | project/standards.md § Frontend > 5 |

## Advisory terminology rule

The word `advis*` carries two distinct senses; apply them differently:

- **Sense A -- artifact-type name.** "Advisory" as the artifact type `/research` produces (formerly `/advise`). Renamed to `research` in advisory-000448 (filenames, folders, headers); completed in plan-000468 (skill bodies, `research-reviewer` agent, telemetry keys, reference prose). New writes use `research`; historical `advisory-NNN` cross-references and the `${ADVISORY_DIR}` legacy read alias are preserved under advisory-000448's forward-only rule.
- **Sense B -- engineering adjective meaning non-blocking / informational.** Examples: `/plan` "Coverage check (advisory)", post-skill "advisory, not blocking" preflight wording, `advisory` as requirement classification (opposite of `security`-blocking above). Unchanged -- describes *severity*, not artifact type.

When you encounter `advis*`, ask: artifact type or severity? Sense A renames to `research`; Sense B keeps the adjective. Origin: research-000467.
