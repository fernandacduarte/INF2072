---
designer_description: "I'm the full long-form instantiation questionnaire for your project -- tiered by expertise so a solo designer can stop after the product sections and let architecture and engineering defaults fill themselves in, or a full team can customise every section -- and my answers are enough for an agent to generate every project reference file from the matching template."
---

# TEMPLATE - PROJECT INSTANTIATION QUESTIONNAIRE

> **Questionnaire version:** 6
> **Last updated:** 2026-04-02 00:00 UTC
>
> **Purpose:** Answer these questions to generate all 9 `project/` reference files from the `template/` templates. An agent can read your completed answers and produce the full set of project-specific references.
>
> **How to use:**
> 1. Start with **Section 0 (`metacomm-message`)** (optional, but fills defaults) and **Section 1 (`basic-definitions`)** -- these 10 answers are enough to generate a minimal skeleton.
> 2. Optionally answer **Section 0 (`metacomm-message`)** first -- an agent will extract project name, description, and user type to suggest defaults throughout the questionnaire.
> 3. For technical questions, choose from the provided alternatives or write your own.
> 4. Write `N/A` or `Skip` for sections that don't apply to your stack.
> 5. Work through remaining sections at your own pace. Sections are grouped by tier (T1 first, then T2, then T3). Use slugs for stable cross-references across documents.
> 6. When done, give this file to an agent with the instruction: *"Instantiate all template/\* files into project/\* files using the answers in this questionnaire."*
>
> **Alternative:** For a faster workflow, use `/design --generate-spec` to create a pre-fillable spec file (see `template/design-spec.md`).

---

## Knowledge Tiers

> This questionnaire is organized into three tiers based on the expertise required. If you are a solo product designer, focus on **T1** and accept the recommended defaults for **T2** and **T3**. If you have a full team, customize all three tiers.

| Tier | Sections | Who Fills It | Description |
|------|----------|-------------|-------------|
| **T1 -- Product & Design** | 0, 1, 2, 3, 4, 5 | Product designer (solo or with team) | What the product is, how it should feel, how it should look |
| **T2 -- Architecture** | 6, 7, 8 | Product designer with defaults OR software architect | Tech stack selection and architecture decisions |
| **T3 -- Engineering Standards** | 9, 10, 11 | Auto-generated from T2 OR engineering team | Testing, i18n, and security standards |

> **Solo designer?** Complete T1 sections fully. For T2, accept the recommended defaults (marked **Recommended** in option tables) or type `?` next to any answer to trigger an interactive discussion. T3 sections will be auto-generated from your T2 choices.

---

## Section Reference Table

> Stable slug identifiers for all sections. Slugs are stable identifiers for questionnaire sections; since SEJA 2.8.1 the standards targets are H2 sections within unified files (e.g., `ux-design-standards` populates `template/design-standards.md § UX patterns`, `backend-standards` populates `template/standards.md § Backend`). Use slugs for stable cross-references in plans and documentation; they are decoupled from file names.

| Slug | # | Title | Tier |
|------|---|-------|------|
| `metacomm-message` | 0 | Metacommunication Message | T1 |
| `basic-definitions` | 1 | Basic Definitions | T1 |
| `conceptual-design` | 2 | Conceptual Design | T1 |
| `ux-design-standards` | 3 | UX Design Standards | T1 |
| `graphic-ui-design-standards` | 4 | Graphic/UI Design Standards | T1 |
| `docs-templates` | 5 | Documentation Templates | T1 |
| `conventions` | 6 | Project Conventions | T2 |
| `frontend-standards` | 7 | Frontend Standards | T2 |
| `backend-standards` | 8 | Backend Standards | T2 |
| `testing-standards` | 9 | Testing Standards | T3 |
| `i18n-standards` | 10 | i18n Standards | T3 |
| `security-checklists` | 11 | Security Checklists | T3 |

---

## Parser directives

> Agents that consume this questionnaire may be invoked with a `section-include` argument that restricts processing to a subset of sections. When `section-include` is absent (the default), the parser processes **all** sections -- identical to pre-directive behavior.

### `section-include` grammar

The argument accepts a comma-separated list of selectors. Whitespace around commas is ignored.

| Selector | Meaning | Example |
|----------|---------|---------|
| `<N>` | A single whole section by ID | `1` = Section 1 |
| `<N>.<M>` | A single question (subsection) by its dotted ID | `0.1` = Question 0.1 |
| `<N>.*` | All questions inside Section N (equivalent to `<N>` for matching purposes, but explicit about the intent) | `2.*` = all of Section 2 |
| `<A>-<B>` | Range: Sections A through B inclusive | `2-5` = Sections 2, 3, 4, 5 |
| `<N>+` | Section N and every section after it | `5+` = Sections 5, 6, 7, 8, 9, 10, 11 |
| `<shortcut-name>` | A named shortcut (see below) | `stack-only` |

### Named shortcuts

| Shortcut | Expands to | Intent |
|----------|-----------|--------|
| `stack-only` | `0.1, 1.*` | Capture only the metacomm answer and the basic definitions needed to pin stack choices. Used by `/seja-setup` when bootstrapping a minimal skeleton. |
| `design-intent-only` | `0, 2.*, 3.*, 4.*, 5+` | Capture all design-intent-bearing sections (the metacomm message plus Sections 2 through 11). Used by `/design` when refining an already-stacked project. |

### Default behavior

When `section-include` is absent, the parser processes every `## Section N --` heading in order. This is backwards-compatible with pre-directive callers.

### Machine-readable section membership

Each `## Section N --` heading below is preceded by an HTML comment of the form:

```html
<!-- section-meta: id=<ID>; shortcuts=<comma-separated-shortcut-names-or-none> -->
```

