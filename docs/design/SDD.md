# Geophysics research platform: product software design document

Date: 2026-09-27
Status: APPROVED by Felipe on 2026-09-27 for product implementation, including the subsequently disclosed Clear Lake QC-only and in-browser M13 parity clarifications. The 2026-09-27 replacement plan was validated by the user's "implement all" instruction.
Repository: fsantibanezleal/CAOS_Geophysics (current name, not the proposed product identity).
Public application: exactly one ML VPS origin after cutover. The existing 0.04.001 release remains live and is not evidence that this design is implemented.

## 1. Problem, boundary and design corrections

The product must support a complete, scientifically inspectable path from data discovery and rights-aware acquisition, through immutable storage, format-specific quality control and processing, to compatible forward/inverse methods, evaluation, visualization, interpretation, export and reproducible local execution. A user with eligible data must be able to complete the declared online workflows. Curated field studies and original synthetic controls must use the same contracts. The repository, not just the browser, must be independently useful for the full offline/GPU method ladder.

The old SDD describes fixed synthetic replay and two static deployments. It is superseded by this document; its green gates are not acceptance evidence for the replacement. Three changes to the 2026-09-27 plan require explicit review:

1. Top-level navigation is exactly App, Introduction, Methodology, Implementation, Experiments and Benchmark, in that order. Catalogue, projects, processing, modelling and evaluation are operations inside the selected-project App workbench, not invented top-level routes. This follows the CAOS product bar and ADR-0017. Cross-case summaries belong only in Experiments and Benchmark.
2. M13, learned earthquake phase picking, is added to the 12-row method matrix so that two learned methods are genuinely implemented. It shares held-out, real waveform data with classical picking M08. M12 remains learned seismic inversion with a separate synthetic/family-disjoint generalization question. A model label or a pretrained checkpoint alone will not count.
3. The working title and current repository name are not approval of a final product identity. The final name/hostname is a pending owner choice. No rename, DNS change, second hostname or Pages shutdown occurs from this document alone.

Non-goals: a claim of uniquely recovered field geology; arbitrary uploaded full-survey FWI on the CPU-only VPS; a browser animation presented as an inverse solve; unsupported raw formats being silently interpreted; copying the reference course's unlicensed notebooks or data; a new inverse-algorithm novelty claim; a second public app deployment. Offline-only full FWI, large 3D sweeps and training remain complete local workflows with importable provenance, but are not called online calculations.

## 2. System boundary and typed contracts

The activated FastAPI app owns accounts, catalogue, project metadata, job admission and result APIs. A distinct, unprivileged worker process owns request-time numerics; FastAPI request/background-task processes never run heavy solves. SQLite with migrations and transactional state is the initial metadata store; raw and derived bytes use a project-scoped filesystem tree outside the web root. The local offline pipeline uses the same ingestion and artifact schemas and an ignored .venv-pipeline; the runtime uses an isolated, pinned .venv and API requirements. There is no unpublished internal Python package. The frontend uses the published shared shell and a typed API client. An authenticated user owns projects; guests may read only rights-cleared curated entries and released artifacts.

The durable state graph is:

source record -> immutable raw asset -> validated dataset version -> processing run -> compatible survey/model -> solver job -> evaluation -> immutable result/export

### 2.1 Ingestion contract, raw to validated dataset

SourceRecord fields: source_id, provider, exact URL or local upload, DOI/citation, retrieval time, rights statement and decision (mirror, provider-link-only, derivative-only or forbidden), declared format, expected bytes, SHA-256, and attribution. Unknown rights do not become permission to publish raw bytes.

RawAsset fields: asset_id, owner/project, source_id, original filename, MIME and detected format, byte count, SHA-256, immutable storage key, upload/download receipt and validation status. A derived asset never replaces it. Remote fetch is restricted to a reviewed provider/object allowlist; arbitrary user URLs are rejected. Archive entry count, expansion ratio, total bytes, path traversal and nested archive depth are bounded before extraction.

