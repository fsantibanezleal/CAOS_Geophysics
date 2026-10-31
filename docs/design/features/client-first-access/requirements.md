# Public client computation and local database access

Date: 2026-10-03
Status: implemented locally; local adversarial gates are recorded in validation.md; actual-host admission and full product acceptance remain open.
Authority: explicit owner decisions on 2026-10-03, followed by "implement all, validate all and deploy". This changes account administration and operating prerequisites, not full scientific or multi-project scope.

| ID | SHALL statement | gate |
|---|---|---|
| CFA-001 | THE default runtime SHALL start with local SQLite database accounts without SMTP configuration and disclose its non-secret access profile. | `tests/adversarial/test_client_first_access_adversarial.py::test_adversarial_client_first_access_contract` |
| CFA-002 | THE local profile SHALL omit public registration, verification and email reset routes while retaining library-managed active-account login/logout, database sessions and CSRF. | `tests/adversarial/test_client_first_access_adversarial.py::test_adversarial_client_first_access_contract` |
| CFA-003 | WHEN an operator provisions an account, THE tool SHALL use library password hashing, retain the exact validated identifier, forbid implicit replacement and never expose a password/hash in output. | `tests/adversarial/test_client_first_access_adversarial.py::test_adversarial_client_first_access_contract` |
| CFA-004 | WHEN an operator explicitly rotates a password, THE tool SHALL revoke that account's sessions and retain its projects and other accounts. | `tests/adversarial/test_client_first_access_adversarial.py::test_adversarial_client_first_access_contract` |
| CFA-005 | THE platform SHALL support multiple independent accounts with multiple projects each and enforce server-side ownership on project, upload and computation APIs. | `tests/adversarial/test_client_first_access_adversarial.py::test_adversarial_client_first_access_contract` |
| CFA-006 | THE frontend SHALL leave public research and supported browser computation accessible without login and offer only local login for protected server operations in the local profile. | `tests/adversarial/test_client_first_access_adversarial.py::test_adversarial_client_first_access_contract` |
| CFA-007 | THE source and browser build SHALL contain no supplied owner password or private credential file, and account provisioning SHALL consume an operator-controlled private file or interactive secret input rather than a command-line password. | `tests/adversarial/test_client_first_access_adversarial.py::test_adversarial_client_first_access_contract` |
| CFA-008 | WHEN a local-profile project is deleted, THE response SHALL identify off-host integration as `not_configured` without claiming external erasure, and SHALL retain the existing refusal to delete a project with recorded local backup custody. | `tests/adversarial/test_client_first_access_adversarial.py::test_adversarial_client_first_access_contract` |
