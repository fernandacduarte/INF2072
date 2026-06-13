---
designer_description: "Maintainer rationale for pending.py: historical artifact citations and design-choice context extracted from the script body so runtime code stays concise while the audit trail remains self-contained."
---

# pending rationale

Maintainer-only context for `pending.py`. This file is not imported or loaded by the script; it is versioned next to the script so historical design context stays discoverable without keeping private artifact citations in runtime comments.

> Runtime contract: do not import this file from Python code. Keep each citation entry to one self-contained paragraph that explains what the cited artifact changed and why the script is marked by it.

## Citation rationale

- **plan-000265**: The usage example demonstrated the `--source plan-NNNNNN` shape for pending actions. The concrete private ID has no semantic role, so the script now uses placeholders while this sibling records why the example existed.