ObservationDataset fields: dataset_id and version; modality; named dimensions and axis order; CRS/EPSG or explicit local survey coordinates; horizontal datum and vertical datum/sign; physical units; station, line, electrode, source/receiver or channel geometry; observed values; mask and missingness reasons; uncertainty kind/units/covariance; correction history; parser/version; parent raw hashes; QC verdict. Every quantity with an ambiguous unit, datum, sign, component orientation or geometry is rejected or retained as an unmodelled raw object. No automatic unit guessing. Coordinate transformations declare axis order explicitly. Non-finite observations are masked with a reason or rejected, never replaced with zero; duplicates are reviewed by modality, not silently averaged. Outlier policies are explicit and reversible: flag by default, reject invalid physics, and require user approval for any exclusion or robust-weight rule. Training normalization is fitted on train only and serialized.

Format adapters are separate, testable verticals: gravity station tables; magnetic flight-line tables and GeoTIFF grids; EDI tensors and selected MTH5 runs; ERT electrode/ABMN data; MiniSEED plus StationXML and event/pick metadata; traveltime source/receiver/pick tables; bounded SEG-Y trace headers/samples. EDI is a transfer-function product and cannot be relabelled raw time series. A provider grid is not an uncorrected observation. SEG-Y and MTH5 are size-gated and may require offline processing; the online interface must return an exact offline recipe or an unsupported verdict, never a fake output.

### 2.2 Job and result contract, pipeline to API/web

ProcessingRun fields: ID, input dataset versions, ordered transform DAG and parameters, code/environment digest, output dataset versions, masks/uncertainties, warnings, wall/RSS/disk, and content hashes.

SolverJob fields: ID, owner/project, dataset version, method ID/version, execution lane, survey geometry, mesh/discretization, model parameterization, starting/reference model, physical bounds, data weights/covariance, regularizer/beta, seed, preflight estimate, admission verdict, state (queued/running/succeeded/failed/cancelled/nonconverged/ineligible), progress, worker identity, timestamps, measured wall/peak RSS/scratch and error record. Retries create a new attempt under the same logical job, never overwrite a successful result.

ResultArtifact fields: schema version, job/input/engine IDs and hashes, axes/dimensions/units, observed and predicted values, signed and normalized residuals, model with physical property units, objective components and stopping reason, sensitivity/coverage or a typed reason unavailable, uncertainty/sweep definition, held-out partition, figure-ready arrays, provenance DAG, rights, licence and SHA-256 per file. Synthetic truth appears only for explicitly synthetic cases. Field results include interpretation hypotheses separately from measured/predicted arrays. A TypeScript mirror of this contract and a Python schema reject shape, orientation, unit and hash drift. Exports are a reproducible bundle of original-access metadata, permitted bytes, config, arrays, results, evaluation and a methods card; re-import must reproduce identity and plots.

The offline pipeline stages remain named and independently testable: ingest -> preprocess -> dataset/split -> feature extraction -> train -> infer -> evaluate -> export -> validate. For a non-learned method, train records a typed not-applicable verdict, never a no-op pretending to fit a model. For learned methods train emits actual checkpoints, split hashes, normalization and history. Canonical bake is an intentional local release operation, not a test, CI or deploy side effect.

## 3. Execution lanes and admission

| Lane | Intended operations | Evidence before activation |
| --- | --- | --- |
| Online bounded CPU worker | Validated upload/source subsets; M01/M03/M05/M08 processing; M06 layered MT; and M02/M04/M07/M09 small inversions only after individual host benchmarks | Exact engine parity, wall/peak RSS/scratch, timeout/cancel and concurrency measurements on the actual ML VPS |
| Client live | Navigation, plotting, linked readouts, slice/angle controls on real 3D models, and an exported M13 phase picker on real held-out traces; other lightweight forward/exported inference only after parity | Offline/live numerical parity, browser memory/latency, control-reactivity and failure fallback |
| Offline local CPU/GPU | Full 3D sweeps, MTH5 transfer-function estimation, FWI optimization, M11 coupling, M12/M13 training and complete held-out benchmarks | Pinned environment, RTX 4070/CUDA receipt where used, source and checkpoint hashes, independent numerics |
| Replay | Curated released field/synthetic results and histories | Schema/hash/case-matrix validation; visibly distinguished from user-submitted live jobs |

