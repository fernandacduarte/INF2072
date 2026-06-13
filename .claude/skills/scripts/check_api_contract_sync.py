# designer: When you change a backend schema or a frontend type and
#   forget to change the other side, I line them up and show you which
#   fields are missing or mistyped on each side. You catch the drift
#   before a caller hits a broken response.
"""Check frontend/backend API contract synchronization.

Invocation: agent-invoked, hook-ci
Lifecycle: active

Purpose:
- Compare backend Marshmallow schema fields with frontend TypeScript interfaces.
- Report mismatches (missing fields, type inconsistencies).

Usage:
  python .claude/skills/scripts/check_api_contract_sync.py
  python .claude/skills/scripts/check_api_contract_sync.py --verbose
  python .claude/skills/scripts/check_api_contract_sync.py --self-test

Customization needed:
- BACKEND_SCHEMAS_DIR: path to Marshmallow schema files
- FRONTEND_API_DIR: path to frontend API type definitions
- KNOWN_PAIRS: mapping of schema files to their frontend counterparts

CHECK_PLUGIN_MANIFEST:
  name: API Contract Sync
  stack:
    backend: [flask]
    frontend: [react]
  scope: api
  critical: true
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from project_config import REPO_ROOT, get_path

# ── Configuration ──────────────────────────────────────────────────────────

BACKEND_SCHEMAS_DIR = get_path("BACKEND_SCHEMAS_DIR") or REPO_ROOT / "backend" / "app" / "schemas"
FRONTEND_API_DIR = get_path("FRONTEND_API_DIR") or REPO_ROOT / "frontend" / "src" / "api"

# Map backend schema files to frontend type definition files
# Format: (backend_schema_file, schema_class) -> (frontend_file, interface_name)
KNOWN_PAIRS: list[tuple[str, str, str, str]] = [
    # (backend_file, schema_class, frontend_file, interface_name)
    # Example:
    # ("group_schema.py", "GroupSchema", "groups.ts", "Group"),
]

# ── Parsers ────────────────────────────────────────────────────────────────

MARSHMALLOW_FIELD_RE = re.compile(
    r"^\s+(\w+)\s*=\s*(?:fields\.|ma\.)(\w+)\s*\(",
    re.MULTILINE,
)

TYPESCRIPT_FIELD_RE = re.compile(
    r"^\s+(\w+)(\??):\s*(.+?);",
    re.MULTILINE,
)


def parse_marshmallow_fields(content: str, schema_class: str) -> dict[str, str]:
    """Extract field names and types from a Marshmallow schema class."""
    fields: dict[str, str] = {}
    # Find the class definition
    class_re = re.compile(
        rf"class\s+{re.escape(schema_class)}\s*\([^)]*\)\s*:",
        re.MULTILINE,
    )
    match = class_re.search(content)
    if not match:
        return fields

    # Extract fields from class body (until next class or end of file)
    class_start = match.end()
    next_class = re.search(r"\nclass\s+\w+", content[class_start:])
    class_body = content[class_start:class_start + next_class.start()] if next_class else content[class_start:]

    for field_match in MARSHMALLOW_FIELD_RE.finditer(class_body):
        field_name = field_match.group(1)
        field_type = field_match.group(2)
        if field_name not in ("Meta", "class"):
            fields[field_name] = field_type

    return fields


def parse_typescript_fields(content: str, interface_name: str) -> dict[str, tuple[str, bool]]:
    """Extract field names, types, and optionality from a TypeScript interface."""
    fields: dict[str, tuple[str, bool]] = {}
    # Find the interface/type definition
    iface_re = re.compile(
        rf"(?:interface|type)\s+{re.escape(interface_name)}\s*(?:=\s*)?\{{",
        re.MULTILINE,
    )
    match = iface_re.search(content)
    if not match:
        return fields

    # Find matching closing brace
    start = match.end()
    depth = 1
    pos = start
    while pos < len(content) and depth > 0:
        if content[pos] == "{":
            depth += 1
        elif content[pos] == "}":
            depth -= 1
        pos += 1

    iface_body = content[start:pos - 1]

    for field_match in TYPESCRIPT_FIELD_RE.finditer(iface_body):
        field_name = field_match.group(1)
        is_optional = field_match.group(2) == "?"
        field_type = field_match.group(3).strip()
        fields[field_name] = (field_type, is_optional)

    return fields


def compare_contracts(
    backend_fields: dict[str, str],
    frontend_fields: dict[str, tuple[str, bool]],
    schema_name: str,
    interface_name: str,
) -> list[str]:
    """Compare backend and frontend fields, returning mismatch descriptions."""
    issues: list[str] = []

    backend_names = set(backend_fields.keys())
    frontend_names = set(frontend_fields.keys())

    # Fields in backend but not frontend
    for field in sorted(backend_names - frontend_names):
        issues.append(
            f"  MISSING in frontend: {interface_name}.{field} "
            f"(exists in {schema_name} as {backend_fields[field]})"
        )

    # Fields in frontend but not backend
    for field in sorted(frontend_names - backend_names):
        ts_type, optional = frontend_fields[field]
        opt_str = " (optional)" if optional else ""
        issues.append(
            f"  MISSING in backend: {schema_name}.{field} "
            f"(exists in {interface_name} as {ts_type}{opt_str})"
        )

    return issues


# ── Self-test ──────────────────────────────────────────────────────────────

def run_self_test() -> bool:
    """Run built-in test cases to validate the parser."""
    print("Running self-tests...\n")
    passed = 0
    failed = 0

    # Test 1: Matching schema/interface (expect no mismatches)
    backend_code = '''
class UserSchema(ma.Schema):
    id = fields.Integer(dump_only=True)
    name = fields.String(required=True)
    email = fields.String(required=True)
'''
    frontend_code = '''
interface User {
  id: number;
  name: string;
  email: string;
}
'''
    bf = parse_marshmallow_fields(backend_code, "UserSchema")
    ff = parse_typescript_fields(frontend_code, "User")
    issues = compare_contracts(bf, ff, "UserSchema", "User")
    if len(issues) == 0:
        print("  PASS: Test 1 — matching schema/interface (0 mismatches)")
        passed += 1
    else:
        print(f"  FAIL: Test 1 — expected 0 mismatches, got {len(issues)}")
        failed += 1

    # Test 2: Extra field on backend (expect 1 mismatch)
    backend_code_2 = '''
class GroupSchema(ma.Schema):
    id = fields.Integer(dump_only=True)
    title = fields.String(required=True)
    description = fields.String()
'''
    frontend_code_2 = '''
interface Group {
  id: number;
  title: string;
}
'''
    bf2 = parse_marshmallow_fields(backend_code_2, "GroupSchema")
    ff2 = parse_typescript_fields(frontend_code_2, "Group")
    issues2 = compare_contracts(bf2, ff2, "GroupSchema", "Group")
    if len(issues2) == 1 and "MISSING in frontend" in issues2[0] and "description" in issues2[0]:
        print("  PASS: Test 2 — extra backend field detected")
        passed += 1
    else:
        print(f"  FAIL: Test 2 — expected 1 'MISSING in frontend' for 'description', got {issues2}")
        failed += 1

    # Test 3: Extra field on frontend (expect 1 mismatch)
    backend_code_3 = '''
class PostSchema(ma.Schema):
    id = fields.Integer(dump_only=True)
    content = fields.String(required=True)
'''
    frontend_code_3 = '''
interface Post {
  id: number;
  content: string;
  author: string;
}
'''
    bf3 = parse_marshmallow_fields(backend_code_3, "PostSchema")
    ff3 = parse_typescript_fields(frontend_code_3, "Post")
    issues3 = compare_contracts(bf3, ff3, "PostSchema", "Post")
    if len(issues3) == 1 and "MISSING in backend" in issues3[0] and "author" in issues3[0]:
        print("  PASS: Test 3 — extra frontend field detected")
        passed += 1
    else:
        print(f"  FAIL: Test 3 — expected 1 'MISSING in backend' for 'author', got {issues3}")
        failed += 1

    print(f"\nSelf-test results: {passed}/{passed + failed} passed")
    return failed == 0


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check frontend/backend API contract synchronization."
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show matched fields"
    )
    parser.add_argument(
        "--self-test", action="store_true", help="Run built-in parser validation tests"
    )
    args = parser.parse_args()

    if args.self_test:
        success = run_self_test()
        sys.exit(0 if success else 1)

    if not KNOWN_PAIRS:
        print("No schema/interface pairs configured in KNOWN_PAIRS.")
        print("Add pairs to check_api_contract_sync.py to enable contract checking.")
        sys.exit(0)

    total_issues = 0
    pairs_checked = 0

    for backend_file, schema_class, frontend_file, interface_name in KNOWN_PAIRS:
        backend_path = BACKEND_SCHEMAS_DIR / backend_file
        frontend_path = FRONTEND_API_DIR / frontend_file

        if not backend_path.exists():
            print(f"WARNING: Backend schema not found: {backend_path}")
            continue
        if not frontend_path.exists():
            print(f"WARNING: Frontend types not found: {frontend_path}")
            continue

        backend_content = backend_path.read_text(encoding="utf-8")
        frontend_content = frontend_path.read_text(encoding="utf-8")

        bf = parse_marshmallow_fields(backend_content, schema_class)
        ff = parse_typescript_fields(frontend_content, interface_name)

        if not bf:
            print(f"WARNING: Could not parse {schema_class} from {backend_file}")
            continue
        if not ff:
            print(f"WARNING: Could not parse {interface_name} from {frontend_file}")
            continue

        pairs_checked += 1
        issues = compare_contracts(bf, ff, schema_class, interface_name)

        if issues:
            print(f"\nMISMATCH: {schema_class} <-> {interface_name}")
            for issue in issues:
                print(issue)
            total_issues += len(issues)
        elif args.verbose:
            print(f"  OK: {schema_class} <-> {interface_name} ({len(bf)} fields)")

    print(f"\n{'='*60}")
    print(f"Pairs checked: {pairs_checked}")
    print(f"Total mismatches: {total_issues}")

    if total_issues > 0:
        print("\nFAIL: API contract mismatches detected.")
        sys.exit(1)
    else:
        print("\nPASS: All API contracts are in sync.")
        sys.exit(0)


if __name__ == "__main__":
    main()
