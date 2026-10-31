# M02 precision and allocation-control replay, 2026-10-31

## Scope

This current-source replay runs the complete `tests/numerics/test_gravity_l2_precision.py` module, including precision contracts and the real certified-delta allocation control. It is local software evidence; its process measurement does not establish a resource upper bound or host acceptance.

## Exact run

- Repository commit at run start: `64372916d2853db13b8b7595570bce4f31eba2f2`.
- Runtime: CPython 3.12.10, Windows, `.venv-pipeline`.
- Native thread policy: `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`.
- Command: `python -m pytest tests/numerics/test_gravity_l2_precision.py -q` with JUnit and temporary files outside the checkout.
- Result: 81 passed, 0 failed, 0 errors, 0 skipped; 50.010 seconds.
- JUnit SHA-256: `65954a6c466d3394a1da90d45266b7a57b7bbbd2c5ee4a4bc63a716568b52a2d`.
- The test for the real certified-delta allocation case emitted one `record_property` warning because pytest uses the `xunit2` JUnit family; the saved case property is present and the test passed.

## Source identities

| File | SHA-256 |
| --- | --- |
| `tests/numerics/test_gravity_l2_precision.py` | `21d8fdd6e97552fd6efcb0e8910fd90237f8aceecb828e00487a88aa6e295d27` |
| `data-pipeline/gravity_l2_precision.py` | `57727cac9ab6550eab902d20d6c43e662be8f9fac406896c6797d1e29b3e7c1a` |
| `data-pipeline/gravity_l2.py` | `3b6e20f6cf0280a3db0f0bf14beec2dec0851445cf9ec157a6ec66d4176f823e` |

The independent full-source review, resource upper proof, host admission, field-source eligibility, non-null IRLS convergence and overall product acceptance remain open.
