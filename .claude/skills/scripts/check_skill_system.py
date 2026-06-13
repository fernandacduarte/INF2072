#!/usr/bin/env python3
# designer: When you want to know whether your skills, agents, and their
#   declared references still hang together, I walk the whole .claude/
#   tree and check that every reference resolves, every dependency points
#   to a real skill, no cycle exists in the depends graph, and each agent
#   carries the frontmatter the harness expects. You get one report that
#   says which skills are structurally sound and which need attention.
"""
check_skill_system.py — Validate .claude skill system integrity.

Invocation: agent-invoked, hook-ci
Lifecycle: active

Exit codes: 0 = pass, 1 = failures found, 2 = script error.

Checks performed
================
  1. SKILL.md frontmatter: required fields (name, description), valid YAML
  2. metadata.references: all referenced files exist in _references/
  3. metadata.eager_references: valid list, paths exist, subset of references, no duplicates, warn if >6
  4. metadata.depends: all declared dependencies are valid skill names
  5. category field: present and matches allowed enum values
  6. Agent definitions: valid frontmatter with name, description, tools
  7. Dependency cycle detection: no circular depends chains
  8. Schema validation: context_budget enum validation

Usage
-----
    python .claude/skills/scripts/check_skill_system.py

Run from the repository root.
Optional flags:
    --verbose    Show details for passing checks too
    --self-test  Run built-in dependency cycle detection tests

CHECK_PLUGIN_MANIFEST:
  name: Skill System
  stack:
    backend: [any]
    frontend: [any]
  scope: harness
  critical: false
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CLAUDE_DIR = REPO_ROOT / ".claude"
SKILLS_DIR = CLAUDE_DIR / "skills"
HARNESS_REFS_DIR = REPO_ROOT / ".claude" / "references"
PROJECT_REFS_DIR = REPO_ROOT / "product-design"
AGENTS_DIR = CLAUDE_DIR / "agents"

ALLOWED_CATEGORIES = {"planning", "analysis", "code", "utility", "internal"}
ALLOWED_BOOLEAN_FIELDS = {"disable-model-invocation"}
ALLOWED_CONTEXT_BUDGETS = {"light", "standard", "heavy"}

# Harness-only detection: no project configured if conventions.md is absent
_PROJECT_CONVENTIONS = PROJECT_REFS_DIR / "conventions.md"
IS_HARNESS_ONLY = not _PROJECT_CONVENTIONS.exists()
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")

# Simple YAML frontmatter parser (between --- delimiters)
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


def parse_frontmatter(text: str) -> dict:
    """Parse YAML-like frontmatter from a markdown file.

    This is a lightweight parser that handles the subset of YAML
    used in SKILL.md and agent definition files: scalar key-value pairs,
    nested mappings (one level), and lists (with - prefix).
    """
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}

    result = {}
    current_key = None
    current_list = None
    in_metadata = False
    metadata = {}

    for line in match.group(1).split("\n"):
        stripped = line.strip()
        if not stripped:
            continue

        # Top-level key: value
        if not line.startswith(" ") and not line.startswith("\t"):
            if current_list is not None and current_key:
                if in_metadata:
                    metadata[current_key] = current_list
                else:
                    result[current_key] = current_list
                current_list = None
            in_metadata = False

            if ":" in stripped:
                key, _, value = stripped.partition(":")
                key = key.strip()
                value = value.strip().strip("\"'")
                if key == "metadata":
                    in_metadata = True
                    current_key = None
                else:
                    result[key] = value if value else ""
                    current_key = key
            continue

        # Indented content (inside metadata or a list)
        if in_metadata:
            if stripped.startswith("- "):
                if current_list is None:
                    current_list = []
                current_list.append(stripped[2:].strip())
            elif ":" in stripped:
                if current_list is not None and current_key:
                    metadata[current_key] = current_list
                    current_list = None
                key, _, value = stripped.partition(":")
                key = key.strip()
                value = value.strip().strip("\"'")
                current_key = key
                if value:
                    # Handle inline empty list notation: key: []
                    if value == "[]":
                        metadata[key] = []
                    else:
                        metadata[key] = value
        elif stripped.startswith("- "):
            if current_list is None:
                current_list = []
            current_list.append(stripped[2:].strip())

    # Flush remaining list
    if current_list is not None and current_key:
        if in_metadata:
            metadata[current_key] = current_list
        else:
            result[current_key] = current_list

    if metadata:
        result["metadata"] = metadata

    return result


def detect_cycles(dep_graph: dict[str, list[str]]) -> list[list[str]]:
    """Detect cycles in a dependency graph using DFS. Returns list of cycles found."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {node: WHITE for node in dep_graph}
    cycles = []
    path = []

    def dfs(node: str):
        color[node] = GRAY
        path.append(node)

        for neighbor in dep_graph.get(node, []):
            if neighbor not in color:
                continue
            if color[neighbor] == GRAY:
                # Found a cycle — extract it from path
                cycle_start = path.index(neighbor)
                cycles.append(path[cycle_start:] + [neighbor])
            elif color[neighbor] == WHITE:
                dfs(neighbor)

        path.pop()
        color[node] = BLACK

    for node in dep_graph:
        if color[node] == WHITE:
            dfs(node)

    return cycles


