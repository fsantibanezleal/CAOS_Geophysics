# M03 architecture and workflow design

Status: planned. Date: 2026-10-03. Read [research](research.md) before this design, then [contracts](contracts.md), [algorithms](algorithms.md), [validation](validation.md) and [tasks](tasks.md). All paths are prospective unless identified as existing. Product implementation stops until MAIN fully reads the exact packet pin and explicitly approves.

## Question and boundaries

Given actual ordered scalar magnetic acquisition lines and eligible geometry/metadata, inspect their coverage, channels and correction state, calculate reproducible QC/derivatives, grid a chosen channel and predict held-out line blocks. Distinguish geometric interpolation, harmonic height transfer and processing assumptions. The output is an inspectable line/grid result with masks and diagnostics, not recovered susceptibility or proof of field geology.

The complete scoped local vertical includes original-byte intake, strict sidecar/CSV contract, reversible row/segment masks, justified correction application, crossover/offset diagnostic, qualified directional residual-filter diagnostic, two genuinely different gridding comparators, blocked selection/evaluation, support/spectrum/continuation, independent controls, exact replay/export and other-data guide. Raw scalar intensity is inspected/corrected; harmonic fits require a documented anomaly or explicitly justified constant-background weak-anomaly control. The future online vertical includes actual new-data execution and durable lifecycle, not a selector pointing to replay.

Out of M03's executable operation set: airborne platform compensation from attitude logs; recovery of unknown contractor processing; raw gradiometer/vector joint inversion; reduction to pole, downward continuation and magnetic-property inversion; inferred acquisition tracks from provider grids. These remain typed ineligible/unsupported paths with M04 or reviewed-extension prerequisites. This is a boundary of the declared scalar processing contract, not acceptance of the whole product by narrowing the parent's promise.

## Local data flow and ownership

Immutable originals + explicit scalar metadata
-> bounded CSV/strict JSON parse and structural QC
-> eligibility + geometry-only sealed partition
-> admissible calibration/time/reference derivatives
-> training-only crossover/leveling diagnostics
-> candidate Harmonica/SciPy fits + inner selection
-> one sealed prediction evaluation
-> grid/height/mask/spectrum diagnostics
-> rights-aware immutable result/export
-> independent result verification/replay.

Processing preserves both source order and measurement values. Sorted indexes are secondary arrays; edits create derivatives with parent hashes. Missing or duplicate values retain row IDs and mask reasons. A user's explicit exclusion requires a derivative policy record; flags alone never remove observations. No field-truth column exists in field results.

Plain scripts data-pipeline/magnetic_line_contract.py, magnetic_lines.py and magnetic_line_validation.py own the local schema, orchestration and evaluation. This is product build tooling, not an internal package or a new dependency. Reuse the existing strict local-boundary discipline conceptually; do not import gravity-only schemas, fabricate mGal conversions or modify that unit to accept magnetic data. Paired scripts invoke by path and only into a user-chosen new output directory.

Existing engine targets: Harmonica 0.7.0, Verde 1.9.0, NumPy 2.2.6, SciPy 1.15.2 and scikit-learn 1.9.1 with threadpoolctl and xarray as the currently inspected gravity-transform environment supplies them. Implementation must verify/persist exact installed direct and transitive versions, loaded source/native hashes and CPython 3.12.x identity before numerical evidence. This packet adds/installs nothing and does not treat loose requirements manifests as a complete lock. Engine/license verification failure is an implementation stop, not permission to install substitutes.

## Stage interpretation

| Standard stage | Actual M03 responsibility |
| --- | --- |
| ingest | Verify original identity, permissions, CSV and explicit physical sidecar. |
| preprocess | Mask/QC and separately admitted correction DAG; no automatic outlier removal. |
| dataset/split | Freeze outer line/spatial geometry partition before value-based choices. |
| feature extraction | Segment geometry, sampling, crossovers, support and qualified spectra. |
| train | Typed not_applicable for learned training; candidate harmonic regression/calibration is explicitly a fit, not a learned checkpoint. |
| infer | Predict at admitted withheld coordinates and declared grid/upper plane. |
| evaluate | Sealed metrics, independent numerical oracles, negative controls and comparator applicability. |
| export | Immutable result/config/lineage, rights-filtered members and replay command. |
| validate | Exact schema/hash/array/coverage/gate results; no aggregate science score. |

