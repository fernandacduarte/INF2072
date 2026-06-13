---
designer_description: "Maintainer rationale for generate_macro_index.py: historical artifact citations and design-choice context extracted from the script body so runtime code stays concise while the audit trail remains self-contained."
---

# generate_macro_index rationale

Maintainer-only context for `generate_macro_index.py`. This file is not imported or loaded by the script; it is versioned next to the script so historical design context stays discoverable without keeping private artifact citations in runtime comments.

> Runtime contract: do not import this file from Python code. Keep each citation entry to one self-contained paragraph that explains what the cited artifact changed and why the script is marked by it.

## Citation rationale

- **advisory-000448**: The macro index recognizes Research headers as the forward-looking output type after the advisory-to-research rename. The parser keeps the historical relationship out of the code body while continuing to index current research artifacts correctly.
