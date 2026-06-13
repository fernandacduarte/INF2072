---
designer_description: "When you run /communicate for evaluators -- the CTOs, tech leads, and engineering managers deciding whether to adopt the harness -- I'm the template the communication-generator fills in to produce adoption-decision material: a crisp executive overview, an honest comparison against alternatives, a concrete adoption path, and the cost-and-ROI evidence a technical leader needs to justify the investment to their peers."
---

# EVL — Evaluators

> CTOs, tech leads, and engineering managers assessing whether to adopt the harness.

## Core Question

"Should we adopt this? What's the ROI?"

## Roles

- Engineering leadership (CTO / VP of Engineering, Engineering manager)
- Technical leadership (Tech lead / Staff engineer, Architecture review board member, Developer experience lead)

## Communication Content

### Essential (all Evaluators need)

- **Executive Overview**: What the harness is, what problem it solves, and how it differs from ad-hoc AI-assisted development. One-page summary with key differentiators and constraints.
- **Adoption Path**: Concrete steps from first contact to team-wide rollout. Prerequisites, time investment, and what changes in daily workflow.
- **Architecture Overview**: How the harness is structured — skills, review perspectives, onboarding layers, product-design/. Diagram of component relationships and extension points.

### Deep-dive (load for thorough evaluation or when Evaluator is the primary audience)

- **Comparison Guide**: Harness vs. alternatives -- raw prompting, other harnesses, none. Honest value/overhead assessment.
- **Proof of Value**: Before/after examples and metrics (review coverage, onboarding time, AI output consistency). Team-pilot template.
- **Migration Path**: Introducing the harness into an existing project with established conventions -- transition expectations, handling resistance, rollback.
- **Cost Analysis**: Setup time, learning curve, maintenance; token, context-window, and attention costs.
- **Framework Value Proposition**: Business-terms summary (faster onboarding, consistency, reduced rework) for non-technical evaluators justifying the investment.
- **Framework ROI Modeling**: ROI calculator template -- inputs (team size, project duration, current onboarding time) and projected savings (conservative/optimistic).
- **Cost of Not Adopting**: Status-quo waste without structured AI-assisted development -- inconsistent output, knowledge silos, repeated mistakes, slower onboarding.

## Diataxis Mapping

| Content Type | Title | Notes |
|-------------|-------|-------|
| Tutorial | "Try the harness in 30 min" | Hands-on walkthrough: clone, seed, design, first skill invocation |
| Explanation | Architecture overview | Why the harness is structured this way, design decisions |
| How-to | Adoption guide | Step-by-step: from evaluation to team rollout |
| Reference | Skills catalog | Complete list of skills with purpose, inputs, outputs |

## Tone Guidance

- Technical but accessible — assume engineering leadership vocabulary, avoid jargon that only harness authors would know.
- Honest about trade-offs — state clearly where the harness adds overhead or complexity, not just where it helps.
- Lead with problems solved — start from pain points the evaluator recognizes, then show how the harness addresses them.
- Respect the evaluator's time — front-load conclusions, put evidence in appendices.
