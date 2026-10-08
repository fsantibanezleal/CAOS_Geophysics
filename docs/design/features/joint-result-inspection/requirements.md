# Local supplied joint result inspection

Qualification is scoped to native-output inspection, not physical replay or
integrated application acceptance. Scientific and transport gates stay distinct.

JR-01 WHEN a local workflow output directory is selected, THE inspector SHALL
admit exact completed solve/evaluate or failed workflow inventories, bounded
JSON and literal native NPY headers before loading any array values.
Gate: frontend/src/test/joint-result.test.ts::rejects malformed transport before value loading

JR-02 WHEN original array bytes are imported, THE inspector SHALL verify every
descriptor file/data SHA-256 and exact shape, preserve original bytes, and bind
model, freeze, result and selection identities without claiming physical replay.
Gate: frontend/src/test/joint-result.test.ts::imports actual workflow without scientific promotion

JR-03 WHILE a completed result is inspected, THE instrument SHALL show linked
observed/predicted/signed and whitened residuals, separate partition metrics,
native active-cell density and susceptibility, exact coordinates and units.
Gate: frontend/src/test/joint-result.test.ts::preserves exact linked physical values

JR-04 WHERE actual calibration states exist, THE inspector SHALL show every
candidate, literal terminal failure, accepted state and five exported terms,
without manufacturing historical predictions or approximate coupling maps.
Gate: frontend/src/test/joint-result.test.ts::retains nonconverged states and exact exported coupling

JR-05 WHEN export is requested, THE inspector SHALL preserve original files in
a private archive and label numeric inspection sidecars as derived inspection,
not an executed inverse, rights grant or scientific acceptance certificate.
Gate: frontend/src/test/joint-result.test.ts::round trips original bytes without promotion

JR-06 WHILE imports are pending or replaced, THE component SHALL prevent stale
results/exports, use explicit accessible bilingual controls and shell language,
reuse scientific widgets, and perform no network requests or offline solve.
Gate: frontend/src/test/joint-result-component.test.ts::renders bilingual inspection boundary
Gate: frontend/e2e/joint-result-inspection.spec.ts

JR-07 IF a workflow failed, THEN THE inspector SHALL retain the failed resource
receipt, replay-verified prefix and explicitly unreplayed last attempt, without
promoting a durable freeze to a completed result or exposing a sealed result.
Gate: frontend/src/test/joint-result.test.ts::retains aborted workflow without sealed promotion