Parsers may read these comments to route sections without re-parsing the natural-language prose in this directive block. When a section belongs to both shortcuts, both names are listed; when it belongs to neither, the value is `none`.

---

<!-- T1: Product & Design -- fill first; solo designers can stop after this block -->

<!-- section-meta: id=0; shortcuts=design-intent-only -->
<!-- Section 0 as a whole belongs to design-intent-only; Question 0.1 inside it additionally belongs to stack-only (see section-meta on Q 0.1 below). -->

## Section 0 -- Metacommunication Message (`metacomm-message`) [T1]

> **What this is:** An optional 1-3 sentence message from you (the designer) speaking directly to your future users. Use "I" (designer) and "you" (user) -- never third-person. See `general/shared-definitions.md` for the phrasing rule.
>
> **Why answer this first:** An agent filling in this questionnaire will extract project description, target user type, and primary use case from your message, offering them as suggested defaults for later questions -- reducing the number of questions you need to answer from scratch.
>
> **Example:** "I know you are a busy researcher who needs to track your experiments across projects. Therefore, I have designed a lightweight experiment tracking platform that lets you log runs, compare results, and share findings with your team."

<!-- section-meta: id=0.1; shortcuts=stack-only,design-intent-only -->

**0.1** Write your metacommunication message (optional):

Answer:

> *Agent extraction hints -- from this answer, an agent will suggest defaults for:*
>
> - *[basic-definitions] 1.1 -- project display name*
> - *[basic-definitions] 1.2 -- application description (1-2 sentences)*
> - *[conceptual-design] 2.1 -- what the platform does and who it is for*
> - *[conceptual-design] 2.10 -- target user community*

---

<!-- section-meta: id=1; shortcuts=stack-only -->

## Section 1 -- Basic Definitions (`basic-definitions`) [T1]

> These 10 questions generate a working skeleton for all 9 files. You can refine later.

| # | Question | Fills | Your Answer |
|---|----------|-------|-------------|
| 1.1 | What is your project's display name? | `{{PROJECT_NAME}}` | |
| 1.2 | What does your application do? (1--2 sentences) | Conceptual design intro | |
| 1.3 | Is this a new project (greenfield) or an existing project with code already written (brownfield)? | Project mode, directory structure | |
| 1.4 | What is your backend language/framework? | Backend standards scope | |
| 1.5 | What is your frontend language/framework? | Frontend standards scope | |
| 1.6 | What database will you use? | Backend DB sections | |
| 1.7 | What are your primary and secondary UI languages? (e.g., en-US, pt-BR) | `{{PRIMARY_LOCALE}}`, `{{SECONDARY_LOCALE}}` | |
| 1.8 | Name your generated-artifacts output folder (e.g., `_output`, `_generated`) | `{{OUTPUT_DIR}}` | |
| 1.9 | Name your backend and frontend source directories (e.g., `backend`, `frontend`) | `{{BACKEND_DIR}}`, `{{FRONTEND_DIR}}` | |
| 1.10 | Who is available on your team? (check all that apply: just me / + architect / + engineer(s) / + UX designer / + graphic/UI designer / + data engineer / + tester(s)) | Team composition | |

> *Agent hint: If the codebase directory contains existing source files (beyond framework files like `.claude/`, `product-design/`, `_output/`), suggest "brownfield" as the default answer for question 1.3.*

---

<!-- section-meta: id=2; shortcuts=design-intent-only -->

## Section 2 -- Conceptual Design (`conceptual-design`) [T1]

> Fills: `project/product-design-as-intended.md` (always) and `project/product-design-as-coded.md § Conceptual Design` (brownfield only) -- describes WHAT your system is (target state, and current state for evolving products), not HOW it's built.

**2.1** What does your platform do? Who is it for? What problem does it solve? (2--3 paragraphs)

Answer:

**2.2** Does your platform follow a specific design philosophy or methodology?

Answer:

**2.3** What are your main entities and their hierarchy? List them from top-level container down to leaf-level content.
> *Example: Organization → Project → Task → Comment*

Answer:

**2.4** For each entity above, briefly describe:
- What it represents
- Visibility/access rules (public, private, role-based)
- Ownership model (who creates it, who can delete it)
- Soft delete behavior (yes/no)

Answer:

**2.5** Are there any domain-specific concepts unique to your application? (e.g., workflows, scoring systems, annotation types, approval chains)

Answer:

**2.6** What permission levels does your system need?

**System-level roles** (e.g., guest, member, admin):

| Role | Capabilities |
|------|-------------|
| | |

**Resource-level access** (e.g., per-project, per-organization -- if applicable):

| Access Level | Capabilities |
|-------------|-------------|
| | |

**2.7** Does your application support content authoring? If so:
- How is authorship tracked?
- Can content be attributed to non-system users (e.g., imported authors)?
- Is there a mention/notification system?

Answer:

**2.8** Does your application support import/export? If so, list the formats and their purpose.

Answer:

**2.9** Is this a greenfield project (no existing implementation) or an evolving product with a gap between current and target design?
> *Determines whether /design defers as-coded files to post-plan execution (greenfield) or instantiates them immediately with current state (brownfield).*

Answer: (greenfield / evolving)

**2.10** Describe your target user community: language, geography, domain expertise.

Answer:

**2.11** What are your domain-driven validation limits? (e.g., title max 200 chars because of academic citation standards)
> *List field names, min/max values, and the domain rationale for each.*

| Field | Min | Max | Rationale |
|-------|-----|-----|-----------|
| | | | |

### Brownfield-Only Questions

> *Skip this subsection if you answered "greenfield" to question 1.3.*

**2.12** What is the existing tech stack? (languages, frameworks, database, hosting)

Answer:

