---
designer_description: "Maintainer rationale for check_telemetry.py: historical artifact citations and design-choice context extracted from the script body so runtime code stays concise while the audit trail remains self-contained."
---

# check_telemetry rationale

Maintainer-only context for `check_telemetry.py`. This file is not imported or loaded by the script; it is versioned next to the script so historical design context stays discoverable without keeping private artifact citations in runtime comments.

> Runtime contract: do not import this file from Python code. Keep each citation entry to one self-contained paragraph that explains what the cited artifact changed and why the script is marked by it.

## Citation rationale

- **plan-000468 and advisory-000448 Rec 5**: The telemetry schema keeps dual-key aliases for the advisory-to-research rename during the transition window. Inline TRANSITION anchors remain next to the affected enum and field definitions, while the full rationale lives here so maintainers know when and why those legacy aliases can eventually be removed.
