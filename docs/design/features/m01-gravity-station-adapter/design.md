# M01 ordinary gravity station adapter sub-SDD and ownership

Date: 2026-10-03. Status: APPROVED by main after reading all four documents and current app contracts, before code. Original design commit 60f9b2eae7fa86cec8a00fc32fddc27c3c7e13ea was persisted and pushed first. Read [research](research.md) first; [requirements](requirements.md) names every gate and [tasks](tasks.md) separates completed design work from implementation. This is a bounded seam within approved M01, not a new method/product, authenticated transport implementation or host approval.

## Scope and exact ownership

Main approved implementation after the design commit. Exclusive implementation ownership is exactly:

- data-pipeline/gravity_station_adapter.py, new ordinary local module, not an internal package.
- tests/numerics/test_gravity_station_adapter.py, new scoped unit tests with real numerical positives.

This feature's four Markdown files may be maintained with its evidence/convergence. No existing core, transform, tests, conftest, requirements, scripts, canonical arrays, app, shared schemas, API, private storage, registry, worker, migrations, frontend or release path is assigned. Original receipts/images/history and protected sources remain unchanged. There is no adapter placeholder or prospective test file committed before main's review.

Main owns the separate shared API integration after MT convergence: authenticated transport/strict byte parsing, account/owner/rights checks, raw hashes, main-approved job/attempt identity, dispatch/child executable, process/resource isolation, persistence, cancellation/recovery, private quotas/export and measured host admission. This ordinary adapter has no HTTP contract, CLI, filesystem publication protocol or worker entrypoint. Main decides those separately and must not treat local success as online authorization.

Base branch task/geophysics-m01-station-adapter-sdd starts at develop 6050100aeb3d1d482eefa1856ac67b2bc04b5bb1, after main merged PR #109. The scientific-core SHA-256 is 7863699269b491c2895bcf030d3fb65cf27ac32a652fce91112bc2c7c9c73321. The proposed implementation reuses this reviewed core and unchanged installed pins, not an independently rewritten correction algorithm.

## Ordinary callable and exact request

Proposed callable: run_station_corrections(request: dict) -> dict. Invalid requests/execution raise GravityStationAdapterError; no failure dictionary resembles a successful result. No optional executable/import/path/URL/caller callback is accepted. Only a fixed import of gravity_processing is permitted; use standard library helpers and the already installed official core engines.

The request has exactly six required keys, no optional keys:

| Key | Required meaning |
| --- | --- |
| schema_version | Literal gravity-station-adapter-request-1, private to this ordinary boundary; not an app schema edit |
| method | Literal gravity.station-corrections/v1, distinct from CSV outlier flags; no generic M01 fallback |
| dataset | The complete unchanged exact gravity-stations-1 parent payload: schema_version/state/metadata/stations/history |
| config | The explicit existing CorrectionConfig.parse input, without API-specific normalization or extra fields |
| input_dataset_sha256 | Lowercase SHA-256 equal to gravity_processing.digest(dataset) on this exact parent |
| submitted_config_sha256 | Lowercase SHA-256 equal to gravity_processing.digest(config) on the exact submitted config |

No owner/project/job/attempt/storage key/raw bytes/transport digest is guessed or inserted. Main's authenticated envelope links those separately. Supplied dataset.metadata.source_sha256 is source provenance, not either request integrity hash and not a verified provider retrieval. Matching supplied hashes establish internal integrity only, not authenticity or field-source eligibility. A fully changed but consistently rehashed scientific request is a different input, not the original request; main owns binding it to the admitted immutable parent version.

The exact existing core validates the scientific object and config: absolute calibrated downward gravity after known unit/sign conversion; WGS84 geodetic coordinates; declared tide/instrument processing; finite primitive errors; land receiver on/above surface; ellipsoidal heights or explicit orthometric geoid/error; known state/history. The schema has no mask, projected XY or arbitrary component key. Ambiguous relative-meter counts, principal facts, operational scripts, incompatible datums, missing SDs and flag-only CSV datasets do not receive a conversion adapter here.

