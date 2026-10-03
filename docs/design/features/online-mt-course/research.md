# Source-to-course research, 2026-10-03

## Existing primary evidence inspected before course code

Approved product SDD; scientific implementation/review/recovery dossiers; MT recovery, independent validation and measured C15 admission chapters; current strict EDI and electromagnetic source; PR100 compute/contract at7b69404; existing Research page, phase course/diagram, citation registry, shell0.6.8 types/README/styles and frontend tests. Governance: entrypoint, ADR0011/12/16/17/56/57/58/69/71/74/75 and quality/SDD practice. Existing C15 and cl061 results are QC-only and cannot supply an eligible field inverse.

## Primary references and decisions

- [SciPy1.15.2 least_squares](https://docs.scipy.org/doc/scipy-1.15.2/reference/generated/scipy.optimize.least_squares.html), opened2026-10-03: cost is half the residual squared norm, bounded TRF differs from LM, default numerical Jacobian is2-point and nfev excludes differentiation calls. Course derives the exact implemented residual; no analytic Jacobian claim.
- [EMTF-FCU source notes](https://github.com/magnetotellurics/EMTF-FCU), opened2026-10-03: complex variance differs from single real-component variance; missing EDI covariance prevents arbitrary uncertainty rerotation. The parser's provenance and strict choices are the product-specific authority, not assumptions that every EDI has those conventions.
- [Caldwell, Bibby and Brown2004](https://doi.org/10.1111/j.1365-246X.2004.02281.x), publisher page inspected2026-10-03: phase tensor diagnoses structure under its assumptions. Small skew/provider label does not override full complex tensor incompatibility, static shift or missing covariance. Use as a distinction, not an implemented phase-tensor filter.
- [USGS Clear Lake release](https://www.usgs.gov/data/magnetotelluric-data-clear-lake-region-northern-california), opened2026-10-03, DOI10.5066/P14KAQ3M and [EarthScope transfer-function release](https://doi.org/10.17611/DP/EMTF/GMEG/Clearlake): measured EDI is transfer-function data, not layer truth. Original cl061 receipt is16411bytes/SHA90c5c96cd69d6d29c866a768097cb3b38bc20e8b9c143e24bf10b2d253261e83. Declared positive sign, supplied native-unit/complex-variance interpretation and full-frequency failures remain explicit.
- [Heagy et al.2017](https://doi.org/10.1016/j.cageo.2017.06.018), verified in the existing research: electromagnetic forward/inverse framework reference. The actual recurrence/estimator constants are taken from [reviewed scientific implementation](https://github.com/fsantibanezleal/CAOS_Geophysics/blob/7b69404/data-pipeline/electromagnetics.py) and [online selection source](https://github.com/fsantibanezleal/CAOS_Geophysics/blob/7b69404/app/mt_compute.py), not attributed to a paper as if identical.

## Adversarial distinctions

Marginal sigma is not VAR, complex RMS or resistivity error. Necessary tensor QC is not dimensionality proof. Index Tikhonov is not a depth derivative. Successful optimizer termination is not model recovery. Data-only central sensitivity is not the optimizer Jacobian. Frozen frequency holdout is not independent-station validation. Correct fixed-h recovery does not validate unknown h. Conditional Gaussian percentile intervals are not Bayesian geology or empirically calibrated field coverage. Course replay controls are not server job submission, and a course build is not actual-host admission.
