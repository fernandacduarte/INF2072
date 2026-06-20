---
designer_description: "Maintainer rationale for check_docs.py: historical artifact citations and design-choice context extracted from the script body so runtime code stays concise while the audit trail remains self-contained."
---

# check_docs rationale

Maintainer-only context for `check_docs.py`. This file is not imported or loaded by the script; it is versioned next to the script so historical design context stays discoverable without keeping private artifact citations in runtime comments.

> Runtime contract: do not import this file from Python code. Keep each citation entry to one self-contained paragraph that explains what the cited artifact changed and why the script is marked by it.

## Citation rationale

- **advisory-000359**: The lifecycle fact uniqueness scanner excludes prerequisite paragraphs and uses a higher Jaccard threshold because moderately similar setup reminders are useful context, not duplicated lifecycle facts. The rationale matters here because the scanner must catch real doc drift without punishing repeated onboarding cues.
- **plan-000402**: The docs-frontmatter scanner enforces the public documentation metadata contract for Diataxis classification, freshness, and review cadence. The code keeps the parser intentionally flat because the generated and hand-authored frontmatter shape is deliberately simple.
- **plan-000451**: The skill-body-length thresholds were calibrated after the first harness-wide editorial compression pass. They represent a practical baseline for current skill sizes rather than a universal limit, and waivers remain available for bodies that have a justified reason to stay longer.
- **plan-000458**: The skill body scanner learned to detect rationale drift after the compression work extracted historical citations and architectural prose into sibling files. The same migration established the pattern of keeping execution instructions in SKILL.md and moving maintainer history out of the runtime body.
- **plan-000466**: The Quick Guide extraction moved designer-facing narrative out of SKILL.md into SKILL-quickguide.md siblings. `check_docs.py` enforces the pointer and uses the shared loader so help surfaces and docs generators all read the same sibling contract.
- **plan-000475**: The mode-factoring work introduced `_internal` worker skills for wrapper-owned flows. The harness integrity scan excludes those internal SKILL.md files from user-skill checks because they are read inline by wrappers and are not standalone user-invocable skills.
