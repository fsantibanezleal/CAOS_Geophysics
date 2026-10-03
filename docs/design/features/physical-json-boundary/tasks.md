# Local physical JSON boundary tasks and convergence

Status: design-only, awaiting full main review. This plan has no implementation authority. See [review packet](review-packet.md).

## Authorized documentation milestone

- [x] Read management entrypoint, applicable ADR-0075/0069/0056/0074 and spec/workflow conventions; inspect exact current ordinary source/contracts.
- [x] Fetch current develop; create independent task/geophysics-physical-json-sdd from7e26d25 in the owned ingestion worktree, preserving coursebe4 references and11 diagnostic directories.
- [x] Persist research before requirements/design/contracts and the explicit local-only/no-waiver boundary (R-PJB01..14).
- [x] Run tracked docs guards and independent path/link/EARS/scope audit; preserve no-code status (R-PJB14). Actual results are in the review packet.
- [ ] Commit/push scoped design and open a draft develop PR with self-review and full review pin; no merge.
- [ ] MAIN reads ALL seven documents and explicitly approves or requests corrections. A docs PR or merge alone does not authorize helper/tests.

## Only after explicit full review and implementation approval

1. Implement only data-pipeline/gravity_station_json.py with exact public function/error/limit contract, bounded iterative scanner, one native materialization and direct structural validation (R-PJB01..10,12).
2. Add only tests/data/test_gravity_station_json.py with authored independent scanner/native/golden/error controls; no field fixture or canonical rewrite (R-PJB01..10,12,14).
3. Execute real unchanged core/ordinary-adapter integration positives and deliberate structural-only/scientific-reject controls under reviewed runtime, preserving source hashes (R-PJB08,11,13).
4. Measure nominal/upper/malformed local wall/CPU/peak allocations/RSS and zero-I/O behavior; run existing scoped regressions; record skips/failures honestly (R-PJB03,06,10,13).
5. Record per-requirement convergence, exact source/runtime/commands/receipt pins, main review and local-only limitations; commit/push only newly approved paths (R-PJB01..14).

No later step adds API/route/wire/storage/migration/job/worker/bundle/frontend/admission activation. A future caller/integration is another approved unit and cannot invoke this plan as a waiver.

## Current convergence

| Requirements | Gate state | Meaning |
| --- | --- | --- |
| R-PJB01..13 | NOT_RUN | Proposed helper/test sources are absent; no execution or numerical/resource claim |
| R-PJB14 | Design boundary specified; full main approval pending | No implementation, method, feature, host or release acceptance |

The existing scientific and product convergence ledgers are unchanged. This design does not close the broader potential-field ingestion/M01/product issues.
