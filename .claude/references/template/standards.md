---
designer_description: "I list the engineering conventions your project follows -- backend layering, frontend framework and structure, testing style and coverage expectations, and i18n approach -- so every PR you open can be reviewed against one agreed baseline rather than a different reviewer's memory, and skills like /check review and /plan can anchor their judgements to the same document."
---

# TEMPLATE - ENGINEERING STANDARDS REFERENCE

> **How to use this template:** Copy this file to `project/standards.md` and populate the relevant sections for your project's stack. This unified file replaces the four separate standards files (backend-standards, frontend-standards, testing-standards, i18n-standards) that existed prior to SEJA 2.8.1. See the harness CHANGELOG for the migration rationale (source: advisory-000264 Phase 1).
>
> Sections are organized by domain. Within each domain, the original section numbers are preserved as H3 subsections so that existing cross-references of the form "backend-standards §6" map naturally to "standards.md § Backend > 6". If your project does not use i18n, leave that section as template placeholder text or delete it -- skills that load this file read only what is relevant to their step.

---

## Backend

### 1. [Core] Project Structure

> Adapt this tree to your project. The key principle is **layered architecture**: API, services, and models are separated.
>
> **See also:** Section 4 (Three-Layer Architecture) for the architectural principles behind this structure; Section 19 (Service Layer Contract) for boundary rules.

```
{{BACKEND_DIR}}/
├── app/                          # Main application package
│   ├── __init__.py              # App factory (create_app)
│   ├── config.py                # Environment-aware configuration classes
│   ├── extensions.py            # Extension singletons
│   ├── exceptions.py            # Custom exception hierarchy
│   ├── api/                     # HTTP layer — one blueprint per entity
│   │   ├── auth.py              # Auth endpoints
│   │   ├── {{entity}}.py        # Entity CRUD
│   │   └── ...
│   ├── models/                  # ORM models
│   │   ├── mixins.py            # Shared mixins (Timestamp, SoftDelete)
│   │   ├── user.py
│   │   ├── {{entity}}.py
│   │   └── ...
│   ├── services/                # Business logic — HTTP-agnostic
│   │   ├── auth_service.py
│   │   ├── {{entity}}_service.py
│   │   └── ...
│   ├── schemas/                 # Validation schemas
│   │   ├── common_schemas.py    # Shared patterns
│   │   ├── {{entity}}_schemas.py
│   │   └── ...
│   ├── utils/                   # Helper utilities
│   │   ├── constants.py         # System-wide constants
│   │   ├── decorators.py        # View decorators
│   │   ├── response_builder.py  # JSON response envelope builders
│   │   ├── validators.py        # Input validation
│   │   └── helpers.py           # Common helpers
│   └── middleware/              # Request/response interceptors
│       ├── permissions.py       # Permission evaluator, route decorators
│       ├── security_headers.py  # HTTP security headers
│       ├── csrf.py              # CSRF protection
│       └── logging_config.py    # Structured logging
├── translations/                # i18n catalogs (if applicable)
├── migrations/                  # Database migrations
├── tests/                       # Test suite
│   ├── conftest.py              # Fixtures
│   └── test_*.py
├── run.py                       # Entry point
├── requirements.txt             # Production dependencies
├── requirements-dev.txt         # Dev/test dependencies
└── Dockerfile
```

**Rules:**
- `api/` holds only HTTP concerns (request parsing, response building). No business logic.
- `services/` holds HTTP-agnostic business logic. Services never import framework request/response.
- `models/` holds ORM definitions, relationships, and serialization.
- `schemas/` holds validation schemas for request validation.
- `utils/` holds stateless helpers shared across layers.
- `middleware/` holds request/response interceptors.

---

### 2. [Core] Application Factory

> **Applies to: Flask**

**Pattern:** App factory via `create_app(config_name)`.

```python
def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'production')
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    # Initialize extensions, register blueprints, install error handlers
    return app
```

**Initialization order:**
1. Load config class -> validate production secrets
2. Initialize extensions
3. Configure CORS
4. Register blueprints
5. Install error handlers
6. Configure structured logging
7. Initialize middleware modules
8. Attach activity logging

**Rules:**
- All extension instances created as module-level singletons in `extensions.py`.
- Production config validates that secrets differ from defaults.
- Guards (CSRF, maintenance) defined in `middleware/` modules, each exposing an `init_<name>(app)` function.

---

### 3. [Core] Configuration

**Pattern:** Class-based configuration with environment override.

| Class | Purpose |
|-------|---------|
| `Config` | Base — loads from `.env`, provides defaults |
| `DevelopmentConfig` | `DEBUG=True`, relaxed CORS |
| `ProductionConfig` | `DEBUG=False`, validates secrets, secure cookies |
| `TestConfig` | Test database |
| `UnitTestConfig` | In-memory SQLite for fast tests |

**Rules:**
- All secrets come from environment variables; never hardcode production secrets.
- `ProductionConfig.validate()` runs at startup and rejects known dev defaults.

---

### 4. [Core] Three-Layer Architecture

> **See also:** Section 1 (Project Structure) for the directory layout implementing these layers; Section 19 (Service Layer Contract) for detailed boundary rules.

```
┌─────────────────────────────┐
│  API Layer (Blueprints)     │  <- HTTP concerns only
│  request -> validate -> call │
├─────────────────────────────┤
│  Service Layer              │  <- Business logic, HTTP-agnostic
│  orchestration, rules       │
├─────────────────────────────┤
│  Data Layer (Models)        │  <- ORM, relationships, serialization
│  ORM + Database             │
└─────────────────────────────┘
```

#### API Layer

Responsibilities: parse request, validate input (schema), call service/model, build response.

**Decorator stacking order:**
1. `@bp.route()` — route registration
2. `@jwt_required()` — authentication
3. `@limiter.limit()` — rate limiting (where applicable)
4. `@admin_required()` / `@member_required()` — authorization
5. `@require_json_body` — payload validation

#### Service Layer

Responsibilities: business rules, orchestration, raise error hierarchy.

**Rules:**
- Services never import framework request/response objects.
- Services raise typed error subtypes; the API layer catches and maps to HTTP status.
- Services receive plain Python arguments (strings, ints, dicts).

#### Data Layer (Models)

Responsibilities: ORM mapping, relationships, `to_dict()` serialization.

**Rules:**
- Models define `to_dict()` for JSON serialization.
- Models may define query helpers but not business rules.

---

### 5. [Core] Exception Hierarchy

> **See also:** Section 8 (API Response Patterns) for how exceptions map to HTTP responses.

```python
class ServiceError(Exception):        # Base — maps to 400
class NotFoundError(ServiceError):     # Maps to 404
class PermissionError(ServiceError):   # Maps to 403
class ValidationError(ServiceError):   # Maps to 400
class AuthenticationError(ServiceError): # Maps to 401
```

**Rules:**
- Services raise `ServiceError` subtypes; never `abort()` or raw HTTP status codes.
- Global `@app.errorhandler` hooks map each exception to its HTTP status.
- Error messages are localized before being sent to the client.

---

### 6. [Core] Models & ORM Patterns

> **See also:** Section 10 (Database Access Patterns) for query style conventions.

> **Applies to: SQLAlchemy**

#### Mixins

| Mixin | Provides | Used By |
|-------|----------|---------|
| `TimestampMixin` | `created_at`, `updated_at` (timezone-aware UTC) | Most models |
| `SoftDeleteMixin` | `deleted_at`, `is_active`/`is_deleted`, `soft_delete()`/`restore()` | Soft-deletable entities |

#### Relationship Loading Strategies

| Strategy | When to Use |
|----------|------------|
| `lazy='select'` | Default; one-off access to small relations |
| `lazy='selectin'` | Small collections always needed (e.g., translations) |
| `lazy='joined'` | Always-needed 1:1 or small 1:N loaded with parent |
| `lazy='dynamic'` | Large collections that need filtering/pagination |

#### Soft Deletes

```python
from sqlalchemy import select

# Query active records (SQLAlchemy 2.0 style)
stmt = select(Entity).where(Entity.deleted_at.is_(None))
entities = db.session.execute(stmt).scalars().all()

# Soft-delete a record
entity.soft_delete()  # sets deleted_at = utcnow()
db.session.commit()
```

**Rules:**
- Soft delete entities must always filter by `deleted_at.is_(None)`.
- All timestamps are timezone-aware UTC.
- Use a naming convention for deterministic migration constraint names.

---

### 7. [Core] Authentication & Authorization

#### JWT Authentication

- **Library:** Flask-JWT-Extended with HS256
- **Access token:** {{access_token_expiry}}
- **Refresh token:** {{refresh_token_expiry}}
- **Identity:** User ID stored as string in JWT `sub` claim
- **Revocation:** Tokens added to blocklist table on logout

#### Brute-Force Protection

- Exponential back-off lockout
- Rate limiting on auth endpoints

#### CSRF Protection

**Pattern:** Double-submit cookie.

#### Permission Model

> Reference your `project/product-design-as-coded.md § Conceptual Design` for domain-level permission rationale.

**System-Level:**

| Constant | Value | Capability |
|----------|-------|------------|
| `PROFILE_GUEST` | {{value}} | View only |
| `PROFILE_MEMBER` | {{value}} | Full participation |
| `PROFILE_ADMINISTRATOR` | {{value}} | Full system access |

**Resource-Level:**

> Define resource-scoped permission constants if applicable.

#### PermissionEvaluator

Centralized static methods — one rule per method:

```python
PermissionEvaluator.can_admin_system(user)
PermissionEvaluator.can_access_resource(user, resource)
PermissionEvaluator.can_edit_entity(user, entity, resource)
```

#### Route Decorators

| Decorator | Effect |
|-----------|--------|
| `@jwt_required()` | Validates JWT, checks revocation |
| `@admin_required()` | Requires administrator |
| `@member_required()` | Requires member or higher |
| `@require_json_body` | Validates JSON payload |

**Rules:**
- Always use `PermissionEvaluator` methods — never inline role comparisons.
- Permission decorators stack after `@jwt_required()`.
- Constants synced between backend and frontend.

---

### 7b. [Core] Object-Level Authorization (BOLA Prevention)

> **See also:** Section 7 (Authentication & Authorization) for role-level checks and route decorators.

> OWASP API Security #1: Broken Object-Level Authorization (BOLA). Every service method that accesses a resource must verify that the requesting user is authorized to access **that specific resource instance**, not just that they have the correct role.

#### Pattern

Every service method that retrieves, updates, or deletes a resource should include an ownership or authorization check as its **first operation** after fetching the resource:

```python
def get_entity(entity_id: int, current_user_id: int) -> Entity:
    entity = db.session.get(Entity, entity_id)
    if entity is None:
        raise NotFoundError(f"Entity {entity_id} not found")

    # Object-level authorization — MUST come before any business logic
    if not PermissionEvaluator.can_access_entity(current_user_id, entity):
        raise PermissionError("Not authorized to access this resource")

    return entity
```

#### When to Apply

| Check Type | When to Use |
|-----------|-------------|
| **Role-level** (system permissions) | Operations not tied to a specific resource (e.g., "can create entities", "can view admin dashboard") |
| **Object-level** (resource ownership) | Any read, update, or delete of a specific resource instance (e.g., "can edit *this* entity") |
| **Both** | Most mutating operations: first check role, then check object-level ownership |

#### Rules

- Never assume that a valid JWT or role check implies access to a specific resource.
- Object-level checks belong in the **service layer**, not in route decorators (decorators handle role-level checks).
- Test both positive and negative authorization paths: a user who owns resource A must NOT be able to access resource B.
- For list endpoints, apply filtering in the query (e.g., `WHERE owner_id = :current_user_id`) rather than post-fetch filtering.

---

### 8. [Core] API Response Patterns

> **See also:** Section 5 (Exception Hierarchy) for the error types these responses map to.

#### Response Builder

| Function | HTTP Status | Envelope |
|----------|-------------|----------|
| `rb.success(data)` | 200 | `{ ...data }` |
| `rb.created(data)` | 201 | `{ ...data }` |
| `rb.no_content()` | 204 | empty body |
| `rb.error(msg, status)` | 4xx/5xx | `{ "error": "msg" }` |
| `rb.not_found(msg)` | 404 | `{ "error": "msg" }` |
| `rb.forbidden(msg)` | 403 | `{ "error": "msg" }` |
| `rb.paginated(items, total, page, pages, has_next)` | 200 | `{ "items": [...], ... }` |

**Rules:**
- Always use response builder — never `jsonify()` + manual status codes.
- Success data at top level (no wrapping envelope).
- Error messages localized.

---

### 9. [Extended] Internationalization (i18n)

> **Applies to: Flask-Babel**

#### Setup

- **Framework:** Flask-Babel with gettext catalogs
- **Catalogs:** `translations/{locale}/LC_MESSAGES/messages.po`
- **Default locale:** `{{BACKEND_DEFAULT_LOCALE}}`

#### Locale Negotiation

Priority: query string (`?lang=...`) -> `Accept-Language` header -> default.

#### Adding New Translatable Strings

1. Add the string to all `.po` files
2. Compile catalogs: `pybabel compile -d translations`
3. Use helper functions in code

**Rules:**
- Every user-facing error or message must be localized.
- `.mo` files are compiled build artifacts — rebuild via `pybabel compile`.

---

### 10. [Core] Database Access Patterns

> **See also:** Section 6 (Models & ORM Patterns) for model definitions and mixins.

#### Query Patterns

```python
from sqlalchemy import select

# Get by primary key (SQLAlchemy 2.0+)
entity = db.session.get(Entity, entity_id)

# Filter queries (SQLAlchemy 2.0 style)
stmt = select(Entity).where(Entity.status == 0)
entities = db.session.execute(stmt).scalars().all()

# Soft-delete aware queries
stmt = select(Entity).where(Entity.deleted_at.is_(None))
entities = db.session.execute(stmt).scalars().all()

# Paginated queries
stmt = select(Entity).where(Entity.deleted_at.is_(None)).limit(per_page).offset((page - 1) * per_page)
items = db.session.execute(stmt).scalars().all()
total = db.session.execute(select(func.count()).select_from(Entity).where(Entity.deleted_at.is_(None))).scalar()
```

**Rules:**
- Use SQLAlchemy 2.0 `select()` statement style for all queries. Avoid the legacy `Model.query` interface.
- Use `db.session.get(Model, pk)` for primary key lookups.
- Always filter soft-deleted records.

---

### 11. [Core] Migrations

> **Applies to: Alembic**

**Rules:**
- All migrations must be **idempotent** — use `IF NOT EXISTS`, `IF EXISTS`, etc.
- Use PostgreSQL syntax (not MySQL backticks).
- Seed data migrations should be idempotent (insert-if-not-exists).
- Never create cycles in revision dependencies.
- Use separate admin credentials for DDL migrations when possible.

---

### 12. [Core] Security

#### Security Headers

