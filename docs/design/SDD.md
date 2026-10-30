# CAOS Geophysics product software design

Status: owner-approved product scope with later user clarifications recorded below. Implementation and release acceptance are separate states; this document does not claim the current live release satisfies the replacement design.

## Problem and non-goals

Geophysical observations constrain subsurface physical properties through method-specific forward operators. Inversion is conditional on acquisition geometry, data errors, parameterization, starting/reference models and regularization; a low residual does not identify a unique geological model. The product must let readers inspect the complete path from source data and processing through forward and inverse calculations, diagnostics, interpretation and reproducible export. Its local repository must independently support the documented CPU and GPU workflows.

The product spans gravity, magnetics, magnetotellurics, electrical resistivity, seismic arrivals, acoustic full-waveform inversion, joint potential-field inversion and learned methods. The same declared data and result contracts govern local workflows, client-side calculations and bounded authenticated server jobs. Synthetic cases state their known truth and limits; field cases never receive invented truth.

Non-goals are unique geological recovery claims, unsupported format guessing, browser animation presented as a solve, synthetic performance described as field validation, unlicensed redistribution, arbitrary full-survey FWI on the bounded VPS, or a second public application origin. Full FWI, large 3D sweeps and training remain reproducible local GPU workflows. Public visitors can read scientific content and run the validated client-side calculations. Account-gated projects, uploads and server jobs use the internal account store; SMTP, external email verification, off-host backup and production-scale account administration are not prerequisites for the current owner-tested system.

## Executive brief

The Introduction opens with the shared-shell executive view of the geophysical inverse problem, then offers the technical view. Content is researched, bilingual, source-linked, product-neutral and rendered by the installed shell component.

Data file: content/executive.json

## Research basis

