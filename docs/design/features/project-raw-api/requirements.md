# Authenticated project and raw-asset API requirements

Date: 2026-09-27. Parent: `docs/design/SDD.md`, especially R-002, R-003 and section 8. This unit owns accounts, projects and immutable uploaded originals. It does not create a validated observation dataset, processing run or solver job.

R-API-01 THE API SHALL use library-managed password hashing, registration, email verification, password reset and revocable database-backed cookie sessions, and SHALL require a verified account for project data. Gate: `tests/api/test_auth.py::test_register_verify_reset_login_logout`.

R-API-02 IF an unsafe browser request lacks a matching CSRF token or same-origin evidence, THEN THE API SHALL reject it; IF an authentication or upload client exceeds its rate limit, THEN THE API SHALL return a retryable 429. Gate: `tests/api/test_security.py::test_csrf_origin_and_rate_limits`.

R-API-03 WHEN a verified account creates, lists, reads or updates a project, THE API SHALL expose only that account's projects and use an indistinguishable 404 for another owner's IDs. Gate: `tests/api/test_projects.py::test_owner_scoped_crud`.

R-API-04 WHEN an owner uploads an original, THE API SHALL stream it to private staging, calculate SHA-256, store the exact bytes under an opaque immutable key, and record a source and receipt with owner, rights, size and hash. Gate: `tests/api/test_assets.py::test_raw_immutable_and_receipt`.

R-API-05 IF an upload is empty, over 200 MiB, an archive, an unsupported format, or its declared MIME disagrees with detected content, THEN THE API SHALL reject it without storing bytes or charging quota. Gate: `tests/api/test_assets.py::test_rejected_bytes_and_mime_leave_no_asset`.

R-API-06 IF physical units, coordinate frame, datum, vertical sign, epoch, component orientation or format-specific geometry are missing or invalid, THEN THE API SHALL reject the upload with field-specific reasons and SHALL never infer them. Gate: `tests/api/test_metadata.py::test_missing_physical_metadata_rejection`.

R-API-07 WHILE an account has stored raw bytes, WHEN it uploads more data, THE API SHALL enforce a transactional 1 GiB per-account quota and SHALL keep concurrent uploads from oversubscribing it. Gate: `tests/api/test_assets.py::test_quota_and_parallel_uploads`.

R-API-08 WHEN an owner downloads an asset or exports a project, THE API SHALL serve only owned original bytes and a ZIP manifest with SHA-256, source, rights and physical metadata so an independent reader can verify every member. Gate: `tests/api/test_export_delete.py::test_export_manifest_and_owned_bytes`.

R-API-09 WHEN an owner permanently deletes a project, THE API SHALL remove its DB rows, raw bytes and any API-managed project backup, retain a deletion receipt for backup reconciliation, and make every old URL inaccessible. Gate: `tests/api/test_export_delete.py::test_delete_erases_project_and_bytes`.

R-API-10 THE API SHALL start only on the committed SQLite migration head, and SHALL expose no job submission route in this unit. Gate: `tests/api/test_migrations.py::test_upgrade_and_schema_guard` and `tests/api/test_migrations.py::test_no_job_route`.

R-API-11 IF a file or DB transition is interrupted, THEN THE API SHALL reconcile unreferenced private bytes and missing records without exposing partial assets as successful uploads. Gate: `tests/api/test_assets.py::test_reconcile_orphaned_bytes`.

The parent SDD's catalogue, dataset processing, method eligibility, jobs, numerical results, worker, frontend and cutover gates remain separate units. A complete raw-upload receipt means byte and metadata-envelope integrity only; it is not a modelling QC verdict.
