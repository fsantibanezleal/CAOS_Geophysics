# M12 v1.1 calibration-threshold reconciliation

**Date:** 2026-10-30

**Scope:** Correct the invalid forward-threshold flags in the immutable v1.1 result using its retained per-record RMSE values. No model training or original receipt modification.

## Source and method

- Source protocol: `m12-nullspace-residual/v1.1`
- Source receipt SHA-256: `30df0c2ad495bd850dda602b1c96725be8290dd086119fb3e8e75355fe9dea22`
- Derived JSON SHA-256: `180267dcd644446fbbf430158eae062d3c5eb987389b5e03da35f37f6211505e`
- Threshold: **1.0649004873 ms**, NumPy linear 95th percentile of the 160-case calibration learned-oracle errors.
- Rule: flag a case only when its retained learned-oracle RMSE is strictly greater than that frozen calibration threshold.

The script validates the full non-fixture receipt, declared/per-record counts, unique IDs, and finite nonnegative errors before writing a new output. The original receipt is read-only and its saved false flags are not treated as evidence.

## Recomputed synthetic cohort flags

| Cohort | n | Exceedances | Rate |
|---|---:|---:|---:|
| Calibration | 160 | 8 | 5.000% |
| ID test | 160 | 7 | 4.375% |
| Family only | 80 | 80 | 100.000% |
| Acquisition only | 80 | 3 | 3.750% |
| Joint OOD | 160 | 160 | 100.000% |

The descriptive ID specificity is 95.625%; joint-OOD sensitivity is 100.000%. They describe these fixed synthetic cohorts only. They are not calibrated probabilities, a field detector, or evidence of geological transfer. The paired RMSE ratios and the original scientific status are unchanged; the status remains **not scientifically accepted**.

## Reproduction

```powershell
.\.venv-pipeline\Scripts\python.exe -m pytest tests\learning\test_m12_threshold_reconciliation.py -q
.\.venv-pipeline\Scripts\python.exe scripts\reconcile_m12_nullspace_threshold.py `
  --receipt data\derived\v2\models\m12-nullspace-v1_1\receipt.json `
  --output <new-output-path>
```

The generated JSON is committed at `data/derived/v2/models/m12-nullspace-v1_1/threshold-reconciliation.json`.
