**What it does**: Shows what skills are available and explains what each one does. Three layers of progressive disclosure: no-args overview grouped by workflow category, per-skill detail cards, and an interactive category browser with a Mermaid skill-graph visualization.

- **Layer 1 -- Overview (no args)**: Lists all user-facing skills grouped into categories (Getting started, Design & plan, Understand the system, Quality & review, Communicate, Housekeeping) with one-sentence summaries. Presents options to drill into a specific skill or browse interactively.
- **Layer 2 -- Skill detail (`/help <skill>`)**: Loads the skill's Quick Guide (What / Example / When to use / Next step), its Arguments table, category, and related skills from the skill graph.
- **Layer 3 -- Interactive browse (`/help --browse`)**: Groups all skills by `metadata.category`, shows category counts, renders a Mermaid skill-relationship diagram, and walks you through picking a category, then a skill, then executing it.

**Examples**:
> `/help`
> Shows an overview of all skills organised by workflow category, then asks which skill or category you'd like to explore.

> `/help research`
> Displays what `/research` does (guide, examples, when to use), its arguments, category, and related skills from the skill graph.

> `/help --browse`
> Shows skill categories with counts, renders the Mermaid skill-relationship graph, and walks you through picking a category, then a skill to run.

**When to use**: You want to know what the harness can do, need details about a specific skill before running it, or want to browse the full catalogue interactively and launch a skill from the menu.

**Not for**: Execution -- `/help` explains and navigates; it does not perform the work itself. Once you know which skill to run, invoke it directly.

**Next step**: `/help --browse` to walk the full skill catalogue by category, then the quick-reference workflow sections in `docs/how-to/plan-and-execute.md`.
