---
designer_description: "When you run /onboard for a level-2 expert -- a senior who needs the why and the trade-offs, not the what -- I'm the level layer the onboarding-generator combines with the new hire's role to shape their plan around architecture deep-dives, decision history, technical debt exploration, first significant contribution, and the mentoring and process-improvement expectations that come with the seniority."
---

# L2 -- Expert (Senior)

> Team members with deep domain expertise. Need context on *why* and *trade-offs*.

## Characteristics

- Extensive experience (5-10 years), strong opinions informed by practice; needs *why* and trade-offs, not just *what*
- Independently designs and implements complex features; expected to mentor and improve team practices
- May productively challenge patterns -- needs decision history to distinguish intentional vs. accidental choices

## Layer 2 -- Level-Specific Onboarding Content

### Support Structure

- **Architecture sponsor**: pair with a tech lead or L3 on system-wide design decisions and rationale.
- **Decision history + stakeholders**: DRRs, plan history (`${PLANS_DIR}/INDEX.md`), historical briefs (use `/explain behavior-evolution`); 1:1s with PM, design lead, other tech leads within first two weeks.

### Learning Path

| Week | Focus | Deliverable |
|------|-------|-------------|
| 1 | Architecture deep-dive, decision history review, stakeholder 1:1s | Architecture critique document (what's strong, what could improve) |
| 2 | Technical debt exploration, codebase audit of assigned area | Technical debt assessment with prioritized recommendations |
| 3-4 | First significant contribution (complex feature or architectural improvement) | PR demonstrating understanding of project patterns and trade-offs |
| 5-8 | Cross-cutting improvement, mentoring contribution | System-wide improvement + mentoring an L1 member |

### Material Format Preferences

- **Do**: ADRs, trade-off analyses, behavior evolution timelines, technical debt inventories, system design diagrams with rationale. **Don't**: step-by-step tutorials (too basic), convention lists without rationale (need the *why*)

### AI-Assisted Development Guidance

- **Rapid codebase comprehension**: "Trace the data flow from [entry] to [database]", "Who calls [function]?"
- **Design sounding board**: "Trade-offs of approach A vs B for [problem]?"; **code reviews**: `/check review` with full perspective framework
- **AI workflow improvement**: identify where AI helps and where it falls short in this project

### Onboarding Milestones

| Milestone | Target | Verification |
|-----------|--------|-------------|
| System understanding | Week 1 | Can explain architectural trade-offs to a newcomer |
| Decision context | Week 2 | Understands *why* key decisions were made, not just *what* |
| First significant contribution | Month 1 | Complex PR that respects existing patterns while improving quality |
| Mentoring active | Month 2 | Actively mentoring at least one L1 member |
| Process improvement | Month 3 | Proposed and implemented at least one team practice improvement |
