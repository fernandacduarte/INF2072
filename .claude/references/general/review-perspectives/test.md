---
designer_description: "When the reviewer is asked to look at what you built through testability eyes, I'm the checklist that tells it what to watch for -- whether existing tests still cover the change, where new tests are needed for success and error paths, contract coverage between services, mocking strategy, test isolation, and reproducibility of the test environment -- so the suite keeps earning its right to gate merges."
tier: Essential
---

# TEST — Testability

## Essential

- [P0] Is this change covered by existing tests, or are new tests needed?
- [P0] Are success path, error paths, and edge cases tested?
- [P0] Are API contract tests catching frontend/backend schema drift?
- [P0] Are security tests (SAST, DAST, fuzzing) integrated into the pipeline?
- [P0] Do consumer-driven contract tests let services deploy independently?

## Deep-dive

- [P1] Can this be tested in isolation without complex setup?
- [P1] Are E2E tests automated in a pipeline (not just locally), with layered architecture (unit/integration/E2E) and clear ownership ratios?
- [P1] Is mutation testing validating test suite effectiveness, with a measured score flagging weak assertions?
- [P1] Are performance/load tests defined for critical paths with baselines and regression thresholds?
- [P1] Is test infrastructure reproducible (containerised runners, pinned dependencies, cached layers) for deterministic results?
- [P2] Is there a flaky test detection/quarantine mechanism?
- [P2] Do property-based or generative tests cover invariants example-based tests miss?
- [P2] Is test data managed via deterministic factories/fixtures, not shared mutable state?
- [P2] Is there a structured exploratory testing charter to complement automated coverage?
- [P3] Are visual regression snapshots captured for UI components with diffing and approval workflow?
