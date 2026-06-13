---
name: seja-setup
description: "Manage the SEJA harness in this project: install into a new or existing codebase, finalise an in-place download, create a companion workspace, bootstrap a demo project, or upgrade harness files to the latest release. State-driven dispatch routes each invocation to the right action, preserving project-specific configuration."
argument-hint: "[<target-directory>] [--here | --workspace | --demo | --upgrade] [--version <tag>] [--dry-run]"
compatibility: "Designed for Claude Code with the SEJA harness"
metadata:
  last-updated: 2026-04-26
  version: 3.5.0
  category: utility
  context_budget: standard
  questionnaire_version: 7
  references:
    - general/shared-definitions.md
    - template/questionnaire.md
    - template/conventions.md
---

> Overview: see [./SKILL-quickguide.md](./SKILL-quickguide.md)

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `<target-directory>` | Yes (unless `--here`, `--upgrade`, or no-args flow) | Path to the target project directory |
| `--workspace` | No | Create a separate workspace directory (for working alongside an existing codebase) |
| `--here` | No | Finalise SEJA setup in the current directory without copying harness files (use when you downloaded SEJA directly into your project) |
| `--demo` | No | Set up with the pre-configured TaskFlow demo project |
| `--upgrade` | No | Upgrade harness files in the current project to the latest SemVer tag (or `--version <tag>`). Preserves project-specific files. |
| `--version <tag>` | No | Public `seja` release tag to pin to (e.g. `v0.1.0`). Default: latest SemVer tag on `simonedjb/seja`. Falls back to HEAD with a warning if no tags exist. |
| `--dry-run` | No | Preview upgrade changes without applying them (valid with `--upgrade`) |

# Seja-Setup

> **`/seja-setup`** scaffolds topology-WHAT (stack, directory layout, CLAUDE.md, rules, smoke-test infra). **`/design`** defines design-intent-WHAT and WHY (entities, permissions, metacomm, personas, standards, constitution). **`/plan`** defines HOW to build it and WHY those hows. Setup creates, design refines, plan schedules.

## Overview

This skill manages every harness-state transition in a project: **install** (copy from source), **finalise in place** (`--here`), **companion workspace** (`--workspace`), **demo** (`--demo`), **upgrade** (`--upgrade`), and **refuse** (dev-repo protection). Entry point inspects cwd via `detect_setup_state.py` and routes to the correct branch; every state is handled in this file.

## Version Pinning

Under the A2 release model, public `seja` ships tagged releases (`vMAJOR.MINOR.PATCH`). `/seja-setup` resolves the tag **before** any copy or upgrade and writes it to `<target>/.seja-version` as the baseline for future upgrades.

**Resolution order**: `--version <tag>` -> that tag; else latest SemVer tag on remote; else warn and record `HEAD` (pre-release fallback). `.claude/skills/seja-setup/resolve_seja_version.py` queries `git ls-remote --tags https://github.com/simonedjb/seja` and validates `--version`.

When running from a local seja checkout, confirm the working tree is at the resolved tag before copying. If HEAD diverges, either `git checkout <tag>` or pass `--version HEAD`.

**Legacy (no `.seja-version`)**: pre-A2 projects upgrade as `unknown -> <target-tag>` with a banner; `.seja-version` is written on first upgrade. Pass `--version <intended-baseline>` to explicitly set a baseline without upgrading to latest.

## Distribution Model

`/seja-setup` is the single entry point into the harness. Mode surface:

| Mode | Invocation | Action |
|------|------------|--------|
| Install | `/seja-setup <target>` | Copy harness files from source into new or existing project directory. |
| Finalise in place | `/seja-setup --here` | When SEJA was cloned directly into the project folder: scaffold project dirs around files already present. See `## --here Flag`. |
| Companion workspace | `/seja-setup --workspace` | Create workspace alongside existing codebase; operate on codebase via `claude --add-dir`. |
| Demo | `/seja-setup --demo <target>` | Install + pre-fill TaskFlow design files. See `## --demo Flag`. |
| Upgrade | `/seja-setup --upgrade` | Refresh harness files at latest release (or `--version <tag>`); preserves project files, settings, output. |

Shared mechanics: the source repository is not a runtime dependency -- after setup, all skills/rules/agents/references live inside the target project, and the user continues working from the target project (not the source). To refresh an existing project use `--upgrade` (or re-run `/seja-setup` with "Overwrite harness only"). (Contributors sometimes call the source repo the "seed repo" internally; not an end-user term.)

## Entry-Point Routing

**First action is always state detection.** Shell out to `python .claude/skills/seja-setup/detect_setup_state.py --json` (from cwd, or from the explicit target) and parse the JSON output. Fields: `state` (one of `no-harness`, `fresh-download`, `partial-init`, `finalised`, `dev-repo-refuse`, `public-clone-soft-confirm`), `signals` dict (diagnostics: `has_claude`, `has_project_conventions`, `has_output`, `git_remote_url`, `has_dev_scripts`), `recommendation` (human-readable sentence).