The 2026-09-27 host observation was 4 vCPU, 7.6 GiB RAM and about 25 GB free disk, without a server GPU. This is a snapshot, not a solver benchmark. Initial safety ceiling proposed for review: one compute worker, at most one active job per account, 2 GiB worker memory, 1 GiB scratch, 10 minutes wall, 200 MiB compressed upload and 1 GiB stored project bytes per account. These are admission limits, not evidence that every method fits. Before enabling each online method, benchmark at least a nominal, upper-bound and malformed job; require the 95th-percentile nominal peak below 70% of its limit and a successful cancel/crash recovery. If a method cannot meet the limit without scientifically invalid resolution, it remains fully executable offline and the web offers its exact recipe/import path. No solver silently substitutes a coarser toy.

## 4. Method ladder and acceptance oracle

Each row requires real engine invocation, pinned dependency/licence, preprocessing/configuration, output contract, independent physical or numerical test, negative/failure control, held-out evaluation where meaningful, local reproducible command, wiki chapter and web lane badge. A method without any one of those is not implemented. The test names below are planned gates, not claims that the tests already exist. Feature SDDs will set numerical tolerances from independent analytic/discretization studies before code for each vertical.

| ID | Scientific workflow and release acceptance | Named gate |
| --- | --- | --- |
| M01 | Gravity station QC and declared reference/correction/transform chain; original versus derived anomalies, holdout and no double correction | tests/numerics/test_gravity_processing.py::test_station_correction_lineage |
| M02 | 3D gravity prism forward and weighted L2/sparse density inversion on survey geometry, with true observed/predicted/residual, sensitivity and alternative mesh/beta | tests/numerics/test_gravity_inverse.py::test_prism_oracle_and_heldout |
| M03 | Aeromagnetic line/tie/height QC, gridding/continuation and blocked flight-line holdout versus provider product | tests/numerics/test_magnetic_processing.py::test_blocked_line_holdout |
| M04 | Induced-field 3D magnetic forward/inverse with recorded field vector; remanent and wrong-field negative controls | tests/numerics/test_magnetic_inverse.py::test_induced_kernel_and_remanence_failure |
| M05 | EDI tensor/variance/rotation/tipper QC and, for selected MTH5, separate raw-to-transfer-function lineage; no invented 1D eligibility | tests/numerics/test_mt_qc.py::test_tensor_rotation_and_dimensionality |
| M06 | Layered MT complex-impedance forward and bounded 1D inverse of eligible components with multi-start, masks and beta/thickness sensitivity | tests/numerics/test_mt_inverse.py::test_halfspace_recursion_and_multistart |
| M07 | Topography-aware 2D ERT geometric factors, QC and inverse, with homogeneous/flat control, reciprocal/errors, sensitivity and residual | tests/numerics/test_ert.py::test_topographic_factor_and_inverse |
| M08 | MiniSEED/StationXML waveform QC, response/filter provenance and classical STA/LTA or matched arrival picking against catalogue phase times | tests/numerics/test_waveform_picks.py::test_response_epoch_and_classical_picks |
| M09 | Field first-arrival traveltime tomography with source/receiver geometry, travel-time fit, ray coverage, start/mesh sensitivity | tests/numerics/test_traveltime.py::test_homogeneous_time_and_field_holdout |
| M10 | Acoustic wave forward and iterative FWI using actual receiver residual gradients, independent stability/adjoint check, multiscale and cycle-skip failure | tests/numerics/test_fwi.py::test_adjoint_heldout_and_cycle_skip |
| M11 | Gravity-magnetic joint structural inverse with two independently optimized baselines, separately weighted data terms, coupling diagnostic and disjoint-source control | tests/numerics/test_joint.py::test_coupling_against_independent_baselines |
| M12 | Learned seismic-velocity inversion with real training, checkpoint, family/acquisition-disjoint test, classical same-input comparator, forward-data consistency and OOD failure | tests/learning/test_velocity_inversion.py::test_family_disjoint_checkpoint_and_forward_consistency |
| M13 | Learned P/S phase picking (PhaseNet-family official MIT implementation or verified equivalent) trained/fine-tuned and evaluated on event/station-disjoint real traces against M08, with probability curves, confusion and timing residuals; a parity-validated browser export runs inference on held-out field traces | tests/learning/test_phase_picker.py::test_event_disjoint_checkpoint_vs_classical and frontend/e2e/phase-picker-live.spec.ts |

