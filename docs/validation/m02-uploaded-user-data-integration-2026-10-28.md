# Uploaded M02 calculation and independent result checks

Validation date: 2026-10-28. Source commit: `0f01b0c` (`test: preserve nonclaims in uploaded gravity results`), including the independent-forward assertions from `2db75e7`.

## Executed path

The API integration test `tests/api/test_gravity_l2_upload.py::test_uploaded_user_survey_runs_isolated_inverse_and_parameter_changes_predictions` passed once in the Windows `.venv-pipeline`. It exercises authenticated account and project creation, original gravity CSV upload, dataset parsing, eligibility, queueing, the isolated M02 ordinary weighted-L2 child, persisted result fetch and export round-trip. The solve was run twice with different declared fixed background values. The original upload SHA-256 and bytes remained unchanged; the output did not claim observed field geology as synthetic truth.

## Independent numerical assertions

For each successful solve, the test requires a selected calibration, a converged final solve, and a finite one-cell density inside its declared bounds. It then evaluates that returned density at every uploaded receiver with Choclo's prism gravity formula and the job's fixed background, comparing the independent values with all 144 exported predictions at `rtol=1e-7`, `atol=1e-10`.

On the sealed outer rows, the test verifies exported predictions equal the corresponding full prediction rows, residuals equal observed minus predicted values, standardized residuals equal residual divided by the declared 0.1 mGal standard deviation, and `phi_d`, WRMS and RMSE recompute from those arrays. Changing the fixed background changes both the immutable request identity and prediction hash. The two runs retain `field_truth=null` and `model_accuracy=null`; the test does not use the authored generator model to score field geology.

The exported result bundle round-trips with the source hash, dataset, units and result values intact. This is evidence for this authored one-cell M02 path only. It does not accept broader M02 families, M01-M13, field eligibility, actual VPS admission or the replacement release.
