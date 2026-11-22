# Corrected IRLS original24 family 0 condition 0

Date: 2026-10-31. This is a source-bound negative result for the approved
`m02-survey-irls-cpu-2` corrected policy. It is not an accepted calibration,
field result, or product release.

## Reproduction and custody

- Gate: `tests/numerics/test_gravity_irls_corrected_matrix.py::test_original24_corrected_science[0-0]`.
- Runtime: CPython 3.12.10, `.venv-pipeline`, Windows, OpenBLAS/OpenMP/MKL set to one thread.
- Frozen request SHA-256: `026d4f051811b1f5dda1bf5d7066659b02103b02e3c81c6680b38a426d10f18e`.
- Corrected result SHA-256: `2cd2d861b0976136b71e335bbea42518a23b1015833c99e9e98073ec4712d6a0`.
- Source-inventory SHA-256: `2fbf14d85009fc6202f55815dbe45d44cf2669c22fc8edd5fe4927e0f6df0f48`.
- Immutable external archive: `E:\_Datos\CAOS_Geophysics\validation\m02-irls-corrected-20261031\data\corrected-family0-condition0-999fd6bae5463c28.gza`, 9,326,644 bytes, SHA-256 `a42c750f8361dbfaf7fcc94356551ed176d28d89fba43a54b5c215ffc2e04e3f`.
- JUnit: `E:\_Datos\CAOS_Geophysics\validation\m02-irls-corrected-20261031\corrected-original24-0-0.xml`, SHA-256 `88e19f2c848e8239cec23052402cb1026e4420249ed2ca97bcd007c20e476e15`.
- Test-source SHA-256 at run: `db1e0df5a784549ac1405c2436500e5b1261792e81808a786fd7b845704f0e8b`.

The exact 24-fit calibration took 504.469 seconds, within the 1,800-second
workflow cap. The archive was atomically preserved before assertions and then
its complete physical/source replay passed. The test failed only at the
unchanged requirement that the positive family/condition control select a
candidate. No final refit or outer evaluation was performed after selection
correctly returned `insufficient_candidates`.

## Actual result

| Beta candidate | Fold outcomes | Eligible |
| ---: | --- | --- |
| 0 | 3 line-search failures | no |
| 1 | 3 line-search failures | no |
| 2 | 3 iteration caps | no |
| 3 | 3 iteration caps | no |
| 4 | 3 iteration caps | no |
| 5 | 1 converged, 2 iteration caps | no |
| 6 | 2 converged, 1 iteration cap | no |
| 7 | 3 fixed-point convergences | yes |

Only one of eight candidates is eligible. The frozen selector requires at
least two complete candidates; it therefore returns no selection. In candidate
6 fold 2, the final recorded weight-relative change is
`1.0348163696477964e-6`, above the unchanged `1e-6` limit. This is retained as
an iteration-cap failure. Candidates 0 and 1 fail in line search before an
IRLS weight update. These observations motivate solver research; they do not
authorize changing candidate rules, stopping tolerances, iteration caps, or
terminal semantics.

The other 23 family/condition cells, full corrected noise/refit/resource
controls, independent review, and M02 acceptance remain open. The historical
CPU3 terminal-certificate proposal does not amend this CPU2 policy and remains
separate from this evidence.
