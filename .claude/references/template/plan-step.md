---
designer_description: "When /plan generates a structured step inside the ## Steps section of a plan file, I'm the canonical step format -- title, self-contained description, Files / References / Depends on / Verify / Tests / Docs / Traces metadata, checkbox -- and the decomposition guidelines that keep each step executable by a fresh subagent without shared context."
---

# Template: Plan Step Format

Canonical shape referenced by: `.claude/skills/plan/SKILL.md` step 3 (Step format section).

## Step shape

Each step must be self-contained -- executable by a subagent with no shared context from prior steps.

```markdown
## Steps

### Step 1: <short imperative title>
<What to do -- a self-contained description that a subagent can execute without reading other steps.
Include enough context that the step makes sense in isolation: what the code should do, not just which file to edit.>
- **Files**: <path> (create|modify|delete), <path> (modify), ...
- **References**: <reference-name>, <reference-name>, ...
- **Depends on**: Step N, Step M *(omit line when no dependencies)*
- **Interface**: <expected public surface for dependency-producing steps (e.g., "exports `UserService` with `find_by_id(id: str) -> User | None`")> | N/A
- **Verify**: <how to know this step succeeded -- e.g., "tests pass", "migration runs forward and backward", "endpoint returns 200">
- **Tests**: <what tests to create or update -- e.g., "Add unit tests for new service method", "Update existing API tests for changed response format"> | N/A (no testable code changes)
- **Docs**: <what documentation to create or update> *(omit line entirely when N/A)*
- **Traces**: REQ-xxx, REQ-yyy *(omit line entirely when N/A)*
- [ ] Done
```

## Decomposition guidelines

- Each step must be completable in one subagent context window (rule of thumb: touches <=5 files). Split larger steps.
- **Files**: every path the step reads, creates, modifies, or deletes. Verify existing files during planning.
- **References**: only `product-design/` files relevant to this step (e.g., `project/standards.md § Backend` for Python; `project/standards.md § Frontend` for React). Omit irrelevant refs.
- **Depends on**: step numbers whose output this step requires. Omit the field entirely for independent steps (absent = no dependencies). Orchestrators use this to avoid executing before dependencies complete.
- **Interface**: populate for steps that create modules, services, or functions consumed by downstream steps in the same plan. List the expected public surface (function names, class names, exported types with signatures). `N/A` for leaf steps or steps with no downstream consumers within the plan. When present and `Tests:` is non-N/A, auto-mode subagents use this as a type contract when writing the TDD failing test (TDD is triggered by non-N/A `Tests:`, not by `Interface:`).
- **Verify**: a concrete, testable condition. Prefer automated checks ("tests pass", "linter clean") over subjective ones.
- **Tests**: required for FEATURE/FIX/REFACTOR steps that create or modify source code files. `N/A` for doc/config/harness-only steps. When too small to warrant its own tests, indicate which step's tests will cover it. For steps where TDD applies (non-N/A `Tests:` in auto mode), express the test scenario as an observable behavior: "when X, returns Y" rather than a structural assertion ("module exports class Z") or bare test names. This lets the subagent write a meaningful failing test before implementation.
- **Docs**: include for FEATURE/REDESIGN steps that create or modify user-facing code or public APIs. Specify what documentation to create or update (e.g., "Update API reference", "Add contextual help page"). Omit for internal refactors, test-only changes, config.
- **Traces**: include when the step implements a design requirement. Comma-separated REQ IDs from `product-design-as-intended.md` (e.g., `REQ-ENT-001, REQ-PERM-003`). Omit when no REQ markers exist or the step does not trace to one. See `general/shared-definitions.md` for the REQ ID convention.
- Order steps so dependencies flow forward (Step 2 depends on Step 1, not the reverse).