The research review maps each covered method to its classical foundations, current implementations, executable engines, data availability, rights and limitations. SimPEG supplies a modular framework for geophysical forward simulation and gradient-based parameter estimation (Cockett et al., 2015, https://doi.org/10.1016/j.cageo.2015.09.015). USGS describes the indirect density and magnetization sensitivity of potential-field observations (https://pubs.usgs.gov/fs/fs-0239-95/). Harmonica and Choclo provide maintained potential-field processing and kernel functions (https://www.fatiando.org/harmonica/latest/ and https://www.fatiando.org/choclo/latest/). EDI is an established MT transfer-function exchange format (https://pubs.usgs.gov/ds/0901/edi_data.html). Geophysical resolution and uncertainty analysis includes sensitivity, resolution and covariance methods (https://doi.org/10.1007/s10712-019-09567-3). FWI is nonconvex and susceptible to cycle skipping (Virieux and Operto, 2009, https://doi.org/10.1190/1.3238367). The primary references, deviations and source-to-content map are recorded in docs/research/review.md and the method chapters.

Notebook source records also cite these implementation and data references: ObsPy stream API (https://docs.obspy.org/packages/autogen/obspy.core.stream.stream.html); SimPEG joint cross-gradient tutorial (https://docs.simpeg.xyz/latest/content/user-guide/tutorials/13_joint_inversion/plot_inv_3_cross_gradient_pf.html); PhaseNet method (Zhu and Beroza, 2019, https://doi.org/10.1093/gji/ggy423), STEAD dataset (Mousavi et al., 2019, https://doi.org/10.1109/ACCESS.2019.2947848), and implementation (https://github.com/AI4EPS/PhaseNet); MTpy v2 (https://github.com/MTgeophysics/mtpy-v2); OpenFWI (https://github.com/lanl/OpenFWI); USGS potential-field methods (https://pubs.usgs.gov/tm/02/d04/tm2d4.pdf); Devito FWI tutorial (https://www.devitoproject.org/examples/seismic/tutorials/03_fwi.html); Harmonica API (https://www.fatiando.org/harmonica/latest/api/index.html); Verde spatial train/test splitting (https://www.fatiando.org/verde/latest/api/generated/verde.train_test_split.html); PyGIMLi Koenigsee example (https://www.pygimli.org/_examples_auto/2_seismics/plot_04_koenigsee/ and https://www.pygimli.org/_examples_auto/2_seismics/plot_04_koenigsee); PyGIMLi ERT field-data example (https://www.pygimli.org/_examples_auto/3_ert/plot_02_ert_field_data/); PyGIMLi inversion guide (https://www.pygimli.org/user-guide/inversion/ and https://www.pygimli.org/user-guide/inversion); and the USGS Clear Lake MT data release (https://www.usgs.gov/data/magnetotelluric-data-clear-lake-region-northern-california).

UNVERIFIED: live host capacity for the replacement release, Zenodo concept DOI and latest report version, and broad transfer of learned models to field geology remain unverified and cannot be inferred from local solver results.

## Sizing and contracts

The activated service separates FastAPI control-plane work from an unprivileged numerical worker. SQLite with migrations stores accounts, projects, job state and metadata. Project files and derived artifacts live outside the web root. Guests can read released content and use validated browser tools; project creation, uploads and VPS computation require an authenticated account and explicit operation. Accounts and projects are plural and owner-scoped.

The persistent data graph is source record → immutable raw asset → validated dataset version → processing run → compatible survey/model → solver job → evaluation → immutable result/export. Source records include provider, exact URL or local origin, citation, retrieval time, format, rights decision, expected and observed byte count, SHA-256 and attribution. Raw bytes are never replaced by derived data. Archive count, expansion ratio, size, path traversal and nesting are bounded. Unknown rights prohibit public mirroring.

Observation datasets record modality, named dimensions and order, CRS or explicit local coordinates, horizontal/vertical datum and sign, units, survey geometry, values, masks and reasons, uncertainty, correction history, parser version, parent hashes and QC verdict. Ambiguous units, geometry, datum, component orientation or sign cannot pass into a solver by guessing. Non-finite values are masked with a reason or rejected; outliers remain flagged unless an explicit reversible exclusion is approved.

Processing runs record input versions, ordered transform DAG, parameters, code/environment digest, output versions, masks, uncertainty, warnings, resource measurements and hashes. Jobs record owner/project, data version, method/version, lane, geometry, discretization, parameterization, references, bounds, covariance/weights, regularization, seed, preflight estimate, admission, lifecycle, progress, worker and measured resource use. Retries create new attempts. Results carry schema, inputs and hashes, axes/dimensions/units, observations, predictions, signed/normalized residuals, physical model, objective terms, stopping reason, sensitivity/coverage or an explicit reason unavailable, uncertainty definition, held-out partition, display arrays, provenance, rights and per-file hashes. Known truth is allowed only for synthetic cases. Export and re-import preserve this identity and provenance.

Format adapters are separate and fail closed: gravity station tables; magnetic line tables and grids; EDI and selected MTH5; ERT electrode/ABMN; MiniSEED with StationXML and picks; source/receiver/pick tables; and bounded SEG-Y. EDI is transfer-function data, not raw time series. Unsupported or over-limit data receive a clear offline recipe or rejection. The local stages are ingest → preprocess → dataset/split → feature extraction → train → infer → evaluate → export → validate. Non-learned training emits a typed not-applicable record; learned training writes actual checkpoints, split hashes, train-only normalization and history.

## Technology and versions

| Layer | Contract and pinned implementation |
|---|---|
| Shared interface | `@fasl-work/caos-app-shell` exact version 0.19.9; shell owns design tokens, fonts, controls, page structure and route chrome. |
| Routes | App, Introduction, Methodology, Implementation, Experiments, Benchmark; App at `/app`; `/` opens Introduction. |
| Web | React 19, TypeScript, Vite, Three.js, uPlot, ONNX Runtime Web; exact lockfile is `frontend/package-lock.json`. |
| Numerical pipeline | Python 3.12; exact scientific and notebook pins in `requirements-precompute.txt`, `requirements-gpu.txt` and `notebooks/requirements.txt`. |
| API runtime | Pinned FastAPI/runtime requirements, isolated from the offline pipeline environment; numerical work runs in the separate worker. |
| Data and artifacts | Versioned JSON contracts, explicit axes/units, content hashes and reviewed source ledger; public build copies only allow-listed derived artifacts. |
| Template | CAOS_PRODUCT_TEMPLATE 0.13.001, recorded in `.template-version`; current guards and runner are copied from the exact template release. |

## Resources

| stage | memory | disk | time | where it runs |
|---|---|---|---|---|
| bake | GPU VRAM and host peak RSS must be recorded in each run receipt; latest full-release peak is not yet sealed | derived artifacts are hashed; full clean-build disk peak is not yet measured | method-specific; full release duration is not yet recorded as a single reproducible measure | local Python 3.12 environment, CUDA where the pinned engine supports it |
| tests | bounded by each test process; full Vitest currently requires retained external M11 fixtures | fixtures and temporary runs are outside the repository | per-test and total timings must be captured by the validation run | local CPU/GPU environments; CI runs only bounded guards and committed-artifact checks |
| build | local TypeScript/Vite build completed in 86 seconds; peak RSS not captured | Vite reports a 14.24 MB ONNX wasm asset before compression; clean-build disk peak not captured | 86 seconds in the 2026-10-29 local run | `frontend/`; no training or scientific recomputation |
| deploy | VPS replacement capacity is unverified; public cutover is prohibited until measured admission passes | current plus two rollback releases are retained by policy; replacement disk use is not yet measured | release duration is not yet measured | the single canonical ML VPS origin, `https://geophysics.ml.fasl-work.com/` |

Unmeasured capacity is an open release gate, not an implied unlimited server allocation. Browser calculations consume client resources and are bounded by their validated contracts; the VPS worker admits only methods with measured per-method limits.

## Lanes

| Lane | Work | Activation condition |
|---|---|---|
| Public browser | Read the wiki, inspect rights-cleared cases and released outputs, run explicitly validated client-side calculators and process compatible local files without upload. | Browser memory, cancellation, unit, result and offline behavior validated for that operation. |
| Authenticated VPS | Create owned projects, upload/import files, run bounded processing and solver jobs, retrieve/export immutable results. | Account and ownership checks, preflight resource estimate, worker isolation, per-method limits, cancellation, cleanup and actual-host test all pass. |
| Local CPU | Ingest, QC, preprocessing, classical inversions, benchmark reproduction and export. | Ignored repository-local environments and documented exact commands; all resource use recorded. |
| Local GPU | Supported FWI, neural training, large matrices and full bake. | Explicit device selection, pinned environment, seeded protocols, held-out splits, checkpoint identity and independent CPU replay. |
| Static artifact replay | View baked arrays and computed optimizer states where the release explicitly labels them. | Artifact hashes and scientific receipts match; replay is never represented as an online inverse calculation. |

## Method ladder

| id | tier | method | acceptance criterion | gate |
|---|---|---|---|---|
| M-1 | classical | Gravity station corrections, reference datum, uncertainty propagation and the no-double-correction chain. | Correction lineage, units, datum and uncertainty reproduce from immutable input; invalid or already-corrected data are rejected before derivation. | `tests/numerics/test_gravity_processing.py::test_station_correction_lineage` |
| M-2 | sota | SimPEG weighted 3D gravity prism inversion, compared with the bounded least-squares reference on the same survey and noise model. | Independent prism forward values, solver objective, held-out predictions and sensitivity reproduce within frozen tolerances; no grid cell is presented as resolved geology. | `tests/numerics/test_gravity_l2.py::test_real_engine_forward_and_geometry_identity` and `tests/numerics/test_gravity_l2_selection.py::test_complete_locked_l2_control_matrix` and `notebooks/en/02-gravity/03-m02-prism-forward-and-inverse-limits.ipynb` |
| M-3 | classical | Aeromagnetic line, tie-line, height and blocked-holdout processing with physically supported continuation. | A withheld flight line remains outside fitting; continuation matches the analytic harmonic transfer and unsupported grid cells remain masked. | `tests/numerics/test_magnetic_processing.py::test_blocked_line_holdout` and `tests/numerics/test_magnetic_continuation.py::test_single_harmonic_decays_by_analytic_fourier_transfer` |
| M-4 | sota | SimPEG induced-magnetization prism forward model and physical objective/derivative construction with Choclo controls. | Independent field-vector and objective-gradient checks pass; the existing fit-fold evidence is explicitly not accepted as a completed survey inversion until a full nonzero inverse and held-out evaluation are recorded. | `tests/data/test_magnetic_fit_assembly.py::test_actual_nonzero_simpeg_fit_assembly_has_physical_objective_derivative` and `tests/numerics/test_magnetic_forward.py::test_m04_exact_magnitude_gaussian_gradient_against_choclo_observations` and `notebooks/en/03-magnetics/03-m04-induced-prism-forward.ipynb` and `notebooks/en/03-magnetics/04-m04-fit-objective-validation.ipynb` |
| M-5 | classical | MT EDI tensor, variance, rotation, tipper and dimensionality quality control before method eligibility. | Independent component scores and rotation invariance reproduce; an ineligible sounding such as cl061 cannot enter a 1D inverse. | `tests/numerics/test_mt_field_qc.py::test_field_scores_against_independent_component_formula_and_tipper_mask` and `tests/numerics/test_mt_field_qc.py::test_ineligible_never_becomes_inverse` |
| M-6 | sota | Layered-earth MT complex-impedance forward response and bounded 1D inversion on eligible components, cross-checked with MTpy. | Complex conventions, masks, independent forward values and matched recovered models reproduce; cl061 remains QC-only because its necessary 1D screen fails. | `tests/api/test_online_mt.py::test_inverse_parameter_effect_and_independent_oracle` and `notebooks/en/04-mt/03-mt-state-of-art.ipynb` |
| M-7 | sota | PyGIMLi 2D ERT inversion with topography, reciprocal/QC checks and the product's mesh and split contract. | Homogeneous and flat controls, topographic factors, held-out residuals and failed-inverse status reproduce; absent or restricted field data are never represented as executed. | `tests/numerics/test_ert.py::test_topographic_factor_and_inverse` and `notebooks/en/05-ert/03-ert-state-of-art.ipynb` |
| M-8 | classical | MiniSEED/StationXML waveform response, filtering and classical STA/LTA or matched-arrival picking. | Instrument response, units, filter provenance, parameter effects and catalogue-reference noninterference reproduce; unsupported response epochs fail closed. | `tests/numerics/test_waveform_picks.py::test_response_epoch_and_classical_picks` and `tests/numerics/test_waveform_picks.py::test_actual_parameter_effects_and_reference_noninterference` |
| M-9 | sota | First-arrival travel-time tomography with source/receiver geometry, bounded velocity, ray coverage and independent LSQR comparison. | Homogeneous travel times, independent forward replay, held-out shots and sensitivity to start/mesh reproduce; the straight-ray limits and absent field eligibility remain explicit. | `tests/numerics/test_traveltime.py::test_homogeneous_time_and_field_holdout` and `tests/numerics/test_traveltime.py::test_independent_process_fit_reproducibility` and `notebooks/en/08-learning/04-first-arrival-user-data.ipynb` |
| M-10 | sota | Devito/Deepwave acoustic full-waveform inversion with cycle-skip controls and product solver comparisons. | Wavelet, geometry, objective, gradient and held-out receiver diagnostics reproduce for the declared cases; no field-scale performance is inferred. | `tests/test_seismic_recovery.py::test_withheld_samples_do_not_influence_inverse_and_terminal_is_saved` and `tests/test_seismic_recovery.py::test_deepwave_refined_discretization_and_adjoint` and `notebooks/en/06-seismology/03-seismic-state-of-art.ipynb` |
| M-11 | sota | SimPEG cross-gradient joint potential-field inversion with shared mesh, active cells and negative controls. | Direct reference gradients and physical controls agree; independent fits, coupling choices and predictive conflict remain reported separately. | `tests/test_recovery.py::test_joint_conflict_verdict_and_optimized_uncoupled_reference` and `notebooks/en/07-joint/03-joint-state-of-art.ipynb` |
| M-12 | sota | Trained learned seismic-velocity inversion with family/acquisition-disjoint evaluation against the matched classical solver and an independent forward oracle. | Checkpoint, splits and predictions reproduce; both predeclared joint-OOD ratios remain reported, including the current learned-model failure. | `tests/learning/test_velocity_inversion.py::test_family_disjoint_checkpoint_and_forward_consistency` and `notebooks/en/08-learning/05-m12-velocity-checkpoint.ipynb` |
| M-13 | sota | PhaseNet-family learned P/S picking with event/station-disjoint evaluation and parity-checked browser inference on held-out STEAD traces. | Native/browser probabilities and picks agree on the declared held-out asset with rights and preprocessing hashes; curated parity is not population accuracy. | `tests/learning/test_phase_evaluation.py::test_matched_inputs_and_failed_picks` and `tests/learning/test_phase_browser_assets.py::test_model_and_benchmark_are_bound_to_public_manifest` and `notebooks/en/06-seismology/04-m13-learned-phase-picking.ipynb` |
| BS-1 | beyond | Geometry-normalized, physics-conditioned residual features for learned travel-time velocity refinement, proposed as a falsifiable product method. | On frozen fresh cohorts, compare the trained model with the matched classical solver and independent bilinear forward operator; preserve negative results and accept no advantage claim unless both predeclared test ratios are below one. | `tests/learning/test_velocity_physics.py::test_frozen_receipt_and_replay` |

## Beyond the state of the art

BS-1 tests whether correcting the dimensions of the backprojected travel-time residual and conditioning a bounded residual CNN on ray coverage improves the matched classical inverse on held-out realizations. The hypothesis is that the dimensionally consistent feature improves velocity and forward-data error under declared geometry shifts. The method normalizes each ray residual by path length, backprojects through the path matrix, divides by cell coverage, and supplies the bounded physical update with a coverage channel. The evaluation freezes disjoint train, validation, in-distribution, family-shift, acquisition-shift and joint-shift cohorts before training; model selection uses validation only. The completed 40-epoch GPU study selected epoch 40 but the CNN lost to the classical baseline, and all 160 joint-shift examples were flagged. This is a negative result, not a novelty or superiority claim. The experiment, source and receipts are in `docs/design/features/velocity-physics-refinement/` and `models/experimental/m12-physics-cuda-20261004/`.

## Cases

The release contains 20 original synthetic geological constructors across gravity, magnetics, MT, seismic, joint inversion and learning. The canonical v2 catalogue represents 120 case-condition artifacts; each case states the physical target, acquisition, noise, truth status, units, solver, regularization, evaluation and limitations. Grid cells are numerical parameterization, not geological resolution. No color scale or interpolation is evidence of added resolving power.

External examples use explicit source records and rights decisions. SimPEG tutorials are processed as ingestion examples, not field-validation benchmarks. Clear Lake `cl061` is QC-only because its transfer-function screen fails the necessary 1D eligibility checks. PyGIMLi Slagdump/Koenigsee data remain provider-linked where redistribution is not authorized. STEAD browser assets retain the reviewed license, attribution, transformation notice and exact manifest hashes; their held-out evaluation is distinct from synthetic M13 cases.

## Oracles

Scientific acceptance requires independent physical identities, sign/unit checks, shape and orientation contracts, derivatives where applicable, data/model separation, held-out evaluation, explicit failed controls and reproducible result hashes. The method matrix is M01-M13; each row has an executable engine, input contract, documented assumptions, named tests, output artifact, case coverage, limitation and local reproduction command. A method label, citation, architecture or selector is not an implementation.

Potential fields use independent Choclo/SimPEG prism checks and coordinate/sign oracles. MT uses complex-impedance identities, independent SciPy comparison, masks and a QC gate before inversion. ERT uses geometric-factor and homogeneous-half-space controls, reciprocal/QC checks, topography controls, held-out data and a separately pinned pyGIMLi comparison. Seismic solvers use homogeneous travel-time controls, independent forward calculations, stability and adjoint-gradient checks, cycle-skip cases and saved-state identity. Learned methods use group-disjoint splits, train-only normalization, checkpoint reload, per-group scores and matched classical predictions. Joint methods compare optimized single-physics baselines and disjoint-source controls. Field datasets never use synthetic truth scores.

The release ledger records pass, fail, unresolved or ineligible per requirement with the exact receipt and hash. A build, plot, low residual or HTTP 200 cannot substitute for a scientific oracle or acceptance review.

## Deploy driver

There is exactly one public application origin: `https://geophysics.ml.fasl-work.com/`, served from the ML VPS. GitHub Pages publication is withdrawn and must remain absent. The VPS hostname remains canonical; no second deployment, mirror, hostname, DNS change or CNAME work is part of this release. Source control and GitHub repository hosting do not create a second application deployment.

The product branch promotes through the governed PR path only after exact-commit CI and complete local scientific, UI, security and actual-host admission pass. Deployment publishes the already validated bundle; it never trains, downloads data or rebuilds artifacts on the host. Keep the current release and two rollback releases. Before cutover, verify artifact identity, HTTPS, all routes, account/project ownership boundaries, data and job APIs, capacity limits, cancellation, cleanup, browser workflows and the retired Pages endpoint. Rollback readiness is separate from user-project backup policy.

## Risks and kill criteria

- Rights uncertainty or inaccessible source: do not mirror; preserve the provider link and exact limitation.
- Unit, sign, frame, forward or derivative oracle failure: stop that method's release and retain the failed receipt.
- Leakage or held-out selection: invalidate the learned result; freeze cohorts and selection rules before training.
- Weak field support or failed 1D screen: keep the case QC-only and do not force an inversion.
- Resource estimate absent, exceeded or unmeasured on the VPS: reject or disable that online job class; never imply unlimited consumption.
- UI control does not change a physical computation or result: remove/repair the control and fail the browser gate.
- Shell token, typography, navigation or component ownership drift: fail the shared-shell baseline.
- Replacement deployment changes identity or rollback slots: do not cut over until current plus two rollback releases and exact-host verification are proven.

## ADR fit

| ADR | Decision for this product | Fit |
|---|---|---|
| ADR-0057 | Template-instantiated, offline-pipeline-heavy product with a bounded backend and documented browser lane. | Adopted; no internal Python package. |
| ADR-0056 | Complete scientific product repository with contracts, pipeline, cases, methods and a deep documentation wiki. | Adopted; method/case matrix and documentation gates apply. |
| ADR-0069 | Full scientific product repository and reproducible method evidence. | Adopted for every published solver and data pipeline. |
| ADR-0017 | Six-page content and UI/UX quality bar; shared shell owns page structure, typography and navigation. | Adopted; product styles are limited to product-owned instruments and plots. |
| ADR-0070 | Focus mode is required for eligible workbench views and shared-shell instrumentation. | Applicable; no focus waiver is declared. |
| ADR-0071 | Related sibling views are grouped and kept within the shell's tab limits. | Adopted for method, experiment and benchmark content. |
| ADR-0074 | CI/CD is bounded; scientific training, baking and full numerical matrices run locally. | Adopted; deployment consumes validated committed artifacts. |
| ADR-0075 / ADR-0078 | SDD and named failing feature gates are release contracts. | Adopted; requirements and adversarial validation records must name real tests. |

## 9. EARS requirements and named failing gates

This 2026-09-27 requirement set is the owner-approved baseline whose status is tracked by `docs/design/convergence.json`. The current feature requirements above refine its implementation gates. Later user-approved clarifications remain binding where they supersede the baseline: Clear Lake `cl061` is QC-only because the 1D screen fails; M13 browser inference must be parity-checked on real held-out traces; visitors may explore and compute in the browser while project writes and heavy VPS jobs require internal account access; SMTP and off-host backup are not current prerequisites; the ML VPS is the only application deployment target.

All gates are planned filenames until implemented. A gate records the actual input, result and failure; a green build or HTTP 200 alone cannot satisfy these requirements. Feature SDDs under docs/design/features will refine each contract and tolerance before their code.

R-001 THE platform SHALL publish a rights-aware searchable catalogue whose advertised raw or derivative links retrieve the named bytes and SHA-256. Gate: tests/data/test_catalogue_sources.py::test_rights_links_and_hash_receipts.

R-002 WHEN a user uploads or imports an original, THE platform SHALL preserve its bytes immutably and create a versioned, owned source record. Gate: tests/data/test_provenance.py::test_raw_immutable_and_owner_scoped.

R-003 IF a format lacks required unit, CRS/datum, time/epoch, component or geometry metadata, THEN THE ingestion contract SHALL reject modelling with a field-specific reason. Gate: tests/data/test_formats.py::test_missing_physical_metadata_rejection.

R-004 WHEN a processing transform runs, THE platform SHALL retain original values and create a hashed derivative with parameters, masks and uncertainty lineage. Gate: tests/data/test_provenance.py::test_transform_dag_roundtrip.

R-005 WHEN a dataset is selected, THE platform SHALL expose only compatible methods and explain every ineligible/offline status. Gate: tests/api/test_method_eligibility.py::test_contract_filtered_methods plus frontend/e2e/eligibility.spec.ts.

R-006 WHEN an eligible online job is submitted, THE worker SHALL execute that method on the submitted dataset, persist measured inputs/outputs and change results when a scientific parameter changes. Gate: tests/api/test_job_execution.py::test_user_dataset_actual_solve_and_parameter_effect.

R-007 IF a job exceeds admission, time, memory or scratch limits, THEN THE service SHALL reject or stop it with a durable, non-success status and no orphan process. Gate: tests/api/test_job_limits.py::test_preflight_timeout_cancel_and_recovery.

R-008 THE numerical release SHALL contain complete M01-M13 verticals with their method-specific named tests, limitations and result artifacts. Gate: scripts/check_method_matrix.py::main plus the M01-M13 gates in section 4.

R-009 THE release SHALL distinguish synthetic truth from field observations and shall not score field geology against an invented true model. Gate: tests/data/test_artifact_contract.py::test_truth_only_for_synthetic.

R-010 THE learned methods SHALL have versioned trained checkpoints, leakage-safe split hashes, per-group metrics and real same-input comparators. Gate: tests/learning/test_split_and_benchmark.py::test_disjoint_groups_and_matched_inputs.

R-011 WHEN a result is exported, THE recipient SHALL be able to re-import arrays, axes, units, rights, parameters and provenance with matching hashes. Gate: tests/data/test_export.py::test_bundle_roundtrip_and_rights.

R-012 THE web workbench SHALL use exactly the six CAOS routes and the shared shell tokens/fonts, with no duplicate application deployment or invented top-level lifecycle routes. Gate: frontend/e2e/routes-shell.spec.ts plus scripts/check_single_origin.py::main.

R-013 WHEN a selected case, dataset or physical control changes, THE App SHALL recompute or load the correctly labelled result and update every linked view/readout. Gate: frontend/e2e/selected-case-reactivity.spec.ts.

R-014 THE visualization SHALL expose physical axes, units, linked values, signed residual scales, real time/iteration frames and angle-step controls only on genuine 3D geometry. Gate: frontend/e2e/scientific-views.spec.ts and frontend/e2e/animation-controls.spec.ts.

R-015 THE six pages and architecture modal SHALL be visually usable in EN/ES, light/dark, desktop/phone and reduced motion without clipped controls or orphaned navigation. Gate: frontend/e2e/visual-matrix.spec.ts::fit_and_pointer_navigation.

R-016 THE in-app course and docs wiki SHALL cover every published method/case with equations, assumptions, worked commands, limits and primary citations. Gate: scripts/check_docs_matrix.py::main and docs/validation/source-to-content-review.md.

R-017 THE one-site release SHALL keep the old VPS release available for rollback until the full scientific/UI and VPS API/jobs/data/HTTPS/browser gates pass, retain the current release and two rollback releases, and prove Pages no longer publishes the app. Gate: scripts/verify_single_vps_release.py::main plus independently reviewed private scientific/UI/actual-host jobs/ownership/HTTPS/browser/retired-publication/rollback receipts. The read-only verifier alone cannot accept this requirement.

R-018 THE scientific release SHALL record a per-requirement convergence verdict with pass, fail, unresolved or ineligible and the exact gate receipt. Gate: scripts/check_sdd_convergence.py::main and docs/design/convergence.json.

R-019 WHEN the Benchmark runs learned M13 inference on real held-out traces in the browser, THE app SHALL show its phase probabilities and compare it with classical M08 on identical inputs without replacing the canonical checkpoint. Gate: frontend/e2e/phase-picker-live.spec.ts and tests/learning/test_phase_evaluation.py::test_matched_inputs_and_failed_picks and frontend/scripts/verify-phase-browser-parity.mjs.

### Historical design record

The approved 2026-09-27 SDD is retained at `docs/design/SDD-approved-2026-09-27.md` for audit. This current document supersedes its route details, research basis, resource assumptions, method-ladder requirements and deployment text where they differ. Historical evidence remains historical and does not imply replacement acceptance.
