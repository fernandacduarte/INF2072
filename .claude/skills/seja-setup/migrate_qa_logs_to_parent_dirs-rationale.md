---
designer_description: "Maintainer rationale for migrate_qa_logs_to_parent_dirs.py: historical artifact citations and design-choice context extracted from the script body so runtime code stays concise while the audit trail remains self-contained."
---

# migrate_qa_logs_to_parent_dirs rationale

Maintainer-only context for `migrate_qa_logs_to_parent_dirs.py`. This file is not imported or loaded by the script; it is versioned next to the script so historical design context stays discoverable without keeping private artifact citations in runtime comments.

> Runtime contract: do not import this file from Python code. Keep each citation entry to one self-contained paragraph that explains what the cited artifact changed and why the script is marked by it.

## Citation rationale

- **advisory-000366**: The QA-log migration example illustrates the companion-file naming convention: post-skill QA logs are collocated next to their parent artifact, while standalone QA logs remain in the central QA directory. The specific historical ID is not needed for runtime behavior.
