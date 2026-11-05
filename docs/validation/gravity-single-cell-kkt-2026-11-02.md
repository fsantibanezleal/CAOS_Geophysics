# Gravity single-cell KKT regression — 2026-11-02

## Finding and correction

The current authenticated 144-station, one-active-cell gravity upload failed
before its first optimizer update. `_kkt_gradient` constructed
`np.maximum.reduce([array, array, scalar, scalar])`; NumPy rejected this
heterogeneous sequence with `ValueError: setting an array element with a
sequence`. The solver correctly retained the job as failed and published no
result. The failing job request SHA-256 was
`fd62b71a1bd35a795133cf06476bf383bc607d42613d26b8b28023abfbd75c10`; its
original upload SHA-256 was
`6c9ca46656e4a28dedd46c8d92f30264cb7658f9478f98e9c67d078806dc1305`.

The tolerance scale now uses nested elementwise `maximum`, which broadcasts
scalar bounds over a one-cell model and retains array-bound behavior. A focused
regression covers interior and both active-bound KKT signs. The failed run and
its diagnostic archive are retained under
`E:\_Datos\CAOS_Geophysics\validation\release-gate-refresh-20261102`.
The failed JUnit SHA-256 is
`fdb42775d4545561d570a8a3ea2123da3a27907bc7ef4aa1846f9f44150b16b0`; the
captured eight-candidate diagnostic SHA-256 is
`c05af1e9d6b19f6aa7c93fca349c1b3cbd8e75d2ed617bd62d3460bfe47f0063`.

## Current-source verification

The product checkout was dirty at base revision
`f0ec2fc37fdae1f0c1c7d40b6cae386a85d7e6ac`. Thread pools were pinned to one for
the native solver controls. Current source SHA-256 values at these runs were:

- `data-pipeline/gravity_l2.py`: `fc6fd9216edd43c02b83fddedca007a782bc627073a9d08da069d29f75d4d016`
- `tests/numerics/test_gravity_l2.py`: `d8599ba60f45919cf42d2dccdf054fb5e009034577c2294303e81d75b7c444a4`
- `app/gravity_l2_compute.py`: `6b519ae0b731906dc1b127a77406d15ca6c54a84d7b85326fde60b8bdbc8859b`
- `tests/api/test_gravity_l2_upload.py`: `8a3688f8cf67ffcfc5b7c9a1ff78942479490964b8e21aa96900b51d3138fa90`

| Check | Result | Retained report and SHA-256 |
|---|---:|---|
| `tests/numerics/test_gravity_l2.py` | 113 passed, zero failed/skipped | `E:\_Datos\CAOS_Geophysics\validation\gravity-upload-after-kkt-fix-20261102\gravity-l2-core.xml`; `f6f9eacfb4c5af6f0471c2656c68544c69554b4902e137d53ba0130e40e25117` |
| Authenticated uploaded survey, parameter effect, Choclo forward oracle, exported held-out residual recomputation and source-preserving result | 1 passed | `E:\_Datos\CAOS_Geophysics\validation\gravity-upload-after-kkt-fix-20261102\r009-gravity-upload-kkt-fix.xml`; `ec0d4316c1376fc7f0b24366a9f568dc2645efc040d1b826a4edcc2b6d0e743e` |
| Gravity admission without loading solver engines | 1 passed | `E:\_Datos\CAOS_Geophysics\validation\gravity-upload-after-kkt-fix-20261102\r006-admission.xml`; `974b17592e056e2cd8c8ae7eff9ce484d153312301f30e96c246484cabb1316f` |
| Uploaded EDI MT inverse and independent oracle | 1 passed | `E:\_Datos\CAOS_Geophysics\validation\gravity-upload-after-kkt-fix-20261102\r006-mt-oracle.xml`; `af5557d1353bef088a85eed701cf2aa7cc590533407f1b2f0c0d8bc110de1038` |
| Physical metadata rejection across raw formats | 12 passed | `E:\_Datos\CAOS_Geophysics\validation\release-gate-refresh-20261102\r003-metadata.xml`; `f69fdafee941c65cd579b6219817fb9d684df799e8512ecd038ffccfaad2a001` |
| Timeout/cancellation/recovery, scratch cap and RSS cap | 3 passed | `E:\_Datos\CAOS_Geophysics\validation\release-gate-refresh-20261102\r007-job-limits.xml`; `60fe5cd8495659aa257472ffc4e5ce0a08c5e58661449557ae2fd01503269db2` |
| FWI artifact lineage and field-truth rejection | 1 passed | `E:\_Datos\CAOS_Geophysics\validation\release-gate-refresh-20261102\r009-fwi-no-truth.xml`; `9bf88ec3a50a024ae093674576de7735fcd7484e08582347de1569a9f7ed06f8` |
| Owner export bundle round-trip, units, rights and tamper refusal | 1 passed | `E:\_Datos\CAOS_Geophysics\validation\release-gate-refresh-20261102\r011-export-rights.xml`; `e26dc85c52a7bcdec7d045af2e40060d0a3fa29fe8c93407263e0a2d7d0e2854` |

The earlier failed upload test was rerun after the fix using the normal short
Windows pytest temporary path. An attempted long external `--basetemp` run
failed before the solver because the Windows path exceeded the test harness's
path envelope; it is infrastructure-only and is not counted as a solver result.

These scoped tests do not replace the source-bound 24-case L2/IRLS matrices,
independent numerical review, all-method artifact coverage, actual-host job
admission, or full product release acceptance. R-006, R-007, R-009, R-011 and
R-008 therefore remain unresolved/failed as recorded by the convergence ledger.
