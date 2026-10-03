# M08/M13 content tasks and convergence

The feature requirements and design precede frontend changes. Complete the tasks vertically, retaining the distinction between source-supported method explanation and unimplemented numerical evidence.

- [x] T01 (R-PC02, R-PC03, R-PC04): author bilingual theory/implementation data and source-linked wiki chapter. Gates: `phase-picking-content.test.ts::m08_content_and_units`, `::m13_architecture_loss_and_honesty`, `::disjoint_same_trace_evaluation_without_results`, `::wiki_source_links`.
- [x] T02 (R-PC05, R-PC06): render equations, primary citations, honest limitations and original themed diagrams without result simulation. Gates: `phase-picking-content.test.ts::equations_citations_and_diagrams`, `::no_false_operation_claim`, `qa-phase-picking.mjs::bilingual_theme_diagram`.
- [x] T03 (R-PC01): integrate grouped Methodology and Implementation navigation, preserving existing chapters. Gates: `phase-picking-content.test.ts::grouped_navigation_preserves_legacy_chapters`, `qa-phase-picking.mjs::pointer_reachability_and_fit`.
- [x] T04 (R-PC01-R-PC07): run full frontend tests and both builds, rendered desktop/phone EN/ES QA, inspect screenshots, and audit changed paths. Gates: Vitest, TypeScript/Vite builds, `qa-phase-picking.mjs`, `qa-foundation.mjs`, `qa-interactions.mjs`, `git diff --cached --check`, `git diff --cached --name-only`. The remote push is verified in the final handoff, not inferred from this document.

## Convergence record

- `npm test`: 9 files, 58 tests passed, including all 7 named content tests.
- `npm run build` and `npm run build:single-origin`: TypeScript/Vite passed. Vite warns about a roughly 599 kB client chunk; no new routing or runtime failure was observed.
- Legacy and single-origin built previews: `qa-phase-picking.mjs` passed 32 M08/M13 views each (desktop/phone, EN/ES, light/dark); `qa-foundation.mjs` passed 68 six-route checks each. `qa-interactions.mjs` passed with no failures, preserving EDI/workbench navigation.
- Manual screenshot inspection covered desktop and phone in both languages and themes, including the method-specific figures. The phone tab strip was shortened and the test now checks each group against the visible strip after selection; no clipping or diagram-label collision remains in the inspected captures.
- M08 numerical execution, M13 training/checkpoint, field-data and pretrained-weight rights, event/station-disjoint metrics, and browser inference parity remain product dependencies. These content gates do not pass any of those scientific or deployment gates.
