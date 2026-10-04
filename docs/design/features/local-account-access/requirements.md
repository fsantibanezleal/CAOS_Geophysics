# Local-account frontend access requirements

Date: 2026-10-03. Authority: explicit user instruction to implement this frontend
unit under the approved public-client/local-account operating decision. No new
auth decision or backend/deploy authority is inferred. Parent issue:
[#150](https://github.com/fsantibanezleal/CAOS_Geophysics/issues/150).
Historical [lifecycle requirements](../api-frontend-lifecycle/requirements.md)
remain evidence of their original email profile; this local-profile contract
supersedes their default registration/mail requirement, not scientific gates.

LA-01 WHEN the account client discovers its profile, THE client SHALL GET the
same-origin /api/auth/config and parse exactly mode, registration_enabled and
mail_flows_enabled; local requires false/false, unknown/malformed/unavailable
profiles SHALL fail closed for server controls, never block public pages.
Gate: frontend/src/test/local-access.test.ts profile parsing/availability cases;
frontend/e2e/local-access.spec.ts unavailable-profile public boundary.

LA-02 WHILE mode is local, THE account panel SHALL show only login/logout and
operator-managed account guidance, with no registration/verification/forgot/reset
prompt or mail promise. Disabled client mail methods SHALL reject before CSRF or
unsafe requests. Gate: local-access.test.ts disabled-flow controls and
local-access.spec.ts EN/ES local login-only matrix.

LA-03 WHEN an active local account authenticates, THE client SHALL permit server
projects without falsely setting is_verified or claiming mailbox verification;
inactive/anonymous accounts SHALL receive no project/upload/server-run controls.
Gate: local-access.test.ts active/local/explicit-email compatibility controls;
local-access.spec.ts guest/direct-project denial and active unverified-local login.

LA-04 THE frontend SHALL preserve public access to all six course/replay routes
and existing validated browser computation, with no silent server fallback.
Gate: local-access.spec.ts anonymous six-route/client-control tests, existing
foundation-routes.test.ts and M13 browser parity unit tests. No scientific
renderer, shell token/palette, model, fixture or compute algorithm edits.

LA-05 IF login fails, profile discovery fails, logout succeeds or a session
expires, THEN THE panel SHALL show actionable EN/ES errors, clear owner data and
transient passwords, cancel stale account probes and preserve non-secret unsent
inputs where possible. Gate: local-access.spec.ts invalid-login/expiry/retry/race
tests and lifecycle-client.test.ts unchanged cookie/CSRF/error transport controls.

LA-06 THE panel SHALL support returned lists of multiple projects and multiple
separate accounts without single-user/single-project assumptions or credential
persistence. Gate: local-access.spec.ts two-project/account switching; no supplied
operator credential in code, bundle, public docs or tests. Backend ownership is
the separate tests/api/test_local_auth.py gate, not a browser-mock claim.

LA-07 THE unit SHALL preserve the shared shell, six-route manifest and existing
styles, and render usable labelled login/project states in EN/ES, light/dark and
desktop/phone. Gate: local-access.spec.ts eight-way matrix, Escape/focus/overflow
checks, screenshot inspection, full Vitest/TypeScript/build/content/base guards.

Scope: frontend/src/api/lifecycle.ts (typed account client),
frontend/src/components/ProjectDrawer.tsx (account/project panel), frontend tests
and this feature docs only. Backend auth/config/bootstrap, API tests and product
SDD are separate boundaries; scientific code and deployment are not modified.

LA-08 WHEN deletion returns external_backup_status:'not_configured' or the
legacy 'pending_reconciliation', THE client SHALL retain the exact wire value
and show EN/ES state-specific copy without claiming external backup existence
or erasure. Unknown states SHALL reject. Gate: local-access.test.ts union and
negative parser controls; local-access.spec.ts both rendered deletion states.
