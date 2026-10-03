# M01 local transform convergence and handoff

Date: 2026-10-03. Verdict: local equivalent-source/upward-continuation workflow passed on independently generated controls and strictly admitted user-declared inputs. The initial run/receipts below are historical bfa5c24 evidence; the current pre-merge receipt/parser hardening and its evidence are recorded in the final section. Full M01 remains unaccepted. Field eligibility is closed for unresolved datum, uncertainty or original processing lineage; the actual USGS field gate is open. No protected field source bytes were read, copied or published by this unit. No backend, frontend, canonical arrays, station-correction code, main-owned intake files, deployment or shared environment was edited.

Branch: task/geophysics-m01-transforms, created in the original owned gravity worktree from develop `9b0cbe5750cdf2b778b269f415c0c4613bd16d5e`. Research and pre-code feature SDD were pushed first in `de059c2`. The derivative geometry seam was disclosed: correction output stays unchanged and a separately declared station-keyed metric Cartesian mapping is required. No API approval follows from these local results. Current concurrent develop changes are main-owned; this branch is an additive integration candidate, not a develop promotion.

## Named local gates

Initial gates are in tests/numerics/test_gravity_transforms.py; 25 parametrized tests passed at bfa5c24. Current extended gate counts are recorded below.

| Requirement | Exact gate | Verdict |
| --- | --- | --- |
| R-T01 | test_contract_lineage_and_originals | PASS: replay, originals, masks and no second correction |
| R-T02 | test_independent_prism_and_continuation | PASS on cases 0, 1, 2: physical kernel and station/elevated predictions |
| R-T03 | test_blocked_selection_no_holdout_leakage | PASS: outer blocks and inner membership; heldout perturbation leaves selected model/grids identical |
| R-T04 | test_masks_condition_and_covariance | PASS: hull AND distance, nulls, checkpoints, independent transfer system and real correlated-covariance propagation |
| R-T05 | test_strong_negative_controls | PASS on 12 parameter/physics mutations |
| R-T06 | test_nonuniqueness_is_not_density | PASS: distinct layer depths fit within noise with substantially different coefficient norms |
| R-T07 | test_export_and_paired_scripts | PASS: complete hashed export, immutable/protected paths, mismatched request and duplicate-key CLI rejection |
| R-T08 | test_theory_and_svg | PASS: source-linked substantial guide, exercise and themed SVG; additionally rendered and inspected |

Additional gates: test_missing_lineage_geometry_and_high_noise, test_unmet_height_precision_and_resource_rejection, test_shared_error_and_covariance_contract, test_conservative_bounds_are_not_standard_deviations. A conservative contribution sum cannot become an SD: require a cited covariance within the recorded bound, or reject. Supplied covariance uses real diagonal-weight fitting and full conditional covariance propagation; this is not GLS.

Final regression command:

```powershell
.venv-m01/Scripts/python.exe -m pytest -o addopts='' tests/numerics/test_gravity_transforms.py tests/numerics/test_gravity_processing.py tests/data/test_sources.py tests/data/test_ingest_dispatch.py -q --disable-warnings
```

Result: **67 passed, 1 skipped in 18.37 s**. The skipped existing correction test requires main's actual principal-fact archive through M01_PRINCIPAL_FACT_ARCHIVE; no synthetic bytes replaced it. Local correction tests remain unchanged, including the exact product-SDD test_station_correction_lineage gate. The transform-only suite also passed (25 tests). Ruff check/format checks pass, pip check reports no broken requirements. Tracked-content/template/CI-budget guards are run on the staged scoped files before commit. The existing SDD ledger structural check remains 1 fail / 18 unresolved, intentionally unchanged; it is not a whole-product acceptance claim.

## Independent physics and honest coverage

Each control has 196 original stations and four reversible masks. Newton volume integration of three offset buried prisms produces the input; the fit uses a different scalar inverse-distance operator. Surveys are irregular, nonconstant-height, rotated and translated, with varying prism geometry and positive/negative contrasts. Gauss-Legendre orders 16 and 22 converge before comparison to the pinned analytic prism engine. These are original labelled synthetic controls, never field observations.

| Case | Supported holdout | Unsupported holdout | Holdout RMSE mGal | Maximum sampled elevated-grid RMSE mGal |
| --- | ---: | ---: | ---: | ---: |
| 0 | 30 | 13 | 0.025773490664026982 | 0.008402996286226466 |
| 1 | 33 | 4 | 0.03422442613473831 | 0.012109760616413395 |
| 2 | 23 | 21 | 0.025587092837193827 | 0.00768831657953749 |

The last geometry has substantial unsupported outer coverage; its reported error is not an all-station score. Predeclared independent tolerances are 1e-7 mGal for converged/analytic prism parity, 1e-12 m⁻¹ for inverse-distance Jacobian parity, and 0.1 mGal for authored covered station/elevated-grid RMSE. Actual analytic/volume discrepancies are below 4e-14 mGal. These smooth buried controls do not establish performance on shallow masses, large surveys or field uncertainty.

