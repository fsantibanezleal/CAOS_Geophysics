# Bounded online EDI M05/M06 self-review

Date: 2026-10-03. Branch: `task/geophysics-online-mt`. Feature SDD preceded implementation. The interrupted dirty implementation was retained and reviewed, then committed in scoped milestones and rebased safely onto develop `2202ebd`, including M13/wiki and the product convergence ledger. The first two rebased milestones are `0f82c3b` (SDD) and `c187ebc` (backend/tests/contracts). No frontend, phase/FWI worktree, public origin, deployment or published scientific artifact is changed by this feature.

## Reviewed boundaries

The authenticated project/asset/dataset/job/result/export flow is reused. Original user EDI bytes are measured, hashed and never rewritten. Dataset parsing is deliberately an envelope, not an eligibility assertion. M05 and every M06 re-screen use the strict existing full-tensor parser and its independent MT Metadata comparison. Every subsequent scientific read uses the hash-verified original-byte snapshot in private staging, avoiding drift between repeated parser/solver calls. Owner-scoped lookup and same-dataset M05 binding apply before queued work. Both API and storage-only worker admission flags default closed; a closed worker refuses previously queued MT work before spawn. Requests/result identities bind source and scientific code/runtime versions.

The worker uses its existing singleton/account quota, fixed child command, stripped environment, one numerical-library thread, cancel/timeout/RSS/scratch enforcement and crash recovery. Snapshot/cache/stderr/result bytes count toward scratch, including final child-exit checks. Parent API/worker memory, Linux address-space limits and operational responsiveness still need actual-host evidence. No host flag is enabled by these tests.

M06 is bounded SciPy TRF through `invert_edi`, not a replay or a second inverse. A halfspace or one imposed finite thickness is fitted in log resistivity. All frequencies participate in tensor eligibility; every fifth sorted frequency is frozen as holdout before solving. Successful starts are selected only by training objective. The same-input halfspace, alternative beta and thickness sensitivity remain visible. The bootstrap is pointwise and conditional on supplied errors, fixed thickness, beta, bounds and frame; geological truth and clean targets remain null. The independent analytic/reflection source generator lives in tests only and its truth is not supplied to the inverse. Clear Lake cl061 parses successfully but fails the full screen and cannot run M06. Re-import checks canonical members/hashes, units/sign/variance/rotation, tensor/curve consistency, predictions/residuals and conditional interval summaries. No raw private EDI is included in the bundle. M01 contracts and tests remain unchanged.

## Local checks and explicit non-passes

Commands ran from this worktree. Use a new short basetemp for each invocation when preserving outputs.

| Check | Command / evidence | Outcome |
| --- | --- | --- |
| Isolated runtime | Fresh standard venv; install `requirements-api.txt` and `requirements-dev.txt`; `python -m pip check`; Torch module lookup | Dependencies consistent, system-site access false, no Torch |
| Complete API after rebase | `.venv-online-mt-oct3/Scripts/python.exe -m pytest -q -x -o addopts= --basetemp data/raw/a4 tests/api` | 84 passed, 1 opt-in skip, 143.13 s |
| Actual worker matrix | Set `GEOPHYSICS_RUN_LOCAL_MT_BENCHMARK=1`; same interpreter, `-m pytest -s -q -x -o addopts= --basetemp data/raw/b4 tests/api/test_online_mt_benchmark.py::test_local_nominal_upper_malformed_admission` | 1 passed, 43.20 s; [receipt](online-mt-local-benchmark.md) |
| Offline strict EDI/MT numerics | `.venv-ingestion/Scripts/python.exe -m pytest -q -x -o addopts= --basetemp data/raw/mt-oct3-offline-numerics tests/test_edi.py tests/test_mt_recovery.py tests/numerics/test_mt_field_qc.py` | 68 passed, 3 existing C15 field-source skips, 54.29 s; separate Torch-capable environment, not isolated runtime evidence |
| Convergence adversarial tests | `.venv-online-mt-oct3/Scripts/python.exe -m pytest -q -o addopts= tests/test_sdd_convergence.py` | 10 passed, 0.72 s |
| Broad lint | `ruff check app data-pipeline tests` | Pass |
| Cheap repository guards | `scripts/check_content_standards.py`, `check_template_residue.py`, `check_ci_budget.py`, `check_phase_assets.py`; scoped whitespace, Markdown links and named feature gates | Pass |
| Product ledger | `scripts/check_sdd_convergence.py` | Structure valid; zero product passes, 18 unresolved, one failed |
| Product release mode | Same checker with `--require-release` | Expected nonzero: replacement not accepted, incomplete product gates, legacy dual origin |
| Published artifact provenance | `scripts/check_artifacts.py` | **Fails**: stale MT scientific source/settings; release reconciliation required |
| Actual VPS admission | Restricted Linux matrix, nominal p95/headroom, cancel/timeout/crash and concurrent-read responsiveness | **Not run; user-owned host harness pending** |

