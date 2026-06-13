#!/usr/bin/env python3
# designer: When you are about to land generated or hand-written code, I
#   scan it for the vulnerability shapes the harness's threat model
#   tracks -- things like shell injection, unsafe deserialisation,
#   hardcoded crypto, path traversal -- and return a list of hits with
#   enough context to decide whether each one is a real problem or an
#   intentional exception.
"""
check_vuln_patterns.py — Scan files for generated code vulnerability patterns.

Invocation: agent-invoked, hook-ci
Lifecycle: active

Exit codes: 0 = no findings, 1 = findings found, 2 = script error.

Checks for dangerous code patterns enumerated in the SEJA threat model
(Generated Code Vulnerability Patterns section). Supports scanning
directories, specific files, or unified diffs from stdin.

Usage
-----
    python .claude/skills/scripts/check_vuln_patterns.py --path src/
    python .claude/skills/scripts/check_vuln_patterns.py --files app.py routes.js
    git diff | python .claude/skills/scripts/check_vuln_patterns.py --diff
    python .claude/skills/scripts/check_vuln_patterns.py --path . --json

Run from the repository root.
Optional flags:
    --path <dir>       Scan all files in directory recursively (default: .)
    --files <paths>    Scan specific files
    --diff             Read unified diff from stdin and scan it
    --json             Output findings as JSON array

CHECK_PLUGIN_MANIFEST:
  name: Vulnerability Pattern Scanner
  stack:
    backend: [any]
    frontend: [any]
  scope: security
  critical: true
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import NamedTuple

try:
    from project_config import REPO_ROOT as _REPO_ROOT
except ImportError:
    _REPO_ROOT = None

REPO_ROOT = _REPO_ROOT or Path(__file__).resolve().parents[3]

# Directories to skip during recursive scanning
SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "venv"}

# Harness skill scripts contain vulnerability pattern definitions as string
# literals (this file, md_to_html.py, etc.) -- not actual vulnerable code.
# Skip any .claude/skills/scripts/ directory to prevent false positives.

# Binary / non-text extensions to skip
BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".bmp", ".svg",
    ".woff", ".woff2", ".ttf", ".eot",
    ".pyc", ".pyo", ".so", ".dll", ".exe",
    ".zip", ".tar", ".gz", ".bz2", ".7z",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".lock", ".map",
}


# ---------------------------------------------------------------------------
# Pattern definitions
# ---------------------------------------------------------------------------

class VulnPattern(NamedTuple):
    name: str
    category: str
    dangerous_substrings: list[str]
    file_extensions: list[str]
    severity: str  # HIGH or MEDIUM
    safe_alternative: str



VULN_PATTERNS: list[VulnPattern] = [
    # -- Injection ----------------------------------------------------------
    VulnPattern(
        name="child_process_exec",
        category="Injection",
        dangerous_substrings=["child_process.exec", "exec(", "execSync("],
        file_extensions=[".js", ".ts", ".tsx", ".jsx"],
        severity="HIGH",
        safe_alternative=(
            "Use execFile() or execFileSync() -- prevents shell injection by not invoking a shell"
        ),
    ),
    VulnPattern(
        name="eval_injection",
        category="Injection",
        dangerous_substrings=["eval("],
        file_extensions=[".js", ".ts", ".tsx", ".jsx"],
        severity="HIGH",
        safe_alternative=(
            "Use JSON.parse() for data, or alternative design patterns"
        ),
    ),
    VulnPattern(
        name="new_function_injection",
        category="Injection",
        dangerous_substrings=["new Function"],
        file_extensions=[".js", ".ts", ".tsx", ".jsx"],
        severity="HIGH",
        safe_alternative=(
            "Avoid dynamic code evaluation; use static alternatives"
        ),
    ),
    VulnPattern(
        name="os_system_injection",
        category="Injection",
        dangerous_substrings=["os.system", "from os import system"],
        file_extensions=[".py"],
        severity="HIGH",
        safe_alternative=(
            "Use subprocess.run() with a list of arguments (no shell=True)"
        ),
    ),
    VulnPattern(
        name="subprocess_shell",
        category="Injection",
        dangerous_substrings=["shell=True"],
        file_extensions=[".py"],
        severity="HIGH",
        safe_alternative=(
            "Use subprocess.run([cmd, arg1, arg2]) with argument list, never shell=True with user input"
        ),
    ),
    VulnPattern(
        name="sql_string_concat",
        category="Injection",
        dangerous_substrings=[
            'execute(f"', "execute(f\'",
            'execute("SELECT', "execute(\'SELECT",
            'execute("INSERT', "execute(\'INSERT",
            'execute("UPDATE', "execute(\'UPDATE",
            'execute("DELETE', "execute(\'DELETE",
        ],
        file_extensions=[".py", ".js", ".ts", ".tsx", ".jsx", ".java"],
        severity="HIGH",
        safe_alternative=(
            "Use parameterized queries / prepared statements"
        ),
    ),
    VulnPattern(
        name="github_actions_workflow",
        category="Injection",
        dangerous_substrings=[
            "${{ github.event.issue.title }}",
            "${{ github.event.pull_request.body }}",
            "${{ github.event.pull_request.title }}",
            "${{ github.event.comment.body }}",
            "${{ github.event.review.body }}",
            "${{ github.event.pages.",
            "${{ github.event.commits",
            "${{ github.event.head_commit.message }}",
        ],
        file_extensions=[".yml", ".yaml"],
        severity="HIGH",
        safe_alternative=(
            "Use env: block with environment variables instead of direct interpolation in run: blocks"
        ),
    ),
    # -- Cross-Site Scripting (XSS) ----------------------------------------
    VulnPattern(
        name="react_dangerously_set_html",
        category="XSS",
        dangerous_substrings=["dangerouslySetInnerHTML"],
        file_extensions=[".js", ".ts", ".tsx", ".jsx"],
        severity="HIGH",
        safe_alternative=(
            "Sanitize with DOMPurify, or use safe React components"
        ),
    ),
    VulnPattern(
        name="document_write_xss",
        category="XSS",
        dangerous_substrings=["document.write"],
        file_extensions=[".js", ".ts", ".tsx", ".jsx"],
        severity="MEDIUM",
        safe_alternative=(
            "Use createElement() and appendChild()"
        ),
    ),
    VulnPattern(
        name="innerHTML_xss",
        category="XSS",
        dangerous_substrings=[".innerHTML =", ".innerHTML="],
        file_extensions=[".js", ".ts", ".tsx", ".jsx"],
        severity="HIGH",
        safe_alternative=(
            "Use textContent for plain text, or sanitize HTML with DOMPurify"
        ),
    ),
    VulnPattern(
        name="jinja2_autoescape_off",
        category="XSS",
        dangerous_substrings=["autoescape=False", "Markup("],
        file_extensions=[".py"],
        severity="HIGH",
        safe_alternative=(
            "Keep autoescape=True (Flask default); use |safe filter only on trusted content"
        ),
    ),
    # -- Deserialization ----------------------------------------------------
    VulnPattern(
        name="pickle_deserialization",
        category="Deserialization",
        dangerous_substrings=["pickle.load", "pickle.loads", "import pickle"],
        file_extensions=[".py"],
        severity="HIGH",
        safe_alternative=(
            "Use json or other safe serialization formats for untrusted data"
        ),
    ),
    VulnPattern(
        name="yaml_unsafe_load",
        category="Deserialization",
        dangerous_substrings=["yaml.load("],
        file_extensions=[".py"],
        severity="HIGH",
        safe_alternative=(
            "Use yaml.safe_load() or yaml.load(data, Loader=SafeLoader)"
        ),
    ),
    VulnPattern(
        name="java_deserialization",
        category="Deserialization",
        dangerous_substrings=["ObjectInputStream", "readObject()"],
        file_extensions=[".java"],
        severity="HIGH",
        safe_alternative=(
            "Use JSON/protobuf; if Java serialization is required, use serialization filters"
        ),
    ),
    # -- Template Injection -------------------------------------------------
    VulnPattern(
        name="ssti",
        category="Template Injection",
        dangerous_substrings=["render_template_string(", "Template("],
        file_extensions=[".py", ".js", ".ts", ".tsx", ".jsx"],
        severity="HIGH",
        safe_alternative=(
            "Never pass user input as the template itself; use template variables instead"
        ),
    ),
]

# Pre-compile a regex for yaml.safe_load to suppress false positives
_YAML_SAFE_LOAD_RE = re.compile(r"yaml\.safe_load\s*\(")


# ---------------------------------------------------------------------------
# Scanning helpers
# ---------------------------------------------------------------------------

def _is_binary_ext(filepath: Path) -> bool:
    """Return True if the file extension suggests a binary file."""
    return filepath.suffix.lower() in BINARY_EXTENSIONS


def _in_skip_dir(filepath: Path) -> bool:
    """Return True if any path component is a directory we should skip."""
    if any(part in SKIP_DIRS for part in filepath.parts):
        return True
    # Skip harness skill scripts (contain pattern definitions, not app code)
    path_str = str(filepath).replace("\\", "/")
    return ".claude/skills/scripts" in path_str


def _matches_extension(pattern: VulnPattern, filepath: Path) -> bool:
    """Return True if the file extension matches the pattern scope."""
    return filepath.suffix.lower() in pattern.file_extensions


def _requires_workflow_path(pattern: VulnPattern, filepath_str: str) -> bool:
    """Return True if the pattern needs .github/workflows/ and path does not match."""
    if pattern.name == "github_actions_workflow":
        normalised = filepath_str.replace("\\", "/")
        return ".github/workflows/" not in normalised
    return False


Finding = tuple[str, str, str, int, str, str]
# (severity, pattern_name, filepath_str, line_num, safe_alternative, line_text)


def scan_line(
    line: str,
    line_num: int,
    filepath_str: str,
    filepath: Path,
    applicable_patterns: list[VulnPattern],
) -> list[Finding]:
    """Check a single line against applicable patterns."""
    findings: list[Finding] = []
    for pat in applicable_patterns:
        if _requires_workflow_path(pat, filepath_str):
            continue
        for substr in pat.dangerous_substrings:
            if substr in line:
                # Special case: yaml.load( should not flag yaml.safe_load(
                if pat.name == "yaml_unsafe_load" and _YAML_SAFE_LOAD_RE.search(line):
                    continue
                findings.append((
                    pat.severity,
                    pat.name,
                    filepath_str,
                    line_num,
                    pat.safe_alternative,
                    line.strip()[:120],
                ))
                break  # one match per pattern per line is enough
    return findings


def scan_file(filepath: Path, rel_to: Path | None = None) -> list[Finding]:
    """Scan a single file for vulnerability patterns."""
    if _is_binary_ext(filepath) or _in_skip_dir(filepath):
        return []

    # Determine which patterns apply based on extension
    applicable = [p for p in VULN_PATTERNS if _matches_extension(p, filepath)]
    if not applicable:
        return []

    try:
        text = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    filepath_str = str(filepath.relative_to(rel_to)) if rel_to else str(filepath)

    findings: list[Finding] = []
    for line_num, line in enumerate(text.split("\n"), start=1):
        findings.extend(scan_line(line, line_num, filepath_str, filepath, applicable))
    return findings


def scan_directory(dirpath: Path) -> list[Finding]:
    """Recursively scan a directory for vulnerability patterns."""
    findings: list[Finding] = []
    try:
        for child in sorted(dirpath.rglob("*")):
            if child.is_file():
                findings.extend(scan_file(child, rel_to=dirpath))
    except OSError as exc:
        print(f"WARNING: error scanning directory {dirpath}: {exc}", file=sys.stderr)
    return findings


def scan_diff(diff_text: str) -> list[Finding]:
    """Scan a unified diff for vulnerability patterns.

    Extracts filenames from diff headers (+++ b/...) and checks only added
    lines (starting with +, but not +++).
    """
    findings: list[Finding] = []
    current_file: str | None = None
    current_path: Path | None = None
    applicable: list[VulnPattern] = []
    line_num = 0
    hunk_re = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")

    for raw_line in diff_text.split("\n"):
        # Detect file header
        if raw_line.startswith("+++ b/"):
            current_file = raw_line[6:]
            current_path = Path(current_file)
            applicable = [p for p in VULN_PATTERNS if _matches_extension(p, current_path)]
            line_num = 0
            continue
        if raw_line.startswith("--- "):
            continue

        # Track line numbers from hunk headers
        m = hunk_re.match(raw_line)
        if m:
            line_num = int(m.group(1)) - 1  # will be incremented on first +
            continue

        if current_file is None or not applicable:
            continue

        # Only scan added lines
        if raw_line.startswith("+"):
            line_num += 1
            content = raw_line[1:]  # strip leading +
            findings.extend(
                scan_line(content, line_num, current_file, current_path, applicable)
            )
        elif not raw_line.startswith("-"):
            line_num += 1  # context line

    return findings


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def format_text(findings: list[Finding]) -> str:
    """Format findings as human-readable text lines."""
    lines = []
    for severity, name, fpath, line_num, alt, _line_text in findings:
        lines.append(f"[{severity}] {name}: {fpath}:{line_num} -- {alt}")
    return "\n".join(lines)


def format_json(findings: list[Finding]) -> str:
    """Format findings as a JSON array."""
    records = []
    for severity, name, fpath, line_num, alt, line_text in findings:
        records.append({
            "severity": severity,
            "pattern": name,
            "file": fpath,
            "line": line_num,
            "safe_alternative": alt,
            "match_text": line_text,
        })
    return json.dumps(records, indent=2)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan files for generated code vulnerability patterns"
    )
    parser.add_argument(
        "--path", type=str, default=None,
        help="Scan all files in directory recursively (default: current directory)",
    )
    parser.add_argument(
        "--files", nargs="+", type=str, default=None,
        help="Scan specific files",
    )
    parser.add_argument(
        "--diff", action="store_true",
        help="Read a unified diff from stdin and scan it",
    )
    parser.add_argument(
        "--json", dest="json_output", action="store_true",
        help="Output findings as JSON array",
    )
    args = parser.parse_args()

    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    findings: list[Finding] = []

    try:
        if args.diff:
            diff_text = sys.stdin.read()
            findings = scan_diff(diff_text)
        elif args.files:
            for fpath_str in args.files:
                fpath = Path(fpath_str).resolve()
                if fpath.is_file():
                    findings.extend(scan_file(fpath))
                else:
                    print(f"WARNING: file not found: {fpath_str}", file=sys.stderr)
        else:
            scan_root = Path(args.path).resolve() if args.path else Path.cwd()
            if not scan_root.is_dir():
                print(f"ERROR: not a directory: {scan_root}", file=sys.stderr)
                sys.exit(2)
            findings = scan_directory(scan_root)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)

    if args.json_output:
        print(format_json(findings))
    else:
        if findings:
            print(format_text(findings))
        else:
            print("No vulnerability patterns found.")

    sys.exit(1 if findings else 0)


if __name__ == "__main__":
    main()

