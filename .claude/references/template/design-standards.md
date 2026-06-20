---
designer_description: "I list the UX and visual-design conventions your project follows -- app type, navigation, form patterns, feedback, empty states, accessibility workflow, tokens, typography, iconography, motion -- so every screen you design and every component you ship can be reviewed against one agreed baseline rather than re-litigated on each feature."
---

# TEMPLATE - DESIGN STANDARDS REFERENCE

> **How to use this template:** Copy this file to `project/design-standards.md` and populate the relevant sections for your project's UX patterns and visual-design conventions. This unified file replaces the two separate design-standards files (ux-design-standards, graphic-ui-design-standards) that existed prior to SEJA 2.8.1. See the harness CHANGELOG for the migration rationale (source: advisory-000264 Phase 1).

---

## UX patterns

### 1. App Type & Default Pattern Set

> Select the app type that best describes your product. This determines the recommended defaults throughout this file.

| App Type | Description | Example | Recommended Navigation | Recommended Form Pattern |
|----------|-------------|---------|----------------------|-------------------------|
| **CRUD Admin** | Data management with lists, forms, and detail views | Project management tool, CMS backend | Sidebar | Inline validation |
| **Content Platform** | Publishing, reading, and discussion of content | Blog platform, knowledge base, wiki | Top nav | Progressive disclosure |
| **Marketplace** | Browse, compare, and transact between parties | E-commerce, freelance marketplace | Top nav + filters | On-submit (checkout flow) |
| **Dashboard** | Data visualization, monitoring, and reporting | Analytics dashboard, admin panel | Sidebar + tabs | Inline validation |
| **Social / Community** | User profiles, feeds, messaging, collaboration | Social network, forum, team chat | Bottom nav (mobile) / Sidebar (desktop) | Inline validation |

**Selected app type:** `{{APP_TYPE}}`

> *Default: CRUD Admin. Rationale: most common app type for new projects; provides a well-understood interaction vocabulary. Example: a project management tool like Trello or Asana.*

---

### 2. Navigation Patterns

> How users move between major sections of your application.

#### Primary Navigation

| Pattern | Best For | Pros | Cons |
|---------|----------|------|------|
| **Sidebar** | Admin panels, data-heavy apps with 5+ top-level sections | Always visible, supports deep hierarchy, works with icons + labels | Consumes horizontal space, harder on small screens |
| **Top nav** | Content sites, marketing pages, apps with 3-5 sections | Clean layout, familiar pattern, full-width content area | Limited items, no deep hierarchy, collapses to hamburger on mobile |
| **Bottom nav** | Mobile-first apps, consumer products | Thumb-friendly, always visible on mobile | Max 5 items, no hierarchy, desktop-unfriendly |
| **Hamburger** | Simple apps, mobile-first, secondary navigation | Saves space, hides complexity | Hidden = lower discoverability, extra tap to access |

**Selected pattern:** `{{PRIMARY_NAVIGATION}}`

> *Default: Sidebar. Rationale: accommodates growth (adding sections later), provides persistent wayfinding, and works well for both data-heavy and content-oriented applications. Example: GitHub's left sidebar.*

#### Secondary Navigation

| Pattern | When to Use | Example |
|---------|-------------|---------|
| **Tabs** | 2-5 views within a page context | Settings page with General / Security / Notifications tabs |
| **Breadcrumbs** | Hierarchical content deeper than 2 levels | File explorer: Home > Projects > My Project > Settings |
| **Contextual sidebar** | Filters, configuration panels | E-commerce category filters |

**Selected secondary pattern:** `{{SECONDARY_NAVIGATION}}`

> *Default: Tabs + Breadcrumbs (both). Rationale: tabs handle in-page navigation while breadcrumbs handle hierarchical depth -- they serve complementary purposes. Example: AWS Console uses breadcrumbs for hierarchy and tabs within resource pages.*

---

### 3. Form Patterns

> How your application collects and validates user input.

#### Validation Strategy

| Strategy | Best For | Pros | Cons |
|----------|----------|------|------|
| **Inline validation** | Most forms, especially data entry | Immediate feedback, fewer submission errors | Can feel aggressive if triggered too early (use on-blur, not on-change) |
| **On-submit** | Checkout flows, multi-step wizards | Less visual noise during entry, batch error display | Users must fix errors after attempting submission |
| **Progressive disclosure** | Complex forms, onboarding | Reduces cognitive load, guides users step by step | Longer perceived flow, users can't see the full picture |

**Selected strategy:** `{{FORM_VALIDATION_STRATEGY}}`

> *Default: Inline validation (on-blur). Rationale: industry standard for web forms since 2015; reduces submission errors by 22% (Baymard Institute, 2024). Trigger validation on field blur, not on every keystroke. Example: GitHub's sign-up form validates username availability on blur.*

#### Form Conventions

