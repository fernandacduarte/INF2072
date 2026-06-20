---
designer_description: "Maintainer rationale for migrate_to_global_ids.py: historical artifact citations and design-choice context extracted from the script body so runtime code stays concise while the audit trail remains self-contained."
---

# migrate_to_global_ids rationale

Maintainer-only context for `migrate_to_global_ids.py`. This file is not imported or loaded by the script; it is versioned next to the script so historical design context stays discoverable without keeping private artifact citations in runtime comments.

> Runtime contract: do not import this file from Python code. Keep each citation entry to one self-contained paragraph that explains what the cited artifact changed and why the script is marked by it.

## Citation rationale

- **advisory-000431**: The global-ID migrator preserves the historical `advise` skill to `advisory` artifact-prefix mapping even after the user-facing skill became `/research`. That explicit mapping prevents old artifact IDs from being renamed to an incompatible prefix.
