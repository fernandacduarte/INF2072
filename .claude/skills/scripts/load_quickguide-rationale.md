---
designer_description: "Maintainer rationale for load_quickguide.py: historical artifact citations and design-choice context extracted from the script body so runtime code stays concise while the audit trail remains self-contained."
---

# load_quickguide rationale

Maintainer-only context for `load_quickguide.py`. This file is not imported or loaded by the script; it is versioned next to the script so historical design context stays discoverable without keeping private artifact citations in runtime comments.

> Runtime contract: do not import this file from Python code. Keep each citation entry to one self-contained paragraph that explains what the cited artifact changed and why the script is marked by it.

## Citation rationale

- **plan-000466**: The quickguide loader is the single helper for reading SKILL-quickguide.md siblings after Quick Guide prose moved out of SKILL.md. Centralizing the path and fallback behavior keeps `/help`, call graph generation, and documentation checks aligned.
