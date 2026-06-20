---
designer_description: "When you run a skill that fans out across many independent work items -- one per audience segment, one per role-and-level pair -- I'm the reference that codifies the six-phase orchestration pattern those batch modes follow, so pre-skill runs once, IDs are reserved up front, shared context is loaded once, N agents execute in parallel, failures are collected honestly, and post-skill closes the whole batch as a single unit."
---

# FRAMEWORK -- BATCH EXECUTION PATTERN

> Canonical reference for skills that parallelize work across multiple subagents.
> Used by: `/communicate` (`--all`), `/onboard` (`--batch`). Any skill needing parallel subagent orchestration should follow this pattern.

## Pattern Overview

Skills generating multiple independent outputs (e.g., one per audience segment, one per role/level combination) use this 6-phase pattern to avoid duplicating orchestration boilerplate.

## Phases

### Phase 1: Run pre-skill once

Run `/pre-skill` a single time for the entire batch, not per work item.

### Phase 2: Reserve IDs upfront

Before launching parallel work, reserve all output IDs with `python .claude/skills/scripts/reserve_id.py --type <artifact-type> --title '<slug>'` once per work item. Prevents ID conflicts when subagents write concurrently; each call returns a globally unique 6-digit zero-padded ID.

### Phase 3: Prepare output folder and load shared context

Compute the date-versioned output folder (`<output-dir>/<YYYY-MM-DD>`, UTC) and create it if missing. Read all shared references and project context (conceptual design, conventions, style config) into a single context block distributed to every subagent, avoiding redundant reads.

### Phase 4: Launch N agents in parallel

Spawn one Agent tool call per work item in a single message so they execute in parallel. Each agent receives:

- The pre-loaded shared context from Phase 3
- Its specific work item parameters (audience segment, role, level, name, focus area, etc.)
- The reserved ID and output file path from Phase 2
- The full single-mode skill instructions for generation and output

### Phase 5: Collect, verify, and handle failures

After all agents complete, verify each expected output exists, report a completion summary (N succeeded, M failed), and list missing or incomplete outputs.

**Failure isolation**: agents run independently -- one failure does not abort the batch. Successful outputs are preserved; the user is notified of partial results and can re-run the skill for just the failed items.

### Phase 6: Run post-skill once

Run `/post-skill` a single time for the entire batch; the hook stages all generated files in a single git commit.

## Key Principle: Bookend Lifecycle Hooks

Pre-skill and post-skill wrap the entire batch, not individual items:

```
pre-skill (once)
  -> reserve IDs (N times)
  -> load shared context (once)
  -> launch N agents (parallel)
  -> collect results
post-skill (once)
```

This yields a single brief entry and a single atomic commit for the batch.

## When to Use

Use when a skill generates 2+ independent outputs from a single invocation, each producible without dependency on others, and all committable atomically.

## When NOT to Use

Do not use when outputs depend on each other (sequential), when there is only one output (single-agent is simpler), or when work requires interactive user input between items.

## Interaction Before Launch

If any work item spec is incomplete (e.g., missing required arguments), do NOT launch agents. Present all incomplete specs to the user for resolution first, then launch all agents at once. Interactive prompts must be fully resolved before the parallel phase.
