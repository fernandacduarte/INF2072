---
recommended: true
depends_on: [all]
freshness: every-release
diataxis: how-to
description: "Contextual help content model with 3-question pattern per screen, i18n support, and callout conventions."
designer_description: "When /document generates the per-screen contextual help that lives next to your UI, I'm the template that shapes each page around the 3-question pattern (what can I do here, how should I go about it, how will I know I succeeded) or the expanded 6-section variant for mature products, using your plan's Docs: fields, the screen the change lands on, and your project's locales, so the help your users pop open mid-task answers their actual in-the-moment question instead of dumping feature reference at them."
---

# TEMPLATE -- CONTEXTUAL HELP CONTENT MODEL

> **How to use this template:** Create a `help/` subdirectory under your user-facing docs folder. For each UI screen that needs contextual help, create one file following the pattern below. If your app supports multiple locales, mirror the structure per locale (e.g., `user_docs/en-US/help/`, `user_docs/pt-BR/help/`).

## File Organization

| Path | Purpose |
|------|---------|
| `{{USER_DOCS_DIR}}/{locale}/help/` | One help page per UI screen |
| `{{USER_DOCS_DIR}}/{locale}/help/styles.css` | Contextual help stylesheet (separate from main docs) |

## Canonical 3-Question Pattern

Every contextual help page follows this structure:

### Section 1: What can I do here?

Describe the purpose of the screen and the actions available. Use short bullet points. Focus on capabilities, not implementation.

### Section 2: How should I go about doing it?

Step-by-step guidance for the primary tasks on this screen. Number the steps. Include expected outcomes after each action.

### Section 3: How will I know if I succeeded?

Describe the visual or functional confirmation the user will see. Include success states, expected changes, and where to find the result.

## Expanded 6-Section Pattern (Mature Products)

As your product matures, expand each contextual help page from 3 to 6 sections. The 3 additional sections address safety and collaboration concerns that become important as user workflows grow more complex.

### Section 4: What are the constraints on my actions?

Describe permission requirements, size limits, format restrictions, and other boundaries. Users should understand what they cannot do before they attempt it.

### Section 5: What can go wrong?

Document common failure modes, error messages, and recovery steps. Focus on the failures users actually encounter, not every theoretical edge case.

### Section 6: How does this affect others?

Explain cascading effects: who gets notified, what changes for other users, what is visible to collaborators or administrators.

### Progressive Disclosure

Present the 3 core sections (What / How / Verify) as the primary content. The 3 expanded sections (Constraints / Failures / Impact) should be visually secondary:
- Below the fold in longer pages
- In a collapsible "More details" section
- As linked sub-pages for complex topics

This preserves scannability (see `general/documentation-quality.md` -- 30-second findability) while providing depth for users who need it.

## Callout Patterns

Use these callout styles for additional guidance:

- **Tip**: Helpful shortcuts or best practices. Format: `<div class="help-tip">` or a blockquote with "Tip:" prefix.
- **Warning**: Actions that cannot be undone or have significant consequences. Format: `<div class="help-warning">` or a blockquote with "Warning:" prefix.

## Example: {{ScreenName}} Help Page

```html
<div class="help-header">
  <h1>{{Screen Title}}</h1>
  <p>{{One-sentence screen description}}</p>
</div>

<div class="help-content">
  <section class="help-section">
    <h2>What can I do here?</h2>
    <ul>
      <li>{{Capability 1}}</li>
      <li>{{Capability 2}}</li>
    </ul>
  </section>

  <section class="help-section">
    <h2>How should I go about doing it?</h2>
    <ol>
      <li>{{Step 1}} -- you will see {{expected result}}</li>
      <li>{{Step 2}}</li>
    </ol>
  </section>

  <section class="help-section">
    <h2>How will I know if I succeeded?</h2>
    <p>{{Success confirmation description}}</p>
  </section>

  <div class="help-tip">
    <strong>Tip:</strong> {{Helpful shortcut or best practice}}
  </div>

  <!-- Expanded sections (optional -- add for mature products) -->
  <hr class="help-expanded-divider" />

  <section class="help-section help-expanded">
    <h2>What are the constraints on my actions?</h2>
    <ul>
      <li>{{Permission requirement or role needed}}</li>
      <li>{{Size limit, format restriction, or boundary}}</li>
    </ul>
  </section>

  <section class="help-section help-expanded">
    <h2>What can go wrong?</h2>
    <ul>
      <li>{{Common failure mode}} -- {{recovery step}}</li>
      <li>{{Error message or symptom}} -- {{what to do}}</li>
    </ul>
  </section>

  <section class="help-section help-expanded">
    <h2>How does this affect others?</h2>
    <ul>
      <li>{{Who gets notified and when}}</li>
      <li>{{What changes for collaborators or administrators}}</li>
    </ul>
  </section>
</div>
```

## i18n Conventions

- One help directory per locale: `help/en-US/`, `help/pt-BR/`, etc.
- File names are locale-independent (same filename across locales): `groups.html`, `posts.html`
- All user-visible text must go through the i18n pipeline -- no hardcoded strings in help pages

## Freshness Policy

Review all contextual help pages before each release. Verify that documented workflows match current UI behavior. When a screen's functionality changes, update its help page in the same release.
