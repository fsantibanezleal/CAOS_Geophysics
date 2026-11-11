# Geometry-normalized residual-learning lesson replay

Date: 2026-11-11. This receipt records one fresh local CUDA training run and the fresh-kernel replay of the English and Spanish Level 4 lessons. It is evidence for this experiment and these two notebooks only; it does not accept the proposed method or the product release.

## Frozen run identity

- Source revision before the notebook-only update: `046f80361a984ab53a7ee0fb8311b178704b05e4`.
- Device: NVIDIA GeForce RTX 4070 Laptop GPU, CUDA; 40 fixed epochs, selected epoch 40.
- Train/validation/held-out counts: 800 / 160 / 480, divided into 160 in-distribution, 80 family-only, 80 acquisition-only and 160 joint-shift records.
- Checkpoint SHA-256: `ff6ceb75c8e641c6e17dee911c99a3aa786fcdad4f290b86e93bfc32e809bbb5`.
- Run receipt SHA-256: `fe0697531923f24ed0dafc7fba1469eb1ba9b2459615fedce3336934b9370ae0`.
- Training code SHA-256: `aa85618783b014df20612e72ca0451f68e658e5dc12ebb4336d1f54259cf4b3e`.
- Operator code SHA-256: `2b9ed95d3ba7b1b0f9f80167fa610640dc75c8a142dafb9f7f09791b96a1fd44`.

The receipt and checkpoint were written outside the repository under the configured data root. The notebook verifies both hashes and regenerates the frozen cohorts before producing scores. The full current-source CPU verifier returned the same checkpoint identity and accepted all recorded per-case metrics within its declared cross-device tolerance.

## Held-out measurements

Ratios are learned divided by matched regularized-ray error; values below 1 favor the learned model. The forward-time score uses the independent bilinear-quadrature operator.

| Cohort | n | Velocity RMSE ratio | Independent time RMSE ratio | Forward-threshold flags |
|---|---:|---:|---:|---:|
| In-distribution | 160 | 3.0339 | 4.9568 | 14 |
| Family shift | 80 | 2.1783 | 5.7331 | 80 |
| Acquisition shift | 80 | 3.0917 | 5.2677 | 6 |
| Joint family/acquisition shift | 160 | 2.1942 | 5.5854 | 160 |

No joint-shift survey improves both error measures. The declared advantage hypothesis fails. This result is retained as a negative synthetic result; it is not field validation, geological generalization, or a novelty/superiority claim.

## Notebook evidence

Fresh-kernel execution passed for:

- `notebooks/en/08-learning/07-physics-conditioned-velocity-refinement.ipynb` — SHA-256 `bbabd8eb247c4e1ad7fcb620d2098bda7080832699946acc4a59d76863d4c24d`.
- `notebooks/es/08-learning/07-physics-conditioned-velocity-refinement.ipynb` — SHA-256 `92c64fc1234dff584ed92a44cca5e9fa4f0f84a5435761837b1232a268bf6c91`.

Command: `python scripts/run_notebooks.py --check --tmp <CAOS_TEMP_ROOT> --only notebooks/en/08-learning/07-physics-conditioned-velocity-refinement.ipynb --only notebooks/es/08-learning/07-physics-conditioned-velocity-refinement.ipynb`, with `M12_OUTPUT` pointing to the verified external run. The two notebooks each contain five executed figures, three display equations, the cohort comparison, paired bootstrap intervals, the input-contract exercise, and the negative result. Both clear the CAOS Level 4 depth floors. The repository-wide notebook gates still report other findings; these two passes do not close notebook-set acceptance.
