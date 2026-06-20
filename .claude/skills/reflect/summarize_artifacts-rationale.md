---
designer_description: "Maintainer rationale for summarize_artifacts.py: historical artifact citations and design-choice context extracted from the script body so runtime code stays concise while the audit trail remains self-contained."
---

# summarize_artifacts rationale

Maintainer-only context for `summarize_artifacts.py`. This file is not imported or loaded by the script; it is versioned next to the script so historical design context stays discoverable without keeping private artifact citations in runtime comments.

> Runtime contract: do not import this file from Python code. Keep each citation entry to one self-contained paragraph that explains what the cited artifact changed and why the script is marked by it.

## Citation rationale

- **plan-000295**: The artifact resolver accepts both fully qualified and bare IDs so callers can summarize a known artifact without remembering its directory. The concrete historical example is illustrative only and has been replaced with a placeholder.
