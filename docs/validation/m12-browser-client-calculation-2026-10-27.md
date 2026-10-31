# M12 browser-side first-arrival calculation: 2026-10-27

## Implemented scope

The public `?instrument=velocity-local` workbench now has two separate paths: calculate a supplied `geophysics.velocity-user-data/v1` request in-browser, or inspect an existing verified Python generation. The browser path validates the closed request contract (512 KiB, 8–2,048 rays, fixed local x–z-down frame, metres/seconds/m/s, unique IDs, explicit uncertainty and regularization bounds), then runs in a dedicated Web Worker. It does not upload the input, invoke an API, or claim field acceptance.

The worker implements the same fixed straight-ray cell-crossing operator, reference slowness, weighted normal equations, first-difference Gram penalty, diagonal stabilizer, Cholesky solve, explicit slowness clipping, predicted cell-crossing times and independent eight-samples-per-cell bilinear quadrature check as `data-pipeline/velocity_user_data.py` and `data-pipeline/velocity_validation.py`. The user can change λ before solving; the selected value is applied to the first-difference penalty. The UI shows velocity, accumulated path-length coverage, observed/predicted times, signed residuals and normalized residuals. Its export records distinct SHA-256 digests for the original file bytes and the normalized request actually solved, so parameter changes do not erase input provenance. Coverage is not resolution or uncertainty.

## Numerical parity control

`frontend/src/test/velocity-browser.test.ts` builds the 128-ray authored acquisition A, a known layered control, and deterministic 0.4 ms sinusoidal perturbations with 1 ms declared sigma. Python product reference values were computed from `velocity_user_data.calculate` with lambda 100.

| Quantity | Python product reference | Browser | Check
|---|---:|---:|---|
| Data WRMS | 0.022635248821506103 | matched to 7 decimal places | pass
| Data chi-square | 0.06558137461907115 | matched to 7 decimal places | pass
| Cell/bilinear travel-time RMSE (s) | 0.00022863825058567995 | matched to 7 decimal places | pass
| Velocity, cell [0,0] (m/s) | 2009.7666832065106 | matched to 4 decimal places | pass
| Velocity, cell [5,7] (m/s) | 2097.9578158758945 | matched to 4 decimal places | pass
| Velocity, cell [15,15] (m/s) | 2267.8933196540747 | matched to 4 decimal places | pass
| First predicted travel time (s) | 0.3948998396460718 | matched to 7 decimal places | pass

The same tests reject duplicate-key JSON, an invalid coordinate and fewer than eight rays. This control verifies code parity for one synthetic acquisition. Observations and inverse share a straight-ray operator, so this is not an independent physics validation or an estimate of generalization. No CNN is run in the browser; retained learned M12 benchmarks fail against their matched classical solver.

## UI and execution evidence

- `npm run build`: passed, including TypeScript and Vite production build. Vite retains the repository's existing >500 kB chunk advisory.
- `npm test -- --run src/test/velocity-browser.test.ts src/test/velocity-local.test.ts`: 19 passed. The added test verifies λ changes the recovered array and predictions and rejects values outside the solver bounds.
- `npm exec playwright test -- --config playwright.velocity-calculator.config.ts --timeout=45000`: passed in Chromium at 1440×960 and 390×844. Both viewports selected the supplied request, ran the worker at λ=25 and 1,000, exported the result with source and solved-request hashes, showed changed predictions and velocity, produced no page errors or API requests, and had no document-width overflow. Screenshots and JSON exports are outside the repository under `E:\_Temp\caos-geophysics-velocity-lambda\run-01\evidence`.
- Full frontend suite: 42 files passed, 2 skipped, 7 failed (36 fixture-gated tests). Failures require original custody, native-joint, actual magnetic, or retained model-extraction fixtures not present in this checkout; they are unrelated to this change and are not reclassified as passes.

## Scientific limits

The solve assumes fixed straight rays and fixed source timing on an 800 m × 800 m, 16 × 16 grid. It does not estimate origin time, refraction, bent rays, anisotropy or wave propagation. The unconstrained normal-equation solution is clipped in slowness to 1/4000–1/1400 s/m afterward; clipping is not a certified box-constrained optimum. WRMS uses the submitted sigma and is not truth error. A result generated in the browser uses the distinct `geophysics.velocity-browser-result/v1` schema and is not accepted by the Python-generation verifier. The local Python route remains available when its independently verified result/manifest bundle or optional experimental checkpoint workflow is needed.
