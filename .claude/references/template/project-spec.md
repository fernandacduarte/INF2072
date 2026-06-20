---
designer_description: "I'm the quickstart spec your project fills in once -- name, mode, team, domain description, stack choices, UX and graphic defaults -- so /design can instantiate the full set of project references from one coherent set of answers instead of walking you through the long-form questionnaire section by section."
---

<!-- Quickstart Spec v2 -- Generated {datetime} -->
<!-- Fill in your choices below. Leave blank to use defaults. -->
<!-- After filling, run /design <spec-file-path> to apply it. -->
<!-- For the full questionnaire with detailed descriptions, see template/questionnaire.md -->
<!-- Knowledge Tiers: T1 (Product & Design) = you fill; T2 (Architecture) = accept defaults or customize; T3 (Engineering) = auto-generated -->
version: 2

## Project
<!-- Required fields -- the agent will ask if these are missing. -->
- name:
- description:

## Project Mode
<!-- Is this a new project or an existing one with code already written?
     greenfield: new project, no existing code
     brownfield: existing project with code, users, and constraints
     Default: greenfield. -->
- mode:

<!-- Who is available on your team? Comma-separated list.
     Options: just-me, architect, engineers, ux-designer, ui-designer, data-engineer, testers
     Default: just-me. Solo designers get recommended defaults for all T2/T3 sections. -->
- team:

<!-- BROWNFIELD ONLY: Fill these if mode is brownfield. Leave blank for greenfield. -->
<!-- Existing tech stack (languages, frameworks, database, hosting). -->
- existing_tech_stack:
<!-- Migration constraints (e.g., cannot change database, must support existing API clients). -->
- migration_constraints:
<!-- Approximate number of active users. -->
- current_user_base:
<!-- Top 3 pain points with the current system. -->
- legacy_pain_points:
<!-- URL or description of existing design system / style guide. Leave blank if none. -->
- existing_design_system:

## Domain
<!-- Describe your conceptual design here. This section is free-form.
     You may provide a free-form metacommunication message.
     Otherwise, include:
     - What your platform does, who it's for, what problem it solves
     - Design philosophy or methodology (if any)
     - Main entities and their hierarchy (e.g., Organization > Project > Task > Comment)
     - For each entity: what it represents, visibility rules, ownership, soft delete (yes/no)
     - Domain-specific concepts (workflows, scoring, annotations, approval chains)
     - Permission model: system-level roles and resource-level access
     - Content authoring: how authorship is tracked, mentions/notifications
     - Target user community: language, geography, domain expertise
     - Validation constants: field limits with domain rationale

     You can use prose, bullet lists, tables, or any Markdown format.
     The agent will use this to populate project/product-design-as-coded.md § Conceptual Design
     and project/product-design-as-intended.md. -->


## Source Directories
<!-- Common values: backend, server, api, src (backend); frontend, client, web, src (frontend). -->
<!-- Defaults: backend=backend, frontend=frontend, output_dir=_output -->
- backend:
- frontend:
- output_dir:
<!-- Additional source directories (optional, one per line):
- mobile:
- shared:
-->

## Backend
<!-- Framework: Flask | Django | FastAPI | Express/NestJS
     Flask: Lightweight, flexible, easy to learn, large ecosystem (RECOMMENDED for small-to-medium APIs)
     Django: Batteries-included (ORM, admin, auth, migrations), mature — good for data-heavy apps
     FastAPI: Async, auto-generated docs, Pydantic validation — good for high-throughput APIs
     Express/NestJS: JavaScript/TypeScript fullstack — good for TypeScript fullstack teams
     Write "none" if your project has no backend. -->
- framework:

<!-- ORM: SQLAlchemy | Django ORM | Prisma | TypeORM/Drizzle
     SQLAlchemy: Most powerful Python ORM, flexible, supports raw SQL (RECOMMENDED for Flask/FastAPI)
     Django ORM: Integrated with Django, simple, great migrations — use with Django
     Prisma: Type-safe, great DX, auto-generated client — use with Express/NestJS
     TypeORM/Drizzle: TypeScript-native — use with NestJS
     Default: inferred from framework. -->
- orm:

<!-- Database: PostgreSQL | MySQL/MariaDB | SQLite | MongoDB
     PostgreSQL: Feature-rich, JSONB, full-text search, rock-solid (RECOMMENDED for production)
     MySQL/MariaDB: Wide hosting support, familiar
     SQLite: Zero setup, embedded — good for prototyping and unit tests only
     MongoDB: Flexible schema, horizontal scaling — good for document-centric apps
     Default: PostgreSQL. -->
