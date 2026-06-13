---
designer_description: "When you are writing or reviewing code and want the universal defaults -- small focused functions, intention-revealing names, fail-fast validation, structured logging, the Rule of Three, why-not-what comments, and conventional commit messages -- I'm the reference that codifies them, so every plan and review has one agreed baseline to point at before your project's stack-specific standards take over."
---

# GENERAL - CODING STANDARDS

## Universal Principles

- **Small, focused functions**: prefer ~20 lines or fewer. If a function does more than one thing, extract the parts.
- **Descriptive naming**: use intention-revealing names. Avoid abbreviations unless universally understood (e.g., `id`, `url`, `db`).
- **Error handling**: fail fast. Validate inputs at boundaries; error messages state what failed, why, and how to fix it.
- **Logging**: use appropriate levels (DEBUG for tracing, INFO for key operations, WARNING for recoverable issues, ERROR for failures). Prefer structured logging over ad-hoc prints.
- **Rule of Three**: extract shared logic only when used 3+ times. Three similar lines beat a premature abstraction.
- **Comments**: explain *why*, not *what*. Self-document via naming and structure; comment non-obvious decisions, workarounds, and constraints.

## Review Integration

- For every code change (create or alter), evaluate against applicable engineering and design perspectives in `general/review-perspectives.md`, recording each as adopted, deferred (with reason), or N/A on the plan. If a perspective is deferred only because out-of-scope, ask the user whether to include it.
- If a helper script generated during execution could benefit future plans, write it to `${TMP_DIR}` (see project/conventions.md) with a header describing purpose, usage, and context.
- For detailed Backend, Frontend, Testing, and i18n conventions, see the corresponding H2 sections of `project/standards.md`.

## Git commit messages

Template:

```
<type>[optional scope]: <description>
[optional body]
[optional footer(s)]
```

Commit types:

- `feat`: adds a new feature
- `fix`: fixes a bug
- `refactor`: rewrites/restructures code without adding features or fixing bugs
- `chore`: miscellaneous changes not touching src/test (e.g., deps, `.gitignore`)
- `perf`: refactor aimed at performance
- `ci`: continuous integration
- `ops`: operational components (infrastructure, deployment, backup, recovery)
- `build`: build system, pipeline, dependencies, project version
- `docs`: documentation (e.g., README)
- `style`: formatting-only changes (whitespace, semi-colons) with no semantic impact
- `revert`: reverts a previous commit
- `test`: adds or fixes tests

Rules:

- Limit subject to 50 chars; capitalize; no trailing period.
- Blank line between subject and body; wrap body at 72 chars.
- Use body to explain what and why.
- Use imperative mood in the subject (e.g., "feat: Add unit tests for user authentication").

## Stack-conditional rules

Apply the rule when its stack applies:

- **i18n**: if strings are created/altered, update all affected i18n entries (mind diacritics and accented characters).
- **Frontend**: if frontend files change, update the corresponding contextual help and user docs.
- **Alembic/PostgreSQL**: Alembic migrations must be idempotent and consider Postgres syntax.
- **TypeScript**: frontend source uses `.ts`/`.tsx`; new files must be TypeScript; convert existing `.js`/`.jsx` when modified. See `project/standards.md § Frontend > 21`.
- **Python**: backend source uses Python 3. See `project/standards.md § Backend`.
