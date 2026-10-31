# Host admission tasks

- [x] Read approved SDD, inspect actual host capacity/systemd/resource semantics, define executable gates before code.
- [x] Implement strict opt-in distribution/concurrency/real-crash tests and receipt.
- [x] Implement/review server-only restricted runner and guide.
- [x] Verify local collection/lint/guide and opt-out behavior without asserting host measurement.
- [x] Persist scoped code and immutable runtime revision, run actual host controls, retain failures and fix the harness-only rate-budget cause without changing production rates.
- [x] Review actual receipts, commit/push evidence and draft PR #101 to develop. No production activation or whole-product acceptance.
- [ ] Pass current SDD admission: measure capacity for the candidate, current plus two rollback releases, existing project bytes, configured job scratch and worker memory; run nominal/upper/malformed jobs and cancellation/crash recovery. The historical 40-job 29.42% observation is retained as evidence but its superseded universal 30% threshold is not an acceptance criterion.
- [x] Integrate reviewed runtime/canonical source reconciliation after PR #97/#100/#106; fresh local API regressions and actual cl061 rejection pass. Keep public MT admission closed until all gates pass.
