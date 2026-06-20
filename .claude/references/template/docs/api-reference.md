---
recommended: false
depends_on: [all]
freshness: every-release
diataxis: reference
description: "API reference conventions with flat endpoint index and per-domain deep-dive file pattern."
designer_description: "When /document generates your developer-facing API reference, I'm the template that shapes the flat endpoint index plus one per-domain deep-dive file using your plan's Docs: fields and the endpoints the diff actually touches, so an integrator can scan every route in one table and then drill into the domain they need without flipping between auto-generated OpenAPI and hand-written prose."
---

# TEMPLATE -- API REFERENCE DOCUMENTATION

> **How to use this template:** Create a `dev_docs/` or `docs/api/` directory. Maintain a flat endpoint index plus one deep-dive file per API domain. This complements auto-generated OpenAPI specs -- it does not replace them.

## File Organization

| Path | Purpose |
|------|---------|
| `{{DEV_DOCS_DIR}}/api-reference.md` | Flat endpoint index (all endpoints in one table) |
| `{{DEV_DOCS_DIR}}/backend/{{domain}}.md` | Per-domain deep-dive (one file per API resource group) |

## Flat Endpoint Index

```markdown
# API Reference

| Method | Path | Auth | Rate Limit | Description |
|--------|------|------|-----------|-------------|
| GET | /api/{{resource}} | {{auth}} | {{limit}} | {{description}} |
| POST | /api/{{resource}} | {{auth}} | {{limit}} | {{description}} |
```

## Per-Domain Deep-Dive Template

```markdown
# {{Domain Name}} API

> Source: `{{source_file_path}}`

## Endpoints

| Method | Path | Auth | Rate Limit | Description |
|--------|------|------|-----------|-------------|
| ... | ... | ... | ... | ... |

## Request/Response Examples

### {{Endpoint Name}}

**Request:**
(HTTP request example)

**Response (200):**
(JSON response example)

## Error Codes

| Code | Meaning | When |
|------|---------|------|
| 400 | Bad Request | {{when}} |
| 401 | Unauthorized | {{when}} |
| 403 | Forbidden | {{when}} |
| 404 | Not Found | {{when}} |

## Business Rules

- {{Rule 1}}
- {{Rule 2}}
```

## Relationship with OpenAPI

- **OpenAPI** (auto-generated at `/api/docs`): machine-readable spec, always up to date
- **This documentation** (hand-written): human-readable context, business rules, examples, and gotchas that don't fit in OpenAPI annotations

## Freshness Policy

Update the API reference whenever endpoints are added, modified, or removed. The flat endpoint index must be complete within its declared scope -- undocumented endpoints are a bug.
