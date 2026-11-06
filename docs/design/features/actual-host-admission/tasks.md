# Host admission tasks

- [x] Read approved SDD, inspect actual host capacity/systemd/resource semantics, define executable gates before code.
- [x] Implement strict opt-in distribution/concurrency/real-crash tests and receipt.
- [x] Implement/review server-only restricted runner and guide.
- [x] Verify local collection/lint/guide and opt-out behavior without asserting host measurement.
- [x] Persist scoped code and immutable runtime revision, run actual host controls, retain failures and fix the harness-only rate-budget cause without changing production rates.
- [x] Review actual receipts, commit/push evidence and draft PR #101 to develop. No production activation or whole-product acceptance.
- [x] Run the current-source isolated ML VPS admission suite for M05/M06: 20 nominal scored jobs per method, upper/malformed controls, concurrent authenticated reads, cancellation/timeout/memory/scratch limits, parent crash and retry recovery. Preserve raw receipts, exact unit properties, source/dependency identities and the post-run cleanup record in `docs/validation/actual-host-admission-mt-2026-11-06.md` and its private external archive.
- [x] Run the isolated ML VPS M02 uploaded ordinary-L2 child control with the registered CPython gravity runtime, applied systemd resource properties, preserved raw receipt, independent Choclo replay and explicit synthetic-data boundary. The authenticated control and 165-test Linux M02 suite passed; see `docs/validation/actual-host-admission-m02-2026-11-06.md`. This is not full M02 or release acceptance.
- [ ] Complete release admission: inventory the exact candidate bundle, current plus two rollback releases and existing project bytes; run actual-host capacity and server-job admission for every method class the product enables; complete ownership/security, public HTTPS/browser, release hash and rollback gates. M05/M06 success is bounded to these two methods and does not pass R-007/R-017.
- [x] Integrate reviewed runtime/canonical source reconciliation after PR #97/#100/#106; fresh local API regressions and actual cl061 rejection pass. Keep public MT admission closed until all gates pass.
