# Local-account access verification contract

This feature changes the account client/dialog only. Tests distinguish typed
protocol behavior, intercepted rendering and real local HTTP integration. None
establishes operating-host admission, deployment or complete-product acceptance.

## Gates

- LA-01..03: strict three-key profile parser, active local accounts with unchanged
  is_verified:false, local mail actions blocked before requests, explicit email
  compatibility only. Profile discovery errors never silently enable actions.
- LA-04..07: anonymous six-route course/replay and browser computation, direct
  private-project refusal, plural project selection, account replacement,
  password clearing, expiry/close races, keyboard/focus and phone containment.
- LA-08: exact deletion-state union and unknown-state rejection; EN/ES labels
  distinguish not_configured from pending_reconciliation without erasure claims.
- LA-09: actual HTTP factory/migrations/provisioner and two randomized accounts
  in a new private DB per control; actual cookies, CSRF, cross-account404, project
  creation/deletion, logout401, guest project/upload/job401 and absent mail404.
  Eight EN/ES × light/dark × desktop/phone controls also verify unchanged auth
  rate admission (eleventh attempt429 and positive Retry-After).

Inspect all language/theme/device screenshots and verify dialog containment.
Intercepted responses prove only frontend behavior; they are not real server
ownership. Real loopback uses cookie_secure:false solely in test Settings; it
does not prove deployed HTTPS. No mail sender or heavy worker runs in these tests.

## Reproduction using an existing trusted runtime

From frontend/, use installed lock-matched dependencies; do not install/upgrade
packages just to run these gates. Use fresh private output paths for every run.

```powershell
npm test -- --reporter=default --reporter=junit --outputFile.junit=$PrivateUnitXml
npm run build
npm run preview -- --port $LocalReviewPort --strictPort
$env:GEOPHYSICS_QA_URL = $LocalReviewOrigin
$env:GEOPHYSICS_QA_EVIDENCE = $PrivateBrowserEvidence
$env:PLAYWRIGHT_JUNIT_OUTPUT_FILE = $PrivateBrowserXml
npx --no-install playwright test e2e/local-access.spec.ts --workers=1 --reporter=line,junit --output=$PrivateBrowserOutput
npx --no-install tsc --noEmit --strict --skipLibCheck --target ES2022 --module ESNext --moduleResolution bundler --types node e2e/local-access.spec.ts e2e/local-real-access.spec.ts
```

For the opt-in actual HTTP test, extract committed app/ from the exact approved
backend revision into a NEW ignored source directory within the trusted backend
checkout. The test verifies every extracted source file against that revision's
Git blob. Point to an existing interpreter, byte-checked frontend build and the
separate operator DB for read-only before/after digest checks. Never point the QA
root at an existing database. The helper enforces a new named raw/ child and
receives generated test credentials over a private stdin pipe, not argv/files.

```powershell
$env:GEOPHYSICS_REVIEW_CHECKOUT = $TrustedImmutableBackendCopy
$env:GEOPHYSICS_REVIEW_BACKEND_REVISION = $ExactBackendRevision
$env:GEOPHYSICS_REVIEW_PYTHON = $ExistingApiPython
$env:GEOPHYSICS_REVIEW_BUILD = $ByteCheckedFrontendBuild
$env:GEOPHYSICS_OPERATOR_DB_GUARD = $ExistingOperatorDb
$env:GEOPHYSICS_QA_EVIDENCE = $NewPrivateRealEvidence
$env:PLAYWRIGHT_JUNIT_OUTPUT_FILE = $NewPrivateRealXml
npx --no-install playwright test e2e/local-real-access.spec.ts --workers=1 --reporter=line,junit --output=$NewPrivateRealOutput
```

Preserve historical failures and private storage. Exact-ID cleanup touches only
projects created by that control; no database or operator-owned data is deleted.
After each control, verify source/build and existing DB digests are unchanged.
Never publish credentials, cookie values, device paths or private DB contents.

## Protected regression boundaries

Run artifact, phase-asset, content/template, CI-budget and single-origin guards.
Scope-review that scientific source/renderers, shell/palette, canonical data,
backend, dependency locks and installed packages have no delta. The requirement
ledger must retain its actual failures/unresolved items. A green local gate does
not close scientific verticals, host durability/security or release admission.