def check_skills(verbose: bool = False) -> tuple[list[str], list[str], list[str]]:
    """Check all SKILL.md files. Returns (errors, warnings, infos)."""
    errors = []
    warnings = []
    all_infos: list[str] = []
    skill_names = set()
    dep_graph: dict[str, list[str]] = {}

    skill_dirs = sorted(
        d for d in SKILLS_DIR.iterdir()
        if d.is_dir() and (d / "SKILL.md").exists()
    )

    print(f"## Skills ({len(skill_dirs)} found)\n")

    for skill_dir in skill_dirs:
        skill_file = skill_dir / "SKILL.md"
        text = skill_file.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        name = skill_dir.name

        # Check required fields
        if not fm.get("name"):
            errors.append(f"  - {name}/SKILL.md: missing 'name' field in frontmatter")
        else:
            skill_names.add(fm["name"])

        if not fm.get("description"):
            errors.append(f"  - {name}/SKILL.md: missing 'description' field in frontmatter")

        # Check metadata
        metadata = fm.get("metadata", {})

        # Check metadata.references — empty list [] is valid
        # Files live in general/, template/ (under HARNESS_REFS_DIR) or
        # project/ entries (under PROJECT_REFS_DIR after stripping the "project/" prefix).
        refs = metadata.get("references", [])
        infos = []
        if isinstance(refs, list):
            for ref in refs:
                if ref.startswith("project/"):
                    ref_path = PROJECT_REFS_DIR / ref.removeprefix("project/")
                else:
                    ref_path = HARNESS_REFS_DIR / ref
                if not ref_path.exists():
                    if IS_HARNESS_ONLY and ref.startswith("project/"):
                        infos.append(
                            f"  - {name}/SKILL.md: project/* reference not found "
                            f"(expected -- no project configured): '{ref}'"
                        )
                    else:
                        errors.append(
                            f"  - {name}/SKILL.md: references non-existent file '{ref}'"
                        )
        elif refs:
            warnings.append(
                f"  - {name}/SKILL.md: 'references' should be a list, got: {type(refs).__name__}"
            )

        # Check metadata.eager_references — optional demand-pull field
        eager_refs = metadata.get("eager_references")
        if eager_refs is not None:
            if not isinstance(eager_refs, list):
                errors.append(
                    f"  - {name}/SKILL.md: 'eager_references' should be a list, "
                    f"got: {type(eager_refs).__name__}"
                )
            else:
                # Paths must exist (general/template via HARNESS_REFS_DIR; project/ via PROJECT_REFS_DIR)
                for eref in eager_refs:
                    if eref.startswith("project/"):
                        eref_path = PROJECT_REFS_DIR / eref.removeprefix("project/")
                    else:
                        eref_path = HARNESS_REFS_DIR / eref
                    if not eref_path.exists():
                        if IS_HARNESS_ONLY and eref.startswith("project/"):
                            infos.append(
                                f"  - {name}/SKILL.md: project/* eager_reference not found "
                                f"(expected -- no project configured): '{eref}'"
                            )
                        else:
                            errors.append(
                                f"  - {name}/SKILL.md: eager_references non-existent file '{eref}'"
                            )
                # No duplicates within eager_references
                seen = set()
                for eref in eager_refs:
                    if eref in seen:
                        errors.append(
                            f"  - {name}/SKILL.md: duplicate in eager_references: '{eref}'"
                        )
                    seen.add(eref)
                # Every eager ref must also be in references
                if isinstance(refs, list):
                    refs_set = set(refs)
                    for eref in eager_refs:
                        if eref not in refs_set:
                            errors.append(
                                f"  - {name}/SKILL.md: eager_references entry '{eref}' "
                                f"not found in references list"
                            )
                # Warn if too many eager refs
                if len(eager_refs) > 6:
                    warnings.append(
                        f"  - {name}/SKILL.md: eager_references has {len(eager_refs)} entries "
                        f"(recommended: <=6 to keep context budget lean)"
                    )

        # Collect info messages from this skill
        all_infos.extend(infos)

        # Check category field
        category = metadata.get("category")
        if not category:
            warnings.append(f"  - {name}/SKILL.md: missing 'category' field in metadata")
        elif category not in ALLOWED_CATEGORIES:
            errors.append(
                f"  - {name}/SKILL.md: invalid category '{category}' "
                f"(allowed: {', '.join(sorted(ALLOWED_CATEGORIES))})"
            )

        # Check context_budget field
        context_budget = metadata.get("context_budget")
        if context_budget is None:
            warnings.append(
                f"  - {name}/SKILL.md: missing 'context_budget' field "
                f"(expected one of: {', '.join(sorted(ALLOWED_CONTEXT_BUDGETS))}; defaulting to 'standard')"
            )
        elif context_budget not in ALLOWED_CONTEXT_BUDGETS:
            errors.append(
                f"  - {name}/SKILL.md: invalid context_budget '{context_budget}' "
                f"(allowed: {', '.join(sorted(ALLOWED_CONTEXT_BUDGETS))})"
            )

        # Version field validation
        version = metadata.get("version")
        if version is not None:
            if not VERSION_RE.match(str(version)):
                warnings.append(
                    f"  - {name}\\SKILL.md: invalid version format '{version}' "
                    f"(expected semver: X.Y.Z)"
                )
        else:
            warnings.append(
                f"  - {name}\\SKILL.md: missing metadata.version field"
            )

        # Build dependency graph
        depends = metadata.get("depends", [])
        if isinstance(depends, list):
            dep_graph[fm.get("name", name)] = depends

        if verbose and not any(name in e for e in errors + warnings):
            print(f"  OK: {name}")

    # Second pass: check depends references
    for skill_dir in skill_dirs:
        skill_file = skill_dir / "SKILL.md"
        text = skill_file.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        name = skill_dir.name
        metadata = fm.get("metadata", {})
        depends = metadata.get("depends", [])
        if isinstance(depends, list):
            for dep in depends:
                if dep not in skill_names:
                    errors.append(
                        f"  - {name}/SKILL.md: depends on unknown skill '{dep}'"
                    )

    # Cycle detection
    cycles = detect_cycles(dep_graph)
    if cycles:
        for cycle in cycles:
            cycle_str = " -> ".join(cycle)
            errors.append(f"  - Dependency cycle detected: {cycle_str}")

    return errors, warnings, all_infos


