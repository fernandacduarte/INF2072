---
designer_description: "When one skill finishes and you are deciding what to do next, I'm the reference that codifies the directed After / Suggest / Reason relationships across the whole skill catalog, so /post-skill can point you at the one or two follow-up skills that genuinely continue the thread -- /implement after /plan, /document after /implement, /explain spec-drift after a long build, and so on."
---

# FRAMEWORK - SKILL RELATIONSHIP GRAPH

> Directed skill-to-skill relationships used by `/post-skill` to suggest contextual next steps. Each skill maps to 1-2 follow-ups with a short reason. After a skill completes, `/post-skill` looks up the skill in the "After" column and displays suggested skill(s) + reason as a tip.

## Relationships

### Planning & Execution

| After | Suggest | Reason |
| --- | --- | --- |
| `/plan` | `/implement` | Ready to implement this plan? |
| `/plan --light` | `/implement` | Ready to implement this proposal? |
| `/plan --roadmap` | `/implement` | Ready to implement items from the roadmap? |
| `/implement` | `/check validate`, `/check review`, `/check preflight` | All checks run by default unless --skip-checks was used. |
| `/implement` | `/document` | Runs automatically via post-skill step 2b for FEATURE/REDESIGN plans and plans with non-N/A Docs: fields; edge stays informational for `--skip-docs` and standalone `/document` modes. |
| `/implement` | `/pending` | Review pending actions created by this implementation |
| `/implement` | `/reflect` | Surface patterns across recent skill runs (non-prescriptive) |
| `/explain spec-drift` | `/plan` | Specs analyzed -- ready to plan next steps? |
| `/explain spec-drift` | `/design` | Drift indicates intent has evolved -- update the project design |
| `/explain spec-drift --promote` | `/explain spec-drift --promote --apply-markers plan-<id>` | Decision proposal drafted -- after you apply the prose, flip the STATUS markers |
| `/explain spec-drift` | `/pending` | Address pending actions surfaced by the drift check |
| `/pending` | `/explain spec-drift --promote` | Next logical step after addressing pending curation items (generates a Decision proposal for promotion candidates) |
| `/pending` | `/implement` | Next logical step after reviewing pending review items |

### Analysis & Review

> `/research` is the usual iteration-2+ entry: branches to `/design` on intent changes, or `/plan` when work can proceed without touching intent.

| After | Suggest | Reason |
| --- | --- | --- |
| `/research` | `/plan`, `/plan --roadmap` | Want to turn these recommendations into a plan? |
| `/research` | `/design` | Recommendations indicate the design intent should change -- update the project design before planning implementation. |
| `/research --inventory` | `/explain` | Want a deeper explanation of any of these? |
| `/explain` | `/research` | Have questions about what you just learned? |
| `/check review` | `/plan` | Want to plan fixes for the review findings? |
| `/check validate` | `/plan` | Found issues? Plan and fix them. |
| `/check validate` | `/check health` | Also check harness health? |
| `/check validate` | `/pending` | Check and address outstanding pending actions |
| `/check validate` | `/reflect` | After quality checks, surface patterns across recent runs |
| `/check smoke` | `/plan` | Found failures? Plan and fix them. |
| `/check health` | `/plan` | Found issues? Plan and fix them. |
| `/check preflight` | `/check review` | Want a detailed code review of the changes? |
| `/check telemetry` | `/research` | Want to discuss usage patterns? |
| `/check telemetry` | `/reflect` | Surface descriptive patterns over the last 30 days? |
| `/reflect` | `/research` | Want an assessment and recommendations on any pattern surfaced here? |
| `/reflect` | `/design` | Want to turn a surfaced pattern into new design intents? |
| `/reflect` | `/plan` | Want to turn a surfaced pattern into new work? |

### Code & Tests

| After | Suggest | Reason |
| --- | --- | --- |
| `/check test-plan` | `/communicate` | Share the test plan with stakeholders? |
| `/check preflight` | `/onboard` |  Need to onboard someone to the project? |

### Framework maintenance

| After | Suggest | Reason |
| --- | --- | --- |
| `/seja-setup --upgrade` | `/check health` | Verify harness health after upgrading |
| `/seja-setup --upgrade` | `/explain spec-drift` | Re-run spec drift after harness upgrade to catch changed conventions |
| `/check preflight` | `/publish` | Preflight passed -- ready to cut a release? |
| `/publish` | `/check health` | Verify harness health after publishing |

### Utilities

| After | Suggest | Reason |
| --- | --- | --- |
| `/document` | `/check docs` | Validate documentation consistency? |
| `/communicate` | `/onboard` | Need to onboard someone to the project? |
| `/onboard` | `/communicate` | Want to generate stakeholder material as well? |
| `/help` | `/help --browse` | Browse all available skills? |
| `/help --browse` | `docs/how-to/plan-and-execute.md` | See quick-reference workflow sequences in the how-to guides |
| `/seja-setup` | `/design` | New project: configure project design (stack, conventions, domain model) after setup |
| `/seja-setup` | `general/getting-started.md` | New to SEJA? Follow the getting-started guide |
| `/design` | `/plan --roadmap` | Project configured -- generate a development roadmap |
| `/design` | `/plan` | Plan your first feature against the new project design |
| `/qa-log` | `/research` | Have more questions to explore? |
