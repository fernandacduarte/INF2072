---
designer_description: "When you run /communicate and need to know which audience gets which kind of artifact, I'm the reference the communication-generator consults to pick the right Diataxis content type (tutorial, how-to, explanation, reference), the right length, and the right priority tier per audience, so you end up with a coherent set of pieces that do not duplicate each other across evaluators, clients, users, and academics."
---

# Diataxis Mapping — Audience x Content Type Matrix

Cross-reference of audience segments against Diataxis content types. Each cell gives title, target length, and priority (P1 = must-have, P2 = nice-to-have).

## Matrix

### Tutorial (Learning-oriented)

| Audience | Content Title | Target Length | Priority | Shared? |
|----------|--------------|---------------|----------|---------|
| EVL — Evaluators | "Try the harness in 30 min" | 1500-2000 words | P1 | Yes (also serves BLD L1-L2) |
| CLT — Clients | — | — | — | Not applicable |
| USR — End Users | — | — | — | Not applicable |
| ACD — Academics | "Extend the harness" workshop | 3000-4000 words | P1 | Yes (also serves BLD L4-L5) |

### How-to (Task-oriented)

| Audience | Content Title | Target Length | Priority | Shared? |
|----------|--------------|---------------|----------|---------|
| EVL — Evaluators | Adoption guide | 2000-2500 words | P1 | — |
| CLT — Clients | Status reporting template | 1000-1500 words | P2 | — |
| USR — End Users | Feedback guide | 500-800 words | P1 | — |
| ACD — Academics | Skill authoring guide | 2000-3000 words | P1 | Yes (also serves BLD L3+) |

### Explanation (Understanding-oriented)

| Audience | Content Title | Target Length | Priority | Shared? |
|----------|--------------|---------------|----------|---------|
| EVL — Evaluators | Architecture overview | 2000-2500 words | P1 | Yes (also serves ACD, BLD L3+) |
| CLT — Clients | Product vision | 800-1200 words | P1 | — |
| CLT — Clients | Metacommunication summary | 500-800 words | P1 | CLT-D primary |
| USR — End Users | Quality manifesto | 500-800 words | P1 | — |
| ACD — Academics | Theoretical foundation | 3000-5000 words | P1 | — |

### Reference (Information-oriented)

| Audience | Content Title | Target Length | Priority | Shared? |
|----------|--------------|---------------|----------|---------|
| EVL — Evaluators | Skills catalog | 1500-2000 words | P1 | Yes (also serves ACD, BLD) |
| CLT — Clients | KPI definitions | 1000-1500 words | P2 | — |
| USR — End Users | — | — | — | Not applicable |
| ACD — Academics | API / extension reference | 2000-3000 words | P2 | Yes (also serves BLD L4+) |

## Shared Artifacts

| Content Title | Primary Audience | Secondary Audiences | Notes |
|--------------|-----------------|---------------------|-------|
| "Try the harness in 30 min" | EVL | BLD (L1-L2) | Evaluators need it for assessment; new builders use it for first contact |
| Architecture overview | EVL | ACD, BLD (L3+) | Same core content, different framing emphasis per audience |
| Skills catalog | EVL | ACD, BLD | Single reference, universally useful |
| Skill authoring guide | ACD | BLD (L3+) | Academics need theoretical grounding; builders need practical steps |
| "Extend the harness" workshop | ACD | BLD (L4-L5) | Research-oriented extension doubles as advanced builder material |
| API / extension reference | ACD | BLD (L4+) | Same technical content, different motivation |

## Content Production Order (by priority and dependency)

1. **Architecture overview** (Explanation, EVL) — foundational for other pieces.
2. **Skills catalog** (Reference, EVL) — prerequisite for adoption/authoring guides.
3. **"Try the harness in 30 min"** (Tutorial, EVL) — highest adoption impact.
4. **Theoretical foundation** (Explanation, ACD) — academic credibility.
5. **Product vision** (Explanation, CLT) — enables client conversations.
6. **Quality manifesto** (Explanation, USR) — sets user expectations.
7. **Adoption guide** (How-to, EVL) — converts evaluators to adopters.
8. **Feedback guide** (How-to, USR) — lightweight, high user impact.
9. **Skill authoring guide** (How-to, ACD) — enables community contributions.
10. **KPI definitions** (Reference, CLT) — supports client reporting.
11. **Status reporting template** (How-to, CLT) — depends on KPI definitions.
12. **API / extension reference** (Reference, ACD) — advanced, lower priority.
