---
designer_description: "Maintainer rationale for reflect_decision_reversals.py: historical artifact citations and design-choice context extracted from the script body so runtime code stays concise while the audit trail remains self-contained."
---

# reflect_decision_reversals rationale

Maintainer-only context for `reflect_decision_reversals.py`. This file is not imported or loaded by the script; it is versioned next to the script so historical design context stays discoverable without keeping private artifact citations in runtime comments.

> Runtime contract: do not import this file from Python code. Keep each citation entry to one self-contained paragraph that explains what the cited artifact changed and why the script is marked by it.

## Citation rationale

- **plan-000295 Step 5**: This primitive was added as part of the `/reflect` primitive taxonomy. It compares accepted decision points against later reversals so the reflection report can surface changes in direction without prescribing a corrective action.
- **plan-000271**: The artifact label example used a real plan ID only to show the output shape. The implementation formats labels generically from the record skill and id, so the concrete example belongs in rationale rather than runtime prose.
