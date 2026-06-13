**What it does**: Configures design intent for your project. Six modes cover every design lifecycle stage: interactive questionnaire (default), from a pre-filled spec file, adding documentation templates, generating a blank spec, interview-driven conversation, and updating existing design sections. After `/seja-setup` populates `conventions.md` with stack definitions, `/design` generates the remaining design-intent artifacts (product-design-as-intended, ux-research-results, standards, design-standards, security-checklists, constitution) and amends CLAUDE.md.

**Examples**:
> `/design`
> Post-`/seja-setup` (partial-design state): detects that conventions.md exists but design intent is absent. Skips Section 1 (stack already answered), walks through Sections 0 (metacomm) and 2-5+ (conceptual-design, UX/visual design, standards, docs).

> `/design` (when project already configured)
> Shows current design summary and offers an interactive menu to update specific sections.

> `/design specs/my-project.md`
> Reads a pre-filled spec file and generates all design artifacts from it without interactive prompts (Mode 2).

> `/design --generate-spec`
> Outputs a blank spec skeleton you can fill out offline and feed back via Mode 2 (Mode 4).

> `/design --add-docs`
> Adds documentation templates to an already-configured project (Mode 3).

> `/design --mode interview`
> Open-ended conversation that builds design intent through questions, then synthesizes structured outputs. Best when you haven't pre-formalized your idea (Mode 5).

> `/design update conceptual`
> Jumps directly to the conceptual-design section update dialog, skipping the interactive menu.

**When to use**: After `/seja-setup` to define design intent for a new project. Anytime you want to update your project's design foundations (stack, domain model, standards, metacommunication). Use `/design update <section-slug>` (valid slugs: `stack`, `conceptual`, `metacomm`, `backend-standards`, `frontend-standards`, `ux-standards`, `ui-standards`, `i18n`, `security`, `testing`, `constitution`, `full`) to jump straight to a specific section. Use Mode 5 (`--mode interview`) when you want to think out loud rather than fill a form; use Mode 1 (default) when you know your stack and want speed.

**Not for**: topology scaffolding (use `/seja-setup`), planning implementation (use `/plan`), or checking drift between intent and code (use `/explain spec-drift`).

**Next step**: `/plan --roadmap` to generate a development roadmap from the new design, or `/plan` to plan your first feature.
