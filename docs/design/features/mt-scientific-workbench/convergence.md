# Selected-project MT frontend: local convergence and independent-review handoff

Ready for review: [PR111 to develop](https://github.com/fsantibanezleal/CAOS_Geophysics/pull/111). Not merged or deployed.

2026-10-03. Frontend-only unit; no deployment, public activation, main promotion or geological recovery claim. Requirements/design/tasks were pushed before code as `3ac149e`. Implementation milestone `8f6e870` and real-worker QA milestone `2f27eb6` were pushed separately. The branch starts at reviewed PR103 (`9b0cbe5`) and incorporates reviewed develop changes; the final PR diff contains only frontend, this feature's documents, and local frontend QA helpers.

Originally tested implementation revision: `3bd0e8757cd0a228c06fcb1afd20e011ebd179bf`, incorporating develop `aff3549a008a499b8b075ca468fddc384b13ce39`. The owner independently pinned that implementation in a detached read-only review tree. Independent enabled and closed-profile QA passed. The subsequent authorized develop integration and fresh backend execution are recorded below; frontend and MT harness source remain unchanged.

## Fresh develop integration and actual backend QA

On 2026-10-03, after owner confirmation that PR97 (including PR100/106 ancestry) and the preceding PR109 transform integration were merged, this task branch normally merged `origin/develop` at `6050100aeb3d1d482eefa1856ac67b2bc04b5bb1`. The merge is `1f6db811f914cc12c3f6e3f8ae43a66d47f9e62a`, with parents `7af8b7381e457de1e138d3198ddf14bd705929cd` and that exact develop revision. There were no conflicts. `git diff --quiet 3bd0e87 -- frontend` and the corresponding MT harness/fixture comparison pass: the complete frontend, not just MT panels, is unchanged from the independently reviewed pin. No course, Research, citation or canonical authoring occurred. Reviewed develop changes are inherited, not authored by this PR.

Actual API/worker execution uses the clean read-only backend at `D:\_worktrees\geophysics-plan-convergence`, verified before and after QA to be exactly `6050100aeb3d1d482eefa1856ac67b2bc04b5bb1`, not the earlier `59f46c5` backend. Backend `app`, pipeline and EDI fixture paths remain clean. The same explicitly selected read-only online-MT interpreter and private loopback harness are used. Backend MT scientific source and the `app/` tree have no diff between the old parity revision and integrated develop; nevertheless the integrated checkout's real routes, migrations, worker and bundle verification were executed again.

Fresh gates on the merge revision:

- `npm test -- --reporter=dot`: 94 tests / 17 files pass, 1.31 seconds.
- `npm run build:single-origin`: TypeScript and single-origin build pass; Vite 4.49 seconds. This is the build served for browser QA.
- With `GEOPHYSICS_MT_QA_BACKEND_ROOT='D:\_worktrees\geophysics-plan-convergence'` and `GEOPHYSICS_MT_QA_ENABLE='isolated-test-only'`, the existing `npx playwright test --config playwright.mt.config.ts --reporter=line` passes 5/5 in 2.4 minutes. All five named actual API/worker tests run, including parameter effects, exported bundle re-import, scientific matrices, actual cl061 QC-only, failure/cancellation and session handling.
- With the same backend but opt-in cleared, the same command passes one closed-admission test with four intentionally inapplicable skips, 8.9 seconds. Actual public-default settings still deny MT submission.
- After browser QA finished, `npm run build` passes, including five static route entrypoints; Vite 3.36 seconds. Existing large-chunk warnings remain in both modes.
- `git diff --check` passes. Existing gravity browser evidence is historical, not represented as rerun in this integration step.

The enabled run spans `2026-10-03T08:49:31.792Z` to `2026-10-03T08:51:52.874Z`, reports zero browser errors, and indexes 714 fresh PNGs and six actual verified ZIP exports. The closed run also reports zero browser errors. Fresh evidence is separately retained in ignored `frontend/node_modules/.mt-qa/integrated-6050100/evidence/`:

| Fresh receipt | SHA-256 |
| --- | --- |
| `run-receipt-enabled.json` | `023b3dddb54f51a2b3a47111d433caa9a159ba32cd732cd35c32f6dbcbc6dafe` |
| `run-receipt-closed.json` | `adadab4d7cc79edbbd21f957ca28fc9e84199bfb8e6c877f3a53c1ad8576c28c` |

The fresh receipt binds the integrated backend commit and these measured source SHA-256 values:

| Source | SHA-256 |
| --- | --- |
| `app/mt_compute.py` | `688b4778746eca06d5b3c213966daa056c1f6819b8e4959687b2b1dd15a17ba4` |
| `app/mt_bundle.py` | `b651347bddf1ba009f1f7e37a9450e1e4c667ebf711657e183c87835ad6b4c87` |
| `data-pipeline/edi.py` | `1a6226f34cd36e3e30f6406a296c6f4e3bc38aa93ca5bda1d4f4428d3852b543` |
| `data-pipeline/electromagnetics.py` | `9e5bed8fbc28772a6c6c6ffe3128ea91b5aefafc2063f2da0b0b4283e592ce7a` |

The integrated run's `cl061-en-dark-1600-tensor-plot-0.png`, `en-dark-1600-residual-pointer-1.png` and `es-light-390-model-pointer.png` were directly inspected again: failed tensor criteria remain QC-only; complex residuals retain a common signed scale; the Spanish phone profile/readout retains imposed 350 m and infinite basement. This is representative inspection, not individual inspection of every capture.

Before execution, the previous evidence and test-results directories were parked within the same explicitly validated private QA parent; after execution, fresh outputs were archived separately and the original directories restored without changing their bytes. Original enabled/closed receipt hashes remain `e8c72c8bd23eb375515734de06d8e0e45e6752093dad28964236f7bdcbd2b69c` and `894278ea97e5b6855450f022430a4f11923ed06ca97a49de8dc8bb46e02f15c6`. The owner's detached-review receipts are untouched. No private artifacts were committed or published.

This closes the requested local develop/backend integration retest, not final main acceptance. No MT UI or test source was changed, no host/main action or deployment occurred, no scientific/canonical acceptance is inferred from this UI run, and default public flags/30% host admission remain unchanged. Owner-controlled PR integration and broader release gates remain separate.

## Owner-reported independent review

On 2026-10-03 the owner reported independent execution in `geophysics-mt-ui-review`, pinned to the exact implementation revision above, against the separate read-only `59f46c5` parity backend:

- 94 frontend tests passed.
- Single-origin build passed.
- Actual API/worker MT Playwright suite passed 5/5 in 2.4 minutes.
- MT contracts, MT client and harness source were reviewed; signed-residual, QC and phone-geometry images were visually inspected.
- The independent closed-profile check passed: one test, four intentionally inapplicable skips, 6.8 seconds.

Owner-reported SHA-256 receipts are stored under the review tree's ignored `node_modules`, separate from and without modifying this branch's original QA evidence:

- Enabled: `3430fa95447da2081ddf1a3b287d0df7e1d7e0bb47bed6402c64a0a4b114c34d`.
- Closed: `bf0bb65ac1cecb568d4763ea0eae758497b31848c8b841c6b668342317cae853`.

These are owner-reported independent results on the original pin, distinct from this branch's indexed local run receipts. That independent run released port 8877 and requested isolation pending PR97 integration. PR97 is now integrated into develop and the subsequently authorized fresh task-branch QA is recorded above. Final PR integration/code feedback remains owner-controlled; readiness for review is not merge, public activation or deployment approval.

## Earlier parity-backend execution and numerical evidence

QA reads the separate backend at `D:\_worktrees\geophysics-mt-bundle-parity`, pinned during execution to `59f46c5a945531e573ae6db611a1f860237e3ba5` (bundle parity correction). Its MT compute/parser/forward source is unchanged from the reviewed online implementation. The explicit interpreter is `D:\_worktrees\geophysics-ingestion-foundation\.venv-online-mt-oct3\Scripts\python.exe`, read-only. Bytecode is disabled. Migrated databases, submitted originals, private child snapshots, caches, worker receipts and screenshots live only under this checkout's ignored `frontend/node_modules/.mt-qa`. No scientific source, production service/configuration, canonical artifact or another checkout is written.

The enabled harness uses the actual authenticated cookie/CSRF API and separate worker, not intercepted scientific responses. It exercises UI register/verified login/project/original upload/declarations/envelope validation, M05 admission/result, same-dataset passing-QC M06 admission/result, immutable parameters, polling, durable failure, cancellation, source/conventions/resource receipts and export. A separate process with no opt-in flag verifies unavailable `pending_host_admission`, disabled submission and actual `409 host_admission_pending`.

| Actual input/run | Returned evidence |
| --- | --- |
| Original independent analytic 100 Ω m halfspace, 24 frequencies | M05 QC-only; M06 model `99.99999999999996` Ω m. Training component WRMS `6.67858089239387e-15`; held-out `6.807441840405618e-15`; 20 successful conditional draws. Truth stays null. |
| Original noisy rotated two-layer control, imposed 350 m, beta .001 | Model `[123.95373357320769, 11.874946645511898]` Ω m; training WRMS `.8912582206379487`, held-out `1.749623256877646`, unfitted -YX/all-frequency WRMS `1.1804083505123504`. |
| Same original, beta .5 | Model `[111.79342590636703, 12.011717364894004]` Ω m; different request SHA and actual selected model. |
| Same original, 420 m and seed 71402 | Model `[92.34223343304507, 11.373638525514318]` Ω m; different actual bootstrap arrays; unchanged frozen holdout mask. |
| Hash-pinned actual USGS cl061, 42 frequencies | Successful M05 only; all pooled scores fail threshold 3: XX `320.23326026462956`, YY `109.50787977874732`, antisymmetry `267.60003875190307`. No inverse/model/residual options, M06 disabled. Tipper missing frequencies `.0004882812` and `.0006915263` remain null. |
| Missing required tensor block | Actual worker job fails with `processing_failed`; no result instrument or export. |
| Worker stopped only inside isolated QA | Queued cancellation reaches cancelled; scientific arrays clear. Transport interruption aborts GET polling without faking API responses; resume re-reads actual status. Logout/reload removes private arrays and submission controls. |

Six actual successful bundles are downloaded through the frontend verifier and re-imported using the actual backend `app.bundle.verify_bundle`: halfspace M05/M06, layered low/high beta, layered changed thickness/seed, cl061 M05. They exclude original raw bytes. Frontend verification is MT-specific: exact bounded stored ZIP members, member SHA/bytes, immutable identity/conventions/source/environment, independent forward predictions, signed residual identity against **exported** predictions, objective normalization, training/holdout WRMS, percentile summaries/seeds and selected little-endian float64 model SHA. This checks serialization/physics consistency, not field calibration or uniqueness.

## Reproduction of the earlier parity-backend run

Run from the scoped checkout's `frontend` directory:

```powershell
npm test -- --reporter=dot
npm run build:single-origin
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
$env:GEOPHYSICS_MT_QA_BACKEND_ROOT='D:\_worktrees\geophysics-mt-bundle-parity'
$env:GEOPHYSICS_MT_QA_PYTHON='D:\_worktrees\geophysics-ingestion-foundation\.venv-online-mt-oct3\Scripts\python.exe'
$env:GEOPHYSICS_MT_QA_CLEAR_LAKE='D:\_worktrees\geophysics-ingestion-foundation\data\downloads\clear-lake\USGS-GMEG.2022.cl061.edi'
$env:GEOPHYSICS_MT_QA_ENABLE='isolated-test-only'
npx playwright test --config playwright.mt.config.ts --reporter=line
$env:GEOPHYSICS_MT_QA_ENABLE=''
npx playwright test --config playwright.mt.config.ts --reporter=line
npx playwright test --config playwright.processing.config.ts --reporter=line
npm run build
```

Results: 94 unit tests / 17 files pass; enabled MT browser suite 5/5 passes; closed profile 1 passes and 4 intentionally inapplicable scientific cases skip; existing gravity browser suite 5/5 passes. Both frontend build modes pass, with the existing large-chunk warning. Local evidence is intentionally ignored, not copied into the public app. The latest indexed runs write `frontend/node_modules/.mt-qa/evidence/run-receipt-enabled.json` and `run-receipt-closed.json`, recording actual backend commit/code hashes, test outcomes, runtime errors and artifact SHA/bytes. These are local evidence, not a deploy/release receipt.

The enabled run completed at `2026-10-03T08:12:57.962Z` (3.8 minutes) and indexes 714 current-run PNG screenshots and six actual ZIP exports, with no browser runtime errors. The closed profile completed at `2026-10-03T08:13:58.562Z` (16.8 seconds including harness startup), also with no browser runtime errors. Gravity regression completed in 36.8 seconds. `git diff --check` also passes. Representative inspected artifacts, relative to the local evidence directory:

- `cl061-en-dark-1600-tensor-plot-0.png`: actual failed tensor QC, no inverse.
- `en-dark-1600-residual-pointer-1.png`: signed common-scale complex residuals and actual selection.
- `es-light-390-model-pointer.png`: phone imposed-layer profile and selected-layer readout.
- `en-dark-390-touch-pinch.png`: actual Chromium two-finger zoom/readout.
- `closed-admission.png`: default-closed authoritative admission.

The full capture matrix is indexed; rendered human inspection covers representative artifacts, not a claim that every one of the 714 images was individually inspected. The owner's independent image and numerical/bundle review remains separate.

| Requirement | Local convergence gate |
| --- | --- |
| MTV-01 / MTV-09 | Strict typed contracts, adversarial unit cases, six actual frontend-verified exports re-imported by the backend verifier. |
| MTV-02 / MTV-03 / MTV-10 | Actual upload/envelope/admission/job lifecycle; actual cl061 QC-only; malformed failure/cancellation/logout; separate default-closed profile. |
| MTV-04 / MTV-06 / MTV-07 | Actual M05/M06 arrays, all seven scientific views, frozen protocol/control tables, conditional and solver diagnostics, inspected matrix examples. |
| MTV-05 / MTV-12 | Unit parameter bounds and actual changed beta/thickness/seed requests/results; immutable parameters and unchanged holdout mask. |
| MTV-08 | Unit coordinate/partition/residual mapping and browser linked selection, signed shared scales, keyboard/brush/pan/zoom/reset/touch. |
| MTV-11 | Both build modes, six-route selected-project integration, full EN/ES/theme/size capture matrix, representative rendered inspection. |

## Scientific visual/interaction matrix

EN/ES × light/dark × 1280×800 / 1600×900 / 2560×1440 / 390×844. The M06 matrix visits all seven views, all response quantities, both signed complex residual components, pooled/full tensor QC, control tables, imposed layer selection, conditional sample/interval/seed/failure tables, solver/objective/local diagnostics. The actual failed cl061 matrix visits response and tensor/QC/ancillary tipper in all 16 combinations; inverse views remain absent. Captures include tops, each chart, intermediate/horizontally scrolled tables and bottoms. The phone matrix executes actual pointer/touch selection and two-finger pinch through Chromium input, not injected application data. Exact-value tables remain accessible.

Rendered inspection includes desktop EN/light response; EN/dark residuals and conditional samples; EN/light control summaries; ES/dark phone complex/tensor curves; ES/light phone imposed-layer pointer/readout; actual cl061 QC-only and default-closed admission. Phone scientific controls were compacted after inspection: navigation actions expand with the existing rail toggle and optional axes/units expand separately. Display-only SD-bar removal allows inspecting cl061's actual tensor without large reported errors dominating the scale, and does not change QC. Signed residual plots share symmetric zero-centred scales across both components and real/imaginary parts. View units convert observations, predictions and SD together; no rho/phase error bars or comparator curves are invented.

## Self-review and limitations

- No `app/`, worker, pipeline, canonical data, source-ledger, convergence-owner files, Methodology/Implementation or theory-agent paths are changed in the PR diff. `.venv-api` is not modified. Existing gravity's statistical-only contract and its tests remain intact.
- Fixed stale-result display at submission initiation; reselecting the same dataset/job no longer clears a result without triggering a reload. Project/dataset/job identity keys reset instrument state; requests abort on change/session loss. Result/export actions require actual success and typed identity checks.
- Source URLs accept only HTTP(S), no executable scheme/embedded credentials. Tests reject sign/unit/shape/truth/QC/mask/winner/prediction/residual/bootstrap/ZIP drift. Serialized model identity and near-zero residual handling are checked without recomputing residuals from a differently rounded independent prediction.
- M05 is necessary tensor QC, never an inverse. M06 fits XY only, imposed thickness, CPU float64 bounded TRF, frozen same-sounding holdout; -YX is unfitted validation. Objective records are residual evaluations, not accepted optimizer iterations. Conditional bootstrap is not geological posterior, simultaneous coverage, calibrated field coverage or independent-station generalization.
- Chromium/Windows loopback is the tested browser/runtime. Safari/Firefox, public Linux browser/service deployment, host resource acceptance and main promotion are not asserted. Actual host disk headroom remains below the unchanged 30% gate per the owner's receipt; public MT flags remain closed. Independent enabled and closed-profile QA passed; final integration acceptance remains pending. Owner-reported checks are recorded separately above.

## Scoped changed paths

- Feature SDD/handoff: `docs/design/features/mt-scientific-workbench/{requirements,design,tasks,convergence}.md`.
- Typed frontend: `frontend/src/api/{mt-contracts,mt-processing,processing-contracts,upload-metadata}.ts`. Existing gravity contract changes export shared validation primitives only; EDI declarations gain optional explicit scientific conventions.
- Selected-project views: `frontend/src/components/{MtProjectWorkbench,MtScientificInstrument,ProjectProcessingWorkbench,ScientificPlots}.tsx`, `frontend/src/components/mt-view-data.ts`, `frontend/src/styles.css`.
- Unit and actual-worker browser QA: `frontend/src/test/mt-processing.test.ts`, test-only `frontend/src/test/fixtures/mt-actual.json`, `frontend/e2e/mt-workbench.spec.ts`, `frontend/playwright.mt.config.ts`, `tests/ui/{mt_contract_fixtures,mt_devserver}.py`.
