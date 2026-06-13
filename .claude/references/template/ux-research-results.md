# TEMPLATE -- UX RESEARCH

<!-- maintained-by: human (designer/researcher); Human (markers) classification since SEJA 2.8.2 -->

> **How to use this template:** Copy this file to `project/ux-research-results.md` and record UX research findings as they arrive. This unified file replaces the two separate ux-research-new.md and ux-research-established.md files that existed prior to SEJA 2.8.2. See the harness CHANGELOG for the migration rationale (source: advisory-000264 Phase 1 C).
>
> **Classification**: `Human (markers)` -- prose content (personas, problem scenarios, journey observations) is human-authored only. Agents may write fixed-format markers (`<!-- INCORPORATED: plan-NNNNNN | YYYY-MM-DD -->`) and append lines to the `## CHANGELOG` section at the bottom of the file, but only via `apply_marker.py` and only after AskUserQuestion confirmation. Enforced by `check_human_markers_only.py` and `check_changelog_append_only.py` during post-skill step 6c.
>
> **Stable IDs**: personas use `R-P-NNN`, problem scenarios use `R-PS-NNN`, discovered journeys use `JM-E-NNN`. IDs are stable across the file's lifetime. Revising an entry in place preserves the ID; superseding an entry mints a new ID and records a `superseded` CHANGELOG entry. Designers MUST use unique R-P-NNN, R-PS-NNN, and JM-E-NNN IDs within the file -- `apply_marker.py` raises `entry id <id> matches N headings (ambiguous)` if two headings share the same ID, which would block marker application.
>
> **One-directional flow**: Research findings in `§5 Discovered User Journeys` inform `project/product-design-as-intended.md §15 Designed User Journeys` (per advisory-000264 Phase 2 design-intent merge). Section 5 is structurally append-only for prose: agents may insert managed INCORPORATED markers above existing headings, but no prose line can be removed, modified, or inserted in the middle. Enforced by `check_changelog_append_only.py`.
>
> **Consistency checking**: The agent can verify consistency between UX research, design intent, and the implemented solution via `/explain spec-drift` or `/check validate`. The agent does not write prose content to this file -- only the designer/researcher does.

---

## 1. Personas

> Define the people who use (or will use) your system. A persona may have multiple goals. Keep personas minimal -- elaborate only as understanding grows. Sections can be marked "N/A -- single-persona product" for simple projects. When a persona's research is incorporated into a design iteration, post-skill will propose an `<!-- INCORPORATED: plan-NNN | YYYY-MM-DD -->` marker via AskUserQuestion.

### Persona Inventory

| ID | Name | Role / Archetype | Goals |
|----|------|-----------------|-------|
| R-P-001 | {{PersonaName}} | {{role}} | {{goal 1, goal 2, ...}} |

<!-- INCORPORATED marker goes on the line immediately above each persona heading once the persona is used in a plan. Example:
  <!-- INCORPORATED: plan-000268 | 2026-04-11 -->
  ### R-P-001: {{PersonaName}}
-->

### R-P-001: {{PersonaName}}

> **Role / Archetype:** {{role}}
>
> **Bio:** {{1-2 sentences of relevant context -- who they are, what they do, how they relate to the problem domain}}
>
> **Goals:**
> - {{G-001}}: {{goal description}}
> - {{G-002}}: {{goal description}}
>
> **Key Frustrations:**
> - {{frustration related to G-001}}
> - {{frustration related to G-002}}
>
> **Relevant Context:**
> - Technical proficiency: {{novice / intermediate / expert}}
> - Usage frequency: {{daily / weekly / occasional}}
> - Domain knowledge: {{description of their domain expertise}}

---

## 2. Problem Scenarios

> Describe the user's pain without the system (or with the current system's limitations). Problem scenarios ground design decisions in real user pain. Each scenario uses a narrative structure: setting, actor, and current pain. A scenario is associated with one or more persona goals. When a scenario is incorporated into a design iteration, post-skill will propose an `<!-- INCORPORATED: plan-NNN | YYYY-MM-DD -->` marker.

### R-PS-001: {{Problem Scenario Title}}

- **Persona:** R-P-001 ({{PersonaName}})
- **Goals:** {{G-001}}, {{G-002}}
- **Setting:** {{where and when the user encounters this problem}}

