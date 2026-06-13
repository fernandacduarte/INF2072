#!/usr/bin/env python3
# designer: When /check smoke exercises your project's API surface, I'm the
#   reusable runner underneath -- the piece that drives each endpoint from a
#   registry, classifies the response as PASS, WARN, or FAIL, and rolls the
#   results into a report. Your project brings the endpoint list, auth
#   adapter, and app factory; I handle the tracking, the error shaping, and
#   the exit-code convention so every smoke test speaks the same language.
"""Smoke Test Core — generic framework for registry-driven API smoke testing.

Invocation: library
Lifecycle: active

Provides:
- SmokeTestRunner: result tracking, error classification, report generation
- run_registry(): registry-driven endpoint executor
- Harness adapters: create_flask_client(), etc.
- Auth adapters: FlaskJWTAuth, etc.

Usage:
    from smoke_test_core import SmokeTestRunner, run_registry, create_flask_client, FlaskJWTAuth

Exit codes (convention):
    0 — All endpoints responded as expected (no FAILs)
    1 — One or more endpoints returned unexpected errors
    2 — Script-level error (import failure, app creation failure, etc.)
"""

import json
import sys
import os
import traceback

from project_config import get


# ---------------------------------------------------------------------------
# SmokeTestRunner — result tracking and reporting
# ---------------------------------------------------------------------------

class SmokeTestRunner:
    """Tracks smoke test results and generates reports."""

    def __init__(self):
        self.results = []

    def record(self, method, path, response, expected_statuses, detail=""):
        """Record the result of an API call."""
        status = response.status_code
        if status in expected_statuses:
            verdict = "PASS"
        elif 500 <= status < 600:
            verdict = "FAIL"
            detail = self._extract_error(response)
        elif status in (401, 403, 404, 405, 409, 422, 429):
            verdict = "WARN"
            detail = detail or self._extract_error(response)
        else:
            verdict = "FAIL"
            detail = detail or self._extract_error(response)
        self.results.append({
            "method": method,
            "path": path,
            "status": status,
            "verdict": verdict,
            "detail": detail,
        })
        return response

    def _extract_error(self, response):
        """Extract error message from response body."""
        try:
            data = response.get_json(silent=True)
            if data and isinstance(data, dict):
                return data.get("error", data.get("message", ""))[:120]
        except Exception:
            pass
        return ""

    def print_report(self):
        """Print the smoke test report to stdout. Returns fail count."""
        pass_count = sum(1 for r in self.results if r["verdict"] == "PASS")
        warn_count = sum(1 for r in self.results if r["verdict"] == "WARN")
        fail_count = sum(1 for r in self.results if r["verdict"] == "FAIL")

        print()
        print("=" * 80)
        print("API SMOKE TEST REPORT")
        print("=" * 80)
        print(f"PASS: {pass_count} | WARN: {warn_count} | FAIL: {fail_count}")
        print("-" * 80)
        print(f"{'METHOD':<8} {'PATH':<45} {'STATUS':<8} {'VERDICT':<8} {'DETAIL'}")
        print("-" * 80)

        for r in self.results:
            marker = ""
            if r["verdict"] == "FAIL":
                marker = " <<<< FAIL"
            elif r["verdict"] == "WARN":
                marker = " (warn)"
            detail = r["detail"][:50] if r["detail"] else ""
            print(f"{r['method']:<8} {r['path']:<45} {r['status']:<8} {r['verdict']:<8} {detail}{marker}")

        print("-" * 80)

        if fail_count > 0:
            print(f"\nFAILED ENDPOINTS ({fail_count}):")
            for r in self.results:
                if r["verdict"] == "FAIL":
                    print(f"  {r['method']} {r['path']} -> {r['status']}: {r['detail']}")

        print()
        return fail_count

    @property
    def pass_count(self):
        return sum(1 for r in self.results if r["verdict"] == "PASS")

    @property
    def warn_count(self):
        return sum(1 for r in self.results if r["verdict"] == "WARN")

    @property
    def fail_count(self):
        return sum(1 for r in self.results if r["verdict"] == "FAIL")


# ---------------------------------------------------------------------------
# Registry loader
# ---------------------------------------------------------------------------

