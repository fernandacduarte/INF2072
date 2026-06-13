**What it does**: Publishes a tagged release to the public SEJA repository. Wraps `tools/publish.py`, which handles the full lifecycle: preflight checks, tag creation, cloning the public repo, syncing harness files, running smoke tests, committing, pushing, and closing the pending PUBLISH: entry. Supports version inference from CHANGELOG.md heuristics (bump hints, subsection analysis) or an explicit version argument.

**Examples**:
> `/publish v0.3.0`
> Publishes version v0.3.0 -- runs preflight, cuts the tag, clones the public repo, syncs, smoke-tests, commits, and pushes.

> `/publish`
> Infers the next version from CHANGELOG.md and git tags, confirms with you, then runs the full pipeline.

> `/publish --dry-run`
> Previews the full command sequence without executing any destructive actions. Useful for verifying the pipeline before a live run.

> `/publish v0.3.0 --yes`
> Non-interactive publish -- accepts all confirmation prompts automatically.

**When to use**: When you are ready to cut a public release. Prerequisites: `seja-public/CHANGELOG.md` has content under `## Unreleased`, working tree is clean, and the remote is reachable. Run `/check preflight` beforehand if you want a quality gate.

**Not for**: Internal harness iteration (just commit normally), changelog authoring (edit `seja-public/CHANGELOG.md` directly), or harness upgrades in consumer projects (use `/seja-setup --upgrade`).

**Next step**: Verify the release on GitHub, then optionally graduate `.claude/CHANGELOG.md`'s `[Unreleased]` section to a new internal version heading.