Applied via `after_request`:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: SAMEORIGIN`
- `Content-Security-Policy: default-src 'self'`
- `Strict-Transport-Security` (production)
- `Referrer-Policy: strict-origin-when-cross-origin`

#### Rate Limiting

- Default: {{default_rate_limit}} per IP
- Auth endpoints: stricter limits
- Production storage: Redis; development: in-memory fallback

#### Input Validation

- Schema validation for structured request validation
- Format checks (email, login, password strength)
- Shared `VALIDATION` constants for field length limits (synced with frontend)
- File upload validation: blocked executable extensions, MIME type checks

#### Maintenance Mode

- Toggled via system setting
- `before_request` guard blocks non-admin requests with 503

**Rules:**
- Never trust client input — validate at the API boundary.
- CORS restricted to `/api/*` routes with explicit origin allowlist.
- Secure cookies in production.

#### Dependency Vulnerability Scanning

Regularly scan dependencies for known vulnerabilities:

| Tool | Command | Use Case |
|------|---------|----------|
| `pip-audit` | `pip-audit` | Audit installed packages against PyPI advisory database |
| `safety` | `safety check` | Check requirements against Safety DB |

**Rules:**
- Run dependency scanning in CI on every pull request.
- Block merges when critical or high-severity vulnerabilities are found.
- Reference: [OWASP API Security Top 10](https://owasp.org/API-Security/) for comprehensive API threat coverage.

---

### 13. [Core] Activity Logging

#### Automatic Logging

- Attached as `after_request` hook
- Routes mapped to semantic tuples: `(action, entity_type, entity_id)`
- **Logged:** create, update, delete, login, logout, register, search, export, import
- **Skipped:** passive reads

**Rules:**
- When adding a new state-changing endpoint, add route mapping to the activity log service.

---

### 14. [Core] Testing

> **Applies to: pytest**

#### Key Fixtures

| Fixture | Scope | Purpose |
|---------|-------|---------|
| `app` | session | App with in-memory SQLite |
| `client` | function | Test client |
| `db_session` | function | SQLAlchemy session (auto-rollback) |
| `admin_token` | function | JWT access token for admin user |

#### Test Pattern

```python
def test_create_entity(client, admin_token):
    response = client.post('/api/{{entities}}/', json={'title': 'Test'},
                           headers={'Authorization': f'Bearer {admin_token}'})
    assert response.status_code == 201
```

#### Integration Tests

> If your project uses a separate integration test suite against a real database, document the setup here.

**Rules:**
- Test files follow `test_<module>.py` naming.
- Use fixtures for common setup.
- Test both success and error paths (401, 403, 404, 400).

---

### 15. [Extended] Extensions & Libraries

> Document your extensions and their singleton names:

| Extension | Purpose | Singleton |
|-----------|---------|-----------|
| {{extension}} | {{purpose}} | `{{name}}` |

**Rules:**
- Extensions instantiated in `extensions.py` as module-level singletons.
- Extensions initialized with `init_app(app)` in the factory.

---

### 16. [Core] Naming Conventions

| Category | Convention | Examples |
|----------|-----------|---------|
| Modules | `snake_case.py` | `auth_service.py`, `{{entity}}_schemas.py` |
| Classes | `PascalCase` | `User`, `PermissionEvaluator` |
| Functions | `snake_case` | `create_app`, `authenticate_user` |
| Constants | `UPPER_SNAKE_CASE` | `PROFILE_ADMINISTRATOR` |
| Blueprints | `snake_case` | `auth`, `{{entity}}` |
| URL prefixes | `kebab-case` | `/api/{{entities}}` |
| DB tables | `snake_case` (plural) | `users`, `{{entities}}` |
| DB columns | `snake_case` | `user_id`, `created_at` |
| Config vars | `UPPER_SNAKE_CASE` | `JWT_SECRET_KEY`, `UPLOAD_FOLDER` |
| Test files | `test_<module>.py` | `test_auth.py`, `test_{{entity}}.py` |

---

### 17. [Extended] File & Media Handling

#### Upload Flow

1. Validate file uploads — block executable extensions, check MIME types
2. Save with UUID filenames
3. Generate previews if applicable

**Rules:**
- Never serve uploaded files with their original filename — use UUID-based names.
- Validate both file extension and MIME type.

---

### 18. [Extended] Import/Export

> If applicable, document your import/export architecture:

#### Export Formats

> List supported export formats and their serializers.

#### Import Architecture

> Document format detection, delegation pattern, and author attribution rules.

**Rules:**
- Import operations are transactional — rollback on failure.

---

### 19. [Core] Service Layer Contract

> **See also:** Section 4 (Three-Layer Architecture) for the overall layer model; Section 1 (Project Structure) for file organization.

#### Boundary Rules

Services are the **sole owners of business logic**.

**Services must:**
- Accept plain Python arguments — never framework request/response objects.
- Raise typed error subtypes — never `abort()` or raw HTTP status codes.
- Return plain Python objects — never serialized responses.

**Services should not:**
- Import framework request objects.
- Use `current_app.logger` — use `logging.getLogger(__name__)`.
- Access `current_app.config` directly — prefer dependency injection.

#### Config Access Pattern

**Preferred (dependency injection):**

```python
def save_file(file_data, upload_folder: str):
    path = os.path.join(upload_folder, generate_uuid_filename())
    ...
```

**Acceptable (config dataclass):**

```python
@dataclasses.dataclass(frozen=True)
class ServiceConfig:
    some_setting: str = 'default'

    @classmethod
    def from_flask_config(cls, cfg: dict) -> 'ServiceConfig':
        return cls(some_setting=cfg.get('SOME_SETTING', 'default'))
```

#### Caching Strategy

Caching is a service-layer concern. Apply caching within services, not in route handlers or models.

| Level | When to Use | Implementation |
|-------|-------------|----------------|
| **Application cache** | Expensive computations, repeated lookups | Redis or in-memory cache (e.g., `cachetools`, `functools.lru_cache`) |
| **HTTP cache headers** | Responses that are safe to cache at the client or CDN | `Cache-Control`, `ETag`, `Last-Modified` headers in the API layer |
| **Query result cache** | Frequently accessed, rarely changed data | Cache at the service layer with TTL-based invalidation |

**Rules:**
- Cache at the service layer — never at the model or route layer.
- Use TTL-based expiration as the default invalidation strategy.
- Invalidate caches explicitly on write operations (create, update, delete) that affect cached data.
- Never cache user-specific or permission-dependent data without including the user/role in the cache key.
- Log cache hit/miss ratios for observability.

---

### 20. [Core] Schema Validation Policy

> **See also:** Section 19 (Service Layer Contract) for how validated data flows into services.

#### Mandatory Schema Usage

Every endpoint accepting JSON **must** validate through a schema. Raw `json_data.get()` without schema validation is prohibited.

#### Library Choice

| Library | Best For | Decision Criteria |
|---------|----------|-------------------|
| **Pydantic** | FastAPI projects, data parsing/coercion, settings management, JSON Schema generation | Native FastAPI integration; automatic type coercion; excellent for request/response models and configuration. Preferred for new projects. |
| **Marshmallow** | Flask projects, complex nested schemas, custom field-level validation, serialization/deserialization asymmetry | Mature Flask ecosystem support; fine-grained control over load vs. dump behavior; better for complex validation pipelines. |

Choose one library per project and use it consistently. Do not mix Pydantic and Marshmallow in the same codebase.

#### Marshmallow Schema Pattern

> **Applies to: Marshmallow**

```python
class CreateEntitySchema(Schema):
    title = fields.String(required=True, validate=validate.Length(min=1, max=200))
    description = fields.String(load_default='')

class UpdateEntitySchema(Schema):
    title = fields.String(validate=validate.Length(min=1, max=200))
    description = fields.String()
```

#### Pydantic Schema Pattern

> **Applies to: Pydantic**

```python
from pydantic import BaseModel, Field

class CreateEntityRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = ""

class UpdateEntityRequest(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
```

#### Schema File Naming

- One schema file per entity: `<entity>_schemas.py`
- Shared schemas: `common_schemas.py`
- Classes: `Create<Entity>Schema`, `Update<Entity>Schema` (Marshmallow) or `Create<Entity>Request`, `Update<Entity>Request` (Pydantic)

---

### 21. [Core] Logging Standards

#### Module-Level Logger

```python
import logging
logger = logging.getLogger(__name__)
```

#### Log Levels

| Level | When to Use |
|-------|------------|
| `logger.debug()` | Detailed diagnostics (disabled in production) |
| `logger.info()` | Normal operational events |
| `logger.warning()` | Unexpected but recoverable situations |
| `logger.error()` | Failures affecting a single request |
| `logger.exception()` | Same as error with stack trace |
| `logger.critical()` | System-wide failures |

#### Structured JSON Logging

All log output JSON-formatted with request context enrichment:

| Field | Source |
|-------|--------|
| `timestamp` | ISO 8601 with timezone |
| `level` | Python log level |
| `name` | Logger name |
| `message` | Log message |
| `request_id` | UUID4 per request |
| `user_id` | From JWT identity |

**Rules:**
- Never use `current_app.logger` in services.
- Include relevant context in log messages.
- Suppress noisy third-party loggers in production.

---

### 22. [Core] Dependency Management

#### Recommended: `pyproject.toml` + Lock File

Use `pyproject.toml` as the single source of truth for project metadata and dependencies. Use a lock file for reproducible installs.

| Tool | Lock File | Install Command |
|------|-----------|-----------------|
| `uv` | `uv.lock` | `uv sync` |
| `pip-tools` | `requirements.lock` | `pip install -r requirements.lock` |

```toml
# pyproject.toml (example)
[project]
name = "{{PROJECT_NAME}}"
requires-python = ">=3.11"
dependencies = [
    "flask>=3.0",
    # ... production dependencies
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    # ... dev/test dependencies
]
```

#### Legacy Alternative: `requirements.txt`

For simpler projects or legacy codebases:

| File | Contents | Used By |
|------|----------|---------|
| `requirements.txt` | Production runtime dependencies only | Docker, production |
| `requirements-dev.txt` | Dev/test tools (includes `-r requirements.txt`) | Local dev, CI |

#### Rules

- **Pin all versions** in lock files for reproducible builds.
- **Use ranges** in `pyproject.toml` (e.g., `>=3.0,<4.0`) to allow compatible updates.
- **Production deps** separated from dev deps (via `[project.optional-dependencies]` or separate files).
- Review and update dependencies periodically; run tests after each upgrade.

---

### 23. [Extended] Test Data Factories

#### Factory Fixtures

```python
@pytest.fixture
def create_entity(db_session):
    def _create(name='Test Entity', **kwargs):
        defaults = {'name': name, 'status': STATUS_ACTIVE}
        defaults.update(kwargs)
        entity = Entity(**defaults)
        db.session.add(entity)
        db.session.flush()
        return entity
    return _create
```

**Rules:**
- Each factory returns the created model instance (flushed but not committed).
- Factories accept `**kwargs` for overriding any default.
- Factories handle FK dependencies.

---

### 24. [Extended] OpenAPI / Swagger Documentation

> If applicable:

Auto-generated OpenAPI spec via `apispec` with schema plugin.

| Route | Response |
|-------|----------|
| `GET /api/docs` | Swagger UI |
| `GET /api/docs/openapi.json` | Raw OpenAPI spec |

**Rules:**
- New endpoints automatically included.
- Schemas must be importable to appear in the spec.
- Docstrings on route handlers used as operation descriptions.

---

### 25. [Extended] Module-Level README Convention

Every backend sub-package directory should contain a `README.md` with a module index table and update instructions.

**Required in:** `app/api/`, `app/models/`, `app/services/`, `app/schemas/`, `app/utils/`, `app/middleware/`

**Template:**

| File | Responsibility |
|------|---------------|
| `{{filename}}.py` | {{one-line description}} |

**Rules:**
- Update the README when adding, removing, or renaming files in the directory.
- Keep descriptions to one line per file.
- Include a "Design Conventions" subsection if the module follows specific patterns (e.g., "all services accept and return dicts, not model instances").

---

### 26. [Core] Operational Readiness

#### Health Check Endpoints

Every deployed backend must expose health check endpoints for orchestrator probes:

| Endpoint | Purpose | Response |
|----------|---------|----------|
| `GET /health/live` | Liveness probe -- process is running | `200 {"status": "ok"}` |
| `GET /health/ready` | Readiness probe -- dependencies are reachable | `200 {"status": "ready"}` or `503 {"status": "not_ready", "checks": {...}}` |

**Readiness checks** should verify critical dependencies:
- Database connection (execute a lightweight query like `SELECT 1`)
- Cache connectivity (Redis ping, if applicable)
- External service availability (if critical to request handling)

**Rules:**
- Health endpoints must not require authentication.
- Liveness probes must not check external dependencies (they only confirm the process is alive).
- Readiness probes must have timeouts to avoid blocking the orchestrator.

#### Graceful Shutdown

- Handle `SIGTERM` by stopping acceptance of new requests and completing in-flight requests within a configurable timeout.
- Close database connections and flush logs before exiting.
- If using background workers (Celery, task queues), allow active tasks to complete or re-queue them.

#### Container Security

When deploying via Docker (referenced in section 1 project structure):

```dockerfile
# Use multi-stage builds to minimize image size
FROM python:{{python_version}}-slim AS builder
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen --no-dev

FROM python:{{python_version}}-slim
# Run as non-root user
RUN useradd --create-home appuser
USER appuser
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY . .
CMD [".venv/bin/python", "run.py"]
```

**Rules:**
- **Run as non-root**: always set a `USER` directive in production Dockerfiles.
- **Pin base image digests**: use `python:3.12-slim@sha256:...` for reproducible builds.
- **Multi-stage builds**: separate build dependencies from runtime image.
- **No secrets in images**: use environment variables or secret managers, never bake secrets into layers.
- **Minimize attack surface**: use slim/distroless base images; remove build tools from the runtime stage.

---

### 27. [Extended] Async Patterns

#### When to Use Async

| Pattern | Best For | Framework |
|---------|----------|-----------|
| **Sync (WSGI)** | CPU-bound work, simple CRUD, projects using Flask/Django | Flask, Django |
| **Async (ASGI)** | I/O-bound work, high-concurrency APIs, WebSockets, streaming | FastAPI, Starlette |

Choose one paradigm per service and use it consistently. Do not mix sync and async handlers in the same application unless the framework explicitly supports it.

#### Async Database Access

> **Applies to: FastAPI / ASGI**

```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import select

async def get_entity(session: AsyncSession, entity_id: int) -> Entity:
    result = await session.execute(select(Entity).where(Entity.id == entity_id))
    return result.scalar_one_or_none()
```

**Rules:**
- Use `create_async_engine` with an async-compatible driver (e.g., `asyncpg` for PostgreSQL).
- Use `AsyncSession` for all database operations in async code.
- Never call sync database operations inside `async def` functions -- use `run_in_executor` if wrapping legacy sync code.

#### Background Task Processing

| Tool | When to Use |
|------|-------------|
| **Celery** | Long-running tasks, scheduled jobs, distributed task queues across multiple workers |
| **asyncio tasks** | Short-lived I/O-bound tasks within the same process (e.g., sending an email after responding) |
| **arq / dramatiq** | Lightweight async-native alternatives to Celery |

**Rules:**
- Offload any operation that takes >500ms to a background task.
- Background tasks must be idempotent -- they may be retried on failure.
- Use a dead-letter queue for tasks that fail repeatedly.
- Log task start, completion, and failure for observability.

---

### 28. [Extended] API Versioning

#### Strategy

Choose a versioning strategy and apply it consistently:

| Strategy | Format | Pros | Cons |
|----------|--------|------|------|
| **URL path** (recommended) | `/api/v1/entities` | Explicit, easy to route, cacheable | URL proliferation |
| **Header** | `Accept: application/vnd.api+json; version=2` | Clean URLs | Harder to test, not cacheable by default |
| **Query parameter** | `/api/entities?version=1` | Simple to implement | Pollutes query string, caching issues |

#### Deprecation Policy

When retiring an API version:

1. **Announce**: add a `Sunset` header to responses from the deprecated version: `Sunset: Sat, 01 Mar 2025 00:00:00 GMT`
2. **Warn**: add a `Deprecation` header: `Deprecation: true`
3. **Grace period**: maintain the deprecated version for at least {{deprecation_grace_period}} after the announcement
4. **Remove**: return `410 Gone` after the sunset date

**Rules:**
- Never break an existing API version -- breaking changes require a new version.
- Document version differences in the OpenAPI spec (section 24).
- Default to the latest stable version when no version is specified.

---

## Frontend

### 1. Project Structure

> Adapt this tree to your project. The key principle is **feature co-location**: domain-specific code lives together, shared code is centralized.

```
{{FRONTEND_DIR}}/src/
├── api/              # One module per entity + shared HTTP client instance
├── assets/           # Static images and resources
├── components/
│   ├── common/         # Reusable, domain-agnostic components
│   ├── forms/          # Shared form primitives
│   ├── layout/         # Layout wrapper and page structure
│   └── {{domain}}/     # Domain-specific shared components
├── context/          # React Context providers
├── features/         # Feature-scoped components, hooks, forms, utils by domain
│   └── {{domain}}/     # Domain feature folder
├── hooks/            # Cross-cutting custom hooks only
├── i18n/
│   └── locales/      # Translation files
├── pages/            # Page-level orchestrator components (one per route)
├── routes/           # Route definitions and guards
├── services/         # Non-API services (storage, event bus)
├── types/            # TypeScript type definitions
├── utils/            # Utility functions and constants
├── App.{{ext}}       # Root component with provider hierarchy
├── index.css         # CSS framework directives + custom component classes
└── main.{{ext}}      # Entry point
```

**Rules:**
- `components/common/` holds reusable, domain-agnostic components.
- `components/forms/` holds **shared form primitives** only.
- `features/{{domain}}/` holds feature-scoped components, hooks, forms, and utils for a single domain.
- `pages/` holds one **orchestrator** per route — state and effects live here, rendering delegated to sub-components.
- `hooks/` holds **only cross-cutting** hooks used by 2+ unrelated domains.
- Feature-specific hooks live **co-located** in `features/{{domain}}/`.

---

### 2. Component Patterns

> If stack includes React:

All components are **functional components** using React Hooks. No class components. All source files use TypeScript (`.ts`/`.tsx`).

#### Structure Template

```tsx
/**
 * @fileoverview Brief description of the component's purpose.
 * @module components/path/ComponentName
 */
