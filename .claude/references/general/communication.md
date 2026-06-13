---
designer_description: "When you need to produce stakeholder-facing material from what your project already knows, I'm the reference that defines the five audience segments -- Evaluators, Adopters, Clients, End Users, Academics -- their core questions, and the Diataxis-aligned content types each one expects, so the /communicate skill can tailor tone, depth, and framing to whoever is on the receiving end."
---

# FRAMEWORK - COMMUNICATION

> Audience-aware framework for generating tailored stakeholder material from project knowledge. 3-layer content model with audience segments and Diataxis-aligned content types.

---

## How to Use

Determine the **audience segment**, then invoke `/communicate`. The skill loads the audience file, project context, and style configuration to produce tailored content.

### Invocation

```
/communicate <audience> [--format md|html] [--all] [--source <file>]
```

| Flag | Description | Default |
|------|-------------|---------|
| `<audience>` | Target audience segment (name or tag). Required unless `--all`. | -- |
| `--format md\|html` | Output format. `html` emits a styled standalone HTML file alongside the markdown. | `md` |
| `--all` | Generate for all audiences in batch (parallel agents). | off |
| `--source <file>` | Path to a research report or markdown file to reformat for the target audience. | -- |

### Audience Segments

Each stakeholder maps to one of five audience segments:

| Tag | Name | File | Core Question | Primary Material Types |
|-----|------|------|---------------|----------------------|
| EVL | Evaluators | [evaluators.md](communication/evaluators.md) | "Should we adopt this? What's the ROI?" | Executive overview, architecture overview, comparison guide, proof of value |
| ADO | Adopters | *(cross-ref: [onboarding.md](onboarding.md))* | "How do I get started and become productive?" | Onboarding plans, tutorials, quickstart guides |
| CLT | Clients | [clients.md](communication/clients.md) | "Is the product I commissioned delivering the outcomes I need?" | Product vision alignment, delivery status, outcome evidence, metacommunication summary |
| USR | End Users | [end-users.md](communication/end-users.md) | "Does the software serve my needs well?" | Quality manifesto, feedback channels, accessibility statement |
| ACD | Academics | [academics.md](communication/academics.md) | "What's the theoretical contribution? How can I build on this?" | Theoretical foundation, research agenda, extension guide |

**Note on A2 Adopters**: served by `/onboard` and `onboarding.md`. `/communicate` does not duplicate adopter material -- it cross-references onboarding output when needed.

**Note on CLT role variants**: Clients includes CLT-D (Decision-maker, shapes product design intent) and CLT-F (Funder, provides financial backing). A single stakeholder may fill both. See [clients.md](communication/clients.md).

---

## Content Layers

Material is organized in 3 progressive layers; each adds specificity:

| Layer | Name | Source | Contents |
|-------|------|--------|----------|
| **0** | Universal Foundation | `project/product-design-as-coded.md`, `project/conventions.md` | Project identity (name, tagline, mission), value proposition (problem/for whom), key differentiators, current state (phase, maturity, key metrics) -- shared across audiences |
| **1** | Audience-Specific | `general/communication/<audience>.md` | Essential + Deep-dive sections, tone guidance (formality, technical depth, framing), Diataxis mapping (Tutorial / How-to / Explanation / Reference) |
| **2** | Format-Specific | `project/communication-style.md` | CSS, header/footer templates, per-audience tone overrides, HTML conversion settings (when `--format html`) |

---

## Diataxis Integration

Each audience segment maps differently to the four Diataxis content types. Not every audience needs every type:

| Audience | Tutorial | How-to | Explanation | Reference |
|----------|----------|--------|-------------|-----------|
| **EVL** Evaluators | "Try the harness in 30 min" | Adoption guide, migration path | Architecture overview, design rationale | Skills catalog, feature matrix |
| **ADO** Adopters | *(via /onboard)* | *(via /onboard)* | *(via /onboard)* | *(via /onboard)* |
| **CLT** Clients | — | Status reporting template | Product vision, metacommunication summary | KPI definitions, outcome metrics |
| **USR** End Users | — | Feedback guide, getting help | Quality manifesto, transparency note | — |
| **ACD** Academics | "Extend the harness" workshop | Skill authoring guide | Theoretical foundation, semiotic engineering basis | Extension API, taxonomy reference |

Full Diataxis mapping with priorities and target lengths: [diataxis-mapping.md](communication/diataxis-mapping.md).

---

## Loading Strategy

For a given invocation, the skill loads files in this order:

### Single audience (`/communicate evaluators`)

1. `general/communication.md` -- this file (harness overview, audience resolution)
2. `general/communication/evaluators.md` -- audience-specific content template and tone
3. `project/product-design-as-coded.md` -- project identity (Layer 0; reads `## Conceptual Design` and `## Metacommunication` H2 sections)
4. `project/communication-style.md` -- Layer 2 overrides (if `--format html` or file exists)
5. `general/report-conventions.md` -- output file naming and encoding rules

### Source reformatting (`/communicate clients --source advisory-0002.md`)

Same as above plus the source file as input #6.

### Batch mode (`/communicate --all`)

Launches parallel agents, one per active audience (EVL, CLT, USR, ACD); each follows the single-audience loading strategy.

---

## Output Structure

Material is saved in date-versioned folders under `${COMMUNICATION_DIR}/`:

```
${COMMUNICATION_DIR}/
├── 2026-03-28/
│   ├── communication-0001-evaluators.md
│   ├── communication-0001-evaluators.html
│   ├── communication-0002-clients.md
│   └── communication-0003-end-users.md
├── 2026-04-15/
│   ├── communication-0004-academics.md
│   └── communication-0005-evaluators.md
```

- **Date folder** (`YYYY-MM-DD` UTC): groups material by generation date; regenerating on a new date creates a new version without overwriting.
- **Sequential ID**: global across date folders (not reset per folder).
- **Audience slug**: lowercase audience name (`evaluators`, `clients`, `end-users`, `academics`).
- **Extension**: `.md` / `.html`; both formats share the same ID and slug when co-generated.
- **Batch**: `--all` generates all active audiences in parallel.

---

## Relationship to Other Framework Components

- **Onboarding** (`general/onboarding.md`, `/onboard`): serves A2 Adopters; `/communicate` cross-references onboarding plans when relevant.
- **Research** (`/research`): reports can be reformatted via `--source <file>` into audience-appropriate communication.
- **Review perspectives** (`general/review-perspectives.md`): the UX perspective's focus on audience-appropriate communication maps to the per-audience tone guidance here.
- **Conceptual design / Metacommunication** (`project/product-design-as-coded.md § Conceptual Design` and `§ Metacommunication`): Layer 0 draws project identity and designer intent from these H2 sections.
- **Style template** (`template/communication-style.md` / `project/communication-style.md`): visual presentation and tone overrides, instantiated per-project by `/design`.
- **Skills system** (`.claude/skills/communicate/SKILL.md`): the `/communicate` skill orchestrates the above.
