# M08 local user-data and export integration

This guide describes the implemented ordinary interfaces and authored Windows controller, not evidence that native safety gates passed or permission to decode hostile native files in-process. Read the [science chapter](waveform-processing.md) and [exact inputs](../design/features/m08-waveform-user-data/contracts.md). No scientific threshold or selection is changed by export or containment.

## 1. Supply actual instrument data

Supply exact immutable MiniSEED2 integer-record bytes, unchanged StationXML and every native request field. Request schema is `caos.local-waveform-request.v1`; copy the contract's full schema, not a partial JSON example with hidden defaults. Its channels identify one station's exact network/station/location/channel and native conditioning/analysis intervals. Include separately supported rights declarations, acquisition identity, processing settings, and nullable ADC rails. Empty location is literal empty string; only the explicit catalogue adapter maps provider `--`.

Waveform cap16MiB, XML2MiB, request JSON64KiB. Counts, record/sample bounds, complete response epoch, sample rate, stage chain, units and analysis coverage are checked independently. A user-selected rights enum is not source authentication. Do not upload/commit raw data or derived arrays without per-object publication rights. Software and waveform licences are different.

`waveform_m08_files.open_input(absolute_path, cap)` holds regular-file and ancestor identities, refuses links/reparse/unsafe paths and reads once. `InputHandle.read_bytes()` records consumed-byte SHA256. These are cooperative private-file safeguards, not a hostile same-user sandbox. The consumer must retain handles throughout its transaction and must not re-open source paths for processing. No directory traversal, archive or network fetch exists.

## 2. Ordinary science boundary

`waveform_m08_child.calculate_bytes(mseed_bytes, stationxml_bytes, request_json_bytes)` invokes the real ordinary calculation and seal; request raw byte/hash identity is attached separately from canonical scientific configuration identity. Direct execution of the child file refuses: the fixed Windows supervisor selects the contained science role. Ordinary tests use authored fixtures through this callable; actual owned-worker tests separately invoke the selected native context on unchanged private originals.

Computed motion uses the actual channel-native displacement/velocity/acceleration response, not a suffix or scalar sensitivity substitute. `qc_only` retains counts and reasons only; physical/filter/spectrum/candidate arrays must be absent. Input rejection is a fixed safe error, not a fabricated waveform result. Onsets are unlabelled, phase and sigma null. Acceptance flags stay false.

The exact Latin1 XML declaration is supported without transcoding original bytes. One interior unity-gain stage may derive equal explicit neighbouring units; its ledger retains original nulls and names that narrow derivation. FIR zero-Hz normalization requires finite nonzero DC and explicit decimation. The actual native stage chain must match the scanner's coefficients, gains, units and decimation. Independent full complex tests distinguish Correction from estimated Delay; transport admission alone does not establish physical field validity.

## 3. Seal, then score independently

`seal_result(result)` produces exact canonical metadata bytes and calculation SHA256 over validated finite, bounded owned arrays/descriptors. No reference enters the calculation. Preserve that seal before any evaluation reference read. `evaluate_waveform_candidates(sealed, reference_json_bytes)` applies unchanged0.5s matching and reports every ambiguous/unusable/unmatched reference. It cannot turn ordinal catalogue quality into calibrated timing sigma or field truth.

Explicit adapters are `references_from_stp` (legacy9) and `references_from_scedc_cloud_stp` (cloud10); no autodetection or fallback. They preserve original phase bytes/hash and selected-row byte lineage. The caller constructs the bounded converted analyst-reference JSON with independent rights/citation and the original parent SHA. Regeneration from original bytes is necessary for source-valid claims; supplied hashes alone are not proof.

For the selected Ridgecrest HNZ case, the cloud file's GSC arrival is HHZ. Converted HNZ references are empty, so any later eligible computation is `not_evaluable`, never a reassigned match. Preserve the old XML and legacy-STP failure receipts alongside the new format diagnostic. Already inspected references cannot support a new blind-validation claim.