- database:

<!-- Migration tool: Alembic | Django Migrations | Prisma Migrate | Manual SQL
     Alembic: SQLAlchemy-native, auto-generates from models (RECOMMENDED with SQLAlchemy)
     Django Migrations: Auto-generated, integrated — use with Django
     Prisma Migrate: Type-safe, declarative schema — use with Prisma
     Default: inferred from ORM. -->
- migrations:

<!-- Validation: Marshmallow | Pydantic | Django Forms/Serializers | Zod/Joi
     Marshmallow: Mature, flexible, great with Flask/SQLAlchemy (RECOMMENDED for Flask)
     Pydantic: Built into FastAPI, Python type hints — use with FastAPI
     Django Forms/Serializers: Integrated, DRF serializers are powerful — use with Django
     Zod/Joi: TypeScript/JavaScript-native, composable — use with Express/NestJS
     Default: inferred from framework. -->
- validation:

<!-- Authentication: JWT (HttpOnly cookies) | JWT (localStorage) | Session-based | OAuth2/OIDC
     JWT (HttpOnly cookies): Stateless, scalable, secure cookie storage (RECOMMENDED for SPAs)
     JWT (localStorage): Simple but XSS-vulnerable — not recommended for production
     Session-based: Simple, built into most frameworks — good for server-rendered apps
     OAuth2/OIDC: Delegated auth, social login — good for identity provider integration
     Default: JWT (HttpOnly cookies). -->
- auth:

<!-- Token expiry times (if using JWT). Defaults: access=1 hour, refresh=7 days. -->
- access_token_expiry:
- refresh_token_expiry:

<!-- Default API rate limit. Default: 200/minute. -->
- rate_limit:

<!-- File uploads: yes/no. If yes, specify size limit and allowed formats. -->
- file_uploads:

<!-- Import/export support: list formats (e.g., PDF, XML, Markdown, JSON, BibTeX) or leave blank. -->
- import_export:

## Frontend
<!-- Framework: React | Vue | Svelte/SvelteKit | Angular
     React: Largest ecosystem, most libraries/tooling, strong hiring pool (RECOMMENDED)
     Vue: Gentler learning curve, good docs, built-in reactivity
     Svelte/SvelteKit: Minimal boilerplate, compiled output, smaller bundles
     Angular: Full-featured, TypeScript-first, built-in routing/forms/DI
     Write "none" if your project has no frontend. -->
- framework:

<!-- Build tool: Vite | Next.js | Webpack
     Vite: Fastest dev server, native ESM, great plugins (RECOMMENDED for new projects)
     Next.js: SSR/SSG built-in, file-based routing — best if you need SSR/SSG
     Webpack: Most mature, handles any edge case — only for existing Webpack projects
     Default: Vite. -->
- build_tool:

<!-- CSS: Tailwind CSS | CSS Modules | styled-components | Plain CSS/SCSS
     Tailwind CSS: Utility-first, fast prototyping, consistent design (RECOMMENDED)
     CSS Modules: Scoped styles, familiar CSS syntax, no runtime cost
     styled-components: CSS-in-JS, dynamic styling, co-located with components
     Plain CSS/SCSS: No dependencies, full control — only for very small projects
     Default: Tailwind CSS. -->
- css:

<!-- State management: React Context + hooks | Zustand | Redux Toolkit | Jotai/Recoil
     React Context + hooks: No extra dependencies, built into React (RECOMMENDED for <10 global values)
     Zustand: Tiny (1KB), simple API, good devtools — good for medium complexity
     Redux Toolkit: Mature, excellent devtools — good for large apps with complex state
     Jotai/Recoil: Atomic state model, fine-grained reactivity
     Default: React Context + hooks. -->
- state:

<!-- Data fetching: TanStack Query | SWR | Manual (useEffect + fetch)
     TanStack Query: Automatic caching, background refetch, optimistic updates (RECOMMENDED)
     SWR: Simpler API, Vercel-maintained — good for simpler needs
     Manual: No dependencies, full control — only for very simple apps
     Default: TanStack Query. -->
- data_fetching:

<!-- HTTP client: Axios | fetch (native) | ky
     Axios: Interceptors, request/response transforms, wide adoption (RECOMMENDED)
     fetch (native): Zero dependencies, built into all browsers
     ky: Tiny (3KB), modern fetch wrapper, retries
     Default: Axios. -->
- http_client:

<!-- Rich text editor: Lexical | TipTap | Quill | none
     Lexical: Meta-maintained, extensible, good React support (RECOMMENDED if needed)
     TipTap: Great DX, extensive extensions, ProseMirror-based
     Quill: Simple setup, good for basic rich text
     Default: none (omitted). -->