**2.13** What are the main migration constraints? (e.g., cannot change database, must support existing API clients, data migration required)

Answer:

**2.14** How many active users does the current system have?

Answer:

**2.15** What are the top 3 pain points with the current system? (from a user or developer perspective)

Answer:

**2.16** Does the current system have an existing design system or style guide? If yes, provide a link or describe it.

Answer: (yes + link / no)

---

<!-- section-meta: id=3; shortcuts=design-intent-only -->

## Section 3 -- UX Design Standards (`ux-design-standards`) [T1]

> Fills: `project/design-standards.md § UX patterns` -- interaction patterns, usability, accessibility workflow, and responsive strategy. This is a **T1 (Product & Design)** section -- product designers should complete this directly.

### App Type

**3.1** What type of application are you building?
> *This determines recommended defaults for navigation, forms, empty states, and other UX patterns throughout this section.*

| Option | Description | Example | Recommendation |
|--------|-------------|---------|----------------|
| **CRUD Admin** | Data management with lists, forms, and detail views | Project management tool, CMS backend | **Recommended** default for most business apps |
| **Content Platform** | Publishing, reading, and discussion of content | Blog platform, knowledge base, wiki | Good for content-centric products |
| **Marketplace** | Browse, compare, and transact between parties | E-commerce, freelance marketplace | Good for multi-sided platforms |
| **Dashboard** | Data visualization, monitoring, and reporting | Analytics dashboard, admin panel | Good for data-heavy products |
| **Social / Community** | User profiles, feeds, messaging, collaboration | Social network, forum, team chat | Good for community-driven products |

Answer:

### Navigation

**3.2** What is your primary navigation pattern?

| Option | Best For | Pros | Cons | Recommendation |
|--------|----------|------|------|----------------|
| **Sidebar** | Admin panels, data-heavy apps with 5+ sections | Always visible, supports hierarchy | Consumes horizontal space | **Recommended** for most apps |
| **Top nav** | Content sites, apps with 3-5 sections | Clean layout, familiar | Limited items, no deep hierarchy | Good for content-focused products |
| **Bottom nav** | Mobile-first consumer products | Thumb-friendly on mobile | Max 5 items, desktop-unfriendly | Good for mobile-first apps |
| **Hamburger** | Simple apps, secondary navigation | Saves space | Hidden = low discoverability | Only if space is very constrained |

Answer:

### Forms

**3.3** What is your form validation strategy?

| Option | Best For | Pros | Cons | Recommendation |
|--------|----------|------|------|----------------|
| **Inline validation (on-blur)** | Most forms, data entry | Immediate feedback, fewer errors | Can feel aggressive if on-change | **Recommended** for most apps |
| **On-submit** | Checkout flows, multi-step wizards | Less noise during entry | Batch error display after submit | Good for transactional flows |
| **Progressive disclosure** | Complex forms, onboarding | Reduces cognitive load | Longer perceived flow | Good for complex onboarding |

Answer:

### Feedback & Notifications

**3.4** What is your primary feedback pattern for success messages?

| Option | Best For | Pros | Cons | Recommendation |
|--------|----------|------|------|----------------|
| **Toast (top-right)** | Most actions | Non-blocking, auto-dismisses | Can be missed | **Recommended** for most apps |
| **Inline banner** | Page-level actions | Highly visible, persistent | Takes space | Good for important confirmations |
| **Modal** | Critical confirmations only | Cannot be missed | Blocks interaction | Only for destructive action confirmations |

Answer:

### Empty States

**3.5** What is your empty state strategy?

| Option | Best For | Pros | Cons | Recommendation |
|--------|----------|------|------|----------------|
| **Action prompt** | Primary entities (first project, first task) | Guides first action | Needs custom copy per entity | **Recommended** for primary entities |
| **Illustration + text** | Secondary views (empty search, no notifications) | Friendly, reduces anxiety | Needs design assets | Good for secondary views |
| **Text-only** | Inline lists, table rows | Lightweight, easy | Less engaging | Good for minor sections |

Answer:

### Error Handling

**3.6** What is your error display preference?

| Option | Best For | Pros | Cons | Recommendation |
|--------|----------|------|------|----------------|
| **Inline (below field)** | Validation errors | Closest to the error source | Can clutter forms | **Recommended** for form validation |
| **Toast** | Network errors, transient failures | Non-blocking | Can be missed | Good for background failures |
| **Full-page** | 404, 500, permission denied | Clear, cannot be missed | Disrupts flow | Good for unrecoverable errors |

Answer:

### Accessibility

**3.7** What WCAG level do you target?

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **WCAG 2.1 AA** | Industry standard, achievable, covers most needs | Misses some enhanced requirements | **Recommended** minimum for all projects |
| **WCAG 2.1 AAA** | Best accessibility, higher contrast | Harder to achieve, some design constraints | Recommended for public/government/education |

Answer:

**3.8** What is your accessibility audit cadence?

| Option | Best For | Pros | Cons | Recommendation |
|--------|----------|------|------|----------------|
| **Per-release** | Most teams | Balances effort and coverage | Issues may accumulate within a release | **Recommended** for most teams |
| **Per-sprint** | Teams with dedicated a11y resources | Catches issues early | Requires tooling and expertise | Good for mature teams |
| **Quarterly** | Small teams, early-stage products | Low overhead | Issues ship to users before caught | Only for very early stage |

Answer:

### Responsive Design

**3.9** What is your responsive approach?

| Option | Best For | Pros | Cons | Recommendation |
|--------|----------|------|------|----------------|
| **Mobile-first** | Consumer products, content platforms | Forces prioritization, better perf | Desktop may feel empty without enhancement | **Recommended** for most projects |
| **Desktop-first** | Admin panels, data-heavy apps | Easier for complex layouts | Mobile often feels cramped | Good for admin-only tools |

