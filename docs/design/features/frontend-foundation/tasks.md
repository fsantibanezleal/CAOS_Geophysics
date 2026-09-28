# Frontend foundation tasks and convergence

The feature design precedes code. Each task names the requirement and the gate that decides it.

- [x] T01 (R-FF01, R-FF02): centralize six routes and configure explicit legacy/single-origin build modes. Gates: `foundation-routes.test.ts`, both Vite builds and `qa-foundation.mjs`.
- [x] T02 (R-FF03): add typed wire mirrors and reject invalid scientific evidence at the boundary. Gate: `foundation-contracts.test.ts`.
- [x] T03 (R-FF04): add same-origin API transport without UI activation. Gate: `foundation-api-client.test.ts`.
- [x] T04 (R-FF05, R-FF06): retain shared shell tokens, update five architecture diagrams and modal copy with target/live labels. Gates: `foundation-architecture.test.ts`, `qa-architecture.mjs`.
- [x] T05 (R-FF07, R-FF08): run the existing EDI/science tests and desktop/phone rendered navigation matrix; fix regressions inside scope. Gates: Vitest, `qa-interactions.mjs` and `qa-foundation.mjs`.
- [x] T06 (R-FF09): audit the staged change scope and base before committing. Gates: `git diff --cached --name-only`, `git diff --cached --check` and `git rev-parse HEAD`. The commit/push SHA is verified separately in the handoff.

## Convergence record

The frontend gates passed locally on 2026-09-27:

| Gate | Result |
| --- | --- |
| `npm test` | 8 files, 51 tests passed, including released EDI/data tests and four foundation suites. |
| `npm run build` | Passed TypeScript/Vite and generated the five legacy static route entrypoints. |
| `npm run build:single-origin` | Passed TypeScript/Vite with root-relative assets and no static route entrypoints. |
| `qa-foundation.mjs`, legacy and single-origin | 68 rendered route checks per mode across desktop/phone, EN/ES and light/dark; actual App and Benchmark hydration, navigation, no document overflow, and architecture modal fit. |
| `qa-architecture.mjs` | 20 desktop SVG language/theme/bounds renders and 20 mobile full-size modal interactions passed. |
| `qa-interactions.mjs` | Existing EDI/scientific workbench interaction checks passed. |
| Scoped Git diff | Stage and commit audits must confirm only `frontend/` and this feature SDD directory. |

These are frontend gates only. API/Python schema parity, authentication and CSRF endpoint behavior, the worker and pipeline, M13 held-out/browser parity, final hostname/identity, and VPS cutover remain unresolved dependencies. The 0.04.001 static release is still the live product; no new online operation or deployment is claimed.
