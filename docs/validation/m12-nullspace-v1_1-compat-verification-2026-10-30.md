# M12 null-space v1.1 compatibility replay

The retained external run was replayed on 2026-10-30 with the hash-bound
scientific sources unchanged. The original verifier stops because it compares
the recomputed calibration-score mapping with exact floating-point equality.
The selected lambda remains exactly 100, the calibration manifest hash is
unchanged, and recomputed candidate scores differ only at roundoff scale.

The compatibility verifier applies rtol=1e-10 and atol=1e-12 only to the
calibration candidate-score mapping. It delegates all other checks to the
original verifier, including the exact selected lambda, source and checkpoint
hashes, split manifests, alpha selection, calibration metrics, and replay of
all four held-out cohorts. The full command exits 0:

    .venv-pipeline/Scripts/python.exe scripts/verify_m12_nullspace_v1_1_compat.py --output E:/_worktrees/_runs/m12-nullspace-v1_1-full-20261027b

| Evidence | Result |
|---|---|
| Receipt SHA-256 | 30df0c2ad495bd850dda602b1c96725be8290dd086119fb3e8e75355fe9dea22 |
| Compatibility verifier SHA-256 | 8195506e3df637e760d23c5bf8edcbebcb377e367e064638dd6a9e6bec71bcef |
| Original bound sources | Verified |
| Selected classical lambda | 100 |
| Selected refinement alpha | 1.0 |
| Held-out cohorts replayed | 4 |
| Receipt result | supported-within-bounded-synthetic-protocol |
| Scientific acceptance | false |

This verifies the saved synthetic computation within its stated protocol. It
does not establish M12 acceptance, field accuracy, geological recovery, or
product release acceptance.
