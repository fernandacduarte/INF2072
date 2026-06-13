---
recommended: true
depends_on: [all]
freshness: on-structural-change
diataxis: reference
description: "Project README structure with architecture links and developer onboarding reading order."
designer_description: "When /document generates your project's top-level README, I'm the template that shapes the project blurb, prerequisites, quick-start, development-setup, and architecture-overview sections using your plan's Docs: fields and the real structure of your repo, so a new developer landing on your root directory gets an onboarding path rather than a wall of unexplained files."
---

# TEMPLATE -- PROJECT README

> **How to use this template:** Copy this file to your project root as `README.md`. Replace `{{placeholders}}` with your project's values. Remove sections that don't apply.

## {{PROJECT_NAME}}

> {{one-paragraph project description: what it does, who it's for, what problem it solves}}

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| {{tool}} | {{version}} | {{purpose}} |

## Getting Started

### Quick start (Docker)

<!-- Replace with your actual commands -->

1. Clone the repository
2. Copy `.env.example` to `.env` and fill in values
3. Run `docker compose up`
4. Open `http://localhost:{{PORT}}`

### Development setup

<!-- Replace with your actual development setup steps -->

## Architecture Overview

> For detailed architecture documentation, see [Architecture]({{ARCHITECTURE_DOC_PATH}}).

{{2-3 sentence architecture summary with key technology choices}}

## Recommended Reading Order

> New to the project? Follow this path to get productive quickly.

| # | Document | What you'll learn |
|---|----------|-------------------|
| 1 | This README | Project overview and setup |
| 2 | {{path}} | {{description}} |
| 3 | {{path}} | {{description}} |

## Contributing

See [Coding Conventions]({{CONVENTIONS_DOC_PATH}}) for code style, commit message format, and review process.

## License

{{license type}}

## Freshness Policy

Review and update this README when the project's directory structure, tech stack, or build process changes significantly. Minor code changes do not require README updates.
