# SEJA-Claude Changelog

All notable changes to the SEJA-Claude harness are documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

<!--
  Unified version namespace policy (plan-000547, supersedes advisory-000418):
  From this entry forward, ONE version heading per release serves both the
  internal harness record and the public seja release. There is no longer a
  separate public-mirror entry (e.g., ## [0.x.y]). Both repos use the same
  version number. SemVer allows gaps; the public repo jumped from v0.2.0 to
  the next internal version (see seja-public/CHANGELOG.md for the gap note).
  Historical dual entries below (## [2.13.0] / ## [0.3.0], etc.) are
  preserved as-is; do not alter them.
-->

## [0.5.0] -- 2026-05-04 14:11 UTC

### Added

- **`/reflect --deep` interactive transition graph**: replaces the static viz.js renderer with a Cytoscape.js graph (cdnjs UMD, no ES-module import). Nodes are sized proportionally to invocation count with rounded-rectangle shape; edges are weighted by transition frequency. Interactions: drag nodes, scroll/pinch to zoom, pan, hover tooltips (invocation count on nodes; source→target transition count on edges), click-to-highlight neighbourhood, Reset view button. Self-loops use the `loop` curve style.
- **Tol 2012 "muted" qualitative palette** covering all 13 SEJA skills (`research`, `plan`, `implement`, `check`, `document`, `communicate`, `reflect`, `pending`, `publish`, `explain`, `design`, `advise`, `seja-setup`). Replaces the 7-class Viridis sequential scale that left six skills encoded in `#999999`. Every entry is verified WCAG 2.0 AA compliant (≥ 4.5:1 text contrast at 11 px) and validated colorblind-safe for deuteranopia, protanopia, and tritanopia. `LIGHT_FILL_SKILLS` frozenset exported from `reflect_colors.py` as the single source of truth for dark-text skills.
- **Event-matrix x-axis gap compression**: when consecutive events are separated by more than 24 hours, the gap is collapsed to a 120-minute stub on the compressed quantitative axis. Each collapsed gap is marked with a vertical gray dashed rule and a small rotated duration label (e.g., "2d 3h"). Session-date labels appear at the left edge of each activity cluster via `axis.values` + `axis.labelExpr` (nested ternary, valid Vega expression syntax). Labels for sessions narrower than 60 compressed minutes are suppressed to prevent overflow. Gap compression activates automatically; windows with no gaps fall through to the original temporal axis unchanged.

### Changed

- Transition graph node shape changed from circle to `round-rectangle`. Node width scales with invocation count (floor set per-node from label character width; `_label_min_width()` measures both label lines). Height is fixed at 46 px (2 × line-height + padding). A monotonicity sweep after sizing ensures that any node with more invocations is at least as wide as every lower-count node regardless of label length or rounding.
- Event-matrix HTML page no longer emits a `<title>` element or `<h1>` tag; the Vega-Lite chart's own `title` field is the sole title.
- Harness metrics: 51 scripts, 558 unit tests, 17 skills, 16 agents.

### Fixed

- Transition graph HTML previously used `<script type="module">` to import viz.js from the `@viz-js/viz` CDN — blocked by browsers when opening local `file://` URLs due to CORS. Replaced with viz.js 2.x UMD via cdnjs plain `<script>` tags, then superseded by the Cytoscape.js rewrite.
- `axis.labelExpr` in the gapped event-matrix spec previously used a JavaScript object-literal lookup (`{...}[key]`) which is not valid Vega expression syntax, causing a silent compile error that left the chart blank. Fixed by replacing with a nested ternary chain (`datum.value == N ? 'date' : ...`).
- Session date labels overlapped chart bars (positioned at `y: {value: 0}` inside the plot area). Moved to the x-axis label row via `axis.values` + `axis.labelExpr`.
- Gap duration labels were invisible (clipped inside chart, `angle: -90`). Replaced with `angle: 0`, `clip: false`, `y: {value: -4}` floating above the plot in a 20 px top-padding strip.

## [0.4.1] -- 2026-05-02 03:20 UTC

### Added

- `check_harness_drift.py` script: compares a canonical source harness against a target workspace to detect added, removed, or revised files. (plan-000553)
- `check_worktree_health.py` script: detects orphaned git worktrees from parallel wave execution. (plan-000553)
- `generate_pending_roadmap.py` script: queries the pending ledger for open implement entries and generates a wave-assigned roadmap with file-overlap-based grouping. (plan-000558)
- `/implement --pending` flag: auto-generates a roadmap from pending implement entries and hands off to the existing `/implement --roadmap` pathway. (plan-000558)
- `/check health --source <path>` option: wires harness drift detection into the health evaluator agent. (plan-000553)
- Parallel worktree execution support for roadmap waves. (research-000557)
- Tests for `check_harness_drift.py` and `generate_pending_roadmap.py`. (plan-000553, plan-000558)

### Changed

- **Priv-only scripts relocated to `scripts/priv/`**: `bump_version.py`, `check_no_private_leaks.py`, `generate_call_graph.py`, `generate_harness_reference.py`, `generate_perspectives_reference.py`, `generate_skills_reference.py`, `scan_public_docs_for_filenames.py`, and their rationale files moved to a priv-only subdirectory excluded from public sync. (plan-000554)
- Preflight checks gate on file existence for priv-only scripts, gracefully skipping when absent. (plan-000554)
- Pre-commit hook path updated for relocated leak checker. (plan-000554)
- Call-graph output redirected to `_output/docs/`. (plan-000554)
- Call-graph and harness-reference regenerated with new script paths. (plan-000554)
- `check_docs.py` updated to find reference generators in `priv/`.
- `upgrade_harness.py` updated to probe `priv/` for reference generators.
- Harness metrics: 46 scripts, 533 unit tests, 17 skills, 16 agents.

## [0.4.0] -- 2026-05-02 00:03 UTC

### Fixed

- `publish.py`: `unreleased_has_content()`, `parse_bump_hint()`, and `_unreleased_subsections()` now match both `## Unreleased` and `## [Unreleased]` heading forms. Previously only the bare form was matched, causing false "empty Unreleased section" preflight errors when the CHANGELOG used Keep-a-Changelog bracket notation.

## [0.3.0] -- 2026-05-01 21:39 UTC

First release under the unified version namespace (plan-000547). Internal version [2.13.0] and public version [0.3.0] are the same release; from this point forward, both repos use the same version number.

### Added

- `/publish` skill and `tools/publish.py` 8-step lifecycle (preflight, cut tag, clone public, copy prose, sync harness, smoke test, commit, push). (plan-000533)
- `sync_to_public.py --target` argument and pub-only marker support; root-level CLAUDE.md generation from priv. (plan-000533, plan-000544)
- Roadmap workflow: pending entry filing/closing at finalization and `/implement --roadmap` completion, orphan cleanup, compaction warning. (plan-000531)
- Post-skill telemetry/metadata fields and context-filtering with top-N cap on next-step suggestions. (plan-000530, plan-000543)
- `pending.py --format banner` and `--formatted` output modes; pre-skill banner integration. (plan-000534, plan-000541)
- Unified D-NNN decision entries inline in `/research` step 9b; `document-generator` wires `drr` doc-type to D-NNN entries; retired the standalone `decision-entry.md` template. (plan-000539)
- `SKILL-reference.md` companion pattern for post-skill (extracted static schemas to keep SKILL.md lean). (plan-000541)

### Changed

- **Framework → Harness terminology rename** across rules, references, scripts, agents, tutorial, and code identifiers. (plan-000525, plan-000535, plan-000537)
- **DRR (Decision Record Recommendation) replaces ADR** across the harness, references, tools, and tutorial. (plan-000526)
- **Split model**: `seja-public` no longer mirrors `.claude/`; consumers receive only the public-authored prose. (plan-000533, plan-000544)
- Pre-skill SKILL.md merged stages (8 → 6). (plan-000534)
- Post-skill SKILL.md slimmed by referencing `SKILL-reference.md` companion. (plan-000541)
- Refactored `/plan` SKILL.md as a thin wrapper dispatching to `_internal/plan/{standard,light,roadmap}/SKILL.md`. (plan-000475)
- `/research` output files: new invocations emit `research-<id>-*.md` under `_output/research-logs/`. (advisory-000448, plan-000449)

### Removed

- Retired `decision-entry.md` template (decision-entry instructions inlined into `/research` step 9b). (plan-000539)
- `seja-public/.claude/` mirror directory. (plan-000533)

## [2.13.0] -- 2026-05-01 21:39 UTC

Internal-version graduation alongside the v0.1.0 public release. Captures the framework→harness terminology rename, split-model decoupling of seja-public, decision-log unification (DRR), and lifecycle-hook streamlining since 2.12.1. Internal and public version namespaces are intentionally decoupled (advisory-000418).

### Added

- `/publish` skill and `tools/publish.py` 8-step lifecycle (preflight, cut tag, clone public, copy prose, sync harness, smoke test, commit, push). (plan-000533)
- `sync_to_public.py --target` argument and pub-only marker support; root-level CLAUDE.md generation from priv. (plan-000533, plan-000544)
- Roadmap workflow: pending entry filing/closing at finalization and `/implement --roadmap` completion, orphan cleanup, compaction warning. (plan-000531)
- Post-skill telemetry/metadata fields and context-filtering with top-N cap on next-step suggestions. (plan-000530, plan-000543)
- `pending.py --format banner` and `--formatted` output modes; pre-skill banner integration. (plan-000534, plan-000541)
- Unified D-NNN decision entries inline in `/research` step 9b; `document-generator` wires `drr` doc-type to D-NNN entries; retired the standalone `decision-entry.md` template. (plan-000539)
- `SKILL-reference.md` companion pattern for post-skill (extracted static schemas to keep SKILL.md lean). (plan-000541)

### Changed

- **Framework → Harness terminology rename** across rules, references, scripts, agents, tutorial, and code identifiers. File renames: `rules/framework-structure.md` → `references/general/harness-governance.md`, `generate_framework_reference.py` → `generate_harness_reference.py`, `agents/framework-health-evaluator.md` → `agents/harness-health-evaluator.md`, `upgrade_framework.py` → `upgrade_harness.py`, plus 30+ test fixture renames. (plan-000525, plan-000535, plan-000537)
- **DRR (Decision Record Recommendation) replaces ADR** across the harness, references, tools, and tutorial. (plan-000526)
- **Split model**: `seja-public` no longer mirrors `.claude/`; consumers receive only the public-authored prose. `.claude/` and root-level `CLAUDE.md` are generated by `sync_to_public.py` at publish time. Leak checker adapted for split model. (plan-000533, plan-000544)
- Pre-skill SKILL.md merged stages (8 → 6 — `orphan-check` and `compaction-check` became sub-steps of `budget-eval`), stripped catalog prose, and compressed body. (plan-000534)
- Post-skill SKILL.md slimmed by referencing `SKILL-reference.md` companion; `harness-structure.md` slimmed to a lean inventory; new `harness-governance.md` created with extracted governance content. (plan-000541)
- Refactored `/plan` SKILL.md as a thin wrapper dispatching to `_internal/plan/{standard,light,roadmap}/SKILL.md` worker skills via the Mode factoring pattern Dispatch B. Wrapper body reduced from 419 to 122 lines; per-mode workflow prose relocated verbatim. `generate_call_graph.py` extended with `skill-internal` node type and `dispatches-inline` edge type; call-graph viewer gains a dedicated filter. (plan-000475)
- `/research` output files: new invocations emit `research-<id>-*.md` under `_output/research-logs/` with header `# Research <id> | ...`. Historical `advisory-<id>-*.md` files under `_output/advisory-logs/` are preserved in place; read-path scripts scan both folders and both filename prefixes. (advisory-000448, plan-000449)

### Removed

- Retired `decision-entry.md` template (decision-entry instructions inlined into `/research` step 9b). (plan-000539)
- `seja-public/.claude/` mirror directory and the redundant duplication of harness scripts/skills/agents/tests in the public repo. (plan-000533)

### Counts since 2.12.1

- Scripts: 50 (was 64 before split model removed the `seja-public/.claude/` mirror).
- Unit tests: 505 (up from 270).
- Active skills: 17. Active agents: 16.
- 99 commits, 58 files added, 355 deleted (mostly the seja-public/.claude/ mirror), 36 renamed.

## [0.3.0] -- 2026-05-01 21:39 UTC

Public minor release on the `seja` repository. Builds on the existing v0.2.0 entry in `seja-public/CHANGELOG.md` with the work from internal version [2.13.0]. Internal and public version namespaces are intentionally decoupled (advisory-000418); this entry mirrors the user-facing portion of [2.13.0] above.

### Added

- Full lifecycle skill set: `/research`, `/plan`, `/implement`, `/check`, `/document`, `/communicate`, `/reflect`, `/explain`, `/onboard`, plus utility skills `/seja-setup`, `/publish`, `/help`, `/pending`, `/qa-log`.
- Agent-design framework with metacomm framing, advisory-driven quality gates, and DRR (Decision Record Recommendation) decision logs.
- Reference materials: general references, project templates, review perspectives (Essential and Deep-dive tiers), onboarding role/level matrix, and audience-segmented communication templates.
- Helper scripts: validation checks, index generators, harness reference generation, call-graph generation (Mermaid + interactive viewer), telemetry, and migration utilities.

### Changed

- `/plan` is a thin wrapper dispatching to `_internal/plan/{standard,light,roadmap}/SKILL.md` worker skills (Mode factoring pattern Dispatch B). (plan-000475)
- `/research` output files emit under `_output/research-logs/`. (plan-000449)
- `/seed` skill renamed to `/setup` (breaking change -- no backward-compat alias). (plan-000406, advisory-000405)

## [2.12.1] -- 2026-04-17 00:08 UTC

### Added

- History-aware `/document --auto-detect` with per-doc-type SHA-anchored bounding (proposal-000368, advisory-000366). The skill now reads `${BRIEFS_INDEX_FILE}` to find the last successful `/document` run per doc-type and bounds the change-detection window accordingly. Two new nullable columns (`Head SHA`, `Generated`) added to `briefs-index.md`. New flags: `--since <ref>` (override bounding window), `--full-history` (ignore windows, revert to unbounded). First-run and fresh-clone scenarios fall through to unbounded behavior automatically.
- New step 2b in `/document` Core Workflow and Harness Changelog Workflow: records `| SHA | <head-sha> | GENERATED | <doc-types>` metadata on the STARTED entry in `briefs.md` before post-skill runs. Parsed by `generate_briefs_index.py` into the new index columns.
- SEJA for Developers spoke appendix for the slide tutorial (`55-spoke-developers.md` in en-US and pt-BR).

### Changed

- `generate_briefs_index.py`: replaced `_extract_plan_id` with `_extract_trailing_metadata` that chains extraction of GENERATED, SHA, and PLAN suffixes from the end of the raw brief line. Backward-compatible -- existing rows render with empty `Head SHA` and `Generated` cells. Script count: 64 (unchanged). Unit test count: 270 (unchanged).
- Harness vocabulary migrated from "as-is / to-be / established" to "as-coded / as-intended / implemented" across all harness-structure documentation and shared definitions (refactor commit `28b0409`).
- `generate_framework_reference.py` stabilized to produce deterministic output across machines by sorting glob results and normalizing path separators.

### Fixed

- `framework-reference.md` output now stable across Windows and macOS due to sorted file enumeration and forward-slash normalization in `generate_framework_reference.py`.

## [2.12.0] -- 2026-04-16 23:41 UTC

### Changed

- `/post-skill` step 3 now writes QA logs next to the artifact they document (e.g., `_output/advisory-logs/advisory-000366-qa-*.md`) instead of centralizing them in `${QA_LOGS_DIR}`. The `output_dir` caller-override passed to `/qa-log` resolves via a prefix→directory table inlined in SKILL.md step 3. `${QA_LOGS_DIR}` (`_output/qa-logs/`) is now reserved exclusively for user-invoked `/qa-log` sessions without a parent artifact. (plan-000367)
- `/qa-log` caller-override documentation updated to describe the collocation pattern. No behavioral change to the skill itself.
- `/upgrade` step 7 ("Offer follow-up actions") now detects legacy-layout QA logs in `${QA_LOGS_DIR}` and offers to migrate them via `migrate_qa_logs_to_parent_dirs.py --apply`.

### Added

- `migrate_qa_logs_to_parent_dirs.py` — idempotent migration script that moves post-skill-generated QA logs from `${QA_LOGS_DIR}` to their parent artifact directories via `git mv`. Dry-run by default; pass `--apply` to execute. Ships with the harness so downstream projects can adopt the new layout on `/upgrade`.

### Migration

Existing projects upgrading to 2.12.0 can migrate their centralized QA logs:

```bash
python .claude/skills/seja-setup/migrate_qa_logs_to_parent_dirs.py          # preview
python .claude/skills/seja-setup/migrate_qa_logs_to_parent_dirs.py --apply  # execute
```

The `/upgrade` skill will also prompt for this migration automatically when it detects legacy-layout files.

## [2.11.1] -- 2026-04-15 18:26 UTC

### Changed

- `/design` interactive questionnaire now reuses an invocation-supplied metacommunication message verbatim: if the user provides a metacomm message as part of the `/design` invocation context (e.g., initial prompt or preceding `/seed` brief), Section 0.1 is treated as already answered and the Final Step is skipped. Avoids re-prompting for content the user already supplied and preserves the metacomm-verbatim rule. Affects `.claude/skills/design/SKILL.md` (v1.0.1) and `.claude/references/template/questionnaire.md` Final Step wording (questionnaire_version unchanged at 6 -- clarification only, no schema change).

## [2.11.0] -- 2026-04-12 22:00 UTC

### Added

- SEJA slide tutorial modular build system (plan-000351) -- manifest-driven slide deck generation replacing the monolithic single-file approach. Each manifest (YAML) declares which slide modules to include, style tokens, and output variants (deck, presenter, handout). `generate_html.py` assembles modules from `_output/tutorial/modules/`, applies per-manifest `theme.css` and `style-tokens.yaml`, and produces audience-specific builds in `_output/tutorial/builds/<variant>/`. Six audience variants shipped: `full-workshop`, `intro-30min`, `cs-audience`, `mixed-audience`, `workshop-format`, `lecture-conceptual`.
- Tutorial content improvements for non-AI audience (plan-000353, advisory-000352) -- rewritten slide modules focusing on semiotic engineering concepts, governance, and design frameworks rather than assuming agentic AI familiarity. Includes calibration poll, pair-share exercises, spoke-specific deep-dives (linguists, designers, philosophers, historians), and a three-act narrative structure.
- Narrated slideshow video generator (plan-000357, advisory-000355) -- `generate_video.py` produces narrated video from slide decks using Playwright screenshots for per-slide PNGs and TTS audio synthesis. Combines PNGs + audio into MP4 via ffmpeg.
- BroadcastChannel cross-window sync for presenter view (plan-000358, advisory-000356) -- the presenter window broadcasts navigation events (`slideChanged`) over a named `BroadcastChannel`, allowing a second browser window (audience view) to follow slide transitions in real time. Includes feedback-loop prevention via a `_fromSync` flag.
- Presenter view numeric go-to navigation -- type a slide number and press Enter to jump directly; Escape to cancel. Visual indicator shows the typed number.
- Touch swipe navigation for mobile slide viewing -- horizontal swipe gestures advance or retreat slides on touch devices.
- `count_loc.py` enhanced with SEJA harness file counting (plan-000339 follow-up) -- new `--framework` and `--heading` options for counting lines across skills, agents, scripts, tests, rules, and references. Supports YAML and Markdown comment markers in LOC counting.
- Externalized CSS and JavaScript for tutorial builds -- `deck-nav.js` (audience navigation), `presenter-nav.js` (presenter navigation + BroadcastChannel), `deck-base.css`, `mermaid-init.js`, and per-mode CSS files (`mode-landscape-only.css`, `mode-portrait-forced.css`) extracted from inline HTML.

### Changed

- Mermaid diagram rendering in presenter view -- 11 fixes across 11 commits addressing: raw code blocks displayed instead of rendered diagrams (HTML-escaping of `<pre><code>` blocks), invisible diagrams on non-active slides, syntax errors from `<<<`/`>>>` in subgraph labels, text clipping at right edge, configurable min/max height, section `overflow-x` cropping, and `.slide-preview` container clipping. The presenter view now correctly renders and sizes Mermaid diagrams inline.
- Video generation pipeline hardened -- switched to Playwright async API to avoid sync-inside-async errors, fixed 24kHz mono audio encoding producing inaudible output, resolved Windows subprocess compatibility by using full paths for marp and ffmpeg executables.
- `generate_html.py` defaults to `--all` when no `--manifest` flag is provided, building every manifest in the `manifests/` directory. Lists available manifests when invoked without arguments.
- Slide screenshots saved to `slide_PNGs/` subfolder instead of the tutorial root directory.
- `conftest.py` test configuration updated -- private modules directory (`scripts/priv/`) added to `sys.path` for test discovery.
- Harness reference documentation regenerated for v2.10.0 timestamp.
- `theme.css` made the single source of truth for all tutorial styles, replacing scattered inline CSS and per-file overrides.
- Script count: 64 → 63. Unit test count: 273 → 268. Skill count: 17 (unchanged). Agent count: 10 (unchanged).

### Removed

- `test_generate_changelog_data.py` from public distribution (`seja-public/`) -- the test file tests a priv-only script and should not have been synced. Excluded from future syncs.
- `plan-000346-priv-only-markers-and-scripts-separation.md` removed (superseded by implementation).

## [2.10.0] -- 2026-04-12 15:22 UTC

### Added

- `/document --type changelog --framework` workflow (plan-000339) -- harness changelog generation mode that runs `generate_changelog_data.py` for structured git history extraction, composes a Keep a Changelog entry inline, and auto-syncs to `seja-public/.claude/CHANGELOG.md`. The script returns commit groups, file diffs, and count metrics as JSON for prose composition.
- Private-only content convention (plan-000346) -- two mechanisms for keeping `seja-priv`-exclusive content out of the public distribution:
  - Paired HTML comment markers (`priv-only-start` / `priv-only-end`) for private content embedded within shared `.md` files. The `sync_to_public.py` `strip_private_sections()` function removes all content between markers (inclusive) when copying to `seja-public/`.
  - `scripts/priv/` directory for entirely private scripts, excluded from sync (`EXCLUDE_DIRS`) and from `collect_source_files()` in `upgrade_framework.py`.
- `check_no_private_leaks.py` validation script (plan-000346) -- scans `seja-public/` for remaining priv-only markers, known private file patterns, and private directory leaks. Registered in `run_preflight_fast.py`. Enhanced with content-fingerprint patterns (plan-000349) to detect private content leaking without markers.
- Artifact-link convention for decision points (plan-000341) -- skills that present `AskUserQuestion` referencing generated artifacts now output a compact "Files for review" block immediately before the question, so users can open and review artifacts before answering. Convention documented in `constraints.md`.
- `/seed` now creates a git commit of the initial harness files before handoff (plan-000340), ensuring the user starts with a clean working tree.
- `tools/README.md` documenting the sync and leak-detection tooling (plan-000349).
- SEJA slide tutorial production roadmap (roadmap-000337) and wave plans (plan-000342/343/344). Marked PRIVATE -- not synced to `seja-public/`.
- 3 new test files with 22 new unit tests: `test_generate_changelog_data.py` (plan-000339), plus expanded coverage in existing test files for fenced code block handling and content-fingerprint patterns. Unit test count: 251 → 273.

### Changed

- `generate_changelog_data.py` moved from `scripts/` to `scripts/priv/` (plan-000346) -- harness changelog generation is a priv-exclusive capability.
- `sync_to_public.py` `strip_private_sections()` now handles fenced code block awareness (46aba9c) -- markers inside fenced code blocks (triple-backtick regions) are preserved as documentation examples, not stripped.
- `check_no_private_leaks.py` enhanced with content-fingerprint detection (plan-000349) -- beyond marker scanning, now detects known private content patterns (file paths, script names) that may leak without markers.
- `/document` SKILL.md updated with `--framework` flag documentation inside priv-only markers (plan-000339, plan-000346).
- Script count: 61 → 64. Preflight fast-check count: 12 → 13 (added `no-private-leaks`).

### Removed

- `generate_changelog_data.py` from public `scripts/` directory (moved to `scripts/priv/`; removed from `seja-public/` by sync exclusion).
- `.claude/references/template/demo/conceptual-design-to-be.md` and `metacomm-to-be.md` (demo file cleanup).

## [2.9.0] -- 2026-04-12 13:00 UTC

### Added

- `/reflect` skill (plan-000295) -- on-demand reflection anchored on specific plans, advisories, or other artifacts. The user picks artifacts from `_output/`, the agent summarizes them, asks an open-ended question, and records the reflection as `_output/reflections/reflection-<id>-<slug>.md`. Includes a `--telemetry` mode for statistical pattern analysis across usage data. 5 reflection analysis primitives: `reflect_decision_reversals.py`, `reflect_duration_anomalies.py`, `reflect_revision_rate.py`, `reflect_sequence_mining.py`, `reflect_stuck_loops.py`. Orchestrated by `generate_reflection_report.py`. Skill count: 16 → 17.
- `generate_decision_digest.py` and `backfill_decision_digest.py` (plan-000323+000324) -- decision digest index (`_output/decision-digest.jsonl`) scanning D-NNN entries in `product-design-as-intended.md` and HIGH/MEDIUM recommendations in advisory logs. The backfill script is idempotent with `--dry-run` support.
- `DECISION_APPEND` marker type in `apply_marker.py` (plan-000322) -- appends new `### D-NNN:` ADR-shaped decision entries to the `## Decisions` section of `product-design-as-intended.md` with auto-assigned IDs. The `/advise` skill step 9b decision-extract proposal flow uses this marker type.
- `/implement --roadmap <id>` wave-runner mode (plan-000332) -- executes all plans in a roadmap wave-by-wave without manual per-plan invocation. Each plan runs via auto mode in a fresh subagent. Pauses between waves for user review (configurable via `--checkpoint wave|plan|none`). Resumable: re-running picks up from the first incomplete item.
- `/onboarding --all`, `--all-levels`, `--all-roles` batch flags (plan-000326) -- generate onboarding plans for all role×level combinations, all levels for one role, or all roles for one level in a single invocation via parallel subagents.
- `--format md|html|both` flag for `/onboarding` skill (plan-000304).
- `/seed` companion workspace option (plan-000310) -- when seeding an existing codebase, the user can now choose between embedding the harness inline or creating a separate companion workspace alongside the codebase. Interactive flow in step 0b asks "Embedded or Companion workspace?" and sets `--workspace` internally.
- SEJA public docs restructuring (roadmap-000276) -- 21 new documentation files in `seja-public/docs/`: `concepts.md` (sign system, profile×pattern, role families, review perspectives, skills overview, decision matrix, harness lifecycle, epistemic stance chapters), `quickstart.md`, `troubleshooting.md`, `foundations.md` + `foundations-assessment.md` (semiotic engineering primer), 4 reference files (`framework-reference.md`, `glossary.md`, `perspectives.md`, `skills.md`), 9 how-to guides (`brownfield-collocated.md`, `brownfield-workspace.md`, `ci-integration.md`, `greenfield-collocated.md`, `greenfield-workspace.md`, `plan-and-execute.md`, `quality-gates.md`, `recipes.md`, `team-and-stakeholders.md`, `upgrade.md`), and `skill-map.md` + `skill-map.svg`.
- `generate_framework_reference.py`, `generate_skills_reference.py`, `generate_perspectives_reference.py` (plan-000281, plan-000289) -- automated reference file generators for SEJA public docs.
- `scan_public_docs_for_filenames.py` (plan-000280) -- docs filename scanner for harness reference generator, used by `check_docs.py`.
- `summarize_artifacts.py` -- artifact summarization utility.
- `upgrade_framework.py` -- script for upgrading a project's SEJA harness files while preserving project-specific data. Supports directory or .zip source, `--dry-run`, idempotent.
- `check_docs.py` plugin-based documentation consistency checker with 6 scanners (plan-000283): harness integrity, path liveness, env vars, command refs, terminology, structural-completeness. Plugin registry in `check_plugin_registry.json`.
- Advisory tags and `advisory_decisions` telemetry field (plan-000320+000321) -- the `/advise` skill now tags advisories; post-skill records `advisory_decisions` in telemetry. Telemetry schema expanded from 14 to 18 fields (14→17 via plan-000295, 17→18 via plan-000321): `qa_type`, `user_revised_output`, `decision_points`, `advisory_decisions`.
- Plan-generation decision point in `/plan --roadmap` workflow (plan-000329) -- after generating a roadmap, offers to create all plans immediately.
- 11 new test files with 120 new unit tests across reflection primitives, harness reference generators, check-docs plugins, telemetry schema, scan-public-docs, macro-index generation, and upgrade-framework. Unit test count: 131 → 251.

### Changed

- Template file renames (plan-000271): `.claude/references/template/design-intent.md` → `product-design-as-intended.md`, `.claude/references/template/ux-research.md` → `ux-research-results.md`, `.claude/references/template/as-coded.md` → `product-design-as-coded.md`. Corresponding project file paths updated everywhere. All skills, agents, scripts, and cross-references updated to use the new names.
- Template file rename (plan-000272): `.claude/references/template/cd-as-is-changelog.md` → `product-design-changelog.md`. Same propagation across all references.
- `apply_marker.py` UX polish (proposal-000270): `--value` now optional at the argparse layer (ESTABLISHED and INCORPORATED are stamp-kind markers that ignore it); `--plan` accepts bare 6-digit ID (e.g., `000267`) and auto-prefixes `plan-`. 6 new tests.
- Onboarding levels consolidated from 5 to 3 (plan-000325): L1 Newcomer + L2 Practitioner → L1 Contributor, L3 Competent stays as L2 Expert, L4 Strategist + L5 Leader → L3 Leader. Reference files renamed accordingly in `.claude/references/general/onboarding/`.
- `/plan` step 7 now uses `AskUserQuestion` tool for the next-step decision point instead of plain text (plan-000330).
- Post-skill as-is alignment condition narrowed (plan-000330) -- only triggers when the plan actually touched implementation files.
- Decision-point rationale phrasing standardized (plan-000335) -- all decision-point options across plan, implement, and advise skills now use "Recommended when / NOT recommended when" instead of "Right when / Wrong when" per the project-wide convention in `constraints.md`.
- `.claude/rules/tests.md` scope expanded (plan-000334) -- added `**/test_*.py` glob to match pytest-convention test files alongside the existing `**/*.test.*` pattern.
- SEJA public docs legacy deletion sweep (plan-000290) -- 42 legacy documentation files removed from `seja-public/docs/` (old architecture/, concepts/, tutorials/, for-designers, for-developers, journeys/, recipes/ batch files) and replaced by the 21 new Diataxis-structured files.
- Internal development references cleaned from `seja-public/` docs (plan-000317) -- removed `_output/` harness references and internal-only pointers.
- Harness `_output` references relocated from public docs (plan-000309).
- Stamp-based interval gating fixed for periodic triggers (0af9bc4) -- content-based staleness check replaces mtime-based check for `skills-manifest.json`.
- `harness-structure.md` reference file maintainer summary updated to reflect all renames and count changes.
- Script count: 45 → 61 (+16 new scripts). Preflight check count: 12 → 16.

### Removed

- `.claude/references/template/design-intent.md` (renamed to `product-design-as-intended.md`).
- `.claude/references/template/ux-research.md` (renamed to `ux-research-results.md`).
- `.claude/references/template/as-coded.md` (renamed to `product-design-as-coded.md`).
- `.claude/references/template/cd-as-is-changelog.md` (renamed to `product-design-changelog.md`).
- 42 legacy documentation files in `seja-public/docs/` superseded by the Diataxis restructuring.
- 4 legacy onboarding level files (`l1-newcomer.md`, `l2-practitioner.md`, `l4-strategist.md`, `l5-leader.md`) replaced by consolidated `l1-contributor.md`, `l2-expert.md`, `l3-leader.md`.

## [2.8.4] -- 2026-04-11 12:00 UTC

### Added

- `.claude/references/template/as-coded.md` -- unified as-is template with three H2 domain sections (`## Conceptual Design`, `## Metacommunication`, `## Journey Maps`). Replaces the three separate as-is files (`conceptual-design-as-is.md`, `metacomm-as-is.md`, `journey-maps-as-is.md`). Classified `Agent` (post-skill writes it after plan execution; designers read-only). Source H2 sections from the three merged files become H3 subsections under the appropriate domain H2; `### 5. Changelog` under `## Metacommunication` is the new home of the metacomm changelog.
- `.claude/skills/post-skill/check_section_boundary_writes.py` -- new preflight validator that rejects any single contiguous write region spanning two or more H2 sections in registered files. Catches the class of bug where a buggy post-skill Edit accidentally modifies an adjacent section. Uses **change-run semantics** (Amendment A): walks each diff hunk body line-by-line and groups consecutive `+`/`-` lines into maximal change runs (context lines terminate a run). Each change run is checked independently against the section map, preventing false-positives where a hunk's context lines span an H2 boundary while the actual edits stay within one section. Extracts H2 sections from BOTH prior and current file versions (Amendment B) to detect cross-section rewrites via H2 deletion. Treats the pre-first-H2 region as an implicit "preamble" section (Amendment C). Silently skips first-write scenarios (new file in diff — Amendment D). Dual-path registry (`SECTION_BOUNDARY_FILES`) with both template and project entries, following plan-000267's pattern.
- 13 new unit tests in `test_check_section_boundary_writes.py` covering: empty-registry warning, within-section edits, cross-section rejection, separate-hunk independence, new-file-in-diff silent pass, non-registered-file skip, append-at-EOF, preamble-only edits allowed (Amendment C), cross-preamble-to-H2 rejection (Amendment C), hunk with two disjoint change runs in one section, hunk with context crossing boundary but edits in one section, pure H2 header insertion allowed (Amendment B), and rewrite deleting an H2 boundary rejected (Amendment B).

### Changed

- `/design` skill now copies one unified `as-coded.md` for brownfield projects instead of three separate as-is files. Step 5c (As-Is Pre-population) populates the `## Conceptual Design` H2 section of the merged file with `### 2. Entity Hierarchy`, `### 4. Permission Model`, and `### 10. Validation Constants` H3 subsections populated from codebase scan results. The other two H2 sections remain as template placeholders; post-skill populates them on first plan execution.
- Post-skill step 2 as-is alignment logic rewritten to target H2 sections within the merged file with a **three-branch discriminator** at the top of step 2b (Amendment F):
    1. **File exists**: incremental edits to the `## Conceptual Design` H2 section via anchor-based `Edit` with `old_string` containing H3 heading text.
    2. **File absent AND no legacy files present**: greenfield / fresh brownfield path, instantiate from `template/as-coded.md`.
    3. **File absent AND any legacy file present**: option-3 migration path, emit a loud warning `legacy as-is layout detected ... Skipping as-is alignment for this plan` and skip as-is alignment entirely (no writes to `as-coded.md`, no writes to legacy files). This matches the CHANGELOG Migration Option 3 promise.
  Steps 2c (Metacommunication) and 2d (Journey Maps) inherit the branch decision from 2b. A new Section boundary discipline note at the end of step 2d documents that writes must stay within one H2 section per `Edit` call and references `check_section_boundary_writes.py`.
- `/explain spec-drift` drift analysis reads the unified `as-coded.md` and extracts `## Conceptual Design` and `## Metacommunication` H2 sections by heading rather than reading three separate files.
- `.claude/references/template/conventions.md` Key Files table: three rows (`CONCEPTUAL_DESIGN_AS_IS`, `METACOMM_AS_IS`, `JOURNEY_MAPS_AS_IS`) collapsed into a single `AS_CODED` row classified `Agent`. To-Be / As-Is Registry two rows updated: `${DESIGN_INTENT}` row as-coded column replaced with `${AS_CODED}`; `${DESIGN_INTENT}` §15 row as-coded column replaced with `${AS_CODED} § Journey Maps` (Amendment G).
- `.claude/rules/harness-structure.md` Group A table: three as-is rows collapsed into one `project/as-coded.md | Agent | Auto-updated by post-skill. Three H2 sections...` row. Narrative paragraph updated to reflect the merge and to introduce the section-boundary enforcement model.
- `check_design_output.py` phrasing-rule scanner now scans the `## Metacommunication` H2 section of `as-coded.md` instead of reading `metacomm-as-is.md` as a whole file. The scanner extracts only the metacomm H2 section so the phrasing rule does not false-positive on the conceptual-design or journey-map sections, which may legitimately use "the user" language.
- Preflight check count: 11 → 12 (added `section-boundary-writes`).
- Unit test count: 118 (plan-000268 baseline) → 131 (+13 new tests).
- Cross-reference updates: `post-skill/SKILL.md`, `explain/SKILL.md`, `implement/SKILL.md`, `check/SKILL.md`, `design/SKILL.md`, `plan/SKILL.md`, `advise/SKILL.md`, `communication/SKILL.md`, `document/SKILL.md`, `onboarding/SKILL.md`, `.claude/agents/communication-generator.md`, `.claude/agents/document-generator.md`, `.claude/agents/onboarding-generator.md`, `.claude/references/general/communication.md`, `.claude/references/general/figma-make-integration.md`, `.claude/references/general/getting-started.md`, `.claude/references/general/onboarding/builders.md`, `.claude/references/general/onboarding/shapers.md`, `.claude/references/template/standards.md`, `.claude/references/template/project-spec.md`, `.claude/references/template/questionnaire.md`, `.claude/references/template/cd-as-is-changelog.md`, `.claude/references/template/agent/entities.yaml`, `.claude/references/template/agent/permissions.yaml`.

### Removed

- `.claude/references/template/conceptual-design-as-is.md` (content moved to `as-coded.md § Conceptual Design`).
- `.claude/references/template/metacomm-as-is.md` (content moved to `as-coded.md § Metacommunication`).
- `.claude/references/template/journey-maps-as-is.md` (content moved to `as-coded.md § Journey Maps`).

### Not Removed

- `.claude/references/template/cd-as-is-changelog.md` -- kept as a separate file. Phase 3 F from advisory-000264 will conditionally embed it into `as-coded.md` in a future release, gated on Phase 1 C (plan-000267) and Phase 2 E (this plan) operating without incidents for one release cycle. Its preamble was updated to reference `as-coded.md § Conceptual Design` as the current-state snapshot.

### Known Limitations

- `.claude/references/template/design-intent.md` and `.claude/references/template/ux-research.md` retain stale prose references to `conceptual-design-as-is.md`, `metacomm-as-is.md`, and `journey-maps-as-is.md` in blockquotes around lines 317, 370, 395 and 106 respectively. Both files are classified `Human (markers)`, so prose edits are rejected by `check_human_markers_only.py`. A follow-up proposal should decide whether template-path entries in `HUMAN_MARKERS_FILES` should be relaxed for harness maintainers (who intentionally update template prose) or whether these specific prose lines should be rewritten via a dedicated escape hatch. The stale references are documentation-only and do not affect runtime behavior, but users who read these blockquotes in a newly-instantiated project will see references to files that no longer exist.
- `.claude/CHANGELOG.md` retains historical references to the three legacy file names in entries from plan-000265, plan-000267, and plan-000268. These are frozen historical records and are intentionally left unchanged.

### Migration

For existing projects that already ran `/design` before 2.8.4, three options are available:

1. **Manual concatenation**: manually concatenate `project/conceptual-design-as-is.md`, `project/metacomm-as-is.md`, and `project/journey-maps-as-is.md` into a single `project/as-coded.md` using the new template's section structure (three H2 domain sections; each source file's content becomes H3+ subsections under the corresponding domain H2).
2. **Back up and re-run /design**: back up the old files and re-run `/design` to regenerate the unified file from the new template. This overwrites any project-specific as-coded content; only use if the implementation state is captured elsewhere.
3. **Continue with the old layout**: post-skill 2.8.4 detects the legacy layout via the three-branch discriminator (Amendment F) and emits a loud warning `legacy as-is layout detected ... Skipping as-is alignment for this plan` on every plan execution, then skips the as-is alignment step entirely (no writes to `as-coded.md`, no writes to the legacy files). The warning repeats until migration. Designers should migrate promptly via Option 1 or Option 2. The harness does not silently write to a fresh `as-coded.md` alongside the legacy files.

## [2.8.3] -- 2026-04-10 23:55 UTC

### Added

- `.claude/references/template/design-intent.md` -- unified design-intent template merging the former `design-intent-to-be.md` (working intent) and `design-intent-established.md` (validated archive) into a single file. 446 lines, 20 H2 sections (§0 Planned Changes through §17 plus `## Decisions` ADR section and `## CHANGELOG`). Preserves all 8 REQ markers from the source files and seeds a `D-001` Decision template entry demonstrating the Nygard shape (Context / Decision / Consequences / optional Supersedes) with a `STATUS: proposed` marker. Classified `Human (markers)` -- prose (working intent, entity hierarchies, metacomm intentions, designed user journeys, Decision rationale) is strictly human-authored; agents write only `STATUS`, `ESTABLISHED`, and `CHANGELOG_APPEND` markers via `apply_marker.py`.
- `.claude/references/template/design-intent.md` AND `product-design/design-intent.md` both registered in `HUMAN_MARKERS_FILES` and `APPEND_ONLY_SECTIONS` per plan-000268 Step 2. Dual-path pattern mirrors the plan-000267 ux-research registration.
- `### Decision entries (ADR)` subsection in `general/shared-definitions.md` documenting the `D-NNN` namespace (orthogonal to `REQ-TYPE-NNN`), the Nygard shape, and the Phase 3a/3b promote workflow. REQ taxonomy table gets a footnote making the orthogonality explicit.
- Phase 3a / Phase 3b promote workflow in `/explain spec-drift --promote`: Phase 3a (`/explain spec-drift --promote`) drafts ADR-shaped Decision entries from plan metadata, writes them to `_output/promote-proposals/promote-proposal-plan-<id>.md`, and queues paired `apply-promote-proposal` + `apply-promote-markers` pending actions (deduped against existing pending pairs for the same plan). Phase 3b (`/explain spec-drift --promote --apply-markers plan-NNNNNN`) heading-only greps `design-intent.md § Decisions` for each proposed D-NNN (`^###\s+D-NNN(?::|\s*$)`, never matching prose), runs per-item `AskUserQuestion` confirmation, invokes `apply_marker.py` on confirmed items to flip STATUS from `implemented` to `established`, and applies precise lifecycle updates (marks `apply-promote-proposal` done only when all proposed entries are present; marks `apply-promote-markers` done only when every present item was flipped successfully). Partial completion leaves `apply-promote-proposal` pending with a "N of M applied" message.
- `test_explain_promote_phase3a_phase3b.py` -- 8 integration tests covering Phase 3a proposal generation, paired pending-action creation, heading-only grep verification, marker flip on present entries, partial-completion lifecycle (Amendment A3), legacy uppercase marker replacement (Amendment A1 + A5), duplicate Phase 3a invocation idempotency (Amendment A3), and non-colon heading form rejection (Amendment A4).
- `test_status_flip_replaces_legacy_uppercase_marker` in `test_apply_marker.py` -- regression test for Amendment A1 widening of `_STATUS_MARKER_RE` to accept legacy uppercase `IMPLEMENTED` so that a Phase 3b flip REPLACES the legacy marker instead of stacking a new lowercase marker above it.
- `test_extract_requirements_ignores_d_nnn_headings` in `test_check_plan_coverage.py` -- regression test for Amendment A2 locking in REQ / D-NNN namespace orthogonality.

### Changed

- `/design` skill: two `design-intent-to-be.md` + `design-intent-established.md` copy directives collapsed into a single `template/design-intent.md` -> `project/design-intent.md` copy with the `Human (markers)` classification note. Key Files table updated. All references to the old split file names replaced with `design-intent.md`.
- `/explain spec-drift --promote`: the legacy single-phase "promote IMPLEMENTED items to established files" workflow replaced by the Phase 3a / Phase 3b split described above. Step B menu option 4 renamed "Promote implemented items" and routed to Phase 3a.
- `/post-skill` step 2c (Design intent curation reminder): output text updated to point designers at `/explain spec-drift --promote` (Phase 3a generates a draft Decision entry proposal; Phase 3b flips the STATUS markers after you apply the prose) instead of the old "move entries from to-be to established" instructions.
- `/post-skill` step 2e (DONE marker proposal): marker format changed from legacy `<!-- STATUS: IMPLEMENTED | plan-NNNNNN | YYYY-MM-DD -->` to the current lowercase scheme `<!-- STATUS: implemented | plan-NNNNNN | YYYY-MM-DD -->`. The "Apply now" branch no longer hedges with "until follow-up plans reclassify real files"; it always routes through `apply_marker.py` for files in `HUMAN_MARKERS_FILES`. Cross-reference note updated to list both `project/ux-research.md` and `project/design-intent.md` as Human (markers).
- `/pending` skill dispatch text for `apply-promote-proposal` and `apply-promote-markers` rewritten to reference the actual Phase 3b command (`/explain spec-drift --promote --apply-markers <source>`) instead of the plan-000265 forward-declaration hedge.
- `apply_marker.py` `_STATUS_MARKER_RE` widened from `[a-z]+` to `[A-Za-z]+` so legacy `STATUS: IMPLEMENTED` markers are detected. `_apply_status` normalizes `IMPLEMENTED` to `implemented` before the transition-allowed lookup, so a flip `implemented -> established` against a legacy marker REPLACES it (not stacks). (Amendment A1)
- `check_plan_coverage.py` now reads the `DESIGN_INTENT` variable from conventions.md with a silent backward-compat fallback to `DESIGN_INTENT_TO_BE` for workspace-mode deployments. Error messages updated to reference `design-intent.md`. (Amendment A2 + A6)
- `check_design_output.py` phrasing-rule scanner now reads `product-design/design-intent.md` with a backward-compat fallback to the legacy path.
- `.claude/references/template/conventions.md` Key Files table: `DESIGN_INTENT_TO_BE` and `DESIGN_INTENT_ESTABLISHED` rows replaced with a single `DESIGN_INTENT` row pointing at `project/design-intent.md` classified `Human (markers)`. `DESIGN_INTENT_TO_BE` retained as a legacy alias row for workspace-mode compatibility (Amendment A6). To-Be / As-Is Registry two design-intent rows collapsed to two `${DESIGN_INTENT}` rows (one for §0-§17 + Decisions + CHANGELOG, one for §15 designed journeys).
- `harness-structure.md`: Group A table two design-intent rows collapsed to one `project/design-intent.md | Human (markers)` row. Narrative paragraph updated to reflect the merge. The "Human (markers) is carried by ux-research.md" note now lists both ux-research.md (since 2.8.2) and design-intent.md (since 2.8.3).
- `shared-definitions.md` Lifecycle Markers: existing "legacy + lowercase STATUS coexistence" paragraph extended to document the widened regex and the design-intent.md lowercase-primary convention.
- `general/getting-started.md`, `general/recipes.md` (Recipe 13 Periodic Curation Sweep), `general/skill-graph.md`, `general/figma-make-integration.md`, `general/onboarding/shapers.md`: all references to `design-intent-to-be.md` / `design-intent-established.md` updated to `design-intent.md`. Recipe 13 rewritten to show the actual Phase 3a + Phase 3b 2026 workflow (replaces the forward-declaration text from plan-000265). Skill graph gains a `/explain spec-drift --promote` -> `/explain spec-drift --promote --apply-markers` edge.
- Unit test count: 108 -> 118 (added 2 regression tests in plan-000268 Steps 3-4 for Amendments A1 and A2, plus 8 Phase 3a/3b integration tests in Step 11 for Amendments A3, A4, A5).

### Removed

- `.claude/references/template/design-intent-to-be.md` (content merged into `design-intent.md` §0-§17).
- `.claude/references/template/design-intent-established.md` (content merged into `design-intent.md § Decisions` ADR section; the `D-001` template entry demonstrates the Nygard shape).

### Migration

For existing projects that already ran `/design` before 2.8.3, three options are available:

1. Manually concatenate the old `design-intent-to-be.md` and `design-intent-established.md` into a single `project/design-intent.md` using the new template's section structure. For any entries already promoted to `established` in the old archive file, add a `### D-NNN:` Decision heading under `## Decisions` and add an `<!-- ESTABLISHED: plan-NNNNNN | YYYY-MM-DD -->` stamp above it. Preserve the designer-authored rationale verbatim.
2. Back up the old files and re-run `/design` to regenerate the unified file from the new template. This overwrites any project-specific working intent and Decision content; only use if your design intent is captured elsewhere.
3. Continue using the two-file layout. `check_changelog_append_only.py` is a no-op for projects that do not have `project/design-intent.md` in the touched set. Existing workflows that read the two old files continue to work: the merged file is not a runtime prerequisite for any skill. Note that new harness features added after 2.8.3 (including the Phase 3a/3b promote workflow) assume the unified layout, so this option is a stopgap.

**Workspace-mode deployments**: projects created via `/seed --workspace` that use the `DESIGN_INTENT_TO_BE` variable in their workspace-owned `project/conventions.md` continue to work transparently via the `check_plan_coverage.py` backward-compat fallback. No stderr deprecation warning is emitted (the fallback is silent by design). The fallback will be removed in a future major release (SEJA 3.0); until then, workspace projects may migrate to `DESIGN_INTENT` at their own pace by editing their `project/conventions.md`.

Manual integration check performed during implementation: the already-committed `.claude/references/template/design-intent.md` was modified via `apply_marker.py --file .claude/references/template/design-intent.md --id D-001 --marker STATUS --value implemented --plan plan-000268 --date 2026-04-10`, the change was staged, and both `check_changelog_append_only.py --staged` and `check_human_markers_only.py --staged` exited 0. This exercises the append-only validator's non-empty-prior-body path (not the new-in-diff bypass). The flip was then reverted.

## [2.8.2] -- 2026-04-10 16:35 UTC

### Added

- `.claude/references/template/ux-research.md` -- unified UX research template with stable paragraph IDs (R-P-NNN personas, R-PS-NNN problem scenarios, existing JM-E-NNN discovered journeys) and an embedded `## CHANGELOG` section. Replaces two separate ux-research-new.md and ux-research-established.md files. 161 lines, 6 H2 sections. First real file classified as `Human (markers)` (plan-000265's test fixture is still registered but is not a real harness artifact).
- `.claude/skills/explain/check_changelog_append_only.py` -- post-skill validator that enforces append-only discipline on designated sections. Two-rule system per plan-000267 Amendment 2: CHANGELOG sections use strict line-level prefix-preserving extension (no middle insertion allowed); §5 Discovered User Journeys uses prose-only prefix-preserving extension (lines matching ALLOWED_MARKERS are filtered out before comparison so apply_marker.py may legally insert INCORPORATED markers above existing JM-E-NNN headings). Registered as the `changelog-append-only` FAST_CHECKS entry in run_preflight_fast.py. 8 unit tests cover the happy path, historical-line modification/removal/middle-insertion rejection, new-file-in-diff silent pass, empty-registry loud warning, marker-line inserted mid-section (prose-only rule), and prose-line inserted mid-section (rejected).
- `.claude/references/template/ux-research.md` AND `product-design/ux-research.md` both registered in `HUMAN_MARKERS_FILES` per plan-000267 Amendment 1. Dual-path pattern: the template path is what `/design` seeds (and harness-level tests touch); the project path is what designer commits exercise via post-skill step 2e. `apply_marker.py` and `check_human_markers_only.py` perform exact-string repo-relative path matching, so both forms must be present. Same dual-path pattern applied to `APPEND_ONLY_SECTIONS` in the new validator.

### Changed

- `/design` skill now copies one unified `ux-research.md` file instead of two during project setup. Copy directive updated with the `Human (markers)` classification note.
- Post-skill step 2e's "Do NOT apply markers to ux-research files" rule is relaxed: agents may now write `INCORPORATED` markers and `CHANGELOG_APPEND` entries to `ux-research.md` via `apply_marker.py` after AskUserQuestion confirmation. Prose content remains human-authored.
- `/explain` skill updated: JM-E-NNN journey references now point at `project/ux-research.md §5` instead of the old `project/ux-research-established.md §5`.
- `harness-structure.md` File Maintainer Summary table: two ux-research rows collapsed to one `project/ux-research.md` row classified `Human (markers)`. The "Human (markers) classification exists but no files currently carry it" note from plan-000265 replaced with a reference to `project/ux-research.md` as the first real consumer.
- `.claude/references/template/conventions.md` Key Files table: `UX_RESEARCH_NEW` and `UX_RESEARCH_ESTABLISHED` rows replaced with a single `UX_RESEARCH` row pointing at `project/ux-research.md` classified `Human (markers)`. To-Be / As-Is Registry ux-research row collapsed to the unified form.
- `.claude/references/template/design-intent-to-be.md` and `.claude/references/template/journey-maps-as-is.md` updated their cross-references to the merged ux-research file.
- Preflight check count: 10 -> 11 (added `changelog-append-only`).
- Unit test count: 100 -> 108 (added 8 tests for the new validator).
- `post-skill/SKILL.md` line 77 (the journey-maps-as-is updater) now cross-references `project/ux-research.md §5` instead of the old established file.

### Removed

- `.claude/references/template/ux-research-new.md` (content moved to `ux-research.md` §1-§4 with stable IDs R-P-NNN, R-PS-NNN).
- `.claude/references/template/ux-research-established.md` (content moved to `ux-research.md §5` with append-only enforcement and Processing Log replaced by per-entry INCORPORATED markers plus the embedded CHANGELOG section).

### Migration

For existing projects that already ran `/design` before 2.8.2, three options are available:

1. Manually concatenate the old `ux-research-new.md` and `ux-research-established.md` into a single `project/ux-research.md` using the new template's section structure (H2 sections 1-5 + CHANGELOG). Assign stable IDs (`R-P-001`, `R-PS-001`, etc.) to existing entries and add a CHANGELOG entry for each.
2. Back up the old files and re-run `/design` to regenerate the unified file from the new template. This overwrites any project-specific research content; only use if your research is captured elsewhere.
3. Continue using the two-file layout. `check_changelog_append_only.py` is a no-op for projects that do not have `project/ux-research.md` in the touched set. Existing workflows that read the two old files continue to work because no skill's runtime path depends on the merged file (the skills that were updated in this plan reference the new path, but they do not crash or fail when the file is absent). Note: new harness features added after 2.8.2 may assume the unified layout, so this option is a stopgap.

The `INCORPORATED` marker scheme is new and only applies to projects that migrate to the unified layout. Projects on the two-file layout continue to use the manual "move entries from new to established" workflow (or no workflow).

Manual integration check performed during implementation: created a scratch `product-design/ux-research.md` with two JM-E-NNN entries in §5, committed the baseline, invoked `apply_marker.py --file product-design/ux-research.md --id JM-E-001 --marker INCORPORATED --value stamp --plan plan-000267 --date 2026-04-10` to insert a marker in the middle of §5, and confirmed both `check_human_markers_only.py --staged` and `check_changelog_append_only.py --staged` exit 0. The scratch file was then reverted. The end-to-end path validates Amendment 1 (dual-path registry) and Amendment 2 (prose-only §5 rule) on live content.

## [2.8.1] -- 2026-04-10 14:50 UTC

### Added

- `.claude/references/template/standards.md` -- unified engineering standards template with H2 sections `## Backend`, `## Frontend`, `## Testing`, `## i18n`. Replaces four separate standards template files. 2445 lines, 70 H3 subsections.
- `.claude/references/template/design-standards.md` -- unified design standards template with H2 sections `## UX patterns` and `## Graphic / visual design`. Replaces two separate design standards template files.
- `_extract_h2_section` helper in `check_design_output.py` and a `Standards section notation` definition in `.claude/references/general/shared-definitions.md` documenting the `§ <Domain> > N` cross-reference convention.
- Three regression tests in `test_check_design_output.py`: `test_backend_framework_in_wrong_section_still_warns` (cross-section contamination), `test_legacy_backend_standards_file_fallback` (backward-compat), `test_neither_standards_file_present_skips_silently` (graceful degradation).

### Changed

- `/design` skill now copies two unified standards files (`standards.md` and `design-standards.md`) instead of six individual files during project setup.
- All skill, rule, and reference documentation cross-references to the old standards files have been updated to point at the new unified files with `§ <Domain>` section notation (e.g., `standards.md § Backend > 6` replaces `backend-standards.md §6`).
- `.claude/references/template/conventions.md` Key Files table replaces `UX_DESIGN_STANDARDS` and `GRAPHIC_UI_DESIGN_STANDARDS` with a single `DESIGN_STANDARDS`, and adds a new `STANDARDS` entry for the merged engineering standards.
- `check_design_output.py` reads the merged `standards.md` and filters by H2 section for backend-vs-frontend-specific framework-propagation checks. Falls back to legacy `backend-standards.md` and `frontend-standards.md` files when the merged file is absent (preserves the value-propagation guardrail for existing projects).
- `check_human_markers_only.py` subprocess call now uses explicit `encoding="utf-8", errors="replace"` to prevent a Windows cp1252 UnicodeDecodeError when the staged diff contains UTF-8 bytes.
- `.claude/references/template/questionnaire.md` section `Fills:` targets updated to point at the merged-file H2 sections; section slugs kept as stable questionnaire identifiers decoupled from file names.

### Removed

- `.claude/references/template/backend-standards.md` (content moved to `standards.md § Backend`)
- `.claude/references/template/frontend-standards.md` (content moved to `standards.md § Frontend`)
- `.claude/references/template/testing-standards.md` (content moved to `standards.md § Testing`)
- `.claude/references/template/i18n-standards.md` (content moved to `standards.md § i18n`)
- `.claude/references/template/ux-design-standards.md` (content moved to `design-standards.md § UX patterns`)
- `.claude/references/template/graphic-ui-design-standards.md` (content moved to `design-standards.md § Graphic / visual design`)

### Migration

For existing projects that already ran `/design` before 2.8.1, three options are available:

1. Manually concatenate the old files into `project/standards.md` and `project/design-standards.md` using the same H2 section structure as the new templates.
2. Back up the old files and re-run `/design` to regenerate the unified files from the new templates (this overwrites any project-specific standards content -- only use if customizations are captured elsewhere).
3. Continue using the old layout -- skills that load standards read template values, so projects that keep `backend-standards.md`, `frontend-standards.md`, etc., continue to work. `check_design_output.py` has been updated to fall back to the legacy filenames if `standards.md` is not present, so the value-propagation guardrails remain active. Note: new harness features added after 2.8.1 may assume the unified layout, so this option is a stopgap, not a long-term path.

Cross-reference notation in existing advisory logs and QA logs will not be rewritten -- a reader following `backend-standards §6` should read it as `standards.md § Backend > 6` under the 2.8.1 layout. See `.claude/references/general/shared-definitions.md` § Notation Conventions for the translation rule.

## [2.8.0] -- 2026-04-10 10:00 UTC

### Added

- New `Human (markers)` classification in the File Maintainer Classification table in `.claude/references/general/shared-definitions.md` and referenced by `.claude/rules/harness-structure.md`. Agent may write fixed-format structured markers only, via `apply_marker.py`, after explicit `AskUserQuestion` confirmation. Enforced by `check_human_markers_only.py`.
- New script `.claude/skills/scripts/human_markers_registry.py` -- shared registry module with `HUMAN_MARKERS_FILES`, `ALLOWED_MARKERS` (STATUS, ESTABLISHED, INCORPORATED, CHANGELOG_APPEND), and path helpers. Initial allowlist contains only a synthetic test fixture; follow-up consolidation plans will reclassify real files.
- New script `.claude/skills/scripts/apply_marker.py` -- sole write path for Human (markers) files. Resolves paths via `Path.resolve(strict=True)` (blocks symlinks and `..`-traversal); validates marker kind, value, STATUS transitions; supports `--dry-run`.
- New script `.claude/skills/scripts/check_human_markers_only.py` -- post-skill verifier that diffs staged or range changes against Human (markers) files and fails on any non-marker hunk. Registered in `run_preflight_fast.py` as the `human-markers` check. Supports `--staged`, `--range`, `--diff-from-file` (the last requires `SEJA_ALLOW_TEST_DIFF_INPUT=1` env var to prevent production misuse).
- New script `.claude/skills/scripts/pending.py` -- pending-actions ledger helper with subcommands `add`, `done`, `snooze`, `dismiss`, `list`, `due`, `cleanup`, `periodic-check`, `status`. First script in the repo to use argparse subparsers. The `status` subcommand (per plan-000265 amendment A8) is a composite call for pre-skill that runs conditional cleanup (24h throttle) and conditional periodic-check (1h throttle) in a single Python process to stay under the per-skill latency budget.
- New pre-skill stage `pending-check` between `compaction-check` and `ref-load`. Runs `pending.py status` once per skill invocation; emits silent / one-line notice / warning block based on pending count and overdue flag. Added to the `skip_stages` allowlist.
- New skill `/pending` at `.claude/skills/pending/SKILL.md` -- interactive management of the pending ledger. Forwards `add|done|snooze|dismiss` subcommands to `pending.py`; for interactive list mode, dispatches items via `AskUserQuestion` based on their `type` field (mark-implemented routes to `apply_marker.py` for STATUS flips; verify/test/update/promote types print guidance and await `/pending done <id>`). Declares `skip_stages: [pending-check, ...]` to prevent recursion.
- New conventions section `## Periodic Triggers` in `.claude/references/template/conventions.md` with configurable intervals: `periodic-curation` (30 days), `spec-drift-check` (14 days), `verify-as-coded file threshold` (5), `pending age escalation` (14 days), `pending auto-dismiss` (90 days).
- New fixture `.claude/skills/scripts/tests/fixtures/marker_fixture.md` -- synthetic Human (markers) file with three entries (R-P-001, R-P-002, D-001) and a `## CHANGELOG` section. Seeded into `HUMAN_MARKERS_FILES` from day one to prevent the empty-allowlist dormant bug and to give the test suite something non-empty to exercise against.
- New permissions.md rule: "Do not use Edit or Write on files classified as Human (markers); use apply_marker.py instead."
- New unit tests: `test_apply_marker.py` (14 cases), `test_check_human_markers_only.py` (10 cases), `test_pending.py` (17 cases), `test_pending_integration.py` (5 cases). Total new tests: 46. All pass (1 skipped for Windows symlink admin requirement).
- Recipe 12 (Deferred Review Workflow) and Recipe 13 (Periodic Curation Sweep) in `.claude/references/general/recipes.md`.
- "Managing deferred work" section in `.claude/references/general/getting-started.md`.
- Skill graph entries linking `/implement`, `/explain spec-drift`, `/design`, `/check validate` to `/pending`, plus reverse edges from `/pending` to `/explain spec-drift --promote` and `/implement`.
- `get_pending_file()` helper in `project_config.py` (lazy function, not module-level constant, to avoid import-time crash when `get_path` returns None).

### Changed

- Pre-skill stage count: 7 -> 8 (added `pending-check`).
- Skill count: 15 -> 16 (14 user-facing + 2 internal hooks). Added `/pending`.
- `.claude/references/general/shared-definitions.md` File Maintainer Classification table now has four values (was three); `Human (markers)` inserted between `Human` and `Human / Agent`.
- Post-skill sub-step `e. DONE marker proposal` AskUserQuestion gains a "Defer for later review" option alongside "Apply now" and "Skip". Choosing defer appends a `mark-implemented` pending action via `pending.py add` instead of applying markers inline.
- Post-skill gains new nested sub-step `g. Pending action creation from plan metadata` under step 2 that auto-creates `verify-as-coded` (for plans with >= 5 files), `test-implementation` (for plans with a Test plan section), and `update-documentation` (for plans whose documentation prompt was skipped) pending actions based on plan metadata.
- Post-skill gains new flush-left sub-step `6c. Human markers verifier` after `6b` that invokes `check_human_markers_only.py --staged` as a pre-commit gate.
- `skip_stages` allowlist extended to include `pending-check`.
- `.claude/rules/harness-structure.md` counts updated to reflect the new stage and skill; "Pre/post-skill monolithic pipelines" ADR paragraph updated.

### Migration

No existing files are reclassified as `Human (markers)` in this release. `HUMAN_MARKERS_FILES` contains only a synthetic test fixture. Follow-up plans (design-intent merge, ux-research merge) will reclassify real files one at a time with confidence, now that the enforcement infrastructure is tested in isolation. See advisory-000264 for the file-consolidation roadmap.

## [2.7.1] -- 2026-04-07 11:01 UTC

### Changed

- Adjusted `what-is-seja.md` to reduce the "absolute self-confidence" poorly expressed when the agent refers to the metacommunication message (from `I know that you` to `I've learned that you`).

## [2.7.0] -- 2026-04-07 00:22 UTC

### Added
- `check_design_output.py` -- validates design output files (5 scanners: entity-permission alignment, section completeness, cross-file consistency, template conformance, variable resolution)
- `test_check_design_output.py` -- unit tests for design output validation
- `check_plan_coverage.py` -- verifies plan steps trace back to design-intent REQ markers; supports `advisory` (informational) and `blocking` (preflight gate) enforcement modes
- `test_check_plan_coverage.py` -- unit tests for plan coverage check
- `bump_version.py` -- atomic version-bump script updating `.claude/skills/VERSION`, `.seja-version`, and validating CHANGELOG heading; supports `--dry-run`
- `figma-make-integration.md` -- guide for using Figma Make alongside SEJA (handoff protocol, intake checklist, MCP Server conventions, token sync)
- Versioning section in `shared-definitions.md` -- documents the three version files (VERSION, CHANGELOG, .seja-version), their distinct purposes, and maintenance rules
- Requirement ID Convention section in `shared-definitions.md` -- defines `REQ-TYPE-NNN` markers for design-intent traceability (ENT, PERM, VAL, UX, MC, JM, I18N, DELTA prefixes)
- `Traces` field in plan step format -- links plan steps to design-intent requirements (`REQ-xxx` IDs)
- Requirements extraction pass in `/plan --roadmap` workflow -- extracts REQ index from design-intent before decomposition
- Coverage check integration in `/plan` (advisory after steps) and `/plan --roadmap` (aggregate after all plans)
- Design output verification pass in `/design` skill -- runs `check_design_output.py` after file generation
- `check_design_output` and `check_plan_coverage` added to `run_preflight_fast.py` preflight pipeline

### Changed
- Script count increased from 39 to 43 (4 new scripts: check_design_output.py, check_plan_coverage.py, bump_version.py, and their tests)
- `check_version_changelog_sync.py` now validates all CHANGELOG `##` headings for `[x.y.z]` bracket format (warns on bare-date headings)
- `.seja-version` dogfood policy: harness repo's `.seja-version` now tracks the current release version (updated from 2.0.0 to 2.7.0)
- Backfilled bare-date CHANGELOG heading `## 2026-03-30 00:00 UTC` as `## [2.0.1] -- 2026-03-30 00:00 UTC`
- `backend-standards.md` template restructured with improved section organization
- `design-intent-to-be.md` template updated with REQ marker placeholders
- `api.md` review perspective expanded with additional CDN questions
- `getting-started.md` expanded with additional onboarding content
- `recipes.md` expanded with new multi-skill workflow recipes
- `/check` semiotic-inspection mode added -- SIM-based communicability evaluation (5-step analysis of metalinguistic, static, and dynamic signs)

## [2.6.0] -- 2026-04-02 00:00 UTC

### Added
- `compatibility` field in all 15 SKILL.md frontmatter files for agentskills.io spec alignment
- `check_skill_spec.py` -- validates SKILL.md files against agentskills.io spec (name rules, description, compatibility, metadata structure)
- `generate_skill_graph.py` -- generates skill-graph.json from skill-graph.md for programmatic skill-dependency lookup
- `generate_skills_manifest.py` -- generates skills-manifest.json (L1 metadata index for fast skill scanning, ~100 tokens per skill)
- `skills-manifest.json` -- L1 metadata index of 13 user-facing skills (name, description, argument_hint, category, version)
- `compaction-check` stage in pre-skill pipeline (non-critical) -- warns when session has many skill invocations; pipeline now has 7 stages (3 critical + 4 non-critical)
- Generator-critic retry loop in `/implement` auto mode -- bounded loop (max 2 retries) when code-reviewer finds critical findings during quality gate; interactive mode unchanged
- Parallel fan-out for `/check preflight` -- launches validate and review as concurrent Agent invocations, synthesizes unified report
- Meta-skills deferral ADR -- documents prerequisites for runtime skill generation (permission inheritance, constitution injection, template factory pattern)
- agentskills.io Spec Alignment section in `harness-structure.md` governance documentation
- Preflight checks for skills-manifest and skill-spec validation in `run_preflight_fast.py`

### Changed
- Script count increased from 35 to 39 (4 new scripts: check_skill_spec.py, generate_skill_graph.py, generate_skills_manifest.py, check_version_changelog_sync.py)
- Pre-skill pipeline expanded from 6 to 7 composable stages
- `generate_cheatsheet.py` now escapes pipe characters in description and argument_hint fields for correct markdown table rendering
- `/check preflight` rewritten with parallel fan-out pattern and failure isolation

## [2.5.0] -- 2026-04-02 00:00 UTC

### Changed
- Questionnaire sections renumbered sequentially by tier order: M->0, 0->1 (renamed "Basic Definitions", slug `quick-start`->`basic-definitions`), 2->2, 8->3, 9->4, 10->5, 1->6, 3->7, 4->8, 5->9, 6->10, 7->11. All question sub-numbers updated to match new section prefixes.
- `/design` skill references migrated from section numbers to slugs for cross-reference stability; `questionnaire_version` bumped from 3 to 6
- Metacommunication message moved from mandatory conceptual-design field (old 2.10) to the questionnaire Final Step; agent now generates a recommended message from prior answers if Section metacomm-message was skipped
- Post-Questionnaire Checklist now uses slug-based references

### Removed
- `.codex/` harness mirror and all Codex-specific files (`AGENTS.md`, `agents-md.md` template, `codex-onboarding-guide.md`, `migrate_claude_to_codex.py`). The harness is now Claude-only.
- `/check health` Check 5 (.claude/.codex sync) removed; remaining checks renumbered (5=Conventions, 6=Constitution). Health report total reduced from 7 to 6.

### Migration (for existing projects)

- **Questionnaire**: consumed once during `/design`; no migration needed for filled-out projects. Old section numbers remain documented in the Version History table.
- **Harness files**: auto-updated by `/upgrade`. Running `/upgrade` will pull the renumbered questionnaire and slug-aware design skill.
- **Existing plans/advisories referencing old section numbers**: numbers in historical documents remain valid as point-in-time records. Prefer slugs in new documents.

## [2.4.0] -- 2026-04-02 13:04 UTC

### Added
- `## 5. Discovered User Journeys` section in `ux-research-established.md` and `ux-research-new.md` -- absorbs `journey-maps-established.md`; uses JM-E-NNN stable IDs, required research citation, Source column, Processing Log; agent-off-limits rule applies to whole file.
- `## 15. Designed User Journeys` section in `design-intent-to-be.md` and `design-intent-established.md` -- absorbs `journey-maps.md`; uses JM-TB-NNN stable IDs, IMPLEMENTED/ESTABLISHED lifecycle markers; §16 (CD Delta) and §17 (Metacomm Delta) renumbered from §15/§16.
- Section column in the To-Be / As-Is Registry (`conventions.md`) -- enables multi-artifact-type files; tools discriminate artifact types by ID prefix (JM-TB-NNN vs JM-E-NNN).

### Changed
- `user-research-established.md` renamed to `ux-research-established.md`; `user-research-new.md` renamed to `ux-research-new.md` -- reflects broader UX research scope.
- `USER_RESEARCH_NEW` and `USER_RESEARCH_ESTABLISHED` variables in `conventions.md` renamed to `UX_RESEARCH_NEW` and `UX_RESEARCH_ESTABLISHED`; file paths updated accordingly.
- `JOURNEY_MAPS` and `JOURNEY_MAPS_ESTABLISHED` variables removed from `conventions.md` (content absorbed into `DESIGN_INTENT_TO_BE §15` and `UX_RESEARCH_ESTABLISHED §5`).
- post-skill step 2d: reads JM-TB-NNN entries from `design-intent-to-be.md §15`; reads JM-E-NNN entries from `ux-research-established.md §5`.
- `/explain spec-drift --promote`: JM-TB-NNN items promote to `design-intent-established.md §15`; JM-E-NNN items noted as research-grounded with no promotion target.
- `/design` Mode 1: generates `ux-research-established.md` and `ux-research-new.md` (not `user-research-*`); no longer generates standalone `journey-maps.md` or `journey-maps-established.md`.

### Removed
- `.claude/references/template/journey-maps-established.md` -- content absorbed into `ux-research-established.md §5`.
- `.claude/references/template/journey-maps.md` -- content absorbed into `design-intent-to-be.md §15`.

### Migration (for existing projects)

- **No breaking changes to existing project data.** Existing `journey-maps.md` and `journey-maps-established.md` files remain functional until migrated.
- **To adopt**: Move `journey-maps.md` JM-TB-NNN entries to a new `## 15. Designed User Journeys` section in `project/design-intent-to-be.md`. Move `journey-maps-established.md` JM-E-NNN entries to a new `## 5. Discovered User Journeys` section in `project/ux-research-established.md`. Rename `project/user-research-*.md` files to `project/ux-research-*.md`. Update `project/conventions.md` variable names and registry.
- **Upgrade path**: run `/upgrade` to pull updated templates; migrate project-specific files manually or via `/design` (update mode).

## [2.3.0] -- 2026-04-02 11:48 UTC

### Added

- `.claude/references/template/journey-maps-established.md` -- third tier of journey maps: research-grounded, human-only, append-only, never agent-modified. Contains `JM-E-NNN` stable IDs, required research citation (method, date, n-count), optional persona/PS-ID fields, Source column in steps table, and Processing Log.
- `JOURNEY_MAPS_ESTABLISHED` variable in `.claude/references/template/conventions.md` (optional; declared always, absent by default).
- To-Be / As-Is Registry section in `.claude/references/template/conventions.md` -- canonical table of all registered to-be/established/as-is file triples; single source of truth for `/design`, `/explain spec-drift`, and post-skill.
- Lifecycle Markers section in `.claude/references/general/shared-definitions.md` -- defines `STATUS: IMPLEMENTED` (prose and table row variants) and `ESTABLISHED:` stamp convention. Agents may read and apply IMPLEMENTED markers; must never alter existing markers.
- post-skill step 2e: DONE marker proposal -- after as-is update, scans registered to-be files for implemented items and proposes `STATUS: IMPLEMENTED` markers via AskUserQuestion.
- `spec-drift --promote` mode in `/explain` -- scans for IMPLEMENTED items across all registered to-be files and promotes confirmed items to their established counterparts with an optional version stamp.

### Changed

- `.claude/references/template/journey-maps.md` (to-be): added `JM-TB-NNN` stable ID field; updated header to link to established file and state one-directional flow rule.
- `.claude/references/template/journey-maps-as-is.md`: added `JM-TB-NNN` anchors in delta tables; added conditional "Delta from Established" section.
- `/explain spec-drift`: now reads the To-Be / As-Is Registry to iterate all registered file pairs instead of hardcoding the design-intent pair. Drift report now includes a "Pending Promotions" section. Step B menu includes "Promote IMPLEMENTED items" option.
- `/design` Mode 1 step 7: now generates `journey-maps-established.md` and `user-research-established.md` during project setup; includes registry-awareness note.
- post-skill step 2e (former `e`): renamed to `f` (include in commit scope); note extended to cover `journey-maps-established.md` as human-maintained.
- CHANGELOG format: entries now include time component (`YYYY-MM-DD HH:MM UTC`) in addition to date.

### Migration (for existing projects)

- **No breaking changes.** All additions are additive. Existing skills degrade gracefully when `journey-maps-established.md` is absent.
- **To adopt the registry:** add the "To-Be / As-Is Registry" section to your `project/conventions.md` by running `/upgrade` or manually copying the section from `.claude/references/template/conventions.md`.
- **To adopt journey-maps-established.md:** run `/design` (update mode) to generate the new template, or manually copy from `.claude/references/template/journey-maps-established.md`.

## [2.2.0] -- 2026-04-02 00:00 UTC

### Added
- Questionnaire Section M (`metacomm-message`): optional early metacommunication message that seeds suggested defaults across subsequent questions (0.1, 0.2, 2.1, 2.10, 2.11)
- Slug reference table in questionnaire header: stable named identifiers for all sections matching template filenames (e.g., `conceptual-design`, `ux-design-standards`, `quick-start`)
- Slug annotations on all section headers in the questionnaire

### Changed
- Questionnaire sections physically reordered into T1 / T2 / T3 tier blocks. Section M appears first (before Section 0) so metacomm defaults are extracted before quick-start questions. Numbers preserved as stable backward-compatible aliases.
- `/design` skill (Mode 1) updated to extract defaults from Section M metacomm message and to reference sections by slug
- Questionnaire version bumped from 3 to 4
- Onboarding guide updated to reference sections by slug; questionnaire description updated to mention 12 sections

### Migration (for existing projects)
- **Questionnaire**: consumed once during `/design`; no migration needed for filled-out projects.
- **Harness files** (`.claude/references/template/`, `.claude/skills/`): auto-updated by `/upgrade`. Running `/upgrade` will pull the slug-aware questionnaire and design skill.
- **Existing plans/advisories referencing "Section N"**: numbers remain valid aliases -- no action required. Prefer slugs in new documents.

## [2.1.0] -- 2026-04-01 00:00 UTC

### Added
- `project/design-intent-to-be.md` — merged single document combining conceptual design (Part I) and metacommunication intent (Part II), replacing the previous two-file model
- `project/design-intent-established.md` — archive of processed design decisions with preserved rationale (human-maintained, never agent-altered)
- `project/user-research-new.md` — user research file for new/planned product contexts (separate from established-product research)
- `project/journey-maps.md` — journey map template for tracking user journeys through planned features
- `project/journey-maps-as-is.md` — agent-maintained implementation-state companion to journey-maps.md (created by post-skill on first plan execution)
- Solution scenarios and user stories as alternative solution representations in design-intent-to-be.md
- Post-skill step 2d: automatic journey-maps-as-is.md maintenance after plan execution

### Changed
- `/design` now generates `design-intent-to-be.md` + `design-intent-established.md` instead of `conceptual-design-to-be.md` + `metacomm-to-be.md`
- User research model corrected: files are now `established` vs. `new` rather than `as-is` vs. `to-be`
- `/advise`, `/explain`, `/implement`, `/plan` reference the new `design-intent-to-be.md` file
- `/seed --demo` demo files updated to reflect new design-intent model

### Removed
- `project/conceptual-design-to-be.md` (merged into `design-intent-to-be.md`)
- `project/metacomm-to-be.md` (merged into `design-intent-to-be.md`)
- Legacy `template/conceptual-design.md` template

## [2.0.1] -- 2026-03-30 00:00 UTC

- Renamed `product-design/` internal structure: files now organized into `general/`, `template/`, and `project/` subdirectories instead of flat files with `general-`, `template-`, `project-` prefixes. Metadata references, scripts, and documentation updated throughout.
- `/implement` quality gate now runs all checks by default (validate, review, test-runner). Previous `--skip-preflight` flag replaced with `--skip-checks`. Roadmap-conclusion gate runs full checks when the last roadmap item completes.
- `/communication` now outputs stakeholder-facing content with dual format: Markdown plus styled HTML, both generated by default (`--format md|html|both`). Next-step recommendations are refined into the content rather than listed. Multi-file subfolder support for audiences with distinct topics. Date-folder index auto-generated when multiple artifacts share the same date.
- `/upgrade` now fetches the foundational SEJA harness directly from GitHub instead of requiring a local copy.
- Skill scanning defaults to codebase root; QA logs centralized in `_output/qa-logs/`.
- Workspace seed resets plan numbering to ensure IDs start at 000001.
- Added Step 14 (Review & next steps) to `/design`: after summary, offers spec review, roadmap generation, or exit. Roadmap auto-derives themes and work items from design intent and metacommunication.
- Updated skill graph: `/design` now suggests `/plan --roadmap` instead of `/help`.
- Removed `/seed --package` (zip packaging). The public repo is now the foundational harness itself. Use GitHub's "Download ZIP" for offline distribution.
- Restructured seja-public/ as a complete foundational harness with docs/ folder.

## [2.0.0] -- 2026-03-29 00:00 UTC

### Added
- Harness upgrade system (`upgrade_framework.py`) for safe project upgrades
- Convention schema diff utility in `project_config.py`
- Semver versioning in VERSION file
- This CHANGELOG
- Upgrade mode in `/quickstart --upgrade`
- Version-bump protocol documentation

### Changed
- References relocated from `.claude/skills/references/` to `product-design/` (migration handled by upgrade script)
- VERSION format changed from plain `version: 1` to semver `version: 2.0.0`

### Removed
- Legacy briefs log format parser (`_LEGACY_RE` in `generate_briefs_index.py`)
- Legacy `lightweight` boolean field validation in `check_skill_system.py`
- Legacy plan format fallback in `implement/SKILL.md`

## [1.0.0] -- 2026-03-27 00:00 UTC (retroactive)

### Added
- Initial SEJA-Claude harness: 19 skills, 24 scripts, 5 agents, 6 rules
- References system in `.claude/skills/references/` (later moved to `product-design/`)
- Template and general reference files
- Project bootstrapping via `/quickstart`
- Packaging via `/quickstart --package`
