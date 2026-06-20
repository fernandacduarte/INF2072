---
designer_description: "Maintainer rationale for reflect_duration_anomalies.py: historical artifact citations and design-choice context extracted from the script body so runtime code stays concise while the audit trail remains self-contained."
---

# reflect_duration_anomalies rationale

Maintainer-only context for `reflect_duration_anomalies.py`. This file is not imported or loaded by the script; it is versioned next to the script so historical design context stays discoverable without keeping private artifact citations in runtime comments.

> Runtime contract: do not import this file from Python code. Keep each citation entry to one self-contained paragraph that explains what the cited artifact changed and why the script is marked by it.

## Citation rationale

- **plan-000295 Step 5**: This primitive was added to detect unusually long skill invocations by comparing current duration against historical medians. It requires a minimum sample size so sparse histories do not create noisy anomalies.
