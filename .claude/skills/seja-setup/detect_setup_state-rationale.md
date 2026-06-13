---
designer_description: "Maintainer rationale for detect_setup_state.py: historical artifact citations and design-choice context extracted from the script body so runtime code stays concise while the audit trail remains self-contained."
---

# detect_setup_state rationale

Maintainer-only context for `detect_setup_state.py`. This file is not imported or loaded by the script; it is versioned next to the script so historical design context stays discoverable without keeping private artifact citations in runtime comments.

> Runtime contract: do not import this file from Python code. Keep each citation entry to one self-contained paragraph that explains what the cited artifact changed and why the script is marked by it.

## Citation rationale

- **plan-000392**: The setup detector recognizes the `--here` download-init workflow, where a workspace can be initialized directly into a target directory. That signal remains part of setup-state detection because it distinguishes partially seeded workspaces from repositories with no SEJA structure at all.
- **plan-000406**: The detector accepts the rename from `/seed` to `/seja-setup` so workspaces created across the naming transition still identify as SEJA workspaces. This keeps setup and upgrade flows backward compatible instead of forcing users to manually rename harness folders first.
- **plan-000433**: The detector accepts the merged `/seja-setup` skill directory after setup and upgrade were combined. It also tolerates the older split directories so legacy installations can be detected and upgraded in place.
