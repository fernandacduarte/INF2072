---
designer_description: "I'm the as-coded mirror of what actually shipped in your project -- conceptual design, metacommunication, and journey maps kept in step with the codebase by post-skill after each plan -- so drift against your product-design-as-intended.md is always visible rather than something you have to reconstruct by reading source."
---

# TEMPLATE -- AS-CODED

<!-- maintained-by: Agent (post-skill); Agent classification since SEJA 2.8.4 -->

> **How to use this template:** Copy this file to `project/product-design-as-coded.md`. It records the implementation state (as-coded) in three domain sections: Conceptual Design, Metacommunication, and Journey Maps. This unified file replaces the three separate as-is files (conceptual-design-as-is, metacomm-as-is, journey-maps-as-is) that existed prior to SEJA 2.8.4. See the harness CHANGELOG for the migration rationale (source: advisory-000264 Phase 2 E).
>
> **Classification**: `Agent` -- this file is written by post-skill step 2 after each plan execution. Designers read the file to understand what the codebase currently implements; post-skill mirrors the target product-design-as-intended.md structure into the three sections here as code ships.
>
> **Section boundary discipline**: post-skill writes target one H2 domain section at a time. The `check_section_boundary_writes.py` validator at preflight step 6c rejects any contiguous write region that spans two or more H2 sections. This catches the class of bug where a buggy Edit call accidentally modifies an adjacent section. The validator uses git-diff against the prior commit and allows arbitrary edits WITHIN a section.
>
> **Related files:**
> - `project/product-design-as-intended.md` -- target design intent, Human (markers) classification (since SEJA 2.8.3)
> - `project/product-design-changelog.md` -- changelog for conceptual-design changes, kept separate (Phase 3 F will embed conditionally)

---

## Conceptual Design

<!-- Unified conceptual design (§1-§10 as H3+ subsections) -->

### 1. Platform Purpose

> Describe in 2-3 paragraphs: What does this platform do? Who is it for? What problem does it solve?

#### Design Philosophy

> If the platform follows a specific design philosophy or methodology, document it here. This helps ensure all design decisions align with the platform's core intent.

### 2. Entity Hierarchy

> Map out the primary entities and their relationships. Use an ASCII tree to show containment/hierarchy:

```
{{TopLevelEntity}}
└── {{ChildEntity}}
    └── {{GrandchildEntity}}
        └── {{LeafEntity}}
```

#### {{TopLevelEntity}}

> For each entity, document:
> - What it represents in the domain
> - Visibility/access rules
> - Ownership model
> - Uniqueness constraints
> - Soft delete behavior (if applicable)

#### {{ChildEntity}}

> - Scope: Belongs to exactly one {{TopLevelEntity}}
> - Key domain rules

#### {{LeafEntity}}

> - The atomic unit of content
> - Threading/nesting behavior (if applicable)
> - Content format (plain text, rich text, etc.)
> - Attachment support (if applicable)

### 3. Domain-Specific Concepts

> Document any domain-specific concepts that are unique to this application and not covered by standard CRUD patterns. For each concept:
> - What it is
> - Why it exists
> - How it relates to other entities
> - Any multilingual or localization requirements

### 4. Permission Model

> Define the permission levels for your application. Most applications have at least two levels: system-wide roles and resource-level access.

#### System-Level Roles

| Role | Level | Capabilities |
|------|-------|-------------|
| {{Role1}} | {{level}} | {{description}} |
| {{Role2}} | {{level}} | {{description}} |
| {{Role3}} | {{level}} | {{description}} |

#### Resource-Level Access

> If your application has resource-scoped permissions (e.g., per-group, per-project, per-organization), define them here:

| Access Level | Level | Capabilities |
|-------------|-------|-------------|
| {{Level1}} | {{value}} | {{description}} |
| {{Level2}} | {{value}} | {{description}} |

> **Rationale:** Explain why these specific permission levels exist and how they map to real-world user roles.

### 5. Content Authoring & Attribution

> If your application supports content creation, document:
> - How authorship is tracked
> - Whether content can be attributed to non-system users
> - Mention/notification systems
> - Import/export attribution rules

### 6. Content Import & Export

> If applicable, document supported formats:

#### Import Formats

| Format | Source | Features |
|--------|--------|----------|
| {{format}} | {{source}} | {{features}} |

#### Export Formats