Answer:

---

<!-- section-meta: id=4; shortcuts=design-intent-only -->

## Section 4 -- Graphic / UI Design Standards (`graphic-ui-design-standards`) [T1]

> Fills: `project/design-standards.md § Graphic / visual design` -- visual identity, color system, typography, spacing, iconography, and motion. This is a **T1 (Product & Design)** section -- product designers should complete this directly.
>
> **Minimal viable path:** Answer only 4.1-4.3 (two colors + one font). All other values will be generated using established design scales.

### Colors

**4.1** What are your brand colors? Provide hex values.
> *Minimum: primary and secondary. The agent will generate a full palette (light/dark variants, semantic colors) from these two inputs.*

| Token | Hex | Usage | Example |
|-------|-----|-------|---------|
| `primary` | | Main actions, headings, active states | `#2563eb` (blue) |
| `secondary` | | Secondary text, borders, icons | `#64748b` (slate) |
| `accent` (optional) | | Highlights, badges, special elements | `#f59e0b` (amber) |

> *Default: Primary `#2563eb`, Secondary `#64748b`. Rationale: blue is the most universally trusted color for digital products; slate provides neutral contrast without the coldness of pure gray. Example: GitHub, Stripe, and Linear all use blue primary palettes.*

**4.2** Will your application support dark mode?

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **No (light only)** | Half the design surface area; faster to ship | No dark mode | **Recommended** for MVP |
| **Yes** | User preference; reduces eye strain | Doubles design/testing surface | Good for consumer products |
| **Later** | Ship light first; plan for dark | Must use semantic tokens from day one | Good compromise |

Answer:

### Typography

**4.3** What is your primary UI font?
> *The agent will generate a full typography scale (7 sizes from xs to 3xl) using the Major Third ratio (1.250) from this font choice.*

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **System font stack** | 0ms load time, matches host OS, no FOIT | Less brand differentiation | **Recommended** unless brand requires custom font |
| **Inter** | Designed for screens, excellent readability, free | Requires font download (~100KB) | Good for products needing brand identity |
| **Custom font** | Maximum brand differentiation | Download cost, FOIT/FOUT risk, licensing | Only if brand guidelines require it |

Answer:

**4.4** What typography scale do you prefer?

| Option | Ratio | Best For | Example |
|--------|-------|----------|---------|
| **Minor Third** | 1.200 | Compact UIs, data-dense apps | Smaller size jumps between headings |
| **Major Third** | 1.250 | Most applications | Balanced hierarchy, clear distinction |
| **Perfect Fourth** | 1.333 | Editorial, marketing, content-heavy | Dramatic size differences |

> *Default: Major Third (1.250). Rationale: clear visual hierarchy without excessive size jumps; works for both data-heavy and content-oriented apps. Example: Tailwind CSS uses a similar progression.*

Answer:

### Spacing & Layout

**4.5** What is your base spacing unit?

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **8px** | Divides cleanly (4px, 2px); aligns with Material Design, Apple HIG | Slightly larger minimum gaps | **Recommended** for most projects |
| **4px** | Finer control, tighter spacing | Requires more skill to use well | Good for data-dense UIs |

Answer:

### Iconography

**4.6** Which icon set will you use?

| Option | Style | Icons | License | Pros | Cons | Recommendation |
|--------|-------|-------|---------|------|------|----------------|
| **Lucide** | Outlined, 24px | 1500+ | ISC (free) | Clean, consistent, active community | Outline-only | **Recommended** for most projects |
| **Heroicons** | Outlined + Solid | 300+ | MIT (free) | Tailwind team, two variants | Smaller set | Good with Tailwind |
| **Phosphor** | 6 weights | 7000+ | MIT (free) | Most versatile, huge set | Can be overwhelming | Good for complex apps |
| **Material Symbols** | Variable weight | 2500+ | Apache 2.0 | Largest set, Google-maintained | Can feel generic | Good for Material Design |

Answer:

### Component Visual Style

**4.7** What border radius style do you prefer?

| Option | Value | Best For | Recommendation |
|--------|-------|----------|----------------|
| **Sharp** | 0-2px | Data-dense UIs, enterprise tools | Professional, minimal |
| **Soft** | 4-8px | Most applications | **Recommended** -- balanced, modern |
| **Round** | 12-16px | Consumer-facing, friendly products | Casual, approachable |
| **Pill** | 9999px | Tags, badges, specific elements | Usually combined with another style |

Answer:

**4.8** What shadow style do you prefer?

| Option | Best For | Pros | Cons | Recommendation |
|--------|----------|------|------|----------------|
| **Flat** | Minimalist designs | Clean, modern | No depth cues | Good for border-based designs |
| **Subtle** | Most applications | Depth without heaviness | May need adjustment for dark mode | **Recommended** for most apps |
| **Elevated** | Material-inspired designs | Clear depth hierarchy | Can feel heavy | Good for layered UIs |

Answer:

### Motion

**4.9** What level of motion/animation do you want?

| Option | Best For | Pros | Cons | Recommendation |
|--------|----------|------|------|----------------|
| **None** | Accessibility-first, enterprise tools | Simplest, fastest | No transition feedback | Only for strictly functional UIs |
| **Subtle** | Most applications | Functional feedback, professional | Requires consistent implementation | **Recommended** for most apps |
| **Expressive** | Consumer products, onboarding | Delightful, memorable | Can be distracting; more work | Good for consumer-facing products |

Answer:

---

<!-- section-meta: id=5; shortcuts=design-intent-only -->

## Section 5 -- Documentation Templates (`docs-templates`) [T1]

