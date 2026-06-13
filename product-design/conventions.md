# PROJECT CONVENTIONS

> Centralized project-specific definitions. All skills and reference files reference variables from this file instead of hardcoding project-specific values.

---

## Project Identity

| Variable | Value | Description |
|----------|-------|-------------|
| `PROJECT_NAME` | fernanda-INF2072 | Project display name |
| `PROJECT_DESCRIPTION` | Multi-agent RL research — custom Pacman environment with ghost coordination using BenchMARL (IQL, VDN, QMIX), for INF2072 at PUC-Rio | One-line project description |
| `PROJECT_MODE` | brownfield | Project mode: greenfield (new project) or brownfield (existing codebase) |

---

## Directory Structure

| Variable | Value | Description |
|----------|-------|-------------|
| `SKILLS_DIR` | `.claude/skills` | Root directory for skill definitions |
| `AGENT_SPECS_DIR` | `product-design/project/agent` | Agent-facing structured specifications in YAML |
| `OUTPUT_DIR` | `_output` | Root directory for all generated artifacts |
| `PLANS_DIR` | `${OUTPUT_DIR}/plans` | Plan output folder |
| `SCRIPTS_DIR` | `${OUTPUT_DIR}/generated-scripts` | Script output folder |
| `ADVISORY_DIR` | `${OUTPUT_DIR}/advisory-logs` | Advisory log output folder |
| `RESEARCH_DIR` | `${OUTPUT_DIR}/research-logs` | Research log output folder |
| `PROPOSALS_DIR` | `${OUTPUT_DIR}/proposals` | Lightweight change proposals |
| `INVENTORIES_DIR` | `${OUTPUT_DIR}/inventories` | Inventory output folder |
| `USER_TESTS_DIR` | `${OUTPUT_DIR}/user-tests` | User test plan output folder |
| `EXPLAINED_BEHAVIORS_DIR` | `${OUTPUT_DIR}/explained-behaviors` | Behavior explanation output folder |
| `EXPLAINED_CODE_DIR` | `${OUTPUT_DIR}/explained-code` | Code explanation output folder |
| `EXPLAINED_DATA_MODEL_DIR` | `${OUTPUT_DIR}/explained-data-model` | Data model explanation output folder |
| `EXPLAINED_ARCHITECTURE_DIR` | `${OUTPUT_DIR}/explained-architecture` | Architecture explanation output folder |
| `BEHAVIOR_EVOLUTION_DIR` | `${OUTPUT_DIR}/behavior-evolution` | Behavior evolution explanation output folder |
| `REFLECTIONS_DIR` | `${OUTPUT_DIR}/reflections` | Reflection report output folder |
| `ONBOARDING_PLANS_DIR` | `${OUTPUT_DIR}/onboarding-plans` | Onboarding plan output folder |
| `COMMUNICATION_DIR` | `${OUTPUT_DIR}/communication` | Communication material output folder |
| `ROADMAP_DIR` | `${OUTPUT_DIR}/roadmaps` | Roadmap output folder |
| `QA_LOGS_DIR` | `${OUTPUT_DIR}/qa-logs` | QA session log output folder |
| `CHECK_LOGS_DIR` | `${OUTPUT_DIR}/check-logs` | Check/preflight/review output folder |
| `TMP_DIR` | `${OUTPUT_DIR}/tmp` | Temporary/helper scripts |
| `CODEBASE_DIR` | `.` | Root directory of the project codebase (embedded mode) |

---

## Key Files

