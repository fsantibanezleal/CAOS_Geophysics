# Local-account frontend tasks and gates

Date: 2026-10-03. Technical gates for the fixed local/public operating decision.
The initial requirements/design were persisted at56f552d before source changes.

- [x] Inspect actual shared shell, old lifecycle SDD and existing API/account/
  private-workbench/public-route seams. Persist requirements/design BEFORE code.
- [x] LA-01..03: test-first strict config, profile-aware active-account probe,
  disabled local mail calls, explicit historical email compatibility.
- [x] LA-02,03,05: implement login-only local dialog, non-secret operator guidance,
  truthful owner label, cancellation/expiry/logout and password clearing.
- [x] LA-04,06: prove anonymous course/replay/browser controls and direct-project
  denial, two-project selection/account switching without new renderers.
- [x] LA-01..07: full Vitest, TypeScript/build and local eight-way Playwright UI
  matrix; inspect screenshots, keyboard/focus/overflow and error/race states.
- [x] LA-08: exact deletion-state union, unknown-state rejection and EN/ES views;
  retain legacy pending_reconciliation without inferring backup existence.
- [x] Run content/template/base/artifact guards and scope/hash self-review; retain
  every negative and distinguish intercepted UI tests from actual API/VPS gates.
- [ ] Separately validate the combined frontend/backend against real local API
  cookies, CSRF and cross-account ownership, then actual operating-host gates.

See [verification](validation.md) for actual red/green chronology and limits.
Intercepted browser responses are not real API, scientific or release acceptance.
