# IRLS control and null-workflow replay, 2026-10-31

## Scope

This current-source run exercises the general IRLS policy/serialization controls,
the corrected-workflow positive/control suite, and the source-correct original
null calibration workflow. The known failing non-null IR-C06 fixed-point case is
deliberately deselected; this replay does not establish non-null convergence,
full 24-condition IRLS acceptance, field eligibility, or full M02 acceptance.

## Exact run

- Repository commit at run start: `c7fd134d648ae9121c4f02487697262c8d139149`.
- Runtime: CPython 3.12.10, Windows, `.venv-pipeline`.
- Native thread policy: `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`.
- Command: `python -m pytest tests/numerics/test_gravity_irls.py tests/numerics/test_gravity_irls_corrected.py tests/numerics/test_gravity_irls_original_workflow.py -k 'not IR_C06_nonnull_actual_fixed_floor_stages_shared_budget_no_step_fabrication'`.
- Result: 86 passed, 0 failed, 0 errors, 0 skipped, 1 deliberately deselected; 404.00 seconds.
- JUnit SHA-256: `d5cd530ed799612bfa00b659cab7714884682a632fab897df8fddc7852f7e7a7`.
- Five `record_property` warnings reflect the configured `xunit2` family; they did not become failures.

## Source identities

| File | SHA-256 |
| --- | --- |
| `tests/numerics/test_gravity_irls.py` | `2d3738dc7bd42c0937b35e0181505453a57ae026f0dd2a2ae2bb35bc43f39248` |
| `tests/numerics/test_gravity_irls_corrected.py` | `45f54f67731d14bc52a45717d21ccde67cb9b704323802579192dce91e919e23` |
| `tests/numerics/test_gravity_irls_original_workflow.py` | `9caf7afd6aa06b4faaad28b6009ff36ac407e84486805f5524a96d8b47889815` |
| `data-pipeline/gravity_irls.py` | `466144b89a12d846723b413633b036dcbeda7a67087e8a82f4bbeb7ecec4542c` |
| `data-pipeline/gravity_irls_corrected.py` | `2e2a2403437e7b6479ab2c4b15d25994cd226661e0ec586817f061bd5ba13a78` |
| `data-pipeline/gravity_irls_original.py` | `7925a0de25ea53069dc349e449a4c4309c53c5538242a8142185a7dbc2ee1c6b` |
| `data-pipeline/gravity_irls_corrected_workflow.py` | `bc9948660346bb560e55106bb19ac1b960d3ec7dda0446636be8d198835c44f0` |

The frozen non-null recurrence's measured stage discrepancies remain recorded
in [the IR-C06 cause analysis](../irls-positive-cause.md). No acceptance
threshold, schedule, beta, weight, or iteration budget is changed by this run.