{{2-3 paragraphs describing the problem narrative. What is the user trying to do? What goes wrong? What is frustrating, slow, or impossible? Write concretely -- use the persona's context to make the scenario vivid and specific.}}

> Are there misuse contexts for this scenario? If so, note them for security review in `project/security-checklists.md`.

---

## 3. Cross-Reference Map

> Explicit links between research artifacts and design-intent files. Personas and problem scenarios feed the EMT analysis section in `project/product-design-as-intended.md`. Solution representations (scenarios, user stories) are recorded in `project/product-design-as-intended.md` Section 13, not here -- they are design decisions, not research.

| Artifact ID | Artifact Title | Design Artifact | Relationship |
|-------------|---------------|----------------|-------------|
| R-P-001 | {{PersonaName}} | product-design-as-intended EMT 1.1 (What I know about you) | Feeds |
| R-PS-001 | {{scenario title}} | product-design-as-intended EMT 1.1, 1.3 (Contexts of use) | Feeds |
| JM-E-001 | {{journey title}} | §5 below (internal reference) | Research evidence |

> Journey map entries from research sessions are documented in §5 below.

---

## 4. Processing Status

> Incorporation status for each research entry. This table is a convenience view -- authoritative status lives in the inline `<!-- INCORPORATED: plan-NNN | YYYY-MM-DD -->` markers on each entry heading. Post-skill proposes these markers via AskUserQuestion and applies them via `apply_marker.py` on confirmation. The old "move entries from new to established" workflow is replaced by in-place marker application.

| Artifact | ID | Status | Design Iteration | Notes |
|----------|-----|--------|-----------------|-------|
| {{persona / problem scenario}} | R-P-001 / R-PS-001 | {{pending / incorporated}} | {{plan-NNNNNN or -}} | {{notes}} |
| Discovered journey | JM-E-001 | {{pending / incorporated}} | {{plan-NNNNNN or -}} | {{notes}} |

---

## 5. Discovered User Journeys

<!-- maintained-by: human (researcher/designer) -- prose is human-only; append-only enforced by check_changelog_append_only.py; INCORPORATED markers allowed above JM-E-NNN headings via apply_marker.py -->

> Journey maps discovered through user research sessions (field observations, usability studies, contextual inquiry, diary studies, etc.). These are empirical findings -- they describe what users *actually do*, not what was designed or what is implemented.
>
> **One-directional flow:** Research findings here inform `project/product-design-as-intended.md §15` (Designed User Journeys). They do NOT flow back into this file.
>
> **Append-only discipline:** This section is structurally append-only for prose. `check_changelog_append_only.py` (post-skill step 6c) diffs this section against the prior git commit using a prose-only rule: lines matching any marker regex in `human_markers_registry.ALLOWED_MARKERS` are filtered out before comparison, so `apply_marker.py` may insert `<!-- INCORPORATED: plan-NNN | YYYY-MM-DD -->` markers above existing `### JM-E-NNN:` headings without triggering a middle-insertion violation. Prose lines, however, cannot be removed, modified, or inserted in the middle. Only prose additions at the end are allowed.
>
> **Related files:**
> - `project/product-design-as-intended.md §15` -- designed journeys (as-intended, human-maintained)
> - `project/product-design-as-coded.md § Journey Maps` -- implemented journeys (agent-maintained)

<!--
  ENTRY PATTERN -- copy this block for each journey map entry from a research session
  ===================================================================================

  ### JM-E-NNN: {{Journey Title}}

  - **Research source:** {{method}} | {{YYYY-MM}} | n={{N}} (required -- e.g., "contextual inquiry | 2025-11 | n=8")
  - **Persona:** R-P-NNN (optional -- link to §1 Persona ID when available)
  - **Problem scenario:** R-PS-NNN (optional -- link to §2 Problem Scenario when available)
  - **Goal:** {{what the user is trying to achieve}}
  - **Pre-conditions:** {{what is true when the journey starts}}

  #### Steps

  | # | Observation | Touchpoint | User Emotion | Pain Point | Source |
  |---|------------|-----------|-------------|-----------|--------|
  | 1 | {{what the researcher observed the user doing}} | {{where they interact}} | {{how they appeared to feel}} | {{friction or frustration observed}} | {{specific session / artifact reference}} |
  | 2 | {{observation}} | {{touchpoint}} | {{emotion}} | {{pain point}} | {{source}} |

  > **Source column** (required in template; if unavailable, note the session date):
  > Reference the specific session, recording, or artifact where this observation was
  > made (e.g., "session-2025-11-03", "diary study P4", "usability test recording #7").

  #### Key Findings

  {{2-3 bullet points summarizing the most important insights from this journey.}}

  #### Mermaid Diagram (optional)

  ```text
  journey
      title {{Journey Title}}
      section {{Phase 1}}
          {{Observed action 1}}: {{satisfaction 1-5}}: User
          {{Observed action 2}}: {{satisfaction 1-5}}: User
      section {{Phase 2}}
          {{Observed action 3}}: {{satisfaction 1-5}}: User
  ```

  > Satisfaction scores derived from observed behavior and verbal protocols:
  > 1 = frustrated, 3 = neutral, 5 = delighted.

  ===================================================================================
-->

---

## CHANGELOG

<!-- Append-only. Format: YYYY-MM-DD | <entry-id> | added|revised|revoked|superseded | plan-NNNNNN | <note (max 200 chars, no HTML comment control chars)>
     New lines are appended at the bottom via apply_marker.py CHANGELOG_APPEND. Historical lines must never change. Enforced by check_changelog_append_only.py (strict prefix-preserving rule).
     The original section numbers from the pre-2.8.2 two-file layout are preserved in spirit -- designers who migrate existing ux-research-new and ux-research-established content should seed this CHANGELOG with the historical Processing Log entries as the initial "added" events. -->

{{YYYY-MM-DD}} | R-P-001 | added | - | initial persona entry