| Convention | Default | Rationale | Example |
|-----------|---------|-----------|---------|
| Required field indicator | Asterisk (*) after label | Most universally recognized pattern (Nielsen Norman Group) | `Email *` |
| Error message placement | Below the field, in red/danger color | Closest to the error source; color provides secondary signal | `Password must be at least 8 characters` |
| Success feedback | Green checkmark icon on valid fields | Positive reinforcement reduces abandonment | Green checkmark after valid email |
| Disabled submit button | Enabled always; show errors on click | Disabled buttons confuse users about what's wrong | Submit button always clickable; errors appear on click if invalid |
| Auto-save | For long forms (>5 fields) | Prevents data loss on accidental navigation | Draft auto-saved every 30 seconds |
| Form layout | Single column, top-aligned labels | Fastest completion time (Matteo Penzo, 2006); mobile-friendly | Labels above fields, one field per row |

---

### 4. Feedback & Notification Patterns

> How the application communicates status changes, confirmations, and errors to users.

#### Feedback Types

| Type | Pattern | When to Use | Duration | Example |
|------|---------|-------------|----------|---------|
| **Success** | Toast notification | After completing an action | 3-5 seconds, auto-dismiss | "Project saved successfully" |
| **Error (recoverable)** | Inline message | Validation errors, failed requests with retry | Persistent until resolved | "Failed to save. [Retry]" |
| **Error (critical)** | Error page or modal | System errors, permission denied, 500 | Persistent | "Something went wrong. Please try again later." |
| **Warning** | Banner or inline alert | Approaching limits, deprecated features | Persistent until dismissed | "You have 2 days left in your trial" |
| **Info** | Inline tip or banner | First-time hints, feature announcements | Dismissible | "Tip: You can drag items to reorder them" |
| **Loading** | Skeleton screen or spinner | Data fetching, processing | Until complete | Skeleton placeholders matching content layout |
| **Confirmation** | Modal dialog | Destructive actions (delete, overwrite) | Until user decides | "Delete this project? This cannot be undone." |

#### Feedback Conventions

| Convention | Default | Rationale | Example |
|-----------|---------|-----------|---------|
| Toast position | Top-right | Visible without obstructing content; follows reading direction (LTR) | Toast appears at top-right, stacks downward |
| Toast auto-dismiss | 4 seconds for success, persistent for errors | Success needs acknowledgment, not action; errors need resolution | Success toast fades after 4s; error toast stays with dismiss button |
| Destructive confirmation | Double confirmation (type to confirm) for irreversible actions | Prevents accidental data loss; required for delete-all, account deletion | "Type DELETE to confirm" |
| Optimistic updates | Yes, for low-risk actions (star, bookmark, reorder) | Reduces perceived latency; rollback on failure | Star icon toggles instantly; reverts if API fails |
| Loading skeleton | Match content layout shape | Reduces layout shift (CLS); feels faster than spinners | Card-shaped skeletons while loading a card grid |

---

### 5. Empty States & Zero-Data Design

> What users see when there's no content to display.

#### Empty State Strategy

| Strategy | Best For | Pros | Cons |
|----------|----------|------|------|
| **Action prompt** | Primary entities (first project, first task) | Guides users to take their first action; reduces confusion | Requires custom illustration/copy per entity |
| **Illustration + text** | Secondary views (empty search results, no notifications) | Friendly, reduces anxiety about empty screens | Requires design assets |
| **Text-only** | Inline lists, table rows, minor sections | Lightweight, easy to implement | Less engaging |

**Selected strategy:** `{{EMPTY_STATE_STRATEGY}}`

> *Default: Action prompt for primary entities, text-only for secondary. Rationale: first-use experience drives retention; primary entities deserve rich empty states while secondary views can be minimal. Example: Notion's "Get started" page with template suggestions vs. an empty search result showing "No results found."*

#### Empty State Checklist

Every empty state must include:

- [ ] Explanation of why it's empty (context-appropriate)
- [ ] Primary action to create content (if applicable)
- [ ] Visual distinction from loading/error states
- [ ] Appropriate tone (encouraging for first-use, neutral for filtered results)

---

### 6. Error Handling UX

> How errors are presented and how users recover from them.

#### Error Handling Strategy

| Error Type | Display Pattern | Recovery Path | Example |
|-----------|----------------|---------------|---------|
| **Validation** | Inline, below field | Fix the field and re-submit | "Email format is invalid" |
| **Network** | Toast or inline banner with retry | Automatic retry + manual retry button | "Connection lost. Retrying... [Retry now]" |
| **Permission** | Full-page or section-level message | Request access or contact admin | "You don't have access to this project. [Request access]" |
| **Not found** | Full-page 404 | Navigation to parent or home | "This page doesn't exist. [Go to dashboard]" |
| **Server error** | Full-page 500 | Retry or contact support | "Something went wrong. [Try again] [Contact support]" |
| **Rate limit** | Toast with countdown | Wait and retry | "Too many requests. Try again in 30 seconds." |

#### Error UX Conventions

| Convention | Default | Rationale | Example |
|-----------|---------|-----------|---------|
| Error language | Plain language, no codes | Users don't understand HTTP codes or stack traces | "We couldn't save your changes" not "Error 500: Internal Server Error" |
| Preserve user input | Always on form errors | Losing typed data is the #1 frustration (Baymard, 2024) | Form fields retain values after validation error |
| Error boundary | Per-section, not full page | A failing widget shouldn't break the entire page | Sidebar error doesn't crash the main content area |
| Retry mechanism | Automatic (3x, exponential backoff) + manual button | Transient failures often resolve on retry | Auto-retry with "Still trying..." then "Retry" button |

