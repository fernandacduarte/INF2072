#!/usr/bin/env python3
# designer: When you want a full-coverage sweep of the harness's validation
#   scripts -- not just the fast gate, but every registered check -- I'm the
#   orchestrator that discovers them, runs them in turn, and rolls the results
#   up into a single pass/fail verdict. You get a per-check breakdown (and an
#   optional JUnit XML report for CI pipelines) instead of having to chase
#   each check script by name.
"""
run_all_checks.py -- CI-independent validation orchestrator for SEJA checks.

Invocation: agent-invoked
Lifecycle: active

Discovers and runs all check_*.py scripts in the scripts directory with unified
exit codes and optional JUnit XML output. This is the preferred orchestrator for
CI pipelines; run_preflight_fast.py remains the lighter-weight option for git
hooks and quick local validation.

Exit codes:
    0 = all checks pass
    1 = one or more checks failed
    2 = orchestrator error

Usage
-----
    # Run all checks from repo root
    python .claude/skills/scripts/run_all_checks.py --root .

    # With JUnit XML output
    python .claude/skills/scripts/run_all_checks.py --root . --junit results.xml

    # Filter by stack (uses check_plugin_registry.json)
    python .claude/skills/scripts/run_all_checks.py --root . --filter flask

    # Verbose mode (streams child stdout/stderr)
    python .claude/skills/scripts/run_all_checks.py --root . --verbose
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

SCRIPTS_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(SCRIPTS_DIR))
from project_config import REPO_ROOT as _DEFAULT_ROOT  # noqa: E402

REGISTRY_FILENAME = "check_plugin_registry.json"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class CheckResult:
    """Result of a single check script execution."""

    __slots__ = ("script", "status", "duration", "stdout", "stderr", "returncode")

    def __init__(
        self,
        script: str,
        status: str,
        duration: float,
        stdout: str,
        stderr: str,
        returncode: int,
    ) -> None:
        self.script = script
        self.status = status
        self.duration = duration
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def discover_scripts(scripts_dir: Path) -> List[Path]:
    """Find all check_*.py files in scripts/ and co-located skill subdirectories."""
    results = list(scripts_dir.glob("check_*.py"))
    for skill_dir in sorted(scripts_dir.parent.iterdir()):
        if skill_dir.is_dir() and skill_dir.name not in ("scripts", "_internal"):
            results.extend(skill_dir.glob("check_*.py"))
    return sorted(set(results))


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

def load_registry(scripts_dir: Path) -> Optional[List[dict]]:
    """Load check_plugin_registry.json. Returns None if missing."""
    registry_path = scripts_dir / REGISTRY_FILENAME
    if not registry_path.is_file():
        return None
    with open(registry_path, encoding="utf-8") as f:
        return json.load(f)


def filter_by_stack(
    scripts: List[Path],
    stack_filter: str,
    registry: Optional[List[dict]],
) -> List[Path]:
    """Keep only scripts whose registry entry matches the given stack keyword.

    A script matches if the stack_filter string appears in any of its
    backend or frontend stack values. Scripts with 'any' in their stack
    always match. If the registry is None, all scripts are returned.
    """
    if registry is None:
        print(
            f"WARNING: {REGISTRY_FILENAME} not found; "
            "running all checks (no filtering applied).",
            file=sys.stderr,
        )
        return scripts

    # Build lookup: script filename -> registry entry
    lookup: dict[str, dict] = {}
    for entry in registry:
        lookup[entry["script"]] = entry

    needle = stack_filter.lower()
    filtered: List[Path] = []
    for script in scripts:
        entry = lookup.get(script.name)
        if entry is None:
            # Not in registry -- include by default
            filtered.append(script)
            continue
        stack = entry.get("stack", {})
        all_values: List[str] = []
        for values in stack.values():
            all_values.extend(v.lower() for v in values)
        if "any" in all_values or needle in all_values:
            filtered.append(script)

    return filtered


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def run_script(
    script: Path,
    root: Path,
    verbose: bool,
) -> CheckResult:
    """Execute a single check script and return its result."""
    cmd = [sys.executable, str(script)]
    start = time.monotonic()
    try:
        result = subprocess.run(
            cmd,
            cwd=str(root),
            capture_output=not verbose,
            text=True,
            timeout=120,
        )
        duration = time.monotonic() - start
        status = "PASS" if result.returncode == 0 else "FAIL"
        stdout = "" if verbose else (result.stdout or "")
        stderr = "" if verbose else (result.stderr or "")
        return CheckResult(
            script=script.name,
            status=status,
            duration=duration,
            stdout=stdout,
            stderr=stderr,
            returncode=result.returncode,
        )
    except subprocess.TimeoutExpired:
        duration = time.monotonic() - start
        return CheckResult(
            script=script.name,
            status="ERROR",
            duration=duration,
            stdout="",
            stderr="Timeout: exceeded 120s",
            returncode=-1,
        )
    except Exception as exc:
        duration = time.monotonic() - start
        return CheckResult(
            script=script.name,
            status="ERROR",
            duration=duration,
            stdout="",
            stderr=str(exc),
            returncode=-1,
        )


# ---------------------------------------------------------------------------
# JUnit XML output
# ---------------------------------------------------------------------------

def write_junit_xml(results: List[CheckResult], path: Path) -> None:
    """Write JUnit XML report from check results."""
    testsuite = ET.Element("testsuite")
    testsuite.set("name", "seja-checks")
    testsuite.set("tests", str(len(results)))
    testsuite.set("failures", str(sum(1 for r in results if r.status == "FAIL")))
    testsuite.set("errors", str(sum(1 for r in results if r.status == "ERROR")))
    total_time = sum(r.duration for r in results)
    testsuite.set("time", f"{total_time:.3f}")

    for r in results:
        testcase = ET.SubElement(testsuite, "testcase")
        testcase.set("name", r.script)
        testcase.set("classname", "seja-checks")
        testcase.set("time", f"{r.duration:.3f}")

        if r.status == "FAIL":
            failure = ET.SubElement(testcase, "failure")
            failure.set("message", f"{r.script} failed with exit code {r.returncode}")
            failure.text = (r.stdout + r.stderr).strip() or "(no output)"
        elif r.status == "ERROR":
            error = ET.SubElement(testcase, "error")
            error.set("message", f"{r.script} encountered an error")
            error.text = (r.stdout + r.stderr).strip() or "(no output)"

    path.parent.mkdir(parents=True, exist_ok=True)
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space="  ")
    tree.write(str(path), xml_declaration=True, encoding="utf-8")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def print_summary(results: List[CheckResult]) -> None:
    """Print a formatted summary table of all results."""
    max_name = max((len(r.script) for r in results), default=10)
    header = f"{'Script':<{max_name}}  {'Status':<6}  {'Duration':>8}"
    sep = "-" * len(header)

    print()
    print("SEJA Validation Orchestrator -- Results")
    print(sep)
    print(header)
    print(sep)

    for r in results:
        duration_str = f"{r.duration:.2f}s"
        print(f"{r.script:<{max_name}}  {r.status:<6}  {duration_str:>8}")

    print(sep)

    passed = sum(1 for r in results if r.status == "PASS")
    failed = sum(1 for r in results if r.status == "FAIL")
    errors = sum(1 for r in results if r.status == "ERROR")
    total_time = sum(r.duration for r in results)

    parts = [f"{passed} passed"]
    if failed:
        parts.append(f"{failed} failed")
    if errors:
        parts.append(f"{errors} errors")
    parts.append(f"{total_time:.2f}s total")

    print(", ".join(parts))
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run all SEJA check scripts with unified reporting.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=_DEFAULT_ROOT,
        help="Repository root directory (default: auto-detected)",
    )
    parser.add_argument(
        "--junit",
        type=Path,
        default=None,
        metavar="PATH",
        help="Write JUnit XML report to PATH",
    )
    parser.add_argument(
        "--filter",
        type=str,
        default=None,
        metavar="STACK",
        help="Only run checks matching the given stack keyword (e.g. flask, react)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Stream child stdout/stderr to console",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    scripts_dir = root / ".claude" / "skills" / "scripts"

    if not scripts_dir.is_dir():
        print(f"ERROR: scripts directory not found: {scripts_dir}", file=sys.stderr)
        return 2

    # Discover
    scripts = discover_scripts(scripts_dir)
    if not scripts:
        print("ERROR: no check_*.py scripts found.", file=sys.stderr)
        return 2

    # Filter
    if args.filter:
        registry = load_registry(scripts_dir)
        scripts = filter_by_stack(scripts, args.filter, registry)
        if not scripts:
            print(f"No checks match stack filter '{args.filter}'.")
            return 0

    print(f"Running {len(scripts)} check(s)...")
    print()

    # Execute
    results: List[CheckResult] = []
    for script in scripts:
        label = script.name
        print(f"  {label} ... ", end="", flush=True)
        result = run_script(script, root, args.verbose)
        print(result.status, flush=True)

        # In non-verbose mode, print output of failed/errored checks
        if not args.verbose and result.status != "PASS":
            combined = (result.stdout + result.stderr).strip()
            if combined:
                for line in combined.splitlines():
                    print(f"    {line}")

        results.append(result)

    # Summary
    print_summary(results)

    # JUnit
    if args.junit:
        write_junit_xml(results, args.junit.resolve())
        print(f"JUnit XML written to: {args.junit}")

    # Exit code
    has_fail = any(r.status == "FAIL" for r in results)
    has_error = any(r.status == "ERROR" for r in results)
    if has_error:
        return 2
    if has_fail:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