## Method and case acceptance

QC passes if supplied geometry, identity and masks are faithfully retained, not if a colourful grid is produced. Crossover/leveling passes only if geometric comparability and graph rank/gauge controls pass. A geometric interpolator passes its barycentric/plane oracle and declares the elevation approximation. Equivalent sources pass an independent dense system plus physical dipole controls at new coordinates/heights. FFT continuation passes analytic sinusoidal and independent dipole edge/refinement controls. Directional filtering passes retained/removed transfer-function checks and explicitly reports genuine geological attenuation; it is conditional and cannot automatically become a corrected field channel.

Cases are distinct objects: Charleston field-lines pending access/metadata; Bartlett provider grid ineligible for line operations; original heterogeneous synthetic acquisition for algorithm validation; geometric plane/null controls; gap/height/mixed-sensor and wrong-reference failures; directional parallel-geology and aliasing controls. At least six synthetic regimes vary actual acquisition/correction/geometry physics; provider field data are never synthetically enlarged to meet a variant count. A field case is incomplete until it has real eligible lines, verified rights, numeric comparator if advertised, measurements/results and source-cited worked interpretation.

## Proposed limits and scientifically valid resolution

Local and future bounded online numerical lane: raw CSV 16 MiB, combined sidecar/request 2 MiB; 400 rows, 32 line IDs, 4 sensors, 399 consecutive segments, 4,096 preflight segment pairs/crossovers, 256 sources, 26 fits (8 candidates x 3 inner folds plus final equivalent-source fit and geometric comparator), 16,384 exported grid cells in total, result 8 MiB, JSON depth 16, 200,000 nodes, key 128 and text 8,192 UTF-8 bytes, numeric token 128 ASCII bytes. Explicit FFT padding is at most twofold per axis and 65,536 internal cells. Limits include invalid/masked rows and all metadata before expensive materialization; raw CSV and combined metadata are counted separately. Offline survey-scale extension needs a reviewed envelope and genuine resource/coverage receipts; it must not quietly lift this bounded contract.

Bounded numerical child budgets proposed for later approval: whole process-tree CPU <=60 s, wall <=120 s, RSS <=512 MiB, scratch <=64 MiB. Native stop reserve at 50 CPU seconds; required measured worst-case dispatch/stop reserve <=10 CPU seconds. Parent-controller CPU <=10 s is separately accounted. One worker and one active job/account, plus existing global/user limits; stricter global limits win. These are design ceilings, not measurements or an admitted profile. Dense matrix size 400x256x8 =819,200 bytes is only one buffer; total allocation must be measured, including decoder/native/JIT/solver/output/temp costs.

The grid is explicitly at a user-requested admissible spacing and plane. Preflight enumerates cells/sources/crossovers/candidate fits exactly; if any ceiling or sampling/height prerequisite fails, return ineligible/resource_refused and a precise local recipe. Source block reduction, if selected explicitly, retains every observation and its residual; no first-N/every-N/stride substitution. No auto-coarsened grid. Spatial resolution limits remain visible even when rendering uses fine cells.

## Future online port, currently CLOSED

Proposed method ID magnetic.flight-line-processing/v1. Requests identify an owned immutable dataset version and exact numerical request SHA-256, not a URL, file path, executable, raw operator override or provider-fetch command. app/magnetic_contract.py verifies owner/source-policy/method/quantity/state and produces the exact local request bytes. app/magnetic_compute.py invokes that unchanged core in an attempt-bound restricted child. app/worker.py owns queue and lifecycle; app/database.py and app/bundle.py integration needs the persistence owner's full reviewed schema/export/recovery extension. No migration is designed/applied by this branch.

Submission, progress, cancel, terminal error, export/import and retries reuse the established product job API shape; each new attempt has fresh identity/custody and cannot replace prior success. A genuine positive online proof records fresh user input, changed scientific parameters, actual numerical child hashes, native CPU counters and owned durable result, then exports/re-imports the same arrays. TestClient acceptance, mocked subprocess, accounting-validator success or MT measurements are insufficient.

