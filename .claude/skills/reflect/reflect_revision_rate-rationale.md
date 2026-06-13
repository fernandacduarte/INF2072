---
designer_description: "Maintainer rationale for reflect_revision_rate.py: historical artifact citations and design-choice context extracted from the script body so runtime code stays concise while the audit trail remains self-contained."
---

# reflect_revision_rate rationale

Maintainer-only context for `reflect_revision_rate.py`. This file is not imported or loaded by the script; it is versioned next to the script so historical design context stays discoverable without keeping private artifact citations in runtime comments.

> Runtime contract: do not import this file from Python code. Keep each citation entry to one self-contained paragraph that explains what the cited artifact changed and why the script is marked by it.

## Citation rationale

- **plan-000295 Step 5**: This primitive was added to estimate revision rates per skill by reading telemetry that marks user-revised outputs. The threshold is intentionally simple so `/reflect` can highlight patterns without diagnosing intent.
