# Existing server-result instruments

Status: planned. Parent: product SDD R-011/R-013/R-014/R-015 and the processing
and MT scientific workbench contracts. This unit extends inspection of existing
server results, not the set of scientific methods or API schemas.

SRV-01 WHEN an owner opens a saved processing ZIP for the selected successful
job, THE workbench SHALL reject files outside22..17825792 bytes before reading
and use the existing modality-specific verifier, original member digests and
selected dataset/job identities before displaying anything from that file.
Gate: `frontend/src/test/scientific-result-views.test.ts` and
`frontend/e2e/scientific-result-views.spec.ts`.

SRV-02 IF verification fails or the project/dataset/job/session changes while
reading, THEN THE file-opening control SHALL retain no newly imported values,
discard stale completion and explain failure without uploading bytes or changing
server records. Gate: the same named unit/browser gates, including foreign-job,
tampered-file and delayed-read controls.

SRV-03 WHEN an owner exports an inspection snapshot, THE instrument SHALL retain
exact declared observations, units, masks, geometry/frame, source rights and
result identities; QC-only unavailable prediction/residual/model fields SHALL
remain null, not zero. Gate: `frontend/src/test/scientific-result-views.test.ts`
exact JSON roundtrip and actual browser download comparisons.

SRV-04 WHEN an MT frequency is selected in any linked response/tensor/residual
view, THE instrument SHALL expose exact XY and sign-corrected -YX observations,
marginal errors, final prediction and signed residual values at that same
frequency, with explicit train/holdout/QC-only labels. Gate: the same named gates.

SRV-05 WHEN recorded MT solver evaluations are inspected, THE instrument SHALL
link the scrubber, objective cursor, literal state identity and recorded layer
profile. Play SHALL advance existing frames only, stop at the final frame and
pause on selection/view change, reduced motion, hidden document or unmount.
Gate: `frontend/e2e/scientific-result-views.spec.ts` recorded-state controls.

SRV-06 WHEN a recorded state is exported, THE JSON SHALL contain its existing
index/kind/step/model/objective and imposed geometry with source identities,
but no fabricated historical prediction. Response panels SHALL remain bound to
the selected final result. Gate: the same named gates, frame-export equality.

SRV-07 THE controls SHALL use existing shared-shell tokens/classes and complete
EN/ES labels in light/dark at desktop/phone sizes, retain keyboard operation and
scientific nonclaims, and introduce no route, style system or numerical engine.
Gate: `frontend/e2e/scientific-result-views.spec.ts` viewport/theme/language/reduced
motion matrix, complete Vitest/build and content/single-origin/artifact guards.
