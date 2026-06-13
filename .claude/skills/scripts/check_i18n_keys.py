#!/usr/bin/env python3
# designer: When you add or rename a translated string, I check that
#   every key your code asks for is defined in each language, that
#   neither translation has drifted ahead of the other, and that
#   nothing is still sitting empty. You see the missing keys before
#   a user sees a blank button.
"""
check_i18n_keys.py — Detect undefined / mismatched i18n keys.

Invocation: agent-invoked, hook-ci
Lifecycle: active

Checks performed
================
FRONTEND (react-i18next)
  1. Keys used in code via t("key") but missing from en-US.json or pt-BR.json
  2. Keys defined in en-US.json but missing from pt-BR.json, and vice-versa
  3. Dynamic keys (template literals) listed as unverifiable warnings

BACKEND (Flask-Babel .po catalogs)
  4. msgid entries in en_US.po but missing from pt_BR.po, and vice-versa
  5. Empty msgstr entries (untranslated strings)
  6. Keys used via get_common_error / get_common_message but missing from .po
  7. Dynamic keys (f-strings) listed as unverifiable warnings

Usage
-----
    python .claude/skills/scripts/check_i18n_keys.py

Run from the repository root.

CHECK_PLUGIN_MANIFEST:
  name: i18n Keys
  stack:
    backend: [flask]
    frontend: [react]
  scope: i18n
  critical: false
"""

import json
import os
import re
import sys
from pathlib import Path

from project_config import REPO_ROOT, get, get_path, get_list

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

FRONTEND_SRC = get_path("FRONTEND_SRC_DIR") or REPO_ROOT / "frontend" / "src"
_I18N_DIR = get_path("FRONTEND_I18N_DIR") or FRONTEND_SRC / "i18n" / "locales"
_I18N_FRONTEND_FILES = get_list("I18N_FRONTEND_FILES", ["en-US.json", "pt-BR.json"])
_I18N_BACKEND_CATALOGS = get_list("I18N_BACKEND_CATALOGS", ["en_US", "pt_BR"])
FRONTEND_LOCALE_FILES = [(_I18N_DIR / f, f) for f in _I18N_FRONTEND_FILES]

BACKEND_APP = get_path("BACKEND_APP_DIR") or REPO_ROOT / "backend" / "app"
TRANSLATIONS_DIR = get_path("TRANSLATIONS_DIR") or REPO_ROOT / "backend" / "translations"
BACKEND_PO_FILES = [
    (TRANSLATIONS_DIR / cat / "LC_MESSAGES" / "messages.po", cat)
    for cat in _I18N_BACKEND_CATALOGS
]

# Regex patterns for frontend t() calls
# Matches:  t("key")  t('key')  t("key", ...)
_T_STATIC = re.compile(
    r"""\bt\(\s*(?P<q>["'])(?P<key>[a-zA-Z0-9_.]+)(?P=q)"""
)

# Matches:  t(`...${...}...`)  — dynamic / template-literal keys
_T_DYNAMIC = re.compile(
    r"""\bt\(\s*`(?P<expr>[^`]*\$\{[^`]*)`"""
)

# Backend: get_common_error('key') / get_common_message('key')  (static)
# Excludes matches where the quoted string is followed by .join() (separator, not a key)
_BE_STATIC = re.compile(
    r"""(?:get_common_error|get_common_message)\(\s*(?P<q>['"])(?P<key>[^'"]+)(?P=q)(?!\.join)"""
)

