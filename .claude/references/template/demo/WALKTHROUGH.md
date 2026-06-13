---
designer_description: "I'm the demo walkthrough /seja-setup --demo writes into your scratch project -- a step-by-step tour of /research, /plan, /implement, and /check against the pre-filled TaskFlow design files, so you can exercise the core SEJA loop on a working example before pointing the harness at your own project."
---

# TaskFlow Demo Walkthrough

This walkthrough guides you through the core SEJA skills using the pre-configured TaskFlow demo project. Each section builds on the previous one, so follow them in order.

---

## 1. Orientation

You are working in a project that has been set up with the SEJA harness and pre-filled with demo design files. The key files are:

- `product-design/conventions.md` -- project identity and directory layout
- `product-design/constitution.md` -- immutable quality principles
- `product-design/product-design-as-intended.md` -- the domain model (Task and Category entities) and designer-to-user communication intentions

Browse these files now to see what a configured SEJA project looks like.

> **What to expect:** You will see completed design files instead of placeholder templates. Every `{{variable}}` has been filled in with values for a simple task management app.

---

## 2. /research demo

Ask the harness a design question:

```
/research What state management approach fits this project?
```

The agent reads your conventions (React, no external state library) and constitution (simplicity principle) before answering. Try a follow-up:

```
/research Should we add drag-and-drop reordering to tasks?
```

> **What to expect:** Answers grounded in your project context, not generic advice. The agent cites specific principles from your constitution and design files. Each Q&A pair is logged in `_output/advisory-logs/`.

---

## 3. /plan demo

Generate a development plan for the first feature:

```
/plan Add the Task entity with create, toggle, and delete operations
```

The agent produces a numbered plan with steps, file paths, and rationale tied to your conceptual design.

For a lighter alternative, try:

```
/plan --light Add a color picker to the category edit form
```

> **What to expect:** A structured plan file in `_output/plans/` with clear steps, each referencing entities and validation constants from your conceptual design. The `--light` variant produces a shorter proposal in `_output/proposals/`.

---

## 4. /implement demo

Execute the plan you just created:

```
/implement 000001
```

The agent reads the plan, implements each step, and reports progress. It follows the constitution (semantic HTML, keyboard navigation, test coverage) while writing code.

> **What to expect:** Working code that matches the plan. The agent creates components, tests, and constants files. It commits after completing the plan and logs a brief in `_output/briefs.md`.

---

## 5. /check validation demo

Run the harness health check to verify everything is wired correctly:

```
/check health
```

Then run a code review on the files you just generated:

```
/check review
```

> **What to expect:** The health check confirms that conventions, constitution, and design files are present and consistent. The code review evaluates the generated code against your constitution's quality principles (test coverage, accessibility, no magic numbers).

---

## Next Steps

- Run `/help` to see all available skills
- Run `/design` to modify the project configuration
- Run `/explain spec-drift` to compare as-coded vs. as-intended design files
- Edit the design files directly and re-run `/check validate` to see how the harness detects changes
