# M01 scientific course sub-SDD

This design plus [requirements](requirements.md), [curriculum](curriculum.md), [contracts](contracts.md), [scenarios](scenarios.md), [workflows](workflows.md) and [validation](validation.md) define the course's scientific, display and source-binding contracts. Primary scientific references and derivations are in its six bilingual chapters. Historical approvals, initiative state and runtime receipts are private management records, not product interfaces.

## 1. Bounded outcome and exclusions

Propose a deep six-question M01 course explaining already implemented ordinary local station corrections, equivalent-source gridding and upward continuation. It teaches justified user-declared eligible inputs, independent analytical controls and rejection reasons. It does not invent field examples or implement missing instrument/DEM reductions. It is not a new method, generic physics dashboard or recovered density model. No M02 inverse or M13/neural work is included; a future neural surrogate would require a different approved design, training/holdout protocol and physics evidence, not an extra course badge.

No existing product scientific file, metadata, ledger, canonical artifact, dependency, API/backend/schema/storage/worker, frontend route/style or MT lesson may change under the current instruction. Authenticated owned correction children and physical jobs remain MAIN-owned future integration; host approval stays false and device profile closed/unset. Documentation/calculators/replay cannot waive that gate. Full M01 field-source acceptance stays open.

The minimal sequence is (A) this research/SDD review, (B) separately approved authored wiki-only content, then (C) separately approved owned lesson components/tests and actual recorded controls. A review of A is not automatic authority for C. No speculative shared host work is required to complete B.

## 2. Actual source-to-course seam

The committed course-record index and executable verifier pin unchanged modules. `process_survey(dataset, config)` returns exactly dataset/processing/qc. The deterministic processing object has twelve keys: method, input_sha256, output_sha256, config, engines, python, module_sha256, uncertainty_model, uncertainty_mgal, uncertainty_components_mgal, full_method_accepted, warnings. CLI receipt timestamps are a separate layer, not part of that object.

Ordinary `run_station_corrections(request)` has six request keys and four result keys, with a thirteen-key receipt; [workflow contracts](workflows.md) specify them. It is not an API endpoint. Its fixed sibling source hash, resolved imported __file__, actual engine pins and CPython3.12 requirement are not authenticated-origin proof.

`transform_survey(request)` accepts exactly schema_version/correction_result/geometry/config. Pass the entire three-key core result, or unwrap the ordinary adapter's correction_result, not its whole four-key envelope and not only its corrected dataset. Admission verifies known deterministic processing identity, config, engines, source, output, errors, warnings, acceptance and compatible recorded Python provenance. It replays to verify, not apply corrections twice. Resumed integer-bearing core parents can be valid for the adapter yet not independently reconstructable by the bounded transform admission; preserve the parent and report this limitation rather than coercing integers or replacing input_sha256.

The transform result has sixteen top-level keys: schema_version, original_correction_result, geometry, config, model, selection, split, stations, evaluation, axes, grids, condition, nonuniqueness, uncertainty, resolution, provenance. Displays read these named scientific fields; do not invent a universal uncertainty/result abstraction shared with MT.

## 3. Three execution lanes

| Lane | Inputs and authority | Output/claim |
| --- | --- | --- |
| Explanatory scalar calculator | Explicit bounded educational numbers; model/source label and units; no file upload, arbitrary code or solver | Surface gamma, infinite-plate magnitude, two-error covariance illustration or ideal Fourier attenuation only; no scientific receipt or job |
| Source-bound recorded control | Actual approved local run of unchanged prism controls; immutable request/result/runtime/source/config/split bindings | Replay of authored analytical controls; view selection never recalculates a different physical scenario |
| User-file Python workflow | User's own exact eligible station JSON, declared errors/geometry and existing pinned environment | Actual local core/adapter/transform results and fresh exports; not host-approved or field-source certified merely because code runs |

There is no fourth live-browser physics lane in this proposal. A future authenticated run control must wait for MAIN's physical-vertical assignment and real approval/job identity. Do not attach a static record to that label. No browser analytical calculator reads provider data or emits a child dataset.

## 4. Lesson model, figures and shell seam

Six chapters answer [curriculum](curriculum.md) questions. After approval, every EN/ES chapter must contain at least four developed paragraphs (physical setup, mathematical argument, observable consequence, failure/limit), captioned equations with all symbols/units, a worked reasoning question and references adjacent to the claims. Counts are floors, not a substitute for scientific review. EN and ES carry equal restrictions and error definitions.

Each of the six proposed diagrams explains a physical relationship: reference surfaces, plate versus relief residual, shared-error coupling, mathematical layer versus independent prism, spatial train/holdout/support and upward spectral attenuation. Axis/height/component directions are literal. No actual field outline/private points or inferred geology. Planned wiki figures are scoped SVGs under a new wiki-local assets directory; dark/light palette and captions inherit the shell when mounted. Alt text must explain the relationship rather than list colours.