import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";

/**
 * Description of the component.
 * @param {Object} props
 * @param {string} props.title - The title to display
 * @param {Function} props.onSubmit - Callback when form submits
 * @returns {JSX.Element}
 */
const ComponentName = ({ title, onSubmit }: Props) => {
  const { t } = useTranslation();
  const [value, setValue] = useState("");

  return <div>{t("key")}</div>;
};

export default ComponentName;
```

**Rules:**
- Props are destructured in the function signature.
- Default export for components and hooks.
- JSDoc on all exported symbols.

#### Complexity Thresholds

| Metric | Soft Limit | Action |
|--------|-----------|--------|
| Component line count | 400 lines | Consider extraction |
| Component line count | 500+ lines | Must split into sub-components |
| Import count per file | 15 imports | Consider extracting sections |
| Import count per file | 25+ imports | Must extract sub-components or modals |

Pages act as **orchestrators**: they own state, effects, and business logic, then delegate rendering to focused sub-components in `features/{{domain}}/`.

---

### 3. State Management

> Choose and document your state management approach. Common options: React Context + hooks, Redux, Zustand, Jotai.

**Approach:** {{state_management_approach}}

#### Context Providers

> List your application's context providers:

| Context | Purpose | Hook |
|---------|---------|------|
| `AuthContext` | User session, login/logout, profile | `useAuth()` |
| `NotificationContext` | Global toast queue | `useNotifications()` |
| `ThemeContext` | Dark/light/system colour scheme preference | `useTheme()` |
| {{additional contexts}} | | |

#### Provider Hierarchy

```
<BrowserRouter>
  <AuthProvider>
    <ThemeProvider>
      <NotificationProvider>
        <QueryClientProvider>
          <AppRoutes />
        </QueryClientProvider>
      </NotificationProvider>
    </ThemeProvider>
  </AuthProvider>
</BrowserRouter>
```

**Rules:**
- Local `useState` for UI state (modals, form data, toggles).
- Context for cross-cutting concerns (auth, notifications, shared reference data).
- Custom hooks to encapsulate business logic.

---

### 4. Routing

> If stack includes React Router:

**Framework:** React Router DOM v{{version}}

#### Structure

- All page routes lazy-loaded with `React.lazy()` + `<Suspense>`.
- Route guard via `<ProtectedRoute>`:

```tsx
<ProtectedRoute adminOnly={false} useLayout={true}>
  <PageComponent />
</ProtectedRoute>
```

**Rules:**
- Every new page must be lazy-loaded.
- Admin-only routes use `adminOnly={true}`.
- `ProtectedRoute` redirects unauthenticated users to `/`, non-admins away from admin routes.

#### URL & Navigation Patterns

- **Query params** for transient state (search filters, pagination): `?page=2&q=term`.
- **Hash fragments** for scroll targets: `#entity-123`.
- **`useSearchParams()`** for reading/writing URL query params.
- Deep links should resolve to the same view regardless of entry point.

#### List Page Pattern

> If your application has standardized list pages, document the shared hook/pattern here.

---

### 5. Styling & CSS

> If stack includes Tailwind CSS:

**Framework:** Tailwind CSS v{{version}} — utility-first with semantic component layer.

#### Architecture

All custom styles live in `src/index.css` using Tailwind layers:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer components {
  .btn--primary { @apply ... ; }
  .chip--status-active { @apply ... ; }
}
```

#### Class Naming Convention — BEM

All custom component classes follow the **BEM (Block Element Modifier)** convention:

```css
.block                     /* standalone entity */
.block__element            /* part of a block */
.block--modifier           /* variant or state of a block */
.block__element--modifier  /* variant or state of an element */
```

**Separators:** double underscore `__` for elements, double dash `--` for modifiers.

> Document your project's BEM blocks as they emerge:

| Block | Role | Example classes |
|-------|------|----------------|
| `btn` | Button variants | `btn--primary`, `btn--secondary`, `btn--danger` |
| `chip` | Badge/pill variants | `chip--status-active`, `chip--tag` |
| `alert` | Alert variants | `alert--error`, `alert--success`, `alert--info` |
| `nav` | Navigation elements | `nav__link--active` |
| `card` | Card containers | `card--container`, `card--interactive` |
| `form` | Form elements | `form__label` |

#### Design Tokens

> Centralize all style primitives in a tokens file:

```ts
// src/styles/tokens.ts
export const colors = {
  primary: "{{primary_hex}}",
  secondary: "{{secondary_hex}}",
} as const;

