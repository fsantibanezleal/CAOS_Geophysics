# M08 actual local waveform processing sub-SDD

Status: ordinary local implementation / native and field gates open. This packet defines the local calculation, not online activation or release.

Read in order: [research](research.md), [contracts](contracts.md), [algorithms](algorithms.md), [requirements](requirements.md), [validation](validation-plan.md), [real case plan](ridgecrest-case.md), [tasks](tasks.md). Each requirement has a future named gate. Ordinary tests exist; resource/field/full-method gates remain separate. See tasks for current scope.

## 1. Scientific question and complete local result

Given exact original integer-count waveform bytes, exact instrument metadata bytes and a declared UTC window/configuration, calculate what the selected channels actually measured, whether clock/continuity/clipping/response evidence permits processing, the conditional band-limited native motion estimate, its explicitly filtered trace and PSD, and classical onset candidates. Preserve failures with their measured source identities. Independent analyst references may subsequently evaluate sealed candidates; they cannot control decoding, conditioning, thresholds or selections.

The named proposed method is `seismic.waveform-qc-classical/v1`, separate from the frozen STEAD M08 comparator. The physical correction is response deconvolution, not inversion for earthquake location, magnitude or Earth structure. Counts are never labelled velocity by file extension. A full response chain is not a newly measured calibration. A trigger interval is not automatically P/S. `field_truth` and calibrated arrival uncertainty are always null. Primary science and engine decisions are in [research](research.md); [algorithms](algorithms.md) specifies every numerical operation.

## 2. Proposed owned files after approval

| New file | Exact responsibility |
| --- | --- |
| `data-pipeline/waveform_input.py` | Byte/sample/record/XML preflight, strict request contract, bounded MiniSEED2 decode, exact channel/clock/response-epoch join; safe typed errors. No path/network access. |
| `data-pipeline/waveform_processing.py` | Ordinary `process_waveform_record(raw_mseed: bytes, raw_stationxml: bytes, request: dict) -> WaveformResult`; private numerical arrays, QC, native response removal, filter, PSD and candidates. No filesystem/network or source acquisition. |
| `data-pipeline/waveform_evaluation.py` | Ordinary `evaluate_waveform_candidates(sealed_result, reference_bytes: bytes) -> EvaluationResult` and `references_from_stp(raw: bytes, event_id: str, selected_nslc: tuple) -> dict`; bounded original STP conversion/lineage and explicit unlabelled matching, never a picker input. No generic QuakeML adapter. |
| `scripts/process_waveform_m08.py` | Local CLI taking explicit `--mseed`, `--stationxml`, `--request`, `--out`; bounded regular-file reads, one supervised child, safe statuses, new-directory-only streaming result writer and hashes. Optional `--evaluate-with` takes converted reference JSON only, opened after sealing. Original STP conversion is a separately invoked ordinary function, not format sniffing/fetch inside the picker. |
| `scripts/process_waveform_m08.ps1`, `scripts/process_waveform_m08.sh` | Equivalent path-explicit wrappers, no download/install/global setting. |
| `tests/data/test_waveform_input.py` | Authored real-format bytes, adversarial preallocation/grammar/epoch/identity controls. |
| `tests/numerics/test_waveform_picks.py` | Product-named integration gate and independent response/filter/PSD/trigger/evaluation oracles and parameter effects. |
| `tests/data/test_waveform_resources.py` | Fresh cold-process nominal/upper/malformed/native crash/timeout/cancel/output-bound measurements. |
| `tests/data/test_waveform_ridgecrest.py` | Opt-in exact original case receipts, rights and retained QC negatives; no live download during a test. |
| `tests/fixtures/waveform_m08/README.md`, `tests/fixtures/waveform_m08/authored-controls.json` | Explicitly authored sensor/signal/record recipes and expected analytical values, not provider bytes or fabricated field truth. |

These files are not authorized yet. No legacy file is a proposed implementation target. In particular, no `ingest.py`, `app/`, requirements file, source ledger, canonical registry, frontend, M13 reader/model/checkpoint or frozen comparator edit. Dependency availability is a separate approval decision; absent/incompatible ObsPy must stop execution rather than trigger an installation. No internal package is introduced.

Future case originals and execution outputs go only to user-declared external/private ignored directories. The retained case declaration belongs to `docs/design/features/m08-waveform-user-data/evidence/ridgecrest-case-receipt.json` after a separately approved acquisition; its current plan is [ridgecrest-case.md](ridgecrest-case.md), with actual byte/hash fields unset. Field arrays cannot be committed merely because they are small.

## 3. Calculation sequence and terminal semantics

