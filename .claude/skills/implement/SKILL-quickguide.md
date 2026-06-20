**What it does**: Runs a previously approved plan step by step. Three execution modes: **auto** (default) dispatches each step to a fresh subagent with isolated context, **manual** runs sequentially in your current context with per-step confirmation, and **roadmap** executes all plans in a roadmap wave by wave. Creates a rollback branch before starting. Includes a Quality Gate at the end (validation, code review, tests, and smoke tests if configured).

**Examples**:
> `/implement 000042`
> Auto mode (default): executes each step of Plan 000042 in a fresh subagent. Reports progress between iterations. Quality Gate runs at the end.

> `/implement 000042 --manual`
> Manual mode: executes steps sequentially in the current context. You confirm each step before it proceeds.

> `/implement --roadmap 000316`
> Reads roadmap 000316, identifies plans across waves. Executes Wave 0 sequentially, pauses for review, then proceeds through remaining waves.

> `/implement --roadmap 000316 --checkpoint plan --max-iterations 10`
> Roadmap mode with per-plan pauses and a 10-iteration cap per plan's auto mode.

> `/implement 000042 --dry-run`
> Previews what each step would create or modify without writing any files.

Advanced: `--skip-checks` skips the Quality Gate; `--skip-docs` suppresses the automatic documentation prompt (files a pending entry instead); `--checkpoint wave|plan|none` controls roadmap pause granularity.

**When to use**: You have reviewed a plan (created by `/plan`) and are ready to have the agent carry it out. Use auto mode (default) for most plans, especially those with more than 6 steps. Use `--manual` for small plans or when you want per-step confirmation. Use `--roadmap` when you want to execute all plans in a roadmap wave-by-wave without manually triggering each one.

Auto mode follows a TDD red-green cycle for steps with explicit `Tests:` fields (write failing test first, then implement until it passes) and includes a generator-critic loop (max 2 retries) for critical code-review findings. Manual mode retains test-after ordering -- the user's presence is the quality checkpoint.

**Next step**: `/check` (validate, review, and tests run automatically unless `--skip-checks` was used). Documentation generation for qualifying plans runs automatically via post-skill unless `--skip-docs` was passed. After that: `/pending` to review pending actions, or `/reflect` to surface patterns across recent work.

**See also**: `/plan` to create a plan first, `/check` for standalone quality checks, `/document` for standalone documentation.