## 4. Export without copying raw sources

Ordinary interfaces in `waveform_m08_export`:

```python
plan = plan_export(result, sealed, evaluation=bounded_evaluation_json_or_none)
with create_output(new_absolute_leaf, trusted_parent=existing_private_parent) as owned:
    receipt = write_export(plan, owned)
with open_output(existing_export_absolute_path) as readonly:
    reopened_seal = verify_export(readonly)
```

Names are generated from exact registered arrays, never user paths. Arrays are little-endian `.bin`, no pickle/NPY/ZIP; metadata declares dtype, shape, unit, length and hash. Read-only memoryviews stream chunks<=65536 without full-array byte copies. Inclusive32MiB counts arrays, calculation, optional evaluation, receipt and manifest. Bounded JSON is checked before encoding/tree allocation. Finiteness and masks are checked independently, even if an adversary rebuilds all hashes.

Evaluation, if supplied, must name the exact seal and pass bounded strict schema and matching replay. This authenticates neither original reference JSON nor provider truth. Receipt authority is always false, resources unavailable. A final manifest is a verified local-export marker, not power-loss durability or native resource eligibility.

Only a new leaf beneath an explicitly supplied preexisting private parent can be written. Existing directories/keys/backups are never reused, erased or permission-modified. Members are exclusive, fsynced and independently reopened before no-replace manifest publication. Read-only `open_output` cannot write, repair or publish. A partial directory is retained for inspection; do not automatically retry into it or infer success from child exit0.

## 5. Fixed contained CLI contract

Python CLI requires explicit `--mseed`, `--stationxml`, `--request`, `--out`, `--python` absolute paths; optional `--evaluate-with` is converted bounded reference JSON only. Windows contained execution also requires `--admission`, an explicit reviewed private code/runtime/ABI/context record. This record is a local operational prerequisite, not an authentication mechanism, signature or production trust certificate. PowerShell wrapper takes explicit `-PythonPath`; shell wrapper's first argument is explicit Python path. Wrappers forward literal argv and never install dependencies. Paths cannot be URLs, globs, devices, ADS, UNC, links, aliases or an existing output target.

Without admission, CLI returns exit4 / `engine_unavailable` / `supervisor_unavailable` **before source/reference reads, staging, native computation or output creation**. With admission, the fixed Windows observer/controller route is wired; absent/mismatched ABI, code, native closure or private context fails closed. No unsafe-direct flag, injectable provider, environment authority toggle, arbitrary script or in-process fallback exists. Authored route/source tests are not actual native safety or a positive contained scientific case.

The fixed route is: private-parent/code/ABI/native-closure checks; at-creation suspended contained controller; exact original reads/hash and private staging inside accounted controller; suspended child membership acknowledgment before science; seal without labels; child drain/exit; independent calculation verification; separate reference open/evaluation; streamed copy to NEW final export; controller exit; stable quiescent job lifetime samples; separate provisional resource receipt and checked handle-release acknowledgment. No scientific child sees originals' paths or reference bytes. Reject3, QC2, computed0, engine_unavailable4, failed5, resource6, timeout124 and cancelled130 remain distinct.

Controller `copy_export` never rewrites the staging manifest or buffers entire arrays. It independently validates both source and final exports and checks retained input+staging+final+control/log reserve+private startup-cache bytes against the unchanged logical scratch limit before copying. Partial outputs and diagnostic staging stay private; no existing user directory is overwritten or erased. The ordinary manifest is not resource eligibility: missing external receipt/release, any failure receipt or uncertain crash forbids success. Resource receipts keep runtime/method/host authority false. These are cooperative owner-controlled local boundaries, not a hostile same-user filesystem/network sandbox.

