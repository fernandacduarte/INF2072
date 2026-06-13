**What it does**: Generates tailored communication material for a specific audience segment. Each audience gets content in their language, focused on what matters to them.

| Audience | Aliases | Focus |
|----------|---------|-------|
| Evaluators | `evaluator`, `evaluators`, `EVL` | Technical depth, architecture decisions, quality evidence |
| Clients | `client`, `clients`, `CLT` | Value proposition, ROI, project outcomes |
| End Users | `end-user`, `end-users`, `USR` | Features, benefits, how-to guidance |
| Academics | `academic`, `academics`, `ACD` | Research context, methodology, theoretical framing |

**Examples**:
> `/communicate clients`
> Reads your project's design vision and produces client-oriented material highlighting value proposition, ROI, and project outcomes. Generates both Markdown and HTML by default.

> `/communicate ACD`
> Same as above, using the short alias for the academic audience.

> `/communicate --all`
> Generates material for all 4 audience segments in parallel, each in its own subagent.

> `/communicate evaluators --format md`
> Produces evaluator material in Markdown only (skips HTML generation).

> `/communicate USR --source _output/advisory-logs/advisory-000100.md`
> Reformats an existing advisory log as end-user-facing material.

> `/communicate clients --deep`
> Includes Deep-dive content sections with expanded technical detail for the client audience.

> `/communicate --all --format html --deep`
> Batch generation for all audiences, HTML only, with Deep-dive sections.

**When to use**: You need to present the project to a specific audience -- evaluators, clients, end users, or academics -- and want material that speaks their language.

**Not for**: new team-member onboarding (use `/onboard`) or project documentation (use `/document`). See `docs/how-to/which-communicative-skill.md` for the audience routing table.

**Next step**: `/onboard` -- need to onboard someone to the project as well?

**References**: Audience templates (`evaluators`, `clients`, `end-users`, `academics`) and the Diataxis mapping live in [.claude/references/general/communication/](../../../.claude/references/general/communication/). Edit those files to update per-audience tone, sections, or content strategy.

**Terminology note**: Output artifacts retain the `communication-NNN` prefix and live in `_output/communication/` for ID and link continuity.