Both hashes are checked before core execution. The caller's exact integer/float representation is retained for canonical hashing; no rewritten observation floats or reconstructed earlier serialization is substituted. An earlier-state resume supplies its actual complete parent. Core process_survey verifies that parent's known additions/order/parameters/value hashes before appending a later stage. The adapter does not take or authenticate an arbitrary earlier processing receipt, and it does not claim to reconstruct unavailable raw-instrument history. Parent processing receipts and their recorded Python provenance remain main-owned separate lineage.

## Bounded object admission, not raw transport parsing

Proposed review limits: 1..400 stations, maximum structural depth 16 (request root depth 1), 200000 total object/key/value nodes, at most 8192 UTF-8 bytes per string value, 128 UTF-8 bytes per key, and 16 MiB of canonical serialized request bytes. All limits are explicit conservative local adapter boundaries, not measured host resource acceptance or amendments to the unchanged core's 10000-station ceiling. No convenience subset or automatic thinning is selected.

Walk the object without invoking user hooks: exact built-in dict/list/str/int/float/bool/None only, string-only keys, valid UTF-8 encodability, finite numbers representable by the core, finite/capped counters and cycle detection. Reject ndarray, object arrays, subclasses/custom mappings, bytes, Decimal, generators and custom __deepcopy__/serialization objects before copying/hashing. Booleans are valid JSON scalars but not scientific numbers; the core's strict numeric checks remain authoritative. Shared noncyclic native subobjects are allowed if within the counted bounds; cycles are not.

Enforce structural/string/node limits before deepcopy/digest, and count canonical JSON encoder chunks before assembling a complete string so oversized input does not require an unbounded serialized copy. Canonical JSON uses the existing digest semantics: sorted keys, compact separators, allow_nan false and the same default ASCII escaping. A transport's UTF-8 byte count can differ from canonical bytes; keep those meanings distinct.

The adapter receives an already decoded object, so it cannot discover duplicate JSON keys lost earlier. Main's future parser must cap actual bytes and depth, reject duplicates/nonfinite/overflow/encoding issues before creating this object, and preserve exact immutable raw bytes separately. No raw-file read helper is introduced here. Deepcopy only after native-object admission; the caller must not mutate the object concurrently during a call.

## Execution, runtime and immutable scientific result

Check the fixed sibling core file's reviewed SHA-256 before a fixed lazy import inside the callable, then verify actual installed core PINS before numerics. This allows missing dependencies/import failures to produce a safe runtime record and prevents an unexpected core file from being imported by the adapter. No user-controlled import mechanism or sys.path change is added. Expected engines are exactly Boule 0.5.0, Harmonica 0.7.0, NumPy 2.2.6 and SciPy 1.15.2, matching the unchanged core PINS. Proposed compatibility lane: CPython 3.12.x release runtime, matching the reviewed isolated environment, with the actual patch recorded rather than invented or compared with an old parent patch. A core or engine change requires a new review; no installation, fallback or requirements edit occurs. Missing dependencies/pins or an unreadable trusted module fail closed. Module-file identity is a reviewed code-integrity control, not protection against a malicious interpreter or authenticated package-origin proof.

Main's approval adds the explicit trusted-import condition: the imported ordinary module's __file__ must resolve to that same fixed sibling file. A preloaded shadow in sys.modules rejects before numerical execution; checking only the sibling's disk hash does not verify which module Python actually imported. Check a preloaded module before import and the returned module after import, without using a user-provided path or rewriting sys.path. Tests cover a ModuleType shadow with a different __file__, missing/invalid __file__, and the real same-file module. This is a file-location/code-integrity check, not authenticated-origin proof.

The implementation first compares the imported filename's normalized absolute lexical path with the fixed sibling before resolving it. A foreign/remote shadow filename is not read or filesystem-resolved. Only the two own fixed module paths are read for fingerprints. The core exception class is validated and bound before execution so ordinary failures cannot turn into arbitrary exception-type lookups during error handling. Current local gate/evidence results are in [convergence](convergence.md); no shared integration follows from them.

