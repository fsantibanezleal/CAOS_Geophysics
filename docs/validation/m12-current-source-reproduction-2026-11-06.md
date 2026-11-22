# M12 current-source reproducibility replay : 2026-11-06

## Scope

This reruns the frozen residual-v3.1 and nullspace-v1.1 protocols from the
current checkout. The run is a reproducibility check of previously evaluated
synthetic cohorts, not a new independent holdout, new method selection, field
validation, or M12/product acceptance. No protocol, seed, threshold, model, or
acceptance rule was changed.

Source checkout revision: `7d395bed436334158d46ce3ccb5fd69265b0a352`.
Outputs are outside the repository at:

- `E:\_Datos\CAOS_Geophysics\experiments\m12-residual-v3.1-reproduction-20261106`
- `E:\_Datos\CAOS_Geophysics\experiments\m12-nullspace-v1_1-reproduction-20261106`

## Reproduction commands

From the repository root in PowerShell:

```powershell
.venv-pipeline\Scripts\python.exe scripts\run_m12_residual_v3.py --device cuda --output E:\_Datos\CAOS_Geophysics\experiments\m12-residual-v3.1-reproduction-20261106
.venv-pipeline\Scripts\python.exe scripts\run_m12_residual_v3.py --verify --output E:\_Datos\CAOS_Geophysics\experiments\m12-residual-v3.1-reproduction-20261106
.venv-pipeline\Scripts\python.exe scripts\run_m12_nullspace_v1_1.py --source-run E:\_Datos\CAOS_Geophysics\experiments\m12-residual-v3.1-reproduction-20261106 --output E:\_Datos\CAOS_Geophysics\experiments\m12-nullspace-v1_1-reproduction-20261106 --device cpu
.venv-pipeline\Scripts\python.exe scripts\run_m12_nullspace_v1_1.py --verify --output E:\_Datos\CAOS_Geophysics\experiments\m12-nullspace-v1_1-reproduction-20261106
```

Both independent verification commands exited zero. Residual-v3.1 regenerated
and scored five cohorts; nullspace-v1.1 regenerated and scored its four held-out
cohorts from the checkpoint and manifests copied into its own immutable output.

## Runtime and immutable output identity

Residual-v3.1 training used CUDA on an NVIDIA GeForce RTX 4070 Laptop GPU.
The receipt records Python 3.12.10, NumPy 2.2.6, SciPy 1.15.2, and Torch
2.14.0+cu126. The full held-out scoring and both independent verification
replays ran on CPU.

| Artifact | SHA-256 |
| --- | --- |
| Residual-v3.1 checkpoint, `m12-residual-v3.1.npz` | `0f7a8fc43a078ab4cb16016774d44b356ccb70d9c60e0f197506fd3f7a53ea03` |
| Residual-v3.1 receipt | `f6f52c544af1a86f07fc17c83296de2ac09e884058e2af1d72adeb3bb35bc1dc` |
| Nullspace-v1.1 copied source checkpoint | `0f7a8fc43a078ab4cb16016774d44b356ccb70d9c60e0f197506fd3f7a53ea03` |
| Nullspace-v1.1 copied training receipt | `f6f52c544af1a86f07fc17c83296de2ac09e884058e2af1d72adeb3bb35bc1dc` |
| Nullspace-v1.1 receipt | `0d4cd8c14e290b9cd17da387800dbe6cf7314729379d03221df8585b1243d880` |

Source hashes recorded in the receipts:

| Source | SHA-256 |
| --- | --- |
| `data-pipeline/velocity_residual_learning.py` | `d85b8bcea8218d7381fab20ad6ec0f66d127ddbaab74a8edc19d288e6d6d2681` |
| `data-pipeline/velocity_validation.py` | `2b9ed95d3ba7b1b0f9f80167fa610640dc75c8a142dafb9f7f09791b96a1fd44` |
| `data-pipeline/velocity_physics_refinement.py` | `aa85618783b014df20612e72ca0451f68e658e5dc12ebb4336d1f54259cf4b3e` |
| `data-pipeline/velocity_nullspace_refinement_v11.py` | `e9486a3c823e47ef462970cf06a28fcfbb5acc7418fc9f686df0c2b1fe6283f9` |
| `scripts/run_m12_nullspace_v1_1.py` | `4dc950573f8667936d4e74c926e7ae3e7df98474821d7af4e234f243609b633d` |

## Results

Ratios are learned-to-classical means within each protocol; values below one
favor the learned or refined result. The protocols use different fixed seed
cohorts, so rows across versions are not paired comparisons.

| Protocol and cohort | n | Velocity RMSE ratio | Independent oracle-time RMSE ratio |
| --- | ---: | ---: | ---: |
| Residual-v3.1 ID | 160 | 0.4127 | 1.0690 |
| Residual-v3.1 family-only | 80 | 1.0474 | 1.4043 |
| Residual-v3.1 acquisition-only | 80 | 0.4168 | 1.0841 |
| Residual-v3.1 joint OOD | 160 | 1.0437 | 1.3961 |
| Nullspace-v1.1 ID | 160 | 0.8035 | 0.9841 |
| Nullspace-v1.1 family-only | 80 | 0.9718 | 0.9962 |
| Nullspace-v1.1 acquisition-only | 80 | 0.8023 | 0.9842 |
| Nullspace-v1.1 joint OOD | 160 | 0.9701 | 0.9967 |

Residual-v3.1 reproduces `failed-held-out-comparator`; both frozen joint-OOD
ratios exceed one. Nullspace-v1.1 reproduces
`supported-within-bounded-synthetic-protocol`; its joint-OOD ratios are below
one, while the oracle-time improvement remains small. Its receipt explicitly
sets `scientific_acceptance=false` and identifies the residual-v3.1 base model
as a failed comparator.

## Scientific limits

Both studies use generated straight-ray travel times, a fixed 16 by 16 grid,
three fixed acquisition layouts, and synthetic velocity families. The
independent oracle checks a distinct bilinear-slowness travel-time operator;
it does not model refracted rays, waveforms, elastic effects, anisotropy, or
field measurement error. The nullspace projection is linear in slowness; the
reciprocal velocity conversion and clipping mean it does not guarantee exact
data invariance. These replays improve source-to-result reproducibility only.
They do not establish field accuracy, geological recovery, learned superiority
outside the named cohorts, full M12 acceptance, or release readiness. R-008
remains failed.
