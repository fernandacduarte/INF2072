---
designer_description: "When you run /onboard for a level-1 contributor -- a newcomer or mid-level practitioner who needs guidance on how, what, and where -- I'm the level layer the onboarding-generator combines with the new hire's role to shape their plan into the support structure, learning path, material format, AI-assistance norms, and week-by-week milestones that move them from day-one environment setup to first independent feature delivery."
---

# L1 -- Contributor (Junior to Mid-level)

> Individual contributors learning the project. Need guidance on *how*, *what*, and *where*.

## Characteristics

- Experience spans newcomer (0-2 years) to mid-level practitioner (2-5 years)
- Newcomers need explicit step-by-step instructions; practitioners complete well-defined tasks independently
- Benefits from structured mentorship, intensity varying with experience
- Newcomers learn via guided practice; practitioners need project-specific context, not general skills
- May not yet see the full picture of architectural trade-offs

## Layer 2 -- Level-Specific Onboarding Content

### Support Structure

| Support | Newcomer (0-2 yrs) | Practitioner (2-5 yrs) |
| --- | --- | --- |
| **Buddy/mentor** | Pair with L2+; daily 15-min check-ins for 2 weeks, then twice weekly for a month | Pair with L2+ for context; weekly 30-min sync for first month |
| **Pair/walkthrough** | Pair programming minimum 2 hrs/week for first month on real tasks | 1-hr architecture walkthrough with a senior on design decisions and trade-offs |
| **Review/context** | First 5 PRs reviewed with detailed, educational feedback explaining *why* | 1-hr domain session with a Shaper (PM/designer) on user goals, personas, product direction |

### Learning Path

| Week | Focus (Newcomer) | Focus (Practitioner) | Deliverable |
|------|-------------------|----------------------|-------------|
| 1 | Environment setup, project overview, first guided task | Environment setup, architecture overview, conventions review | First commit/PR merged |
| 2 | Conventions deep-dive, second guided task | Deep-dive into assigned area, dependency mapping | Second commit + one code review given (practitioner) |
| 3-4 | First independent task (well-scoped, with safety net) | Independent feature work or significant bug fix | Independent PR / feature branch completed |
| 5-8 | Gradual task complexity increase | Cross-area exploration, process contribution | Consistent contributions with decreasing review feedback / contribution outside initial area |

### Material Format Preferences

| | Newcomer | Practitioner |
| --- | --- | --- |
| **Do** | Step-by-step walkthroughs, annotated code examples, video recordings of pair sessions, checklists | Architecture diagrams, convention reference sheets, "why we chose X over Y" decision records, curated reading lists |
| **Don't** | Dense reference documents, architecture decision records (too abstract), large-scope tasks | Step-by-step hand-holding (too slow), full codebase walkthrough (too broad) |

### AI-Assisted Development Guidance

- Use AI to **explore and understand**: "What does this function do?", "How is this component used?"; **accelerate context**: "Explain the data flow for [feature]", "Conventions for [pattern]?"
- Use AI to **explain errors**, **generate code**, and **review your own** ("What could go wrong?", "Am I missing edge cases?") -- but always verify against project conventions; suggested patterns may not match
- **Read and understand** AI-generated code before committing -- never treat it as a black box; develop judgment for when to trust, question, or override
- **Red flag**: If you can't explain the code in plain language, don't commit it

### Onboarding Milestones

| Milestone | Target | Verification |
|-----------|--------|-------------|
| Environment running | Day 1 | All tests pass locally |
| First commit | Week 1 | PR merged with mentor/buddy approval |
| Architecture mental model | Week 1-2 | Can draw the system diagram from memory (practitioner) |
| Convention fluency | Week 2-4 | PRs pass review with minimal style/convention feedback |
| Independent feature delivery | Month 1-2 | End-to-end feature without architectural guidance |
| Meaningful code reviews | Month 2-3 | Review feedback that catches real issues |
| Cross-area contribution | Month 3+ | Successful PR in an unfamiliar area of the codebase |
