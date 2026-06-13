---
designer_description: "Maintainer rationale for check_changelog_append_only.py: historical artifact citations and design-choice context extracted from the script body so runtime code stays concise while the audit trail remains self-contained."
---

# check_changelog_append_only rationale

Maintainer-only context for `check_changelog_append_only.py`. This file is not imported or loaded by the script; it is versioned next to the script so historical design context stays discoverable without keeping private artifact citations in runtime comments.

> Runtime contract: do not import this file from Python code. Keep each citation entry to one self-contained paragraph that explains what the cited artifact changed and why the script is marked by it.

## Citation rationale

- **plan-000267 Amendment 1 and Amendment 2**: The append-only checker was shaped by the UX research consolidation, where generated tools may append lifecycle or changelog entries but must not rewrite human-authored historical rows. It registers both template and project paths and applies section-specific growth rules so discovered journeys and changelogs remain auditable.
