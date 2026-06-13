---
designer_description: "Maintainer rationale for backfill_decision_digest.py: historical artifact citations and design-choice context extracted from the script body so runtime code stays concise while the audit trail remains self-contained."
---

# backfill_decision_digest rationale

Maintainer-only context for `backfill_decision_digest.py`. This file is not imported or loaded by the script; it is versioned next to the script so historical design context stays discoverable without keeping private artifact citations in runtime comments.

> Runtime contract: do not import this file from Python code. Keep each citation entry to one self-contained paragraph that explains what the cited artifact changed and why the script is marked by it.

## Citation rationale

- **advisory-000448**: The research-header parser recognizes the forward-only rename from advisory logs to research logs. The code keeps the research header shape explicit because new research artifacts should be indexed under the new naming surface while historical advisory artifacts remain readable elsewhere.
