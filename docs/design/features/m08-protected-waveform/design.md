# Protected M08 waveform vertical

## Boundary and scientific invariants

The method is seismic.waveform-qc-classical/v1: immutable integer counts plus exact StationXML, raw QC, native response deconvolution, offline acausal SOS bandpass, unit-bearing Welch PSD, unlabelled classical STA/LTA intervals and separately sealed optional evaluation. Source samples, response stages, declared units, UTC windows and thresholds never change to obtain a pass. The ordinary local waveform contract/algorithms remain authoritative. Computed is not accepted field geology, authenticated provider data, calibrated timing or a P/S classifier. All scientific acceptance flags remain false. Existing held-out replay and original Ridgecrest failure seals are unchanged.

Scope includes protected source-pair indexing, queue/worker dispatch, durable multi-artifact result, downloads/export, restart/delete/quota, waveform-specific UI and ordinary offline workflow. Auth implementation, other method dispatch, profile implementation, shell mounting and production activation are not part of this feature.

## Dataset and request contract

POST /api/projects/{project}/datasets adds optional waveform_request only for miniseed. It is the exact caos.local-waveform-request.v1 native object; no defaults or coercion. Original request bytes remain a distinct domain in the local CLI. The service binds the validated scientific canonical ASCII request and its hash; it never pretends a JSON framework reserialization is the original transport byte hash. Existing asset_id-only EDI/gravity requests remain unchanged. Request-bearing indexing checks structure without native decoder/inventory imports. Request hash is part of the named parser version so distinct explicit windows/configurations may coexist without overwriting an earlier dataset.

The companion is the existing raw asset physical.geometry.stationxml_asset_id, resolved under the same owner/project transaction. Both assets/source records must have private-storage attestation, non-forbidden rights and measured original sizes/hashes. Source pair versions/IDs, observed NSLC/record/sample counts, raw identities, explicit request and hash form a strict geophysics.waveform-dataset/v1 envelope. It is a structural source index, not physical QC clearance. Native decode/full response QC happens in the worker only.

POST jobs accepts exact waveform parameters {scientific_request_sha256}; all processing parameters already belong to the immutable indexed request. No URL/path/native context from the browser. Method eligibility requires exact modality and request binding; safety eligibility also requires an installed reviewed per-run native context. Missing context is explicit unavailable, not a simulated successful job. Existing one active job/account and global queue/quota apply.

## Storage and revision

0004_waveform_artifacts adds waveform_dataset_sources (dataset_id, role, asset_id, source_id, raw_sha256, raw_bytes, source_version) with roles miniseed/stationxml, unique dataset/role and foreign keys; waveform_result_artifacts (job_id, name, storage_key, byte_count, sha256) with unique job/name and key. Existing tables and0003 rows are unchanged. Foreign keys plus application validation prove owner/project and relation identities. Revision is explicit: no recovery wildcard/future format inference. Production backup adapter work is deferred.

Dataset/result JSON retains existing generated keys. Scientific export members live only at derived/{owner}/{project}/waveforms/{job}/{generated_name}; names are the bounded local export grammar, never user filenames/NSLC/path fragments. The scientific export's <=33554432 bytes, <=55 entries, <=2MiB metadata, <=65536-byte streamed chunks are unchanged. A small result envelope records exact job/dataset/request/source identities, scientific status, calculation hash, bounded metadata and exact member inventory. Native private diagnostics/context are excluded from downloads; native final/release receipt is represented by digest and typed measured resources with authority false. Committed memory/cgroup charge is never peak RSS.

## Execution/publication sequence

1. Claim and revalidate row, request, exact raw pair/source records and measured held inputs; create only a new exact job stage.
2. Invoke the fixed waveform platform supervisor and explicit reviewed runtime/context. Controller plus child and exited descendants are in lifetime accounting. B60/S57 CPU, sample-gap stop, drain/final samples and release acknowledgment remain unchanged; unavailable native context fails closed. No psutil lifetime substitution.
3. Calculate/seal without catalogue access. Verify complete local export, optional post-seal evaluation, unchanged source identities and native final/release. Scientific QC-only is retained visibly; malformed/crash/cancel/resource failure never becomes successful empty science.
4. Reserve scratch/account bytes, fsync verified members, install one new exclusive immutable artifact directory and result JSON; write exact artifact rows plus terminal job result in one SQLite transaction. Cancellation is checked before installation and under terminal transaction. Any uncertain outcome preserves stage/installed bytes and fails restart inventory until operator review. Never erase potentially committed bytes.
5. Exact startup inventory checks every row and file/hash/schema and raw dependency. Deletion validates the exact inventory and no active jobs, preserves member identities in durable deletion receipt, removes dependency/artifact rows before parent rows, then purges only the proven manifest. Unknown files/links fail closed. Old snapshots are not authorized to restore0004.

## Protected export and frontend

Result GET returns the typed envelope; member GET authorizes owner/project/job and verifies size/hash before streaming. ZIP is constructed from the verified bounded member list only, with no originals or private diagnostics; independent local reopener validates extracted science. Project raw export preserves originals; waveform result exports are explicit separate reproducible bundles, not silently omitted science dressed as a complete raw ZIP.

WaveformProjectWorkbench uses the existing authenticated ApiClient/CSRF, uploads through existing owner raw routes, selects the exact companion and supplies explicit scientific request, submits/polls/cancels jobs, displays QC/response/filter/PSD/candidates and source/request/seal provenance, and downloads the exact result bundle. It never invents default catalogue picks. Waveform client/contracts/components/tests are additive; a small shell mount diff is delivered separately.

## Proof and nonclaims

Test-first pure/real API controls use temporary migrated SQLite and fresh private fixture directories, original bytes and native engine comparisons. Ordinary science tests can use a separate read-only scientific interpreter; API imports never install or decode. Tests of authored supervisor doubles are dispatch/validation proof only. Actual Windows/Linux safety, cold nominal/upper/original controls and selected runtime/context are separate measured gates. Missing evidence remains NOT_RUN/FAIL, not xfail/skip-as-PASS, host admission or public activation. No altered thresholds, resampling, alternate channels, provider rewriting or imaginary runtime provider closes a gate.
