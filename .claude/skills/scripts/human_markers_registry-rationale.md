---
designer_description: "Maintainer rationale for human_markers_registry.py: historical artifact citations and design-choice context extracted from the script body so runtime code stays concise while the audit trail remains self-contained."
---

# human_markers_registry rationale

Maintainer-only context for `human_markers_registry.py`. This file is not imported or loaded by the script; it is versioned next to the script so historical design context stays discoverable without keeping private artifact citations in runtime comments.

> Runtime contract: do not import this file from Python code. Keep each citation entry to one self-contained paragraph that explains what the cited artifact changed and why the script is marked by it.

## Citation rationale

- **plan-000267 Amendment 1**: The marker registry lists both template and project reference files so marker tools validate the source templates and the instantiated workspace files with identical rules. That keeps the human-marker boundary intact before and after setup.
- **advisory-000264 Q3**: The STATUS marker accepts both current lowercase lifecycle values and the older uppercase `IMPLEMENTED` value. This compatibility lets promotion and validation tools work across files authored before the lifecycle vocabulary was normalized.