| Variable | Value | Description | Maintained by |
|----------|-------|-------------|---------------|
| `BRIEFS_FILE` | `${OUTPUT_DIR}/briefs.md` | Execution log of all skill invocations | Agent |
| `BRIEFS_INDEX_FILE` | `${OUTPUT_DIR}/briefs-index.md` | Lightweight briefs index | Agent |
| `ARTIFACT_INDEX_FILE` | `${OUTPUT_DIR}/INDEX.md` | Single global artifact index | Agent |
| `CONSTITUTION_FILE` | `product-design/project/constitution.md` | Project constitution — immutable principles | Human |
| `AS_CODED` | `product-design/project/product-design-as-coded.md` | Unified implementation state | Agent |
| `CD_AS_IS_CHANGELOG` | `product-design/project/product-design-changelog.md` | As-built conceptual design changelog | Agent |
| `DESIGN_INTENT` | `product-design/project/product-design-as-intended.md` | Unified working intent + Decisions + CHANGELOG | Human (markers) |
| `DESIGN_INTENT_TO_BE` | `product-design/project/product-design-as-intended.md` | Legacy alias for `DESIGN_INTENT` | Human (markers) |
| `UX_RESEARCH` | `product-design/project/ux-research-results.md` | UX research: personas, scenarios, journeys | Human (markers) |
| `STANDARDS` | `product-design/project/standards.md` | Engineering standards | Human / Agent |
| `DESIGN_STANDARDS` | `product-design/project/design-standards.md` | Design standards | Human / Agent |
| `SESSION_NOTES_FILE` | `${TMP_DIR}/session-notes.md` | Session-scoped working memory | Agent |
| `DECISION_DIGEST_FILE` | `${OUTPUT_DIR}/decision-digest.jsonl` | Machine-readable decision index | Agent |
| `CONVERSATION_TRACE_FILE` | `${OUTPUT_DIR}/conversation-trace.jsonl` | Append-only conversation trace log | Agent |

---

## As-Intended / As-Coded Registry

| As-Intended file | Section | As-Coded counterpart |
| ---------------- | ------- | -------------------- |
| `${DESIGN_INTENT}` | §0-§17 design intent + Decisions + CHANGELOG | `${AS_CODED}` |
| `${DESIGN_INTENT}` | §15 designed journeys | `${AS_CODED} § Journey Maps` |
| `${UX_RESEARCH}` | all (personas, scenarios, journeys, CHANGELOG) | `-` |

---

## Review Configuration

| Variable | Value | Description |
|----------|-------|-------------|
| `MINIMUM_REVIEW_DEPTH` | `light` | Minimum review depth floor. Valid values: `light`, `standard`, `deep`. |

---

## Periodic Triggers

| Trigger | Interval (days) | Action type | Description |
|---------|-----------------|-------------|-------------|
| Periodic curation | 30 | `periodic-curation` | Review `product-design-as-intended.md` for items ready to promote |
| Spec-drift check | 14 | `spec-drift-check` | Run `/explain spec-drift` to surface drift |
| Git freshness check | 7 | `check-git-freshness` | Compare repo to upstream |

| Threshold | Value | Description |
|-----------|-------|-------------|
| Pending plan age escalation | 30 | Days before an open `implement` pending entry is surfaced |
| Verify-as-coded file threshold | 5 | Minimum files changed before post-skill auto-creates a `verify-as-coded` action |
| Pending age escalation | 14 | Days before a pending action is flagged "overdue" |
| Pending auto-dismiss | 90 | Days after which unaddressed pending actions are auto-dismissed |

---

## Stack Description

| Variable | Value | Description |
|----------|-------|-------------|
| `TESTING_STACK` | pytest | Testing technology |
| `DEPLOYMENT_STACK` | local (Windows, Python 3.11 venv) | Deployment target |

---

## Architecture Description

| Variable | Value | Description |
|----------|-------|-------------|
| `ARCHITECTURE_DESCRIPTION` | Research CLI scripts organized by concern: `benchmarl_setup/` for training runners and benchmarks, `custom_environment/` for Pacman RL environment and evaluation, `test/` for smoke tests. No server; experiments run locally via Python scripts. | High-level architecture description |
| `ARCHITECTURE_PATTERN` | Script-based research pipeline | Architecture pattern |
| `CONVENTION_1` | Python 3.11 required; use `py -3.11` to invoke scripts | Key project convention #1 |
| `CONVENTION_2` | All experiment outputs (checkpoints, reward plots, benchmark CSVs) go to `benchmarl_setup/runs/` | Key project convention #2 |
| `CONVENTION_3` | Custom environment lives in `custom_environment/`; BenchMARL integration adapters live in `benchmarl_setup/` | Key project convention #3 |
