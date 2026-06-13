---
designer_description: "When you run /onboard for a shaper -- a product manager, UX or UI designer, researcher, or analyst joining your team -- I'm the role layer the onboarding-generator combines with the new hire's level to shape their plan into the intent-facing essentials: the conceptual design and metacommunication record, personas and journey maps, the design system, the roadmap, and the AI tooling they will use to explore the codebase without having to read code directly."
---

# SHP — Shapers

> Product managers, UX/UI designers, data analysts, and others who define what gets built and how.

## Roles

- Product management (Product manager / Product owner)
- Design (UX designer, UI designer, Content strategist)
- Research & analytics (UX researcher, Data/Business analyst)

## Layer 1 — Role-Specific Onboarding Content

### Essential (all Shapers must cover)

- **Conceptual design and metacommunication**: As-coded state and design intent (`project/product-design-as-coded.md` `## Conceptual Design` + `## Metacommunication`, `project/product-design-as-intended.md`). Entity model, roles, permissions, interaction patterns, and designer intent -- who the user is and why the system works this way.
- **User personas and journey maps**: Who uses the system, their goals, and how they move through key workflows.
- **Design system and component library**: Visual language, tokens, reusable components, interaction patterns.
- **Product roadmap and priorities**: Current/upcoming work, strategic goals, prioritization. Use `/plan --roadmap` output if available.
- **AI-assisted design workflow**: Using AI tools (e.g. Claude Code with the skill system) to explore the codebase, validate design decisions, and generate explanations without reading code directly.

### Deep-dive (load for thorough onboarding or when Shaper is the primary role)

- **Analytics and metrics**: KPIs, tracking, and dashboards for user behavior.
- **User research findings**: Usability studies, surveys, support ticket patterns, A/B outcomes.
- **Accessibility requirements**: WCAG level, assistive tech support, review process.
- **Internationalization**: Supported locales, translation workflow, cultural considerations.
- **Competitive landscape**: Product positioning, key differentiators, known gaps.
- **Stakeholder map**: Decision influencers, approval workflows, escalation paths.

## Recommended First Tasks by Level

| Level | First Task | Goal |
|-------|-----------|------|
| L1 Contributor | Conduct a heuristic evaluation (newcomer) or write a feature brief (practitioner) | Learn the product through a critical lens |
| L2 Expert | Review and critique the conceptual design document | Understand design intent, propose refinements |
| L3 Leader | Map cross-feature dependencies (Strategist) or lead a design review session (Manager) | Identify systemic design issues or understand team norms |

## Key Reference Files

- `project/product-design-as-coded.md § Conceptual Design` (current system design)
- `project/product-design-as-intended.md` (unified working intent, Decisions log, and metacommunication; Human (markers) classification since SEJA 2.8.3)
- `project/product-design-as-coded.md § Metacommunication` (current metacommunication record)
- `general/shared-definitions.md` (project terminology)
- `general/review-perspectives/ux.md` (UX review standards)
- `general/review-perspectives/a11y.md` (accessibility standards)
- `general/review-perspectives/vis.md` (visual design standards)
