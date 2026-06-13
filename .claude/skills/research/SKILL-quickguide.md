**What it does**: Ask any question about the project -- architecture, design decisions, trade-offs. The agent researches your codebase, analyzes from multiple perspectives, and gives you actionable recommendations at HIGH/MEDIUM/LOW priority. Two modes: **research** (default, question-driven) and **inventory** (`--inventory`, codebase element catalog).

In research mode, the agent produces a structured report with perspective analysis and recommendations. If it detects design decisions in the Q&A, it offers a decision-extract proposal flow: create a structured D-NNN entry now, defer to the pending ledger, or skip. Tags (2-5 topic tags) are derived automatically. Follow-up Q&A continues within the same session.

In inventory mode, it scans the codebase and produces a structured catalog of all elements matching a pattern (e.g., all API endpoints, all form components, all database models).

**Examples**:
> `/research Should we use a modal or a full page for the new settings flow?`
> Researches the codebase, evaluates from UX, accessibility, and architecture perspectives, and provides a recommendation with pros and cons. Asks if you have follow-up questions.

> `/research --deep Should we migrate from REST to GraphQL?`
> Activates a structured expert council debate with 5-7 named archetypes for a high-stakes decision. Produces position statements, cross-examination, and a synthesis.

> `/research --inventory List all API endpoints and their HTTP methods`
> Scans the codebase and produces a structured inventory of all API endpoints.

**When to use**: You need guidance on a design decision, want to understand trade-offs, or are unsure about the best approach. Use `--inventory` when you need an overview of what exists in the codebase. Use `--deep` for high-stakes decisions that benefit from structured multi-perspective debate. From iteration 2 onward, `/research` is the usual lifecycle entry: you ask your question here, and depending on what surfaces you move into `/design` (when intent needs to change) or `/plan` (when intent is set and you need a build plan).

**Next step**: `/plan` to turn recommendations into an actionable build plan, `/plan --roadmap` for a full product roadmap, or `/design` when research surfaces that intent must change first. After `--inventory`: `/explain` for a deeper explanation of any item.

**Terminology note**: New output artifacts use the `research-<id>-*.md` filename pattern in `_output/research-logs/`; historical `advisory-<id>-*.md` files in `_output/advisory-logs/` are preserved in place per the artifact-immutability rule. Read-path scripts scan both folders.