Validate config with the core parser, retaining both its exact submitted form and explicit normalized defaults for the receipt. Plate/terrain targets still require explicit density and density SD; no adapter default makes missing physical information present. Existing nonphysical QC defaults are recorded exactly as the core normalizes them. Nothing is inserted into the submitted dataset/config, and no terrain/drift/tide/isostatic/curvature model is invented.

Call the real process_survey exactly once on deep copies of the admitted dataset/config. Existing history verification is not another emitted reduction. The core is the trusted numerical execution authority; adapter postconditions are integrity/schema checks, not a second independent scientific solve. Independent formula tests and full core parity verify the scientific seam. Repeated/backward targets and incompatible history reject through the core. Outlier flags remain derived diagnostics with every input station preserved; no correction mask/exclusion field is added.

Require the returned core object to have exactly dataset/processing/qc and its currently known nested fields. Check finite/typed/count-consistent output, unchanged originals/metadata/station order/history prefix, target/current state, no excluded stations, exact config normalization, method/engine/module/input/output identity, actual fresh runtime provenance and full_method_accepted false. Preserve every core warning and uncertainty model/component without relabelling bounds or zero primitive errors. The complete returned object is hashed. Error/warning semantics come from the trusted existing core and are also compared in full against a separate real-core call in unit parity tests; the adapter does not pretend to authenticate arbitrary externally supplied output.

Exact processing keys are method, input_sha256, output_sha256, config, engines, python, module_sha256, uncertainty_model, uncertainty_mgal, uncertainty_components_mgal, full_method_accepted and warnings. Normalized config keys are target, uncertainty_model, density_kg_m3, density_sigma_kg_m3, outlier_z and terrain. Exact QC keys are station_ids, longitude_deg, latitude_deg, receiver_ellipsoidal_m, surface_ellipsoidal_m, original_mgal, derived_mgal, robust_z, outlier_flag and excluded_station_ids. Exact uncertainty component keys are observed_gravity, latitude, receiver_height, surface_height, density, geoid and terrain. All stationwise quantities retain input order and count; robust_z alone permits the core's documented null/unassessable values. Reject missing/extra keys rather than carrying an unverified extra receipt field.

The result has exactly schema_version, method, correction_result and receipt:

| Key | Meaning |
| --- | --- |
| schema_version | Literal gravity-station-adapter-result-1 |
| method | Literal gravity.station-corrections/v1 |
| correction_result | Full unchanged process_survey return, including exact processing keys/errors/warnings/QC |
| receipt | Separate adapter integrity and non-acceptance record below |

The receipt has exactly these keys:

- adapter_version: literal 1 as a string.
- adapter_module_sha256: digest of this new trusted module's actual bytes.
- core_module_sha256: verified approved core digest, identical to correction_result.processing.module_sha256.
- request_sha256: canonical digest of the complete six-key request.
- input_dataset_sha256: verified exact parent digest, also equal to core processing.input_sha256.
- submitted_config_sha256: verified exact caller config digest.
- normalized_config_sha256: digest of core processing.config, including explicit defaults.
- output_dataset_sha256: digest of corrected dataset, equal to core processing.output_sha256.
- correction_result_sha256: digest of the entire unchanged core result, covering errors/warnings/QC.
- engines: actual verified core PINS, equal to core processing.engines.
- python and python_implementation: actual execution declarations for this fresh call, compatible with the reviewed lane; not rewritten parent runtime provenance.
- acceptance: exact object host_approved=false, full_method_accepted=false, field_source_verified=false.

No generated timestamp, raw-file hash, owner/job identifier, wall/RSS/scratch estimate, geological truth or automatic public rights decision is fabricated. Main separately measures and stores resource/job/transport receipts and computes the final saved-envelope byte hash; no self-referential envelope hash is inserted. Acceptance false here means this function does not certify those authorities, even if a later main-owned host receipt authorizes its execution. Main must keep its actual approval decision separate, not flip these local non-certification declarations to manufacture approval.

## Safe failures

GravityStationAdapterError is an ordinary exception with a to_record() method returning exactly code, field, message, retryable. Codes/messages and optional fields come from a fixed allowlist. retryable is false for all errors in this boundary; main decides future infrastructure retry policy separately. The proposed records are:

