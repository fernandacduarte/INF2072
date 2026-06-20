---
designer_description: "Maintainer rationale for apply_marker.py: historical artifact citations and design-choice context extracted from the script body so runtime code stays concise while the audit trail remains self-contained."
---

# apply_marker rationale

Maintainer-only context for `apply_marker.py`. This file is not imported or loaded by the script; it is versioned next to the script so historical design context stays discoverable without keeping private artifact citations in runtime comments.

> Runtime contract: do not import this file from Python code. Keep each citation entry to one self-contained paragraph that explains what the cited artifact changed and why the script is marked by it.

## Citation rationale

- **plan-000268 Amendment A1**: This amendment widened STATUS marker handling so Phase 3b promotion can replace legacy uppercase `IMPLEMENTED` markers instead of stacking new lowercase markers above them. The script keeps the compatibility path because older design-intent files may still carry uppercase markers, while current lifecycle processing uses lowercase state-machine values.
- **plan-000265**: The old argparse help text used a real private plan ID as a shape example for `--plan`. The migration replaces that with placeholders so public users learn the accepted format without being pointed at a private artifact they cannot resolve.
