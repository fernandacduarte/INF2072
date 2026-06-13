#!/usr/bin/env python3
# designer: When your project ships in more than one language, I compare the
#   translation catalogs side by side and tell you which strings are missing
#   from one locale, which have been left untranslated, which need review,
#   and which message keys your code uses but no catalog defines -- so your
#   next release does not leak English into a non-English UI.
"""
check_po_parity.py — Verify Flask-Babel .po catalog parity.

Invocation: agent-invoked, hook-ci
Lifecycle: active

Checks performed
================
  1. msgid entries in en_US.po but missing from pt_BR.po, and vice-versa
  2. Empty msgstr entries (untranslated strings)
  3. Keys used via get_common_error/get_common_message in Python source
     but missing from both .po catalogs
  4. Fuzzy entries (marked #, fuzzy — may need review)

Usage
-----
    python .claude/skills/scripts/check_po_parity.py

Run from the repository root.
Optional flags:
    --verbose       Show all entries, not just problems
    --check-code    Also scan Python source for missing keys (slower)

CHECK_PLUGIN_MANIFEST:
  name: PO Parity
  stack:
    backend: [flask]
    frontend: []
  scope: i18n
  critical: false
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

from project_config import REPO_ROOT, get_path

TRANSLATIONS_DIR = get_path("TRANSLATIONS_DIR") or REPO_ROOT / "backend" / "translations"
EN_PO = TRANSLATIONS_DIR / "en_US" / "LC_MESSAGES" / "messages.po"
PT_PO = TRANSLATIONS_DIR / "pt_BR" / "LC_MESSAGES" / "messages.po"

BACKEND_APP = get_path("BACKEND_APP_DIR") or REPO_ROOT / "backend" / "app"

# Backend: get_common_error('key') / get_common_message('key')
_BE_STATIC = re.compile(
    r"""(?:get_common_error|get_common_message)\(\s*(?P<q>['"])(?P<key>[^'"]+)(?P=q)(?!\.join)"""
)


def parse_po_file(path):
    """Parse a .po file and return (entries, fuzzy_msgids).

    entries: dict of msgid -> msgstr
    fuzzy_msgids: set of msgids marked as fuzzy
    """
    entries = {}
    fuzzy_msgids = set()
    current_msgid = None
    current_msgstr = None
    is_fuzzy = False
    reading = None

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")

            if line.startswith("#, fuzzy"):
                is_fuzzy = True
                continue

            if line.startswith("msgid "):
                # Save previous entry
                if current_msgid is not None and current_msgid != "":
                    entries[current_msgid] = current_msgstr or ""
                current_msgid = _extract_po_string(line[6:])
                current_msgstr = None
                reading = "msgid"
                if is_fuzzy and current_msgid:
                    fuzzy_msgids.add(current_msgid)
                    is_fuzzy = False
            elif line.startswith("msgstr "):
                current_msgstr = _extract_po_string(line[7:])
                reading = "msgstr"
            elif line.startswith('"') and reading:
                continuation = _extract_po_string(line)
                if reading == "msgid":
                    current_msgid = (current_msgid or "") + continuation
                elif reading == "msgstr":
                    current_msgstr = (current_msgstr or "") + continuation
            elif line.startswith("#") or line.strip() == "":
                reading = None
                is_fuzzy = False
            else:
                reading = None

    # Save last entry
    if current_msgid is not None and current_msgid != "":
        entries[current_msgid] = current_msgstr or ""

    return entries, fuzzy_msgids


def _extract_po_string(s):
    """Extract the string content from a .po quoted string."""
    s = s.strip()
    if s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
        s = s.replace('\\"', '"').replace("\\n", "\n").replace("\\\\", "\\")
    return s


def scan_code_keys():
    """Scan Python source for get_common_error/get_common_message calls.

    Returns dict of key -> list of file:line locations.
    """
    usages = {}
    for dirpath, _dirs, filenames in os.walk(BACKEND_APP):
        for fn in filenames:
            if not fn.endswith(".py") or fn in ("i18n.py", "i18n_helpers.py"):
                continue
            fpath = Path(dirpath) / fn
            try:
                content = fpath.read_text(encoding="utf-8")
            except Exception:
                continue
            for lineno, line in enumerate(content.splitlines(), 1):
                for m in _BE_STATIC.finditer(line):
                    key = m.group("key")
                    try:
                        rel = fpath.relative_to(REPO_ROOT).as_posix()
                    except ValueError:
                        rel = str(fpath)
                    usages.setdefault(key, []).append(f"{rel}:{lineno}")
    return usages


def main():
    parser = argparse.ArgumentParser(description="Check Flask-Babel .po catalog parity")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show all entries, not just problems")
    parser.add_argument("--check-code", action="store_true",
                        help="Also scan Python source for missing keys")
    args = parser.parse_args()

    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("# Flask-Babel .po Parity Check\n")

    if not EN_PO.exists():
        print(f"ERROR: {EN_PO} not found")
        sys.exit(1)
    if not PT_PO.exists():
        print(f"ERROR: {PT_PO} not found")
        sys.exit(1)

    en_entries, en_fuzzy = parse_po_file(EN_PO)
    pt_entries, pt_fuzzy = parse_po_file(PT_PO)

    en_msgids = set(en_entries.keys())
    pt_msgids = set(pt_entries.keys())

    errors = []
    warnings = []

    # 1. Parity check
    only_en = en_msgids - pt_msgids
    only_pt = pt_msgids - en_msgids
    for msgid in sorted(only_en):
        errors.append(f"msgid in en_US.po but missing from pt_BR.po: \"{msgid}\"")
    for msgid in sorted(only_pt):
        errors.append(f"msgid in pt_BR.po but missing from en_US.po: \"{msgid}\"")

    # 2. Empty msgstr
    for msgid, msgstr in sorted(en_entries.items()):
        if not msgstr.strip():
            warnings.append(f"Empty msgstr in en_US.po: \"{msgid}\"")
    for msgid, msgstr in sorted(pt_entries.items()):
        if not msgstr.strip():
            warnings.append(f"Empty msgstr in pt_BR.po: \"{msgid}\"")

    # 3. Fuzzy entries
    for msgid in sorted(en_fuzzy):
        warnings.append(f"Fuzzy entry in en_US.po: \"{msgid}\"")
    for msgid in sorted(pt_fuzzy):
        warnings.append(f"Fuzzy entry in pt_BR.po: \"{msgid}\"")

    # 4. Code key check (optional)
    if args.check_code:
        print("Scanning Python source for i18n key usage...\n")
        code_keys = scan_code_keys()
        all_msgids = en_msgids | pt_msgids
        for key, locations in sorted(code_keys.items()):
            if key not in all_msgids:
                loc_str = ", ".join(locations[:3])
                if len(locations) > 3:
                    loc_str += f" (+{len(locations) - 3} more)"
                errors.append(f"Key \"{key}\" used in code but missing from .po catalogs  --  {loc_str}")

    # Report
    print(f"en_US.po: {len(en_entries)} entries")
    print(f"pt_BR.po: {len(pt_entries)} entries\n")

    if args.verbose:
        common = en_msgids & pt_msgids
        print(f"## Common entries ({len(common)})\n")
        for msgid in sorted(common):
            print(f"  OK  \"{msgid}\"")
        print()

    if errors:
        print(f"## Errors ({len(errors)})\n")
        for msg in errors:
            print(f"- X {msg}")
        print()

    if warnings:
        print(f"## Warnings ({len(warnings)})\n")
        for msg in warnings:
            print(f"- ! {msg}")
        print()

    if not errors and not warnings:
        print("PASS: All .po catalogs are in sync with no empty translations\n")
    elif errors:
        print(f"FAIL: {len(errors)} error(s), {len(warnings)} warning(s)")
        sys.exit(1)
    else:
        print(f"WARN: {len(warnings)} warning(s), 0 errors")


if __name__ == "__main__":
    main()
