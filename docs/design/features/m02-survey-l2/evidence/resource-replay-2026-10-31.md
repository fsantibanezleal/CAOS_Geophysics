# M02 locked-control resource replay, 2026-10-31

## Scope

This is a current-source local Windows measurement of the approved resource harness. The cap and nominal categories each ran 20 serial children. The nominal child executes locked family 0, condition 0, including the complete 25-fit candidate/refit workflow. The cap child executes the real certified-delta allocation control. Peak memory is sampled process-tree RSS, not an allocation upper bound and not a VPS measurement.

## Exact run

- Repository commit: `88cb8681619c69b7eb53017e1adb86c6700d9335`.
- Runtime: CPython 3.12.10, Windows, `.venv-pipeline`.
- Native thread policy: `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`.
- Command: `python scripts/validate_m02_resources.py --output <external-data-root>/validation/m02-resource-20261031-current --count 20`.
- Result: 40 science receipts passed; 40 resource receipts passed; 40/40 sampling complete; 0 timeouts; 0 sampling errors; exit status 0.
- Cap case p95 sampled process-tree peak RSS: 754,779,340.8 bytes; p95 wall time: 18.7506 seconds.
- Nominal case p95 sampled process-tree peak RSS: 287,802,163.2 bytes; p95 wall time: 209.828 seconds.
- Summary SHA-256: `ac462943083158da70b6d9de59197f85f21165608048e53f25e83c17a75b0311`.
- External receipt set contains all 40 per-run JSON, resource JSON and log files plus `summary.json`.

## Pinned sources

| File | SHA-256 |
| --- | --- |
| `scripts/validate_m02_resources.py` | `d7dd475e18ccebceaa3a6a252c1ce8fc2c9aadc45e30dc439988a0c79c711d17` |
| `tests/numerics/test_gravity_l2_selection.py` | `f6557c33df18599ec8d511b9656a67456d1434ff84430ea4cf87b86e1bc82028` |
| `tests/numerics/test_gravity_l2_precision.py` | `21d8fdd6e97552fd6efcb0e8910fd90237f8aceecb828e00487a88aa6e295d27` |
| `data-pipeline/gravity_forward.py` | `46d205a453147cc18697464e4a6deda2920d0d88307e366b6fd336d9a1ac07d5` |
| `data-pipeline/gravity_l2.py` | `3b6e20f6cf0280a3db0f0bf14beec2dec0851445cf9ec157a6ec66d4176f823e` |
| `data-pipeline/gravity_l2_metric.py` | `d09a2b4630258d2c26a1a82ea92a3cd79b42143695d3e630d5252df5ba8dfe8b` |
| `data-pipeline/gravity_l2_precision.py` | `57727cac9ab6550eab902d20d6c43e662be8f9fac406896c6797d1e29b3e7c1a` |
| `data-pipeline/gravity_survey_l2.py` | `50934e1f56fcd468787b113598d01966b0a0eb1b124cb95363605fea8278da97` |

## Interpretation

The automated harness summary explicitly leaves `resource_upper_proof` and `host_accepted` false for both categories. These receipts establish repeatable local process measurements only. They do not establish the 24-condition scientific matrix, an allocation upper bound, VPS admission, field eligibility or full M02 acceptance. The scientific matrix is recorded separately.