> Fills: `project/docs/` -- documentation structures for your project. These templates define what documentation your project will maintain and how it's organized.
>
> **Quick path:** Accept defaults to get the 3 recommended templates (README, contextual help, DRR). Say "skip" to opt out entirely.

**5.1** Which documentation structures do you want?
> *Recommended templates are pre-selected. Optional templates depend on your app type.*

| Template | What it provides | Recommended |
|----------|-----------------|-------------|
| **README** | Project overview, setup, reading order for developers | Yes |
| **Contextual help** | Per-screen help pages with 3-question pattern (What/How/Verify) | Yes |
| **DRR** | Design Rationale Records for tracking design rationale | Yes |
| **Help center** | User-facing manual (minimal 5-page or full searchable) | No (recommended for content/marketplace/community apps) |
| **API reference** | Developer API documentation (endpoint index + deep-dives) | No |
| **Changelog** | User-facing release notes (Keep a Changelog format) | No |

Answer: (list selected templates, or "defaults" for recommended only, or "skip" for none)

**5.2** Does your application have user-facing screens that need contextual help?
> *If yes, the contextual help template will include i18n-ready structure for per-screen help pages following the proven "What can I do? / How to do it? / How to verify?" pattern.*

Answer: (yes / no)

**5.3** Do you want to track design decisions as DRRs?
> *Design Rationale Records capture the "why" behind significant decisions (framework choices, design patterns, trade-offs). They prevent future developers from undoing decisions without understanding the context.*

Answer: (yes / no)

---

<!-- T2: Architecture -- fill with team or accept Recommended defaults -->

<!-- section-meta: id=6; shortcuts=design-intent-only -->

## Section 6 -- Project Conventions (`conventions`) [T2]

> Fills: `project/conventions.md` -- the master variable file that all other references depend on.

**6.1** Project display name?
> *Fills `{{PROJECT_NAME}}`.*

Answer:

**6.2** Root directory for generated artifacts (plans, scripts, inventories, advisories)?
> *Fills `{{OUTPUT_DIR}}`. This folder will be created at the repo root. Choose a name that won't conflict with source directories.*

Answer:

**6.3** Backend source root directory?
> *Fills `{{BACKEND_DIR}}`. Typically `backend`, `server`, `api`, or `src`.*

Answer:

**6.4** Frontend source root directory?
> *Fills `{{FRONTEND_DIR}}`. Typically `frontend`, `client`, `web`, or `src`.*

Answer:

**6.5** Do you have additional source directories (e.g., `mobile`, `shared`, `libs`)? If so, list them with a short description.

Answer:

---

<!-- section-meta: id=7; shortcuts=design-intent-only -->

## Section 7 -- Frontend Standards (`frontend-standards`) [T2]

> Fills: `project/standards.md § Frontend` -- architectural and design conventions for the frontend.

### Framework Choices

**7.1** Which frontend framework will you use?
> *Fills overall frontend architecture. Choose one:*

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **React** | Largest ecosystem, most libraries/tooling, strong hiring pool | JSX learning curve, no built-in routing/state | **Recommended** for most web apps |
| **Vue** | Gentler learning curve, good docs, built-in reactivity | Smaller ecosystem than React, fewer enterprise patterns | Good for smaller teams or rapid prototyping |
| **Svelte/SvelteKit** | Minimal boilerplate, compiled output (smaller bundles) | Smaller ecosystem, fewer enterprise patterns, less hiring pool | Good for performance-critical or small-team projects |
| **Angular** | Full-featured framework (routing, forms, DI built-in), TypeScript-first | Steeper learning curve, heavier, opinionated | Good for large enterprise teams with Angular experience |

Answer:

**7.2** Which build tool?
> *Affects dev server, bundling, and plugin ecosystem.*

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **Vite** | Fastest dev server, native ESM, great plugin ecosystem | Newer, some edge cases with legacy deps | **Recommended** for new projects |
| **Next.js** | SSR/SSG built-in, file-based routing, Vercel integration | React-only, opinionated, heavier | Best if you need SSR/SSG |
| **Webpack** | Most mature, handles any edge case | Slower dev server, complex config | Only if migrating an existing Webpack project |

Answer:

**7.3** Which CSS framework/approach?

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **Tailwind CSS** | Utility-first, fast prototyping, consistent design, small production CSS | Class verbosity in markup, learning curve | **Recommended** for most projects |
| **CSS Modules** | Scoped styles, familiar CSS syntax, no runtime cost | No design system out of the box, more files | Good if team prefers traditional CSS |
| **styled-components** | CSS-in-JS, dynamic styling, co-located with components | Runtime cost, bundle size, React-specific | Good for highly dynamic theming |
| **Plain CSS / SCSS** | No dependencies, full control | No scoping, harder to maintain at scale | Only for very small projects |

Answer:

**7.4** Which state management approach?

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **React Context + hooks** | No extra dependencies, built into React, simple for most apps | Performance issues with frequent updates, no devtools | **Recommended** for apps with <10 global state values |
| **Zustand** | Tiny (1KB), simple API, good devtools, no boilerplate | Less structured than Redux | Good for medium complexity |
| **Redux Toolkit** | Mature, excellent devtools, structured patterns | Boilerplate, steeper learning curve | Good for large apps with complex state |
| **Jotai / Recoil** | Atomic state model, fine-grained reactivity | Newer, smaller ecosystem | Good for apps with many independent state atoms |

Answer:

**7.5** Which data fetching/caching library?

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **TanStack Query** | Automatic caching, background refetch, optimistic updates, devtools | Learning curve for cache invalidation | **Recommended** for any app with REST/GraphQL APIs |
| **SWR** | Simpler API than TanStack Query, Vercel-maintained | Fewer features (no mutations, no devtools) | Good for simpler data-fetching needs |
| **Manual (useEffect + fetch)** | No dependencies, full control | No caching, stale data, boilerplate | Only for very simple apps or learning |

