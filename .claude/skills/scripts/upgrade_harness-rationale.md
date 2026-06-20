---
designer_description: "Maintainer rationale for upgrade_harness.py: historical artifact citations and design-choice context extracted from the script body so runtime code stays concise while the audit trail remains self-contained."
---

# upgrade_harness rationale

Maintainer-only context for `upgrade_harness.py`. This file is not imported or loaded by the script; it is versioned next to the script so historical design context stays discoverable without keeping private artifact citations in runtime comments.

> Runtime contract: do not import this file from Python code. Keep each citation entry to one self-contained paragraph that explains what the cited artifact changed and why the script is marked by it.

## Citation rationale

- **plan-000466**: Harness upgrades collect SKILL-quickguide.md siblings because Quick Guide prose is part of the shipped user-facing skill surface. Missing these siblings would make upgraded workspaces lose their help narrative.
- **SKILL-rationale pattern**: Harness upgrades also collect SKILL-rationale.md siblings because maintainer rationale files are versioned with the skill source. They are not loaded at runtime, but they are part of the public harness source when self-contained.
