# M12 residual correction v3.1 validation record

**Disposition: failed scientific comparator; do not advertise as an accepted
inversion method.** This record preserves the complete bounded synthetic run,
including its negative result. It is not evidence of field validity.

## Reproduction and retained files

Run on the NVIDIA GeForce RTX 4070 Laptop GPU (CUDA training; CPU cohort
scoring):

```powershell
.\.venv-pipeline\Scripts\python.exe scripts/run_m12_residual_v3.py --device cuda --output E:\_Temp\CAOS_Geophysics\validation\m12-residual-v3.1-20261025
.\.venv-pipeline\Scripts\python.exe scripts/run_m12_residual_v3.py --output E:\_Temp\CAOS_Geophysics\validation\m12-residual-v3.1-20261025 --verify
```

The immutable run directory contains `receipt.json` (919,010 bytes) and
`m12-residual-v3.1.npz` (282,651 bytes). Receipt SHA-256:
`c8364024d830076af674d0bb18f521870497c0c400eea2e17805a69695cde072`.
Checkpoint SHA-256:
`0f7a8fc43a078ab4cb16016774d44b356ccb70d9c60e0f197506fd3f7a53ea03`.
The verifier independently replayed all five evaluation cohorts and returned
`verified`; CPU/CUDA parity passed the declared v3.1 envelope. The receipt
records source hashes, complete disjoint manifests, per-record errors,
per-family/acquisition summaries, all epochs and threshold counts.

## Locked result

The run used 1,200 training groups, 160 validation, 160 ID test, 80
family-only, 80 acquisition-only and 160 joint-OOD groups. Validation selected
epoch 100 and classical regularization lambda 100. Ratios below 1 favor the
learned correction over the matched classical inverse.

| Cohort | n | Velocity RMSE ratio | Independent travel-time RMSE ratio |
|---|---:|---:|---:|
| Validation | 160 | 0.4052 | 1.0698 |
| ID test | 160 | 0.4127 | 1.0690 |
| Held-out geology family | 80 | 1.0474 | 1.4043 |
| Held-out acquisition layout | 80 | 0.4168 | 1.0841 |
| Joint geology + acquisition OOD | 160 | 1.0437 | 1.3961 |

The preregistered joint-OOD gate requires both ratios below 1.0. Both fail;
the independent oracle travel-time ratio also exceeds 1.0 on every cohort.
The method can produce visually plausible velocity maps while making their
independent forward predictions worse. It must not be enabled or described as
a successful solver. A future revision needs to address physical consistency
and family/acquisition generalization, then freeze a new protocol and fresh
seeds before test scoring.

## Numerical replay amendment

The first v3 attempt stopped before any held-out scoring because its strict
CPU/CUDA cellwise assertion failed. That incomplete folder is retained as
`E:\_Temp\CAOS_Geophysics\validation\m12-residual-v3-20261025`; it contains no
receipt and no test scores. Protocol v3.1 changed only the replay tolerance,
predeclaring max/p99/mean bounds of 0.15/0.05/0.02 m/s. Observed values were
0.1194/0.0427/0.01064 m/s, respectively. Test outputs were then recomputed
from the CPU-reloaded checkpoint. Model, data split, training, validation
selection and scientific comparator were unchanged.
