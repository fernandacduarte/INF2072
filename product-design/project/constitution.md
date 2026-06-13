# PROJECT CONSTITUTION — fernanda-INF2072

> Immutable principles that override all other guidance. Loaded by pre-skill before any other reference.

---

## Project Identity

fernanda-INF2072 — A custom multi-agent Pacman RL environment with coordinated ghost agents for benchmarking IQL, VDN, and QMIX algorithms under reproducible conditions.

Target users: PUC-Rio graduate students and researchers working with multi-agent reinforcement learning.

---

## Technical Principles

| # | Principle | Rationale |
|---|-----------|-----------|
| T1 | Python 3.11 is the required interpreter; use `py -3.11` to invoke scripts | Algorithm reproducibility depends on consistent Python version |
| T2 | All experiment outputs (checkpoints, reward plots, benchmark CSVs) go to `benchmarl_setup/runs/` | Centralized output prevents scattered artifacts and enables cross-run comparison |
| T3 | Custom environment lives in `custom_environment/`; BenchMARL integration adapters live in `benchmarl_setup/` | Separation of domain logic from framework integration |
| T4 | No hardcoded seed values in production scripts — seeds must be configurable via CLI args | Reproducibility requires explicit seed control |
| T5 | ChromaDB indices must not be deleted or restructured without an explicit migration plan | Prevents loss of embedded knowledge base state |

---

## Quality Principles

| # | Principle | Rationale |
|---|-----------|-----------|
| Q1 | Every training run must emit a reward log; no silent runs | Results must be comparable and auditable |
| Q2 | Tests in `test/` must remain passing before committing changes to the environment | Smoke tests guard against regressions in the RL environment |
| Q3 | Benchmark runs use a minimum of 5 seeds to produce statistically meaningful results | Single-seed results are insufficient for RL comparison claims |

---

## Security Invariants

| # | Invariant | Rationale |
|---|-----------|-----------|
| S1 | No API keys or credentials committed to version control | Local research tool must not leak secrets |
| S2 | External model checkpoints must not be loaded without explicit user confirmation | Pickle-based checkpoints are a code execution vector |

---

## Compliance Requirements

| # | Requirement | Regulation/Contract |
|---|-------------|---------------------|
| C1 | Results reported in academic papers must reference the exact commit hash of the codebase used | Academic integrity / reproducibility standards |

---

## Enforcement

- These principles are loaded into every agent context via pre-skill.
- `/check validate` verifies conformance against constraints in `product-design/project/agent/constraints.yaml`.
- Violations during `/check review` or `/check preflight` are classified as **blocking**.
- To amend this constitution, the change must be explicitly approved by the project lead and documented in the changelog below.

---

## Changelog

### v1 — 2026-06-13 15:49 UTC
- Initial constitution created via `/design`.
