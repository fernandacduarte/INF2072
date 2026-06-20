**What it does**: Creates a personalized onboarding plan based on role and experience level. Covers what to learn, in what order, and where to find things. Use it to onboard a new teammate -- or yourself, if you are new to the toolkit or the project.

Three role families and three expertise levels:

| Role family | Aliases | Focus |
|-------------|---------|-------|
| Builder (BLD) | `builder`, `BLD` | Engineers -- code, architecture, testing |
| Shaper (SHP) | `shaper`, `SHP` | Designers, PMs -- product, UX, strategy |
| Guardian (GRD) | `guardian`, `GRD` | QA, security, ops -- quality, reliability |

| Level | Aliases | Profile |
|-------|---------|---------|
| L1 | `contributor`, `junior`, `mid` | New to the role or project |
| L2 | `expert`, `senior` | Experienced practitioner |
| L3 | `leader`, `staff`, `lead` | Technical leader or architect |

**Examples**:
> `/onboard shaper L2 Alice --area frontend`
> Generates a 30-60-90 day onboarding plan for a mid-level product designer focused on the frontend.

> `/onboard builder L1 --area backend`
> Starter onboarding plan for a newcomer in an engineering role, focused on backend.

> `/onboard guardian L3`
> Leadership-level onboarding plan for a QA/security/ops lead.

> `/onboard --all`
> Generates onboarding plans for all 9 role-level combinations (3 roles x 3 levels) in parallel.

> `/onboard --all-levels shaper`
> Generates plans for L1, L2, and L3 of the shaper role family (3 plans).

> `/onboard --all-roles L2`
> Generates plans for builder, shaper, and guardian at L2 (3 plans).

> `/onboard --batch "builder L1 Alice; shaper L2 Bob --area frontend"`
> Generates multiple plans in parallel from semicolon-separated specs.

> `/onboard builder L2 --format md`
> Produces the onboarding plan in Markdown only (skips HTML generation).

**When to use**: A new team member is joining and you want a structured, role-appropriate onboarding experience rather than ad-hoc knowledge transfer. Also useful when *you* are the newcomer and want a clear learning path into the project and the toolkit.

**Not for**: stakeholder updates (use `/communicate`) or API/architecture documentation (use `/document`). See `docs/how-to/which-communicative-skill.md` for the audience routing table.

**Next step**: `/communicate` -- want to generate stakeholder material as well?

**References**: Role-family and expertise-level templates live in [.claude/references/general/onboarding/](../../../.claude/references/general/onboarding/). Edit those files to update per-role learning paths, reading lists, or milestone checkpoints.

**Terminology note**: Output artifacts retain the `onboarding-NNN` prefix and live in `_output/onboarding-plans/` for ID and link continuity.
