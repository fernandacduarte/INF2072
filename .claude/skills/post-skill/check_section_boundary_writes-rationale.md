---
designer_description: "Maintainer rationale for check_section_boundary_writes.py: historical artifact citations and design-choice context extracted from the script body so runtime code stays concise while the audit trail remains self-contained."
---

# check_section_boundary_writes rationale

Maintainer-only context for `check_section_boundary_writes.py`. This file is not imported or loaded by the script; it is versioned next to the script so historical design context stays discoverable without keeping private artifact citations in runtime comments.

> Runtime contract: do not import this file from Python code. Keep each citation entry to one self-contained paragraph that explains what the cited artifact changed and why the script is marked by it.

## Citation rationale

- **plan-000267 Amendment 1**: The registry includes both template and project paths because the UX research and design files exist in both harness-source and project-instantiated locations. That dual-path shape lets preflight protect generated templates and live project references with the same rule.
- **plan-000269 Amendments A-D**: The section-boundary checker was refined around the unified as-coded file. It treats diff hunks as multiple change runs, gives preamble content its own section, handles H2 insertion and deletion deliberately, and skips first-write cases so ordinary post-skill updates are blocked only when they cross domain boundaries.
- **plan-000271**: The legacy `product-design/as-coded.md` path remains registered during the workspace upgrade window. Keeping it in the registry protects older workspaces until the setup upgrade path has removed the pre-unification file layout.
