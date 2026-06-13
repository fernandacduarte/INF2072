# designer: When you want to know whether your frontend and backend agree on
#   the API surface, I line up the backend's declared routes against the
#   frontend's API calls and flag the endpoints that one side added without
#   the other -- so dead routes and missing callers surface before a user
#   hits them.
"""Check that backend API routes have corresponding frontend API methods and vice versa.

Invocation: agent-invoked, hook-ci
Lifecycle: active

Purpose
- Detect frontend/backend API drift: routes defined on one side but missing on the other.
- List routes that exist in the backend but have no frontend caller.
- List frontend API calls that reference endpoints not defined in the backend.

Usage:
  python .claude/skills/scripts/check_route_coverage.py
  python .claude/skills/scripts/check_route_coverage.py --verbose

Customization needed:
- BACKEND_API_DIR: path to Flask blueprint files
- FRONTEND_API_DIR: path to frontend API modules
- ROUTE_PATTERN: regex for backend route decorators
- FRONTEND_CALL_PATTERN: regex for frontend API call patterns

CHECK_PLUGIN_MANIFEST:
  name: Route Coverage
  stack:
    backend: [flask]
    frontend: [react]
  scope: api
  critical: false
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from project_config import REPO_ROOT, get_path

# ── Configuration ──────────────────────────────────────────────────────────

BACKEND_API_DIR = get_path("BACKEND_API_DIR") or REPO_ROOT / "backend" / "app" / "api"
FRONTEND_API_DIR = get_path("FRONTEND_API_DIR") or REPO_ROOT / "frontend" / "src" / "api"

# Matches Flask route decorators: @bp.route('/path', methods=['GET'])
ROUTE_PATTERN = re.compile(
    r"""@\w+\.route\(\s*['"]([^'"]+)['"]"""
    r"""(?:\s*,\s*methods\s*=\s*\[([^\]]+)\])?\s*\)""",
    re.MULTILINE,
)

# Matches common frontend HTTP call patterns:
# axios.get('/api/path'), api.get('/path'), fetch('/api/path')
FRONTEND_CALL_PATTERN = re.compile(
    r"""(?:axios|apiClient|api|client|http)\s*\.\s*(get|post|put|patch|delete)"""
    r"""[^(]*\(\s*[`'"](/?api)?(/[^'"`\s]+)""",
    re.IGNORECASE | re.DOTALL,
)

# Also match template literal URLs: `${baseURL}/path`
FRONTEND_URL_PATTERN = re.compile(
    r"""[`'"](/(?:api/)?[a-z][a-z0-9_/-]+)['"`]""",
    re.IGNORECASE | re.MULTILINE,
)


def extract_backend_routes() -> dict[str, list[str]]:
    """Extract routes from backend Flask blueprints.

    Returns: dict mapping route path to list of HTTP methods.
    """
    api_dir = BACKEND_API_DIR
    if not api_dir.exists():
        print(f"WARNING: Backend API directory not found: {BACKEND_API_DIR}")
        return {}

    routes: dict[str, list[str]] = {}
    for py_file in api_dir.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        # Find blueprint prefix
        bp_prefix = ""
        bp_match = re.search(
            r"""Blueprint\s*\(\s*['"][^'"]+['"]\s*,\s*[^,]+,\s*url_prefix\s*=\s*['"]([^'"]+)['"]""",
            content,
        )
        if bp_match:
            bp_prefix = bp_match.group(1).rstrip("/")

        for match in ROUTE_PATTERN.finditer(content):
            route_path = match.group(1)
            methods_str = match.group(2)
            if methods_str:
                methods = [
                    m.strip().strip("'\"").upper()
                    for m in methods_str.split(",")
                ]
            else:
                methods = ["GET"]

            full_path = bp_prefix + route_path
            # Normalize parameter placeholders: <int:id> -> <id>
            full_path = re.sub(r"<\w+:(\w+)>", r"<\1>", full_path)
            routes[full_path] = methods

    return routes


def extract_frontend_endpoints() -> set[str]:
    """Extract API endpoint paths referenced in frontend code.

    Returns: set of endpoint path patterns.
    """
    api_dir = FRONTEND_API_DIR
    if not api_dir.exists():
        print(f"WARNING: Frontend API directory not found: {FRONTEND_API_DIR}")
        return set()

    endpoints: set[str] = set()
    for src_file in api_dir.rglob("*"):
        if not src_file.is_file():
            continue
        if src_file.suffix not in (".js", ".jsx", ".ts", ".tsx"):
            continue
        try:
            content = src_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        for match in FRONTEND_CALL_PATTERN.finditer(content):
            path = match.group(3)
            if path and len(path) > 1:
                # Normalize: strip /api prefix if present
                path = re.sub(r"^/api", "", path)
                # Replace template expressions with parameter placeholders
                path = re.sub(r"\$\{[^}]+\}", "<param>", path)
                endpoints.add(path)

        for match in FRONTEND_URL_PATTERN.finditer(content):
            path = match.group(1)
            if path and "/api/" in path:
                path = re.sub(r"^/api", "", path)
                path = re.sub(r"\$\{[^}]+\}", "<param>", path)
                endpoints.add(path)

    return endpoints


def normalize_for_comparison(path: str) -> str:
    """Normalize a route path for fuzzy comparison."""
    # Strip /api prefix so backend and frontend paths align
    normalized = re.sub(r"^/api", "", path)
    # Replace specific params with generic placeholder
    normalized = re.sub(r"<\w+>", "<param>", normalized)
    # Remove trailing slash
    normalized = normalized.rstrip("/")
    return normalized.lower()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check backend/frontend API route coverage."
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show matched routes"
    )
    args = parser.parse_args()

    print("Extracting backend routes...")
    backend_routes = extract_backend_routes()
    print(f"  Found {len(backend_routes)} backend routes\n")

    print("Extracting frontend API endpoints...")
    frontend_endpoints = extract_frontend_endpoints()
    print(f"  Found {len(frontend_endpoints)} frontend endpoint references\n")

    if not backend_routes and not frontend_endpoints:
        print("No routes found on either side. Check configuration paths.")
        sys.exit(0)

    # Normalize for comparison
    backend_normalized = {
        normalize_for_comparison(r): r for r in backend_routes
    }
    frontend_normalized = {
        normalize_for_comparison(e): e for e in frontend_endpoints
    }

    # Find matches and mismatches
    matched = set(backend_normalized.keys()) & set(frontend_normalized.keys())
    backend_only = set(backend_normalized.keys()) - set(frontend_normalized.keys())
    frontend_only = set(frontend_normalized.keys()) - set(backend_normalized.keys())

    print(f"{'='*60}")
    print(f"Matched routes: {len(matched)}")
    print(f"Backend-only (no frontend caller): {len(backend_only)}")
    print(f"Frontend-only (no backend route): {len(frontend_only)}")
    print(f"{'='*60}\n")

    if args.verbose and matched:
        print("MATCHED ROUTES:")
        for norm in sorted(matched):
            print(f"  {backend_normalized[norm]}")
        print()

    has_issues = False

    if backend_only:
        has_issues = True
        print("BACKEND ROUTES WITHOUT FRONTEND CALLERS:")
        print("(Routes defined in backend but not called from frontend API modules)\n")
        for norm in sorted(backend_only):
            route = backend_normalized[norm]
            methods = backend_routes.get(route, ["?"])
            print(f"  [{','.join(methods)}] {route}")
        print()

    if frontend_only:
        has_issues = True
        print("FRONTEND ENDPOINTS WITHOUT BACKEND ROUTES:")
        print("(Endpoints called from frontend but not found in backend blueprints)\n")
        for norm in sorted(frontend_only):
            print(f"  {frontend_normalized[norm]}")
        print()

    if has_issues:
        print(
            "Note: Some mismatches may be expected (e.g., third-party APIs, "
            "dynamically constructed URLs, or authentication endpoints)."
        )
        sys.exit(1)
    else:
        print("All backend routes have frontend callers and vice versa.")
        sys.exit(0)


if __name__ == "__main__":
    main()
