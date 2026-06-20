**What it does**: Saves the current conversation (questions and answers) to a file for future reference. Standalone mode writes to `_output/qa-logs/` with a reserved ID and slug-based filename (`qa-<id>-<slug>.md`). Post-skill also uses this skill in companion mode to produce collocated QA logs next to the parent artifact.

**Examples**:
> `/qa-log`
> Captures the full Q&A exchange from this session, derives a title from the conversation topic, and saves it as a timestamped file.

> `/qa-log Design decisions for the notification system`
> Same as above, using the provided text as the log title.

**When to use**: You have had a productive conversation with useful decisions or insights and want to preserve it as project documentation.

**Next step**: `/research` -- have more questions to explore after capturing the current session?
