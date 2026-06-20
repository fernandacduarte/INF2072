**What it does**: Manages SEJA's state in this project. Single entry point for every harness-lifecycle operation: install, finalise in place, companion workspace, demo bootstrap, and upgrade. On first install it scaffolds `CLAUDE.md` with stack-dependent content, populates `.claude/rules/` with stack-flavored rule files, and fills `product-design/conventions.md` with basic definitions. With no arguments, it inspects the current directory via `detect_setup_state.py` and routes to the correct action.

State detection recognizes four project states: **no-harness** (fresh install target), **fresh-download** (SEJA cloned into project, needs finalisation), **partial-init** (conventions.md exists but design intent absent), and **finalised** (full project, offers upgrade).

**Examples**:
> `/seja-setup /path/to/my-project`
> Detects the scenario (greenfield/existing), copies all harness files, populates conventions.md with stack definitions via the Section 1 questionnaire, scaffolds CLAUDE.md and rules, and tells you to run `/design` next.

> `/seja-setup --here`
> Detects you downloaded SEJA into your project folder; finalises setup in place. Prompts for git-history handling and cleanup of harness-dev artefacts.

> `/seja-setup /path/to/my-project --workspace`
> Creates a companion workspace directory alongside an existing codebase. The workspace is its own git repo with version-controlled design history.

> `/seja-setup /path/to/taskflow-demo --demo`
> Sets up the harness with the pre-configured TaskFlow demo project (pre-filled conventions, constitution, conceptual design, and walkthrough).

> `/seja-setup --upgrade`
> Upgrades harness files in the current project to the latest SemVer tag without touching project-specific files.

> `/seja-setup --upgrade --version v0.2.0`
> Pins the upgrade to a specific release tag instead of latest.

> `/seja-setup --upgrade --dry-run`
> Previews what the upgrade would change without applying anything.

> `/seja-setup`
> No args: inspects cwd, reports the detected state, and routes to install, finalise, upgrade menu, or refuse as appropriate.

**When to use**: Every time you touch SEJA's state in a project -- first install, in-place finalisation, companion-workspace creation, demo bootstrap, or later harness upgrade. After the first iteration, you rarely run `/seja-setup` unless upgrading.

Stack-presence modes determine what gets scaffolded: **full-stack** (backend + frontend), **API-only** (`FRONTEND_FRAMEWORK=none`), **frontend-only** (`BACKEND_FRAMEWORK=none`), and **CLI / library** (both `none`). Each mode emits only the appropriate rows in `conventions.md`, sections in `CLAUDE.md`, rule files, and smoke-test infrastructure.

**Next step**: `/design` after a fresh install to define design intent (entities, permissions, metacommunication, personas, standards). If you are new to SEJA, read `general/getting-started.md` first. After `--upgrade`: `/check health` to verify harness integrity, then `/explain spec-drift` to catch changed conventions.

**Merge background**: This skill merges the former `/setup` and `/upgrade` into a unified harness-state command.