| Format | Output | Use Case |
|--------|--------|----------|
| {{format}} | {{output}} | {{use_case}} |

### 7. User Community & Localization

#### Target Community

> Describe the primary user base: language, geography, domain expertise.

#### Localization Design

| Aspect | Primary | Secondary |
|--------|---------|-----------|
| UI default language | {{PRIMARY_LOCALE}} | {{SECONDARY_LOCALE}} |
| Backend error default | {{BACKEND_DEFAULT}} | — |

> Explain why these locale choices were made.

### 8. User Experience Patterns (Domain-Driven)

> Document the key UX patterns that are driven by domain requirements rather than generic UI conventions. For each pattern:
> - What the user sees/does
> - Why this pattern was chosen (domain rationale)
> - Any metacommunication intent

### 9. Administrative Domain

#### Activity Logging

> What operations are logged? What format?

#### Backup & Restore

> Any domain-specific backup/restore requirements?

#### Terms & Conditions

> Any domain-specific legal/compliance requirements?

### 10. Validation Constants (Domain)

> Domain-driven validation limits. These should reflect real-world constraints, not arbitrary technical limits.

| Constant | Value | Domain Rationale |
|----------|-------|-----------------|
| {{field}} length | {{min}}–{{max}} chars | {{why}} |

> **Note:** These constants must be kept in sync between backend and frontend. See `project/security-checklists.md` Quick Reference for the technical mapping.

---

## Metacommunication

<!-- Unified metacommunication (§1-§5 as H3+ subsections) -->

### 1. Global Metacommunication Summary

> Summarize the current designer-to-user message as actually implemented in the system. **Phrasing: use "I" as the designer and "you" as the user — never third-person or passive voice (see `general/shared-definitions.md` § Phrasing rule).** Use the semiotic engineering frame: "Here is my understanding of who you are, what I've learned you want or need to do, in which preferred ways, and why. This is the system that I have therefore designed for you, and this is the way you can or should use it in order to fulfill a range of purposes that fall within this vision."

{{GLOBAL_METACOMM_SUMMARY}}

### 2. Extended Metacommunication Template Guiding Questions

1. Analysis (understanding needs and defining requirements)
   1.1. What do I know or don’t know about (all of) you and how?
   {{EMT_ANALYSIS_WHAT_I_KNOW_OR_DONT_KNOW_ABOUT_YOU_AND_HOW}}
   > For persona profiles and problem scenarios informing the current design, see `project/ux-research-results.md §1-§4`.
   1.2. What do I know or don’t know about affected others and how?
   {{EMT_ANALYSIS_WHAT_I_KNOW_OR_DONT_KNOW_ABOUT_AFFECTED_OTHERS_AND_HOW}}
   1.3. What do I know or don’t know about the intended (and other anticipated) contexts of use?
   {{EMT_ANALYSIS_WHAT_I_KNOW_OR_DONT_KNOW_ABOUT_THE_INTENDED_AND_OTHER_ANTICIPATED_CONTEXTS_OF_USE}}
   1.4. *What ethical questions can be raised by what I have learned? Why?
   {{EMT_ANALYSIS_WHAT_ETHICAL_QUESTIONS_CAN_BE_RAISED_BY_WHAT_I_HAVE_LEARNED}}
2. Design
   2.1. What have I designed for you?
   {{EMT_DESIGN_WHAT_HAVE_I_DESIGNED_FOR_YOU}}
   2.2. Which of your goals have I designed the system to support?
   {{EMT_DESIGN_WHICH_OF_YOUR_GOALS_HAVE_I_DESIGNED_THE_SYSTEM_TO_SUPPORT}}
   2.3. In what situations/contexts do I intend/accept you will use the system to achieve each goal? Why?
   {{EMT_DESIGN_IN_WHAT_SITUATIONS_CONTEXTS_DO_I_INTEND_ACCEPT_YOU_WILL_USE_THE_SYSTEM_TO_ACHIEVE_EACH_GOAL}}
   > For implemented solution representations, see Section 3 below. For visual journey maps, see `project/product-design-as-coded.md § Journey Maps`.
   2.4. How should you use the system to achieve each goal, according to my design?
   {{EMT_DESIGN_HOW_SHOULD_YOU_USE_THE_SYSTEM_TO_ACHIEVE_EACH_GOAL}}
   > For step-by-step user journeys, see `project/journey-maps.md`.
   2.5. For what purposes do I not want you to use the system?
   {{EMT_DESIGN_FOR_WHAT_PURPOSES_DO_I_NOT_WANT_YOU_TO_USE_THE_SYSTEM}}
   2.6. *What ethical principles influenced my design decisions?
   {{EMT_DESIGN_WHAT_ETHICAL_PRINCIPLES_INFLUENCED_MY_DESIGN_DECISIONS}}
   2.7. *How is the system I designed for you aligned with those ethical considerations?
   {{EMT_DESIGN_HOW_IS_THE_SYSTEM_I_DESIGNED_FOR_YOU_ALIGNED_WITH_THOSE_ETHICAL_CONSIDERATIONS}}
