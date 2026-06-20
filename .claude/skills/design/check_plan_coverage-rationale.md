---
designer_description: "Maintainer rationale for check_plan_coverage.py: historical artifact citations and design-choice context extracted from the script body so runtime code stays concise while the audit trail remains self-contained."
---

# check_plan_coverage rationale

Maintainer-only context for `check_plan_coverage.py`. This file is not imported or loaded by the script; it is versioned next to the script so historical design context stays discoverable without keeping private artifact citations in runtime comments.

> Runtime contract: do not import this file from Python code. Keep each citation entry to one self-contained paragraph that explains what the cited artifact changed and why the script is marked by it.

## Citation rationale

- **plan-000268 Amendment F**: The coverage checker accepts both the modern `DESIGN_INTENT` convention and the older `DESIGN_INTENT_TO_BE` workspace variable so projects created before the two-file design-intent merge still validate silently during their upgrade window.
