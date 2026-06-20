#!/usr/bin/env python3
# designer: When you want to know whether a target workspace's harness files
#   have drifted from the canonical source -- new files missing, stale files
#   lingering, or content diverged -- I compare the two trees, report the
#   delta, and optionally generate an editable remediation plan so you can
#   review before applying destructive changes.
"""
check_harness_drift.py -- Compare a canonical harness source against a target
workspace, report drift, and generate / apply remediation plans.

Invocation: skill-invoked, user-cli
Lifecycle: active

Usage:
    # Detect drift (text summary)
    python check_harness_drift.py --source <path> [--target <path>] [--json] [--plan-output <path>]

    # Apply a remediation plan
    python check_harness_drift.py --apply <plan-path> --source <path> [--target <path>]

Exit codes: 0 = no drift, 1 = drift found, 2 = error.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from upgrade_harness import collect_source_files, is_preserved

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class DriftEntry:
    """A single file-level drift observation."""
    rel_path: str
    kind: str  # "add", "remove", "revise"
    source_hash: str | None = None
    target_hash: str | None = None
    diff_summary: str | None = None


@dataclass
class DriftReport:
    """Aggregated drift between source and target harness trees."""
    source: str
    target: str
    add: list[DriftEntry] = field(default_factory=list)
    remove: list[DriftEntry] = field(default_factory=list)
    revise: list[DriftEntry] = field(default_factory=list)

    @property
    def has_drift(self) -> bool:
        return bool(self.add or self.remove or self.revise)

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "target": self.target,
            "add": [e.rel_path for e in self.add],
            "remove": [e.rel_path for e in self.remove],
            "revise": [{"path": e.rel_path, "diff_summary": e.diff_summary} for e in self.revise],
        }


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def _sha256(path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _diff_summary(source_file: Path, target_file: Path, max_lines: int = 20) -> str:
    """Generate a truncated unified diff summary between two files."""
    try:
        source_lines = source_file.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
        target_lines = target_file.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    except OSError:
        return "(unable to read files for diff)"

    diff = list(difflib.unified_diff(
        target_lines, source_lines,
        fromfile="target", tofile="source",
        lineterm="",
    ))
    if not diff:
        return "(no text differences)"

    lines = [line.rstrip("\n") for line in diff[:max_lines]]
    if len(diff) > max_lines:
        lines.append(f"... ({len(diff) - max_lines} more lines)")
    return "\n".join(lines)


def compute_drift(source: Path, target: Path) -> DriftReport:
    """Compare source and target harness trees and classify the delta.

    Exported for programmatic use by other scripts.
    """
    source = source.resolve()
    target = target.resolve()

    source_files = collect_source_files(source)
    target_files = collect_source_files(target)

    source_rels = {f.relative_to(source).as_posix(): f for f in source_files}
    target_rels = {f.relative_to(target).as_posix(): f for f in target_files}

    report = DriftReport(source=str(source), target=str(target))

    # ADD: in source but not target (excluding preserved paths)
    for rel in sorted(source_rels.keys() - target_rels.keys()):
        if not is_preserved(rel):
            report.add.append(DriftEntry(
                rel_path=rel,
                kind="add",
                source_hash=_sha256(source_rels[rel]),
            ))

    # REMOVE: in target but not source (excluding preserved paths)
    for rel in sorted(target_rels.keys() - source_rels.keys()):
        if not is_preserved(rel):
            report.remove.append(DriftEntry(
                rel_path=rel,
                kind="remove",
                target_hash=_sha256(target_rels[rel]),
            ))

    # REVISE: in both but with different content hashes
    for rel in sorted(source_rels.keys() & target_rels.keys()):
        src_hash = _sha256(source_rels[rel])
        tgt_hash = _sha256(target_rels[rel])
        if src_hash != tgt_hash:
            report.revise.append(DriftEntry(
                rel_path=rel,
                kind="revise",
                source_hash=src_hash,
                target_hash=tgt_hash,
                diff_summary=_diff_summary(source_rels[rel], target_rels[rel]),
            ))

    return report


# ---------------------------------------------------------------------------
# Plan generation
# ---------------------------------------------------------------------------


def _write_plan(report: DriftReport, plan_path: Path) -> None:
    """Write a markdown remediation plan from a DriftReport."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines: list[str] = [
        "# Drift Remediation Plan",
        f"Source: {report.source}",
        f"Target: {report.target}",
        f"Generated: {now}",
        "",
        "## Files to Add (informational -- no review needed)",
    ]
    if report.add:
        for entry in report.add:
            lines.append(f"- {entry.rel_path}")
    else:
        lines.append("(none)")
    lines.append("")

    lines.append("## Files to Remove")
    lines.append("Delete these files from the target. Remove an entry to exclude it.")
    if report.remove:
        for entry in report.remove:
            lines.append(f"- [ ] {entry.rel_path}")
    else:
        lines.append("(none)")
    lines.append("")

    lines.append("## Files to Revise")
    lines.append("Overwrite these target files with the source version. Remove an entry to exclude it.")
    if report.revise:
        for entry in report.revise:
            lines.append(f"- [ ] {entry.rel_path}")
            diff_text = entry.diff_summary or "(no diff available)"
            diff_lines = diff_text.splitlines()
            if diff_lines:
                lines.append(f"  Changes: {diff_lines[0]}")
                for dl in diff_lines[1:]:
                    lines.append(f"  {dl}")
            else:
                lines.append(f"  Changes: {diff_text}")
    else:
        lines.append("(none)")

    lines.append("")
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Plan parsing
# ---------------------------------------------------------------------------

