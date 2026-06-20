---
name: seja-setup-upgrade-internal
description: "Inlined worker for /seja-setup Upgrade Flow. Not user-invocable."
compatibility: "Designed for Claude Code with the SEJA harness"
metadata:
  internal: true
  category: internal
  version: 1.0.0
---

> This is an inlined worker; execute these instructions as part of the caller's flow. The wrapper at `.claude/skills/seja-setup/SKILL.md` has already run the Entry-Point Routing dispatch; execute the steps below as part of the `/seja-setup` skill's flow.

## Upgrade Flow

> **Precondition**: target is in `finalised` (or user-confirmed `partial-init`) state with `.claude/`, `product-design/conventions.md`, and `.seja-version` (or legacy no-pin fallback). Entry-point routing has already redirected or refused `dev-repo-refuse`, `no-harness`, and `fresh-download`.

Runs from the **target project** (not the source repo). Applies safe updates to project-independent files and preserves project-specific customizations.

> **Scaffolding-migration note**: Upgrade never re-runs the Section 1 scaffolding questionnaire. Per the File Classification table below, `product-design/**` is classified "Never overwrite" -- your existing `conventions.md` is preserved unchanged. Projects finalised before the scaffolding move (those whose `conventions.md` still carries `{{VAR}}` placeholders) will retain those placeholders through the upgrade; run `/design update stack` afterwards to fill them and regenerate downstream artifacts (CLAUDE.md, rules, smoke-test infra) via the named scaffolding anchors. Greenfield and brownfield legacy projects both route through the same migration path.

### File Classification

| Category | Files | Overwrite? | Action |
|----------|-------|------------|--------|
| Skills | `.claude/skills/*/SKILL.md` | Yes | Auto-update |
| General references | `.claude/references/general/*.md` | Yes | Auto-update |
| Templates | `.claude/references/template/**` | Yes | Auto-update |
| Harness metadata | `.claude/CHANGELOG.md`, `VERSION`, `CHEATSHEET.md` | Yes | Auto-update |
| Scripts | `.claude/skills/scripts/*.py` | No -- hardcoded project paths | Show diff, manual merge |
| Agents | `.claude/agents/*.md` | Mostly -- may have local tweaks | Show diff, ask per file |
| Rules | `.claude/rules/*.md` | No -- project-specific conventions | Show diff, manual merge |
| Project definitions | `product-design/**` | Never | Skip |
| Settings | `.claude/settings.json`, `settings.local.json` | Never | Skip |
| Output directory | `_output/` (or configured) | Never | Skip |
| CLAUDE.md | `CLAUDE.md` | Never | Skip |

### Steps

1. **Resolve target version**: `python .claude/skills/seja-setup/resolve_seja_version.py [--version <tag>]` (default: latest SemVer tag on `simonedjb/seja`). Capture the resolved tag for steps 3 and 5; surface the `HEAD` fallback warning if emitted. If resolved tag matches current `.seja-version`, print "Harness already up to date at `<tag>`" and exit.

2. **Locate SEJA source repo**: if a path is provided, trust the user has it at the desired tag. Otherwise `git clone --depth 1 --branch <resolved-tag> https://github.com/simonedjb/seja <temp-dir>` (drop `--branch` if resolved ref is `HEAD`). On clone failure, ask for a local path.

3. **Validate source repo**: confirm it contains `.claude/skills/` with skill definitions and `product-design/` with reference files.

4. **Read project conventions**: read `project/conventions.md` for output-directory name and other project-specific paths.

5. **Run upgrade script**: `python .claude/skills/scripts/upgrade_harness.py --from <source-path> --target . --new-version <resolved-tag>`. Add `--dry-run` for preview. Omit `--new-version` only on the pre-release HEAD fallback path. The script reads existing `.seja-version` for the banner's "from" half and writes the resolved tag on success.

6. **Review summary**: highlight public-release pin change (e.g., `v0.1.0 -> v0.2.0`), internal harness version change, old-layout migration if any, new convention variables, files auto-updated vs needing manual merge.

7. **Show diffs for manual-merge files**: unified diff for each script/rule/agent that differs. For agents: ask "Accept source / Keep current / Show diff?" per file. For scripts and rules: show diff and advise on merge.

8. **Offer follow-up actions**:
   - New convention variables -> "Add to your `project/conventions.md`?"
   - Old path references -> "Update the references?"
   - Stale CLAUDE.md -> "Regenerate your CLAUDE.md?"
   - `${QA_LOGS_DIR}` (default `_output/qa-logs/`) contains files matching `^<prefix>-\d{6}-qa-.*\.md$` (legacy centralized layout) -> "Post-skill now collocates QA logs with the parent artifact, not `${QA_LOGS_DIR}`. Migrate N detected files via `python .claude/skills/seja-setup/migrate_qa_logs_to_parent_dirs.py --apply`? (safe, uses `git mv` to preserve history, `--dry-run`-previewable.)"

9. **Clean up**: remove the temp clone directory if one was created.

10. **Post-upgrade summary**:
    > Upgrade complete.
    >
    > - Pinned to `<resolved-tag>` (recorded in `.seja-version`)
    > - N files auto-updated
    > - N files need manual merge (diffs shown above)
    > - N new files added
    > - Reference files regenerated (harness-reference.md, skills.md, perspectives.md)
    >
    > Run `git diff` to review all changes before committing.
