---
designer_description: "When you run /communicate for end users -- the people who actually use the software you ship -- I'm the template the communication-generator fills in to produce warm, non-technical material that speaks designer-to-user: the metacommunication message that tells users who the system thinks they are, a quality manifesto of what they can rely on, and the feedback channels you commit to keeping open."
---

# USR — End Users

> People who use the software built with the harness.

## Core Question

"Does the software serve my needs well?"

## Roles

- General users: application end user, customer/client user, internal business user.
- Specialized profiles: accessibility-dependent user, power/frequent user.

## Communication Content

### Essential (all End User communications need)

- **Metacommunication Message**: Use the definition in `general/shared-definitions.md`. If multiple user groups are identified, create one message per group; when overlap is high, start with a shared message and append group-specific sections indicating which parts address whom.
- **Quality Manifesto**: Plain-language commitment to the team's standards -- what users can expect for reliability, usability, and responsiveness -- written from the people who build the software to the people who use it.
- **Feedback Channels**: How users report issues, request features, and share experience. Clear paths with expected response times; emphasize the team's commitment to listening.

### Deep-dive (load for thorough engagement or when End User trust is the primary goal)

- **Transparency Note**: How AI-assisted development is used, what it means for quality, what safeguards are in place, and what it does not mean (the software is designed, reviewed, and validated by people using AI as a tool).
- **Accessibility Statement**: The team's approach -- which standards are followed (WCAG level), how accessibility is tested, and how to report barriers.
- **Privacy Commitment**: How user data is handled during development (e.g., AI tools do not receive production user data) and a clear statement on user-relevant data practices.

## Diataxis Mapping

| Content Type | Title | Notes |
|-------------|-------|-------|
| Explanation | Quality manifesto | Why the team builds software the way they do |
| How-to | Feedback guide | How to submit feedback, report bugs, request features |

## Tone Guidance

- Non-technical -- avoid developer jargon; write as if to someone who has never written code.
- User-centric -- focus on what the software does for the user, not how it is built; the harness is invisible to this audience.
- Warm but not patronizing -- respect the user's intelligence while keeping language accessible.
- Focus on commitments -- users want to know what they can rely on, not how the team organizes its work.
