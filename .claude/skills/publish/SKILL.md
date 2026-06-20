---
name: publish
description: "Publish a tagged release to the public SEJA repository via the automated publish pipeline."
argument-hint: "[version] [--dry-run] [--yes]"
compatibility: "Designed for Claude Code with the SEJA harness"
metadata:
  last-updated: 2026-05-01 00:00 UTC
  version: 1.0.0
  category: utility
  context_budget: light
  skip_stages: [pending-check, orphan-check, compaction-check, constitution]
  eager_references: []
  references: []
---

> Overview: see [./SKILL-quickguide.md](./SKILL-quickguide.md)

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `[version]` | No | Version tag to publish (vMAJOR.MINOR.PATCH, e.g., v0.3.0). When omitted, `publish.py` infers the next tag from CHANGELOG.md + git tags and prompts for confirmation. |
| `--dry-run` | No | Preview the full command sequence without executing any destructive actions |
| `--yes` | No | Non-interactive mode: accept all defaults at confirmation prompts |