M13 is added to reconcile the validated plan with the minimum two learned methods. The [official PhaseNet repository](https://github.com/AI4EPS/PhaseNet) and [paper](https://doi.org/10.1093/gji/ggy423) are candidate implementation references; checkpoint redistribution and field-data permissions still require a recorded decision. M12's [OpenFWI repository](https://github.com/lanl/OpenFWI) is a candidate benchmark source, not proof its linked datasets can be mirrored. A learned model trained only on synthetic data cannot be claimed field-validated.

## 5. Case taxonomy, coverage and rights

The release registry must contain at least 12 scientifically distinct, configurable cases spanning field observations, known-truth synthetic controls, acquisition degradation, null/negative controls and out-of-family tests. Six parameter regimes are required only when the case has a meaningful physical family; regimes are not made by merely shifting the same centred 2D object. No current synthetic case is grandfathered in without geology, survey, inverse-crime and visual review.

| Case group | Candidate source or construction | Method eligibility | Release question and limiting gate |
| --- | --- | --- | --- |
| Fault-zone potential fields | [USGS Bartlett Springs, DOI 10.5066/P90F5TGH](https://www.usgs.gov/data/gravity-aeromagnetic-magnetic-potential-and-physical-property-data-bartlett-springs-fault-zone) | M01/M02/M04/M11 where co-registered data permit | Do density/susceptibility constraints improve held-out survey prediction? Check station/grid/correction meaning and CC0 attachments. Metadata names gravity stations, measured properties and magnetic grids; direct attachments returned 403 in this environment, so bytes and hashes remain unverified. Elevation in feet requires explicit conversion. No subsurface truth. |
| Airborne magnetic lines | [USGS Charleston, DOI 10.5066/P9EWQ08L](https://www.usgs.gov/data/airborne-magnetic-and-radiometric-survey-charleston-south-carolina-and-surrounds-2019) | M03/M04 | What is lost by gridding and corrections? Preserve flight/tie line identities and blocked holdouts. USGS metadata estimates the flight-line CSV at 2,580 MB, not a measured download size; acquire and subset locally before considering VPS storage. A small GeoTIFF cannot substitute for line processing. |
| Multistation MT | [USGS Clear Lake, DOI 10.5066/P14KAQ3M](https://www.usgs.gov/data/magnetotelluric-data-clear-lake-region-northern-california) | M05/M06 only for screened 1D-eligible sites | Which sites permit a conditional layered approximation? The 16,411-byte cl061 EDI is hash-verified for M05 tensor QC but its current dimensionality screen rejects M06; select another independently screened station for the 1D inverse. EDI versus MTH5 lineage, tensor error and dimensionality remain explicit. |
| Topographic ERT | [pyGIMLi Slagdump field example](https://www.pygimli.org/_examples_auto/3_ert/plot_02_ert_field_data/) | M07 | How does topography change factors and inverse? The commit-pinned 5,435-byte file has a verified hash, but its repository declares no raw-data licence. Provider link only unless redistribution permission is obtained. |
| Field refraction | [pyGIMLi Koenigsee example](https://www.pygimli.org/_examples_auto/2_seismics/plot_04_koenigsee/) | M09 | What velocity fits travel times and what is unresolved? The commit-pinned 9,844-byte file has a verified hash; raw redistribution terms remain unresolved. This is picks, not waveforms or FWI. |
| Earthquake traces | [SCEDC archive](https://scedc.caltech.edu/data/cloud.html) with StationXML and phase catalogue | M08/M13 | Can classical and learned pickers reproduce independent analyst picks? Verify source/weight rights and event/station split. Not FWI data. |
| Active-source acoustic | Original heterogeneous controlled surveys and a size/rights-cleared SEG-Y line if accessible | M10/M12 | What start/coverage/frequency regimes fail? Field FWI is not promised until acquisition/wavelet suitability is proven. |
| Synthetic controls | Original offset basins, dipping contacts/dykes, remanent and disjoint structures, complex MT layering, topographic ERT, wave speed faults/salt and noisy/wrong-geometry surveys | All relevant rows | Known truth permits model error; generated observations use a different mesh/discretization or operator from inversion. |

Every published case requires a source-rights verdict, exact retrieval and hash receipt, raw/derived separation, units/CRS/geometry QA, processing graph, eligible-method matrix, observed/predicted/residual/coverage views, at least one failure or sensitivity comparison, worked scientific interpretation, export and reproducible command. A provider-link-only case may publish a permitted derived result, but must not mirror raw bytes without rights. If any candidate cannot be accessed, licensed or processed within host storage, an equivalent-science replacement requires an SDD amendment and owner review; an empty case cell is not completion.

## 6. Evaluation oracles and evidence model

There is no combined "science score". Verification is layered and non-substitutable:

1. Source/contract oracle: provider identity, rights, original SHA-256, schema, units, geometry and raw immutability. Parsing a file is not numerical validation.
2. Forward/derivative oracle: analytical halfspaces/prisms/homogeneous travel times/geometric factors where available, an independent library or discretization, sign/unit and mesh/time convergence, finite-difference/adjoint directional checks. A solver agreeing with its own generated data alone is weak evidence.
3. Synthetic inverse oracle: independently generated known truth with differing inversion discretization, held-out observations, negative controls, alternate start/beta/mesh and physically meaningful error. A visually similar image is not enough.
4. Field predictive oracle: withheld stations/lines/receivers/events, residual structure, fit to declared uncertainties, source metadata and model sensitivity. No field "truth 3D volume" metric. Bayesian/posterior language is forbidden unless uncertainty is actually calibrated.
5. Learned oracle: disjoint groups defined before normalization, real checkpoints, classical same-input comparator, per-family/site/event metrics, degradation/OOD and probability calibration where applicable. Confusion/ROC/PR only for tasks with valid labels (for example phase/noise picking), not fabricated for continuous velocity inversion.

The case matrix records passed, failed, unresolved, ineligible and not-run separately. No averages hide missing cells. Scientific claims in the manuscript or UI cite a specific result hash and the corresponding oracle level.

## 7. Public workbench, documentation and visual contract

The six top-level routes are App (/), Introduction, Methodology, Implementation, Experiments and Benchmark. App shows one selected project/dataset/case at a time, with a rights-aware source chooser and project drawer. Discovery, import, provenance, processing, method configuration, job progress, evaluation and export are linked operations on that selected object, not separate top-level pages or "meta method" tabs. Incompatible methods are visibly ineligible with a reason; offline methods offer a runnable local recipe and attributable artifact import, not a run button that replays a saved animation. The method navigation groups 13 methods into no more than six question-oriented groups with a second-level method selection. Every control used for a physical result must alter actual computation or a clearly labelled view transformation; the sidebar retains a live readout. Cross-case matrices appear on Experiments and Benchmark only.

The shared shell owns fonts, tokens, header/footer, tabs, theme, language and architecture modal. Product CSS may style only scientific widgets and layout composition; it must not redefine shell primitives or introduce an unrelated palette/font. The primary instrument occupies at least half the App viewport; no document-level horizontal or vertical overflow in fixed workbench views. EN/ES labels, diagrams and equations are complete, not partial translations. The architecture modal has at least five dense, hand-authored themed SVGs (system, lanes, web flow, science, contracts), with bilingual SVG text and light/dark rendered bounds checks.

Each physical modality gets appropriate, linked axes and units: potential-field survey/line maps and genuine 3D property volumes with user angle-step/slices; MT tensor, apparent-resistivity/phase and station eligibility; ERT electrodes/topography/pseudosection/model; waveform traces/spectra/pick uncertainty; traveltime geometry/ray coverage/velocity; FWI shot gathers, observed/predicted/difference data and actual time/iteration frames; learned probabilities, calibration and OOD diagnostics. Sequential colours represent magnitude, zero-centred diverging colours signed residuals, and phase uses a declared circular treatment. Colour bars show quantity, units and range. Animations expose physical time, acquisition step or solver iteration with pause/scrub, reduced motion and numeric frame export; decorative looping is rejected.

Documentation page floors follow ADR-0017 rather than an invented product style: Introduction has five substantial sections and at least three captioned equations; Methodology has at least six deep method-family tabs, including separate M12 and M13 learned-method tabs, each with equations, themed figure, limits and scoped citations; Implementation has at least eight algorithm/contract tabs; Experiments has at least six study/protocol tabs and a leakage diagram; Benchmark reads committed metrics, runs M13 in-browser on real held-out traces, compares M08 on the same traces, and shows per-phase confusion/recall, degradation and provenance. ADR-0071 limits simultaneously visible sibling tabs to about six, so deeper material uses grouped sub-navigation without hiding a promised method.

The in-app six-page course and the repository's navigable docs wiki are authored vertically with each method. Each chapter gives source-linked theory, governing equations and symbol definitions, assumptions, data/metadata contract, exact algorithm and parameter semantics, independent tests, worked field and synthetic case, limitations, reproducible local/API command, exercise and EN/ES source-linked presentation. The Implementation page explains actual algorithms and constants rather than stack slogans; inline Cite and per-section Refs point to real DOI/URL. Internal paths/ADR names never appear in user-facing prose.

## 8. Security, operations and deployment driver

The proposed access model is guest read-only curated research and account-gated upload/project/job endpoints using a maintained self-hosted FastAPI auth library, with session cookies, CSRF protection where applicable, password reset/verification, server-side ownership checks and rate limits. [FastAPI Users](https://github.com/fastapi-users/fastapi-users) is the ADR-0044 default but is now in maintenance mode; feature design must verify its security/compatibility or select Authlib with an approved reason. No custom password/session implementation. Successful project data is retained until explicit user deletion or an announced policy change; quotas prevent indefinite unbounded growth. A project export and permanent deletion cover raw, derivatives, jobs and backups according to a published retention schedule. Backups are encrypted/restricted, and a restore drill is part of release evidence. Secrets never enter the public repo or frontend bundle.

Deployment driver: this product has private user state, request-time CPU jobs and potentially large raw/derived artifacts, so a static Pages site cannot serve it. The owner's single-deployment requirement selects one vps-service origin on the ML VPS. The proposed release threshold is not an unmeasured belief: before cutover, the integrated frontend/API/worker must pass numerical admission tests, one-worker resource tests with at least 30% memory/disk headroom against configured limits, backup/restore, security checks, external HTTPS/SNI/API/browser hydration and concurrent-read responsiveness. If it fails, cutover is blocked; it does not create a Pages mirror or silently drop the job features. The final hostname/name is pending owner choice. GitHub remains the public source/issues/releases. After the one VPS origin passes, remove Pages workflow, disable Pages through GitHub, verify the Pages app URL no longer publishes this application, and update every link/registry. DNS method is whatever the final VPS hostname actually uses; do not claim a CNAME when the existing .ml wildcard is an A record.

CI/CD follow ADR-0074: develop/main and manual triggers only, cheap lint/guards/committed-artifact checks/web build, bounded jobs and concurrency. No train, scientific test suite, data download, bake or benchmark in CI/CD. The complete numerical, security and browser suites run locally before scoped PR promotion. Deploy publishes the already-validated release and never regenerates evidence.

## 9. EARS requirements and named failing gates

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

R-017 THE one-site release SHALL keep the old origin intact until VPS API/jobs/data/HTTPS/browser and backup/restore gates pass, then disable Pages and prove it no longer publishes the app. Gate: scripts/verify_single_vps_release.py::main and docs/validation/cutover-receipt.json.

R-018 THE scientific release SHALL record a per-requirement convergence verdict with pass, fail, unresolved or ineligible and the exact gate receipt. Gate: scripts/check_sdd_convergence.py::main and docs/design/convergence.json.

R-019 WHEN the Benchmark runs learned M13 inference on real held-out traces in the browser, THE app SHALL show its phase probabilities and compare it with classical M08 on identical inputs without replacing the canonical checkpoint. Gate: frontend/e2e/phase-picker-live.spec.ts::real_trace_parity_and_matched_baseline plus tests/learning/test_live_export.py::test_onnx_offline_parity.

## 10. Risks, kill criteria and review decisions

- Rights or inaccessible source: no raw mirror until explicit permission/CC0 and reproducible retrieval; replace the case with equal scientific coverage through SDD review if access fails.
- Incorrect metadata or solver signs: stop the method release on independent oracle failure, not on a pretty plot; field residual alone cannot override.
- Shared 8 GB host saturation: disable the online method, not the resource guard; never claim full-GPU web compute.
- Training leakage or non-generalization: publish negative results; do not choose only successful families or tune on held-out data.
- Static-website regression: fail release if new user data cannot complete the methods promised online, exports cannot round-trip, or any job is replay disguised as computation.
- UI quality: fail release on shell/font/style divergence, scientific axes without units, unreadable EN/ES, no-op controls, decorative animation or missing user visual review.
- Operational irreversibility: keep the old VPS release and Pages until the replacement origin has a verified rollback snapshot; retire Pages only after the single-VPS release is externally verified.

Felipe explicitly approved the product SDD on 2026-09-27 in response to its review request for the six-page UI, M13 learned phase picker, account-gated writes, provisional resource limits and single-ML-VPS design. The approved decisions are: six prescribed pages in place of the plan's lifecycle routes; M13 as the second learned vertical; guest-read/account-write policy and stated provisional limits; bounded online CPU methods with full FWI/training offline; rights/capacity substitutions only by reviewed amendment. The final product/repository identity and hostname remain a separate owner choice, so cutover is held until selected. This SDD approval authorizes feature SDDs and code; it does not assert that any new method, dataset, online job or deployment already exists.

Felipe separately approved including the Clear Lake cl061 QC-only finding and the requirement for parity-checked M13 inference on real held-out traces in the browser before this SDD was promoted.

## Research basis

The dated management research dossiers 02-05 and validated replacement plan are the source of this design. Public primary references include [SimPEG](https://doi.org/10.1016/j.cageo.2015.09.015), [USGS gravity procedures](https://pubs.usgs.gov/tm/02/d04/tm2d4.pdf), [Harmonica](https://www.fatiando.org/harmonica/latest/api/index.html), [Verde blocked splitting](https://www.fatiando.org/verde/latest/api/generated/verde.train_test_split.html), [MTH5](https://mth5.readthedocs.io/en/latest/source/mth5_format.html), [MTpy](https://github.com/MTgeophysics/mtpy-v2), [pyGIMLi inversion](https://www.pygimli.org/user-guide/inversion/), [ObsPy](https://docs.obspy.org/packages/autogen/obspy.core.stream.Stream.html), [Deepwave FWI](https://www.ausargeo.com/deepwave/example_fwi), [Devito FWI](https://www.devitoproject.org/examples/seismic/tutorials/03_fwi.html), [SimPEG joint inversion](https://docs.simpeg.xyz/latest/content/user-guide/tutorials/13_joint_inversion/plot_inv_3_cross_gradient_pf.html), [PhaseNet](https://doi.org/10.1093/gji/ggy423), [OpenFWI](https://github.com/lanl/OpenFWI), [W3C PROV-O](https://www.w3.org/TR/prov-o/) and [CF conventions](https://cfconventions.org/Data/cf-conventions/cf-conventions-1.13/cf-conventions.html). Source-specific rights and exact attachment hashes remain acquisition gates, not inferred from these citations.
