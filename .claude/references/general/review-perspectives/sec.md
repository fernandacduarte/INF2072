---
designer_description: "When the reviewer is asked to look at what you built through security eyes, I'm the checklist that tells it what to watch for -- attack surfaces, input validation, secret handling, auth and session integrity, least-privilege authorization, and dependency or supply-chain exposure -- so the findings that come back separate the things that would block a release from the ones you can safely defer."
tier: Essential
---

# SEC — Security

## Essential

- [P0] Does this introduce or widen an attack surface (injection, XSS, CSRF, auth bypass)?
- [P0] Are inputs validated at the boundary? Outputs sanitized before rendering?
- [P0] Are secrets, tokens, and credentials handled per project/security-checklists.md?
- [P0] Can user-controlled input reach OS commands, SQL queries, or template engines without parameterization or sandboxing?
- [P0] Are auth/session flows resistant to token leakage, fixation, and replay, and is authorization enforced server-side for every state-changing op (incl. horizontal escalation between tenants)?

## Deep-dive

- [P1] Are rate limits applied per authenticated user (not just IP), with lockout on repeated auth failures?
- [P1] Are dependencies audited for known vulnerabilities (`pip audit`, `npm audit`) before deployment?
- [P1] Are cryptographic primitives current (no MD5/SHA-1 for integrity, no ECB), keys rotated on schedule, random values from a CSPRNG?
- [P1] Are cloud permissions scoped to least privilege, with buckets, queues, and endpoints protected against public exposure or IAM misconfig?
- [P1] Are dependencies pinned to exact versions with verified checksums, and is CI/CD protected against dependency confusion and compromised build tooling?
- [P1] Has the threat model been updated for new trust boundaries, data flows, or elevated-privilege components?
- [P1] Is personal/sensitive data minimized at collection, encrypted at rest and in transit, and purgeable within GDPR Art. 17 / CCPA 1798.105 SLAs?
- [P2] Is there account enumeration protection on login/register/reset endpoints?
- [P2] Are audit-log completeness (who, what, when, from-where per SOC 2 CC7/CC8, ISO 27001 A.12.4) and detection signals (structured logs, alerts, correlation IDs) sufficient to triage exploitation within SLA?
- [P3] Are API versioning or deprecation headers in place to prevent clients from using stale, insecure endpoints?