3. Prototyping, implementation, and formative evaluation
   3.1. How have I built the system to support my design vision?
   {{EMT_PROTOTYPING_IMPLEMENTATION_AND_FORMATIVE_EVALUATION_HOW_HAVE_I_BUILT_THE_SYSTEM_TO_SUPPORT_MY_DESIGN_VISION}}
   3.2. What have I built into the system to prevent undesirable uses and consequences?
   {{EMT_PROTOTYPING_IMPLEMENTATION_AND_FORMATIVE_EVALUATION_WHAT_HAVE_I_BUILT_INTO_THE_SYSTEM_TO_PREVENT_UNDESIRABLE_USES_AND_CONSEQUENCES}}
   3.3. What have I built into the system to help identify and remedy unanticipated negative effects?
   {{EMT_PROTOTYPING_IMPLEMENTATION_AND_FORMATIVE_EVALUATION_WHAT_HAVE_I_BUILT_INTO_THE_SYSTEM_TO_HELP_IDENTIFY_AND_REMEDY_UNANTICIPATED_NEGATIVE_EFFECTS}}
   3.4. *What ethical scenarios have I used to evaluate the system?
   {{EMT_PROTOTYPING_IMPLEMENTATION_AND_FORMATIVE_EVALUATION_WHAT_ETHICAL_SCENARIOS_HAVE_I_USED_TO_EVALUATE_THE_SYSTEM}}
4. Continuous, post-deployment evaluation and monitoring
   4.1. How much of my vision is reflected in the system’s actual use?
   {{EMT_CONTINUOUS_POST_DEPLOYMENT_EVALUATION_AND_MONITORING_HOW_MUCH_OF_MY_VISION_IS_REFLECTED_IN_THE_SYSTEMS_ACTUAL_USE}}
   4.2. What unanticipated uses have been made? By whom? Why?
   {{EMT_CONTINUOUS_POST_DEPLOYMENT_EVALUATION_AND_MONITORING_WHAT_UNANTICIPATED_USES_HAVE_BEEN_MADE_BY_WHO_WHY}}
   4.3. What anticipated and unanticipated effects have resulted from its use? Whom do they affect? Why?
   {{EMT_CONTINUOUS_POST_DEPLOYMENT_EVALUATION_AND_MONITORING_WHAT_ANTICIPATED_AND_UNANTICIPATED_EFFECTS_HAVE_RESULVED_FROM_ITS_USE_WHO_DO_THEY_AFFECT_WHY}}
   4.4. *What ethical issues need to be handled through system redesign, redevelopment, policy, or even decommissioning?
   {{EMT_CONTINUOUS_POST_DEPLOYMENT_EVALUATION_AND_MONITORING_WHAT_ETHICAL_ISSUES_NEED_TO_BE_HANDLED_THROUGH_SYSTEM_REDESIGN_REVOLUTIONARY_POLICY_OR_EVEN_DECOMMISSIONING}}

### 3. Solution Representations (Implemented)

> Solution representations that have been implemented. Mirrors the structure in `project/product-design-as-intended.md` Section 13, but reflects what is actually built. Maintained by post-skill after plan execution.

#### Option A: Solution Scenarios

##### {{SS-001}}: {{Solution Scenario Title}}

- **Persona:** {{PersonaName}} (from user research)
- **Goals:** {{G-001}}, {{G-002}} (from user research)
- **Problem Scenario:** {{PS-001}} (from user research, optional)
- **Setting:** {{where and when the user uses the system}}
- **Implementation Status:** {{implemented / partial / not started}}
- **Design Rationale:** {{optional -- why this solution approach was chosen over alternatives}}

