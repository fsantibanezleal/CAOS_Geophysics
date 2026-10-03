# Dependency-sequenced implementation and convergence

1. Define MT-ON-01 through MT-ON-10 and their named gates in `requirements.md`; settle source, worker, numerical and host boundaries in `design.md`. **Done before code.**
2. MT-ON-01/02/03/06: extend the existing EDI dataset and owner-scoped M05 admission, then add strict worker QC on original bytes. **Implemented; API gates passed.**
3. MT-ON-04/05: extend `invert_edi` only for frozen active frequencies, implement bounded M06 starts/baseline/sensitivity and conditional intervals, and validate the child result. **Implemented; independent halfspace, layered parameter-effect and bundle gates passed.**
4. MT-ON-07/09: reuse singleton worker limits, add method-specific preflight and default-closed host admission; test cancellation and failure states. **Local preflight/cancel/timeout/RSS/scratch gates passed; actual ML VPS admission pending.**
5. MT-ON-08/10: extend re-import validation and execute M01 regression gates. **Implemented; M01/API regressions passed.**
6. Run independent numerical, negative, API, export, local nominal/upper/malformed resource and SDD convergence gates. **Local gates passed; measured receipt is in `docs/validation/online-mt-local-benchmark.md`.**

## Convergence verdict

| Requirement | Gate and local verdict | Remaining limit |
| --- | --- | --- |
| MT-ON-01/02 | `test_source_identity_and_m05_screen`, original hash/bytes and full screen: pass; `tests/test_edi.py` independent parser/units/rotation gates: pass | None in this bounded parser subset |
| MT-ON-03 | `test_malformed_and_clear_lake_exclusion` on actual ignored, hash-pinned cl061 plus `test_declared_physics_mismatch_fails_m05`: pass | Other EDI dialects are rejected unless their strict parser succeeds |
| MT-ON-04/05 | `test_inverse_parameter_effect_and_independent_oracle`, `tests/test_mt_recovery.py` and bundle checks: pass | Fixed halfspace/two-layer approximation; field geological truth unavailable |
| MT-ON-06/08 | `test_bundle_roundtrip_and_wrong_principal` and tampered re-hashed prediction: pass | Export deliberately omits private raw original |
| MT-ON-07 | `test_preflight_cancel_timeout_and_memory`, `test_raw_receipt_tamper_blocks_m05`, `test_mt_account_quota_reserves_full_m06_scratch` and existing `test_job_limits.py`: pass | Host-specific recovery still required |
| MT-ON-09 | `test_host_gate_defaults_closed`: pass; local nominal/upper/malformed benchmark: pass | **Pending:** actual ML VPS p95/headroom, cancel/crash/concurrent-read and external release gates; flag remains off |
| MT-ON-10 | M01 execution/export regressions and full API suite: pass | No M01 version or result-format change |

Validation commands on the branch: `python -m pytest -q -x -o addopts= tests/api` (79 passed, 1 opt-in benchmark skipped before the final quota test), focused quota/export rerun (18 passed), `python -m pytest -q -x -o addopts= tests/test_edi.py tests/test_mt_recovery.py tests/numerics/test_mt_field_qc.py` (68 passed, 3 existing skips), opt-in local benchmark (1 passed), and `ruff check app tests/api/test_online_mt.py tests/api/test_online_mt_benchmark.py data-pipeline/edi.py data-pipeline/electromagnetics.py` (pass). The actual-host gate is not converged, and this draft branch does not activate, merge or deploy M05/M06.
