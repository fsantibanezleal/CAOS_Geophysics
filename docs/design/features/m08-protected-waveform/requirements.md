# Protected waveform service requirements

Status (2026-10-08): protected Windows implementation committed; Linux fixed-lane
implementation authorized and qualification open. See the current
[Linux amendment](linux-fixed-lane.md). Named gates below remain requirements,
not claims that every native/host gate passed. Historical local-only exclusions
do not limit the currently approved user/API/UI workflow.

The lossless record transport requirements R-M08L-01..04 and their named gates
are in [record-ledger.md](record-ledger.md); all original scientific and native
resource predicates below remain unchanged.

R-M08S-01 WHEN a user submits an owned MiniSEED asset and its declared StationXML companion, THE service SHALL index only the exact unchanged original pair with strict source rights, sample/record/XML caps, NSLC and explicit request; it SHALL not decode or compute in an API request. Gate: `tests/api/test_waveform_service.py::test_owned_pair_and_request_index`.

R-M08S-02 IF identity, companion, rights, schema, request or source bytes differ, THEN THE service SHALL reject with safe typed errors and no derived publication. Gate: `tests/api/test_waveform_service.py::test_pair_rejections`.

R-M08S-03 WHEN an admitted job runs, THE worker SHALL invoke the same M08 scientific pipeline under the concrete selected platform supervisor, revalidate both raw parents and request, preserve failed scientific/resource outcomes and reject unavailable containment rather than run an uncontained fallback. Gate: `tests/api/test_waveform_service.py::test_worker_dispatch_and_closed_context`.

R-M08S-04 WHEN a scientific export and final native release are validated, THE worker SHALL publish immutable bounded individual artifacts and one typed result with exact source/request/calculation/member identities; uncertain commit SHALL preserve the exact stage and installed bytes for operator review. Gate: `tests/api/test_waveform_service.py::test_publication_and_roundtrip`.

R-M08S-05 THE service SHALL charge every artifact once, reserve full bounded scratch, audit exact inventory on restart, reject unknown entries, block active-job deletion and retain all derived identities in deletion receipts. Gate: `tests/api/test_waveform_service.py::test_inventory_quota_delete`.

R-M08S-06 THE schema SHALL use explicit waveform source-dependency and result-artifact tables at revision0004_waveform_artifacts; existing0003 backup adapters SHALL remain unsupported for this new revision. Gate: `tests/api/test_waveform_service.py::test_migration_and_unknown_revision`.

R-M08S-07 THE protected waveform UI SHALL bind the selected original pair, explicit scientific parameters, eligibility, job/cancellation and exact result/download identities; missing references SHALL remain not_evaluable and no phase or field truth SHALL be fabricated. Gate: `frontend/src/test/waveform-project.test.tsx`.

R-M08S-08 THE ordinary full workflow SHALL compare real same-input processing arrays, seals and streaming export/reopen at nominal one/three and upper three-channel sizes without changing scientific thresholds. Gate: `tests/data/test_waveform_full_workflow.py`.

R-M08S-09 THE protected UI SHALL provide grouped, source-bound controls for exact UTC windows/NSLC, native response units, four-corner prefilter, offline bandpass, STA/LTA and Welch segment length. Empty fields SHALL remain unset, not method defaults; edits SHALL produce the same explicit scientific request as advanced JSON and create a new immutable dataset, never mutate a submitted request. Gate: `frontend/src/test/waveform-request.test.tsx` (roundtrip, empty/malformed fields, unchanged source and rails, no numeric coercion).

R-M08S-10 THE UI SHALL retain advanced JSON import/export, original asset/companion identity, source provenance and explicit rights. Changing the original selection SHALL invalidate request-source binding until explicitly reviewed again. It SHALL not invent NSLC locations, provider inputs, ADC rails, units, picks or scientific defaults. Gate: `frontend/src/test/waveform-request.test.tsx` and `frontend/e2e/waveform-workbench.spec.ts` (real owned indexing and source binding).

R-M08S-11 WHEN a ZIP has been verified against the successful job, THE UI SHALL plot actual response amplitude and principal phase against its measured response-frequency array, alongside counts, native physical signal, filtered signal, PSD and characteristic arrays. Amplitude SHALL be hypot(real, imaginary), phase atan2(imaginary, real) in radians; these display transforms SHALL not change exported arrays, scientific hashes or acceptance flags. Gates: `frontend/src/test/waveform-request.test.tsx` (exact response transforms/units) and `frontend/e2e/waveform-workbench.spec.ts` (real arrays rendered).

R-M08S-12 THE UI SHALL show exact conditioning/analysis UTC windows, actual edge-valid mask and time taper, explicitly acausal filtering, native channel units and unlabelled trigger intervals. Frequency plots SHALL not share a time cursor. The owned component SHALL preserve optional methodNavigation inside its one instrument aside, existing shell controls/styles and bilingual phone/desktop chart usability. Gates: `frontend/src/test/waveform-project.test.tsx` and `frontend/e2e/waveform-workbench.spec.ts` (EN/ES, both themes, mobile controls, real response plots and usable chart width).

R-M08S-13 WHERE protected Linux execution is installed, THE service SHALL use only a fixed installation-owned waveform helper and canonical owned job UUID; an irrevocably nonroot reader SHALL bind the current job/project/dataset/two-original/source relations, and root SHALL never open worker-controlled SQLite/WAL or original paths. Gates: `tests/data/test_waveform_owned_reader.py` and `tests/api/test_waveform_linux_installation.py` (closed authority, changed/foreign relations, nonroot reads, fixed command and snapshot binding).

R-M08S-14 BEFORE native processing, THE installed helper SHALL verify the complete immutable interpreted/source/native import namespace and fixed no-site startup; additions, changed names/bytes/owners/modes/identities or escaped links SHALL refuse rather than adopt a regenerated digest. Gate: `tests/data/test_waveform_import_closure.py` (inventory additions, links, mutation and actual selected-runtime qualification).

R-M08S-15 WHEN an installed job terminates, THE helper and worker SHALL preserve bounded external descriptor-held custody and source-bound full receipts, publish only after native extinction and existing scientific/member checks, and remove only exact known successful files after transaction commit; unproved cancel, caller loss, readback failure or changed stage SHALL preserve debt. Gates: `tests/api/test_waveform_linux_installation.py` and `tests/api/test_waveform_native_workflow.py` (actual nonroot protected queue, CANCEL/EOF, publication/ZIP/restart/deletion).