Answer:

**7.6** Which HTTP client?

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **Axios** | Interceptors, request/response transforms, wide adoption | 13KB bundle, third-party dependency | **Recommended** for apps needing interceptors (auth, CSRF, error normalization) |
| **fetch (native)** | Zero dependencies, built into all browsers | No interceptors, manual JSON parsing, verbose error handling | Good for simple apps or when bundle size is critical |
| **ky** | Tiny (3KB), modern fetch wrapper, retries | Smaller ecosystem | Good middle ground |

Answer:

**7.7** Which rich text editor? (Skip if not needed)

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **Lexical** | Meta-maintained, extensible, good React support, small bundle | Steeper learning curve, newer | **Recommended** for new projects needing rich text |
| **TipTap** | Great DX, extensive extensions, ProseMirror-based | Larger bundle, some features behind paywall | Good for content-heavy apps |
| **Quill** | Simple setup, good for basic rich text | Less extensible, older architecture | Good for simple use cases |
| **None** | Simpler codebase | No rich text capability | Skip this section |

Answer:

**7.8** Which router? (if React)

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **React Router v7** | Most mature, large ecosystem, file-based routing option | API churn between versions | **Recommended** for React apps |
| **TanStack Router** | Type-safe, search params validation, newer design | Newer, smaller ecosystem | Good for TypeScript-heavy projects |

Answer:

### Design Choices

**7.9** What are your brand colors?
> *Provide semantic names and hex values. Minimum: primary, secondary.*

| Token | Hex | Usage |
|-------|-----|-------|
| `primary` | | Main actions, headings |
| `secondary` | | Links, secondary actions |

**7.10** What fonts will you use?
> *Provide font family names for sans-serif (UI) and serif (content, if applicable).*

| Token | Font Family | Usage |
|-------|------------|-------|
| `sans` | | Primary UI font |
| `serif` | | Content font (if applicable) |

**7.11** Will your application support dark mode?

Answer: (yes / no / later)

**7.12** What WCAG level do you target?

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **WCAG 2.1 AA** | Industry standard, achievable, covers most needs | Misses some enhanced requirements | **Recommended** minimum for all projects |
| **WCAG 2.1 AAA** | Best accessibility, higher contrast, more keyboard support | Harder to achieve, some design constraints | Recommended for public/government/education platforms |

Answer:

**7.13** List the React Context providers your app will need:
> *Common contexts: Auth, Theme, Notifications. Add domain-specific ones.*

| Context | Purpose | Hook |
|---------|---------|------|
| `AuthContext` | User session | `useAuth()` |
| | | |

**7.14** What reusable components will your app start with?
> *Common: AlertMessage, Modal, DoubleConfirmationModal, Toast, Breadcrumb, ErrorBoundary. Add domain-specific ones.*

Answer:

---

<!-- section-meta: id=8; shortcuts=design-intent-only -->

## Section 8 -- Backend Standards (`backend-standards`) [T2]

> Fills: `project/standards.md § Backend` -- architectural conventions for the backend.

### Framework Choices

**8.1** Which backend framework?

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **Flask** | Lightweight, flexible, easy to learn, large ecosystem | No built-in ORM/auth/admin, more manual setup | **Recommended** for small-to-medium APIs |
| **Django** | Batteries-included (ORM, admin, auth, migrations), mature | Heavier, more opinionated, monolithic | Good for data-heavy apps needing admin UI |
| **FastAPI** | Async, auto-generated docs, Pydantic validation, modern Python | Younger ecosystem, async complexity | Good for high-throughput APIs or microservices |
| **Express/NestJS** | JavaScript/TypeScript fullstack, large ecosystem | Node.js event loop quirks, callback patterns (Express) | Good for TypeScript fullstack teams |

Answer:

**8.2** Which ORM / database layer?

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **SQLAlchemy** | Most powerful Python ORM, flexible, supports raw SQL | Complex, steeper learning curve | **Recommended** for Flask or FastAPI |
| **Django ORM** | Integrated with Django, simple, great migrations | Django-only, less flexible for complex queries | Use with Django |
| **Prisma** | Type-safe, great DX, auto-generated client | Node.js only, less mature for complex queries | Use with Express/NestJS |
| **TypeORM / Drizzle** | TypeScript-native, decorators or schema-based | TypeORM has known issues at scale; Drizzle is newer | Use with NestJS |

Answer:

**8.3** Which database?

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **PostgreSQL** | Feature-rich, JSONB, full-text search, rock-solid | Slightly more setup than SQLite | **Recommended** for production apps |
| **MySQL/MariaDB** | Wide hosting support, familiar | Fewer advanced features than Postgres | Good if hosting requires it |
| **SQLite** | Zero setup, embedded, great for dev/testing | Single-writer, no network access, limited concurrent writes | Good for prototyping and unit tests only |
| **MongoDB** | Flexible schema, horizontal scaling | No ACID transactions (by default), query limitations | Good for document-centric or high-write-volume apps |

Answer:

**8.4** Which migration tool?

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **Alembic** | SQLAlchemy-native, auto-generates from models, flexible | Manual for complex migrations | **Recommended** with SQLAlchemy |
| **Django Migrations** | Auto-generated, integrated, easy | Django-only | Use with Django |
| **Prisma Migrate** | Type-safe, declarative schema | Prisma-only | Use with Prisma |
| **Manual SQL** | Full control, no abstraction | Error-prone, no rollback tracking | Not recommended |

Answer:

