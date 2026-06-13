---
designer_description: "When the reviewer is asked to look at what you built through developer-experience eyes, I'm the checklist that tells it what to watch for -- readability, self-documentation, helpful error messages, CI/CD hygiene, onboarding friction, and the 13 communicability breakdowns that expose where a developer might give up, get stuck, or silently misuse your API -- so the next contributor doesn't need tribal knowledge to ship a change."
tier: Essential
---

# DX — Developer Experience

## Essential

- [P0] Is the code readable, self-documenting, and following project conventions?
- [P0] Are error messages helpful for debugging? Are edge cases handled gracefully?
- [P0] Is there CI/CD running tests, linting, and type-checking on every commit?
- [P0] Can a developer go from clone to passing tests in under 5 minutes with a single command, and does the pipeline fail fast with actionable errors?
- [P0] Does the internal developer platform provide self-service environment provisioning, secrets, and deployment -- no tickets for routine work?
- [P0] Are inline comments, API docs, and DRRs up to date and co-located with the code they describe?
- [P0] Will a new contributor understand this without tribal knowledge?

## Deep-dive

- [P1] Is there automated dependency update tooling (Dependabot, Renovate)?
- [P1] Are coverage thresholds enforced, preventing regressions below a minimum?
- [P1] Are code review guidelines documented and enforced (turnaround, approvals, feedback norms)?
- [P1] Is there a structured onboarding path (quick-start, sample tasks, mentorship) that lets a new member ship a meaningful change in their first week?
- [P1] Are contribution guidelines, issue templates, and a code of conduct published so external or cross-team contributors can participate without friction?
- [P2] Does the project provide editor configs (`.editorconfig`, recommended extensions, launch configs) so IDE features work out of the box?
- [P2] Are linting, formatting, and static analysis automated in pre-commit hooks and CI so style never blocks reviews?
- [P2] In a monorepo, are build caching, affected-target detection, and dependency graph tooling in place so developers only build and test what changed?
- [P3] Are developer productivity metrics (build times, CI wait, deploy frequency, time-to-first-commit) tracked regularly to identify bottlenecks?

## Communicability

> 13 utterances from Semiotic Engineering [SemEng-2005, Ch. 4; adapted for developer-facing interfaces per SigniFYI-2016], grounded in the **illocution vs. perlocution discrimination principle**. Each maps 1:1 to a breakdown type between the developer and the tool/API/framework designer's deputy. Use to diagnose how APIs, CLIs, SDKs, config, and docs fail to communicate design intent.

### Complete Failures (I) -- developer cannot achieve their goal

| Utterance | Code | Breakdown | Diagnostic question |
|-----------|------|-----------|-------------------|
| "I give up." | Ia | Abandons goal -- out of knowledge, patience, or time for the tool/API | Could a developer exhaust docs, examples, and error messages without finding a path to their task? |
| "Looks fine to me." | Ib | Believes API call/config/integration succeeded when it didn't -- silent failures, partial writes, ignored parameters | Could a developer believe their operation succeeded when it didn't (silent failures, swallowed errors, ignored parameters)? |

### Temporary Failures (II) -- eventual success, but local steps break down

IIa = halted semiosis (sense-making stuck). IIb = wrong illocution (approach is wrong). IIc = clarification-seeking (probing designer intent).

| Utterance | Code | Breakdown | Diagnostic question |
|-----------|------|-----------|-------------------|
| "Where is it?" | IIa1 | Cannot find the endpoint, config option, CLI flag, or API method | Could a developer not find the endpoint, config option, or CLI flag for their action? |
| "What happened?" | IIa2 | Cannot see the outcome of a call/command -- no response, unclear status, missing logs | Does every API call, CLI command, and config change produce clear feedback? |
| "What now?" | IIa3 | Clueless about next step -- docs, errors, and responses give no guidance | After an API response or error, could a developer be left with no next step? |
| "Where am I?" | IIb1 | Using the API/tool in the wrong context or mode | Could a developer confuse which API version, environment, or auth context they're in? |
| "Oops!" | IIb2 | Immediate slip -- wrong endpoint, parameter, or command | Are there parameters, flags, or method names whose similarity could cause an accidental mis-call? |
| "I can't do it this way." | IIb3 | Abandons a whole integration approach after discovering it won't work | Could a developer follow a plausible integration path that doesn't support their use case? |
| "What's this?" | IIc1 | Probes a parameter, return value, or config for meaning -- reads types, explores responses | Are there parameters, response fields, or config options with ambiguous names? |
| "Help!" | IIc2 | Explicitly consults docs, examples, or asks for help | Are docs reachable, contextual, and sufficient to resolve the specific problem? |
| "Why doesn't it?" | IIc3 | Repeats failing calls to understand what's wrong -- experimental debugging | Could a developer repeat the same failing call multiple times, unable to determine why? |

### Partial Failures (III) -- goal achieved, but not via the intended path

| Utterance | Code | Breakdown | Diagnostic question |
|-----------|------|-----------|-------------------|
| "I can do otherwise." | IIIa | Goal achieved via unintended path (raw SQL not ORM, direct file access not API) without knowing the supported approach | Could a developer achieve their goal via a workaround without discovering the intended approach? |
| "Thanks, but no, thanks." | IIIb | Understands the intended approach but bypasses it -- cumbersome, slow, or over-engineered for their need | Is the intended pattern cumbersome enough that an informed developer would prefer a shortcut? |
