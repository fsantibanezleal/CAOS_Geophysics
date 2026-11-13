# Current-source CPU2 original24 calibration matrix

## Protocol and receipts

The complete frozen six-family by four-condition matrix was recalibrated with the approved CPU2 terminal certificate source. Each scenario used the fixed eight-beta grid, three development folds, independent sealed outer observations and the unchanged per-fit/update limits. The 23 remaining cases ran in one sequential pytest process; the family-0/condition-0 case was run immediately beforehand. Across the two invocations, all 24 scenario tests passed: 24 selected calibration workflows, 576 candidate-fold fits and 24 selected final refits. Solver records retained 376 converged and 224 nonconverged results; all nonconverged candidate/fold records stayed in the receipts and were not treated as selected fits.

The 23-case invocation passed in 10,720.64 seconds. The first case passed in 221.73 seconds. Summed pytest duration was 10,942.37 seconds (3 h 2 m 22.37 s); this is local CPU evidence, not VPS capacity evidence. Every case independently checked the frozen archive identity, outer evaluation, residual/metric calculation and physical forward prediction. Each selected workflow refers to the exact selected beta index shown below.

| Synthetic family | Condition 0: diagonal noise | Condition 1: correlated noise | Condition 2: deterministic gaps | Condition 3: unmodelled trend and outliers |
| ---: | --- | --- | --- | --- |
| 0 | β 5; WRMS 1.22; RMSE ratio 0.78 | β 6; 1.14; 0.52 | β 6; 1.28; 0.51 | β 6; 2.87; 0.92 |
| 1 | β 6; 0.97; 0.85 | β 6; 1.20; 0.86 | β 6; 1.04; 0.87 | β 6; 2.60; 1.06 |
| 2 | β 6; 1.16; 0.64 | β 6; 1.14; 0.61 | β 7; 0.90; 0.63 | β 6; 2.92; 0.96 |
| 3 | β 5; 0.97; 0.37 | β 5; 1.09; 0.45 | β 6; 1.06; 0.49 | β 6; 2.64; 0.65 |
| 4 | β 7; 1.15; n/a | β 7; 1.16; n/a | β 7; 0.96; n/a | β 7; 2.96; n/a |
| 5 | β 6; 1.11; 0.84 | β 6; 0.90; 0.88 | β 5; 0.81; 0.91 | β 7; 2.60; 0.97 |

β values in this table are the selected candidate indices, not physical regularization values. The density truth for family 4 is identically zero, so a relative model-error ratio has a zero denominator and is correctly unavailable. Condition 1 uses the predeclared spatially correlated covariance. Condition 2 excludes every seventh station under explicit gap masks. Condition 3 adds an unmodelled linear trend and deterministic outliers.

## Interpretation and limitations

All six condition-3 cases report WRMS above 2 because the control deliberately adds signal not represented by the assumed noise model. The frozen method design defines `WRMS <= 2` versus `> 2` as a descriptive `prediction_quality` label, explicitly **not** a scientific acceptance threshold. These values remain visible as poor under declared noise; they do not get reclassified as successful predictive fit. The predeclared acceptance assertions for family 0 and 1 under conditions 0 and 1 passed, including WRMS `<= 2` and truth-relative model RMSE `< 1`.

This matrix establishes current-source software behavior and synthetic calibration/evaluation across the frozen controls only. It does not establish field accuracy, geologic truth, Clear Lake eligibility, complete M02/product acceptance, user-data/API/browser acceptance, resource admission, host capacity, or release readiness. The convergence ledger still has one failed requirement and 15 unresolved requirements. Do not promote this result to a field or product claim.

## External evidence identities

All 48 compressed calibration and outer-evaluation archives (24 pairs) and the machine-readable 24-case summary are kept outside the repository at `E:\_worktrees\validation\geophysics\cpu2-matrix\`. The manifest catalogs every archive name, byte size and SHA-256; it has SHA-256 `21351BFE233EF2A4E6F84A2A629F473D4512B11BE51C9D469ACADA02394FF2E6`.

| Receipt | Location | SHA-256 |
| --- | --- | --- |
| Family 0 / condition 0 JUnit | `E:\_worktrees\validation\geophysics\junit-cpu2-family0-condition0-2026-11-13.xml` | `92A47DE7DB04C49E8C9D49B971FD5D7497BF6EE3AE82017F959C536B3F72C177` |
| Remaining 23 JUnit | `E:\_worktrees\validation\geophysics\junit-cpu2-remaining23-2026-11-13.xml` | `1117F8C69F3C02B51DA6A4AFC2D59D17C82E488568A21B4FBEC9022B5E05393D` |
| Six focused frozen-fold JUnit | `E:\_worktrees\validation\geophysics\junit-cpu2-six-folds-2026-11-13.xml` | `6D0C54CF3252E349D52C1E763C31E09A3AA138725A79D23EBA846D6F13D10270` |

The runtime epoch is `m02-survey-irls-cpu-2-terminal-certificate-exact-q-replay-legacy-init-1`; the engine source-inventory SHA-256 is `27220b385b6ab936459a99d48f731a8a5529384981dd12c2a730555f4fca4d93`. The machine-readable summary includes each request/result identity, selected index, metrics, solver-record counts and the full archive catalog.

## Reproduction

Use `GEOPHYSICS_M02_IRLS_CORRECTED_DATA_ROOT` and `GEOPHYSICS_M02_IRLS_CORRECTED_TEMP_ROOT` pointing to the retained external directories. Run the same 24 `test_original24_corrected_science[family-condition]` node IDs in `tests/numerics/test_gravity_irls_corrected_matrix.py` with the single-thread environment shown in the linked [family-0/condition-0 reproduction](cpu2-family0-condition0-calibration-2026-11-13.md). Exact compatible archives are decoded and independently checked; incompatible receipts are never reused.
