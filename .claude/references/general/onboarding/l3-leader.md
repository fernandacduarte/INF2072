---
designer_description: "When you run /onboard for a level-3 leader -- a staff or principal strategist, or a tech lead or engineering manager joining with strategic or managerial influence -- I'm the level layer the onboarding-generator combines with the new hire's role to shape their plan around organizational context, cross-team dependencies, decision and incident history, governance audits, and the first cross-cutting initiative or quick win that earns them trust without disrupting what is already working."
---

# L3 -- Leader (Staff / Principal / Manager)

> Team members with strategic or managerial influence. Need *organizational context* and *team dynamics*.

## Characteristics

- Deep, broad experience (10+ years or equivalent); thinks in systems, not features -- sees cross-team implications
- Influences technical direction beyond immediate team (Strategist) or owns process/people outcomes (Manager)
- Understands organizational constraints, not just technical ones; must earn trust quickly without disrupting working patterns
- May join to address a strategic challenge or lead a team through transition

## Layer 2 -- Level-Specific Onboarding Content

### Support Structure

| Support | Strategist (IC: Staff/Principal) | Manager (Tech Lead/EM) |
| --- | --- | --- |
| **Sponsor/peer** | Executive sponsor: direct access to engineering leadership for strategic context, history, political landscape | Leadership peer: pair with another tech lead or EM for organizational context and norms |
| **Cross-team/team history** | Cross-team liaison: intros to leads of all interacting teams; dedicated 1:1s in first week | Retrospective access: review last 3-6 months of retro notes for team health patterns |
| **Briefing/1:1s** | 1-hr strategic briefing: why the team exists, what success looks like, biggest risks, what's been tried and failed | 30-min 1:1s with every team member in first two weeks; listen more than talk |

### Learning Path

| Week | Focus (Strategist) | Focus (Manager) | Deliverable |
|------|---------------------|------------------|-------------|
| 1 | Organizational context, cross-team dependencies, strategic priorities | Team introductions, process observation, 1:1s | Stakeholder map (Strategist) / team dynamics assessment (Manager) |
| 2 | Technical debt audit, system-wide architecture review | Process review, governance audit, metrics review | Technical vision draft (Strategist) / process improvement shortlist (Manager) |
| 3-4 | First cross-cutting initiative (architectural improvement, process change, or debt reduction) | First process improvement, hiring/staffing review | Initiative proposal (Strategist) / one quick win implemented (Manager) |
| 5-12 | Strategic execution, coalition building | Team development, strategic alignment, sustainable cadence | Measurable progress on initiative (Strategist) / team operating rhythm established (Manager) |

### Material Format Preferences

| | Strategist | Manager |
| --- | --- | --- |
| **Do** | Strategic roadmaps, cross-team dependency maps, technical debt inventories with business impact, historical incident postmortems, org charts with responsibilities | Team health dashboards, DORA metrics history, retrospective summaries, escalation path documentation, hiring pipeline status, team skill matrix |
| **Don't** | Coding tutorials, convention guides (absorbed via code review), isolated component documentation | Detailed coding guides (absorbed via code review), individual module documentation (too granular for first weeks) |

### Onboarding Focus Areas

- **Technical debt landscape**: inventory with severity, business impact, payoff timelines. Run `/research --inventory` if missing.
- **Cross-team dependencies**: who depends on this system, what SLAs exist, where friction occurs.
- **Failed initiatives**: what has been tried and why it didn't work -- avoids repeating mistakes.
- **Budget and resource constraints**: team size, hiring plans, infrastructure costs, vendor contracts.
- **Compliance and regulatory context**: external obligations constraining technical decisions.
- **Team composition and skills** (Manager): who does what, skill gaps, growth aspirations, flight risks.
- **Process and ceremonies** (Manager): sprint cadence, standup, retrospective, planning -- what's working and what's not.
- **Escalation paths** (Manager): when/how to escalate technical, people, and cross-team issues.
- **Hiring context** (Manager): open roles, hiring pipeline, interview process, future-hire onboarding.

### Governance Areas to Audit (within first month)

| Area | Key Questions |
|------|--------------|
| Code review | Who reviews what? Average turnaround? Quality of feedback? |
| Deployment | How often? Who approves? What's the rollback process? |
| Incident response | Who's on call? What's the SLA? How are postmortems run? |
| Technical debt | Is there an inventory? How is it prioritized against features? |
| Team development | Are there growth plans? Regular feedback? Learning budget? |

### AI-Assisted Development Guidance

- **System-wide analysis**: "Common patterns across services?", "Where are the consistency gaps?"
- **Impact assessment**: "If we change [module], what are the downstream effects?"
- **Documentation generation**: `/explain architecture` and `/research --inventory` for system maps
- Shape the team's **AI strategy**: where AI adds most value, usage guidelines
- **Codebase orientation, process docs, team norms** (Manager): enough AI-reading fluency to review code and make decisions; generate/improve team docs, runbooks, onboarding guides; establish sanctioned tools, AI-code review process, quality bar

### Onboarding Milestones

| Milestone | Target | Verification |
|-----------|--------|-------------|
| Organizational context / team relationships | Week 1-2 | Can explain cross-team dynamics (Strategist) / completed 1:1s with all team members (Manager) |
| Technical vision / process understanding | Week 2 | Draft vision shared (Strategist) / can describe team cadence and pain points (Manager) |
| First strategic initiative / quick win | Month 1 | Cross-cutting improvement in progress (Strategist) / one process improvement implemented (Manager) |
| Influence established / trust earned | Month 2-3 | Other teams consult on decisions (Strategist) / team brings issues proactively (Manager) |
| Measurable impact / sustainable cadence | Month 3-6 | Visible improvement in a system-wide metric (Strategist) / team operating rhythm reflects leadership (Manager) |
