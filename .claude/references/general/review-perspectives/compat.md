---
designer_description: "When the reviewer is asked to look at what you built through compatibility eyes, I'm the checklist that tells it what to watch for -- API contract stability, schema-evolution safety, browser and runtime support, graceful degradation, dependency-range conflicts, and whether older clients can still talk to your new service during rollout -- so breaking changes either get a migration window or get caught before they ship."
tier: Deep-dive
---

# COMPAT — Compatibility

## Essential

- [P0] Does this change break existing API contracts or database schemas?
- [P0] Is backward compatibility preserved, or is a migration path provided?
- [P0] Are API contract changes validated against existing client versions before deployment?
- [P0] Do API changes include a versioning or deprecation strategy giving consumers a migration window before breaking endpoints are removed?
- [P0] Are schema changes deployed via reversible migrations, with the previous application version still able to operate against the new schema during rollout?

## Deep-dive

- [P1] Are browser compatibility targets defined and tested (browserslist, cross-browser E2E)?
- [P1] Does this change rely on Web APIs or CSS features absent from any supported browser without fallbacks?
- [P1] Have touch interactions, viewport constraints, and OS-specific behaviors (iOS Safari, Android WebView) been verified on supported mobile platforms?
- [P1] Have dependency version constraints been checked for conflicts across transitive ranges?
- [P1] Is the code free of runtime-specific APIs (Node-only, Deno-only, Bun-only) that would break in any targeted JavaScript runtime?
- [P1] Has legacy-system integration been validated so protocol versions, encodings, and data formats remain compatible with older upstream/downstream services?
- [P2] Do UI changes maintain equivalent functionality across assistive-tech browser/screen-reader pairings (NVDA+Firefox, VoiceOver+Safari)?
- [P2] Does the feature degrade gracefully when JavaScript is unavailable or optional platform capabilities are missing (progressive enhancement)?
- [P2] Are new platform features consumed via feature detection rather than UA sniffing, with polyfills loaded only when the native API is absent?
