# UX RESEARCH — fernanda-INF2072

<!-- maintained-by: human (designer/researcher); Human (markers) classification since SEJA 2.8.2 -->

---

## 1. Personas

### Persona Inventory

| ID | Name | Role / Archetype | Goals |
|----|------|-----------------|-------|
| R-P-001 | Graduate Researcher | PUC-Rio MARL researcher | Train and compare MARL algorithms; produce reproducible results for INF2072 |

### R-P-001: Graduate Researcher

> **Role / Archetype:** PUC-Rio graduate student, INF2072 course project
>
> **Bio:** A graduate student in computer science at PUC-Rio working on multi-agent reinforcement learning as part of the INF2072 course. Familiar with Python, PyTorch, and RL concepts. May be new to BenchMARL specifically.
>
> **Goals:**
> - G-001: Train cooperative ghost agents using IQL, VDN, and QMIX on the custom Pacman environment
> - G-002: Produce a statistically valid comparison of coordination behaviors across algorithms
> - G-003: Generate publication-ready figures and results for the course report
>
> **Key Frustrations:**
> - Long training wall-clock times make iteration slow
> - Difficulty reproducing results across different machines
>
> **Relevant Context:**
> - Technical proficiency: intermediate (Python, PyTorch) to expert (RL theory)
> - Usage frequency: daily during course project period
> - Domain knowledge: graduate-level MARL theory; may be less familiar with BenchMARL internals

---

## 2. Problem Scenarios

### R-PS-001: Irreproducible Results

- **Persona:** R-P-001 (Graduate Researcher)
- **Goals:** G-002, G-003
- **Setting:** Preparing the course report; attempting to reproduce a result from a prior run

The researcher runs the same algorithm twice and gets different reward curves. Without explicit seed control in the training script, random initialization produces non-deterministic results. The researcher cannot determine whether a difference in results is due to a configuration change or random variance. This undermines the validity of algorithm comparisons and makes it impossible to cite specific results in the report.

---

## 3. Cross-Reference Map

| Artifact ID | Artifact Title | Design Artifact | Relationship |
|-------------|---------------|----------------|-------------|
| R-P-001 | Graduate Researcher | product-design-as-intended EMT 1.1 | Feeds |
| R-PS-001 | Irreproducible Results | product-design-as-intended §11 (seed control) | Feeds |

---

## 4. Processing Status

| Artifact | ID | Status | Design Iteration | Notes |
|----------|-----|--------|-----------------|-------|
| Persona | R-P-001 | pending | - | initial |
| Problem scenario | R-PS-001 | pending | - | initial |

---

## 5. Discovered User Journeys

*No formal user research sessions conducted yet. Journeys will be added as course project progresses.*

---

## CHANGELOG

2026-06-13 | R-P-001 | added | - | initial persona entry
2026-06-13 | R-PS-001 | added | - | initial problem scenario