def check_agents(verbose: bool = False) -> tuple[list[str], list[str]]:
    """Check all agent definition files. Returns (errors, warnings)."""
    errors = []
    warnings = []

    if not AGENTS_DIR.is_dir():
        warnings.append("  - Agents directory not found")
        return errors, warnings

    agent_files = sorted(AGENTS_DIR.glob("*.md"))
    print(f"## Agents ({len(agent_files)} found)\n")

    for agent_file in agent_files:
        text = agent_file.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        name = agent_file.stem

        if not fm.get("name"):
            errors.append(f"  - {name}.md: missing 'name' field in frontmatter")

        if not fm.get("description"):
            errors.append(f"  - {name}.md: missing 'description' field in frontmatter")

        if not fm.get("tools"):
            warnings.append(f"  - {name}.md: missing 'tools' field in frontmatter")

        if verbose and not any(name in e for e in errors + warnings):
            print(f"  OK: {name}")

    return errors, warnings


def check_references(verbose: bool = False) -> tuple[list[str], list[str]]:
    """Check reference file structure. Returns (errors, warnings)."""
    errors = []
    warnings = []

    harness_refs_found = 0
    project_refs_found = 0

    if HARNESS_REFS_DIR.is_dir():
        harness_ref_files = sorted(HARNESS_REFS_DIR.glob("**/*.md"))
        harness_refs_found = len(harness_ref_files)
        valid_subdirs = {"general", "template"}
        for ref_file in harness_ref_files:
            rel = ref_file.relative_to(HARNESS_REFS_DIR)
            if rel.parts[0] not in valid_subdirs:
                warnings.append(
                    f"  - {rel}: not in expected subdirectory "
                    f"(expected general/ or template/)"
                )
            if verbose:
                print(f"  OK: .claude/references/{rel}")
    else:
        errors.append("  - .claude/references/ directory not found")

    if PROJECT_REFS_DIR.is_dir():
        project_ref_files = sorted(PROJECT_REFS_DIR.glob("**/*.md"))
        project_refs_found = len(project_ref_files)
        if verbose:
            for ref_file in project_ref_files:
                rel = ref_file.relative_to(PROJECT_REFS_DIR)
                print(f"  OK: product-design/{rel}")

    total = harness_refs_found + project_refs_found
    print(f"## References ({harness_refs_found} harness, {project_refs_found} project, {total} total)\n")

    return errors, warnings


