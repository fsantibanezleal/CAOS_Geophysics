# M12 physics-v2 current-source run : 2026-11-06

## Scope

This records a fresh execution of the frozen 40-epoch physics-v2 protocol and
its independent CPU verifier. It uses fixed synthetic cohorts and is a
reproducibility and comparator result, not a new holdout, field validation,
M12 acceptance, or product release acceptance.

Source checkout revision: `0f4f08594b20f45f6de552ef256f45a74681a287`.
The CUDA training run used the NVIDIA GeForce RTX 4070 Laptop GPU. The verifier
regenerated each non-training cohort on CPU and checked source identity,
partition manifests, per-case and aggregate metrics, and the frozen verdict.
Both commands exited zero:

```powershell
.venv-pipeline\Scripts\python.exe scripts\run_m12_velocity.py --device cuda --protocol physics-v2 --output E:\_Models\CAOS_Geophysics\m12-physics-v2-run-2026-11-06
.venv-pipeline\Scripts\python.exe scripts\run_m12_velocity.py --verify --protocol physics-v2 --output E:\_Models\CAOS_Geophysics\m12-physics-v2-run-2026-11-06
```

## Immutable run identity

The training receipt and checkpoint remain outside the repository at the path
above. Receipt runtime: Python 3.12.10, NumPy 2.2.6, SciPy 1.15.2, and Torch
2.14.0+cu126. Training selected epoch 40 and took 22.542 seconds.

| Artifact or source | SHA-256 |
| --- | --- |
| `receipt.json` | `d0b7905b80a184f01a761bb80430e7b6557fcc9dc00a88326f57c9bbdcf5975d` |
| `m12-physics.npz` checkpoint | `b7d606a04fe66286490b62b5ddae89e9c4aca882c15afe56524f21f0e511beaf` |
| `velocity_physics_refinement.py` | `aa85618783b014df20612e72ca0451f68e658e5dc12ebb4336d1f54259cf4b3e` |
| `velocity_validation.py` operator | `2b9ed95d3ba7b1b0f9f80167fa610640dc75c8a142dafb9f7f09791b96a1fd44` |

Seed: `77213`. The run contains 800 training, 160 validation, 160 ID,
80 family-only, 80 acquisition-only, and 160 joint-OOD records. Cohort
manifests and noisy-input hashes are retained in the receipt.

## Held-out results

Ratios are learned-to-classical mean RMSE; a value below one favors the learned
method. Oracle travel time is scored independently from the fitted model.

| Cohort | n | Velocity RMSE ratio | Oracle-time RMSE ratio | Forward-threshold exceedances |
| --- | ---: | ---: | ---: | ---: |
| ID test | 160 | 3.0502 | 5.1281 | 12 |
| Family-only OOD | 80 | 2.1735 | 5.7405 | 80 |
| Acquisition-only OOD | 80 | 3.1075 | 5.4266 | 7 |
| Joint OOD | 160 | 2.1896 | 5.5954 | 160 |

The frozen verdict is `failed-held-out-comparator`. Both required joint-OOD
ratios are greater than one, and all 160 joint-OOD cases exceed the recorded
forward threshold. The negative result is retained without retuning on these
test cohorts. It does not establish field behavior or support a learned-method
advantage; M12 and product scientific acceptance remain open.