---

### 7. Usability Heuristics Checklist

> Adapted from Jakob Nielsen's 10 Usability Heuristics (1994, revised 2024) for web applications. Use this as a review checklist when designing new features.

| # | Heuristic | Question to Ask | Example |
|---|-----------|----------------|---------|
| 1 | **Visibility of system status** | Does the user always know what's happening? | Loading indicators, progress bars, save confirmations |
| 2 | **Match between system and real world** | Does the UI use the user's language, not developer jargon? | "Remove" not "DELETE", "Sign in" not "Authenticate" |
| 3 | **User control and freedom** | Can users undo, cancel, or go back easily? | Undo toast after delete, Cancel button on every modal |
| 4 | **Consistency and standards** | Does this follow platform conventions and our own patterns? | Same button styles, same form layouts, same terminology |
| 5 | **Error prevention** | Does the design prevent errors before they happen? | Disable unavailable options, confirm destructive actions |
| 6 | **Recognition rather than recall** | Is information visible rather than requiring memory? | Autocomplete, recent items, visible labels (not just icons) |
| 7 | **Flexibility and efficiency** | Can experienced users take shortcuts? | Keyboard shortcuts, bulk actions, search-as-navigation |
| 8 | **Aesthetic and minimalist design** | Is every element necessary? Does it earn its space? | Remove decorative elements that don't serve function |
| 9 | **Help users recognize and recover from errors** | Are error messages clear, specific, and actionable? | "Password must include a number" not "Invalid input" |
| 10 | **Help and documentation** | Is help available in context, not just in a separate docs site? | Tooltips, inline hints, contextual help panels |

---

### 8. Accessibility Workflow

> How your team ensures the application is accessible to all users.

#### Target Level

**WCAG target:** `{{WCAG_LEVEL}}`

> *Default: WCAG 2.1 AA. Rationale: industry standard; legally required in many jurisdictions (ADA, EAA 2025); achievable without specialized expertise. AAA is recommended for public/education/government platforms. Example: all text meets 4.5:1 contrast ratio (AA) vs. 7:1 (AAA).*

#### Accessibility Audit Cadence

| Cadence | Best For | Pros | Cons |
|---------|----------|------|------|
| **Per-sprint** | Teams with dedicated a11y resources | Catches issues early, prevents debt | Requires tooling and expertise |
| **Per-release** | Most teams | Balances effort and coverage | Issues may accumulate within a release |
| **Quarterly** | Small teams, early-stage products | Low overhead | Issues ship to users before being caught |

**Selected cadence:** `{{A11Y_AUDIT_CADENCE}}`

> *Default: Per-release. Rationale: catches issues before they reach users without requiring per-sprint overhead; automated tools (axe-core, Lighthouse) can run in CI for continuous basic coverage. Example: axe-core in CI catches P0 issues automatically; manual audit before each release catches nuanced issues.*

#### Audit Tools & Process

| Tool | Type | When to Run | What It Catches |
|------|------|------------|----------------|
| **axe-core** (or axe-linter) | Automated | CI pipeline, every PR | ~57% of WCAG issues: missing alt text, contrast, ARIA |
| **Lighthouse** | Automated | Pre-release | Performance + a11y scores, best practices |
| **Screen reader testing** | Manual | Per-release | Navigation flow, dynamic content announcements |
| **Keyboard navigation** | Manual | Per-feature | Focus management, tab order, keyboard traps |

#### Minimum Accessibility Requirements

| Requirement | Standard | Verify |
|------------|----------|--------|
| Color contrast | >= 4.5:1 (text), >= 3:1 (large text, UI components) | axe-core or contrast checker |
| Keyboard navigation | All interactive elements focusable and operable | Tab through entire flow |
| Focus indicators | Visible focus ring on all interactive elements | Visual inspection |
| Alt text | All informative images have descriptive alt text | axe-core |
| Form labels | All inputs have associated labels | axe-core |
| Error identification | Errors identified by text, not just color | Manual review |
| Skip navigation | Skip-to-main-content link on all pages | Keyboard test |
| ARIA landmarks | Main, nav, aside, footer landmarks present | axe-core |

---

### 9. User Research Artifacts

> How your team maintains understanding of users over time.

#### Persona Maintenance

| Artifact | Cadence | Owner | Format |
|----------|---------|-------|--------|
| **Persona documents** | Review quarterly, update after major research | Product designer | Markdown in `project/ux-research-results.md §1-§2` |
| **Problem/solution scenarios** | Update per major feature or user research round | Product designer | Markdown in `project/ux-research-results.md §3-§4` |
| **Journey maps** | Update per major feature | Product designer | Diagram in `project/product-design-as-intended.md §15` (designed) + `project/product-design-as-coded.md § Journey Maps` (implemented), or design tool |
| **Usability test reports** | Per-release (minimum) | Product designer or UX researcher | Markdown report with findings + severity |

> *Default: Quarterly persona review + per-release usability test. Rationale: personas drift as the product evolves; usability tests before release catch the highest-impact issues. Example: a 5-participant usability test using think-aloud protocol on the 3 most critical user flows.*