**8.5** Which validation library?

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **Marshmallow** | Mature, flexible, great with Flask/SQLAlchemy | Separate from ORM, boilerplate | **Recommended** for Flask |
| **Pydantic** | Built into FastAPI, Python type hints, fast | FastAPI-centric, less flexible for complex nesting | Use with FastAPI |
| **Django Forms / Serializers** | Integrated, DRF serializers are powerful | Django-only | Use with Django/DRF |
| **Zod / Joi** | TypeScript/JavaScript-native, composable | Node.js only | Use with Express/NestJS |

Answer:

**8.6** Which authentication approach?

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **JWT (HttpOnly cookies)** | Stateless, scalable, secure cookie storage | Token revocation requires blocklist, cookie setup complexity | **Recommended** for SPAs with same-origin API |
| **JWT (localStorage)** | Simple frontend implementation | XSS-vulnerable, tokens accessible to JavaScript | Not recommended for production |
| **Session-based** | Simple, built into most frameworks, easy revocation | Server-side storage, scaling requires session store | Good for traditional server-rendered apps |
| **OAuth2 / OpenID Connect** | Delegated auth, social login, enterprise SSO | Complex setup, third-party dependency | Good when integrating with identity providers |

Answer:

**8.7** What JWT token expiry times?
> *Fills `{{access_token_expiry}}`, `{{refresh_token_expiry}}`.*

- Access token: (e.g., 1 hour)
- Refresh token: (e.g., 7 days)

Answer:

**8.8** What is the default rate limit?
> *Fills `{{default_rate_limit}}`.*

Answer: (e.g., 200/minute)

**8.9** List your initial backend extensions/libraries:
> *Common: ORM, JWT auth, migrations, rate limiter, i18n, CORS, validation, API docs.*

| Extension | Purpose |
|-----------|---------|
| | |

**8.10** Will your backend serve file uploads? If yes, what are the size limits and allowed formats?

Answer:

**8.11** Will your backend support import/export? If yes, what formats?

Answer:

---

<!-- T3: Engineering Standards -- auto-generated from T2 choices or fill with engineering team -->

<!-- section-meta: id=9; shortcuts=design-intent-only -->

## Section 9 -- Testing Standards (`testing-standards`) [T3]

> Fills: `project/standards.md § Testing` -- testing conventions across all layers.

**9.1** Which backend test framework?

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **pytest** | Powerful fixtures, plugins, parametrize, most popular Python | Some magic with fixtures/discovery | **Recommended** for Python backends |
| **unittest** | Built into Python, no extra dependency | Verbose, less ergonomic | Only if avoiding dependencies |
| **Jest** | Built-in mocking, snapshots, wide JS adoption | Node.js only | Use with Express/NestJS |

Answer:

**9.2** Which frontend test framework?

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **Vitest** | Vite-native, fast, compatible with Jest API | Newer, some edge cases | **Recommended** with Vite |
| **Jest** | Most mature, largest ecosystem, snapshots | Slower than Vitest, CJS-native | Good for Webpack projects |

Answer:

**9.3** Which E2E test framework?

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **Playwright** | Multi-browser, auto-wait, codegen, trace viewer | Larger install size | **Recommended** for new projects |
| **Cypress** | Great DX, time-travel debugging, dashboard | Chromium-focused, no multi-tab, paid features | Good for simpler E2E needs |
| **None** | Simpler setup | No E2E coverage | Skip E2E section |

Answer:

**9.4** Will you use a separate integration test suite against a real database? (yes / no)

Answer:

**9.5** What is your E2E base URL?
> *Fills `{{base_url}}`.*

Answer: (e.g., `http://localhost:3000`)

---

<!-- section-meta: id=10; shortcuts=design-intent-only -->

## Section 10 -- i18n Standards (`i18n-standards`) [T3]

> Fills: `project/standards.md § i18n` -- internationalization conventions.

**10.1** How many languages will your application support at launch?
> *List RFC 5646 codes (e.g., `en-US`, `pt-BR`, `fr-FR`, `de-DE`).*

| Locale Code | Language | Role |
|------------|----------|------|
| | | Primary (UI default) |
| | | Secondary |
| | | (additional, if any) |

