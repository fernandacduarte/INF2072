---
designer_description: "When you are maintaining designer-copy-voice.md and need the backstory -- why the rubric exists, which plan-000426 session shipped the call-graph viewer side panel, the governing encoding and priv/public pointers, and which generator hook consumes the extracted prose -- I am the sibling file that holds the rationale so designer-copy-voice.md can stay tight on voice and encoding rules."
---

# Designer Copy Voice -- Rationale and Historical Context

Maintainer-only context for `.claude/references/general/designer-copy-voice.md`. NOT loaded at runtime (no entry in any `metadata.references`, the sync tool and call-graph generator both ignore this file). Edit both files when rationale changes.

## Origin and motivation (plan-000426)

`designer-copy-voice.md` is the authoring guide for the 167-node designer-description backfill and for every future node that enters the call-graph. The call-graph viewer's right-hand panel renders whatever the rubric produces verbatim.

- Origin: plan-000426 "Manual actions" (the session that shipped the viewer and surfaced the badge).
- Origin detail: plan-000426 section "Manual actions" and section "Voice tips" -- the session that shipped the call-graph viewer side panel and surfaced the 174-node backlog.

## Non-applicable file types -- extractor follow-up

`.yaml` and `.json` files under `.claude/references/template/` are out of scope for the rubric. Extractor support for non-`.md` template files is a separate follow-up flagged in plan-000426.

## Encoding-conformance gate (plan-000427)

LLM-drafted prose introduces typographic substitutions (em-dash, en-dash, curly quotes) silently. Step 12 of plan-000427 codifies the grep-for-forbidden-code-points check as an explicit gate across all 167 targeted files. The rubric body references the check in-place; this entry records the plan that made it a gate.

## Related references

- Governing encoding rules: `.claude/references/general/report-conventions.md`.
- Priv-public split: `.claude/references/general/harness-governance.md` section Private-Only Content Convention.
- Generator hook: `.claude/skills/scripts/priv/generate_call_graph.py` (`_parse_frontmatter_designer_description`, `_extract_python_designer_description`, `compute_node_description`).
