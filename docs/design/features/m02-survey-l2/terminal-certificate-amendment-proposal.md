# Proposal: exact fixed-point certificate at the IRLS update cap

**State: certificate design approved by the user; full validation and product acceptance remain open.** See the controlling [dated amendment](terminal-certificate-amendment-2026-11-02.md). The implementation in this checkout remains candidate-only pending the full gates there.

## Decision sought

The authorized design adds one terminal certificate for the ordinary non-null original-IRLS workflow. It preserves the 20 accepted weight-update cap, existing change tolerances, 1e-12 absolute projected-KKT threshold, 1e-5 normalized KKT threshold, per-fit 120 s limit, and aggregate 1,800 s limit. It applies only after the existing 20 updates at the epsilon floor, when the current three-transition test fails.

The candidate certificate requires all of the following from the source-bound final stage:

1. The native bounded quadratic solver reports `absolute_stationary` and its independently replayed terminal state is exactly the accepted model `q`.
2. Recomputing the sparse weights from that terminal `q` produces the exact same weight array used by that stage (`canonical_weight_mismatch == 0.0`), not merely a value below the existing 1e-6 diagnostic tolerance.
3. The independently recomputed projected-gradient infinity norm is at most 1e-12 in the recorded physical normalization.
4. The frozen stage objective is strictly convex on the feasible box, with the existing positive smallness diagonal and positive lower-eigenvalue proof. Therefore its KKT point is the unique global bounded minimizer.
5. The request, bounds, active set, stage operator, beta, epsilon, weights, native source identity, all 20 preceding stage records, and all existing resource caps replay exactly.

This is a direct certificate that the current model is a fixed point of the prescribed map, not an extra update, a tolerance relaxation, a retrospective model substitution, or a claim about a global L1 objective. Outside this narrow, user-approved certificate route, the existing terminal policy still requires three small successive transitions. The certificate remains candidate-only until its additional controls pass.

## Evidence prompting the proposal

The current-source original24 archive contains 12 final stages for candidates 3–6 whose inner reason is `absolute_stationary`. The exact-state terminal audit reconstructs the same weight arrays bit-for-bit, recomputes projected-KKT infinity residuals from `1.76e-13` to `8.04e-13`, and verifies a positive smallness-diagonal coefficient of at least `0.15`. Its external receipt and hash are in [the continuation research evidence](evidence/floor-continuation-research-2026-10-31.md). Some of these folds fail the existing terminal solely because one of the last three IRLS transitions exceeds 1e-6. The research-only continuation then performs a zero-iteration solve and records another small transition, but that solve exceeds the existing 20-update cap and is not product-eligible.

This observation is limited to the frozen family-0 / condition-0 synthetic source and does not establish eligibility for candidates 0–2 or 7, full calibration selection, the other 23 family/condition pairs, or field data.

## Required design and validation before implementation

The dated additive amendment records the approved design and source epoch. Positive and adversarial gates must independently recompute weights, KKT, strict convexity and unique-optimum identity from original requests. Positive controls must cover every currently implicated beta/fold plus a distinct seeded non-null case. Negative controls must reject: nonzero weight mismatch even when below 1e-6; KKT just above 1e-12; nonconverged inner solves; non-SPD/zero-smallness cases; stale or altered operators, beta, epsilon, bounds or source; tie/active-bound ambiguity that prevents the positive lower-eigenvalue proof; and a model whose native state differs by one representable float. Null/reference and existing three-transition paths must remain unchanged.

Then rerun the full local scientific, archive/replay, all 24 calibration cells and resource gates on the exact new source. The unchanged aggregate and per-fit limits must pass. Independent review must reproduce the certificate without importing the producer's terminal decision. The rule must be reverted or remain proposed if any one gate fails. No VPS release may be staged until the entire approved product and host release checklist passes.

## Scope boundary

This proposal does not repair the aggregate-wall overrun, the low-beta initialization and line-search failures, the bound-tied generalized-weight derivative case, candidates 0–2 or 7, or any other family/condition. It does not claim scientific or product acceptance and does not authorize changing the approved SDD by itself.
