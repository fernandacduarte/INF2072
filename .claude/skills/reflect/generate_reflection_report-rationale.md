---
designer_description: "Maintainer rationale for generate_reflection_report.py: historical artifact citations and design-choice context extracted from the script body so runtime code stays concise while the audit trail remains self-contained."
---

# generate_reflection_report rationale

Maintainer-only context for `generate_reflection_report.py`. This file is not imported or loaded by the script; it is versioned next to the script so historical design context stays discoverable without keeping private artifact citations in runtime comments.

> Runtime contract: do not import this file from Python code. Keep each citation entry to one self-contained paragraph that explains what the cited artifact changed and why the script is marked by it.

## Citation rationale

- **plan-000295 Step 6**: The reflection report orchestrator was introduced as the non-prescriptive composer over the primitive analyzers. It preserves primitive observation wording and writes reflection artifacts without adding recommendations, keeping `/reflect` observational rather than directive.
