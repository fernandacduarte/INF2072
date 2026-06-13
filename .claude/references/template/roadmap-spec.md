---
designer_description: "I'm your project's roadmap spec -- vision, horizon, strategic themes, and work items sized and classified as design or technical with dependency links between them -- so when /plan --roadmap reads me, it can turn one coherent delivery picture into a set of plans you can execute in parallel where the dependency graph allows."
---

<!-- Roadmap Spec v1 -- Generated {datetime} -->
<!-- Fill in your choices below. Delete sections that don't apply. -->
<!-- After filling, run /plan --roadmap --from-spec <this-file> to generate plans. -->
<!-- Independent items can then be executed in parallel via the implement skill. -->

## Product Vision
<!-- 1-3 sentences: where is the product heading? What user problem are you solving next? -->

## Roadmap Horizon
<!-- Timeframe this roadmap covers. Examples: "Q2 2026", "Next 4 weeks", "March-April 2026". -->
- horizon:

## Themes
<!-- Group work items under strategic themes. Each theme is a high-level goal.
     Mark priority: P0 (must-have), P1 (should-have), P2 (nice-to-have). -->

### Theme: {Theme Name}
<!-- Brief description of why this theme matters. -->
- priority: P0 | P1 | P2

#### Work Items
<!-- Each work item becomes one plan. Keep scope small enough for a single planning step.
     Fields:
     - id: short unique slug (e.g., "viewed-tracking", "export-pdf")
     - title: one-line description
     - scope: backend | frontend | fullstack | infra | docs
     - size: S (< 5 files) | M (5-15 files) | L (15+ files)
     - depends_on: list of item ids this depends on, or "none"
     - type: optional override for automatic classification.
             "technical" -> planned via the plan skill (implementation-first)
             "design" -> planned via the metacomm skill (metacommunication framing, UX-first)
             If omitted, the plan --roadmap mode classifies automatically based on whether
             the item's primary concern is user-facing (design) or internal (technical).
     - description: 2-5 sentences of what needs to happen
-->

- id:
  title:
  scope:
  size:
  type:
  depends_on: none
  description: >

- id:
  title:
  scope:
  size:
  type:
  depends_on: none
  description: >

### Theme: {Theme Name}
- priority: P1

#### Work Items

- id:
  title:
  scope:
  size:
  type:
  depends_on: none
  description: >

## Constraints
<!-- Cross-cutting constraints that apply to all items. Examples:
     - "No breaking API changes — mobile client v2.1 is in production"
     - "All new endpoints need integration tests"
     - "Must maintain backwards compat with existing exports" -->

## Parallel Execution Strategy
<!-- After generating plans, use this section to identify execution waves.
     Wave = set of items with no mutual dependencies that can run in parallel.

     Example:
     - Wave 1: viewed-tracking, export-pdf, i18n-cleanup (all independent)
     - Wave 2: notification-system (depends on viewed-tracking)
     - Wave 3: analytics-dashboard (depends on notification-system)

     For parallel execution, use one of:
     - Multiple agent terminal sessions, each running the implement skill on a different plan
     - Worktree-isolated agents from a single session (safest, auto-branches)
-->

### Wave 1 (independent)
-
-
-

### Wave 2 (depends on Wave 1)
-
-
