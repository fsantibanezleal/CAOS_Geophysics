# M12 paired projection counterfactual

This is a post-hoc ablation of the frozen M12 null-space v1.1 synthetic study.
It evaluates the raw residual-v3.1 CNN and its null-space-projected prediction
on the same regenerated cases, using the existing calibration-selected
`alpha=1.0` and `lambda=100`. It does not change the frozen receipt, model,
splits, parameter selection, or original scientific verdict.

The result JSON retains each case ID, family, acquisition, velocity RMSE,
independent bilinear-oracle travel-time RMSE, all three model errors (raw CNN,
projected CNN, and straight-ray L2), the exact split-manifest hashes, the
checkpoint and receipt hashes, source hashes, and paired bootstrap intervals.
Both the raw and projected scores are recomputed from the same checkpoint and
inputs; the projected score is checked against the original v1.1 receipt before
the new analysis is written.

## Same-case projected-to-raw CNN error ratios

Ratios are ratios of mean per-case RMSE; values below one favor the projected
candidate. Intervals are 95% paired case-bootstrap percentile intervals with
20,000 draws and NumPy PCG64. “Lower” counts cases where projection reduced the
per-case error. Intervals describe resampling within each fixed cohort only.

| Frozen cohort | n | Velocity ratio [95% interval] | Velocity lower | Oracle-time ratio [95% interval] | Oracle-time lower |
| --- | ---: | ---: | ---: | ---: | ---: |
| In distribution | 160 | 1.9583 [1.9070, 2.0113] | 0 | 0.9290 [0.9093, 0.9495] | 113 |
| Family shift | 80 | 0.9143 [0.9060, 0.9225] | 76 | 0.7013 [0.6830, 0.7207] | 80 |
| Acquisition shift | 80 | 1.8798 [1.8123, 1.9502] | 0 | 0.9146 [0.8900, 0.9400] | 57 |
| Joint family and acquisition shift | 160 | 0.9177 [0.9123, 0.9230] | 158 | 0.7080 [0.6954, 0.7213] | 160 |

The paired intervention exposes a trade-off hidden by projected-to-L2 ratios:
projection lowers independent travel-time error in every cohort, but it nearly
doubles velocity RMSE relative to the raw CNN on ID and acquisition-only cases.
It lowers both metrics relative to the raw CNN on family-only and joint shift.
This is evidence about the fixed checkpoint, generator, four cohorts and
discretized operators. It is not evidence of field accuracy, geological
recovery, a general projection benefit, or superiority to state-of-the-art
tomography.

## Reproduction

From the repository root, run the analysis into a new directory outside every
Git checkout:

```powershell
.venv-pipeline\Scripts\python.exe scripts\analyze_m12_projection_counterfactual.py `
  --output E:\_Datos\CAOS_Geophysics\experiments\m12-projection-counterfactual-<new-id>
```

The script refuses output inside a checkout or into an existing directory. It
uses the committed M12 checkpoint package at
`data/derived/v2/models/m12-current-reproduction-20261106/` and verifies the
source receipts and all four regenerated case manifests before scoring.