def run_self_test() -> bool:
    """Run built-in tests for cycle detection. Returns True if all pass."""
    print("Running self-test...\n")
    passed = True

    # Test 1: Acyclic graph — should find no cycles
    acyclic = {"a": ["b", "c"], "b": ["c"], "c": [], "d": ["a"]}
    cycles = detect_cycles(acyclic)
    if not cycles:
        print("  PASS: Acyclic graph correctly detected as cycle-free")
    else:
        print(f"  FAIL: Acyclic graph reported cycles: {cycles}")
        passed = False

    # Test 2: Simple cycle — a -> b -> a
    cyclic_simple = {"a": ["b"], "b": ["a"]}
    cycles = detect_cycles(cyclic_simple)
    if cycles:
        print(f"  PASS: Simple cycle detected: {' -> '.join(cycles[0])}")
    else:
        print("  FAIL: Simple cycle (a -> b -> a) was not detected")
        passed = False

    # Test 3: Longer cycle — a -> b -> c -> a
    cyclic_long = {"a": ["b"], "b": ["c"], "c": ["a"]}
    cycles = detect_cycles(cyclic_long)
    if cycles:
        print(f"  PASS: Longer cycle detected: {' -> '.join(cycles[0])}")
    else:
        print("  FAIL: Longer cycle (a -> b -> c -> a) was not detected")
        passed = False

    # Test 4: Self-loop — a -> a
    self_loop = {"a": ["a"]}
    cycles = detect_cycles(self_loop)
    if cycles:
        print(f"  PASS: Self-loop detected: {' -> '.join(cycles[0])}")
    else:
        print("  FAIL: Self-loop (a -> a) was not detected")
        passed = False

    # Test 5: Disconnected graph with one cycle
    mixed = {"a": ["b"], "b": [], "c": ["d"], "d": ["c"]}
    cycles = detect_cycles(mixed)
    if cycles:
        print(f"  PASS: Cycle in disconnected component detected: {' -> '.join(cycles[0])}")
    else:
        print("  FAIL: Cycle in disconnected component was not detected")
        passed = False

    print()
    if passed:
        print("Self-test PASSED: all cycle detection fixtures validated correctly.")
    else:
        print("Self-test FAILED: see above for details.")

    return passed


