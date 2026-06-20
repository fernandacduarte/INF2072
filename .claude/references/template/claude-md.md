---
designer_description: "I'm your project's CLAUDE.md -- the top-of-directory instructions every Claude agent reads first, so your stack, build and test commands, key conventions, and the list of references each skill should load stay one prompt away from any session that touches this codebase."
---

# Template: CLAUDE.md

> Copy this file to the project root as `CLAUDE.md` and fill in the placeholders.

---

# ${PROJECT_NAME}

${PROJECT_DESCRIPTION}

## Stack

- **Backend:** ${BACKEND_STACK}
- **Frontend:** ${FRONTEND_STACK}
- **Testing:** ${TESTING_STACK}
- **Deployment:** ${DEPLOYMENT_STACK}

## Build & Run

### Backend

```bash
cd ${BACKEND_DIR}
# Add backend setup and run commands
```

### Frontend

```bash
cd ${FRONTEND_DIR}
# Add frontend setup and run commands
```

### Tests

```bash
# Backend unit tests
cd ${BACKEND_DIR} && ${BACKEND_TEST_CMD}

# Frontend unit tests
cd ${FRONTEND_DIR} && ${FRONTEND_TEST_CMD}

# E2E tests
cd e2e && ${E2E_TEST_CMD}
```

### Database Migrations

```bash
cd ${BACKEND_DIR}
# Add migration commands
```

## Architecture

### Backend

${BACKEND_ARCHITECTURE_SUMMARY}

### Frontend

${FRONTEND_ARCHITECTURE_SUMMARY}

## Key Conventions

- ${CONVENTION_1}
- ${CONVENTION_2}
- ${CONVENTION_3}

## Validation Scripts

Helper scripts in `.claude/skills/scripts/`:

```bash
# List available validation scripts and their purpose
```

## Skills & References

This project uses Claude Code skills (`.claude/skills/`) and reference files (`product-design/`). Skills are invoked via `/skill-name`. Key skills: `/plan`, `/implement`, `/research`, `/check review`, `/check validate`.

@product-design/conventions.md
@.claude/references/general/constraints.md
@.claude/references/general/permissions.md
