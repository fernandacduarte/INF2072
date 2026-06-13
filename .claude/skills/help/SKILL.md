---
name: help
description: "Show contextual help, browse skills by category, or get details on a specific skill."
argument-hint: "[skill-name | --browse]"
compatibility: "Designed for Claude Code with the SEJA harness"
metadata:
  last-updated: 2026-03-29 00:15 UTC
  version: 1.0.0
  category: utility
  context_budget: light
  references: []
---

> Overview: see [./SKILL-quickguide.md](./SKILL-quickguide.md)

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `[skill-name]` | No | Show full details for a specific skill (Quick Guide, arguments, category, related skills) |
| `--browse` | No | Interactive category browser with skill graph. Lets you pick a category, then a skill to run |

# Help

## Skill-specific Instructions

This skill provides three layers of progressive disclosure depending on the arguments provided.

### Layer 1: No argument — Overview

When invoked without arguments (`/help`), display a curated overview of all user-facing skills organized by designer workflow. Present the categories to the user and let them pick one to explore further.

**Categories and skills:**

- **Getting started** — `/seja-setup`, `/design`, `/help`
- **Design & plan** — `/research`, `/plan`, `/implement`
- **Understand the system** — `/explain`
- **Quality & review** — `/check`
- **Communicate** — `/communicate`, `/onboard`
- **Housekeeping** — `/qa-log`

For each category, show the skill names and a one-sentence summary. After the overview, show available options and then ask the user what they'd like to explore:

**Options:**
- `/help <skill>` — Full details for a specific skill (guide, arguments, related skills)
- `/help --browse` — Interactive category browser with skill graph

### Layer 2: With skill name — Full details

When invoked with a skill name (`/help research`):

1. Read `.claude/skills/<skill-name>/SKILL-quickguide.md` and display its full body (What / Example / When to use / Next step; YAML frontmatter stripped, if any). If the sibling file does not exist, fall back to the `description` field from `.claude/skills/<skill-name>/SKILL.md`'s YAML frontmatter.
2. Additionally show:
   - **Arguments**: Extract and display the `## Arguments` section from the skill's SKILL.md (everything between `## Arguments` and the next heading). If no `## Arguments` section exists, fall back to displaying the `argument-hint` field from frontmatter.
   - **Category**: The skill's `metadata.category` value.
   - **Related skills**: Look up the skill in `.claude/references/general/skill-graph.md` and show which skills are suggested after this one, and which skills suggest this one as a follow-up.
3. After displaying, ask: "Ready to use this skill? Just type the command."

### Layer 3: With --browse flag — Interactive Browse

When invoked with `--browse` (`/help --browse`), or when the user says "pick prompt", "pick skill", or "prompt menu":

1. Scan the `.claude/skills/` directory for all subdirectories containing a `SKILL.md` file. For each, read the `name` and `description` fields from the YAML frontmatter. Exclude internal lifecycle hooks (`pre-skill`, `post-skill`) from the menu. If a SKILL.md cannot be parsed, log a warning and skip it.

2. Group the discovered skills by their `metadata.category` field:

   | Category value | Display label |
   |---------------|---------------|
   | `planning` | Planning & Execution |
   | `analysis` | Analysis & Review |
   | `code` | Code & Tests |
   | `utility` | Utilities |

   Exclude skills with `category: internal` from the menu. If a skill has no `category` field, place it in **Utilities** as a fallback.

3. If an argument is provided (other than `--browse`), attempt to match it to one of the available skills. If you find up to 4 matches, present the options to the user and let them choose what to execute.

4. Otherwise, show ONE question with the category options (with a count of skills in each). Then show the skills in the chosen category with their descriptions.

5. After the user picks a specific skill, ask what arguments to pass (if the skill has an `argument-hint`), then execute the corresponding skill command.

6. **Skill Relationships** -- After showing categories (step 4) and before the user picks a skill, include a "Skill Relationships" section. Display the contents of `.claude/references/general/skill-map.mmd` inside a Mermaid code block so the user can visualize how skills connect. If the file does not exist, skip this section silently.

   Format:

   **Skill Relationships**

   ```mermaid
   <contents of .claude/references/general/skill-map.mmd>
   ```

   > To regenerate: `python .claude/skills/help/generate_skill_map.py`