export const fontFamily = {
  sans: ["{{sans_font}}", "sans-serif"],
  serif: ["{{serif_font}}", "serif"],
} as const;
```

**Rules:**
- All color hex values and font definitions must originate from a tokens file.
- Token names use semantic meaning (`primary`, `secondary`) not visual descriptions.
- No CSS Modules, no styled-components, no separate `.css` files per component.
- All custom component classes go in `index.css` under `@layer components`.
- Prefer Tailwind utility classes inline; extract to `@layer components` only when a pattern repeats 3+ times.

#### Dark Mode

> If your application supports dark mode, document the strategy (Tailwind `class` strategy, CSS variables, etc.) and the token structure.

---

### 6. Internationalization (i18n)

> If stack includes i18n:

**Framework:** react-i18next + i18next

#### Setup

- Languages: `{{PRIMARY_LOCALE}}` (default), `{{SECONDARY_LOCALE}}`.
- Translation files: `src/i18n/locales/{{primary}}.json`, `src/i18n/locales/{{secondary}}.json`.

#### Usage

```tsx
const { t, i18n } = useTranslation();

// String lookup
<h1>{t("{{section}}.title")}</h1>

// Current language
const lang = i18n.language;

// Change language
i18n.changeLanguage("{{locale}}");
```

**Rules:**
- Every user-facing string must use an i18n key. No hardcoded text.
- Translation keys use **dot notation**: `"errors.loadFailed"`, `"auth.loginPlaceholder"`.
- When creating or modifying strings, update **all** locale files.
- `escapeValue: false` when React handles escaping.
- **Security warning:** Never interpolate user-supplied values into translation keys rendered via `dangerouslySetInnerHTML` without sanitization.

---

### 7. API Layer

> If stack includes Axios or similar HTTP client:

**Framework:** Axios v{{version}} with a shared instance.

#### Architecture

```
src/api/
├── axios.ts          # Shared instance, interceptors, error normalization
├── apiFactories.ts   # createCrudApi() factory
├── authApi.ts        # Auth-specific endpoints
└── {{entity}}Api.ts  # One module per entity
```

#### Error Normalization

Every rejected promise carries:

| Property | Type | Description |
|----------|------|-------------|
| `error.message` | `string` | Human-readable message |
| `error.status` | `number` | HTTP status code |
| `error.details` | `object` | Raw response body |
| `error.errorType` | `string` | One of: `"network"`, `"timeout"`, `"canceled"`, `"server"`, `"unknown"` |

#### CRUD Factory Pattern

```ts
export const createCrudApi = (basePath: string) => ({
  list: async (params?) => { ... },
  getById: async (id: number) => { ... },
  create: async (data: unknown) => { ... },
  update: async (id: number, data: unknown) => { ... },
  remove: async (id: number) => { ... },
});
```

#### JWT Token Flow

> Document your authentication token flow:

1. Backend sets tokens as `HttpOnly; Secure; SameSite=Lax` cookies on login/refresh.
2. Browser automatically sends cookies with every request.
3. Response interceptor detects 401 and attempts token refresh.
4. On session expiry -> event -> AuthContext clears user state.

#### Backend-Frontend API Contract

##### Endpoint Naming

| Pattern | HTTP Method | Purpose | Example |
|---------|-------------|---------|---------|
| `/api/{{entity}}/` | GET | List (paginated) | `GET /api/{{entities}}/` |
| `/api/{{entity}}/` | POST | Create | `POST /api/{{entities}}/` |
| `/api/{{entity}}/<id>` | GET | Get by ID | `GET /api/{{entities}}/5` |
| `/api/{{entity}}/<id>` | PUT | Update | `PUT /api/{{entities}}/5` |
| `/api/{{entity}}/<id>` | DELETE | Delete | `DELETE /api/{{entities}}/5` |

URL entities use **kebab-case**.

##### Response Envelope

| Backend Builder | HTTP Status | Frontend Shape |
|-----------------|-------------|----------------|
| `rb.success(data)` | 200 | `{ ...data }` |
| `rb.created(data)` | 201 | `{ ...data }` |
| `rb.no_content()` | 204 | empty body |
| `rb.error(msg)` | 4xx/5xx | `{ "error": "msg" }` |
| `rb.paginated(items, total, page, pages, has_next)` | 200 | `{ "items": [...], "total", "page", "pages", "has_next" }` |

##### Constants Sync

> List the constants that must stay in sync between backend and frontend:

| Constant | Backend Location | Frontend Location |
|----------|-----------------|-------------------|
| Role levels | `{{backend_constants_path}}` | `{{frontend_constants_path}}` |
| Validation limits | `{{backend_validation_path}}` | `{{frontend_constants_path}}` |

**Rules:**
- One API module per entity.
- Use `createCrudApi()` for standard CRUD; extend with custom methods as needed.
- Components consume API modules, never the HTTP client directly.

---

### 8. Data Fetching & Caching

> If stack includes TanStack Query:

**Framework:** TanStack Query v{{version}}

#### Query Pattern

```tsx
const { data = [], isLoading, error } = useQuery({
  queryKey: queryKeys.{{entity}}.list({ page, search }),
  queryFn: () => {{entity}}Api.list({ page, search }),
  enabled: !!userId,
});
```

#### Mutation Pattern

```tsx
const createMutation = useMutation({
  mutationFn: (data) => {{entity}}Api.create(data),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.{{entity}}.all });
  },
  onError: (err) => {
    setError(extractApiError(err, "errors.createFailed", t));
  },
});
```

#### Query Key Factory

All queries **must** use keys from a centralized factory:

```tsx
queryKeys.{{entity}}.all           // ["{{entity}}"]
queryKeys.{{entity}}.list(params)  // ["{{entity}}", "list", params]
queryKeys.{{entity}}.detail(id)    // ["{{entity}}", "detail", id]
```

#### QueryClient Defaults

| Setting | Value | Rationale |
|---------|-------|-----------|
| `staleTime` | {{value}} | {{rationale}} |
| `gcTime` | {{value}} | {{rationale}} |
| `retry` | 1 (queries) / 0 (mutations) | One retry for transient errors |
| `refetchOnWindowFocus` | {{value}} | {{rationale}} |

#### Expected UI States

Every data-fetching component must handle:

| State | UI | Implementation |
|-------|-----|----------------|
| **Loading** | Spinner or skeleton | `if (isLoading) return <LoadingSpinner />;` |
| **Error** | Alert with retry | `if (error) return <AlertMessage variant="error">...` |
| **Empty** | Informational message | `if (data.length === 0) return <p>{t("noResults")}</p>;` |
| **Success** | Render data | Normal rendering path |

**Rules:**
- Always handle all 4 UI states.
- Use `useQuery` for fetching; `useMutation` for state-changing operations.
- Use the `queryKeys` factory — never hardcode key arrays.
- Invalidate via parent keys after mutations.

---

### 9. Form Handling

> Document your form handling approach: manual state, React Hook Form, Formik, etc.

**Approach:** {{form_approach}}

#### Validation

- Client-side validation uses shared `VALIDATION` constants.
- Validation in submit handlers; server-side errors shown via alert components.

**Rules:**
- Validate against shared constants for field length/format.
- Provide keyboard shortcuts for form submission (Enter) and cancellation (Escape).

---

### 10. Rich Text Editor

> If your application includes a rich text editor, document the framework and content flow:

**Framework:** {{editor_framework}}

#### Content Flow

1. User edits via rich text editor
2. Content serialized as HTML
3. HTML sanitized with DOMPurify before storage
4. Backend stores HTML; frontend renders via sanitized component

**Rules:**
- All rich text content must be sanitized with DOMPurify before rendering user-generated HTML.
- Editor toolbar components are shared primitives — do not duplicate.

---

### 11. Modal Management

#### Hook Selection Guide

| Hook | Use Case | Manages |
|------|----------|---------|
| `useModalState()` | Single modal toggle | `{ isOpen, open, close }` |
| `useCrudModals()` | Create/edit/delete modal trio | `{ isOpen(name), open(name, item), close(name), selected }` |

**Rules:**
- Maximum 1 modal visible at a time (no stacking).
- Use form-specific modal variants for dialogs containing forms (prevent data loss from backdrop clicks).
- For complex pages, consolidate modals into a dedicated sub-component.

---

### 12. Performance

#### Memoization Guidelines

| Technique | When to Use | When NOT to Use |
|-----------|------------|-----------------|
| `useMemo` | Expensive computations (tree building, sorting large lists) | Simple derivations, small arrays |
| `useCallback` | Callbacks passed to memoized children | Handlers used only in the same component |
| `React.memo` | Leaf components that re-render frequently with same props | Components that always receive new props |

#### Lazy Loading

- All page routes lazy-loaded via `React.lazy()` + `<Suspense>`.
- Heavy components imported dynamically.

**Rules:**
- Profile before optimizing — don't prematurely memoize.
- Always clean up blob URLs with `URL.revokeObjectURL()` in effect cleanup.
- Debounce search inputs (300ms default).

---

### 13. Accessibility (WCAG 2.1 AAA Target)

#### Keyboard Navigation (WCAG 2.1.3)

- All interactive elements must be reachable via Tab.
- Modals trap focus and return focus to trigger on close.
- Dropdown/selector components support ArrowUp/ArrowDown, Enter, Escape.

#### ARIA Guidelines (WCAG 4.1.2)

- Modals: `role="dialog"`, `aria-modal="true"`, `aria-labelledby`.
- Alerts: `role="alert"` for error messages, `role="status"` for info/success.
- Toast notifications: `aria-live="polite"`, `role="status"`, `aria-atomic="true"`.
- Loading states: `aria-busy="true"` on containers.
- Icon-only buttons: always include `aria-label` or `title`.
- Toggle buttons: `aria-pressed="true/false"`.
- Form inputs: `aria-required`, `aria-invalid`, `aria-describedby`.

#### Form Labels (WCAG 1.3.1, 3.3.2)

- Every form input must have a visible `<label>` with `htmlFor`.
- Placeholder text is supplementary — never the sole label.
- Error messages linked via `aria-describedby`.

#### Color Contrast (WCAG 1.4.6 AAA Enhanced)

> Document your color contrast ratios:

- Primary color on white: {{ratio}} (target: ≥7:1 for AAA)
- All text on light backgrounds: minimum ~5.7:1

#### Visual Presentation (WCAG 1.4.8)

- Body font size: relative units for zoom support.
- Minimum font size: 14px equivalent.
- Text content blocks: `max-width: 80ch`.

#### Skip Navigation (WCAG 2.4.1)

- "Skip to main content" link as first child of Layout.

#### Reduced Motion (WCAG 2.3.2)

- `@media (prefers-reduced-motion: reduce)` disables animations.

**Rules:**
- Every icon-only button must have an `aria-label`.
- Destructive actions use type-to-confirm dialogs.
- Error messages use `role="alert"`.
- All form inputs must have associated `<label>` elements.
- New table headers must include `scope="col"`.

---

### 14. Testing

> If stack includes Vitest:

**Stack:** Vitest + @testing-library/react + happy-dom

#### File Naming

- Component tests: `ComponentName.test.tsx`
- Hook tests: `useHookName.test.ts`
- Utility tests: `utilityName.test.ts`

#### Test Pattern

```tsx
vi.mock("../../api/{{entity}}Api", () => ({
  {{entity}}Api: { list: vi.fn(), create: vi.fn() },
}));
vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key, i18n: { language: "en-US" } }),
}));

