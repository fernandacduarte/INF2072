---
designer_description: "When you are maintaining post-skill and need the backstory behind a step or decision -- telemetry schema evolution, the pipeline's monolithic shape, Q&A companion-by-default, section boundary discipline, legacy-layout migration -- I am the sibling file that holds the rationale so SKILL.md can stay tight on execution instructions."
---

# Post-skill rationale

Maintainer-only context for `post-skill/SKILL.md`. NOT loaded at runtime (no entry in `metadata.references`, the sync tool and call-graph generator both ignore this file). Edit both files when rationale changes.

## Telemetry schema evolution

The telemetry record written at step 8b has grown twice under an additive, backwards-compatible contract:

- **14 -> 17 fields** (plan-000295): introduced `qa_type`, `user_revised_output`, and `decision_points` to capture interaction shape, lazy post-hoc revision detection, and per-`AskUserQuestion` rationale-presentation flags.
- **17 -> 18 fields** (plan-000321): introduced `advisory_decisions` so `/research` can record the substance of HIGH/MEDIUM recommendations as structured entries (separate from the `decision_points` list, which only records `AskUserQuestion` interactions).
- **20 -> 21 fields** (plan-000568): introduced `session_id` (Claude Code session UUID from `CLAUDE_SESSION_ID`) to enable correlation of skill invocations within the same conversation session.

Backwards-compatibility invariant (carried verbatim from the SKILL.md body prior to plan-000458 step 8): the new fields are additive. JSON field order is non-significant; well-behaved readers ignore unknown keys. No field has ever been renamed, removed, or retyped. Any telemetry reader that expected the previous 14-field or 17-field record continues to parse newer records as a JSON object and can safely ignore the new keys. This invariant is what lets `/reflect` and future downstream tools run against a mixed telemetry stream without version gates.

Design intent: the schema is extended via plan-N, not revised in place. When a new field becomes necessary, add it at the end of the record with a fallback default (`null`, `[]`, `"single-prompt"`) so older readers remain correct. Avoid breaking changes.

## Pipeline pattern rationale

Post-skill is 13 steps in a single monolithic pipeline (plus pre-skill's 8 stages -- paired by design). The full lifecycle is readable in one file so maintainers can trace "what happens after a skill finishes" without hopping across micro-hooks. Decomposing into per-step hook files would add file count and configuration without solving an actual problem.

See `.claude/references/general/harness-governance.md § Governance > Architectural Decisions > Pre/post-skill monolithic pipelines` for the canonical ruling. Revisit only if a step needs independent versioning, at which point the `skip_stages` mechanism (the pre-skill analogue) would extend to post-skill.

## Q&A companion-by-default

Post-skill step 3 emits a sibling `<prefix><id>-qa-<slug>.md` companion file collocated with the parent artifact. Parent skills opt into inline embedding via `skip_qa_log: true` only when the parent's primary content shape *is* a Q&A transcript -- currently only `/research`.

Rationale (advisory-000423): two structural reasons.

1. **Maintainer-class collision**. Plans are schema-fixed Agent files; design intent and ux research are `Human (markers)` enforced by `check_human_markers_only.py` and `check_changelog_append_only.py`. An Agent-injected inline Q&A region inside any of these either breaks the classification model or demands per-artifact exemptions.
2. **`/reflect` diff-signal protection**. The `user_revised_output` field diffs the parent across commits to detect human edits. An Agent-written Q&A region inside the parent corrupts that signal unless `/reflect` learns a masking convention.

Companion files keep the parent diff narrow and the maintainer-class boundary intact. See also `.claude/references/general/harness-governance.md § Governance > Architectural Decisions > Q&A capture: companion-by-default with narrow inline opt-out`.

## Section boundary discipline

Post-skill step 2 writes to `project/product-design-as-coded.md`, which has three H2 domain sections: `## Conceptual Design`, `## Metacommunication`, `## Journey Maps`. Writes must stay within one H2 section per `Edit` call; multi-section updates require multiple Edits.

Rationale (SEJA 2.8.4, plan-000269): the unified as-coded file was produced by merging the three prior `-as-is.md` files. To keep domain ownership legible after the merge, `check_section_boundary_writes.py` (invoked at post-skill step 6c) rejects any single contiguous write region that spans two or more H2 sections. Anchor-based `Edit` using H3 heading text (rather than line numbers) keeps rewrites deterministic as the file grows.

The executional instruction stays in SKILL.md (step 2d's Section-boundary-discipline callout). This file records why that rule exists.

## Legacy-layout migration

The Branch-3 WARNING emitted at step 2b (when `project/product-design-as-coded.md` is missing but any of `conceptual-design-as-is.md`, `metacomm-as-is.md`, `journey-maps-as-is.md` exist on disk) is the SEJA 2.8.4 migration signal.

Two supported migration paths (see `seja-public/CHANGELOG.md § 2.8.4`):

- **Option 1**: run `/seja-setup --upgrade` to let the harness instantiate `project/product-design-as-coded.md` from `template/product-design-as-coded.md` and move relevant content out of the three legacy files.
- **Option 2**: manually instantiate `project/product-design-as-coded.md` from the template, copy the live content over, and delete the three legacy files.

The warning text itself (which the agent emits verbatim) stays in SKILL.md because it is the agent-visible output. This file records the migration context so maintainers can update the warning when the migration window closes or extend it if a future unification demands a third branch.

## Human-markers enforcement at step 2e

The step 2e callout states "Markers on `ux-research-results.md` and `product-design-as-intended.md` must go through `apply_marker.py` (both Human (markers))."

Enforcement detail (extracted from the SKILL.md body for space): the rule is verified at step 6c by `check_human_markers_only.py` (catches prose mutations in Human (markers) files) and `check_changelog_append_only.py` (catches non-append edits to the `### Changelog` / `## Changelog` sections). The scripts are wired into pre-commit and into `/check validate`. Agents that file markers through `apply_marker.py` pass both checks; agents that hand-edit these files fail and are prompted to abort.

This is the runtime enforcement side of the `Human (markers)` classification documented in `.claude/references/general/shared-definitions.md § File Maintainer Classification` and tabulated in `.claude/references/general/harness-governance.md § Reference File Maintainer Summary`.

## Citation index

Short list of plans and advisories referenced from post-skill's execution rules or historical context.

- `plan-000269` -- SEJA 2.8.4 unification of the three legacy `-as-is.md` files into `product-design-as-coded.md` with H2 domain sections.
- `plan-000295` -- telemetry 14 -> 17 field expansion (`qa_type`, `user_revised_output`, `decision_points`).
- `plan-000321` -- telemetry 17 -> 18 field expansion (`advisory_decisions`).
- `plan-000408` -- `implement` lifecycle: entry filed at `/plan` step 7h, closed at `/implement` rename, safety-net at post-skill step 2g.iv.
- `plan-000444` -- auto-doc default at post-skill step 2b (flip default to Auto-run now with two opt-outs).
- `advisory-000153` -- `/explain` vs `/document` skill-boundary decision (not post-skill execution, but referenced in the separation rationale).
- `advisory-000264` -- the SEJA 2.8 unification arc that produced 2.8.2 (ux-research), 2.8.3 (design-intent), and 2.8.4 (as-coded).
- `advisory-000423` -- Q&A companion-by-default decision (see section above).
- `advisory-000441` / `plan-000444` -- auto-doc step 2b default-flip rationale.

New plan/advisory references added to post-skill rules (or moved into this file) should extend this index.