#### Usability Testing Conventions

| Convention | Default | Rationale | Example |
|-----------|---------|-----------|---------|
| Test method | Remote unmoderated (for speed) or moderated (for depth) | Remote unmoderated scales; moderated catches nuance | UserTesting.com or Maze for unmoderated; Zoom for moderated |
| Participants per round | 5 | Finds ~85% of usability issues (Nielsen, 2000) | 5 participants per persona for each test round |
| Severity scale | Critical / Major / Minor / Cosmetic | Prioritizes fixes by user impact | Critical = task failure; Major = significant delay; Minor = noticed but worked around |
| Task success rate target | >= 80% for primary flows | Below 80% indicates a broken flow | "Create a new project" succeeds for 4/5 participants |

---

### 10. Responsive Design Strategy

> How your application adapts across screen sizes and devices.

#### Approach

| Strategy | Best For | Pros | Cons |
|----------|----------|------|------|
| **Mobile-first** | Consumer products, content platforms | Forces prioritization, smaller initial CSS | Desktop may feel empty without enhancement |
| **Desktop-first** | Admin panels, data-heavy apps | Easier to design complex layouts first | Mobile often feels cramped as an afterthought |

**Selected approach:** `{{RESPONSIVE_APPROACH}}`

> *Default: Mobile-first. Rationale: forces content prioritization, results in better performance on constrained devices, and progressive enhancement is more robust than graceful degradation. Example: start with a single-column layout, add sidebar and multi-column at larger breakpoints.*

#### Breakpoints

| Token | Width | Target | Example |
|-------|-------|--------|---------|
| `sm` | `{{BP_SM}}` | Mobile landscape, large phones | 640px (Tailwind default) |
| `md` | `{{BP_MD}}` | Tablets, small laptops | 768px (Tailwind default) |
| `lg` | `{{BP_LG}}` | Laptops, desktops | 1024px (Tailwind default) |
| `xl` | `{{BP_XL}}` | Large desktops | 1280px (Tailwind default) |

> *Default: Tailwind CSS default breakpoints. Rationale: widely adopted, well-tested across device landscape, and consistent with the recommended CSS framework. Example: sidebar collapses to hamburger below `lg` (1024px).*

#### Responsive Conventions

| Convention | Default | Rationale | Example |
|-----------|---------|-----------|---------|
| Touch targets | Minimum 44x44px | WCAG 2.5.8 (AAA) and Apple HIG recommendation | Buttons, links, and interactive elements >= 44px tap area |
| Content reflow | Single column below `md` | Prevents horizontal scrolling on mobile | Two-column layout becomes single column on tablets |
| Image strategy | Responsive images with `srcset` | Serves appropriate resolution per device; saves bandwidth | 1x, 2x, and 3x variants for hero images |
| Font scaling | `clamp()` for fluid typography | Smooth scaling without media query breakpoints | `font-size: clamp(1rem, 2.5vw, 1.5rem)` |

---

### 11. Design System Governance

> How design decisions are documented, maintained, and evolved.

#### Token Naming Convention

| Layer | Pattern | Example |
|-------|---------|---------|
| **Primitive** | `color-{hue}-{shade}` | `color-blue-500`, `color-gray-100` |
| **Semantic** | `color-{purpose}` | `color-primary`, `color-danger`, `color-surface` |
| **Component** | `{component}-{property}-{state}` | `button-bg-hover`, `input-border-focus` |

> *Default: Three-layer token architecture (primitive > semantic > component). Rationale: primitives provide a palette, semantic tokens assign meaning, component tokens handle state -- this prevents coupling between visual design and component logic. Example: changing brand color updates `color-primary` (semantic), which cascades to all `button-bg-*` (component) tokens.*

#### Component Lifecycle

| Stage | Description | Rule |
|-------|-------------|------|
| **Draft** | Proposed, not yet reviewed | May be used in feature branches only |
| **Active** | Reviewed, documented, in production | Preferred for all new development |
| **Deprecated** | Superseded by a newer pattern | Show console warning; migration deadline set |
| **Removed** | Deleted from codebase | Must be removed from all consumers first |

#### Design System Maintenance

| Activity | Cadence | Owner | Example |
|----------|---------|-------|---------|
| Token audit | Per-release | Product designer | Verify all tokens are used; remove orphans |
| Component inventory | Quarterly | Product designer + engineer | List all components, check for duplicates or drift |
| Pattern documentation | Per new pattern | Whoever creates it | Add usage guidelines, do/don't examples |

---

## Graphic / visual design

### 1. Visual Identity

> Brand-level design decisions that inform all visual output.

#### Logo Usage

| Rule | Guideline | Example |
|------|-----------|---------|
| Primary logo | Use the full logo in headers and marketing pages | Logo in top-left of sidebar or top nav |
| Icon-only logo | Use the icon (favicon) in compact spaces | Browser tab, mobile app icon, collapsed sidebar |
| Minimum size | No smaller than 24px height for icon, 32px for full logo | Prevents illegibility at small sizes |
| Clear space | Maintain padding equal to the icon height around the logo | Logo surrounded by whitespace equal to its height |
| Background | Use on light backgrounds by default; provide a reversed variant for dark | Logo on white background; white logo on dark footer |