Selection uses inner blocked training only, then full-training stability. Case 0 selects depth 700 m, damping 100 and height 300 m. Conditional covered maximum SDs at heights 300, 600 and 1000 m are 0.0148727120, 0.0090646791 and 0.0061991751 mGal. Weaker damping candidates can fail coverage, condition or engine/transfer parity; failed reasons remain visible, and tolerances were not loosened. Different mathematical layers fitting within noise show nonuniqueness, not inferred density or basement depth.

## Environment, receipts and render evidence

Owned isolated .venv-m01, Python 3.12.10 Windows x64; existing NumPy 2.2.6, SciPy 1.15.2, Boule 0.5.0, Harmonica 0.7.0, Verde 1.9.0 and scikit-learn 1.9.1 stay pinned. Only the owned environment was extended with Matplotlib 3.10.8 and its exactly matched plotting dependencies. requirements-m01-transforms.txt includes the unchanged complete correction pins. No unpublished package, global Python fallback or other agent's environment modification occurs.

[Verification receipt](evidence/verification.json) records all three controls, actual primary-document byte hashes/HTTP 200 receipts, installed engine source hashes and official downloaded plotting-wheel URLs/hashes. Reproduce with scripts/check_m01_transforms.py, selecting a new ignored output filename; existing evidence is never overwritten. This auditor acquires only public official engine documentation, not field providers. Original control definitions and all full station/grid arrays remain in ignored local bundles, not canonical products or protected-source Git commits.

Historical bfa5c24 transform module SHA-256: `30b4135a1501375653596e8d57cb599c474a4af18c2f4f7c19b473b18de22e34`.

The actual PowerShell and WSL/bash runs both succeed using the same owned Windows environment. Explicit WSL path conversion is necessary; a first smoke invocation exposed the path seam and was fixed before the passing paired runs. [Control export receipt](evidence/control-export.json) records the complete bundle file hashes and equal paired result-file SHA-256 `9a0c4226a1eff9f1b37563133a5beadf68ec45ddd1ecffccc797bbe1fa46d926`. Result identity digest is `8aa77e96e2931ec0dbfddd2a9001a3f256ec5378318a264371539ef699ac44d6`. Full bundles are ignored data/raw/gravity-m01-transforms/ps-reviewed and sh-reviewed.

Maps are 3150×2310 PNG plus vector SVG; diagnostics are 3150×2100 PNG plus SVG. All are labelled synthetic, in mGal with metric equal-aspect axes, signed residual scales, covered/null regions and explicit conditional-error limitations. Original control figures in [evidence](evidence/) were visually inspected in both themes. The hand-authored theory SVG was rendered using a separate headless Edge profile with explicit prefers-color-scheme emulation, not inferred from OS defaults; every text bounding box is in the 1200×820 canvas. [SVG receipt](evidence/svg-render.json) records backgrounds, engine and screenshot hashes. Its light/dark PNGs were inspected. This is static scientific document QA, not EN/ES app/browser acceptance.

## Exact scoped files

- data-pipeline/gravity_transforms.py
- data-pipeline/gravity_transform_controls.py
- data-pipeline/gravity_transform_figures.py
- data-pipeline/requirements-m01-transforms.txt
- scripts/run_m01_transforms.ps1
- scripts/run_m01_transforms.sh
- scripts/check_m01_transforms.py
- scripts/render_m01_transform_svg.mjs
- tests/numerics/test_gravity_transforms.py
- docs/methods/gravity-processing/gravity-processing.md
- docs/methods/gravity-processing/02_equivalent-source-transforms.md
- docs/methods/gravity-processing/assets/equivalent-source-transforms.svg
- docs/design/features/m01-gravity-transforms/research.md
- docs/design/features/m01-gravity-transforms/requirements.md
- docs/design/features/m01-gravity-transforms/design.md
- docs/design/features/m01-gravity-transforms/tasks.md
- docs/design/features/m01-gravity-transforms/convergence.md
- docs/design/features/m01-gravity-transforms/evidence/verification.json
- docs/design/features/m01-gravity-transforms/evidence/control-export.json
- docs/design/features/m01-gravity-transforms/evidence/svg-render.json
- docs/design/features/m01-gravity-transforms/evidence/maps-light.png
- docs/design/features/m01-gravity-transforms/evidence/maps-dark.png
- docs/design/features/m01-gravity-transforms/evidence/diagnostics-light.png
- docs/design/features/m01-gravity-transforms/evidence/diagnostics-dark.png
- docs/design/features/m01-gravity-transforms/evidence/theory-light.png
- docs/design/features/m01-gravity-transforms/evidence/theory-dark.png

## Remaining full M01 gates and ownership

