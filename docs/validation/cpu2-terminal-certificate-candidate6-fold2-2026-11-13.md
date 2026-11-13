# CPU2 terminal certificate: frozen candidate 6, fold 2

## Result and boundary

The approved CPU2 terminal certificate was exercised on the deterministic, locked family-0 / condition-0 synthetic gravity control, beta candidate 6 (`beta_candidate = 100`), fold 2. The solve terminated `converged / irls_fixed_point_certificate` after the unchanged 20 weight updates, 77 total iterations, and 3.781 seconds. Its final native inner solve took zero iterations and retained the exact same model state.

This is one source-bound synthetic fold. It does not establish beta selection, a successful full calibration, an outer-test result, field eligibility, or complete M02 acceptance. The full candidate/fold matrix and the wider product gates remain open.

## Why this terminal state is certifiable

The first of the last three recorded weight changes is `1.0348163696477964e-6`, which remains above the existing `1e-6` transition rule. The following two transitions are exact no-ops. The certificate does not change that threshold or count an extra update. It checks the terminal state directly: the saved model, final inner model, and canonical model are exactly equal; canonical and adopted sparse weights are exactly equal; and the projected KKT infinity norm is `3.765876499528531e-13`.

The test independently reconstructs the final SimPEG `Sparse` regularizer from the admitted request, reapplies the recorded thresholds, recomputes every IRLS weight array, and evaluates the fixed-stage gradient and box-projected KKT residual. The smallest diagonal entry of the smallness Hessian is `2,000,000`; multiplied by the positive engine beta (`7,200`), this gives a strict-convexity lower bound of `14,400,000,000` for the fixed weighted quadratic. The independent values and all weight hashes match the persisted certificate exactly.

## Reproduction

Run from the repository root with the pipeline environment and native thread pools fixed before Python imports NumPy or SciPy:

```powershell
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
$env:NUMEXPR_NUM_THREADS = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
& .\.venv-pipeline\Scripts\python.exe -m pytest `
  tests/numerics/test_gravity_irls_corrected_matrix.py::test_cpu2_terminal_certificate_frozen_candidate6_fold2 `
  -q -o addopts='' -o junit_family=legacy
```

The run passed 1 test in 5.55 seconds with CPython 3.12.10, NumPy 2.2.6, SciPy 1.15.2, Choclo 0.3.2, and SimPEG 0.25.2. The retained external JUnit file `junit-final.xml` has SHA-256 `658dfce411f9b8022c77da1ba15e5dd62fb133e29466b5f14fdf754c699703f7`.

## Frozen identities

| Item | SHA-256 |
| --- | --- |
| Request | `55f22d00f261b094736708bc0dae40581cdd4b7f34ee9ac699281964c72cb321` |
| CPU2 engine source inventory | `27220b385b6ab936459a99d48f731a8a5529384981dd12c2a730555f4fca4d93` |
| Terminal model | `b98fccfb948b49cd97a8a21d285abc10b6bc6b45d4f2a4cf20eb3f4bf81d4eb2` |
| Test source | `b0a0a34e49e931a1d640b37322190b6422cb6181600c0176aef759cff0a573c4` |
| CPU2 engine source | `d5a6a80c75b22d3fd9b01f251d40443585b4c9cd24e5b27fa1d72a037bdc4b01` |
| Workflow source | `c9538fdf7aad5153c29cc319a65398489bd0c9b20b85b6598ce0bdf40927c6ba` |
| L2 builder source | `fc6fd9216edd43c02b83fddedca007a782bc627073a9d08da069d29f75d4d016` |

The JUnit is retained in the operator's external validation store, not committed to the product repository. This validation note reports the single-fold terminal proof only; it does not upgrade the whole-method or release verdict.