{{2-3 paragraphs describing how the user achieves their goal with the implemented system.}}

#### Option B: User Stories

##### {{US-001}}: {{User Story Title}}

- **Story:** As {{PersonaName}}, I want to {{action}} so that {{benefit}}.
- **Goals:** {{G-001}}, {{G-002}} (from user research)
- **Problem Scenario:** {{PS-001}} (from user research, optional)
- **Implementation Status:** {{implemented / partial / not started}}
- **Acceptance Criteria:**
  - {{criterion 1}} -- {{met / not met}}
  - {{criterion 2}} -- {{met / not met}}

### 4. Per-Feature Metacommunication Log

> For each feature or interaction flow, document the designer's intent as currently implemented. **Each intent must be phrased as "I ... for you / because you ..." — see `general/shared-definitions.md` § Phrasing rule.**

| Feature / Flow | Designer Intent | Implementation Status | Source | Last Updated |
|---|---|---|---|---|
| {{feature}} | {{intent}} | {{Implemented / Partial / Planned}} | {{human / agent (metacomm) / agent (post-skill)}} | {{YYYY-MM-DD HH:MM UTC}} |

### 5. Changelog

> Versioned entries tracking how the implemented metacommunication has evolved. Each entry is appended automatically by post-skill after plan execution.

#### v1 — {{YYYY-MM-DD HH:MM UTC}}
- **Initial**: Baseline metacommunication record created
- **Source**: human (design)

---

## Journey Maps

<!-- Unified journey maps (H3+ subsections) -->

### JM-TB-001: {{Journey Title}}

- **Persona:** {{PersonaName}} (from `project/ux-research-results.md`)
- **Solution Scenario:** {{SS-001}} (from `project/product-design-as-intended.md §13`)
- **Goal:** {{what the user wants to achieve}}
- **Implementation Status:** {{implemented / partial / not started}}

#### Steps

| # | Action | Touchpoint | Implemented | Notes |
|---|--------|-----------|-------------|-------|
| 1 | {{what the user does}} | {{where they interact}} | {{yes / partial / no}} | {{implementation notes or gaps}} |
| 2 | {{action}} | {{touchpoint}} | {{yes / partial / no}} | {{notes}} |
| 3 | {{action}} | {{touchpoint}} | {{yes / partial / no}} | {{notes}} |

#### Mermaid Diagram (optional)

> Mirror the as-intended diagram structure but annotate with implementation status.

### Delta from As-Intended

> Gaps between current implementation and intended journey design (`project/product-design-as-intended.md §15 (Designed User Journeys)`).
> Updated by post-skill or manually via `/explain spec-drift`.

#### Not Yet Implemented

| Journey (JM-TB-NNN) | Step(s) | Gap Description |
|---------------------|---------|----------------|
| {{JM-TB-001}} | {{step numbers}} | {{what is missing}} |

#### Differs from Intent

| Journey (JM-TB-NNN) | Step(s) | As-Intended | As-Coded | Reason |
|---------------------|---------|-------------|----------|--------|
| {{JM-TB-001}} | {{step numbers}} | {{intended}} | {{current}} | {{why it differs}} |

### Delta from Research Findings

<!-- Populate this section when `project/ux-research-results.md §5` contains JM-E-NNN entries
     (i.e., the project has conducted formal journey research and documented it there).
     This delta compares the current implementation against empirical research findings --
     a qualitatively different signal from the as-intended delta above (research-vs-reality, not intent-vs-reality).
     Leave this section empty or omit it when no such entries are present. -->

#### Not Yet Matching Research Findings

| Journey (JM-E-NNN) | Step(s) | Research Finding | As-Coded State | Gap |
|--------------------|---------|-----------------|----------------|-----|
| {{JM-E-001}} | {{step numbers}} | {{what research showed}} | {{current behavior}} | {{gap description}} |

#### Differs from Research

| Journey (JM-E-NNN) | Step(s) | Research Finding | As-Coded | Reason |
|--------------------|---------|-----------------|----------|--------|
| {{JM-E-001}} | {{step numbers}} | {{finding}} | {{current}} | {{why it differs}} |

### Changelog

#### v1 -- {{YYYY-MM-DD HH:MM UTC}}

- **Added/Changed/Removed**: {{description}}
- **Source**: agent (post-skill)
- **Plan**: {{plan-id}}
