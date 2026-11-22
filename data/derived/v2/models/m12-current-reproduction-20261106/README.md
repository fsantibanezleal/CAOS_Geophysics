# M12 current-source reproduction, 2026-11-06

This immutable package preserves the exact outputs of the two frozen synthetic protocols reproduced from checkout revision `7d395bed436334158d46ce3ccb5fd69265b0a352`. The residual model was trained on an NVIDIA RTX 4070 Laptop GPU. Both independent verification replays ran on CPU and returned `status=verified`.

## Files and identities

| Protocol artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `residual-v3.1/m12-residual-v3.1.npz` | 282651 | `0f7a8fc43a078ab4cb16016774d44b356ccb70d9c60e0f197506fd3f7a53ea03` |
| `residual-v3.1/receipt.json` | 919008 | `f6f52c544af1a86f07fc17c83296de2ac09e884058e2af1d72adeb3bb35bc1dc` |
| `nullspace-v1.1/m12-residual-v3.1-source.npz` | 282651 | `0f7a8fc43a078ab4cb16016774d44b356ccb70d9c60e0f197506fd3f7a53ea03` |
| `nullspace-v1.1/m12-residual-v3.1-training-receipt.json` | 919008 | `f6f52c544af1a86f07fc17c83296de2ac09e884058e2af1d72adeb3bb35bc1dc` |
| `nullspace-v1.1/receipt.json` | 497860 | `0d4cd8c14e290b9cd17da387800dbe6cf7314729379d03221df8585b1243d880` |

The repeated checkpoint and training receipt are the exact source copies required by the null-space verifier. They are intentionally duplicated so each immutable protocol directory is independently verifiable.

## Reproduce the verification

Copy each protocol subdirectory to a path outside every Git checkout, then run from the product root:

```powershell
.venv-pipeline\Scripts\python.exe scripts\run_m12_residual_v3.py --verify --output <external-path>\residual-v3.1
.venv-pipeline\Scripts\python.exe scripts\run_m12_nullspace_v1_1.py --verify --output <external-path>\nullspace-v1.1
```

The check regenerates the deterministic synthetic cohorts and verifies the receipts and outputs; it does not read field observations. Residual-v3.1 remains a failed held-out comparator (joint-shift velocity ratio 1.0437; independent oracle-time ratio 1.3961). Nullspace-v1.1 remains supported only within the bounded synthetic protocol (joint-shift ratios 0.9701 and 0.9967); its receipt keeps `scientific_acceptance=false`. The two studies use different cohorts, so their results do not isolate the incremental effect of null-space projection. Neither result establishes field accuracy, geological recovery, or product acceptance.

The full run report is `docs/validation/m12-current-source-reproduction-2026-11-06.md`; the governing protocol and limitations are in `docs/design/features/m12-velocity-validation/nullspace-v1_1-protocol.md`.
