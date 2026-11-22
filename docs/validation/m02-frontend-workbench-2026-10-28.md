# Uploaded gravity M02 frontend workbench

Validation date: 2026-10-28. Source commit: `f3275d3` (`feat: add uploaded gravity L2 workbench`).

The authenticated project gravity workflow now parses the API's `gravity.survey-l2-ordinary/v1` job contract, exposes the method only when the API marks it eligible, submits validated typed parameters, loads completed results, and verifies the exported ZIP members and identities. The dataset-derived 2 × 2 × 1 mesh and spatial-block window are labeled as starter values; the user must review the fixed-geometry model, split and prior. The API remains authoritative for source eligibility and host admission.

The result instrument reads hash-verified typed arrays. Its elevation selector renders returned active-cell bounds in physical XY coordinates. Predicted values and held-out residuals are plotted at returned receiver coordinates; station tooltips and the expanded held-out table report observed, predicted, residual and whitened values with units. The output explicitly preserves `field_truth = null`, `model_accuracy = null`, and false field/full-method/GPU/host acceptance claims.

Verification on this commit:

- `npm test -- src/test/gravity-l2-contracts.test.ts src/test/processing-contracts.test.ts src/test/project-instrument-mount.test.tsx --reporter=dot`: 19 passed across three files.
- `npm run build`: passed; Vite retains the existing >500 kB workbench chunk warning.
- `git diff --check`: passed.

This validates the browser contract against controlled artifacts, not the VPS. The external-output-matrix frontend suite was not run because `GEOPHYSICS_JOINT_OUTPUT_MATRIX_FIXTURE` is not configured. Hosted M02 remains unavailable because the VPS has no measured M02 admission receipt. A heterogeneous or sparse user survey can fail the backend's frozen requirement for at least 12 occupied spatial blocks and union units; the starter split is explicitly provisional. Full M02, field-data, visual-matrix, and release acceptance remain open.
