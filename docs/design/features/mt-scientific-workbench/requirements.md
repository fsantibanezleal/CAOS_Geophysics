# Selected-project MT scientific workbench requirements

Status: planned
Date: 2026-10-03. Parent: [approved product SDD](../../SDD.md), M05/M06, R-005/006/007/009/011/013/014/015/016. The owner explicitly renewed this complete frontend unit, including real isolated worker QA, before implementation. Base: reviewed PR103, develop `9b0cbe5750cdf2b778b269f415c0c4613bd16d5e`. No deployment, host activation, canonical modification or backend change is authorized.

MTV-01 THE frontend SHALL parse the immutable EDI envelope, M05 screen, M06 candidate and MT export as distinct typed contracts, reject identity/unit/axis/shape/semantic drift, and never use the gravity result verifier. Gate: `frontend/src/api/mt-processing.test.ts`.

MTV-02 WHEN an owner selects project MT processing, THE App SHALL expose original validation, authoritative eligibility, actual queued M05/M06 submission, polling, cancellation and durable non-success handling within the existing six-route shell. Gate: `frontend/e2e/mt-workbench.spec.ts`.

MTV-03 IF the original tensor fails the necessary all-frequency screen, THEN THE workbench SHALL show measured tensor/QC and reasons only, disable M06, and retain null truth/no inverse; actual cl061 SHALL remain QC-only. Gate: `frontend/e2e/mt-workbench.spec.ts` and `frontend/src/api/mt-processing.test.ts`.

MTV-04 WHEN M05 succeeds, THE instrument SHALL display linked Zxy and -Zyx real/imaginary E/H ohm, apparent resistivity ohm m, principal phase degrees and per-real/imaginary SD, full signed tensor, frame and ancillary tipper/missingness with no invented covariance. Gate: `frontend/src/components/mt-view-data.test.ts` and `frontend/e2e/mt-workbench.spec.ts`.

MTV-05 WHEN an eligible M06 is configured, THE form SHALL validate zero/one imposed thickness [2,4000] m, one/two starts strictly (1,6000) ohm m, beta [0,1], 20..40 bootstrap draws and integer seed, binding the actual same-dataset M05 ID. Gate: `frontend/src/api/mt-processing.test.ts` and `frontend/e2e/mt-workbench.spec.ts`.

MTV-06 WHEN M06 succeeds, THE instrument SHALL expose the actual fixed-layer model, both components' observed/predicted/signed complex residuals, frozen train/holdout partition and WRMS, successful/failed starts, same-input halfspace and beta/thickness comparators without holdout tuning or synthetic truth. Gate: `frontend/src/components/mt-view-data.test.ts` and `frontend/e2e/mt-workbench.spec.ts`.

MTV-07 THE instrument SHALL expose solver stop/budget, objective-state identity, local identifiability, conditional interval quantiles/samples/seeds/failures/status and conditioning, never geological posterior or calibrated field coverage. Gate: `frontend/src/api/mt-processing.test.ts` and `frontend/e2e/mt-workbench.spec.ts`.

MTV-08 WHEN view controls change, THE instrument SHALL correctly map Hz/seconds, ohm/milliohm, signed raw/standardized residuals with symmetric linear scales, linked selection and physical readouts; charts SHALL support pointer brush/pan/zoom/reset, keyboard and accessible exact-value tables. Gate: `frontend/src/components/mt-view-data.test.ts` and `frontend/e2e/mt-workbench.spec.ts`.

MTV-09 WHEN an owner downloads a successful MT bundle, THE client SHALL verify bounded ZIP members, original member SHA-256, job/dataset/source/environment/parameters/units identity and MT scientific array consistency before download. Gate: `frontend/src/api/mt-processing.test.ts` and `frontend/e2e/mt-workbench.spec.ts` with actual `app.bundle.verify_bundle`.

MTV-10 WHILE public host admission remains closed, THE UI SHALL show the API's unavailable verdict and offer no forced activation; actual MT QA SHALL opt in only within a loopback isolated private API/worker store. Gate: `frontend/e2e/mt-workbench.spec.ts` and `tests/ui/mt_devserver.py`.

MTV-11 THE complete scientific views SHALL use shared shell tokens/fonts, Tabs, Equation/Cite/Refs, full EN/ES and light/dark, desktop/phone pointer interactions and screenshots, no decorative 3D layers or orphan route. Gate: `frontend/e2e/mt-workbench.spec.ts`, `npm run build` and `npm run build:single-origin`.

MTV-12 WHEN a real thickness/beta/seed configuration changes, THE API worker SHALL return the submitted immutable parameters and a measured effect in model/prediction or conditional sample arrays, without replacing the frozen holdout; private/canonical artifacts SHALL remain excluded. Gate: `frontend/e2e/mt-workbench.spec.ts` and scoped Git diff review recorded in `convergence.md`.
