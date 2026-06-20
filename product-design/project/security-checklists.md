# SECURITY CHECKLISTS — fernanda-INF2072

> Local research CLI tool. Minimal attack surface. Checklists focus on secrets hygiene and safe dependency use.

---

## Quick Reference — Validation Constants

| Field | Value | Notes |
|-------|-------|-------|
| Minimum benchmark seeds | 5 | Statistical validity |
| Maximum ghost count | 4 | Tractable MARL |
| Minimum training steps | 10,000 | Meaningful learning signal |

---

## Checklist A — Secrets Hygiene

- [ ] No API keys, tokens, or passwords in source files
- [ ] `.env` files excluded via `.gitignore`
- [ ] No hardcoded model server URLs or cloud credentials

## Checklist B — Dependency Safety

- [ ] All dependencies pinned in `requirements.txt`
- [ ] `pip-audit` run before major dependency updates
- [ ] PyTorch and BenchMARL versions documented in `requirements.txt`

## Checklist C — Checkpoint Safety

- [ ] Model checkpoints loaded only from local researcher-specified paths
- [ ] No automatic download of remote checkpoints without explicit user confirmation
- [ ] Checkpoint paths validated before `torch.load()` call

## Checklist D — Output Safety

- [ ] Output directories are timestamped to prevent silent overwrite of prior results
- [ ] No experiment output written outside `benchmarl_setup/runs/` without explicit flag

---

## N/A Checklists

The following standard checklists do not apply to this project:

- Auth / JWT (no authentication)
- CSRF / XSS / SQL injection (no web layer)
- File upload validation (no user file uploads)
- Rate limiting (no API)
- SSRF (no user-supplied URLs)
- PII / GDPR (no personal data processed)