def check_script_imports(verbose: bool = False) -> tuple[list[str], list[str], list[str]]:
    """Try to import every .py script in the scripts/ directory.

    Returns (errors, warnings, infos).
    Only SyntaxError counts as an error. ImportError for missing external
    packages counts as a warning. All other exceptions (FileNotFoundError,
    SystemExit, RuntimeError, etc.) count as info -- these are expected in
    harness-only repos where project_config cannot find conventions.md.
    """
    errors: list[str] = []
    warnings: list[str] = []
    infos: list[str] = []

    scripts_dir = Path(__file__).resolve().parent
    # Discover all .py files, excluding helpers/test directories
    py_files = sorted(
        f for f in scripts_dir.iterdir()
        if f.suffix == ".py"
        and f.name != "__init__.py"
        and "__pycache__" not in f.parts
        and "tests" not in f.parts
    )

    total = len(py_files)
    successful = 0
    warn_count = 0
    error_count = 0

    print(f"## Script Imports ({total} scripts found)\n")

    for py_file in py_files:
        mod_name = f"_check_import_{py_file.stem}"
        try:
            spec = importlib.util.spec_from_file_location(mod_name, py_file)
            if spec is None or spec.loader is None:
                infos.append(f"  - {py_file.name}: could not create import spec")
                continue
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            successful += 1
            if verbose:
                print(f"  OK: {py_file.name}")
        except SyntaxError as exc:
            error_count += 1
            errors.append(
                f"  - {py_file.name}: SyntaxError: {exc.msg} (line {exc.lineno})"
            )
        except ImportError as exc:
            # Check if the missing module is a local script (sibling .py file)
            missing = exc.name or ""
            local_candidate = scripts_dir / f"{missing}.py"
            if local_candidate.exists():
                # Local cross-import issue — treat as info, not warning
                infos.append(
                    f"  - {py_file.name}: ImportError (local): {exc}"
                )
            else:
                warn_count += 1
                warnings.append(
                    f"  - {py_file.name}: ImportError (missing package): {exc}"
                )
        except Exception as exc:  # noqa: BLE001
            infos.append(
                f"  - {py_file.name}: {type(exc).__name__}: {exc}"
            )

    info_count = len(infos)
    print(
        f"  Script imports: {total} total, {successful} successful, "
        f"{warn_count} warnings, {error_count} errors"
    )
    if info_count:
        print(f"  ({info_count} info-level exceptions — expected in harness-only repos)")
    print()

    return errors, warnings, infos


def main():
    parser = argparse.ArgumentParser(
        description="Validate .claude skill system integrity"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show details for passing checks too"
    )
    parser.add_argument(
        "--self-test", action="store_true",
        help="Run built-in cycle detection tests"
    )
    args = parser.parse_args()

    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if args.self_test:
        success = run_self_test()
        sys.exit(0 if success else 1)

    print("# Skill System Integrity Check\n")

    if not CLAUDE_DIR.is_dir():
        print("ERROR: .claude directory not found")
        sys.exit(2)

    all_errors = []
    all_warnings = []
    all_infos: list[str] = []

    # Check skills (includes cycle detection)
    errs, warns, infos = check_skills(verbose=args.verbose)
    all_errors.extend(errs)
    all_warnings.extend(warns)
    all_infos.extend(infos)

    # Check agents
    errs, warns = check_agents(verbose=args.verbose)
    all_errors.extend(errs)
    all_warnings.extend(warns)

    # Check references
    errs, warns = check_references(verbose=args.verbose)
    all_errors.extend(errs)
    all_warnings.extend(warns)

    # Check script imports
    errs, warns, infos = check_script_imports(verbose=args.verbose)
    all_errors.extend(errs)
    all_warnings.extend(warns)
    all_infos.extend(infos)

    # Report
    print()
    if all_errors:
        print(f"## Errors ({len(all_errors)})\n")
        for msg in all_errors:
            print(msg)
        print()

    if all_warnings:
        print(f"## Warnings ({len(all_warnings)})\n")
        for msg in all_warnings:
            print(msg)
        print()

    if all_infos:
        print(f"## Info ({len(all_infos)})\n")
        for msg in all_infos:
            print(msg)
        print()

    if not all_errors and not all_warnings:
        print("PASS: Skill system integrity check passed")
    elif all_errors:
        print(f"FAIL: {len(all_errors)} error(s), {len(all_warnings)} warning(s)")
        sys.exit(1)
    else:
        print(f"WARN: {len(all_warnings)} warning(s), 0 errors")


if __name__ == "__main__":
    main()