**Logo files location:** `{{LOGO_DIR}}`

> *Default: `{{FRONTEND_DIR}}/src/assets/logo/`. Rationale: co-located with other static assets; accessible to the build tool for optimization. Example: `logo-full.svg`, `logo-icon.svg`, `logo-reversed.svg`.*

#### Brand Voice in UI Copy

| Attribute | Default | Rationale | Example |
|-----------|---------|-----------|---------|
| Tone | Friendly, professional | Approachable without being casual; builds trust | "Your project was created" not "Awesome! Project created!" |
| Vocabulary | User's domain language | Reduces cognitive load; matches mental model | "Article" not "Content item" (for a blog platform) |
| Capitalization | Sentence case for UI labels | Easier to read; title case feels formal/dated | "Create new project" not "Create New Project" |
| Microcopy | Action-oriented, specific | Tells users what will happen | "Save and publish" not just "Submit" |
| Error tone | Empathetic, solution-oriented | Reduces frustration; focuses on recovery | "We couldn't save your changes. Try again?" not "Save failed" |

---

### 2. Minimal Viable Design System

> Generate a complete, production-ready visual foundation from three inputs: primary color, secondary color, and one font. Each derived value uses an established scale with documented rationale.

#### Inputs

| Input | Value | Example |
|-------|-------|---------|
| **Primary color** | `{{PRIMARY_COLOR}}` | `#2563eb` (blue) |
| **Secondary color** | `{{SECONDARY_COLOR}}` | `#64748b` (slate) |
| **Primary font** | `{{SANS_FONT}}` | `Inter` or system font stack |

> *Default: Primary `#2563eb`, Secondary `#64748b`, Font: system font stack (`-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`). Rationale: blue is the most universally trusted color for digital products (UsabilityHub, 2023); slate provides neutral contrast; system fonts load instantly (0ms FOIT) and match the host OS. Example: GitHub uses blue primary + gray secondary + system fonts.*

#### Derived Color Palette

Generate a full palette from the two input colors using HSL manipulation:

| Token | Derivation | Example (from #2563eb) | Usage |
|-------|-----------|----------------------|-------|
| `color-primary` | Input as-is | `#2563eb` | Primary buttons, links, active states |
| `color-primary-light` | Lightness +15% | `#60a5fa` | Hover states, light backgrounds |
| `color-primary-dark` | Lightness -15% | `#1d4ed8` | Pressed states, dark accents |
| `color-primary-50` | Lightness ~95% | `#eff6ff` | Subtle backgrounds, selected rows |
| `color-secondary` | Input as-is | `#64748b` | Secondary text, borders, icons |
| `color-secondary-light` | Lightness +15% | `#94a3b8` | Placeholder text, disabled states |
| `color-secondary-dark` | Lightness -15% | `#475569` | Body text, strong borders |
| `color-success` | Fixed: green | `#16a34a` | Success messages, positive indicators |
| `color-warning` | Fixed: amber | `#d97706` | Warnings, attention-needed states |
| `color-danger` | Fixed: red | `#dc2626` | Errors, destructive actions |
| `color-info` | Fixed: blue (lighter) | `#0ea5e9` | Informational messages, tips |
| `color-surface` | Fixed: white | `#ffffff` | Page backgrounds, card backgrounds |
| `color-surface-alt` | Fixed: near-white | `#f8fafc` | Alternate row backgrounds, subtle sections |
| `color-text` | Fixed: near-black | `#0f172a` | Primary body text |
| `color-text-muted` | Secondary color | `#64748b` | Secondary text, captions |

#### Derived Typography Scale

Based on the **Major Third** ratio (1.250). Each step multiplies by 1.25.

| Token | Size | Line Height | Weight | Usage | Example |
|-------|------|-------------|--------|-------|---------|
| `text-xs` | 0.75rem (12px) | 1rem | 400 | Captions, fine print | Timestamp on a comment |
| `text-sm` | 0.875rem (14px) | 1.25rem | 400 | Secondary text, table cells | Table row content |
| `text-base` | 1rem (16px) | 1.5rem | 400 | Body text, form labels | Paragraph text |
| `text-lg` | 1.25rem (20px) | 1.75rem | 500 | Section subheadings | Card title |
| `text-xl` | 1.563rem (25px) | 2rem | 600 | Page section titles | "Recent Projects" heading |
| `text-2xl` | 1.953rem (31px) | 2.25rem | 700 | Page titles | "Dashboard" page heading |
| `text-3xl` | 2.441rem (39px) | 2.5rem | 700 | Hero headings | Landing page headline |

> *Default: Major Third (1.250) scale. Rationale: provides clear visual hierarchy without excessive size jumps; works well for both UI-dense admin panels and content-oriented pages. Alternative scales: Minor Third (1.200) for compact UIs, Perfect Fourth (1.333) for editorial/marketing. Example: Tailwind CSS uses a similar progression.*

#### Derived Spacing Scale

Based on the **8px grid** system.

| Token | Value | Usage | Example |
|-------|-------|-------|---------|
| `space-0` | 0px | Reset | No margin/padding |
| `space-0.5` | 2px | Micro adjustments | Icon-to-text gap in small buttons |
| `space-1` | 4px | Tight spacing | Inline badge padding |
| `space-2` | 8px | Base unit | Inner padding, gap between related elements |
| `space-3` | 12px | Compact sections | List item vertical padding |
| `space-4` | 16px | Standard padding | Card inner padding, form field gap |
| `space-6` | 24px | Section spacing | Gap between form sections |
| `space-8` | 32px | Large gaps | Gap between page sections |
| `space-12` | 48px | Page margins | Side margins on desktop |
| `space-16` | 64px | Hero spacing | Vertical padding in hero sections |

> *Default: 8px base grid. Rationale: divides cleanly into halves (4px) and quarters (2px) for fine adjustments; aligns with Material Design, Apple HIG, and most design systems. 4px grids are viable but produce tighter spacing that requires more skill to use well. Example: all padding, margin, and gap values are multiples of 8px.*

---

### 3. Color System

> Full color system specifications, extending the minimal viable palette.

#### Semantic Color Tokens

| Token | Light Mode | Dark Mode | Usage |
|-------|-----------|-----------|-------|
| `--color-bg` | `#ffffff` | `#0f172a` | Page background |
| `--color-bg-alt` | `#f8fafc` | `#1e293b` | Card/section background |
| `--color-bg-hover` | `#f1f5f9` | `#334155` | Hover background |
| `--color-text` | `#0f172a` | `#f8fafc` | Primary text |
| `--color-text-muted` | `#64748b` | `#94a3b8` | Secondary text |
| `--color-border` | `#e2e8f0` | `#334155` | Default borders |
| `--color-border-strong` | `#cbd5e1` | `#475569` | Emphasized borders |
| `--color-focus-ring` | `{{PRIMARY_COLOR}}` | `{{PRIMARY_COLOR}}` | Focus indicators (a11y) |

**Dark mode support:** `{{DARK_MODE}}`

> *Default: No (ship light mode first). Rationale: dark mode doubles the design surface area; ship light-only for MVP, add dark mode as an enhancement. Prepare by using semantic tokens (not hardcoded colors) from day one. Example: use `var(--color-bg)` instead of `#ffffff` so dark mode is a token swap, not a rewrite.*

#### Color Accessibility

| Rule | Requirement | Tool |
|------|-------------|------|
| Text contrast (AA) | >= 4.5:1 for normal text, >= 3:1 for large text | WebAIM contrast checker |
| UI component contrast (AA) | >= 3:1 for borders, icons, and interactive elements | axe-core |
| Don't rely on color alone | Use icons, text, or patterns alongside color | Manual review |
| Color-blind safe | Test with Deuteranopia and Protanopia simulators | Chrome DevTools > Rendering |

---

### 4. Typography System

> Comprehensive typography specifications extending the minimal viable scale.

#### Font Stack

| Role | Font | Fallback | Usage | Example |
|------|------|----------|-------|---------|
| **Sans (UI)** | `{{SANS_FONT}}` | `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif` | All UI elements | Buttons, labels, navigation |
| **Serif (Content)** | `{{SERIF_FONT}}` | `Georgia, 'Times New Roman', serif` | Long-form content (optional) | Blog posts, articles |
| **Mono (Code)** | `{{MONO_FONT}}` | `'Fira Code', 'Cascadia Code', 'JetBrains Mono', monospace` | Code blocks, technical data | API keys, code snippets |

> *Default: System font stack for sans (no web font download = fastest load); no serif or mono unless needed. Rationale: system fonts render at 0ms (no FOIT/FOUT), match the host OS, and are optimized for screen reading. Add a custom font only if brand identity requires it. Example: GitHub uses system fonts; Medium uses a custom serif for content.*

#### Typography Conventions

| Convention | Default | Rationale | Example |
|-----------|---------|-----------|---------|
| Base font size | 16px (`1rem`) | Browser default; readable on all devices; scales with user preferences | Body text at 16px |
| Line height (body) | 1.5 | Optimal readability for body text (WCAG SC 1.4.12) | 16px text with 24px line height |
| Line height (headings) | 1.2-1.3 | Tighter for larger text; prevents excessive whitespace | 32px heading with 38px line height |
| Max line length | 65-75 characters | Optimal reading speed (Baymard, 2024) | `max-width: 65ch` on content containers |
| Paragraph spacing | 1em (equal to font size) | Clear separation without excessive gaps | 16px gap between paragraphs |
| Font weight range | 400 (regular), 500 (medium), 600 (semibold), 700 (bold) | Four weights cover all UI needs without bloating font downloads | Regular for body, medium for labels, semibold for subheadings, bold for headings |

---

### 5. Iconography

> Icon set selection, sizing, and usage conventions.

#### Icon Set

| Option | Style | Size | License | Pros | Cons |
|--------|-------|------|---------|------|------|
| **Lucide** | Outlined, 24px grid | 1.2KB avg | ISC (free) | Clean, consistent, 1500+ icons, active community | Outline-only (no filled variant) |
| **Heroicons** | Outlined + Solid, 24px grid | 1KB avg | MIT (free) | Tailwind team, outline + solid variants, clean | ~300 icons (may need supplementing) |
| **Phosphor** | 6 weights, 24px grid | 1.5KB avg | MIT (free) | Most versatile (thin to bold), 7000+ icons | Larger set can be overwhelming |
| **Material Symbols** | Variable weight/grade, 24px grid | 2KB avg | Apache 2.0 (free) | Largest set (2500+), variable font, Google-maintained | Can feel generic/Googley |

**Selected icon set:** `{{ICON_SET}}`

> *Default: Lucide. Rationale: best balance of quality, consistency, size, and availability; pairs well with Tailwind CSS and React; active maintenance. Example: Lucide's `<Plus />`, `<Search />`, `<Settings />` icons in a sidebar.*

#### Icon Sizing

| Token | Size | Usage | Example |
|-------|------|-------|---------|
| `icon-xs` | 12px | Inline indicators | Status dot next to a username |
| `icon-sm` | 16px | Inside buttons, table cells | Edit icon in a table action column |
| `icon-md` | 20px | Navigation items, form icons | Sidebar nav icons |
| `icon-lg` | 24px | Page headers, standalone actions | Page title icon |
| `icon-xl` | 32px | Empty states, feature highlights | Empty state illustration accent |

#### Icon Conventions

| Convention | Default | Rationale | Example |
|-----------|---------|-----------|---------|
| Stroke weight | 1.5px (for 24px grid) | Matches Lucide/Heroicons default; visible without being heavy | Consistent stroke across all icons |
| Color | Inherit from text color | Icons should match surrounding text for visual harmony | `currentColor` in SVG |
| Interactive icons | Always paired with text label or tooltip | Icons alone fail recognition tests (NNGroup, 2023) | Trash icon + "Delete" label; or trash icon + tooltip "Delete" |
| Decorative vs. informative | Decorative: `aria-hidden="true"`; Informative: `aria-label` | Screen readers should announce informative icons, skip decorative ones | Star icon as rating: `aria-label="4 out of 5 stars"` |

---

### 6. Component Visual Specifications

> Default visual properties for common UI components.

#### Border Radius

| Style | Value | Best For | Example |
|-------|-------|----------|---------|
| **Sharp** | 0-2px | Data-dense UIs, tables, enterprise tools | `border-radius: 2px` |
| **Soft** | 4-8px | Most applications, balanced feel | `border-radius: 6px` |
| **Round** | 12-16px | Friendly, consumer-facing products | `border-radius: 12px` |
| **Pill** | 9999px | Tags, badges, toggle buttons | `border-radius: 9999px` |

**Selected style:** `{{BORDER_RADIUS_STYLE}}`

> *Default: Soft (6px). Rationale: professional yet approachable; works across all component types; aligns with modern design trends (2024-2026) which favor subtle rounding over sharp edges or excessive rounding. Example: Tailwind's `rounded-md` (6px) is the most commonly used radius.*

#### Radius Tokens

| Token | Value | Usage | Example |
|-------|-------|-------|---------|
| `radius-none` | 0px | Tables, code blocks | Flat-edged data table |
| `radius-sm` | 2px | Small elements, tags | Inline code badge |
| `radius-md` | `{{BORDER_RADIUS}}` | Buttons, cards, inputs | Primary button |
| `radius-lg` | `{{BORDER_RADIUS}}` * 2 | Modals, dialogs | Modal container |
| `radius-full` | 9999px | Avatars, pills, toggles | User avatar circle |

> *Default: `radius-md` = 6px, `radius-lg` = 12px. Example: buttons use `radius-md`, modals use `radius-lg`, avatars use `radius-full`.*

#### Shadows

| Style | Use Case | Value | Example |
|-------|----------|-------|---------|
| **Flat** | Minimalist designs, inside cards | None (`box-shadow: none`) | Flat design with border-only cards |
| **Subtle** | Most applications | `0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06)` | Light shadow on cards |
| **Elevated** | Dropdowns, popovers, modals | `0 10px 15px rgba(0,0,0,0.1), 0 4px 6px rgba(0,0,0,0.05)` | Floating dropdown menu |

**Selected style:** `{{SHADOW_STYLE}}`

> *Default: Subtle. Rationale: provides depth cues without visual heaviness; works in both light and dark modes (adjust opacity for dark). Example: Tailwind's `shadow-sm` on cards, `shadow-lg` on dropdowns.*

#### Shadow Tokens

| Token | Value | Usage | Example |
|-------|-------|-------|---------|
| `shadow-none` | `none` | Flat elements, pressed states | Pressed button |
| `shadow-sm` | `0 1px 2px rgba(0,0,0,0.05)` | Subtle lift: buttons, inputs | Input field focus state |
| `shadow-md` | `0 4px 6px rgba(0,0,0,0.07), 0 2px 4px rgba(0,0,0,0.06)` | Cards, sections | Content card |
| `shadow-lg` | `0 10px 15px rgba(0,0,0,0.1), 0 4px 6px rgba(0,0,0,0.05)` | Dropdowns, popovers | Autocomplete dropdown |
| `shadow-xl` | `0 20px 25px rgba(0,0,0,0.1), 0 8px 10px rgba(0,0,0,0.04)` | Modals, dialogs | Modal overlay |

#### Transitions

| Token | Value | Usage | Example |
|-------|-------|-------|---------|
| `transition-fast` | `150ms ease-in-out` | Hover states, toggles | Button hover background change |
| `transition-normal` | `200ms ease-in-out` | Expanding sections, tooltips | Accordion open/close |
| `transition-slow` | `300ms ease-in-out` | Modals, page transitions | Modal fade-in |

> *Default: ease-in-out easing for all transitions. Rationale: natural-feeling acceleration/deceleration; `ease` front-loads speed (feels snappy but abrupt); `linear` feels mechanical. Example: `transition: background-color 150ms ease-in-out` on buttons.*

---

### 7. Image & Illustration Guidelines

> How images, illustrations, and media are handled in the application.

#### Image Conventions

| Convention | Default | Rationale | Example |
|-----------|---------|-----------|---------|
| Format | WebP with JPEG fallback | WebP is 25-35% smaller than JPEG at equivalent quality; supported by all modern browsers | `<picture><source type="image/webp"><img src="fallback.jpg"></picture>` |
| Lazy loading | All images below the fold | Reduces initial page load; native `loading="lazy"` has broad support | `<img loading="lazy" ...>` |
| Aspect ratios | 16:9 (hero), 1:1 (avatar), 4:3 (card thumbnail) | Consistent aspect ratios prevent layout shift | `aspect-ratio: 16/9` CSS property |
| Placeholder strategy | Blurred low-res placeholder (LQIP) or solid color | Prevents layout shift (CLS); provides visual continuity during load | 20px blurred thumbnail inline as base64 |
| Alt text | Required for all informative images; empty for decorative | WCAG 1.1.1; screen readers need descriptions | `alt="Team photo showing 5 members at the office"` |
| Max file size | 200KB for thumbnails, 500KB for hero images | Keeps page weight reasonable for mobile users | Compress with tools like Squoosh or sharp |

#### Illustration Style

| Attribute | Default | Rationale | Example |
|-----------|---------|-----------|---------|
| Style | Flat vector with brand colors | Consistent with modern UI; scalable; small file size | SVG illustrations using primary and secondary colors |
| Usage | Empty states, onboarding, error pages | Adds warmth to functional screens; reduces anxiety on error/empty states | Illustration of a person searching on 404 page |
| Source | Open-source sets or custom | unDraw.co (free, customizable colors), Storyset, or custom illustrations | unDraw illustration recolored to match brand |

---

### 8. Motion & Animation Principles

> How motion is used to enhance (not distract from) the user experience.

#### Motion Level

| Level | Description | Best For | Example |
|-------|-------------|----------|---------|
| **None** | No animations; instant state changes | Accessibility-first, enterprise tools, `prefers-reduced-motion` | All transitions are instant |
| **Subtle** | Micro-animations for feedback and transitions | Most applications | Hover color change (150ms), modal fade (200ms) |
| **Expressive** | Rich animations for delight and storytelling | Consumer products, onboarding flows | Confetti on milestone completion, bouncy button press |

**Selected level:** `{{MOTION_LEVEL}}`

> *Default: Subtle. Rationale: provides functional feedback (confirms actions, guides attention) without being distracting; respects `prefers-reduced-motion` by reducing to None automatically. Example: button hover transitions (subtle) vs. page-load animations (expressive, usually unnecessary).*

#### Motion Conventions

| Convention | Default | Rationale | Example |
|-----------|---------|-----------|---------|
| Easing | `ease-in-out` | Natural-feeling motion; objects accelerate and decelerate | `transition: all 200ms ease-in-out` |
| Duration (micro) | 100-150ms | Fast enough to feel instant; slow enough to be perceived | Button hover, toggle switch |
| Duration (small) | 200-300ms | Expandable sections, tooltips | Accordion open, dropdown appear |
| Duration (large) | 300-500ms | Modals, page transitions | Modal fade-in, route transition |
| `prefers-reduced-motion` | Respect always; reduce to instant | Required for accessibility; some users experience motion sickness | `@media (prefers-reduced-motion: reduce) { * { transition-duration: 0.01ms !important; } }` |
| Entrance animations | Fade-in or slide-in from natural direction | Elements should appear from where they logically originate | Dropdown slides down from trigger; sidebar slides in from left |
| Exit animations | Faster than entrance (80% of entrance duration) | Exiting elements should leave quickly to not block the user | Modal fade-out at 160ms (vs. 200ms fade-in) |
| Loading animations | Skeleton shimmer or pulsing dot | Indicates activity without demanding attention | Skeleton with left-to-right shimmer gradient |

#### Duration Tokens

| Token | Value | Usage | Example |
|-------|-------|-------|---------|
| `duration-instant` | 0ms | Immediate state changes, reduced motion fallback | Color change on toggle |
| `duration-fast` | 100ms | Micro-interactions: hover, focus, toggle | Button background on hover |
| `duration-normal` | 200ms | Standard transitions: dropdowns, tooltips, accordions | Dropdown menu appearing |
| `duration-slow` | 300ms | Large transitions: modals, drawers, page transitions | Modal overlay fade-in |
| `duration-slower` | 500ms | Emphasis animations: onboarding, celebration | Confetti animation on milestone |
