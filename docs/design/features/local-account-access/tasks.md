# Local-account frontend tasks and gates

Date: 2026-10-03. Branch: task/geophysics-local-account-access. Explicit user
implementation authority, with the approved local/public decision fixed.

- [x] Inspect actual shared shell, old lifecycle SDD and existing API/account/
  private-workbench/public-route seams. Persist requirements/design BEFORE code.
- [ ] LA-01..03: test-first strict config, profile-aware active-account probe,
  disabled local mail calls, explicit historical email compatibility.
- [ ] LA-02,03,05: implement login-only local dialog, non-secret operator guidance,
  truthful owner label, cancellation/expiry/logout and password clearing.
- [ ] LA-04,06: prove anonymous course/replay/browser controls and direct-project
  denial, two-project selection/account switching without new renderers.
- [ ] LA-01..07: full Vitest, TypeScript/build and local eight-way Playwright UI
  matrix; inspect screenshots, keyboard/focus/overflow and error/race states.
- [ ] Run content/template/base/artifact guards and scope/hash self-review; retain
  every negative and distinguish intercepted UI tests from actual API/VPS gates.
- [ ] Commit/push scoped paths, report exact branch/head/evidence to MAIN for
  integration. No backend/auth decisions, package installs, main/merge/deploy.

No test is currently claimed PASS by this pre-code packet. Actual execution
receipts and dependency gaps will be additive, not rewriting historical SDDs.
