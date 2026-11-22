# Retained joint-survey frontend fixture validation

On 2026-11-05, the joint-survey browser contract suites ran against the retained
external fixtures below. The data were read in place; the runner neither copies
nor regenerates them. Reproduce with
`scripts/run_joint_frontend_validation.ps1` from the repository root.

Result: **7 test files passed, 80 tests passed, 4 optional tests skipped, 0
failures** (Vitest 4.1.12, 77.93 seconds). The skipped tests require retained
actual evaluation, abort, and durable-abort outputs that were not supplied to
this run. The runner clears those optional environment variables so another
shell's values cannot silently change the evidence set.

The committed runner was then executed as a clean replay: the same 7 files,
80 passes and 4 skips completed in 7.32 seconds with the local file cache warm.

The run covered the 24-case original input matrix and 24-case native output
matrix, the maximum-resource native output, selected-state instrument export,
and an actual Python owner-only API custody archive. Tests included complete
output import and original-byte round trips, importer queue limits and resource
profiles, matrix failure retention, archive identity/hash controls, UI rendering,
and custody failure-state handling. The output matrix's current importer suite
observed all 624 candidate attempts, including nonconverged states.

External fixture manifests retained outside Git:

| Fixture | Retained control file | SHA-256 |
| --- | --- | --- |
| Input matrix | `validation/combined-joint-input-matrix-20261031/fixture-manifest.json` | `946ca7904d5d9d063d0c3f57e1e78ffeb96453f04e4e9f25ff14601a746c659d` |
| Output matrix | `validation/combined-joint-output-matrix-20261031/matrix.json` | `043e69ac428b7c0dc608aeaaFB374290bd9cf8f5ba3c6f90de57dc95cb9e5356` |
| Maximum-resource gate | `validation/combined-joint-maximum-resource-20261031/resource-gate.json` | `d5aef2d1ec0783146e0a36e91bc995f7e689f601a8d987d8f48773ba3413911e` |
| Python API history | `validation/combined-api-custody-20261031/actual-history.json` | `d67b63bc870a725f889e5ef5b998320a34dca35e6e7fb567e30cb689f285f08d` |
| Python API index | `validation/combined-api-custody-20261031/actual-index.json` | `631d405d8c4048f294a5f247defaae21ae517a953245780699cc3069caee0ba2` |
| Python API archive | `validation/combined-api-custody-20261031/actual-export.zip` | `a413868195835b7f1cd56f25d95bc751fb3f04c0559220b8ab128fce0c4ae846` |
| Selected-state instrument | `validation/joint-instrument-replay-20261031/current-instrument-case00/result/result.json` | `22339b57f87f216abe610e800cf486e90578048722e6dd26a9f20c0f8df62bab` |

This is local parser, custody, and browser-contract evidence for retained
synthetic/native artifacts. It does not establish field-data validity, scientific
recovery, full method acceptance, actual-host acceptance, or release readiness.