| Code | Field | Fixed message |
| --- | --- | --- |
| adapter_contract | request | Request does not match the reviewed station adapter contract. |
| adapter_limit | request | Request exceeds the reviewed local adapter bounds. |
| input_identity | input_dataset_sha256 | Parent dataset integrity does not match the supplied identity. |
| config_identity | submitted_config_sha256 | Submitted configuration integrity does not match the supplied identity. |
| scientific_contract | null | Dataset or configuration does not satisfy the reviewed correction contract. |
| runtime_incompatible | runtime | Reviewed runtime, engine or scientific core identity is unavailable or incompatible. |
| result_integrity | result | Scientific result does not satisfy the reviewed adapter postconditions. |
| execution_failed | null | Station correction execution failed without a publishable result. |

Never return/log raw core exception text, exception arguments/context, arbitrary unknown keys, user values, station IDs, citations, filenames, URLs, paths, subprocess output or traceback locals. Known core GravityContractError maps to scientific_contract rather than string-parsing its potentially user-influenced missing/unknown-key lists. Adapter structural/hash/runtime/result checks give their fixed codes. Other ordinary execution exceptions map to execution_failed with no partial result. Do not catch BaseException/KeyboardInterrupt/SystemExit or turn cancellation into success. Displayed chaining is suppressed, but the error record is the only safe serialized surface: main must not introspect/serialize the original exception context.

All scientific result/source metadata remain private caller data, even if the error record is safe. The function prints nothing, writes no user data, makes no network or subprocess calls, and never controls host approval. Reading its own two fixed trusted module files for fingerprints is the only new adapter filesystem operation; no user-supplied path exists. Source-provider scripts, imports and array/pickle execution are prohibited.

## Prospective verification and kill criteria

One new test file implements the eleven named gates in requirements.md only after review. Real positive cases cover all three derived targets, SI/microGal/upward conversion, legitimate known-stage resumes, exact parent integer serialization, explicit orthometric geoid/errors, conservative/independent propagation, zero deterministic primitive SD and flagged-but-retained stations. Compare the complete core result, not only selected columns. Call-count spies support rejection and ensure one real core execution; they are not substitutes for positive physics.

Independent tolerances retain the existing reviewed scientific gates: Somigliana surface parity 1e-5 mGal due to published constant truncation, known 45-degree/1000-m normal gravity 1e-7 mGal, plate/sign 1e-10 mGal, authored 12-mGal worked disturbance 1e-8 mGal, normalized sign/unit parity 1e-8 mGal, and deterministic full-object parity exact in the same runtime. Existing uncertainty derivative tolerances remain as specified in test_height_datum_and_uncertainty; no new loosening is authorized. Assert a second empirical free-air term is absent.

Adversarial cases: unknown method/schema/keys, CSV/provider/flag-only shapes, missing datum/error/instrument status, duplicate geometry/IDs, repeated/backward/contradictory histories, stale parent/config hashes, malformed SHA, nonfinite/bool numeric inputs, cycles/custom hooks/ndarrays, 0/401 stations, excessive depth/nodes/strings/canonical bytes, incompatible runtime/pins/core, malformed returned keys/state/hash/errors/components/counts and private markers inside ordinary/core exceptions. No field bytes or fabricated field fixtures are added. Injected failure controls must produce fixed safe records and no result/files/logs.

Parity, identity, mutation or privacy failure blocks adapter acceptance. Any need for a shared file edit, requirements update, unsupported physical conversion or alternative core is a review stop, not implied authority. A bounded local pass is not proof of authenticated ownership, durable worker lifecycle, measured host safety, eligible Bartlett modelling, full M01 or deployment.

## Main review request and remaining authority

Main approved the exact six-key request, four-key result/receipt, callable name, native-object limits, fixed safe-error mapping, direct exact-parent resume policy and CPython 3.12/core-pin lane, with the imported-file check above. Implementation may now proceed only in the two assigned new paths plus these feature docs. App/shared schema and MT worker protocols remain separately main-owned; this approval is not shared integration authority. Host approval remains false. Main will independently review the final pinned unit before merging; no merge/deploy is authorized here.
