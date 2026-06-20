#!/usr/bin/env python3
# designer: Before you ship a backend change, I walk every route in
#   your API, check each one for a login guard and an authorization
#   check, and hand you back the list of endpoints that would be
#   reachable without either. You see the gaps before a reviewer does.
"""
check_api_auth_decorators.py — Verify API endpoint auth coverage in dialogos.

Invocation: agent-invoked, hook-ci
Lifecycle: active

Checks performed
================
  1. Scan all .py files in backend/app/api/
  2. For each @bp.route(...) decorated function, check:
     - Presence of @jwt_required() decorator
     - Presence of authorization check (@admin_required or PermissionEvaluator usage)
  3. Report unprotected endpoints (excluding intentionally public ones)

Usage
-----
    python .claude/skills/scripts/check_api_auth_decorators.py

Run from the repository root (dialogos/).
Optional flags:
    --verbose       Show all endpoints including protected ones

CHECK_PLUGIN_MANIFEST:
  name: API Auth Decorators
  stack:
    backend: [flask]
    frontend: []
  scope: auth
  critical: true
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from project_config import REPO_ROOT, get_path

API_DIR = get_path("BACKEND_API_DIR") or REPO_ROOT / "backend" / "app" / "api"

# Endpoints that are intentionally public (no @jwt_required needed).
# Format: (module_name, function_name)
PUBLIC_ENDPOINTS = {
    ("auth", "login"),
    ("auth", "register"),
    ("status", "health_check"),
    ("status", "get_status"),
    ("status", "status_check"),
    ("access_requests", "create_access_request"),
    ("access_requests", "confirm_access_request"),
    ("access_requests", "approve_access_request"),
    ("access_requests", "reject_access_request"),
    ("access_requests", "clarify_access_request"),
    ("openapi", "openapi_spec"),
    ("password_reset", "request_password_reset"),
    ("password_reset", "confirm_password_reset"),
    ("password_reset", "reset_password"),
    ("password_reset", "validate_reset_token"),
}

# Regex to match @bp.route('...', methods=[...])
_ROUTE_RE = re.compile(
    r"^@\w+\.route\(\s*['\"](?P<path>[^'\"]+)['\"]"
    r"(?:.*?methods\s*=\s*\[(?P<methods>[^\]]*)\])?"
)

# Regex to match def function_name(...)
_DEF_RE = re.compile(r"^def\s+(?P<name>\w+)\s*\(")


def analyse_file(fpath: Path) -> list[dict]:
    """Parse a single API file and return endpoint metadata.

    Returns a list of dicts with keys:
      module, function, path, methods, has_jwt, has_authz, line
    """
    module = fpath.stem  # e.g. "auth", "groups"
    text = fpath.read_text(encoding="utf-8")
    lines = text.splitlines()

    endpoints = []
    pending_route = None
    pending_decorators: list[str] = []
    pending_line = 0

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Collect route decorator
        route_match = _ROUTE_RE.match(stripped)
        if route_match:
            pending_route = route_match.group("path")
            methods_str = route_match.group("methods") or "GET"
            pending_decorators = [stripped]
            pending_line = i
            # Also capture the methods
            methods = [m.strip().strip("'\"") for m in methods_str.split(",")]
            pending_methods = methods
            continue

        # Collect other decorators between @bp.route and def
        if pending_route and stripped.startswith("@"):
            pending_decorators.append(stripped)
            continue

        # Match function definition after decorators
        def_match = _DEF_RE.match(stripped)
        if def_match and pending_route:
            func_name = def_match.group("name")
            deco_text = "\n".join(pending_decorators)

            has_jwt = "jwt_required" in deco_text
            has_authz = any(pat in deco_text for pat in (
                "admin_required", "PermissionEvaluator",
            ))

            # Also check function body for PermissionEvaluator usage
            # (sometimes it's called inside the function, not as a decorator)
            body_start = i
            body_end = min(i + 30, len(lines))
            body_text = "\n".join(lines[body_start:body_end])
            if "PermissionEvaluator" in body_text or "admin_required" in body_text:
                has_authz = True

            endpoints.append({
                "module": module,
                "function": func_name,
                "path": pending_route,
                "methods": pending_methods,
                "has_jwt": has_jwt,
                "has_authz": has_authz,
                "line": pending_line,
            })

            pending_route = None
            pending_decorators = []
            continue

        # If we hit a non-decorator, non-def line while pending, reset
        if pending_route and stripped and not stripped.startswith("#"):
            # Could be a multi-line decorator — don't reset for continuations
            if not stripped.startswith(")") and not stripped.startswith("'") and not stripped.startswith('"'):
                pass  # keep pending

    return endpoints


def main():
    parser = argparse.ArgumentParser(description="Check API endpoint auth coverage")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show all endpoints including protected ones")
    args = parser.parse_args()

    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("# API Auth Decorator Check\n")

    if not API_DIR.is_dir():
        print(f"ERROR: API directory not found: {API_DIR}")
        sys.exit(1)

    all_endpoints = []
    for fpath in sorted(API_DIR.glob("*.py")):
        if fpath.name.startswith("__"):
            continue
        all_endpoints.extend(analyse_file(fpath))

    unprotected = []
    no_authz = []
    protected = []

    for ep in all_endpoints:
        is_public = (ep["module"], ep["function"]) in PUBLIC_ENDPOINTS

        if is_public:
            protected.append(ep)
            continue

        if not ep["has_jwt"]:
            unprotected.append(ep)
        elif not ep["has_authz"]:
            no_authz.append(ep)
        else:
            protected.append(ep)

    print(f"Total endpoints scanned: {len(all_endpoints)}")
    print(f"Protected: {len(protected)}")
    print(f"Public (whitelisted): {sum(1 for ep in all_endpoints if (ep['module'], ep['function']) in PUBLIC_ENDPOINTS)}")
    print()

    if args.verbose:
        print("## All Endpoints\n")
        for ep in all_endpoints:
            jwt_tag = "JWT" if ep["has_jwt"] else "NO-JWT"
            authz_tag = "AUTHZ" if ep["has_authz"] else "NO-AUTHZ"
            is_public = (ep["module"], ep["function"]) in PUBLIC_ENDPOINTS
            pub_tag = " [PUBLIC]" if is_public else ""
            methods = ",".join(ep["methods"])
            print(f"  [{jwt_tag}] [{authz_tag}]{pub_tag}  {ep['module']}.{ep['function']}  "
                  f"{methods} {ep['path']}  (line {ep['line']})")
        print()

    errors = []

    if unprotected:
        print(f"## Missing @jwt_required ({len(unprotected)})\n")
        for ep in unprotected:
            methods = ",".join(ep["methods"])
            msg = (f"{ep['module']}.{ep['function']}  {methods} {ep['path']}  "
                   f"(line {ep['line']})")
            print(f"- X {msg}")
            errors.append(msg)
        print()

    if no_authz:
        print(f"## Has JWT but missing authorization check ({len(no_authz)})\n")
        for ep in no_authz:
            methods = ",".join(ep["methods"])
            msg = (f"{ep['module']}.{ep['function']}  {methods} {ep['path']}  "
                   f"(line {ep['line']})")
            print(f"- ! {msg}")
        print()

    if errors:
        print(f"FAIL: {len(errors)} endpoint(s) missing @jwt_required")
        sys.exit(1)
    elif no_authz:
        print(f"WARN: {len(no_authz)} endpoint(s) with JWT but no explicit authorization check")
    else:
        print("PASS: All non-public endpoints have @jwt_required")


if __name__ == "__main__":
    main()
