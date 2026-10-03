# Local validation receipt

Date: 2026-09-28. Branch: `task/geophysics-api-lifecycle-ui`. This is a branch-local integration receipt, not a release/cutover or scientific dataset verdict.

| Gate | Observed result |
| --- | --- |
| INT-API-FE-01 / R-FE-API-01 | `frontend/src/test/api-live-contract-parity.test.ts` accepts the v1 owner-view fixture and rejects private key, version, false QC and owner-path drift. `tests/api/test_frontend_contract_fixture.py` validates the same JSON through the real `RawAssetView` Pydantic model. |
| Typed client / R-FE-API-02, 03, 05, 06 | `npm test`: 12 files, 66 tests passed. Includes auth/CSRF/form login/reset, owner-scoped project/raw paths, byte/hash verification, error field propagation and scientific declaration rejections. |
| Backend contract cross-check | `.venv-api\Scripts\python.exe -m pytest tests/api -q`: 45 tests passed, including versioned owner view, source rights and backup-refusal tests. One upstream Starlette/httpx deprecation warning; no test failure. |
| Two build modes / R-FE-API-07 | `npm run build:single-origin` and `npm run build` passed; legacy generated five direct static route entrypoints and exposes no project button. Existing Vite large-chunk warning remains non-failing. |
| Real browser lifecycle / R-FE-API-02–07 | `npx playwright test e2e/api-lifecycle.spec.ts --workers=1`: 3 tests passed against a loopback-only real FastAPI/SQLite instance and built single-origin frontend. EN desktop + ES phone completed registration, mailed-token verification, login, project create, wrong-datum 422 with field path, corrected original upload, owner receipt, SHA-checked download, project ZIP, typed-name deletion/backup caveat and logout; EN desktop also completed mailed-token password reset. Opposite EN phone + ES desktop guest views stayed readable. |
| Legacy guest regression | `npx playwright test e2e/legacy-guest.spec.ts --workers=1`: 2 tests passed against the built static preview in EN/ES phone. Six shell links, hydrated Model view and no account affordance. |
| Rendered inspection | Inspected guest, upload, validation error, receipt and deletion screenshots in EN desktop/ES phone, plus EN phone/ES desktop guest and legacy EN/ES phone. Captures are generated under ignored `data/raw/qa-browser-screenshots/`; no private test data or screenshots are added to the public branch. Sticky close control, visible mobile error and no dialog horizontal overflow were checked after repair. |

Unresolved dependencies: the API has no individual asset-delete endpoint, so only confirmed project deletion is offered; backup inventory/purge and restore discipline remain operator work. No dataset QC, processing, method/job/result API, rights-cleared public catalogue or production single-origin hostname/cutover exists in this feature. Private raw upload and its `raw_metadata_checked` receipt do not establish scientific validity or a live inverse operation.
