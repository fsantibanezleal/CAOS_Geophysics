# Local validation checkpoint: 2026-10-31

This is evidence from the dirty direct checkout at `9f022aae8d178211b4c77730b722723fc3345a3b`. It records bounded local checks, not a release acceptance. The canonical ML VPS still serves `0.04.001`; no replacement was staged or deployed.

## Passed checks

| Check | Result | Receipt / boundary |
|---|---:|---|
| Offline lane | 569 passed, 0 failed, 0 errors, 0 skipped | `E:\_Temp\CAOS_Geophysics\validation\offline-suite-20261031-stepwise-resume5.junit.xml` · stepwise lane excludes API/ops, adversarial, ERT/traveltime/profile-mesh and the locked 24-solve matrix. The locked matrix was reused from exact verified JUnit receipts. |
| M01 scientific course and gravity JSON custody controls | 28 passed, 0 failed | `E:\_Temp\CAOS_Geophysics\validation\m01-current-source-replay-20261031.junit.xml` · retained historical bundles keep their exact source hashes; current code replays their scientific arrays. |
| Gravity transforms and M01 negative controls | passed | Current-source checks include historical/current module identities and refusal of an unsupported core hash. |
| API metadata | 14 passed, 0 failed | `.venv-api`; includes StationXML companion rejection as a standalone dataset. |
| API suite | 1,198 passed, 0 failed/errors, 138 skipped | `E:\_Temp\CAOS_Geophysics\validation\api-suite-6421f5c-20261031\api-complete.junit.xml` · local API/service evidence only; skips remain explicit. |
| Cross-format data tests | 72 passed | `.venv-pipeline`; parser/format checks only. |
| Production frontend build | passed | TypeScript and Vite build; 1,045,868,078 bytes across 311 built files. Build warning: the Workbench and Three.js chunks exceed 500 kB minified. |
| CAOS shell browser gate | 1,442 states, 157 screenshots, 0 failures, 0 waivers | [Gate report](shell-gate-2026-10-31.json); external captures are in `E:\_Temp\CAOS_Geophysics\validation\shell-gate-20261031`. Dirty-tree UI/layout evidence only. |
| Read-only ML VPS refresh | passed | [Host receipt](actual-host-capacity-readonly-2026-10-31.md): 31,749,431,296 bytes free; current release plus exactly two rollback releases; no extra release directory existed to prune. |

## Open acceptance gaps

The default frontend unit run reports **380 passed, 23 skipped, 36 failed** across 51 files. The failures require original external joint and magnetic custody inputs, including `GEOPHYSICS_JOINT_OUTPUT_FIXTURE`, `GEOPHYSICS_JOINT_MATRIX_FIXTURE`, the actual Python custody API receipt, the M04 selected-final extraction, and the owned-custody browser control. Those exact inputs are unavailable at their recorded locations; no substitute was made. This is not a passing frontend gate.

The physical child in `scripts/process_physical_job.py` is not dispatched by `app/physical_assembly.py`: the participating worker still sends non-M11 claims to the legacy executor. Therefore protected online gravity correction/transform jobs are not implemented end to end, regardless of the local child and producer modules. The full release harness is also unqualified because the exact retained M01 correction/transform packets, profile-incomplete receipt, and M11 native database are absent. The convergence ledger still records `R-008` failed with 17 requirements unresolved. The solver/release gates therefore do not accept scientific field eligibility, full online jobs, or replacement readiness.

## Deployment observation

At `2026-10-31T08:01:00Z`, `https://geophysics.ml.fasl-work.com/` served the legacy `0.04.001` static app. `/api/health` returned the SPA fallback as `text/html`; API and worker services were inactive. The active release and two rollback directories were preserved. No release was changed.
