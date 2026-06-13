---
designer_description: "I'm your project's security-review checklists -- one list per surface that historically bites, from new endpoints and file uploads to auth flows, CSRF, security headers, and XSS on user-generated content -- so every time you add or change one of those surfaces there is a concrete, ticked-off set of conditions the change has to satisfy before it merges."
---

# TEMPLATE - SECURITY CHECKLISTS

> **How to use this template:** Copy this file to `project/security-checklists.md`. These checklists are largely generic — customize the Quick Reference table with your project's actual validation constants and file paths. Remove checklists that don't apply to your stack.

---

## Checklist A — New Endpoint

- [ ] `@jwt_required()` decorator (unless intentionally public)
- [ ] Authorization check via permission evaluator (admin / member / resource-level)
- [ ] Schema validation for JSON body (no raw `json_data.get()`)
- [ ] Rate limiting on sensitive operations
- [ ] Input validation for user-supplied strings (length, format)
- [ ] Error messages localized — no secrets in error responses
- [ ] Activity log mapping added for state-changing operations
- [ ] CSRF exempt only if endpoint is pre-auth or safe method
- [ ] Redirect targets validated against internal paths only — no open redirects from user input

## Checklist B — File Upload

- [ ] Extension validated against blocklist (executables, scripts, server-side code)
- [ ] Double-extension check (all dot-separated segments, not just last)
- [ ] Magic-byte (file signature) validation — content matches claimed type
- [ ] Filename sanitized via `secure_filename()` — stored with UUID, not original name
- [ ] File size within `MAX_CONTENT_LENGTH`
- [ ] Admin-configurable allowlist checked if configured
- [ ] Display name sanitized (no `\r`, `\n`, `\x00`; max 256 chars)

## Checklist C — User-Generated Content (XSS)

- [ ] HTML sanitized via DOMPurify before `dangerouslySetInnerHTML` (frontend)
- [ ] DOMPurify config: restrictive attribute allowlist
- [ ] Internal links intercepted; `javascript:` URLs blocked
- [ ] Framework's default escaping used for all non-HTML text output
- [ ] CSP header: `script-src 'self'` — no inline scripts allowed
- [ ] i18n interpolation: never render translated output via `dangerouslySetInnerHTML` with user-supplied interpolation values without sanitization

## Checklist D — Authentication Changes

- [ ] Passwords hashed with bcrypt (never plaintext, never reversible)
- [ ] JWT access token: short expiry (e.g., 1 hour)
- [ ] JWT refresh token: longer expiry (e.g., 7 days)
- [ ] JWT tokens stored as HttpOnly cookies — never in localStorage
- [ ] Token revocation on logout (added to blocklist; cookies cleared)
- [ ] Brute-force protection: exponential lockout
- [ ] Rate limiting on auth endpoints
- [ ] Rate limit storage: use Redis or shared store in multi-instance production (not in-memory)
- [ ] Token revocation on privilege changes: revoke all tokens when password, role, or status changes
- [ ] Production config validates secrets differ from dev defaults

## Checklist E — CSRF

- [ ] Double-submit cookie pattern active for state-changing requests (POST/PUT/PATCH/DELETE)
- [ ] Frontend sends CSRF token header (via HTTP client interceptor)
- [ ] Cookie: `SameSite=Lax`, `Secure=True` in production
- [ ] Exempt only: safe methods, pre-auth endpoints, health checks

## Checklist F — Security Headers

- [ ] `X-Content-Type-Options: nosniff`
- [ ] `X-Frame-Options: SAMEORIGIN`
- [ ] `Content-Security-Policy: default-src 'self'`
- [ ] CSP `script-src` does not include `'unsafe-inline'` or `'unsafe-eval'`
- [ ] `Strict-Transport-Security` enabled in production
- [ ] `Referrer-Policy: strict-origin-when-cross-origin`
- [ ] `Permissions-Policy` disables unused APIs (camera, microphone, geolocation)
- [ ] `Cache-Control: no-store` for sensitive responses

## Checklist G — CORS

- [ ] Restricted to `/api/*` routes only
- [ ] Explicit origin allowlist
- [ ] Credentials enabled (`withCredentials: true`)
- [ ] Exposed headers: `Content-Type`, `Authorization`, `Content-Disposition`
- [ ] Production config strips localhost patterns

## Checklist H — Database

- [ ] All queries via ORM (prevents SQL injection)
- [ ] Separate admin credentials for DDL migrations (if applicable)
- [ ] Connection pooling with health checks
- [ ] Soft delete queries always filter `deleted_at.is_(None)`

## Checklist I — Mass Assignment Prevention

- [ ] Every endpoint accepting JSON body validates through a schema — no raw access
- [ ] Schemas explicitly list allowed fields — never use `fields = "__all__"`
- [ ] Sensitive fields (role, status, admin flags, user_id, timestamps) are never writable from client input
- [ ] Update schemas only include fields the user is authorized to change

## Checklist J — Dependency Security

- [ ] `pip audit` / `safety check` run against requirements before each release
- [ ] `npm audit` run against frontend packages before each release
- [ ] No known critical or high CVEs in production dependencies at release time
- [ ] Dependency audit integrated into CI pipeline
- [ ] Dependencies reviewed and updated periodically
- [ ] Lock files committed for reproducible builds

## Checklist K — Secret Management

- [ ] `.env` files listed in `.gitignore` — never committed
- [ ] Pre-commit hook or CI step scans for secret patterns
- [ ] Any secret accidentally committed is rotated immediately
- [ ] Production secrets stored in environment variables or secrets manager
- [ ] Production config rejects known dev defaults
- [ ] Database credentials, JWT secret, and SMTP credentials unique per environment

## Checklist L — SSRF Prevention

- [ ] If any endpoint accepts URLs from user input:
  - [ ] Validate URL scheme is `http` or `https` only
  - [ ] Block private/internal IP ranges (`127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`)
  - [ ] Block cloud metadata endpoints (`169.254.169.254`)
  - [ ] Set connection timeouts and response size limits
  - [ ] Use an allowlist of trusted domains when possible

## Checklist M — Logging & Monitoring Security

- [ ] Log messages never contain secrets, tokens, passwords
- [ ] PII in logs complies with data retention policies
- [ ] Log format strings are not user-controlled
- [ ] Structured JSON logging used — no ad-hoc `print()` statements
- [ ] Failed authentication attempts logged with IP and username
- [ ] Log levels appropriate — sensitive operations at INFO or above
- [ ] Log rotation and retention policies configured
- [ ] Application logs do not expose stack traces to end users

## Checklist N — Backup & Restore Security

- [ ] Backup files contain sensitive data — treat as confidential
- [ ] Backup archives stored with restricted file permissions
- [ ] Backup download endpoint requires admin authentication and CSRF validation
- [ ] Restore operation requires double confirmation
- [ ] Restore preserves the current admin user — prevents lockout
- [ ] Backup filenames use timestamps, not user-controlled names
- [ ] Old backup files cleaned up per retention policy
- [ ] Backup/restore operations logged

## Quick Reference — Validation Constants

> Customize this table with your project's actual constants and file paths:

| Constant | Backend | Frontend | Value |
| -------- | ------- | -------- | ----- |
| {{field}} length | `{{BACKEND_CONSTANT}}` | `{{FRONTEND_CONSTANT}}` | {{value}} |
| {{field}} min | `{{BACKEND_CONSTANT}}` | `{{FRONTEND_CONSTANT}}` | {{value}} |

**These constants must stay in sync** between `{{backend_constants_path}}` and `{{frontend_constants_path}}`.
