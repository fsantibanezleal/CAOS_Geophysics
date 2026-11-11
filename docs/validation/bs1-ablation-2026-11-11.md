# Channel ablation replay

Date: 2026-11-11. This is a post-hoc, exploratory ablation for the frozen
geometry-normalized residual-learning study. It does not change the primary
experiment, its predeclared test, or its negative scientific verdict.

## Frozen execution

- Primary receipt SHA-256: `fe0697531923f24ed0dafc7fba1469eb1ba9b2459615fedce3336934b9370ae0`.
- Primary checkpoint SHA-256: `ff6ceb75c8e641c6e17dee911c99a3aa786fcdad4f290b86e93bfc32e809bbb5`.
- Ablation source SHA-256: `be3711425d4407f8772ff7c81656c0a20824601fcd9e18b847cbb9a0b6ccf81e`.
- Feature pipeline SHA-256: `aa85618783b014df20612e72ca0451f68e658e5dc12ebb4336d1f54259cf4b3e`.
- Forward operator SHA-256: `2b9ed95d3ba7b1b0f9f80167fa610640dc75c8a142dafb9f7f09791b96a1fd44`.
- Compute: NVIDIA GeForce RTX 4070 Laptop GPU; 40 epochs per trained ablation;
  29.32 seconds for both variants and scoring in the recorded run.
- Receipt SHA-256: `85838d36b5adb34329866ca25a55a468892e7baf21e63c4076673c79d5dfc5a6`.
- External run directory: `E:\_Datos\CAOS_Geophysics\m12-physics-ablation-v1-20261111-run3`.

The primary full-channel checkpoint was replayed without retraining. Two variants
were trained from the same frozen training/validation cohorts and seed: residual
channel only (`[1, 0]`) and coverage channel only (`[0, 1]`). Validation selected
epoch 40 for the residual-only model and epoch 3 for coverage-only. All three
models were scored on newly generated, disjoint seed namespaces, not on the
primary run's held-out records: 160 in-distribution, 80 family-shift, 80
acquisition-shift and 160 joint-shift cases. The classical regularization value
was selected on validation and matched the primary receipt.

## Fresh-seed held-out measurements

Ratios are learned divided by matched classical RMSE; values above one mean the
learned model has larger error. Flags use a separate 95th-percentile validation
threshold for each model. They are diagnostics, not calibrated probabilities and
not directly comparable between variants.

| Model | Cohort | n | Velocity RMSE ratio | Independent travel-time RMSE ratio | Threshold flags |
|---|---|---:|---:|---:|---:|
| Full channels | In-distribution | 160 | 2.8768 | 4.7305 | 8 |
| Full channels | Family shift | 80 | 2.2205 | 5.6156 | 80 |
| Full channels | Acquisition shift | 80 | 3.0796 | 5.4167 | 8 |
| Full channels | Joint shift | 160 | 2.2165 | 5.5967 | 160 |
| Residual only | In-distribution | 160 | 3.4195 | 4.9854 | 7 |
| Residual only | Family shift | 80 | 2.3442 | 5.8603 | 80 |
| Residual only | Acquisition shift | 80 | 3.4665 | 5.4569 | 8 |
| Residual only | Joint shift | 160 | 2.3269 | 5.7570 | 160 |
| Coverage only | In-distribution | 160 | 11.0984 | 27.7105 | 8 |
| Coverage only | Family shift | 80 | 3.6419 | 12.8681 | 22 |
| Coverage only | Acquisition shift | 80 | 10.9868 | 28.6354 | 6 |
| Coverage only | Joint shift | 160 | 3.5966 | 12.7651 | 51 |

The coverage-only model remains close to its reference velocity on validation and
performs substantially worse on every held-out error metric. Removing coverage
does not rescue the full model: residual-only errors also exceed the matched
classical baseline in every cohort. The primary negative result therefore has a
more specific failure diagnosis: coverage alone carries insufficient structural
information, while the learned residual channel and its combination with coverage
still do not outperform the classical inverse under these shifts.

## Verification and limits

The frozen replay command completed on CPU:

```powershell
python scripts/run_m12_physics_ablation.py `
  --output E:\_Datos\CAOS_Geophysics\m12-physics-ablation-v1-20261111-run3 `
  --primary E:\_Datos\CAOS_Geophysics\m12-physics-v2-20261111-run1 --verify
```

It regenerated all fresh cohort manifests, reloaded all three hash-checked
checkpoints, and matched aggregate and per-record velocity/travel-time errors and
threshold flags within the declared `rtol=1e-5`, `atol=1e-4` cross-device rule.
The training run and CPU replay use the same committed script and source hashes.

This is a single-seed ablation, with known synthetic families, a 16 by 16 grid,
straight-ray training physics and a bilinear synthetic scoring operator. It has no
field-data evidence, no independent geological-family discovery, and no repeated
training-seed uncertainty. Because it was designed after inspection of the primary
held-out outcome, it is exploratory and cannot be presented as a confirmatory
rescue, a novelty claim or evidence of field generalization. A manuscript must
label that boundary and retain the original failed hypothesis.