Experimental Windows limits are defined in the [resource contract](../design/features/m08-waveform-user-data/intrinsic-resources.md). Committed job memory is not RSS; an experimental ceiling is not an accepted device minimum. Cumulative job user+kernel accounting includes the controller and exited descendants; sampled stopping is not instantaneous zero-overshoot enforcement. Actual Windows safety, cold nominal/upper and unchanged original physical cases remain separate execution gates. Linux needs its separately reviewed concrete implementation and cannot inherit Windows evidence.

## 6. Evidence boundaries

Authored analytic and direct numerical controls, held-out counts-comparator replay, unchanged-original format diagnostics, ordinary export/file tests and native platform controls are different evidence classes. The held-out display subset is already inspected and its weak agreement remains negative; no new learned-method inference occurred. The actual owned Windows worker processes original files without source repair; scientifically ineligible requests remain visible QC-only. The frozen whole-second Ridgecrest request is off its sample grid and retains `gap`; any separate sample-aligned request has a new scientific identity and cannot replace that negative or support a blind claim. Actual full-envelope/cold/adversarial and independent platform gates remain required; local directory/ABI binding tests alone cannot close them.

## 7. Protected projects and external storage

The API and worker require explicit absolute external `GEOPHYSICS_DATA_DIR`; `GEOPHYSICS_DB_PATH`, if set, must also be external. No repository raw/model/temp default exists. The selected `.waveform-context/context.json` binds actual interpreter and admission bytes; `scripts/qualify_waveform_m08.py` requires an explicit external root, selected compiled SDK probe/hash, review and exact source revision. It measures only a Windows local context and grants no scientific/host authority. Requalify after scientific/controller source changes. Queued jobs bind `implementation_sha256` and reject changed code rather than silently executing the new version.

The CLI and native transaction reject repository-contained working input,
request, reference, admission and output paths before I/O or launch. Use the
device's external data/temp roots for these files. The selected interpreter and
reviewed code are different roles: the existing product scientific environment
may execute an isolated worktree's sources. Relative database paths are rejected,
not silently converted into an absolute path. Qualification inventories the
direct Python image's actual closed bootstrap and scientific environment;
case-equivalent Windows image paths collapse only when their byte hashes agree.
The admitted native closure still rejects unknown images and duplicate keys.

The isolated browser harness uses a separate `qa-waveform.html`, existing shared
shell/styles and the actual migrated API and waveform worker, not mock results.
It requires explicit external `GEOPHYSICS_QA_DATA`, `GEOPHYSICS_QA_DIST`,
`GEOPHYSICS_QA_CACHE` and `GEOPHYSICS_QA_EVIDENCE` roots, plus the selected SDK
probe/review/scientific interpreter. `tests/ui/waveform_devserver.py` requires
`GEOPHYSICS_WAVEFORM_QA=isolated-loopback-only` and binds loopback only. Run the
isolated Vite build with `vite.waveform-qa.config.ts` and the browser checks with
`playwright.waveform-qa.config.ts`. This entry point does not mount or activate
the production router, qualify Linux, or establish public host acceptance.

Owned MiniSEED indexing requires `waveform_request` and the exact owned `physical.geometry.stationxml_asset_id`. `0004_waveform_artifacts` records both source roles and immutable result members. Structural indexing is not physical QC. The fixed worker validates original/index/request identities, final resources, complete export and release before transactional publication. Unknown or uncertain stage bytes are retained for recovery; only verified committed successful stages are removed. Startup independently audits inventory, quota and dependencies. Project deletion includes the validated waveform artifacts and sources.

The bilingual `WaveformProjectWorkbench` uses existing workbench/shell styles and the same protected session/CSRF client. It supports explicit requests, indexed datasets, job history/cancellation, exact scientific results, unit-bearing traces/PSD, verified ZIP export/reopen and source/QC/edge/pick provenance. It does not tune with catalogue labels, invent timing uncertainty or assign P/S. Router integration must preserve other positive modality guards. Working reports are written only under an explicitly selected external root, never `data/derived/waveform`; compact golden identities in tests are not raw fixture mirrors or field acceptance.
