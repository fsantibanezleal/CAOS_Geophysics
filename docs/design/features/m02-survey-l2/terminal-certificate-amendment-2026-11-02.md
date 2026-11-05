# Additive M02 terminal certificate amendment — 2026-11-02

**Decision:** the user approved designing and validating this additive certificate.
**State:** design approved; candidate implementation present in the direct checkout.
The exact current-source 24-cell matrix passed 24/24; 208 certificates across all
24 current-source archives passed a separate computational replay. The 36 focused
controls, two fresh-root timing replays, and fresh exact-source 20-cap/20-nominal
resource replay also pass locally. The earlier resource receipt remains historical
because its solver source hash differed; the new 40-run receipt matches all 108
current source files. It still does not prove an allocation upper bound or actual
VPS admission. External peer/owner review and broader product acceptance remain
open.

## Scope and unchanged policy

This amendment applies only to the ordinary non-null CPU2 original-IRLS fixed-
point workflow, after its original 20 accepted weight updates at the epsilon
floor when the three-transition criterion fails. It adds no IRLS update, solver
call, retry, post-cap continuation, tolerance relaxation, or alternate objective.
The original 120 s per-fit and 1,800 s aggregate caps remain binding. CPU1, null
and reference terminals, and the existing three-transition success path retain
their prior behavior.

The new terminal route is allowed only when the final native bounded quadratic
solve reports `absolute_stationary` with zero iterations and no failed trial;
its serialized native state, independently replayed native trace, accepted
model, and final model are exactly array-equal; the source-recomputed sparse
weights and their hash exactly match the accepted stage; and independently
recomputed projected-KKT infinity norm is at most `1e-12`.

The certificate is restricted to a unique interior non-null maximum-weight
branch with no active bounds. Its frozen quadratic must have a strictly
positive smallness Hessian diagonal and a positive lower bound
`beta * min(diag(H_smallness))`. The other data and directional regularization
terms are positive semidefinite, so this lower bound proves strict convexity of
the fixed stage objective and a unique global minimizer on the feasible box.
The resulting statement is a fixed point of the prescribed weighted-stage map,
not a global-L1 optimality or geological-recovery claim.

The full source inventory, problem/request, bounds, beta, epsilon, active-set
branch, operators, weights, all preceding 20 stage records, terminal state,
resource counters, and result digest must be replayed. Any missing/altered or
ambiguous item rejects the certificate and retains the existing failure.

## Version and implementation identity

The candidate source is versioned as
`m02-survey-irls-cpu-2-terminal-certificate-exact-q-replay-legacy-init-1` with
policy `safeguarded-irls-interior-threepair-log17-terminal-certificate-exact-q-replay-legacy-init-1`.
The legacy source and its terminal policy remain a separate comparison. This
amendment records the user-authorized design for the candidate code already
present in this checkout; it does not imply that code is merged, promoted, or
accepted.

## Required verification before promotion

1. Positive: certificate identity and independent replay; every implicated
   source-bound beta/fold; a separate seeded non-null case; and unchanged null
   and three-transition controls.
2. Negative: any nonzero weight mismatch even below `1e-6`; KKT just above
   `1e-12`; nonconverged or nonzero-iteration final inner solve; one-ULP native
   state mismatch; nonpositive smallness curvature; tied maximum or active-bound
   branch; and tampered request, bounds, beta, epsilon, source, operator, stage,
   certificate, or result identities.
3. Run the complete source-bound local scientific suite, archive/replay gates,
   all 24 calibration cells, and measured per-fit and aggregate resource gates
   against this exact source epoch. Retain all failures and full resource
   evidence. A unit-test pass or research-only archived diagnostic does not
   satisfy these gates.
4. Computational replay without the producer's terminal-decision function is
   recorded for all 208 current-source archive certificates. External peer/owner
   review remains required before scientific acceptance or promotion.

Until every gate passes, this terminal route is candidate-only and does not
change scientific acceptance, selection, or release eligibility. The proposal
remains rejected operationally if any invariant, 24-cell result, or unchanged
resource cap fails.
