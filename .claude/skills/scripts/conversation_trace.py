#!/usr/bin/env python3
# designer: When any utterance -- from the user, assistant, or tool -- happens
#   outside a skill, I'm the append-only ledger that records each message with
#   its emitter, type, session linkage, event chaining, and automatic
#   sensitivity masking so the epistemic history of the project is preserved
#   without leaking secrets.
"""
conversation_trace.py -- Append-only conversation trace log for SEJA.

Invocation: skill-invoked, user-cli
Lifecycle: active

Manages the conversation trace JSONL file (CONVERSATION_TRACE_FILE from conventions.md).
Each entry records a single utterance with emitter, type, session and event-chain
linkage.

Subcommands:
  append           Append a new entry (with automatic secret masking)
  backfill-skill   Set led_to_skill on an existing entry
  last-evt-id      Print the last evt_id for a session

Usage
-----
    python .claude/skills/scripts/conversation_trace.py append \\
        --session-id abc123 --emitter user --message "How does X work?" \\
        --type question
    python .claude/skills/scripts/conversation_trace.py backfill-skill \\
        --evt-id qa-000003 --skill-id /implement
    python .claude/skills/scripts/conversation_trace.py last-evt-id \\
        --session-id abc123

Exit codes: 0 success, 1 error, 2 masking confirmation required.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Import project_config from the same directory
from project_config import get_path

# Import SECRET_PATTERNS from the design/ sibling directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "design"))
from check_secrets import SECRET_PATTERNS

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# Trace file resolution
# ---------------------------------------------------------------------------

_EVT_ID_RE = re.compile(r"^qa-(\d{6})$")


def _trace_path() -> Path:
    """Resolve the conversation trace file path from conventions."""
    p = get_path("CONVERSATION_TRACE_FILE")
    if p is None:
        print("ERROR: CONVERSATION_TRACE_FILE not configured in conventions.md",
              file=sys.stderr)
        sys.exit(1)
    return p


def _read_entries(path: Path) -> list[dict]:
    """Read all JSONL entries from the trace file."""
    if not path.is_file():
        return []
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"WARNING: skipping malformed line {line_num}: {e}",
                      file=sys.stderr)
    return entries


def _next_evt_id(entries: list[dict]) -> str:
    """Compute the next evt_id from existing entries."""
    max_num = 0
    for entry in entries:
        eid = entry.get("evt_id", "")
        m = _EVT_ID_RE.match(eid)
        if m:
            max_num = max(max_num, int(m.group(1)))
    return f"qa-{max_num + 1:06d}"


def _mask_message(message: str) -> tuple[str, bool]:
    """Apply SECRET_PATTERNS to mask sensitive spans in a message.

    Returns (masked_message, was_masked).
    """
    masked = message
    was_masked = False
    for name, pattern in SECRET_PATTERNS:
        def _replacer(m: re.Match, _name: str = name) -> str:
            nonlocal was_masked
            was_masked = True
            return f"[MASKED:{_name}]"
        masked = pattern.sub(_replacer, masked)
    return masked, was_masked


# ---------------------------------------------------------------------------
# Subcommand: append
# ---------------------------------------------------------------------------


def _cmd_append(args: argparse.Namespace) -> int:
    """Append a new utterance entry to the trace file."""
    trace_file = _trace_path()
    entries = _read_entries(trace_file)

    evt_id = _next_evt_id(entries)
    masked_message, was_masked = _mask_message(args.message)

    # If masking occurred and --confirm not set, show masked text and exit 2
    # so the caller can confirm before sensitive data is persisted
    if was_masked and not args.confirm:
        print(f"Masking applied. Masked message:\n{masked_message}")
        print(f"\nRe-run with --confirm to accept and append the masked entry.")
        return 2

    # Parse topic tags; None when not provided (matches documented "null when not yet tagged")
    topic_tags = None
    if args.topic_tags:
        topic_tags = [t.strip() for t in args.topic_tags.split(",") if t.strip()]

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": args.session_id,
        "evt_id": evt_id,
        "preceding_evt_id": args.preceding_evt_id,
        "emitter": args.emitter,
        "message": masked_message,
        "message_masked": was_masked,
        "type": args.type,
        "led_to_skill": args.led_to_skill,
        "topic_tags": topic_tags,
    }

    # Ensure parent directory exists
    trace_file.parent.mkdir(parents=True, exist_ok=True)

    with open(trace_file, "a", encoding="utf-8", newline="") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(evt_id)
    return 0


# ---------------------------------------------------------------------------
# Subcommand: backfill-skill
# ---------------------------------------------------------------------------


def _cmd_backfill_skill(args: argparse.Namespace) -> int:
    """Set led_to_skill on an existing entry."""
    trace_file = _trace_path()
    entries = _read_entries(trace_file)

    if not entries:
        print(f"ERROR: trace file is empty or missing", file=sys.stderr)
        return 1

    found = False
    for entry in entries:
        if entry.get("evt_id") == args.evt_id:
            entry["led_to_skill"] = args.skill_id
            found = True
            break

    if not found:
        print(f"ERROR: evt_id {args.evt_id!r} not found in trace",
              file=sys.stderr)
        return 1

    # Rewrite the entire file
    with open(trace_file, "w", encoding="utf-8", newline="") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return 0


# ---------------------------------------------------------------------------
# Subcommand: last-evt-id
# ---------------------------------------------------------------------------


def _cmd_last_evt_id(args: argparse.Namespace) -> int:
    """Print the last evt_id for a given session."""
    trace_file = _trace_path()
    entries = _read_entries(trace_file)

    last_id = None
    for entry in entries:
        if entry.get("session_id") == args.session_id:
            last_id = entry.get("evt_id")

    print(last_id if last_id is not None else "null")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="conversation_trace.py",
        description="Manage the SEJA conversation trace log.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # -- append --
    p_append = sub.add_parser("append", help="Append a new utterance entry")
    p_append.add_argument("--session-id", required=True,
                          help="Session identifier")
    p_append.add_argument("--emitter", required=True,
                          help="Who produced the utterance (e.g. user, claude)")
    p_append.add_argument("--message", required=True,
                          help="The utterance text (sensitivity-masked at write time)")
    p_append.add_argument("--type", required=True,
                          help="Utterance type (e.g. question, answer, instruction)")
    p_append.add_argument("--preceding-evt-id", default="null",
                          help="evt_id of the preceding entry in the chain")
    p_append.add_argument("--led-to-skill", default=None,
                          help="Skill invoked as a result of this utterance")
    p_append.add_argument("--topic-tags", default=None,
                          help="Comma-separated topic tags")
    p_append.add_argument("--confirm", action="store_true",
                          help="Confirm appending a masked entry")

    # -- backfill-skill --
    p_backfill = sub.add_parser("backfill-skill",
                                help="Set led_to_skill on an existing entry")
    p_backfill.add_argument("--evt-id", required=True,
                            help="Target evt_id to update")
    p_backfill.add_argument("--skill-id", required=True,
                            help="Skill identifier to set")

    # -- last-evt-id --
    p_last = sub.add_parser("last-evt-id",
                            help="Print the last evt_id for a session")
    p_last.add_argument("--session-id", required=True,
                        help="Session identifier to search for")

    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    dispatch = {
        "append": _cmd_append,
        "backfill-skill": _cmd_backfill_skill,
        "last-evt-id": _cmd_last_evt_id,
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    try:
        return handler(args)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
