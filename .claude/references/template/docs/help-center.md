---
recommended: false
depends_on: [Content Platform, Marketplace, Social / Community]
freshness: every-release
diataxis: how-to
description: "Help center structure with two variants (minimal 5-page manual and full searchable), i18n support."
designer_description: "When /document generates your end-user help center, I'm the template that shapes either the minimal 5-page manual (overview, per-role pages, workflows, admin) or the full searchable variant with FAQ and i18n mirroring, using your plan's Docs: fields and the roles your project has declared, so the help your users actually read is organised by what they want to do rather than by your feature list."
---

# TEMPLATE -- HELP CENTER / USER MANUAL

> **How to use this template:** Choose the variant that fits your project size. The minimal variant works for most apps; the full variant adds search and FAQ for larger products with diverse user bases.

## Variant 1: Minimal (5-Page Manual)

Organize by role and capability, not by feature. Five topic pages cover most applications:

| Page | Covers | Audience |
|------|--------|----------|
| `index.html` | Overview, capability matrix, navigation | All users |
| `{{role-1}}.html` | Capabilities for {{role 1}} | {{Role 1}} users |
| `{{role-2}}.html` | Capabilities for {{role 2}} | {{Role 2}} users |
| `{{workflows}}.html` | Step-by-step task guides | All users |
| `{{admin}}.html` | Administration and configuration | Admins |

### Page Structure

Each page follows this structure:
- Header with navigation links to all other pages
- Main content organized by `<section>` blocks with `<h2>` headings
- "Back to overview" footer link

## Variant 2: Full (Searchable Help Center)

Extends the minimal variant with:

| Addition | Purpose |
|----------|---------|
| Search | Full-text search across all help articles |
| FAQ | Frequently asked questions per category |
| Categories | Hierarchical organization beyond 5 pages |
| Feedback | "Was this helpful?" widget per article |

### Category Structure

```
help-center/
  {locale}/
    index.html          -- Overview with search
    getting-started/    -- Onboarding articles
    {{category-1}}/     -- Domain-specific articles
    {{category-2}}/
    faq.html            -- Frequently asked questions
```

## i18n Conventions

- Mirror the entire structure per locale: `{locale}/`
- Same filenames across locales
- All user-visible text through i18n pipeline

## Freshness Policy

Review all help center pages before each release. Verify that documented workflows match current UI. Update screenshots and step counts when flows change.
