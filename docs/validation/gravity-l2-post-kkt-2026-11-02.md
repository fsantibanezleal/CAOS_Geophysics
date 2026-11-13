# Gravity L2 locked matrix after scalar-bound KKT fix : 2026-11-02

## Reproduction and scope

The corrected source was exercised with the full frozen six-family by four-condition calibration and held-out evaluation. No case, seed, threshold, or solver limit was changed. Run command:

```powershell
$env:OPENBLAS_NUM_THREADS='1'; $env:OMP_NUM_THREADS='1'; $env:MKL_NUM_THREADS='1'
.\.venv-pipeline\Scripts\python.exe -m pytest tests/numerics/test_gravity_l2_selection.py::test_complete_locked_l2_control_matrix -q --junitxml E:\_Datos\CAOS_Geophysics\validation\gravity-l2-post-kkt-20261102\locked24-current-source.xml
.\.venv-pipeline\Scripts\python.exe scripts/validate_gravity_l2_matrix.py --junit E:\_Datos\CAOS_Geophysics\validation\gravity-l2-post-kkt-20261102\locked24-current-source.xml
```

Outcome: **24 passed, zero failed, zero errors, zero skipped**. Pytest emitted 24 known warnings because `record_property` is incompatible with the configured `xunit2` family; the required properties are present and parsed by the independent receipt validator. Recorded case time sums to 7,896.810 seconds; total wall time was about 2 hours 8 minutes.

Receipt SHA-256: `424c88e1e57532fa84094bd49a25048861398cf0bb5af027fbcc5bf5dd17f8a7`.
Validator JSON SHA-256: `1ea15532da8526e84b51c0dff1c4b4424726a98aa66b6312239405b7e3537fc9`.
Validator confirms 24 unique cell IDs, eight candidates and three folds per cell, 24 selected workflows, and finite held-out WRMS in all cells.

## Results by condition

| Condition | Interpretation declared by the test | Cells | Held-out WRMS range | Model-error ratio >1 | Result |
|---:|---|---:|---:|---:|---|
| 0 | Independent diagonal Gaussian noise | 6 | 0.942–1.233 sigma | 0/5 defined | within declared noise |
| 1 | Correlated Gaussian noise | 6 | 0.901–1.220 sigma | 0/5 defined | within declared noise |
| 2 | Declared station exclusion mask | 6 | 0.818–1.274 sigma | 0/5 defined | within declared noise |
| 3 | Deliberately unmodelled spatial/impulsive nuisance | 6 | 2.613–2.957 sigma | 1/5 defined | all six flagged poor |

The F4 cases define no nonzero truth model, so their model-error ratios are intentionally absent. Candidate-fold failures remain visible in the raw JUnit outcomes; they were not removed or retried. Every cell selected a beta and completed the separate final refit/evaluation path.

## Source identity and limits

- Checkout base revision: `f0ec2fc37fdae1f0c1c7d40b6cae386a85d7e6ac`; working tree was already dirty.
- `data-pipeline/gravity_l2.py`: `fc6fd9216edd43c02b83fddedca007a782bc627073a9d08da069d29f75d4d016`.
- `tests/numerics/test_gravity_l2_selection.py`: `f6557c33df18599ec8d511b9656a67456d1434ff84430ea4cf87b86e1bc82028`.
- `scripts/validate_gravity_l2_matrix.py`: `5d0a077d4b93a9c73191c0001ee519d0a4cfc5a3bce674117a36888e6273ba0c`.

The rerun establishes reproducible execution of this synthetic locked matrix on these exact source bytes. It is not an independent review, field-data qualification, a claim of unique density recovery, full M02/IRLS acceptance, actual-host admission, or product release acceptance. The convergence gate remains open pending the separately required review and other method/product gates.
