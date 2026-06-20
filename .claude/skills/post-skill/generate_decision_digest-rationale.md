---
designer_description: "Maintainer rationale for generate_decision_digest.py: historical artifact citations and design-choice context extracted from the script body so runtime code stays concise while the audit trail remains self-contained."
---

# generate_decision_digest rationale

Maintainer-only context for `generate_decision_digest.py`. This file is not imported or loaded by the script; it is versioned next to the script so historical design context stays discoverable without keeping private artifact citations in runtime comments.

> Runtime contract: do not import this file from Python code. Keep each citation entry to one self-contained paragraph that explains what the cited artifact changed and why the script is marked by it.

## Citation rationale

- **advisory-000448**: The research-header parser supports the forward-only rename from advisory to research outputs so decision extraction can read current research logs while older advisory handling remains separate.