**Flag short-circuits** (before state dispatch):

| Flag | Route |
|------|-------|
| `--upgrade` | `## Upgrade Flow` (still honour `dev-repo-refuse` before mutating) |
| `--here` | `## --here Flag` |
| `--demo <target>` | `## Standard Install Flow` + `## --demo Flag` extension |
| `--workspace` | `## Standard Install Flow` with workspace routing at step 2b |
| `<target>` only | `## Standard Install Flow` |

**No-arg dispatch by state**:

| State | Prompt | Menu / Action |
|-------|--------|---------------|
| `fresh-download` | SEJA files present but `project/` and `_output/` not populated. | AskUserQuestion: **Finalise here** -> `## --here Flag`; **Set up a different target** -> prompt for target path -> `## Standard Install Flow`; **Cancel** -> abort. |
| `finalised` | Harness + project files exist. If `.seja-version` == latest, print "Harness already up to date at `<tag>`" and exit. | AskUserQuestion: **Upgrade to latest** -> `## Upgrade Flow`; **Overwrite harness only** -> `## Standard Install Flow` step 1 with flag preselected; **Overwrite everything** -> Standard Install + extra confirmation; **Create companion workspace** -> Standard Install step 2b (brownfield detection); **Abort**. |
| `partial-init` | Print state summary from `signals` (`conventions.md`, `_output/`, `.claude/settings.json` present/absent). | AskUserQuestion: **Finalise here (reconcile)** -> `## --here Flag`; **Upgrade harness files** -> `## Upgrade Flow`; **Cancel**. |
| `public-clone-soft-confirm` | A `git clone` of public `seja` with no divergence; soft-confirm, not hard-refuse. | AskUserQuestion: **Yes, continue** -> `## --here Flag`; **No, cancel** -> abort. |
| `no-harness` | "How would you like to set up your project?" | AskUserQuestion: **I have a target directory** -> ask path -> Standard Install step 1; **Guide me through setup** -> ask (a) greenfield/brownfield, (b) embedded/companion workspace, (c) target path (+ workspace path if companion) -> Standard Install step 1 with `--workspace` set internally if chosen; **Abort**. |
| `dev-repo-refuse` | Hard-refuse, no menu. | Print the multi-line refusal message below (cite `git_remote_url`, `has_seja_public_subtree`, `has_dev_scripts` from `signals`), then exit without mutation. |

**Menu rationale at render time**: when presenting the AskUserQuestion blocks above, follow Short-form rationale allowance (`general/constraints.md`): one-line "Recommended when ..." for obvious options (`Cancel`, `Abort`, `No, cancel`, `Yes, continue`), two-line "Recommended when ... / NOT recommended when ..." for non-obvious ones. For the `finalised` menu specifically, keep the two-line form on **Upgrade to latest** (NOT when starting over), **Overwrite harness only** (NOT when local customisations must survive -- use Upgrade), **Overwrite everything** (NOT when project is active and reset is unsure), and **Create companion workspace** (NOT when the embedded layout is intentional).

**`dev-repo-refuse` message**:

> "You are inside a SEJA development repository. `/seja-setup` no-arg routing and `--here` are intended for end-user projects and refuse to run here to avoid corrupting the harness source.
>
>  Signals detected:
>  - git remote: `<git_remote_url>`
>  - seja-public subtree: `<has_seja_public_subtree>`
>  - dev scripts: `<has_dev_scripts>`
>
>  If you meant to work on the harness itself, use `git pull` and standard development workflows -- not `/seja-setup`.
>  If you meant to set up a consumer project, run `/seja-setup <target-directory>` with an explicit target outside the dev repo."

## Dispatch

Once Entry-Point Routing has resolved the active mode, read the corresponding internal skill's `SKILL.md` via the Read tool (not the Skill tool -- avoids firing lifecycle hooks twice) and execute its instructions inline. Pre-skill has already run in the wrapper; the internal owns the mode-specific step sequence.

| Mode | Flag/state | Internal SKILL.md path |
|------|-----------|------------------------|
| Standard install | `<target>` only or no-args `no-harness`/`fresh-download` state | `.claude/skills/_internal/seja-setup/install/SKILL.md` |
| Upgrade | `--upgrade` | `.claude/skills/_internal/seja-setup/upgrade/SKILL.md` |
| Demo | `--demo` | `.claude/skills/_internal/seja-setup/demo/SKILL.md` |
| Finalise in place | `--here` | `.claude/skills/_internal/seja-setup/here/SKILL.md` |

## Rationale

Setup/upgrade unification, state-driven dispatch, and workspace separation: advisory-000431, plan-000392, advisory-000366 (A2 release model).
