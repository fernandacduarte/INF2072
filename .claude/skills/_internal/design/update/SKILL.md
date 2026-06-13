---
name: design-update-internal
description: "Inlined worker for /design Design Update branch. Not user-invocable."
compatibility: "Designed for Claude Code with the SEJA harness"
metadata:
  internal: true
  category: internal
  version: 1.0.0
---

> This is an inlined worker; execute these instructions as part of the caller's flow. The wrapper at `.claude/skills/design/SKILL.md` has already run the Detection Logic and routed to this mode.
>
> **Pre-skill ownership**: Step 1 of the Design Update instructs running pre-skill. That step stays here in the internal (not in the wrapper) so that pre-skill fires exactly once, from within the mode that actually needs it. Initial-design modes (Modes 1, 2, 3, 4, 5) skip pre-skill entirely because `project/conventions.md` does not yet exist when they run.

## Design Update (project definitions exist)

When `project/conventions.md` already exists AND `project/product-design-as-intended.md` exists:

> **Ownership split (stack updates vs. initial scaffolding)**: Initial stack scaffolding (first-time `conventions.md` population, CLAUDE.md / rules / smoke-test infra scaffolding) is owned by `/seja-setup` (see `/seja-setup` Standard Install Flow step 4b and the `Scaffold-CLAUDE.md` / `Scaffold-Rules` / `Scaffold-SmokeTestInfra` anchors in steps 7c-7e). Stack *updates* in finalised projects go through `/design update stack` (or the interactive Update menu option 1 below). Updates are a separate concern from creation: a user swapping a stack mid-project gets a single entry point here, and `/design` re-invokes the `Scaffold-*` anchors by name to keep downstream artifacts consistent.

1. Run /pre-skill "design" $ARGUMENTS to load general instructions and register the brief. Pre-skill is invoked only in the Update branch; initial-design modes (Mode 1/2/4) remain bootstrap-clean because `project/conventions.md` does not yet exist when they run.

2. **Show current design summary**: Read `project/conventions.md` and display current stack choices.

3. **Offer update options** (skipped on CLI fast path `/design update <slug>`):
   > "Your project design is already configured. What would you like to update?"
   >
   > 1. Stack choices (backend, frontend, database) | 2. Conceptual design (entities, permissions, relationships) | 3. Metacommunication (designer intent, feature messaging) | 4. Backend standards | 5. Frontend standards | 6. UX design standards | 7. Graphic/UI design standards | 8. i18n configuration | 9. Security checklists | 10. Testing standards | 11. Constitution | 12. Full reconfiguration

   Slug-to-option map (CLI fast path): `stack`->1, `conceptual`->2, `metacomm`->3, `backend-standards`->4, `frontend-standards`->5, `ux-standards`->6, `ui-standards`->7, `i18n`->8, `security`->9, `testing`->10, `constitution`->11, `full`->12.

4. **Apply updates**: Read current `project/` file, present values, walk through changes. Preserve unmodified sections.

   **Stack choices (menu option 1 / slug `stack`)**: edit the stack variables in `project/conventions.md` in place -- `BACKEND_FRAMEWORK`, `FRONTEND_FRAMEWORK`, `DATABASE`, `BACKEND_TEST`, `FRONTEND_TEST`, `ORM`, `MIGRATIONS`, `VALIDATION`, `AUTH`, `BUILD_TOOL`, `CSS`, `STATE`, `DATA_FETCHING`, `HTTP_CLIENT`, `ROUTER`, `E2E`, `WCAG`, directory paths (`BACKEND_DIR`, `FRONTEND_DIR`, `MIGRATIONS_DIR`, `FRONTEND_I18N_DIR`), and related conditional rows. Walk the user through each field with the current value shown and the ability to override. Apply the same conditional-population rules documented in `/seja-setup` Standard Install Flow step 4c (omit `BACKEND_*` rows when the new value is `BACKEND_FRAMEWORK=none`; omit `FRONTEND_*` rows and `FRONTEND_I18N_DIR` / `I18N_FRONTEND_FILES` when the new value is `FRONTEND_FRAMEWORK=none`; never leak `{{VAR}}` placeholders into the saved file).

5. **Regenerate dependent files**:

   **Stack-flip orchestration** (applies when menu option 1 / slug `stack` changed `BACKEND_FRAMEWORK` or `FRONTEND_FRAMEWORK`, especially between something and `none` in either direction). `/design` does NOT duplicate the anchor bodies -- it re-enters the corresponding `/seja-setup` step behaviors by anchor name so a stack flip has the same downstream effect as a first-time scaffold:

   - Re-run the `Scaffold-CLAUDE.md` anchor (`/seja-setup` Standard Install Flow step 7c) to regenerate the stack-time portions of `CLAUDE.md` (stack summary, build/run commands, Backend / Frontend Architecture Summary sections, i18n block, pure-CLI fallback). The `## Project design` H2 added by `/design` Mode 1 step 8 (design-intent `@`-references) is preserved -- the Scaffold-CLAUDE.md rebuild writes only the stack-time sections, not the amend-appended design-intent tail.
   - Re-run the `Scaffold-Rules` anchor (`/seja-setup` Standard Install Flow step 7d) to add or remove rule files per the new stack presence. Stack-specific rules that no longer apply (for example `backend-flask.md` after a backend->none flip, or `frontend-react.md` after a frontend->none flip) are removed; new stack-specific rules are added per the new slug (for example `backend-django.md` after a Flask->Django flip). `harness-structure.md` is always preserved.
   - Re-run the `Scaffold-SmokeTestInfra` anchor (`/seja-setup` Standard Install Flow step 7e) to add or remove smoke-test infrastructure. If the new stack has `BACKEND_FRAMEWORK == none`, smoke-test files are removed (`smoke_test_registry.json`, `smoke_test_api.py`, any `e2e/smoke.spec.ts`). If the new stack has a backend but previously had none, the files are emitted. `e2e/smoke.spec.ts` is gated on both `FRONTEND_FRAMEWORK != none` AND an E2E tool being present in the updated `conventions.md`.

   For non-stack updates (slugs `conceptual`, `metacomm`, `backend-standards`, etc.), regenerate only the affected project-specific reference file(s); the `Scaffold-*` anchors are not invoked.
