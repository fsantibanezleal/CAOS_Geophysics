# CPU2 family-0 / condition-0 calibration

## Result

The complete frozen original24 calibration and independent outer evaluation passed for the synthetic family-0 / condition-0 control. The run used the exact current CPU2 runtime epoch and request SHA-256 `55f22d00f261b094736708bc0dae40581cdd4b7f34ee9ac699281964c72cb321`.

- Beta selection: selected index 5, beta `10`.
- Held-out normalized weighted RMS: `1.2211798942675418` (gate: `<=2`).
- Model RMSE relative to the known synthetic density truth: `0.7829055221538097` (gate: `<1`).
- Calibration plus independent evaluation: 24 candidate/fold fits, 220.015 seconds total; full pytest case 221.73 seconds.
- 16 of 24 fits converged. Eight low-beta fits retained non-converged terminal outcomes (`line_search_failed` or `irls_iteration_cap`) and were not silently repaired or treated as eligible. The configured selector excluded them and still selected a candidate with all required folds converged.
- Independent outer forward evaluation, metrics, and archived identities matched the test oracle. Pytest: 1 passed, 0 failed/errors/skips.

The calibration and outer-evaluation archive bytes are retained outside the repository in `E:\_worktrees\validation\geophysics\cpu2-matrix\data`:

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `corrected-family0-condition0-89bcf62df7d11b72.gza` | 9,926,866 | `C4CFF4D1EF99D5EB3596F97CC2646F14EDBDA583FFEE7D294F6EFDC0D5B4B0FD` |
| `corrected-outer-family0-condition0-4c0e8f0ff723-3793de2c08a0-8730d699c2a8.gza` | 9,932,962 | `AE60BCCDD30809D710DC3FC96358878EDBF697691CF0606E2C58AAEE06099C4E` |

The retained JUnit receipt is outside the repository at `E:\_worktrees\validation\geophysics\junit-cpu2-family0-condition0-2026-11-13.xml`, SHA-256 `92A47DE7DB04C49E8C9D49B971FD5D7497BF6EE3AE82017F959C536B3F72C177`.

## Reproduction

Set `GEOPHYSICS_M02_IRLS_CORRECTED_DATA_ROOT` and `GEOPHYSICS_M02_IRLS_CORRECTED_TEMP_ROOT` to operator-controlled external directories. Then, from the product root, constrain native numerical thread pools before Python imports NumPy/SciPy and run:

```powershell
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
$env:NUMEXPR_NUM_THREADS = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
& .\.venv-pipeline\Scripts\python.exe -m pytest `
  'tests/numerics/test_gravity_irls_corrected_matrix.py::test_original24_corrected_science[0-0]' `
  -q -o addopts='' -o junit_family=legacy
```

## Scope limit

This report records the first frozen synthetic control and its independent held-out evaluation. The subsequent complete 24-scenario current-source CPU2 replay is documented in the [full matrix report](cpu2-original24-calibration-matrix-2026-11-13.md). Neither report establishes field-data accuracy or eligibility, the complete M02 gate, API/browser/host acceptance, or release readiness. In particular, these synthetic controls do not qualify the separate Clear Lake field case; it remains QC-only under the approved product definition.