The API and benchmark runs each emit one upstream Starlette TestClient/httpx deprecation warning. An initial complete API attempt under a long basetemp hit the unchanged M01 deletion fixture's Windows path limit (263-264-character paths); the complete suite passes with short private basetemps. No M01 implementation change was made to hide that environmental failure. Failed outputs are preserved.

The artifact guard binds full scientific source bytes, so the lazy Torch import in `electromagnetics.py` makes all 24 published MT synthetic replay fingerprints stale; the `edi.py` active-mask extension also changes cl061's published parser-source hash. A read-only scan confirms no other family fingerprint changed. The published bytes, manifests and the guard itself are untouched. Before any promotion/release, the release owner must reconcile these source-bound artifacts with actual scientific executions and review their results, not merely replace hashes. The static cl061 receipt remains QC-only; the new actual-byte API screen independently demonstrates its exclusion. This blocker is distinct from live-host admission and full frontend/product convergence. Trunk-only CI has no automatic task-branch/PR test invocation; local tests are not a green remote CI assertion.

## Exact feature path inventory

The initial feature changed 25 paths relative to its develop base. The authorized source-reconciliation follow-up adds the offline checker, adversarial tests and measured candidate evidence, and updates its SDD and script index; see the [additional inventory and actual-source verdict](mt-source-reconciliation.md). The ledger and incoming M13/wiki files are not modified by this feature.

```text
app/bundle.py
app/config.py
app/mt_bundle.py
app/mt_compute.py
app/mt_contract.py
app/processing.py
app/processing_contract.py
app/processing_storage.py
app/worker.py
data-pipeline/edi.py
data-pipeline/electromagnetics.py
docs/README.md
docs/data-contract/02_online-edi-mt.md
docs/design/features/online-edi-m05-m06/design.md
docs/design/features/online-edi-m05-m06/requirements.md
docs/design/features/online-edi-m05-m06/tasks.md
docs/guides/08_online_edi_mt.md
docs/guides/README.md
docs/validation/online-mt-local-benchmark.md
docs/validation/online-mt-self-review.md
requirements-api.txt
requirements-dev.txt
tests/api/conftest.py
tests/api/test_online_mt.py
tests/api/test_online_mt_benchmark.py
```

No database migration is needed: the existing generic processing tables store the new versioned method/request/result receipts. Private original data, all earlier `.pytest-tmp-mt-*` directories, failed/successful `data/raw` test outputs and both virtual environments are preserved and excluded from commits. The [stable contract](../data-contract/02_online-edi-mt.md) is the frontend-agent and actual-host harness handoff. Related issues #32, #40, #47, #48, #38 and #80 remain open where their full scope exceeds this bounded backend. This is review-only work for a draft PR to develop, not merge/deployment authority.

Follow-up: the owner authorized actual-source MT reconciliation into an ignored candidate. [Its receipt](mt-source-reconciliation.md) now establishes all 24 fresh condition solves, 72 numerical result replays, actual bootstrap refits and a freshly regenerated cl061 QC-only screen. This resolves the MT contribution's candidate computation/replay work, not the full-release assembly, canonical provenance guard, product acceptance or actual-host gate. Online compute/scientific source bytes remain unchanged from `7b69404`.