_CHECKLIST_RE = re.compile(r"^- \[[ x]\] (.+)$")
_LIST_ITEM_RE = re.compile(r"^- (.+)$")


def _parse_plan(plan_path: Path) -> dict[str, list[str]]:
    """Parse a remediation plan file into categorized path lists.

    Returns dict with keys "add", "remove", "revise".
    Only entries still present in the file are included.
    """
    text = plan_path.read_text(encoding="utf-8")
    sections: dict[str, list[str]] = {"add": [], "remove": [], "revise": []}
    current_section: str | None = None

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## Files to Add"):
            current_section = "add"
            continue
        elif stripped.startswith("## Files to Remove"):
            current_section = "remove"
            continue
        elif stripped.startswith("## Files to Revise"):
            current_section = "revise"
            continue
        elif stripped.startswith("## "):
            current_section = None
            continue

        if current_section == "add":
            m = _LIST_ITEM_RE.match(stripped)
            if m:
                sections["add"].append(m.group(1).strip())
        elif current_section in ("remove", "revise"):
            m = _CHECKLIST_RE.match(stripped)
            if m:
                sections[current_section].append(m.group(1).strip())

    return sections


# ---------------------------------------------------------------------------
# Detect mode
# ---------------------------------------------------------------------------


def run_detect(
    source: Path,
    target: Path,
    json_output: bool,
    plan_output: Path | None,
) -> int:
    """Run drift detection and print results. Returns exit code."""
    report = compute_drift(source, target)

    if json_output:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        if not report.has_drift:
            print("No drift detected.")
        else:
            print(f"Drift detected between source and target:\n")
            if report.add:
                print(f"  ADD ({len(report.add)} files):")
                for e in report.add:
                    print(f"    + {e.rel_path}")
            if report.remove:
                print(f"  REMOVE ({len(report.remove)} files):")
                for e in report.remove:
                    print(f"    - {e.rel_path}")
            if report.revise:
                print(f"  REVISE ({len(report.revise)} files):")
                for e in report.revise:
                    print(f"    ~ {e.rel_path}")
            print()
            total = len(report.add) + len(report.remove) + len(report.revise)
            print(f"Total: {total} file(s) with drift.")

    if plan_output:
        _write_plan(report, plan_output)
        if not json_output:
            print(f"\nRemediation plan written to: {plan_output}")

    return 1 if report.has_drift else 0


# ---------------------------------------------------------------------------
# Apply mode
# ---------------------------------------------------------------------------


