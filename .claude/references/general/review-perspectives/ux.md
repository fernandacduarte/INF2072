---
designer_description: "When the reviewer is asked to look at what you built through user-experience eyes, I'm the checklist that tells it what to watch for -- flow intuitiveness, loading/empty/error/offline states, error recovery, information architecture, dark-pattern avoidance, and the 13 communicability breakdowns that expose where a user might get stuck, misread the interface, or silently fail -- so the design speaks clearly for you instead of needing a user manual."
tier: Essential
---

# UX — User Experience

## Essential

- [P0] Is the user flow intuitive, with clear feedback for actions and errors?
- [P0] Do user research findings (personas, journey maps, usability studies) inform these design decisions, and are unvalidated assumptions flagged for testing?
- [P0] Has the flow been validated with real users across key task scenarios, with usability issues above a severity threshold resolved?
- [P0] On error, does the UI explain in plain language, preserve user input, and offer a clear recovery or undo path?

## Deep-dive

- [P1] Does the interaction follow established UX patterns in the project?
- [P1] Are loading, empty, and error states handled?
- [P1] Are offline or degraded-network states handled gracefully (retry, queue, feedback)?
- [P1] Is information architecture structured so users can form accurate mental models and find content through multiple paths?
- [P1] Are micro-interactions (transitions, hover, affordances) consistent and purposeful, reinforcing cause-and-effect rather than adding noise?
- [P1] Are dark patterns absent, with opt-outs as easy as opt-ins and no manipulative urgency or social proof?
- [P1] Do components adhere to design system token and pattern contracts, with deviations documented and tracked for backport?
- [P1] Does onboarding progressively disclose complexity, provide quick wins, and let users skip or revisit steps without losing progress?
- [P1] Are analytics events instrumented at decision points so drop-off, task completion, and variant performance can be measured?
- [P2] Are optimistic updates used where appropriate to reduce perceived latency?
- [P2] Is there a consistent skeleton/shimmer loading pattern across data-dependent views?
- [P2] Is copy concise, scannable, and action-oriented, with terminology consistent and aligned with users' actual vocabulary?

## Communicability

> 13 utterances from Semiotic Engineering [SemEng-2005, Ch. 4 pp.123-138], grounded in the **illocution vs. perlocution discrimination principle**. Each maps 1:1 to a breakdown type between the user and the designer's deputy (the system speaking on the designer's behalf).

### Complete Failures (I) -- global intent does not match global outcome

| Utterance | Code | Breakdown | Diagnostic question |
|-----------|------|-----------|-------------------|
| "I give up." | Ia | User consciously abandons the goal -- has run out of knowledge, skill, time, or patience | Could a user plausibly exhaust all apparent paths to their goal and have no visible way forward? |
| "Looks fine to me." | Ib | User believes they succeeded but actually hasn't -- the system state does not match their intent, and they cannot tell | Could the UI lead a user to believe an action completed successfully when it didn't (silent failures, missing confirmation, invisible side effects)? |

### Temporary Failures (II) -- global intent achieved, but local steps break down

IIa = halted semiosis (sense-making stuck). IIb = wrong illocution (user realizes their approach is wrong). IIc = clarification-seeking (user probes the designer's message).

| Utterance | Code | Breakdown | Diagnostic question |
|-----------|------|-----------|-------------------|
| "Where is it?" | IIa1 | Cannot find the control among visible signs | Could a user plausibly not find the control for this action? |
| "What happened?" | IIa2 | Cannot see or perceive the outcome of their action | Does every user action produce visible, timely feedback? |
| "What now?" | IIa3 | Clueless about next step -- no sign means anything in context | Could a user face a screen where no element suggests a next step? |
| "Where am I?" | IIb1 | Acting in the wrong context/mode -- action would be valid elsewhere | Could a user confuse which mode, section, or state they're in? |
| "Oops!" | IIb2 | Immediate slip-and-backtrack -- isolated wrong expression | Are there controls whose proximity or labels could cause a quick mis-click? |
| "I can't do it this way." | IIb3 | Abandons a multi-step plan after realizing it won't work | Could a user follow a plausible multi-step path that leads nowhere? |
| "What's this?" | IIc1 | Probes an element for meaning (hovers, opens menus) -- implicit metacommunication | Are there elements whose meaning isn't self-evident and lack tooltips/labels? |
| "Help!" | IIc2 | Explicitly invokes help (F1, docs, asks someone) -- explicit metacommunication | Is help reachable, contextual, and sufficient to resolve the breakdown? |
| "Why doesn't it?" | IIc3 | Repeats failing steps to understand what went wrong -- autonomous sense-making | Could a user repeat the same failing action multiple times, unable to determine why? |

### Partial Failures (III) -- goal achieved, but not via the intended path

| Utterance | Code | Breakdown | Diagnostic question |
|-----------|------|-----------|-------------------|
| "I can do otherwise." | IIIa | Goal achieved via unintended path without understanding the designed solution -- residual misconception | Could a user achieve their goal via a workaround without discovering the intended approach? |
| "Thanks, but no, thanks." | IIIb | Understands the designed solution but deliberately chooses an alternative -- designer's user-model mismatch | Is the intended path cumbersome enough that an informed user would prefer a shortcut? |

### Sign Classification (optional analytical lens)

> Segmented analysis by sign class mirrors the Semiotic Inspection Method [SemEng-Methods-2009] and can catch inconsistencies that cross-cutting reviews miss.

- [P2] **Metalinguistic signs**: Are help text, error messages, tooltips, and docs consistent with the interactive behavior they describe?
- [P2] **Static signs**: Do labels, icons, layout, and visual hierarchy communicate available actions and their relationships in a single-moment snapshot?
- [P2] **Dynamic signs**: Do state transitions, animations, and feedback confirm the user's understanding of what happened and what to do next?