# Backend: get_common_error(f'...{...}...')  (dynamic / f-string)
_BE_DYNAMIC = re.compile(
    r"""(?:get_common_error|get_common_message)\(\s*f(?P<q>['"])(?P<expr>[^'"]*\{[^'"]*?)(?P=q)"""
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def flatten_json(obj, prefix=""):
    """Flatten a nested dict into dot-separated keys."""
    keys = set()
    for k, v in obj.items():
        full = f"{prefix}{k}" if not prefix else f"{prefix}.{k}"
        if isinstance(v, dict):
            keys |= flatten_json(v, full)
        else:
            keys.add(full)
    return keys


def load_locale_keys(path):
    """Load a JSON locale file and return its flattened key set."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return flatten_json(data)


def iter_files(root, extensions):
    """Yield Path objects matching given extensions under *root*."""
    for dirpath, _dirs, filenames in os.walk(root):
        for fn in filenames:
            if any(fn.endswith(ext) for ext in extensions):
                yield Path(dirpath) / fn


def relative(path):
    """Return a repo-root-relative POSIX path string."""
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def parse_po_file(path):
    """Parse a .po file and return a dict of msgid -> msgstr.

    Handles multi-line msgid/msgstr entries. Skips the header entry
    (empty msgid).
    """
    entries = {}
    current_msgid = None
    current_msgstr = None
    reading = None  # 'msgid' or 'msgstr'

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")

            if line.startswith("msgid "):
                # Save previous entry
                if current_msgid is not None and current_msgid != "":
                    entries[current_msgid] = current_msgstr or ""
                # Start new msgid
                current_msgid = _extract_po_string(line[6:])
                current_msgstr = None
                reading = "msgid"
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
            else:
                reading = None

    # Save last entry
    if current_msgid is not None and current_msgid != "":
        entries[current_msgid] = current_msgstr or ""

    return entries


def _extract_po_string(s):
    """Extract the string content from a .po quoted string like '"text"'."""
    s = s.strip()
    if s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
        # Unescape common .po escape sequences
        s = s.replace('\\"', '"').replace("\\n", "\n").replace("\\\\", "\\")
    return s


# ---------------------------------------------------------------------------
# Frontend checks
# ---------------------------------------------------------------------------

def check_frontend():
    """Return (errors, warnings) for the frontend i18n layer."""
    errors = []
    warnings = []

    # 1. Load locale files
    locale_keys = {}  # filename -> set of keys
    for fpath, fname in FRONTEND_LOCALE_FILES:
        if not fpath.exists():
            errors.append(f"Locale file not found: {relative(fpath)}")
            return errors, warnings
        locale_keys[fname] = load_locale_keys(fpath)

    # 2. Scan source for t() calls (JS/JSX/TS/TSX)
    static_usages = {}   # key -> set of file locations
    dynamic_usages = []  # (expr, file, line)

    for fpath in iter_files(FRONTEND_SRC, (".js", ".jsx", ".ts", ".tsx")):
        # Skip test files to reduce noise
        fname = fpath.name
        if any(fname.endswith(suf) for suf in (
            ".test.js", ".test.jsx", ".test.ts", ".test.tsx"
        )):
            continue

        try:
            content = fpath.read_text(encoding="utf-8")
        except Exception:
            continue

        for lineno, line in enumerate(content.splitlines(), 1):
            for m in _T_STATIC.finditer(line):
                key = m.group("key")
                static_usages.setdefault(key, set()).add(
                    f"{relative(fpath)}:{lineno}"
                )
            for m in _T_DYNAMIC.finditer(line):
                dynamic_usages.append(
                    (m.group("expr"), relative(fpath), lineno)
                )

    # react-i18next plural suffixes: t("key", { count }) resolves to
    # key_zero / key_one / key_other automatically.
    _PLURAL_SUFFIXES = ("_zero", "_one", "_other")

    def _has_key_or_plural(key, keys):
        """Check if a key exists directly or as pluralization variants."""
        if key in keys:
            return True
        return any(f"{key}{suffix}" in keys for suffix in _PLURAL_SUFFIXES)

    # 3. Report keys used in code but missing from locale files
    for key, locations in sorted(static_usages.items()):
        missing_in = []
        for fname, keys in locale_keys.items():
            if not _has_key_or_plural(key, keys):
                missing_in.append(fname)
        if missing_in:
            loc_str = ", ".join(sorted(locations)[:3])
            if len(locations) > 3:
                loc_str += f" (+{len(locations) - 3} more)"
            errors.append(
                f"Key \"{key}\" used in code but missing from: "
                f"{', '.join(missing_in)}  —  {loc_str}"
            )

    # 4. Keys in one locale but not the other (pairwise)
    locale_names = list(locale_keys.keys())
    for i, name_a in enumerate(locale_names):
        for name_b in locale_names[i + 1:]:
            only_a = locale_keys[name_a] - locale_keys[name_b]
            only_b = locale_keys[name_b] - locale_keys[name_a]
            for key in sorted(only_a):
                errors.append(f"Key \"{key}\" defined in {name_a} but missing from {name_b}")
            for key in sorted(only_b):
                errors.append(f"Key \"{key}\" defined in {name_b} but missing from {name_a}")

    # 5. Dynamic keys (unverifiable)
    for expr, fpath, lineno in dynamic_usages:
        warnings.append(
            f"Dynamic key: t(`{expr}`)  —  {fpath}:{lineno}"
        )

    return errors, warnings


# ---------------------------------------------------------------------------
# Backend checks (Flask-Babel .po catalogs)
# ---------------------------------------------------------------------------

def check_backend():
    """Return (errors, warnings) for the backend i18n layer."""
    errors = []
    warnings = []

    # 1. Parse .po files
    catalog_entries = {}  # catalog_name -> {msgid: msgstr}
    for po_path, catalog_name in BACKEND_PO_FILES:
        if not po_path.exists():
            errors.append(f".po file not found: {relative(po_path)}")
            return errors, warnings
        catalog_entries[catalog_name] = parse_po_file(po_path)

    catalog_msgids = {name: set(entries.keys()) for name, entries in catalog_entries.items()}

    # 2. Parity check — msgids in one catalog but not the other (pairwise)
    catalog_names = list(catalog_msgids.keys())
    for i, name_a in enumerate(catalog_names):
        for name_b in catalog_names[i + 1:]:
            only_a = catalog_msgids[name_a] - catalog_msgids[name_b]
            only_b = catalog_msgids[name_b] - catalog_msgids[name_a]
            for msgid in sorted(only_a):
                errors.append(f"msgid \"{msgid}\" in {name_a}.po but missing from {name_b}.po")
            for msgid in sorted(only_b):
                errors.append(f"msgid \"{msgid}\" in {name_b}.po but missing from {name_a}.po")

    # 3. Empty msgstr (untranslated strings)
    for catalog_name, entries in catalog_entries.items():
        for msgid, msgstr in sorted(entries.items()):
            if not msgstr.strip():
                warnings.append(f"Empty msgstr in {catalog_name}.po: \"{msgid}\"")

    # 4. Scan Python source for get_common_error / get_common_message calls
    all_msgids = set()
    for msgids in catalog_msgids.values():
        all_msgids |= msgids
    static_usages = {}   # (func, key) -> set of locations
    dynamic_usages = []  # (func, expr, file, line)

    for fpath in iter_files(BACKEND_APP, (".py",)):
        if fpath.name in ("i18n.py", "i18n_helpers.py"):
            continue

        try:
            content = fpath.read_text(encoding="utf-8")
        except Exception:
            continue

        for lineno, line in enumerate(content.splitlines(), 1):
            for m in _BE_STATIC.finditer(line):
                func = "get_common_error" if "error" in m.group(0) else "get_common_message"
                key = m.group("key")
                static_usages.setdefault((func, key), set()).add(
                    f"{relative(fpath)}:{lineno}"
                )
            for m in _BE_DYNAMIC.finditer(line):
                func = "get_common_error" if "error" in m.group(0) else "get_common_message"
                dynamic_usages.append(
                    (func, m.group("expr"), relative(fpath), lineno)
                )

    # Report keys used in code but missing from .po catalogs
    for (func, key), locations in sorted(static_usages.items()):
        if key not in all_msgids:
            loc_str = ", ".join(sorted(locations)[:3])
            if len(locations) > 3:
                loc_str += f" (+{len(locations) - 3} more)"
            errors.append(
                f"Key \"{key}\" used via {func}() but missing from .po catalogs"
                f"  —  {loc_str}"
            )

    # Dynamic keys
    for func, expr, fpath, lineno in dynamic_usages:
        warnings.append(
            f"Dynamic key: {func}(f'{expr}')  —  {fpath}:{lineno}"
        )

    return errors, warnings


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    # Force UTF-8 on Windows to avoid charmap errors with symbols
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    _project = get("PROJECT_NAME", "project")
    print(f"# {_project} i18n Key Checker\n")

    total_errors = 0
    total_warnings = 0

    # --- Frontend ---
    print("## Frontend — react-i18next\n")
    print(f"Locales: {', '.join(f for _, f in FRONTEND_LOCALE_FILES)}")
    print(f"Source: {relative(FRONTEND_SRC)}/\n")

    fe_errors, fe_warnings = check_frontend()
    total_errors += len(fe_errors)
    total_warnings += len(fe_warnings)

    if fe_errors:
        print(f"### Errors ({len(fe_errors)})\n")
        for msg in fe_errors:
            print(f"- X {msg}")
        print()

    if fe_warnings:
        print(f"### Warnings — dynamic keys ({len(fe_warnings)})\n")
        for msg in fe_warnings:
            print(f"- ! {msg}")
        print()

    if not fe_errors and not fe_warnings:
        print("- OK No issues found.\n")

    # --- Backend ---
    print("## Backend — Flask-Babel .po catalogs\n")
    print(f"Catalogs: {', '.join(f'{cat}/messages.po' for _, cat in BACKEND_PO_FILES)}")
    print(f"Source: {relative(BACKEND_APP)}/\n")

    be_errors, be_warnings = check_backend()
    total_errors += len(be_errors)
    total_warnings += len(be_warnings)

    if be_errors:
        print(f"### Errors ({len(be_errors)})\n")
        for msg in be_errors:
            print(f"- X {msg}")
        print()

    if be_warnings:
        print(f"### Warnings ({len(be_warnings)})\n")
        for msg in be_warnings:
            print(f"- ! {msg}")
        print()

    if not be_errors and not be_warnings:
        print("- OK No issues found.\n")

    # --- Summary ---
    print("---\n")
    if total_errors:
        print(f"FAIL: {total_errors} error(s), {total_warnings} warning(s)")
    else:
        print(f"PASS: {total_errors} error(s), {total_warnings} warning(s)")

    sys.exit(1 if total_errors else 0)


if __name__ == "__main__":
    main()
