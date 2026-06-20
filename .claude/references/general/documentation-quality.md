---
designer_description: "When you write or review project documentation, I'm the reference that defines what good looks like -- accuracy, completeness within declared scope, consistency, scannability, and maintainability -- paired with the writing principles (imperative mood, concrete verbs, task-first structure) that the documentation templates and the /check docs validator both rely on."
---

# FRAMEWORK -- DOCUMENTATION QUALITY GUIDE

> Canonical writing standards for all documentation in SEJA projects. Referenced by documentation templates in `template/docs/` and validated by `check_docs.py`.

## Quality Attributes

Five measurable attributes of documentation quality:

### 1. Accuracy
Docs match current behavior; when the system changes, docs change in the same release. Stale docs actively mislead.

### 2. Completeness Within Declared Scope
Every page declares its scope; within it, no gaps. An API reference listing 8 of 12 endpoints is worse than none -- readers trust the incomplete list. Document everything in scope, or explicitly state what is excluded and why.

### 3. Consistency
Uniform terminology, formatting, and structure (see `general/shared-definitions.md`): same term for same concept; same heading hierarchy, table format, and callout style.

### 4. Scannability
Users find answers in under 30 seconds via descriptive headings (not "Overview"), tables for structured data, bold lead-ins for list items, short paragraphs (3-5 sentences), and code blocks for commands/examples.

### 5. Maintainability
Updates possible without heroic effort, via automated validation (path liveness, terminology, structural completeness), per-type freshness policies (template frontmatter), single source of truth (reference, don't duplicate), and template-based structure.

---

## Writing Principles

Five rules for documentation content:

### 1. Imperative Mood for Steps
Write steps as commands: "Click Save" not "The user should click Save." Shorter, clearer, translates better.

### 2. Bold Lead-ins for List Items
In how-to content, start each item with a bold phrase summarizing the action:
- **Create the file** -- run `touch config.yml` in the project root
- **Add the key** -- open the file and add `api_key: YOUR_KEY`

### 3. Expected Outcomes Alongside Actions
After every action step, state what the user should see:
- "Click Save -- the confirmation toast appears in the top-right"
- "Run `npm test` -- all tests pass with 0 failures"

### 4. Two Callout Types Only
Limit callouts to two types to prevent fatigue: **Tip** (helpful shortcuts/best practices) and **Warning** (actions that cannot be undone or have significant consequences). Do not use Note, Info, Important, Caution, or Danger -- distinctions lost on readers.

### 5. Write for Global Audience
All docs must be translatable:
- Simple sentence structures (subject-verb-object)
- No idioms ("out of the box", "under the hood")
- No cultural references or humor
- Avoid contractions in formal docs ("do not" over "don't")
- Standard date format (YYYY-MM-DD) not locale-specific

---

## Diataxis Framework

Every page belongs to exactly one of four types. If a page serves two purposes, split it.

| Type | Purpose | Tone | Structure |
|------|---------|------|-----------|
| **Tutorial** | Learning-oriented | "Follow along with me" | Numbered steps with guaranteed outcome |
| **How-to** | Task-oriented | "Do this to achieve X" | Steps with decision points and alternatives |
| **Reference** | Information-oriented | "Here are the facts" | Tables, lists, exhaustive and dry |
| **Explanation** | Understanding-oriented | "Here is why" | Narrative prose, context, trade-offs |

Each template declares its type in YAML frontmatter (`diataxis: tutorial | how-to | reference | explanation`).

---

## Progressive Disclosure

Most-needed info first; deeper detail available without forcing users through it.

- **Page level**: core content before edge cases. The 3-question contextual help pattern (What / How / Verify) is primary; constraints, failure modes, and impact are secondary.
- **Section level**: one-sentence summary before details, then expand.
- **Doc-set level**: getting-started before architecture deep-dives; README links to a recommended reading order.
