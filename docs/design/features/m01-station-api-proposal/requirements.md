# M01 station upload/correction API proposal requirements

Status: planned, awaiting main ownership/approval after current units and MT runtime converge. No backend implementation or API activation is authorized here. Prospective test names below are specifications, not claims that tests exist or pass. API approval defaults false until actual host admission.

R-MU01 WHEN an authenticated owner uploads exact gravity-stations-1 JSON, THE API SHALL preserve private immutable raw bytes and transport SHA-256 plus a separately retained scientific source identity; reject unauthorized/cross-owner access, unsafe paths, unknown rights and resource overruns without leaking content. Prospective gate: tests/api/test_gravity_station_json.py::test_private_exact_bytes_and_ownership.

R-MU02 IF schema, physical units/sign/component/datum, finite numeric error/geometry, instrument status or ordered correction lineage is missing/ambiguous, THEN admission SHALL reject with typed field paths and no guessed metadata, parser coercion or computed child. Prospective gate: tests/api/test_gravity_station_json.py::test_strict_physics_and_no_csv_relabelling.

R-MU03 WHEN an approved correction job executes, THE fixed unprivileged child adapter SHALL call the exact pinned existing process_survey and persist a new versioned correction child linked to unchanged input dataset/raw/job hashes; flag-only CSV results SHALL remain a distinct method/contract. Prospective gate: tests/api/test_gravity_station_corrections.py::test_real_child_matches_local_correction_oracle.

R-MU04 WHEN any execution path checks eligibility, THE registry/submit/worker SHALL require both reviewed adapter compatibility and explicit actual-host approval, default false, with fail-closed pin/resource checks. Unknown ops variants SHALL require a named adapter review, never fallback execution. Prospective gate: tests/api/test_gravity_station_corrections.py::test_host_default_false_and_unknown_adapter.

R-MU05 THE job/child lifecycle SHALL retain private owner boundaries, quotas, exact error/conservative-bound typing, no double correction, cancellation/timeout/crash recovery and exclusive publication/re-import identities without corrupting the original or exposing partial children as successful. Prospective gate: tests/api/test_gravity_station_corrections.py::test_immutable_lineage_cancel_and_export.

R-MU06 BEFORE online approval, THE owner SHALL retain actual-host nominal/upper/malformed wall/RSS/scratch, responsiveness, timeout/cancel/crash, quota/concurrency and pinned local-child parity receipts against approved limits/headroom. Neither local passes nor this SDD SHALL imply release or full M01 acceptance. Prospective gate: tests/api/test_gravity_station_admission.py::test_actual_host_admission_receipt.
