# User supplied first arrivals: bounded QP correction

Date: 2026-11-06. Scope: the local Python processor, its result verifier,
browser first-arrival calculator, result schema readers and focused controls.
This record covers one numerical method implementation; it is not a field or
product acceptance.

## Corrected optimization

For the fixed straight-ray path matrix `A`, reference slowness `s0`, declared
standard deviations `sigma`, and `q = 1000 (s - s0)`, define
`B = A / (1000 sigma)` and `y = (t - A s0) / sigma`. The solver minimizes

`||B q - y||² + lambda ||D q||² + 0.01 ||q||²`

subject to `1000 (1/4000 - s0) <= q <= 1000 (1/1400 - s0)`.

The normal matrix is `H = B.T B + lambda D.T D + 0.01 I`; the positive ridge
makes this quadratic strictly convex, so it has a unique box-constrained
minimizer. The previous implementation solved the unconstrained system and
clipped slowness afterward. That clipped vector was generally not the
minimizer of the stated bounded problem. New Python output uses
`geophysics.velocity-result/v2`; browser output uses
`geophysics.velocity-browser-result/v2`. Both use a deterministic primal
active-set solve with face minimization and bound-multiplier release. Both
recompute projected KKT diagnostics from the returned velocity array. Python's
generation verifier independently reconstructs the normal system, bounds and
KKT residual before writing the success manifest.

The numerical gate is projected KKT relative residual `<= 1e-9`; the export
records its absolute and relative values, gate, active-bound cell count and
iteration count. This is a floating-point first-order optimality check for the
declared QP, not interval arithmetic, an independent physical forward model, or
field validation. The browser-side result inspector checks exact file hashes
and scalar consistency only; it does not replay the ray operator or optimizer.
Legacy Python v1 files remain inspectable under their historical
solve-then-clip contract and are not relabeled as bounded solutions.

## Independent checks

`tests/numerics/test_velocity_bounded_qp.py` compares the active-set solver
against SciPy `lsq_linear` on Cholesky-factored strictly convex quadratics,
including active lower and upper bounds and invalid-input rejection. The
user-data suite independently builds the neighbor-difference matrix and
compares both interior and physically active solutions with SciPy's bounded
least-squares oracle. A 2,048-ray export/reopen control exercises the upper
admission limit, and a legacy v1 control exercises backward inspection.

The browser suite checks an interior case and a 128-ray active-bound case
against the Python product result. The active-bound case reproduces 127 active
cells, 134 iterations, WRMS `17.276330634904177`, and selected velocities
`2064.8644568639766`, `2286.153461042268`, and `2081.4622948206534` m/s at
`[0,0]`, `[5,7]`, and `[15,15]`. The matching values establish parity for this
authored synthetic control only.

Validation run on current source:

- `.venv-pipeline/Scripts/python.exe -m pytest -p no:cacheprovider tests/numerics/test_velocity_bounded_qp.py tests/data/test_velocity_user_data.py -q`: 42 passed.
- `npm test -- --run src/test/velocity-browser.test.ts src/test/velocity-local.test.ts`: 23 passed.
- `npm run build`: successful; TypeScript and Vite production build completed. Vite reported the existing large-chunk advisory for chunks above 500 kB.
- `npm exec playwright test -- --config playwright.velocity-calculator.config.ts --timeout=45000`: 1 passed in desktop 1440×960 and phone 390×844 contexts; the browser displayed the KKT diagnostics, exported v2 results for two lambda values, preserved both source identities, and made no API requests.

## Remaining physical limits

The data contract still describes an 800 m by 800 m, 16 by 16 grid and fixed
straight rays. It does not estimate source time, ray bending, refraction,
anisotropy, elastic propagation, or a geological truth model. Data WRMS is
weighted fit to submitted arrivals, not model accuracy. This correction does
not close M09 field tomography, learned M12 acceptance, whole-method review,
user-data acceptance across modalities, host admission, visual acceptance, or
the product release gate. No VPS release was changed by this scoped validation.
