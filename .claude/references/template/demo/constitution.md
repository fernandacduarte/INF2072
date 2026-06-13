---
designer_description: "I'm the demo constitution /seja-setup --demo writes into your scratch project -- a pre-filled set of immutable technical and quality principles for a React-plus-localStorage task app, so you can see what a constitution with real content looks like before you author your own."
---

# PROJECT CONSTITUTION -- TaskFlow Demo

> Immutable principles for the TaskFlow demo project.

---

## Project Identity

TaskFlow -- A minimal task management app that helps individuals organize work into categorized lists.

Designed for solo users who want a clean, accessible interface without account setup overhead.

---

## Technical Principles

| # | Principle | Rationale |
|---|-----------|-----------|
| T1 | All state lives in React context with no external state library. | Keeps the demo simple and dependency-light. |
| T2 | Components use semantic HTML elements before reaching for ARIA roles. | Native elements provide built-in accessibility and reduce code. |
| T3 | No runtime CSS-in-JS -- use CSS Modules or plain CSS. | Avoids bundle bloat and keeps styling predictable. |

---

## Quality Principles

| # | Principle | Rationale |
|---|-----------|-----------|
| Q1 | Every component must have at least one unit test covering its primary interaction. | Regression prevention is non-negotiable even for a demo. |
| Q2 | All interactive elements must be keyboard-navigable and meet WCAG 2.1 AA contrast. | Accessibility is a core project value, not an afterthought. |
| Q3 | No hardcoded magic numbers -- validation limits come from a shared constants file. | Single source of truth prevents frontend/backend drift. |

---

## Enforcement

- These principles are loaded into every agent context via pre-skill.
- `/check validate` verifies conformance against the agent-facing constraints.
- Violations discovered during review or preflight are classified as **blocking**.

---

## Changelog

### v1 -- 2026-03-31
- Initial constitution created for TaskFlow demo.
