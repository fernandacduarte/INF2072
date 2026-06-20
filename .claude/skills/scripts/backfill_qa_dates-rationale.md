---
designer_description: "Maintainer rationale for backfill_qa_dates.py: historical artifact citations and design-choice context extracted from the script body so runtime code stays concise while the audit trail remains self-contained."
---

# backfill_qa_dates rationale

Maintainer-only context for `backfill_qa_dates.py`. This file is not imported or loaded by the script; it is versioned next to the script so historical design context stays discoverable without keeping private artifact citations in runtime comments.

> Runtime contract: do not import this file from Python code. Keep each citation entry to one self-contained paragraph that explains what the cited artifact changed and why the script is marked by it.

## Citation rationale

- **advisory-000058, plan-000014, check-000051**: The QA filename examples document the difference between a real QA companion filename and a slug that merely contains `-qa-`. The examples were illustrative only; the scanner behavior is driven by filename shape rather than by any specific historical artifact.