**10.2** What is the backend's default locale for error messages?
> *Fills `{{BACKEND_DEFAULT_LOCALE}}`. Often differs from frontend default (e.g., backend defaults to `en-US` for developer-facing logs while frontend defaults to the community's primary language).*

Answer:

**10.3** Why did you choose these defaults?
> *Helps document the rationale in the i18n standards file.*

- Frontend default rationale:
- Backend default rationale:

**10.4** Does your application send localized emails? (yes / no)

Answer:

**10.5** Do any domain entities store translations in the database? (e.g., category names in multiple languages)
> *If yes, list the entities and their translatable fields.*

Answer:

---

<!-- section-meta: id=11; shortcuts=design-intent-only -->

## Section 11 -- Security Checklists (`security-checklists`) [T3]

> Fills: `project/security-checklists.md` -- security checklists are mostly generic; customize the constants table.

**11.1** List your validation constants with their values:
> *These will populate the Quick Reference table and must stay in sync between backend and frontend.*

| Field | Backend Constant | Frontend Constant | Value |
|-------|-----------------|-------------------|-------|
| Login length min | | | |
| Login length max | | | |
| Password min | | | |
| Name max | | | |
| Email max | | | |
| (add more) | | | |

**11.2** Where are validation constants defined?
> *Fills `{{backend_constants_path}}` and `{{frontend_constants_path}}`.*

- Backend:
- Frontend:

**11.3** Are there any checklists (A--N) that don't apply to your project? List them.
> *Example: "Checklist B (File Upload) -- N/A, no file uploads" or "Checklist L (SSRF) -- N/A, no user-supplied URLs"*

Answer:

**11.4** Do you have any project-specific security requirements not covered by checklists A--N? (e.g., compliance certifications, data residency, audit logging requirements)

Answer:

---

## Final Step -- Metacommunication Message (if not provided in Section 0)

> **When this applies:** Only when the user did not provide a metacommunication message -- neither in Section 0 (`metacomm-message`) nor at `/design` invocation (e.g., as part of the initial prompt/brief). If a metacomm message was supplied at invocation, the agent reuses it verbatim as the Section 0.1 answer and skips this Final Step. Otherwise, this step is always the last item asked, regardless of whether the user skipped other sections.
>
> **What the agent does:** Using the answers (or assumed defaults) from all previous sections, the agent composes a recommended metacommunication message -- a 1-3 sentence message from the designer (I) speaking directly to the user (you), describing who the user is, what the designer has designed for them, and why (see `general/shared-definitions.md` for the full definition and phrasing rule).
>
> **Interaction:** The agent presents the recommended message and asks the user to:
>
> - **Accept** -- the message is recorded as-is. The agent appends a note: *"Generated by the design agent based on specifications defined in the design session on \<YYYY-MM-DD HH:MM UTC\>."*
> - **Edit** -- the user modifies the message; the agent records the edited version verbatim (per the verbatim rule in `general/shared-definitions.md`). No generation note is appended.
> - **Reject and skip** -- no metacommunication message is recorded; the field is left blank.
>
> *Feeds `project/product-design-as-intended.md`. Must follow the phrasing rule in `general/shared-definitions.md` -- always "I" (designer) and "you" (user), never third-person.*

---

## Post-Questionnaire Checklist

After completing all sections:

- [ ] Section `metacomm-message` (0) -- Metacommunication Message is filled or explicitly skipped
- [ ] Section `basic-definitions` (1) -- Basic Definitions is fully filled (including project mode and team composition)
- [ ] Section `conceptual-design` (2) -- describes entities, permissions, and greenfield/evolving status
- [ ] Section `ux-design-standards` (3) -- has interaction patterns, accessibility, and responsive choices
- [ ] Section `graphic-ui-design-standards` (4) -- has colors, typography, spacing, icons, and visual style choices
- [ ] Section `docs-templates` (5) -- has selected templates or explicit "skip"
- [ ] Section `conventions` (6) -- defines all directory paths
- [ ] Section `frontend-standards` (7) -- has framework and design choices
- [ ] Section `backend-standards` (8) -- has framework and architecture choices
- [ ] Section `testing-standards` (9) -- has framework choices per layer
- [ ] Section `i18n-standards` (10) -- has locale codes and defaults
- [ ] Section `security-checklists` (11) -- has validation constants

**Next step:** Give this file to an agent with:
> *"Read template/questionnaire.md and instantiate all template/\* files in `product-design/` into corresponding project/\* files using my answers."*

---

## Version History

> This section tracks changes to the questionnaire format. When a spec file's `version` field differs from the current `questionnaire_version`, the agent uses this history to identify new, changed, or removed fields and offer migration.

| Version | Date       | Changes                                                                                                                      |
|---------|------------|------------------------------------------------------------------------------------------------------------------------------|
| 1       | 2026-03-25 00:00 UTC | Initial versioned release. Sections 0-7 with all fields. Companion spec file format (template/design-spec.md) introduced |
| 2       | 2026-03-29 00:00 UTC | Added Knowledge Tiers preamble (T1/T2/T3). Added questions 0.3 (project mode, moved early for directory-structure routing) and 0.10 (team composition) to Section 0. Renumbered 0.3-0.8 to 0.4-0.9. Added brownfield-only questions 2.13-2.17 to Section 2. Added Section 8 (UX Design Standards, 9 questions). Added Section 9 (Graphic/UI Design Standards, 9 questions). Updated post-questionnaire checklist. Total project files generated: 7 to 9. |
| 3       | 2026-04-01 00:00 UTC | Added Section 10 (Documentation Templates, 3 questions) to T1 tier. Documentation templates in `template/docs/` can now be instantiated during project setup. Updated post-questionnaire checklist. |
| 4       | 2026-04-02 00:00 UTC | Added Section M (Metacommunication Message) as first T1 section. Added Section Reference Table with slugs. Annotated all section headers with slug identifiers and tier tags. Reordered sections by tier (T1: M, 0, 2, 8, 9, 10; T2: 1, 3, 4; T3: 5, 6, 7). Added HTML tier block dividers. Updated How to use block. T1 tier now includes section M. |
| 5       | 2026-04-02 00:00 UTC | Moved metacommunication message fallback from question 2.10 to a new "Final Step" section after all questionnaire sections. When the user did not provide a message in Section M, the agent now generates a recommended metacommunication message inferred from previous answers, allowing the user to accept, edit, or reject-and-skip. Accepted generated messages are annotated with a generation note. Renumbered 2.11-2.17 to 2.10-2.16. |
| 6       | 2026-04-02 00:00 UTC | Renumbered all sections sequentially by tier order: M->0, 0->1 (renamed "Basic Definitions", slug `quick-start`->`basic-definitions`), 2->2, 8->3, 9->4, 10->5, 1->6, 3->7, 4->8, 5->9, 6->10, 7->11. All question sub-numbers updated to match new section prefixes. Post-Questionnaire Checklist now uses slug-based references. External references (SKILL.md) migrated from section numbers to slugs. |
| 7       | 2026-04-20 00:00 UTC | Introduced `section-include` parser directive and the `stack-only` / `design-intent-only` shortcuts (see `## Parser directives` near the top of the file). Added per-heading `<!-- section-meta: id=...; shortcuts=... -->` comments to enable parser routing without re-parsing prose. No questions added, removed, or renumbered. Supports split ownership: `/seja-setup` consumes `stack-only`; `/design` consumes `design-intent-only`. |
