---
designer_description: "Maintainer rationale for <script>.py: historical artifact citations and design-choice context extracted from the script body so runtime code stays concise while the audit trail remains self-contained."
---

# <script> rationale

Maintainer-only context for `<script>.py`. This file is not imported or loaded by the script; it is versioned next to the script so historical design context stays discoverable without keeping private artifact citations in runtime comments.

> Runtime contract: do not import this file from Python code. Keep each citation entry to one self-contained paragraph that explains what the cited artifact changed and why the script is marked by it.

## Citation rationale

- **plan-NNNNNN**: One paragraph summarizing what the artifact changed and why this script carries the resulting design choice. The paragraph must be self-contained enough that a public consumer can understand the rationale without resolving the private artifact.
