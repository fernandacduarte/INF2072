---
designer_description: "When the reviewer is asked to look at what you built through data-integrity-and-privacy eyes, I'm the checklist that tells it what to watch for -- PII handling under GDPR/CCPA, encryption at rest, cascade and referential-integrity rules, consent capture and withdrawal, retention and right-to-deletion, cross-border transfer controls, and audit-log completeness -- so the data your feature touches stays lawful, classified, and traceable end-to-end."
tier: Deep-dive
---

# DATA — Data Integrity & Privacy

## Essential

- [P0] Does this change handle personal data (PII) in compliance with GDPR/privacy requirements?
- [P0] Are cascade deletes, orphan records, and referential integrity properly managed?
- [P0] Are PII fields encrypted at rest, or is the encryption boundary clearly documented?
- [P0] Does every processing activity involving personal data have a documented lawful basis, with ROPA updated to reflect this change?
- [P0] Are uniqueness constraints, check constraints, and foreign keys enforced at the database level rather than in application logic alone?
- [P0] Is user consent captured with granular purpose-scope and version-stamped, with withdrawal honored within the required timeframe?
- [P0] For cross-border transfers, is a valid mechanism in place (SCCs, adequacy decision, BCRs) with data residency enforced at the infrastructure level?

## Deep-dive

- [P1] Are data validation rules enforced at both the API boundary and the database level?
- [P1] Are data retention, anonymization, and right-to-deletion considerations addressed?
- [P1] Are retention policies defined and enforced (auto-purge of old activity logs, soft-deleted records)?
- [P1] Are data pipelines idempotent and schema-versioned so reprocessing or rollback cannot silently corrupt or duplicate downstream records?
- [P1] Is personal data minimized by default -- collected only for an explicit purpose and excluded from logs, caches, and analytics unless a PIA approves it?
- [P1] Are data classification labels (public, internal, confidential, restricted) assigned to every new or modified data element with ownership recorded?
- [P1] Is end-to-end data lineage tracked so origin, transformations, and downstream consumers are discoverable in the data catalog?
- [P1] When personal data is anonymized or synthesized for non-production use, is re-identification risk formally assessed against an acceptable threshold?
- [P2] Do audit trails capture who accessed or mutated sensitive data, tamper-evident and retained per policy for regulatory examination?
- [P3] Is there a Software Bill of Materials (SBOM) for supply chain transparency?