1. Actual eligible USGS/field bytes, rights and source identity remain main-owned. The 2929-row transformed author data remain ineligible, with unresolved datum/error/original-lineage gaps and a size beyond this reviewed dense vertical. No guessed σ, zWGS84 relabelling or synthetic replacement closes this gate. Already tide/drift/reference/Bouguer/terrain-processed principal facts never receive duplicate corrections.
2. Independent field comparisons must resolve datum/tide/reference, correction definitions, component, uncertainty/correlation, fixed-geometry limits, source-free domain and meaningful sampling before parameter tuning. A supplied citation is a user declaration, not automatic verification of a CRS or geological model.
3. Main owns authenticated upload, immutable versioned correction/transform children, project/worker/export integration and private rights enforcement. Existing CSV outlier flags are not a correction dataset. This unit offers ordinary local functions and exact inputs, not an API adapter.
4. Actual host admission remains false/unmeasured: upper-bound wall/RSS/scratch, timeout/cancel/crash recovery, quotas, concurrency and pinned runtime parity must pass before online activation. Local ceilings are not host benchmarks.
5. Main owns selected-project EN/ES theme/device displays, app interaction, the full method wiki integration and broader product release gates. This branch neither merges nor deploys and does not close issue #43.

Reviewable handoff: [PR #109 to develop](https://github.com/fsantibanezleal/CAOS_Geophysics/pull/109), implementation bfa5c24, [named-test self-review](https://github.com/fsantibanezleal/CAOS_Geophysics/pull/109#issuecomment-5966949751). At opening it was open/mergeable, with no required checks reported; that is not a claim of green CI. The separately requested next-feature [station API proposal](../m01-station-api-proposal/design.md) is design-only, awaiting main approval/ownership and MT runtime convergence; its four documentation files are additional scoped handoff paths, not backend implementation.

## Current pre-merge review hardening

Main independently identified that initial admission replayed physics but checked only some processing fields. This is fixed, not described as a previously passing gate. All known processing keys are now required; extra/missing keys reject. Method, input/output/config/engine/module/errors/error model/components/warnings/full acceptance are checked against canonical deterministic replay. process_survey emits no generated timestamp. Python is validated as a compatible release declaration for the reviewed CPython 3.12.x lane, not required to equal the current patch or asserted to authenticate the original runtime. The original declaration is preserved, with runtime origin explicitly unverified and the source interpreter implementation explicitly unspecified.

Input hashes must match an independently reconstructed canonical earlier state: converted observation floats or a verified earlier history prefix with unchanged station/metadata fields. Known gravity-to-Bouguer and Bouguer-to-terrain resumes pass; the current target cannot be its own input. Arbitrary/unrecorded original numeric serialization needs its exact parent and is explicitly rejected, not assigned a verified input hash. No arbitrary prior config/runtime is invented. gravity_processing.py remains byte-identical at SHA-256 `7863699269b491c2895bcf030d3fb65cf27ac32a652fce91112bc2c7c9c73321`.

The CLI reads at most 32 MiB plus one sentinel, checks actual read length rather than a stale pre-read stat, requires a regular file/strict UTF-8, and rejects duplicate keys, nonfinite constants, overflowing numeric literals and structural depth above 16 before any engine/output call. The depth scanner ignores quoted brackets/escapes. Tests explicitly exercise a changed read despite a small stat, invalid nesting/encoding/constants, preserved compatible patch declarations, genuine known-stage resumes, and rehashed stale/missing/extra receipt fields.

Current extended regression: **88 passed, 1 existing actual-archive test skipped in 19.59 s**. There are 46 transform tests, including the new test_full_processing_identity [17 mutations], test_reconstructable_resume_and_python_provenance, test_unreconstructable_input_serialization_is_explicit, test_bounded_strict_request_reader and test_committed_scientific_evidence. Main separately reported its actual-author-archive negative admission control PASS; this branch did not reread or publish those private bytes, and that negative control is not modelling eligibility or full M01 acceptance.

Current source/module/result receipts are separate [verification-current](evidence/verification-current.json) and [control-export-current](evidence/control-export-current.json), with explicit [history](evidence/history.json). Earlier verification/control-export/svg receipts remain unchanged and are not retroactively claimed to cover the new gate. The numerical models, blocked metrics, selected parameters and maps are unchanged; all four newly rendered map/diagnostic PNGs match the committed prior images byte-for-byte, verified by their actual hashes. Static theory SVG/source and screenshots are unchanged. The current evidence-integrity test validates these screenshots/receipts alongside all three real-engine independent controls.

Current transform module SHA-256: `d11d0f207c89c308c9f8711da2a31b84b8adaeb0c12597a5ecc89ce527fdecf0`.
Current paired result identity digest: `da5e80919f8316a71f710d381736ddc3b6637b0f3da948c937d59664632eb2ae`.
Actual PowerShell/WSL result-file SHA-256: `c3c94f316b60ec4badb7184d89181c514d66660939d3c75cf99d6a5e67e4f9b8` (both identical).
Ignored actual runs: data/raw/gravity-m01-transforms/ps-review-fix and sh-review-fix.

Additional exact scoped paths since the first handoff: evidence/verification-current.json, evidence/control-export-current.json, evidence/history.json under this feature, and docs/design/features/m01-station-api-proposal/validation-plan.md. The prospective next API plan now distinguishes private storage permission from public redistribution rights, exact correction-schema absence of masks, and correction error bounds from transform SDs. Its acceptance/state/error/ownership matrix is design-only; no API edits, adapter implementation or host approval occur.
