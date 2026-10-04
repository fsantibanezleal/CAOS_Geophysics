# Access and execution design

Date: 2026-10-03
Status: owner-approved operating boundary; implementation and gates pending.
Issue: [150](https://github.com/fsantibanezleal/CAOS_Geophysics/issues/150).

## Scope

The complete M01-M13 scientific system, case matrix, documentation and multi-account/multi-project data model are unchanged. The owner will initially test small projects; this is not a singleton-account or singleton-project edition. The operational amendment removes SMTP, external email flows and off-host backups from this stage. It does not mark any unfinished scientific, interface or resource test passed.

## Public versus protected

Public: six science pages, catalogue and rights-cleared studies/artifacts, visual controls, exports of public/local results, and validated browser calculations. Compatible files can be opened locally without sending their contents to the server. The web tool reports a browser failure; it never silently submits a VPS job. ONNX Runtime Web is for exported neural inference, with supported WASM/WebGPU execution and parity checks, not a replacement for arbitrary Python solvers.

Protected: server project creation/persistence, uploaded originals, private derivatives and server job submission/results. Existing owner foreign keys, API dependencies and transactional project/job schema remain. An explicit server upload or run requires a local account. Server admission still bounds actual CPU, memory, scratch and wall time. A visitor's local computation is not server scientific consumption; normal static asset traffic is separate.

## Internal accounts

Reuse the existing SQLite `user` and `access_tokens` tables and FastAPI Users 15.0.5, CookieTransport and DatabaseStrategy. Do not add a second account database or custom session/password protocol. Default `GEOPHYSICS_AUTH_MODE=local`; an explicit `email` profile retains historical library email-flow regression coverage but is not deployed or required. Missing SMTP configuration cannot prevent local startup. Invalid profiles fail clearly rather than downgrade authentication.

Local accounts are provisioned by an operator, not a public HTTP route. Use the library PasswordHelper (Argon2), the existing migrated database and typed user schema. Local minimum password length is eight characters to support the owner-specified test credential; the historical email profile retains its twelve-character rule. This is not a production credential-strength assertion. No owner identifier/password is hard-coded in public source, examples, fixtures or browser assets. The exact supplied credential lives only in the private management vault. `is_verified` remains false for operator-provisioned local accounts: no claim of mailbox verification. Local login/current-user dependencies require active authentication but not email verification; the explicit email profile still requires verification.

The operator command reads a private JSON file with `username` and `password`, or prompts without echo. Default creation refuses to overwrite an existing account. Explicit password rotation changes only the hash and revokes that account's stored sessions in the same transaction; it retains account identity, flags, project ownership and every other account. Refuse inactive-account reuse rather than silently activating it. Output includes only a created/unchanged/rotated verdict and non-secret account ID; validation failures must never print a Pydantic representation containing a password or file contents. No automatic bootstrap on every API startup.

`GET /api/auth/config` returns only `mode`, `registration_enabled` and `mail_flows_enabled`; no username, hash or SMTP settings. The frontend discovers this contract and shows login only for the local profile. HttpOnly/Secure/SameSite cookies, same-origin CSRF, server ownership and logout are retained. Administrative signup, mail and off-host backup controls are not needed to test full scientific capabilities.

## Deployment and retention

Exactly one ML VPS origin: the existing canonical hostname. Retain current plus two rollback releases, never delete shared-host data indiscriminately. Scientific artifacts are produced and validated locally; deployment publishes them without training or recalculating benchmarks. No off-host backup destination, SMTP sender or arbitrary whole-host 30% free-space threshold is a prerequisite for this owner-tested stage. Measure enough real capacity for the release/rollback set, existing project bytes and configured active-job resources. Existing historical tooling/evidence is preserved, not relabelled as current production acceptance.

## Source verification

- [FastAPI Users password hashing](https://fastapi-users.github.io/fastapi-users/latest/configuration/password-hash/): library Argon2/default PasswordHelper, automatic upgrades.
- [FastAPI Users auth router](https://fastapi-users.github.io/fastapi-users/latest/configuration/routers/auth/): explicit optional verification requirement.
- [ONNX Runtime Web](https://onnxruntime.ai/docs/tutorials/web/): client inference and execution-provider support; no general Python solver transpilation claim.

These primary sources were checked on 2026-10-03. Source claims do not replace the pinned-runtime and real API/browser tests named in requirements.