def run_apply(plan_path: Path, source: Path, target: Path) -> int:
    """Apply a remediation plan. Returns exit code."""
    if not plan_path.is_file():
        print(f"ERROR: Plan file not found: {plan_path}", file=sys.stderr)
        return 2

    try:
        entries = _parse_plan(plan_path)
    except Exception as exc:
        print(f"ERROR: Failed to parse plan file: {exc}", file=sys.stderr)
        return 2

    source = source.resolve()
    target = target.resolve()
    actions: list[str] = []

    def _check_containment(path: Path, root: Path, label: str) -> bool:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            print(f"ERROR: Path escapes {label} root: {path}", file=sys.stderr)
            return False

    # Process ADD entries (unconditional)
    for rel in entries["add"]:
        src_file = (source / rel).resolve()
        dst_file = (target / rel).resolve()
        if not _check_containment(src_file, source, "source"):
            continue
        if not _check_containment(dst_file, target, "target"):
            continue
        if not src_file.is_file():
            print(f"WARN: Source file not found for ADD: {rel}")
            continue
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src_file), str(dst_file))
        actions.append(f"ADD: {rel}")

    # Process REMOVE entries
    for rel in entries["remove"]:
        dst_file = (target / rel).resolve()
        if not _check_containment(dst_file, target, "target"):
            continue
        if dst_file.is_file():
            dst_file.unlink()
            actions.append(f"REMOVE: {rel}")
            try:
                dst_file.parent.rmdir()
            except OSError:
                pass
        else:
            print(f"WARN: Target file not found for REMOVE: {rel}")

    # Process REVISE entries
    for rel in entries["revise"]:
        src_file = (source / rel).resolve()
        dst_file = (target / rel).resolve()
        if not _check_containment(src_file, source, "source"):
            continue
        if not _check_containment(dst_file, target, "target"):
            continue
        if not src_file.is_file():
            print(f"WARN: Source file not found for REVISE: {rel}")
            continue
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src_file), str(dst_file))
        actions.append(f"REVISE: {rel}")

    # Summary
    if actions:
        print(f"Applied {len(actions)} action(s):")
        for action in actions:
            print(f"  {action}")
    else:
        print("No actions to apply.")

    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _find_project_root() -> Path:
    """Walk up from CWD to find the directory containing .claude/."""
    current = Path.cwd().resolve()
    while current != current.parent:
        if (current / ".claude").is_dir():
            return current
        current = current.parent
    return Path.cwd().resolve()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check for harness drift between source and target.",
        epilog=(
            "Examples:\n"
            "  python check_harness_drift.py --source ../seja --target .\n"
            "  python check_harness_drift.py --source . --target . --json\n"
            "  python check_harness_drift.py --apply drift-plan.md --source ../seja"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--source",
        required=False,
        default=None,
        help="Path to canonical harness source directory",
    )
    parser.add_argument(
        "--target",
        default=None,
        help="Path to target workspace (default: auto-detect repo root)",
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--plan-output",
        default=None,
        help="Write a remediation plan file to this path",
    )
    parser.add_argument(
        "--apply",
        dest="apply_plan",
        default=None,
        help="Apply a remediation plan file",
    )

    args = parser.parse_args()

    if args.source is None:
        print("INFO: Harness drift check skipped (no --source provided).")
        sys.exit(0)

    source = Path(args.source).resolve()
    if not source.is_dir():
        print(f"ERROR: Source path is not a directory: {source}", file=sys.stderr)
        sys.exit(2)

    if args.target:
        target = Path(args.target).resolve()
    else:
        target = _find_project_root()

    if not target.is_dir():
        print(f"ERROR: Target path is not a directory: {target}", file=sys.stderr)
        sys.exit(2)

    try:
        if args.apply_plan:
            plan_path = Path(args.apply_plan).resolve()
            exit_code = run_apply(plan_path, source, target)
        else:
            plan_output = Path(args.plan_output) if args.plan_output else None
            exit_code = run_detect(source, target, args.json_output, plan_output)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
