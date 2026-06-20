---
designer_description: "When you onboard a new team member, I'm the reference that defines the role-family and expertise-level matrix -- Builders / Shapers / Guardians crossed with Contributor / Expert / Leader -- and the four progressive disclosure layers the /onboard skill assembles into a plan tailored to who they are and what they need to become productive."
---

# HARNESS - ONBOARDING

> Role- and level-aware onboarding framework: 4-layer progressive disclosure across role families and expertise tiers.

---

## How to Use

Determine the member's **role family** and **expertise level**, then load the matching files. `/onboard` automates this.

### Determining Role Family

One (occasionally two) role families per member; cross-functional roles load both files.

| Tag | Name | File | Description |
|-----|------|------|-------------|
| BLD | Builders | [builders.md](onboarding/builders.md) | Write, deploy, and maintain code -- developers, DevOps, infra engineers |
| SHP | Shapers | [shapers.md](onboarding/shapers.md) | Define what gets built and how -- product managers, designers, data analysts |
| GRD | Guardians | [guardians.md](onboarding/guardians.md) | Ensure quality and alignment -- QA, security engineers, tech leads, engineering managers |

### Determining Expertise Level

Three bands consolidate the original 5-level Dreyfus taxonomy (advisory-000314): guided contributor, independent expert, organizational leader.

| Tag | Name | File | Characteristics |
|-----|------|------|-----------------|
| L1 | Contributor | [l1-contributor.md](onboarding/l1-contributor.md) | Junior to mid-level IC (0-5 years); needs guidance on *how*, *what*, and *where* |
| L2 | Expert | [l2-expert.md](onboarding/l2-expert.md) | Senior (5-10 years); needs context on *why* and *trade-offs* |
| L3 | Leader | [l3-leader.md](onboarding/l3-leader.md) | Staff/Principal/Manager (10+ years); needs *organizational context* and *team dynamics* |

### Onboarding Layers

| Layer | Name | Audience | Timing |
|-------|------|----------|--------|
| **0** | Universal Foundation | All roles, all levels | Day 1 |
| **1** | Role-Specific Context | By role family | Week 1 |
| **2** | Level-Specific Depth | By expertise level | Weeks 1-4 |
| **3** | Living Knowledge | All roles (ongoing) | 30-60-90 days and beyond |

### Loading Strategy

Layer 0 is embedded in the skill. Load the role family file(s) for Layer 1 and the level file for Layer 2. Layer 3 is generated dynamically from project state (briefs, ADRs, plans).

### Role-Level Shortcuts

| Scenario | Role | Level | Key Focus |
|----------|------|-------|-----------|
| Junior frontend dev | BLD | L1 | Guided tutorial, pair programming, code review receiving |
| Mid-level backend dev | BLD | L1 | Project conventions, architecture boundaries, independent features |
| Senior backend dev | BLD | L2 | Architecture decisions, system design rationale, technical debt |
| New product manager | SHP | L1 | Domain context, user research, roadmap, metrics |
| New QA engineer | GRD | L1 | Test strategy, coverage expectations, review perspective framework |
| Tech lead joining | BLD+GRD | L3 | Team dynamics, process ownership, cross-team dependencies |
| Designer with AI tools | SHP+BLD | L1 | Conceptual design, AI-assisted workflow, metacommunication |

---

## Onboarding KPIs

Effectiveness metrics (aligned with DX P1/P3):

| Metric | Target | Measured At |
|--------|--------|-------------|
| Time-to-environment-setup | < 30 minutes | Day 1 |
| Time-to-first-commit | < 1 week | Week 1 |
| Time-to-first-review | < 2 weeks | Week 2 |
| Time-to-independent-contribution | < 30 days | Month 1 |
| Onboarding satisfaction score | >= 4/5 | Day 30 |

---

## Output Structure

Plans saved in date-versioned folders under `${ONBOARDING_PLANS_DIR}/<YYYY-MM-DD>/onboarding-<NNNN>-<name>-<role>-<level>.md` (e.g. `onboarding-0001-alice-bld-l1.md`, `onboarding-0005-dave-bld+grd-l3.md`).

- **Date folder** (`YYYY-MM-DD` UTC): groups plans generated that day; regenerating on a new date versions without overwriting.
- **Sequential ID**: global across date folders (not reset per folder).
- **Batch generation**: `--all` (3 roles x 3 levels), `--all-levels <role>`, `--all-roles <level>`, or `--batch` for custom spec lists. See `/onboard`.

---

## Relationship to Other Harness Components

- **Review perspectives** (`general/review-perspectives.md`): addresses the DX P1 question on structured onboarding paths.
- **Conceptual design** (`project/conceptual-design-*.md`): primary source for Shapers.
- **Metacommunication** (`project/metacomm-*.md`): Shapers and Guardians load it to understand designer intent.
- **Coding standards** (`project/standards.md §§ Backend and Frontend`): referenced by Builders.
- **Skills system** (`.claude/skills/`): the onboarding skill orchestrates all of the above.
