# Public client computation and local database access

Date: 2026-10-03
Status: planned
Authority: explicit owner decisions on 2026-10-03, followed by "implement all, validate all and deploy". This changes account administration and operating prerequisites, not full scientific or multi-project scope.

R-001 THE default runtime SHALL start with local database accounts without SMTP configuration and disclose its non-secret access profile. Gate: tests/api/test_local_auth.py::test_default_environment_needs_no_smtp.

R-002 THE local profile SHALL omit public registration, verification and email reset routes while retaining library-managed active-account login/logout, database sessions and CSRF. Gate: tests/api/test_local_auth.py::test_local_routes_and_session_lifecycle.

R-003 WHEN an operator provisions an account, THE tool SHALL use library password hashing, retain the exact validated identifier, forbid implicit replacement and never expose a password/hash in output. Gate: tests/api/test_local_auth.py::test_operator_provisioning_and_explicit_rotation.

R-004 WHEN an operator explicitly rotates a password, THE tool SHALL revoke that account's sessions and retain its projects and other accounts. Gate: tests/api/test_local_auth.py::test_rotation_revokes_only_owner_sessions.

R-005 THE platform SHALL support multiple independent accounts with multiple projects each and enforce server-side ownership on project, upload and computation APIs. Gate: tests/api/test_local_auth.py::test_plural_accounts_projects_and_anonymous_boundary.

R-006 THE frontend SHALL leave public research and supported browser computation accessible without login and offer only local login for protected server operations in the local profile. Gate: frontend/e2e/local-access.spec.ts and frontend/src/test/local-access.test.ts.

R-007 THE source and browser build SHALL contain no supplied owner password or private credential file, and account provisioning SHALL consume an operator-controlled private file or interactive secret input rather than a command-line password. Gate: tests/api/test_local_auth.py::test_provisioning_cli_redacts_invalid_secret_input.

R-008 WHEN a local-profile project is deleted, THE response SHALL identify off-host integration as not_configured without claiming external erasure, and SHALL retain the existing refusal to delete a project with recorded local backup custody. Gate: tests/api/test_local_auth.py::test_local_deletion_profile_and_existing_backup_custody.