The complete current M05/M06 components/data/exercises/diagrams/record producer were read. Reuse their question/equation/citation and visibly recorded-result pattern, not their observations, rho_a/phase errors or observed-minus-predicted sign. M01 residual is prediction-minus-observation. Current MT course is mounted in Research.tsx methodology/implementation and Python areas; no large-route rewrite is included. MAIN must assign a minimal M01 mount seam after component approval. Until then wiki content is independently readable and a frontend mount stays BLOCKED_BY_ASSIGNMENT, not silently completed.

Use installed shared-shell 0.6.8 Equation with bilingual captions, InlineMath, Figure, Callout, language context, controlled Tabs/SubTabs and per-section Cite/Refs. The library's ReferenceList export does not override ADR-0017's prohibition. No fonts, theme roots, body-width/global CSS or shell tab replacements. Event-driven calculators have no animation loop; if animation is later proposed, pause/reduced-motion/visibility and ADR-0071 review apply. Six lesson questions are navigation topics, not six new method-family acceptance claims.

## 5. Current limits that lessons cannot hide

- Core CLI supports 1..10000 rows, while ordinary adapter and transform lanes bound 1..400 and 20..400 respectively; transforms additionally need at least 20 unmasked noncollinear stations. A source subset does not repair scientific eligibility.
- Core supports only stated land/on-or-above-ellipsoid geometry, WGS84/tide-free calibrated absolute gravity. Datum/correction state and primitive SD are explicit. Supplied terrain is not generated DEM terrain. `terrain: null` is valid for a nonterrain target; a non-null object is not.
- Transform geometry is fixed conditional, <=20 km local metric extent, with exact receiver heights and original masks. No coordinate conversion or source-free proof is supplied by this engine.
- Fit uses diagonal weights even with supplied covariance; full covariance propagates conditional noise. Current first-order/marginal limits do not become confidence intervals, parameter-selection uncertainty or geological error.
- At most twelve depth/damping pairs, eight candidates per list, at most12000 grid nodes. Height is absolute and cannot fall below any original receiver. Null unsupported values remain null; no filling/extrapolation.
- Source plane depth and coefficient norm illustrate mathematical nonuniqueness, not recovered physical depth/density. Damped conditioning, sampling, coverage, fit and geological resolution are distinct.
- Actual author principal-fact data lack resolved vertical datum/primitive errors/original lineage for this workflow. No field modelling eligibility claim, new private-source catalogue or fabricated fix.

## 6. Proposed artifacts and evidence

Do not change a scientific receipt schema for teaching. A future course-record index is a separate exact eight-key plain object: schema_version=`m01-course-record-1`, scenario_id, label_kind=`synthetic_control_replay`, request_sha256, result_sha256, source_pins, runtime, artifacts. `source_pins` maps the five inspected local scientific/figure modules to their actual SHA-256 values. `runtime` records python, python_implementation and engines from the actual run. `artifacts` is a list of exact role/path/bytes/sha256 entries for the original request, result, emitted CLI receipt and all actual theme-aware plots. Byte counts are measured original-file lengths for capped loading, not a proposed device-memory guarantee. Paths must be scoped relative authored-course artifact names, not user/private filesystem paths. No timestamp/origin/approval is invented by a viewer.

This index binds the exact result (which contains config and split identity) and exact scientific receipt bytes, preserving their distinct hash dialects. A later approved Python producer must verify every binding against emitted files, not only compare labels. JavaScript cannot reconstruct the Python scientific digest from parsed numbers without losing integer/float identity: the future browser must verify original artifact-byte hashes against the approved index before parsing, and cross-check receipt/result declarations, not use JSON.stringify as scientific replay. Source/native-parent preservation resides in the unchanged bound files, not a browser-rewritten object. Changes to any data/error/depth/damping/height/mask/geometry require a new actual request/run/index; selected plot view or already computed height does not. Missing/stale/unknown scenario bindings fail closed with no metric/map rendered. No course index or result array is generated now. Index structure itself remains subject to MAIN review.

Future evidence needs independent existing formula/parity tests, actual blocked controls, negative controls, numerical receipts, independent source/receipt self-review and rendered EN/ES light/dark/mobile/keyboard/direct-route QA. Frozen scientific tolerances cannot be weakened to obtain course agreement. Historical receipts stay historical. Test success cannot substitute for reading a lesson or checking rendered signs.

## 7. MAIN decisions required

Approve/amend all six questions, the four explicitly explanatory models, the exact recorded-index seam, no-live-job boundary, integer/resume limitation and ownership sequence. Approve first wiki-only paths after full read; separately assign future lesson component/test/artifact paths and the minimal mount seam. Any requirement for a live job, arbitrary user upload, external DEM computation or neural model is a scope change requiring another coordinated design. Current work ends with a docs-only reviewable pinned branch/PR, not course PASS.
