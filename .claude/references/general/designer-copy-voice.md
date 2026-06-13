---
name: designer-copy-voice
description: "Authoring rubric for designer_description: keys and # designer: blocks surfaced by the call-graph viewer's side panel."
designer_description: "When you write a node's side-panel paragraph -- an agent, a rule, a reference file, or a script -- I'm the rubric that keeps your voice, encoding, and scope consistent, so the whole viewer reads as one harness speaking to you rather than a patchwork of module docstrings and H1 leads."
---

> Rationale / historical context: see `designer-copy-voice-rationale.md` in this directory.

# Designer Copy -- Voice and Encoding Rubric

This file is the authoring guide for every node that enters the call-graph. The call-graph viewer's right-hand panel renders whatever this rubric produces verbatim.

## Voice

- **Speak in first person.** "I", not "the script". The viewer is the harness addressing you directly; third-person prose breaks that illusion.
- **Address the user as "you".** Not "the user", not "the contributor". "You" is who the viewer is for.
- **Start with context, not mechanics.** Open with "When you ..." or "After ..." or "Before ...". Avoid "This script reads ..." / "This file contains ...".
- **Describe outcomes.** What you get back, not what I do internally. "You see a list of failures" beats "I iterate over the check registry and print JSON."
- **Avoid tool names when a designer-level noun exists.** Prefer "the health check" over "run_all_checks.py"; prefer "the onboarding template" over "onboarding/bld-l1.md". Tool names are fine when the user would recognize them from the CLI (e.g., "/plan", "/implement").
- **One paragraph by default.** Block form is reserved for nodes whose side panel genuinely benefits from structure -- two paragraphs, a short list, a scenario split. Most nodes do not need this.

## Encoding

### Markdown files (agents, rules, general refs, template refs, project refs)

Add a `designer_description:` key to the YAML frontmatter.

Inline form -- one paragraph, quoted:

```yaml
---
name: code-reviewer
description: Reviews code changes against engineering perspectives.
designer_description: "When you finish implementing a feature, I walk your diff through seven review lenses -- security, accessibility, architecture, testability, performance, compatibility, operations -- and tell you which findings would block a release, which are nice-to-have, and which don't apply here."
---
```

Block form -- multi-paragraph or list:

```yaml
---
name: code-reviewer
designer_description: |
  When you finish implementing a feature, I step in and check it from
  seven angles -- security, accessibility, architecture, testability,
  performance, compatibility, and operations.

  I call out the findings that would block a release, flag the ones
  that are nice-to-have, and stay quiet on the ones that don't apply.
---
```

Place the key in the existing frontmatter block. If no frontmatter exists on a `.md` file under the targeted directories, add one at the very top (`---` fences) containing at minimum `designer_description: ...`.

### Python files (scripts)

Add a `# designer:` top-of-file comment block immediately after the shebang (if any) and before the module docstring. Use `#` on every continuation line.

```python
#!/usr/bin/env python3
# designer: When you run the harness's health check, I walk through
#   every registered validation script and tell you which ones pass,
#   fail, or need attention -- in plain language, not error codes.
"""run_all_checks.py -- CI-independent validation orchestrator..."""
```

Alternative form for IDE-friendly editing -- a module-level variable. The extractor accepts either; the variable form is preferable when you expect the designer copy to be edited repeatedly in a code editor.

```python
"""run_all_checks.py -- CI-independent validation orchestrator..."""

__designer_description__ = (
    "When you run the harness's health check, I walk through every "
    "registered validation script and tell you which ones pass, fail, "
    "or need attention -- in plain language, not error codes."
)
```

### Non-applicable file types

`.yaml` and `.json` files under `.claude/references/template/` are out of scope for this rubric.

## Encoding conformance

The authored prose must be **ASCII-only** at the paragraph level. The governing rule lives in `.claude/references/general/report-conventions.md` § Character Restrictions.

Forbidden code points when authoring designer copy:

- `U+2014` em-dash (`—`) -- use `--` (double-hyphen) or `-` (hyphen) instead.
- `U+2013` en-dash (`–`) -- use `-` or `--` instead.
- `U+2018` / `U+2019` curly single quotes (`‘` `’`) -- use straight apostrophe `'`.
- `U+201C` / `U+201D` curly double quotes (`“` `”`) -- use straight double-quote `"`.

LLM-drafted prose introduces these substitutions silently. Before committing, grep the newly-authored block for any of the five code points above and fix any hit.

## Priv-only awareness

Designer copy under `.claude/` and `product-design/` propagates to `seja-public/` at the next release sync (`tools/sync_to_public.py`). The existing `check_no_private_leaks.py` catches raw filename and directory references but does not read content semantics, so designer prose is a channel that can leak priv-only information if you are not deliberate.

Describe only the **public-facing surface** of a node. If a script or skill carries a priv-only flag (e.g., a flag wrapped in the `priv-only-start` / `priv-only-end` HTML-comment markers), a priv-only mode, or a capability gated behind the `scripts/priv/` directory, describe the public behaviour and omit the private capability. Cross-reference: `.claude/references/general/harness-governance.md` § Private-Only Content Convention.

Edge cases to avoid in designer copy:
- Naming a priv-only flag by its CLI form.
- Describing the harness-development-only side of a node whose consumer-facing surface is different.
- Referring to priv-only directories (`scripts/priv/`) by path.

If a node genuinely has *only* priv-only behaviour, it should not have a designer description in the public-visible frontmatter; leave the developer fallback in place or wrap the block in priv-only markers (advanced; not required for this backfill).

## Template-instantiation voice

Template files under `.claude/references/template/*.md` (and their nested subdirectories) are copied verbatim into consumer projects by `/seja-setup --workspace`, `/design`, and `create_workspace.py`. The template's `designer_description:` frontmatter lands in the consumer's instantiated project file, which then renders in their own call-graph viewer.

When authoring a template's designer copy:

- Write for the **consumer who will inherit the instantiated file**, not the harness contributor reading the template in-place.
- Use second-person "you" as the instantiating-project designer, not as a template author.
- Avoid phrases like "this template", "when you customize this template", or "the harness ships this as a starting point" -- those read awkwardly once the file is a concrete project file.
- Describe what the file will mean in the consumer's own project (e.g., "I describe your project's backend conventions ..."), not what the template slot represents.

Example -- acceptable template designer copy:

```yaml
designer_description: "I list the backend conventions your project follows -- framework, dependency injection pattern, error handling style, naming, test layout -- so every backend PR you open can be reviewed against one agreed baseline."
```

Example -- awkward template designer copy (do not use):

```yaml
designer_description: "When you customise this template, I become your project's backend standards document."
```

The difference: the first reads as the instantiated file speaking to the consumer; the second reads as meta-commentary about the template system.

## Idempotence

If a file already has a non-empty `designer_description:` or `# designer:` block, leave it alone **unless** the existing text violates this rubric. Known exception cases that warrant rewriting:

- The block is empty or a placeholder (`"TODO"`, `"Designer copy here"`, `""`).
- The block is written in third person or passive voice (breaks the Voice rules above).
- The block contains forbidden typographic characters (em-dash, en-dash, curly quotes).
- The block references priv-only surfaces that should not ship to the public mirror.
- The block is a verbatim paste of the developer-fallback prose (module docstring or H1 + lead) with no voice shift.