Existing [physical accounting contracts](../physical-worker-accounting/contracts.md) list gravity methods only; M03 is not admitted by that document. Native Linux/Windows controllers need method-specific reviewed profiles and source/runtime/module pins before registry integration. Startup/recovery must reject any unrecognized magnetic child, maintain deletion authority and block success until file and DB identity agree. Cancellation/crash/hash drift leave durable non-success and identified staging custody. No progress callback or inherited stdout can authorize publication.

## Visualization and course contract

Use AppShell, Tabs/SubTabs, Equation/InlineMath, Cite/Refs, existing theme/language tokens and six prescribed routes. Existing frontend/src/pages/Workbench.tsx is the integration owner; add the prospective MagneticLineInstrument and MagneticLineCourse only in a separately approved vertical. No seventh route, custom header/font or visible internal ADR/path prose. [ADR-0016](https://github.com/fsantibanezleal/_CAOS_MANAGE/blob/develop/conventions/architecture/1-frontend/ADR-0016-web-app-shell-and-content-depth.md), [ADR-0017](https://github.com/fsantibanezleal/_CAOS_MANAGE/blob/develop/conventions/architecture/1-frontend/ADR-0017-rotorvitals-frontend-bar.md), [ADR-0058](https://github.com/fsantibanezleal/_CAOS_MANAGE/blob/develop/conventions/architecture/0-archetype/ADR-0058-in-app-architecture-modal.md) and [ADR-0071](https://github.com/fsantibanezleal/_CAOS_MANAGE/blob/develop/conventions/architecture/1-frontend/ADR-0071-sized-containers-and-navigation-depth.md) govern composition.

| View | Quantities, identity and linkage |
| --- | --- |
| Map | Actual segment polylines grouped by flight/tie/reflight and sensor, metres/CRS, original/QC/partition masks, grid cells with nT legend. Never join gaps or unrelated lines. Select row/segment/cell to drive every sibling view. |
| Line profile | Supplied acquisition ordinal, along-track distance m or genuine UTC; original/derived nT and height/clearance on separately labelled m axes. Line direction reversal is visible. |
| Tie/crossover | Two actual bracket segments, interpolation weights, signed flight-minus-tie nT, z/time separation, eligible/rejected reason and leveling graph/gauge. No numerical residual for invalid crossing. |
| Residual | Observed-minus-predicted nT, zero-centred diverging scale; heldout/training/calibration partition visible. Standardized residual only with credible supplied error, with its meaning. |
| Power | k_e,k_n in cycles/m or rad/m as explicitly labelled, power nT^2 normalization; line Nyquist/support and directional filter response/removed power. No depth or geological-confidence title. |

One selected project/run on App; cross-case comparison belongs on Experiments/Benchmark. All hover and keyboard readouts resolve stable IDs into result arrays; null/zero/masked/unsupported are visibly different. Changing grid spacing/plane/damping/channel is a real new request, while pan/zoom/channel visibility is a labelled view change. On pending jobs keep old result labelled old, never reinterpret it under new parameters. Desktop/phone view sections split controls to fit; primary scientific area >=50% viewport, no document overflow, controls reachable by pointer/keyboard. EN/ES, light/dark, reduced motion and all five linked views require rendered acceptance.

The future architecture magnetic-lines.svg shows immutable source -> contract/partition -> correction/fit -> masks/evaluation -> export and separate local/online/replay lanes, with bilingual text pairs, theme tokens and explicit transfer labels. The wiki/course teaches quantities, correction evidence, IGRF/basis/datum, aliasing, crossover height, regularization, sealed evaluation, continuation versus interpolation, remanence/RTP limitations and exact worked local/online commands. No unrun field example is filled with synthetic outputs.

## Failure and deployment boundary

Rights/metadata ambiguity returns a durable eligibility reason. Numerical rank/conditioning or support failure returns ineligible/nonconverged, never an all-zero replacement grid. CPU/memory/disk/cancel failure produces no success artifact. If the actual host cannot meet bounds at useful spatial resolution, online stays CLOSED with full local execution/import. The approved one-ML-VPS origin remains the deployment destination for later integrated acceptance; this packet changes no production state, DNS, Pages, version, release or parent ledger.