- rich_text_editor:

<!-- Router (if React): React Router v7 | TanStack Router
     React Router v7: Most mature, large ecosystem (RECOMMENDED)
     TanStack Router: Type-safe, search params validation
     Default: React Router v7. -->
- router:

### Design Choices
<!-- Colors, fonts, dark mode, and WCAG level have moved to the "Graphic / UI Design" and "UX Design" sections below. -->
<!-- These remaining fields are frontend-framework-specific. -->

<!-- Context providers: list names and purposes (optional).
     Example: Auth (user session), Theme (dark/light), Notifications -->
- context_providers:

<!-- Reusable components to start with (optional).
     Common: AlertMessage, Modal, DoubleConfirmationModal, Toast, Breadcrumb, ErrorBoundary -->
- initial_components:

## UX Design
<!-- [T1 -- Product & Design] These choices shape how users interact with your product. -->
<!-- Solo designers: accept defaults or customize. -->

<!-- App type: crud-admin | content-platform | marketplace | dashboard | social-community
     crud-admin: Data management with lists, forms, detail views (RECOMMENDED default)
     content-platform: Publishing, reading, discussion
     marketplace: Browse, compare, transact
     dashboard: Data visualization, monitoring
     social-community: Profiles, feeds, messaging
     Default: crud-admin. Rationale: most common archetype; well-understood interaction vocabulary. -->
- app_type:

<!-- Primary navigation: sidebar | top-nav | bottom-nav | hamburger
     sidebar: Always visible, supports hierarchy, works for 5+ sections (RECOMMENDED)
     top-nav: Clean layout, familiar, good for 3-5 sections
     bottom-nav: Thumb-friendly on mobile, max 5 items
     hamburger: Saves space but hides navigation
     Default: sidebar. Rationale: accommodates growth, persistent wayfinding. -->
- navigation:

<!-- Form validation: inline-validation | on-submit | progressive
     inline-validation: Immediate feedback on blur, fewer submission errors (RECOMMENDED)
     on-submit: Less noise during entry, batch error display
     progressive: Step-by-step, reduces cognitive load for complex forms
     Default: inline-validation. Rationale: reduces submission errors by ~22% (Baymard, 2024). -->
- form_pattern:

<!-- Empty state strategy: action-prompt | illustration | text-only
     action-prompt: Guides first action for primary entities (RECOMMENDED for primary)
     illustration: Friendly, reduces anxiety for secondary views
     text-only: Lightweight for minor sections
     Default: action-prompt. Rationale: first-use experience drives retention. -->
- empty_states:

<!-- Error display: toast | inline | full-page
     toast: Non-blocking, auto-dismiss, good for transient errors
     inline: Below field, closest to error source (RECOMMENDED for validation)
     full-page: For unrecoverable errors (404, 500)
     Default: inline for validation, toast for network errors, full-page for system errors. -->
- error_handling:

<!-- WCAG level: AA | AAA
     AA: Industry standard, achievable (RECOMMENDED minimum)
     AAA: Best accessibility -- recommended for public/education platforms
     Default: AA. -->
- wcag:

<!-- Accessibility audit cadence: per-sprint | per-release | quarterly
     per-release: Balances effort and coverage (RECOMMENDED)
     per-sprint: Best coverage but requires dedicated resources
     quarterly: Low overhead but issues ship to users
     Default: per-release. Rationale: catches issues before release; axe-core in CI for continuous basic coverage. -->
- a11y_audit_cadence:

<!-- Responsive approach: mobile-first | desktop-first
     mobile-first: Forces prioritization, better performance (RECOMMENDED)
     desktop-first: Easier for complex layouts, good for admin-only tools
     Default: mobile-first. Rationale: progressive enhancement is more robust than graceful degradation. -->
- breakpoints:

## Graphic / UI Design
<!-- [T1 -- Product & Design] Visual identity and design system foundations. -->
<!-- Minimal viable path: fill primary_color, secondary_color, and sans_font only. -->
<!-- All other values will be derived from established design scales. -->

<!-- Brand colors: hex values.
     Example: #2563eb (blue), #64748b (slate)
     Default: primary=#2563eb, secondary=#64748b. Rationale: blue is universally trusted; slate provides neutral contrast. -->
- primary_color:
- secondary_color:
- accent_color:

<!-- Fonts: provide font family names.
     system: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif (RECOMMENDED -- 0ms load)
     Inter: Designed for screens, excellent readability, free (~100KB download)
     Custom: Maximum brand differentiation but adds load time
     Default: system font stack. Rationale: instant rendering, matches host OS. -->
