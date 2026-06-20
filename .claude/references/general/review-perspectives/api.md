---
designer_description: "When the reviewer is asked to look at what you built through API-design eyes, I'm the checklist that tells it what to watch for -- RESTful conventions, route and naming consistency, request/response contracts, versioning and deprecation discipline, object-level authorization, and how the API communicates its intent to consumers -- so the surface you ship feels predictable to integrate against."
tier: Deep-dive
---

# API — API Design

## Essential

- [P0] Is the endpoint RESTful, consistent with existing routes, and properly documented?
- [P0] Is every public endpoint routed through the API gateway with consistent authentication, throttling, circuit-breaking, and request-tracing policies applied?
- [P0] Is there a versioning strategy (URI path, header, or content negotiation) in place, with a documented deprecation timeline and sunset headers for retired versions?
- [P0] Are authentication tokens validated on every request, and are object-level and field-level authorization checks enforced to prevent BOLA/BFLA vulnerabilities?

## Deep-dive

- [P1] Are error responses localized, structured, and free of internal details, with request/response schemas validated (e.g., via Marshmallow)?
- [P1] Are rate limit status headers (`X-RateLimit-Remaining`, `X-RateLimit-Reset`) returned to clients?
- [P1] Do resource URIs follow a consistent noun-based hierarchy, with HTTP methods used per their semantics (PUT=full replacement, PATCH=partial)?
- [P1] Are query complexity limits, depth restrictions, and field-level authorization enforced for GraphQL?
- [P1] Are response shapes stable for generated SDK clients, with nullable fields marked and envelope structures consistent?
- [P1] Are payloads optimized (pagination, sparse fieldsets, compression) and N+1 query patterns eliminated server-side?
- [P1] Are breaking changes detected via contract tests or schema diff in CI, under a documented compatibility policy (e.g., additive-only)?
- [P2] Is the OpenAPI spec browsable via a documentation UI (Swagger UI, ReDoc), with example request/response payloads included?
- [P2] Does every endpoint have a human-readable description, parameter constraints, and at least one success and one error example documented inline?
- [P2] **Consistency** (CDN): Do similar API operations use similar parameter names, response shapes, and error formats?
- [P2] **Role-expressiveness** (CDN): Can a developer infer the purpose of an endpoint, parameter, or response field from its name alone?
- [P2] **Error-proneness** (CDN): Does the API design invite mistakes (confusable parameter names, missing validation, destructive operations without confirmation)?
- [P2] **Hidden dependencies** (CDN): Are relationships between resources (ordering, cascade effects, required sequences) visible or documented?
- [P2] **Viscosity** (CDN): How many API calls or config changes are needed for a single logical change?
- [P2] **Abstraction level** (CDN): Do the API's abstractions match the consumer's mental model, or impose an unfamiliar conceptual framework?
- [P2] **Closeness of mapping** (CDN): Does the vocabulary use domain terminology consumers recognize, or internal implementation jargon?
- [P2] **Intent clarity** (SigniFYIng APIs): Does documentation, naming, and structure communicate what the API was designed to do, for whom, and in which contexts?
- [P2] **Effect match & unconscious failure risk** (SigniFYIng APIs): Could a consumer experience the API as *misused*, *misunderstood*, or *unexpected*, and could they believe they succeeded when they haven't (lenient parsing, contextually wrong defaults, invisible side effects)?
- [P3] Do error messages, status codes, and pagination patterns feel intuitive and consistent enough that a new developer can integrate without reading supplementary guides?