describe("ComponentName", () => {
  it("should render expected content", () => {
    render(<ComponentName />);
    expect(screen.getByText("expected.i18n.key")).toBeTruthy();
  });
});
```

**Rules:**
- Mock **API modules**, not the HTTP client, in component tests.
- Use a stable `useTranslation` mock: `(key) => key`.
- Test files live alongside their source files (co-located).

---

### 15. Naming Conventions

| Category | Convention | Examples |
|----------|-----------|---------|
| Components | PascalCase `.tsx` | `LoginForm.tsx`, `SettingsPage.tsx` |
| Hooks | camelCase, `use` prefix `.ts` | `useAsyncData.ts`, `useModalState.ts` |
| Utilities | camelCase `.ts` | `errorUtils.ts`, `dateFormatter.ts` |
| Constants | UPPER_SNAKE_CASE | `SESSION_EXPIRED`, `STALE_THRESHOLD_MS` |
| API modules | camelCase + `Api` suffix `.ts` | `authApi.ts`, `{{entity}}Api.ts` |
| Pages | PascalCase + `Page` suffix `.tsx` | `SettingsPage.tsx`, `DashboardPage.tsx` |
| Contexts | PascalCase + `Context` suffix `.tsx` | `AuthContext.tsx` |
| Type definitions | PascalCase or camelCase `.ts` | `src/types/api.ts`, `src/types/entities.ts` |
| CSS classes | BEM (`block__element--modifier`) | `btn--primary`, `nav__link--active` |
| i18n keys | dot notation | `errors.loadFailed`, `auth.loginPlaceholder` |

---

### 16. Import Conventions

> If stack includes Vite:

**Path alias imports** (`@/`) for cross-boundary imports. Relative paths for co-located imports.

#### Import Order

1. React + external libraries
2. Internal API modules (`@/api/`)
3. Context and hooks (`@/context/`, `@/hooks/`)
4. Utilities (`@/utils/`)
5. Components (`@/components/`, `@/features/`)
6. Co-located relative imports (`./`, `../`)
7. Assets/styles

---

### 17. Error Handling

#### In Components (TanStack Query)

```tsx
const { data, error, isLoading } = useQuery({
  queryKey: queryKeys.{{entity}}.list(params),
  queryFn: () => {{entity}}Api.list(params),
});

if (error) {
  return <AlertMessage variant="error">{error.message}</AlertMessage>;
}
```

#### Error Extraction

```ts
import { extractApiError } from "@/utils/errorUtils";

try {
  await api.create(data);
} catch (err) {
  setError(extractApiError(err, "errors.createFailed", t));
}
```

#### Error Boundary

- Wrap each page route in an error boundary to prevent blank screens.

**Rules:**
- Always use a centralized error extraction utility.
- Provide an i18n fallback key for error messages.
- Display errors via alert components.

---

### 18. Authentication & Permissions

#### AuthContext API

| Method/Property | Description |
|-----------------|-------------|
| `user` | Current user object or `null` |
| `loading` | Auth state initializing |
| `login(username, password)` | Returns `{ success, error? }` |
| `logout()` | Ends session |
| `isAdmin()` | Admin check |

#### Permission Hook

```ts
const { isSystemAdmin, canWrite, canRead } = usePermissions(resourceContext);
```

#### Route Protection

```tsx
<ProtectedRoute adminOnly={true}>
  <AdminOnlyPage />
</ProtectedRoute>
```

**Rules:**
- Use a centralized permission evaluator — never inline role comparisons.
- Use route guards for route-level access control.
- JWT tokens stored as HttpOnly cookies; user profile cached in localStorage for optimistic rendering.

---

### 19. Reusable Components

> Document your shared component library as it grows:

| Component | Purpose |
|-----------|---------|
| `AlertMessage` | Dismissible alerts — `error`, `success`, `info`, `warning` |
| `Modal` | Generic modal dialog wrapper |
| `DoubleConfirmationModal` | Type-to-confirm destructive action dialog |
| `Breadcrumb` | Navigation breadcrumb |
| `Toast` | Auto-dismissing notification |
| `ErrorBoundary` | Catches rendering errors per page |

**Rules:**
- Before creating a new component, check `components/common/`.
- New reusable components go in `components/common/`.
- Domain-specific components go in `features/{{domain}}/`.

---

### 20. Custom Hooks

#### Cross-cutting hooks (`hooks/`)

> Document hooks shared across 2+ domains:

| Hook | Purpose |
|------|---------|
| `usePermissions` | Derive permission flags from auth + resource context |
| `useModalState` | Manage modal open/close state |
| `useCrudModals` | Manage CRUD action modals |
| `useFormKeyboardShortcuts` | Enter-to-submit, Escape-to-cancel |
| `useToast` | Local toast notification state |
| `useDebouncedSearch` | Debounced search input |
| `useListPage` | Shared list page behavior |

**Rules:**
- Cross-cutting hooks (used by 2+ unrelated domains) go in `hooks/`.
- Feature-specific hooks go in `features/{{domain}}/`.
- Each hook has JSDoc with `@param` and `@returns`.
- All feature folders use barrel exports (`index.ts`).

---

### 21. Type System

> If stack includes TypeScript:

**Approach:** TypeScript with `strict: {{true|false}}`, `allowJs: {{true|false}}`.

#### Directory Structure

```text
src/types/
├── index.ts      # Barrel re-export
├── api.ts        # API error shapes, response envelopes
├── auth.ts       # Authentication types
├── entities.ts   # Domain entity types
└── hooks.ts      # Custom hook return types
```

**Rules:**
- Organize types by concern, not by feature.
- Use barrel export in `types/index.ts`.
- Use `as const` assertions for immutable objects.
- Import types via `import type { ... }`.

---

### 22. File & Attachment Handling

> If your application handles file uploads/downloads, document the utilities here.

**Rules:**
- Normalize attachment data from API responses.
- Always revoke blob URLs in cleanup.
- File type detection uses extension-based checks; MIME validation happens server-side.

---

### 23. Date & Time Formatting

> Document your date/time formatting approach (library or pure JS):

**Rules:**
- Always parse UTC strings from the API with timezone awareness.
- Use a consistent formatter as the default for user-facing timestamps.

---

### 24. URL Construction Utilities

> If the application runs under a configurable base path, document the URL utilities:

| Function | Purpose |
|----------|---------|
| `withAppBase(path)` | Prepends base path to absolute paths |
| `stripAppBase(pathname)` | Removes base path prefix |

**Rules:**
- Use `import.meta.env.*` (Vite) for environment variables.
- Always strip trailing slashes from API URLs.

---

### 25. Local Storage Service

> Document your localStorage abstraction:

**Rules:**
- Never access `localStorage` directly in components.
- All storage operations wrapped in try/catch for graceful degradation.
- Only cache non-sensitive, reconstructible data.
- **Never store tokens or secrets in localStorage.**

---

### 26. Search Patterns

> Document your search hook selection guide:

#### Debounce Standard

All search hooks use a **300ms debounce** by default.

**Rules:**
- Use the appropriate search hook for each use case (list page search, type-ahead, full-text).
- Separate input state from applied/submitted search state.

---

### 27. Module-Level README Convention

Every frontend source subdirectory should contain a `README.md` with a module index and conventions.

**Required in:** `src/`, `src/api/`, `src/hooks/`, `src/components/`, and any feature directories

**Template:**

| File/Directory | Responsibility |
|---------------|---------------|
| `{{name}}` | {{one-line description}} |

**Rules:**
- Update the README when adding, removing, or renaming files in the directory.
- Keep descriptions to one line per entry.
- For `src/components/`, list subdirectories (not individual files) with their scope.
- Include a "Conventions" subsection for directory-specific patterns (e.g., "hooks must start with `use` prefix").

---

## Testing

### 1. Backend Testing (pytest)

> If stack includes Python + pytest:

#### Stack

| Tool | Purpose |
|------|---------|
| pytest | Test runner |
| pytest-cov | Coverage reporting |
| In-memory SQLite + StaticPool | Fast, isolated unit tests |

#### Fixtures (conftest.py)

| Fixture | Scope | Purpose |
|---------|-------|---------|
| `app` | session | App with test config (in-memory SQLite) |
| `client` | function | Test client for HTTP calls |
| `db_session` | function | ORM session (auto-rollback between tests) |
| `admin_token` | function | JWT access token for admin user |
| `member_user` / `guest_user` | function | Pre-created test users with cleanup |

#### Factory Fixtures

Factory fixtures create entities with sensible defaults and auto-incrementing IDs:

```python
@pytest.fixture
def create_entity(db_session):
    def _create(name='test_entity', **kwargs):
        defaults = {'name': name, 'status': STATUS_ACTIVE}
        defaults.update(kwargs)
        entity = Entity(**defaults)
        db.session.add(entity)
        db.session.flush()
        return entity
    return _create