1. CLI resolves only the four explicitly supplied paths. Reject URL/glob/archive/symlink/reparse/device input and output inside any input file or protected tree. Hold each input handle, bounded-read/hash its actual bytes once, detect growth beyond cap; processing receives those same bytes. Never reopen by mutable path for the scientific read. No recursive delete, overwrite or provider request.
2. The ordinary boundary requires exact `bytes` and a strict native request. Preflight the complete MiniSEED record chain and XML grammar/counters before native decode/inventory construction. Do not ask ObsPy to read a whole archive and then slice/check limits.
3. Decode admitted records one at a time, verify native output count/identity/rate/time and STEIM integration consistency against preflight, append only into pre-sized bounded counts arrays. Preserve original record offsets/order while computing a chronological view. Never fill gaps, deduplicate overlap or zero-fill channels.
4. Compute raw QC and resolve one exact nested NSLC response epoch covering the entire conditioning interval. Parseable but scientifically unsupported records produce `qc_only` with ordered reasons and raw diagnostics; no physical/pick arrays. Invalid grammar/bounds/native decode mismatch produces `rejected`, not a successful empty artifact.
5. For fully admitted records, process a private float64 copy per channel. Keep raw arrays read-only. Obtain the engine's complex response, audited inverse/prefilter, conditional physical trace, explicit SOS filtered trace, Welch densities and unlabelled candidate intervals. No cross-channel summation when units differ.
6. Seal a `computed` result with exact source/request/engine/array hashes. If optional references were supplied, open them only in the separate evaluator after this seal. Evaluation cannot mutate any prediction.
7. CLI writes uncompressed little-endian arrays and bounded metadata to a freshly created output directory, atomically publishes its final manifest only after verifying every size/hash/finite check. An existing destination is an error; cancelled/failed partial output has no success manifest and is retained privately with status, not silently deleted or reused.

Terminal statuses: `computed`, `qc_only`, `rejected`, `engine_unavailable`, `failed`, `cancelled`, `timed_out`, `resource_exceeded`. Exit codes respectively 0, 2, 3, 4, 5, 130, 124, 6. Evaluation adds its own `evaluated` or `not_evaluable` record and never changes the calculation status. No worker/job/owner/storage/API contract is borrowed. `computed` means this local algorithm completed, not science/provider/method/host acceptance.

## 4. Resources and actual admission holds

Proposed bounds are literal in [contracts](contracts.md): 16 MiB MiniSEED, 2 MiB StationXML, 64 KiB request, one station, at most three channels, 4096 records, 180000 decoded samples overall and 300 seconds conditioning duration. These are a local algorithm envelope, not a measured process-memory bound. One integer record can declare far more samples than its payload supports; all allocation counters must pass before decompression.

An admitted channel has at most 60000 samples. Response FFT is at most 131072, so each complex frequency vector has at most 65537 values. Three float64 time products need at most 4320000 array bytes across all channels, raw int32 counts at most720000; response/audit/filter/PSD/metadata copies add more. Those arithmetic counts do not include XML inventories, native libraries, Python containers, FFT temporaries, allocator fragmentation, instrumentation, process startup or parent overhead. All must be measured in fresh processes.

Proposed artifact ceiling: 32 MiB total uncompressed derived bytes, with 2 MiB JSON metadata maximum and no original raw source copy. Pre-count every array and conservative metadata bound before writing, then count actual bytes during streaming; do not serialize/zip an unbounded graph and check afterward. No ZIP/bundle import or browser representation is proposed here. Numerical arrays remain float64; display thinning cannot be used to force acceptance.

Response work W is the exact aggregate bin-coefficient expression in contracts, capped at20000000 before evalresp. It is a proposed complexity gate, not a CPU-seconds conversion; actual FIR/PZ native time still needs measurement. All XML coefficients, selected native inventories, operator arrays and return arrays count toward the measured peak, including the scanner-only and whole-helper negative controls.

Timeout candidate is 60 s for the local child, measured separately with and without instrumentation. Memory acceptance threshold starts UNSET/CLOSED; choose only after the [resource matrix](validation-plan.md) has actual parent/child/process-tree peak, CPU, scratch and cancellation/crash evidence on a named local runtime. Missing enforcement/telemetry is `UNRESOLVED`, not zero or PASS. Windows Job Object and Linux controls require their own approved implementation/revalidation. This unit cannot certify a phone, browser, VPS or the larger physical vertical's provisional server ceiling.

## 5. Engine decision and exclusions

Proposed scientific engine: ObsPy 1.4.2 `read(..., format='MSEED')`, `read_inventory(..., format='STATIONXML')`, evalresp and `Trace.remove_response` on private bounded copies; NumPy 2.2.6 and SciPy 1.15.2 for float64 arrays/filter/Welch. This is a source-reviewed candidate, not an installed compatible stack. No automatic fallback to another ObsPy/libmseed/evalresp version, no version upgrade, no scalar-only response substitute. Record CPython/OS and package/native-library identities in each execution receipt. Native warning/failure handling and MiniSEED decoder isolation are acceptance gates, not assumed Python exception safety.

Excluded: MiniSEED3, full SEED, floating sample encodings, arbitrary stations/archives, DAS/SEG-Y, sensor-polynomial correction, time-varying/multiple response epochs, resampling, interpolation, rotation, non-native motion conversion, magnitude/location/FWI, training/M13 inference and automatic phase assignment. These exclusions bound one scientifically complete local trace workflow; they do not redefine the full M08 product requirement or waive its future UI/online/rendered/source gates.

## 6. Approval and evidence sequence

Sequence: authored test-first gates; ordinary parser and real engine integration; independent numerical controls; unchanged original case and rights; separately reviewed cold resource/crash/cancel controls; independent pinned review. Missing engines, retained failures and skipped gates remain disclosed. API/UI/browser/host release is separate.
