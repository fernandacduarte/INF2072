import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent  # .claude/skills/scripts/
_SKILLS_DIR = _SCRIPTS_DIR.parent                       # .claude/skills/

# Add the scripts directory to sys.path so tests can import sibling modules
sys.path.insert(0, str(_SCRIPTS_DIR))
# Also add scripts/priv/ for private-only modules (e.g., generate_changelog_data)
sys.path.insert(0, str(_SCRIPTS_DIR / "priv"))
# Add skill subdirectories that now contain scripts co-located with their skill
for _skill in ["reflect", "check", "seja-setup", "post-skill", "design", "explain", "help"]:
    sys.path.insert(0, str(_SKILLS_DIR / _skill))