```

**Rules:**
- Factories return flushed (not committed) model instances.
- Factories accept `**kwargs` to override any default.
- Factories handle FK dependencies.

#### Test Pattern

```python
def test_create_entity(client, admin_token):
    response = client.post('/api/{{entities}}/', json={'title': 'Test'},
                           headers={'Authorization': f'Bearer {admin_token}'})
    assert response.status_code == 201
    assert response.json['title'] == 'Test'
```

**Rules:**
- File naming: `test_<module>.py`
- Test both success and error paths (401, 403, 404, 400).
- Use fixtures for common setup — avoid repeated boilerplate.
- In-memory SQLite keeps tests fast; no external DB required.

#### Integration Tests (Database-Specific)

> If your project has a separate integration test suite against a real database:

**Setup:**
1. Start the test stack: `docker compose -f docker-compose.test.yml up -d`
2. Run integration tests: `cd {{BACKEND_DIR}} && pytest -m integration`
3. Tear down: `docker compose -f docker-compose.test.yml down -v`

**Marker segregation:**
- All integration tests use `pytestmark = pytest.mark.integration`
- Default `pytest` runs only unit tests
- `pytest -m integration` runs only the database-specific suite

**Focus areas for integration tests:**
- Row-level locking behavior
- Unique and FK constraint enforcement
- Timezone-aware datetime behavior
- Transaction rollback, savepoints, error recovery
- Full CRUD cycle for core entities

---

### 2. Frontend Testing (vitest)

> If stack includes React + Vitest:

#### Stack

| Tool | Purpose |
|------|---------|
| Vitest | Test runner (Vite-native) |
| @testing-library/react | Component rendering and queries |
| happy-dom | Lightweight DOM environment |
| @vitest/coverage-v8 | Coverage via V8 provider |

#### Mock Hierarchy

Mocks are set up in a consistent order at the top of test files:

1. **i18n** — stable `useTranslation` mock (critical)
2. **react-router-dom** — `useNavigate`, `useParams`, `Link`
3. **Context hooks** — `useAuth`, etc.
4. **API modules** — mock the API module, not the HTTP client
5. **Custom hooks** — mock hooks consumed by the component under test
6. **Child components** — render as `data-testid` containers

#### Stable useTranslation Mock (CRITICAL)

**Always use this pattern** — unstable mocks cause flaky tests and hangs:

```javascript
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key) => key,
    i18n: { language: "en-US", changeLanguage: vi.fn() },
  }),
}));
```

**Never** return a new object reference on each call. The mock must be referentially stable.

#### Test Setup Helpers

```javascript
beforeEach(() => {
  vi.clearAllMocks();
  // set up mock return values
});

afterEach(() => { cleanup(); });
```

#### Component Test Pattern

```javascript
describe("ComponentName", () => {
  it("should render expected content", () => {
    render(<ComponentName />);
    expect(screen.getByText("expected.i18n.key")).toBeTruthy();
  });

  it("should handle user interaction", async () => {
    render(<ComponentName />);
    await act(() => fireEvent.click(screen.getByTestId("action-btn")));
    expect(mockApi.create).toHaveBeenCalled();
  });
});
```

#### Hook Test Pattern

```javascript
import { renderHook, act } from "@testing-library/react";

it("should update state", () => {
  const { result } = renderHook(() => useMyHook());
  act(() => { result.current.doSomething(); });
  expect(result.current.value).toBe("expected");
});
```

#### Timer-Based Tests

```javascript
beforeEach(() => { vi.useFakeTimers({ shouldAdvanceTime: true }); });
afterEach(() => { vi.runOnlyPendingTimers(); vi.useRealTimers(); });

it("should debounce", async () => {
  const { result } = renderHook(() => useDebouncedSearch(mockFn));
  await act(async () => { result.current.setQuery("test"); });
  vi.advanceTimersByTime(300);
  expect(mockFn).toHaveBeenCalled();
});
```

**Rules:**
- Mock **API modules**, not the HTTP client directly.
- Mock child components as `data-testid` containers when testing parent behavior.
- Use `vi.clearAllMocks()` in `beforeEach`, `cleanup()` in `afterEach`.
- Wrap state updates in `act()`.
- For async operations, use `waitFor()` or `await act(async () => {...})`.

---

### 3. E2E Testing (Playwright)

> If stack includes Playwright:

#### Stack & Configuration

| Setting | Value |
|---------|-------|
| Base URL | `{{base_url}}` |
| Parallel | `false` — sequential execution |
| Retries | 0 locally, 1 in CI |
| Timeouts | 60s test, 10s expect, 15s navigation |
| Browser | Chromium only |

#### Auth Fixtures (worker-scoped)

```javascript
// Pre-authenticated pages — cached per worker
adminPage   // Browser context with admin JWT
memberPage  // Browser context with member JWT
```

**Rules:**
- Tests share database state — order matters.
- Use pre-authenticated fixtures, not manual login in each test.

---

### 4. Cross-Cutting Rules

#### File Naming

| Layer | Pattern | Example |
|-------|---------|---------|
| Backend | `test_<module>.py` | `test_auth_endpoints.py` |
| Frontend component | `ComponentName.test.tsx` | `SettingsPage.test.tsx` |
| Frontend hook | `useHookName.test.ts` | `useToast.test.ts` |
| Frontend utility | `utilityName.test.ts` | `errorUtils.test.ts` |
| E2E | `<feature>.spec.js` | `auth.spec.js` |

#### What to Test

- **Always:** success path, common error paths (401, 403, 404, 400)
- **Components:** rendering, user interactions, error display, loading states
- **Hooks:** state transitions, side effects, edge cases
- **API endpoints:** CRUD operations, permission enforcement, input validation
- **E2E:** critical user flows, RBAC enforcement

#### What NOT to Test

- Implementation details (internal state shape, private methods)
- Third-party library internals
- Styling/CSS classes (unless behavior-dependent)

#### Coverage

- Coverage is reported but no hard threshold is enforced.
- Aim for broad coverage of business logic and user-facing behavior.
- Prioritize untested critical paths over reaching a percentage target.

---

### 5. TanStack Query Testing Patterns

> If stack includes TanStack Query:

Components and hooks using TanStack Query require a `QueryClientProvider` wrapper in tests.

#### QueryWrapper Setup

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

export const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });

export const QueryWrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={createTestQueryClient()}>
    {children}
  </QueryClientProvider>
);
```

#### Usage

```tsx
render(<MyComponent />, { wrapper: QueryWrapper });

const { result } = renderHook(() => useMyQueryHook(), {
  wrapper: QueryWrapper,
});
```

**Rules:**
- Always wrap components/hooks that use `useQuery`/`useMutation` in `QueryWrapper`.
- Use `retry: false` and `gcTime: 0` in test QueryClient.
- Use `waitFor` for async query resolution.
- Mock the API module functions, not the query hooks themselves.

---

### 6. Smoke Testing (Registry-Driven)

> If stack includes a backend framework (Flask, Django, FastAPI, Express):

Smoke tests provide a fast, automated sanity check that all API endpoints respond without server errors. They are driven by a JSON registry file and a generic engine — no per-endpoint test code is needed.

#### Architecture

| Component | Location | Purpose |
|-----------|----------|---------|
| `smoke_test_core.py` | `.claude/skills/scripts/` | Generic engine: runner, registry loader, framework adapters, auth adapters |
| `smoke_test_registry.json` | `.claude/skills/scripts/` | Endpoint registry: groups, expected statuses, auth requirements, ID capture |
| `smoke_test_api.py` | `.claude/skills/scripts/` | Thin project-specific runner: imports core, creates test client, loads registry |

#### How It Works

1. The runner creates an in-memory test client (e.g., Flask test client with SQLite)
2. Auth setup: registers a test user, logs in, captures JWT
3. For each endpoint group in the registry, sends requests in order
4. Records PASS (expected status), WARN (auth/client errors), or FAIL (5xx or unexpected)
5. Prints a summary report: `PASS: N | WARN: N | FAIL: N`

