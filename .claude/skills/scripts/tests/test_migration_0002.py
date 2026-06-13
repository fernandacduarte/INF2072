"""Tests for migration 0002 (/seed -> /setup rename)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# Load run_migrations (sibling-scripts import) for _parse_version access.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import run_migrations  # noqa: E402


def _load_migration_module():
    """Import the 0002 migration module by file path.

    The migration lives at .claude/migrations/0002_rename_seed_to_setup.py.
    The leading digit makes it an invalid Python identifier, so we load it
    via importlib rather than a normal import.
    """
    repo_root = Path(__file__).resolve().parents[4]
    migration_path = (
        repo_root / ".claude" / "migrations" / "0002_rename_seed_to_setup.py"
    )
    spec = importlib.util.spec_from_file_location(
        "migration_0002_rename_seed_to_setup", str(migration_path)
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# upgrade() tests
# ---------------------------------------------------------------------------


def test_migration_0002_upgrade_rewrites_seed_to_setup(tmp_path: Path) -> None:
    """All five /seed patterns are replaced; a GitHub URL is left alone."""
    module = _load_migration_module()

    claude_md = tmp_path / "CLAUDE.md"
    claude_md.write_text(
        "\n".join(
            [
                "# Project",
                "",
                "Run `/seed hello-world` to copy the framework.",
                "Run `/seed --here` to finalise in place.",
                "Run `/seed --workspace` for a companion workspace.",
                "Run `/seed --demo` for the hello-world tour.",
                "Run `/seed --version v0.1.0` to pin a release.",
                "",
                "See https://github.com/simonedjb/seja for the source.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    module.upgrade(tmp_path)

    updated = claude_md.read_text(encoding="utf-8")
    assert "/setup hello-world" in updated
    assert "/setup --here" in updated
    assert "/setup --workspace" in updated
    assert "/setup --demo" in updated
    assert "/setup --version v0.1.0" in updated
    # Ensure every user-typed /seed command was rewritten.
    assert "/seed" not in updated
    # The GitHub URL must be untouched.
    assert "https://github.com/simonedjb/seja" in updated


def test_migration_0002_idempotent(tmp_path: Path) -> None:
    """Second run is a no-op; file contents unchanged after the first pass."""
    module = _load_migration_module()

    claude_md = tmp_path / "CLAUDE.md"
    claude_md.write_text(
        "Run `/seed hello` and `/seed --here`.\n", encoding="utf-8"
    )

    module.upgrade(tmp_path)
    first = claude_md.read_text(encoding="utf-8")

    module.upgrade(tmp_path)
    second = claude_md.read_text(encoding="utf-8")

    assert first == second
    assert "/seed" not in second


# ---------------------------------------------------------------------------
# Version-gate test (Plan Amendment 1)
# ---------------------------------------------------------------------------


def test_migration_0002_gate_fires_for_v0_1_0_consumer() -> None:
    """from_version <= parse('v0.1.0') < to_version -- migration must fire."""
    module = _load_migration_module()

    consumer = run_migrations._parse_version("v0.1.0")
    from_v = run_migrations._parse_version(module.from_version)
    to_v = run_migrations._parse_version(module.to_version)

    assert from_v <= consumer < to_v, (
        f"Migration gate did not fire for consumer v0.1.0: "
        f"from={from_v}, consumer={consumer}, to={to_v}"
    )
