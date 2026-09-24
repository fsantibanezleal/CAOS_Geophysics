# Scientific recovery execution ledger

This is implementation evidence, not a deployment receipt. Production remains
0.03.000 until the complete replacement matrix passes numerical and browser gates.

## Potential-field and joint correction

- Seven recovery tests pass: physical derivatives and positive precision,
  uncertainty-sensitive inversions, final-state identity, repeatable conditional
  ensembles, rejection of perfect-data/failed-model results, fitted-GMM gradient,
  metre-scaled cross-gradients and an independent Choclo magnetic prism check.
- Seven existing CPU numerical/ingestion tests pass after the solver change.
- An eight-run potential/joint probe passed 30 forward/state/metric contracts.
  A separate final-preconditioner joint probe passed ten method contracts.
- The basin reference L2 model RMSE is 0.1744869 g/cm³ versus the 0.2141267
  zero-model baseline; the deployed release had 0.285882. This is an improvement,
  but the reconstructed correlation remains only 0.2831 and is labelled unresolved.
- Reduced-coverage magnetic dykes still have L2 withheld WRMS about 11.64.
  The failure remains visible rather than being classified by active-data fit.
- Shared-case PGI improves independent density RMSE by about 0.34%; cross-gradient
  coupling worsens it about 0.28%. These are not evidence of a general PGI advantage.
  The decoupled case is a declared petrophysical-prior mismatch control.
- Independent prior calibration and interval evidence are recorded in
  `spatial-calibration.json`: sixteen held-out models yield mean model/zero-baseline
  RMSE ratio 0.8543653. Conditional pointwise interval coverage is only 0.09881882.
  This exposes regularization bias and excludes any 95% posterior-coverage claim.

The probes, temporary arrays and images stay in ignored `data/experiments/`.
Source, original fixtures, final compact canonical results and release evidence
are the intended tracked deliverables. No raw/private data or virtual environment
is staged.