#### Registry Format

```json
{
  "framework": "flask",
  "test_config": "unit_testing",
  "auth": { "register_path": "/api/auth/register", "login_path": "/api/auth/login", ... },
  "groups": [
    {
      "name": "Entity Name",
      "endpoints": [
        { "method": "POST", "path": "/api/entities", "body": {...}, "expect": [201], "auth": true, "capture_id": true },
        { "method": "GET", "path": "/api/entities/{id}", "expect": [200], "auth": true }
      ]
    }
  ]
}
```

#### Adding Endpoints

To add a new endpoint to smoke tests, edit `smoke_test_registry.json` — no Python changes needed:

1. Add the endpoint to the appropriate group (or create a new group)
2. Set `expect` to the list of acceptable status codes
3. Set `auth: true` if the endpoint requires authentication, `admin: true` for admin-only
4. Set `capture_id: true` on POST endpoints whose response `id` is needed by subsequent requests
5. Use `{id}` in paths to reference the current group's captured ID, or `{GroupName.id}` for cross-group references

#### Running

```bash
# Via the /smoke-test skill (recommended):
/smoke-test api          # API only — fast, no servers needed
/smoke-test ui           # Playwright UI tests only
/smoke-test              # Both (default)

# Directly:
cd backend && python ../.claude/skills/scripts/smoke_test_api.py
```

#### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All endpoints responded as expected |
| 1 | One or more endpoints returned unexpected errors |
| 2 | Script-level error (import failure, app creation failure) |

**Rules:**
- Keep the registry up to date when adding new endpoints.
- Smoke tests are not a substitute for unit tests — they verify that endpoints respond, not that business logic is correct.
- The API scope uses an in-memory database, so tests are fast and isolated.

---

### 7. Security Testing Patterns

Security testing should be a first-class concern alongside functional testing.

#### Backend — Auth & Permission Tests

```python
# Test unauthenticated access (expect 401)
def test_create_entity_unauthenticated(client):
    response = client.post('/api/{{entities}}/', json={'title': 'Test'})
    assert response.status_code == 401

# Test wrong role (expect 403)
def test_create_entity_as_guest(client, guest_token):
    response = client.post('/api/{{entities}}/', json={'title': 'Test'},
                           headers={'Authorization': f'Bearer {guest_token}'})
    assert response.status_code == 403
```

#### Backend — Input Validation Tests

```python
# Test oversized input (expect 400)
def test_create_entity_title_too_long(client, admin_token):
    response = client.post('/api/{{entities}}/', json={'title': 'A' * 1000},
                           headers={'Authorization': f'Bearer {admin_token}'})
    assert response.status_code == 400
```

#### Frontend — Security-Relevant Component Tests

```javascript
// Test that user-generated HTML is sanitized before rendering
it("should sanitize HTML content before rendering", () => {
  const maliciousContent = '<img src=x onerror="alert(1)">';
  render(<RichTextContent content={maliciousContent} />);
  const img = document.querySelector('img[onerror]');
  expect(img).toBeNull();
});

// Test that admin-only UI is hidden for non-admins
it("should not render admin controls for members", () => {
  mockUseAuth.mockReturnValue({ user: mockUser, isAdmin: () => false });
  render(<SettingsPage />);
  expect(screen.queryByTestId("admin-actions")).toBeNull();
});
```

#### Rules

- Every new endpoint must have at least one unauthenticated test (401) and one unauthorized test (403).
- Every endpoint accepting user input must test oversized values against `VALIDATION` constants.
- Every endpoint with schemas must test invalid input shapes (missing required fields, wrong types).
- Components rendering user-generated HTML must test that `<script>` and event handlers are stripped.

---

## i18n

### 1. Locale Codes

All layers use **RFC 5646** locale codes consistently:

| Context | Format | Values | Default |
|---------|--------|--------|---------|
| Frontend | RFC 5646 | `{{PRIMARY_LOCALE}}`, `{{SECONDARY_LOCALE}}` | `{{PRIMARY_LOCALE}}` |
| Backend (API responses) | RFC 5646 | `{{PRIMARY_LOCALE}}`, `{{SECONDARY_LOCALE}}` | `{{BACKEND_DEFAULT_LOCALE}}` |
| Database (user preference) | RFC 5646 | `{{PRIMARY_LOCALE}}`, `{{SECONDARY_LOCALE}}` | `{{PRIMARY_LOCALE}}` |

#### Backward Compatibility

> If your project accepts legacy locale formats, document the normalization rules:

- Backend `normalize_locale()` accepts 2-letter input and normalizes to RFC 5646.

---

### 2. Frontend i18n

> If stack includes react-i18next:

#### Setup

- Framework: i18next + react-i18next
- Single `translation` namespace (no multi-namespace)
- `interpolation.escapeValue: false` (framework handles escaping)
- Resource keys: RFC 5646 codes
- Language loaded from user preferences on startup

> **Security warning:** Because `escapeValue` is disabled, the frontend framework's default escaping is the only protection. This does NOT apply when translations are rendered via `dangerouslySetInnerHTML`. Never interpolate user-supplied values into translation keys that are rendered as raw HTML without sanitization first.

#### Translation Files

| File | Purpose |
|------|---------|
| `src/i18n/locales/{{primary}}.json` | Primary locale translations (e.g., `en-US.json`) |
| `src/i18n/locales/{{secondary}}.json` | Secondary locale translations (e.g., `pt-BR.json`) |

Both files must have **identical key structure** — parallel keys, no extras in either file.

#### Key Naming Convention

Hierarchical dot notation with camelCase leaf names:

```
"auth.loginPlaceholder"
"{{entity}}.confirmDelete"
"errors.loadFailed"
```

| Segment | Convention | Examples |
|---------|-----------|---------|
| Root | Feature/domain name | `auth`, `errors`, `settings` |
| Leaves | camelCase action/noun | `title`, `confirmDelete`, `loadFailed` |

#### Interpolation

```json
{ "confirmDeleteMessage": "Type \"{{name}}\" to confirm deletion..." }
```

Usage: `t("confirmDeleteMessage", { name: entity.title })`

#### Usage in Components

```tsx
const { t, i18n } = useTranslation();

// String lookup
<h1>{t("{{section}}.title")}</h1>

// Current language (RFC 5646)
const lang = i18n.language;

// Change language
i18n.changeLanguage("{{locale}}");
```

---

### 3. Backend i18n

> If stack includes Flask-Babel:

#### Setup

- **Framework:** Flask-Babel with standard gettext `.po/.pot` catalogs
- **Catalogs:** `{{BACKEND_DIR}}/translations/{locale}/LC_MESSAGES/messages.po`
- **Helpers:** Wrapper functions around `flask_babel.gettext()`
- **Compilation:** `.mo` files built via `pybabel compile -d translations`

#### Translation Lookup

```python
locale = get_request_locale()
message = get_common_error('Error message key', locale=locale)
```

#### Locale Negotiation

Priority:
1. Query parameter `?lang=...` (normalized)
2. HTTP `Accept-Language` header (first match)
3. Default: `{{BACKEND_DEFAULT_LOCALE}}`

#### Interpolation

Uses Python `str.format()` with keyword arguments (applied after gettext lookup):

```python
message = get_common_error('Entity {name} not found', locale=locale, name=name)
```

> **Security warning:** Python's `str.format()` can access object attributes. Never pass user-supplied data as the format string itself. Always use keyword arguments from a trusted template string.

#### Adding New Backend Strings

1. Add the `msgid` / `msgstr` pair to all `.po` files
2. Compile: `pybabel compile -d translations`
3. Use helper functions in code
4. To extract markers from source: `pybabel extract -F babel.cfg -o translations/messages.pot .`

---

### 4. Multilingual Domain Entities

> If any entities store translations in the database, document them:

| Entity | Translation Table | Fields |
|--------|------------------|--------|
| {{Entity}} | {{EntityTranslation}} | `name`, `locale` |

#### Resolution

```python
name = resolve_translation_name(entity.translations, locales=['{{locale}}'], fallback='{{fallback}}')
```

---

### 5. Rules — Always Follow

#### When Creating or Modifying Strings

1. **Update all locale files** — every key in one file must exist in all others.
2. **Mind diacritics** — languages with accented characters require proper encoding.
3. **No hardcoded text** — every user-facing string must use an i18n key (frontend) or helper function (backend).
4. **Backend error messages** — add entries to all `.po` files, then compile.

#### Key Sync Checklist

When adding a feature that spans both layers:

- [ ] Frontend: add keys to all locale JSON files
- [ ] Backend: add entries to all `.po` files, then compile
- [ ] Constants: ensure validation limits match between backend and frontend
- [ ] Labels: if adding selectable options, ensure all locale labels are present

#### Email Templates

> If your application sends localized emails:

- Email template dictionaries use short language keys (e.g., `'en'`, `'pt'`)
- An adapter function converts RFC 5646 locale codes to template keys

---

### 6. Default Locale Rationale

> Document why your frontend and backend use different default locales (if they do):

- **Frontend default:** `{{PRIMARY_LOCALE}}` — {{rationale}}
- **Backend default:** `{{BACKEND_DEFAULT_LOCALE}}` — {{rationale}}

---

### 7. Known Limitations & Future Improvements

| Limitation | Impact | Future Target |
|------------|--------|---------------|
| {{limitation}} | {{impact}} | {{target}} |
