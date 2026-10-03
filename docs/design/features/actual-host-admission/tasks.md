# Host admission tasks

- [x] Read approved SDD, inspect actual host capacity/systemd/resource semantics, define executable gates before code.
- [x] Implement strict opt-in distribution/concurrency/real-crash tests and receipt.
- [x] Implement/review server-only restricted runner and guide.
- [x] Verify local collection/lint/guide and opt-out behavior without asserting host measurement.
- [x] Persist scoped code and immutable runtime revision, run actual host controls, retain failures and fix the harness-only rate-budget cause without changing production rates.
- [x] Review actual receipts, commit/push evidence and draft PR #101 to develop. No production activation or whole-product acceptance.
- [ ] Pass complete admission: corrected 40-job sample failed unchanged 30% free-disk headroom (measured 29.42%). No exemption or passing receipt is authorized.
- [ ] Integrate reviewed runtime/canonical source reconciliation after dependency PRs; keep public MT admission closed until all gates pass.