def load_registry(path):
    """Load and validate a smoke test registry JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        registry = json.load(f)

    if "$schema" not in registry:
        print(f"WARNING: Registry {path} has no $schema field", file=sys.stderr)

    required_keys = ["framework", "auth", "groups"]
    for key in required_keys:
        if key not in registry:
            raise ValueError(f"Registry missing required key: {key}")

    return registry


# ---------------------------------------------------------------------------
# Registry-driven executor
# ---------------------------------------------------------------------------

def run_registry(client, runner, registry, auth_adapter):
    """Execute all endpoints in a registry.

    Args:
        client: Harness test client (e.g., Flask test client)
        runner: SmokeTestRunner instance
        registry: Parsed registry dict
        auth_adapter: Auth adapter instance with get_headers()/get_admin_headers()

    Returns:
        dict of captured IDs: {"group_name": {"id": value, ...}}
    """
    captured = {}  # group_name -> {field: value}
    auth_config = registry.get("auth", {})

    # Phase 1: Auth setup
    _run_auth_setup(client, runner, auth_config, auth_adapter)

    # Phase 2: Main endpoint groups
    for group in registry.get("groups", []):
        group_name = group.get("name", "Unknown")
        group_captured = {}
        print(f"  {group_name}...")

        for endpoint in group.get("endpoints", []):
            _run_endpoint(
                client, runner, endpoint, auth_adapter,
                group_captured, captured,
            )

        captured[group_name] = group_captured

    # Phase 3: Destructive auth (logout, password change)
    destructive = registry.get("destructive_auth", [])
    if destructive:
        print("  Auth (destructive)...")
        for endpoint in destructive:
            _run_endpoint(client, runner, endpoint, auth_adapter, {}, captured)

    return captured


def _run_auth_setup(client, runner, auth_config, auth_adapter):
    """Run the auth setup sequence: register + login."""
    print("  Auth setup...")

    _api_prefix = get("BACKEND_API_PREFIX", "/api")
    register_path = auth_config.get("register_path", f"{_api_prefix}/auth/register")
    login_path = auth_config.get("login_path", f"{_api_prefix}/auth/login")
    register_body = auth_config.get("register_body", {})
    login_body = auth_config.get("login_body", {})

    # Register
    resp = client.post(register_path, json=register_body)
    runner.record("POST", register_path, resp, {201})

    # Login
    resp = client.post(login_path, json=login_body)
    runner.record("POST", login_path, resp, {200})

    # Profile (if path specified)
    profile_path = auth_config.get("profile_path")
    if profile_path:
        headers = auth_adapter.get_headers()
        resp = client.get(profile_path, headers=headers)
        runner.record("GET", profile_path, resp, {200})


def _run_endpoint(client, runner, endpoint, auth_adapter, group_captured, all_captured):
    """Execute a single endpoint from the registry."""
    method = endpoint.get("method", "GET").upper()
    path = endpoint.get("path", "")
    expect = set(endpoint.get("expect", [200]))
    body = endpoint.get("body")
    auth = endpoint.get("auth", False)
    admin = endpoint.get("admin", False)
    capture_id = endpoint.get("capture_id", False)
    label = endpoint.get("label", "")
    depends_on = endpoint.get("depends_on")

    # Substitute {id} placeholders from captured IDs
    path = _substitute_path(path, group_captured, all_captured, depends_on)

    # Skip if path has unresolved placeholders
    if "{" in path:
        return

    # Build headers
    headers = {}
    if admin:
        headers = auth_adapter.get_admin_headers()
    elif auth:
        headers = auth_adapter.get_headers()

    # Build display path
    display_path = f"{path} ({label})" if label else path

    # Execute request
    kwargs = {"headers": headers}
    if body is not None and method in ("POST", "PUT", "PATCH"):
        kwargs["json"] = body

    http_method = getattr(client, method.lower())
    resp = http_method(path, **kwargs)
    runner.record(method, display_path, resp, expect)

    # Capture ID from response if requested
    if capture_id and resp.status_code in expect:
        data = resp.get_json(silent=True)
        if data and isinstance(data, dict):
            captured_id = data.get("id")
            if captured_id is not None:
                group_captured["id"] = captured_id


def _substitute_path(path, group_captured, all_captured, depends_on=None):
    """Replace {id} and {group.id} placeholders in paths."""
    # Replace {id} with the current group's captured ID
    if "{id}" in path and "id" in group_captured:
        path = path.replace("{id}", str(group_captured["id"]))

    # Replace {GroupName.id} with another group's captured ID
    for group_name, group_data in all_captured.items():
        placeholder = "{" + group_name + ".id}"
        if placeholder in path and "id" in group_data:
            path = path.replace(placeholder, str(group_data["id"]))

    # Replace {depends_on} with explicit dependency
    if depends_on and "{ref_id}" in path:
        for group_name, group_data in all_captured.items():
            if group_name == depends_on and "id" in group_data:
                path = path.replace("{ref_id}", str(group_data["id"]))

    return path


# ---------------------------------------------------------------------------
# Harness adapters
# ---------------------------------------------------------------------------

def create_flask_client(config_name="unit_testing"):
    """Create a Flask test client with in-memory SQLite.

    Returns:
        tuple: (app, client, db) — Flask app, test client, SQLAlchemy db instance
    """
    from app import create_app
    from app.extensions import db

    app = create_app(config_name)
    ctx = app.app_context()
    ctx.push()
    db.create_all()

    client = app.test_client()
    return app, client, db, ctx


def cleanup_flask(db, ctx):
    """Clean up Flask test resources."""
    db.drop_all()
    ctx.pop()


# ---------------------------------------------------------------------------
# Auth adapters
# ---------------------------------------------------------------------------

class FlaskJWTAuth:
    """Auth adapter for Flask + JWT (HttpOnly cookies).

    Creates tokens directly via create_access_token (same as conftest.py).
    """

    def __init__(self, auth_config):
        self._config = auth_config
        self._user_id = None
        self._admin_user_id = None

    def setup(self, client):
        """Find the registered user and store their ID."""
        _default_user_model = get("BACKEND_USER_MODEL", "app.models.user.User")
        model_path = self._config.get("user_model_path", _default_user_model)
        login_field = self._config.get("user_model_login_field", "login")
        register_body = self._config.get("register_body", {})
        login_value = register_body.get(login_field, register_body.get("login", "smoke_user"))

        # Import the user model dynamically
        User = _import_class(model_path)
        user = User.query.filter_by(**{login_field: login_value}).first()
        if user:
            self._user_id = user.id

    def setup_admin(self, client):
        """Register and promote an admin user."""
        from app.extensions import db as _db

        admin_body = self._config.get("admin_register_body", {
            "login": "smoke_admin",
            "email": "smoke_admin@test.local",
            "name": "Smoke Admin",
            "password": "Adm1nP@ss!",
        })
        _api_prefix = get("BACKEND_API_PREFIX", "/api")
        _default_user_model = get("BACKEND_USER_MODEL", "app.models.user.User")
        register_path = self._config.get("register_path", f"{_api_prefix}/auth/register")

        # Register admin
        client.post(register_path, json=admin_body)

        # Promote to admin
        User = _import_class(self._config.get("user_model_path", _default_user_model))
        login_field = self._config.get("user_model_login_field", "login")
        admin_login = admin_body.get(login_field, admin_body.get("login", "smoke_admin"))
        admin_user = User.query.filter_by(**{login_field: admin_login}).first()

        if admin_user:
            role_field = self._config.get("admin_role_field", "role")
            role_value = self._config.get("admin_role_value", 99)
            setattr(admin_user, role_field, role_value)
            _db.session.commit()
            self._admin_user_id = admin_user.id

    def get_headers(self):
        """Get auth headers for the regular user."""
        if not self._user_id:
            return {}
        token = self._create_token(self._user_id)
        return {"Authorization": f"Bearer {token}"}

    def get_admin_headers(self):
        """Get auth headers for the admin user."""
        if not self._admin_user_id:
            return {}
        token = self._create_token(self._admin_user_id)
        return {"Authorization": f"Bearer {token}"}

    def _create_token(self, user_id):
        """Create a JWT access token directly."""
        from flask_jwt_extended import create_access_token
        return create_access_token(identity=str(user_id))


def _import_class(dotted_path):
    """Import a class from a dotted path like 'app.models.user.User'."""
    module_path, class_name = dotted_path.rsplit(".", 1)
    import importlib
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


# ---------------------------------------------------------------------------
# Main entry point (for direct execution with a registry path)
# ---------------------------------------------------------------------------

def main(registry_path=None, backend_dir=None):
    """Run a smoke test from a registry file.

    Args:
        registry_path: Path to the smoke test registry JSON
        backend_dir: Path to the backend directory (added to sys.path)

    Returns:
        int: exit code (0=pass, 1=fail, 2=error)
    """
    try:
        if backend_dir:
            backend_dir = os.path.abspath(backend_dir)
            if backend_dir not in sys.path:
                sys.path.insert(0, backend_dir)

        if not registry_path:
            print("ERROR: No registry path provided", file=sys.stderr)
            return 2

        registry = load_registry(registry_path)

        framework = registry.get("framework", "flask")
        if framework != "flask":
            print(f"ERROR: Unsupported framework: {framework}", file=sys.stderr)
            return 2

        # Create client
        app, client, db, ctx = create_flask_client(
            registry.get("test_config", "unit_testing")
        )

        runner = SmokeTestRunner()

        # Create auth adapter
        auth_adapter = FlaskJWTAuth(registry.get("auth", {}))

        print("Running API smoke tests...")

        # Run registry
        run_registry(client, runner, registry, auth_adapter)

        # Auth setup (find user after registration)
        auth_adapter.setup(client)

        # Run admin endpoints if registry has admin groups
        has_admin = any(
            any(ep.get("admin") for ep in g.get("endpoints", []))
            for g in registry.get("groups", [])
        )
        if has_admin:
            auth_adapter.setup_admin(client)

        # Cleanup
        cleanup_flask(db, ctx)

        # Report
        fail_count = runner.print_report()
        return 1 if fail_count > 0 else 0

    except Exception as e:
        print(f"\nSCRIPT ERROR: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 2
