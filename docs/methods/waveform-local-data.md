# M08 local user-data and export integration

This guide describes the ordinary implemented interfaces, not permission to decode hostile native files in-process. Read the [science chapter](waveform-processing.md) and [exact inputs](../design/features/m08-waveform-user-data/contracts.md). The full workflow includes a contained child; its controller is not yet implemented. No scientific threshold or selection is changed by export.

## 1. Supply actual instrument data

Supply exact immutable MiniSEED2 integer-record bytes, unchanged StationXML and every native request field. Request schema is `caos.local-waveform-request.v1`; copy the contract's full schema, not a partial JSON example with hidden defaults. Its channels identify one station's exact network/station/location/channel and native conditioning/analysis intervals. Include separately supported rights declarations, acquisition identity, processing settings, and nullable ADC rails. Empty location is literal empty string; only the explicit catalogue adapter maps provider `--`.

Waveform cap16MiB, XML2MiB, request JSON64KiB. Counts, record/sample bounds, complete response epoch, sample rate, stage chain, units and analysis coverage are checked independently. A user-selected rights enum is not source authentication. Do not upload/commit raw data or derived arrays without per-object publication rights. Software and waveform licences are different.

`waveform_m08_files.open_input(absolute_path, cap)` holds regular-file and ancestor identities, refuses links/reparse/unsafe paths and reads once. `InputHandle.read_bytes()` records consumed-byte SHA256. These are cooperative private-file safeguards, not a hostile same-user sandbox. The consumer must retain handles throughout its transaction and must not re-open source paths for processing. No directory traversal, archive or network fetch exists.

## 2. Ordinary science boundary

`waveform_m08_child.calculate_bytes(mseed_bytes, stationxml_bytes, request_json_bytes)` invokes the real ordinary calculation and seal; request raw byte/hash identity is attached separately from canonical scientific configuration identity. Direct execution of the child file refuses: only a future reviewed supervisor may run it as a contained native worker. Unit tests use authored fixtures through this callable, not the private Ridgecrest native decode.

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

## 5. CLI contract and remaining integration

Python CLI requires explicit `--mseed`, `--stationxml`, `--request`, `--out`, `--python` absolute paths; optional `--evaluate-with` is converted bounded reference JSON only. PowerShell wrapper takes explicit `-PythonPath`; shell wrapper's first argument is explicit Python path. Wrappers forward literal argv and never install dependencies. Paths cannot be URLs, globs, devices, ADS, UNC, links, aliases or an existing output target.

Current actual CLI returns exit4 / `engine_unavailable` / `supervisor_unavailable` **before source/reference reads, staging, native computation or output creation**. This is the tested unavailable path, not a complete positive CLI vertical. No unsafe-direct flag, injectable provider, environment authority toggle or in-process fallback exists. Pure ordinary file/export success does not close the controller gate.

Future positive sequence is fixed: private-parent/closure/capacity verification; exact original reads; at-creation contained suspended child; monitored accounting; seal without labels; drain/exit/final counters; independent calculation verification; separate reference open/evaluation; validated export; post-parent-exit eligibility receipt. Reject paths3, QC2, computed0, failed5, resource6, timeout124 and cancelled130 remain distinct. Until actual controller/closure/context review and tests, only unavailable and safe rejection CLI paths are executable here.

## 6. Evidence boundaries

Authored analytic and direct numerical controls, held-out counts-comparator replay, unchanged-original format diagnostics, ordinary export/file tests and native platform controls are different evidence classes. The held-out display subset is already inspected and its weak agreement remains negative; no new learned-method inference occurred. Original physical processing and native lifecycle/resource controls remain NOT_RUN. Local directory/ABI binding tests are not Job Object or cgroup capability evidence. Whole-method/API/UI/host integration remains open.
