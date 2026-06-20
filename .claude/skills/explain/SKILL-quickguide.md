**What it does**: Get a clear explanation of how something works -- a feature's behavior, the data model, the overall architecture, how behavior evolved over time, how code works, or the drift between your design specs. Includes diagrams and analogies to make complex topics accessible. Six mode types, each producing a different kind of explanation report. The **spec-drift** mode also offers an interactive sync workflow to realign diverged specs.

**Examples**:
> `/explain architecture How does the authentication flow work?`
> Produces a visual diagram of the auth flow, explains each step in plain language, and highlights key design decisions.

> `/explain behavior What happens when a user submits a form with validation errors?`
> Explains the emergent behavior from the user's perspective, covering each path through the flow.

> `/explain behavior-evolution How has the notification system changed?`
> Explains current notification behavior AND traces how it evolved through past plans and commits.

> `/explain code src/auth/middleware.ts`
> Explains how the code works, aimed at junior developers being onboarded.

> `/explain data-model How are users and permissions related?`
> Explains the data model with entity diagrams, pitfalls, and refactoring opportunities.

> `/explain spec-drift`
> Compares as-coded and as-intended design specs. Reports entities, permissions, and UX patterns that have drifted. Asks whether you want to sync.

> `/explain spec-drift conceptual-design`
> Narrows the scan to only the conceptual-design sections of the registry.

> `/explain spec-drift metacomm`
> Narrows the scan to only the metacommunication sections.

> `/explain spec-drift --scope since-plan plan-000295`
> Scans only registry files touched by a specific plan -- useful after `/implement` to check drift introduced by that plan.

> `/explain spec-drift --promote`
> Generates Decision proposals (D-NNN entries) for items ready to be promoted from as-coded to as-intended.

> `/explain spec-drift --promote --apply-markers plan-000295`
> After you have written the Decision entries, flips the STATUS markers for items covered by the plan (Phase 3b).

**When to use**: You want to understand how a part of the system works, need to onboard yourself on unfamiliar code, want a visual overview of the architecture, or want to see and resolve the gap between as-coded and as-intended design specs. In its general modes (architecture, behavior, code, data-model, behavior-evolution) it most often hands off to `/research` for follow-up questions. In `spec-drift` mode it has a recurring post-`/reflect` role -- after each cycle closes, run `/explain spec-drift` to detect divergence.

**Not for**: generating artifacts someone else will read (use `/document`, `/communicate`, or `/onboard`); `/explain` answers *your* questions about the system. See `docs/how-to/which-communicative-skill.md` for the audience routing table.

**Next step**:
- After general modes (architecture, behavior, etc.): `/research` to follow up with deeper questions.
- After `spec-drift`: `/plan` to address the drift, `/design` if intent has evolved, or `/pending` to address pending actions surfaced by the check.
- After `spec-drift --promote`: `--apply-markers plan-<id>` to flip STATUS markers once you have written the Decision entries.

**See also**: `/document` -- generate project documentation artifacts (READMEs, changelogs, API references, ADRs).
