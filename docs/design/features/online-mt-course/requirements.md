# Online MT scientific course requirements

Status: implemented and locally validated; Main's pinned independent course review passed; post-review develop6050100 integration validated. Date: 2026-10-03. Authorized by the user's explicit M05/M06 course request under the approved [product SDD](../../SDD.md).

This is a course/content change, not backend admission, canonical promotion or completion of M01-M13. Initial base: develop afac8ab; develop3b0fd0e and then6050100 safely integrated. Historical scientific reference: PR100 compute7b69404. The integrated scientific/backend/canonical tree is inherited unchanged from develop6050100, including actual PR97, not a separate science edit. The actual consolidated page is `frontend/src/pages/Research.tsx`; separate Methodology.tsx/Implementation.tsx files do not exist. Its two MT content slots, import seam and subsequently authorized Introduction scope are in scope. Bacon owns App/widgets/processing contracts/styles.

R-MTC-001 THE course SHALL state the complex Maxwell/plane-wave recurrence, positive time convention, E/H units, tensor frame, variance-to-sigma conversion and conservative full-frequency QC in faithful EN/ES with captioned equations and primary references in every section. Gate: frontend/src/test/online-mt-course.test.ts::scientific content and equations.

R-MTC-002 THE course SHALL describe the actual weighted complex log-resistivity TRF objective, adjacent-index Tikhonov normalization, finite-difference Jacobians, frozen mask, training-only multistart, bounds, baseline and beta/thickness controls without claiming analytic derivatives or holdout selection. Gate: tests/test_online_mt_course.py::test_objective_mask_and_normalization and frontend/src/test/online-mt-course.test.ts::implementation contract.

R-MTC-003 WHEN a worked synthetic case is selected, THE course SHALL display actual independently checked fixed-h, wrong-h, halfspace and beta results, source identity, known synthetic target separated from supplied-data truth, and answer explanations. Gate: tests/test_online_mt_course.py::test_worked_case_replay and frontend/e2e/online-mt-course.spec.ts::course grid.

R-MTC-004 IF the Clear Lake cl061 case is discussed, THEN THE course SHALL retain its actual original hash, byte count, failed full-tensor screen, null field truth and QC-only/ineligible M06 interpretation. Gate: tests/test_online_mt_course.py::test_cl061_source_exclusion and frontend/src/test/online-mt-course.test.ts::field exclusion.

R-MTC-005 THE course SHALL distinguish data fit, geometry g, beta and fixed h conditioning, local identifiability and conditional pointwise bootstrap from global uniqueness, geological posterior and calibrated field coverage. Gate: frontend/src/test/online-mt-course.test.ts::conditional scope and tests/test_online_mt_course.py::test_reflection_oracle_and_conditional_bootstrap.

R-MTC-006 THE course SHALL tie equations to actual functions and array axes/shapes, immutable owner-scoped worker/bundle identity and explicit admission limits, without a filesystem diagram or assertion of host activation. Gate: frontend/src/test/online-mt-course.test.ts::implementation contract.

R-MTC-007 WHEN the course is navigated from App, THE shell SHALL expose every M05/M06 section, exercise and theme-aware hand-authored physics SVG in EN/ES, light/dark, desktop/phone and reduced motion with actual pointer navigation and rendered bounds. Gate: frontend/e2e/online-mt-course.spec.ts::course grid.

R-MTC-008 THE change SHALL preserve every non-MT page section, existing replay MT algorithms, global styles, App/widgets/contracts, backend/scientific sources, canonical data and private ignored candidates. Gate: frontend/src/test/online-mt-course.test.ts::scoped integration and docs/validation/online-mt-course-review.md (path/section diff and full frontend test/build receipt).

Independent release gates remain unresolved: canonical full assembly, actual-host resource/headroom/security acceptance and integrated App acceptance. Course tests cannot satisfy them.

R-MTC-009 WHEN Introduction describes the product, THE course SHALL distinguish immutable originals, derived processing/corrections and inversion; actual owned CSV flag processing and reviewed bounded EDI admission; null field truth; offline GPU, bounded CPU and export/import without promising thirteen online methods or passed host admission. Preserve existing mathematical lessons. Gate: frontend/src/test/online-mt-course.test.ts::Introduction current scope and frontend/e2e/online-mt-course.spec.ts::Introduction scope grid.

Ownership amendment2026-10-03: main explicitly verified exclusive Research.tsx ownership and authorized Introduction scope corrections. Preserve its existing equations and core lessons. R-MTC-008's preservation clause now excludes only this newly authorized Introduction prose/seam, not its equations or any other page.
