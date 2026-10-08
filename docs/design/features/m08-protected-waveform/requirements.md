# Protected waveform service requirements

Status: planned

R-M08S-01 WHEN a user submits an owned MiniSEED asset and its declared StationXML companion, THE service SHALL index only the exact unchanged original pair with strict source rights, sample/record/XML caps, NSLC and explicit request; it SHALL not decode or compute in an API request. Gate: `tests/api/test_waveform_service.py::test_owned_pair_and_request_index`.

R-M08S-02 IF identity, companion, rights, schema, request or source bytes differ, THEN THE service SHALL reject with safe typed errors and no derived publication. Gate: `tests/api/test_waveform_service.py::test_pair_rejections`.

R-M08S-03 WHEN an admitted job runs, THE worker SHALL invoke the same M08 scientific pipeline under the concrete selected platform supervisor, revalidate both raw parents and request, preserve failed scientific/resource outcomes and reject unavailable containment rather than run an uncontained fallback. Gate: `tests/api/test_waveform_service.py::test_worker_dispatch_and_closed_context`.

R-M08S-04 WHEN a scientific export and final native release are validated, THE worker SHALL publish immutable bounded individual artifacts and one typed result with exact source/request/calculation/member identities; uncertain commit SHALL preserve the exact stage and installed bytes for operator review. Gate: `tests/api/test_waveform_service.py::test_publication_and_roundtrip`.

R-M08S-05 THE service SHALL charge every artifact once, reserve full bounded scratch, audit exact inventory on restart, reject unknown entries, block active-job deletion and retain all derived identities in deletion receipts. Gate: `tests/api/test_waveform_service.py::test_inventory_quota_delete`.

R-M08S-06 THE schema SHALL use explicit waveform source-dependency and result-artifact tables at revision0004_waveform_artifacts; existing0003 backup adapters SHALL remain unsupported for this new revision. Gate: `tests/api/test_waveform_service.py::test_migration_and_unknown_revision`.

R-M08S-07 THE protected waveform UI SHALL bind the selected original pair, explicit scientific parameters, eligibility, job/cancellation and exact result/download identities; missing references SHALL remain not_evaluable and no phase or field truth SHALL be fabricated. Gate: `frontend/src/test/waveform-project.test.tsx`.

R-M08S-08 THE ordinary full workflow SHALL compare real same-input processing arrays, seals and streaming export/reopen at nominal one/three and upper three-channel sizes without changing scientific thresholds. Gate: `tests/data/test_waveform_full_workflow.py`.