- sans_font:
- serif_font:
- mono_font:

<!-- Typography scale: minor-third (1.200) | major-third (1.250) | perfect-fourth (1.333)
     minor-third: Compact, data-dense UIs
     major-third: Balanced hierarchy, most applications (RECOMMENDED)
     perfect-fourth: Dramatic, editorial/marketing
     Default: major-third. Rationale: clear hierarchy without excessive size jumps. -->
- type_scale:

<!-- Base spacing unit: 4px | 8px
     8px: Divides cleanly (4px, 2px), aligns with Material Design and Apple HIG (RECOMMENDED)
     4px: Finer control for data-dense UIs
     Default: 8px. Rationale: most widely adopted grid system. -->
- spacing_unit:

<!-- Border radius style: sharp (0-2px) | soft (4-8px) | round (12-16px) | pill (9999px)
     sharp: Data-dense, enterprise
     soft: Balanced, modern (RECOMMENDED)
     round: Friendly, consumer-facing
     pill: Tags, badges, toggles
     Default: soft. Rationale: professional yet approachable; aligns with 2024-2026 design trends. -->
- border_radius:

<!-- Shadow style: flat | subtle | elevated
     flat: Minimalist, border-based depth
     subtle: Light shadows on cards and dropdowns (RECOMMENDED)
     elevated: Material-inspired layered depth
     Default: subtle. Rationale: depth cues without visual heaviness. -->
- shadow_style:

<!-- Motion level: none | subtle | expressive
     none: Instant state changes, accessibility-first
     subtle: Micro-animations for feedback and transitions (RECOMMENDED)
     expressive: Rich animations for delight and storytelling
     Default: subtle. Rationale: functional feedback without distraction; respects prefers-reduced-motion. -->
- motion:

<!-- Icon set: lucide | heroicons | phosphor | material-symbols
     lucide: Clean, 1500+ icons, active community, ISC license (RECOMMENDED)
     heroicons: Tailwind team, outline + solid, 300+ icons
     phosphor: 6 weights, 7000+ icons, most versatile
     material-symbols: Largest set (2500+), variable font
     Default: lucide. Rationale: best balance of quality, consistency, and availability. -->
- icon_set:

<!-- Dark mode: yes | no | later
     no: Ship light mode first, half the design surface (RECOMMENDED for MVP)
     yes: User preference, reduces eye strain, doubles design work
     later: Ship light first but use semantic tokens from day one
     Default: no. Rationale: ship faster; add dark mode as enhancement. -->
- dark_mode:

## i18n
<!-- Primary UI locale (RFC 5646). Default: en-US. -->
- primary_locale:

<!-- Secondary locale (RFC 5646). Leave blank if monolingual. -->
- secondary_locale:

<!-- Backend default locale for error messages. Default: en-US. -->
- backend_default_locale:

<!-- Localized emails: yes | no. Default: no. -->
- localized_emails:

<!-- Entities with database-stored translations (optional).
     Example: Category (name), Tag (label) -->
- translatable_entities:

## Testing
<!-- Backend test framework: pytest | unittest | Jest
     pytest: Powerful fixtures, plugins, parametrize (RECOMMENDED for Python)
     unittest: Built into Python, no extra dependency
     Jest: Built-in mocking, snapshots — use with Express/NestJS
     Default: inferred from backend framework. -->
- backend_test:

<!-- Frontend test framework: Vitest | Jest
     Vitest: Vite-native, fast, Jest-compatible API (RECOMMENDED with Vite)
     Jest: Most mature, largest ecosystem — good for Webpack projects
     Default: inferred from build tool. -->
- frontend_test:

<!-- E2E test framework: Playwright | Cypress | none
     Playwright: Multi-browser, auto-wait, codegen (RECOMMENDED)
     Cypress: Great DX, time-travel debugging
     Default: Playwright. -->
- e2e:

<!-- Integration test suite against real database: yes | no. Default: yes. -->
- integration_suite:

<!-- E2E base URL. Default: http://localhost:3000. -->
- e2e_base_url:


## Security
<!-- List validation constants if known. Leave blank for defaults.
     Format: field: min-max (rationale)
     Example:
     - login_length: 3-20 (short academic identifiers)
     - password_min: 8
     - name_max: 50 (full names)
     - title_max: 200 (descriptive titles)

     Also note:
     - Where validation constants are defined (backend/frontend paths)
     - Which security checklists (A-N) don't apply to your project
     - Any project-specific security requirements (compliance, data residency, audit logging) -->
