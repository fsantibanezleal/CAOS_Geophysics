# Stopping precision prospective validation and current evidence

Status2026-10-03: proposal NOT_APPROVED for product code. [Research](../../../research/m02-l2-precision-2026-10-03.md) and [design](stopping-precision-amendment.md) precede any changed numerical acceptance. Original [validation](validation.md), [binding tests](binding-set-validation.md), source epochs and receipts remain frozen. None of the prospective tests below was authored/run as a formal acceptance test in this docs-only task.

## Actual research execution, narrow assertions only

Command in the scoped worktree, using the existing read-only approved pipeline CPython3.12.10 interpreter:

`python docs/research/m02-l2-precision-diagnostic-2026-10-03.py`.

Process environment disables bytecode, fixes OPENBLAS/OMP/MKL threads to1, and places Numba cache beneath NEW private `.validation/precision-research-20261003-a/numba`. No install, package edit, persistent setting or other-checkout file write. Harness reads the unchanged unsealed test specification and solver, calls the original record/direction methods exactly once per corresponding real event, snapshots q/d/native-g, and restores the in-process diagnostic wrappers. There is no acceptance override. No export to a canonical data folder.

Actual final harness exit0, with seven named invariant families enforced by assertions in both coefficient domains: positive rational SPD pivots; exact Hq=c; exact strict box feasibility; exact optimum gradient zero; residual delta equals exact objective difference; directed margin contains rational truth; directed slope contains rational truth. There are20 precision certificates (two domains, two actual native chords, five precision levels); both inclusions are asserted for each. This is NOT "seven scientific tests PASS", independent-owner acceptance, an amended solve, or a full source/runtime certificate. The included future step/refinement diagnostics do not enter the original accepted trace.

The original frozen execution reproduced FAIL/nonconverged/zero_free_direction; relative changes and actual source/test hashes match the prior blocker. The research runner exits0 because its diagnostic proofs completed, NOT because frozen convergence passed. The full raw result is [retained](evidence/precision-investigation-20261003.json), including exact optimum rational strings, source hashes, binary hex state vectors, all shortened native-chord trials and noop/true-ascent negatives. Original failure JUnit/archive receipts remain byte-identical and protected. Five actual primary fetch receipts returned200, separately hashed with explicit PDF/HTML domains.

## Mandatory named tests after full design approval

All SP-T01..16 are NOT_RUN for the proposed product evaluator. Test-first implementation would occur only after MAIN authorizes the exact code/test paths and decision policy. No original threshold/assertion/start/sample/timing rewrite or exclusion.

| gate | prospective test and required observation |
| --- | --- |
| SP-T01 | `test_certified_delta_native_six_cell_full_chord`: unchanged failing specimen, actual native full chord, directed margin encloses rational reference and is strictly negative; native post-step gradient<=1e-12, genuine end-to-end status only after implementation |
| SP-T02 | `test_certified_delta_no_fake_progress`: repeated state, rounded noop, zero slope, precision escalation and rejected trials never append history or satisfy three-change rule |
| SP-T03 | `test_certified_delta_rounding_reversal`: real exact decrease with rounded native Phi increase is certified without overwriting native Phi; corresponding exact ascent is rejected even if rounded native Phi appears equal/lower |
| SP-T04 | `test_certified_delta_frozen_slope`: use exact recorded-native-gradient dot ACTUAL projected displacement; not t*p, new gradient, finite difference, oracle gradient, or overwritten coefficient |
| SP-T05 | `test_certified_delta_interval_inclusion`: exact rational tiny references, directed rounding at every operation; intervals contain delta/slope/margin, boundary equality/unresolved never midpoint-pass |
| SP-T06 | `test_certified_delta_source_identity`: dobs and qref preserve native rounding; G/W/Wj/Dj/alpha/beta exact float identity; no flatten-then-round, higher-precision d-b or ideal decimal1e-4 substitution |
| SP-T07 | `test_certified_delta_platform_precision`: measured longdouble53bits8bytes stays non-extended; changed runtime/source or unsupported rounding/range refuses proof; no hidden package/engine fallback |
| SP-T08 | `test_certified_delta_native_failures`: nonfinite/stale-state/engine failure/CG cap/residual failure/line-search cap keep original precedence, outputs None where unavailable; interval success cannot rescue native failure |
| SP-T09 | `test_certified_delta_precision_deadline_caps`: ladder34/50/80 fixed, max3passes per trial, LS20, states201, accepted200,120s/1800s; no retries/new directions; expired deadline prevents accepted publication |
| SP-T10 | `test_certified_delta_exact_diagnostic_keys`: proposed14keys, exact bounded decimals/enums/types/order, no NaN/Infinity/arbitrary bigint/caller-selected precision, unknown/extra keys reject; unavailable None, not0 |
| SP-T11 | `test_certified_delta_null_bound_faces`: stationary null/reference, exact bound minimizer, near-bound interior inward gradient, ambiguous interval sign and mixed binding release; no altered bound diagnostic/feasible clipping |
| SP-T12 | `test_certified_delta_unchanged_controls`: all28 original/supplemental six-cell starts/bounds/noise cases plus tiny J/volume/full-C/mask/order/reference controls, exact frozen optimum/model/objective/prediction/KKT comparisons and required status |
| SP-T13 | `test_certified_delta_streaming_resources`: actual n/a/operator/covariance/workspace preflight and measured full workflow memory/time; interval object growth accounted before allocation, no full-size Fraction/dense H or cap weakening |
| SP-T14 | `test_certified_delta_selection_refit_sealed`: actual8beta*3fold+refit, unopened outer evaluation and locked24family/condition matrix with existing scientific thresholds, literal failed-candidate exclusion and no specimen substitution |
| SP-T15 | `test_stagnation_verdict_closed`: no new convergence reason/eligibility in preferred policy; correctable terminal with genuine native chord cannot receive stagnation; frozen stopping failure remains historical FAIL |
| SP-T16 | `test_scale_stagnation_prospective_negatives`: ONLY if contingency separately authorized: enclosure-upper normalized KKT, componentwise scale, allowance bound, exact active-face signs, exhausted/noop evidence; unknown/above-target/correctable/resource failures never pass |

SP-T12 is28 mathematical six-cell start/noise/bounds controls, NOT the locked24family/condition evaluation. SP-T14 must separately run real selection/refit/evaluation, not fixed beta diagnostic fits or fixture success. Existing engine kernel/geometry tolerance, covariance condition<=1e8, no jitter/floors and source-identity guards remain exact.

## Independent optimum and error-proof review checklist

Reviewer must reproduce BOTH domain certificates, not just BVLS status or native low gradient. Assert symmetric exact H, positive exact pivots, exact stationary solution, strict box feasibility, known active-face sign conditions for future narrow-bound certificates, and global SPD optimum argument. Our present wide specimen proves an INTERIOR bounded optimum; it does not claim all active-bound controls already exact-certified.

Check all q hex values and recorded native gradient against the unchanged genuine callbacks. Verify residual direct-delta identity independently and that the same models, not manufactured steps, generate it. Native vs independent coefficient differences must remain visible. Exact rational output is relative to fixed binary coefficients, NOT a bound on analytic prism physics, geometry/measurement errors or geological uniqueness.

Check gamma formula/exponent/underflow assumptions; the flattened conservative bound is NOT a native nested-BLAS proof. Review production nested interval/error propagation independently, including transposes, covariance mixing, regularization reference subtraction and scalar weights. Outward decimal endpoints cannot be rounded inward during formatting/serialization. Review exact operand import, context restoration and signed-zero/subnormal/overflow/NaN rejection.

The observed native full chord meets the current absolute exception; verify that preferred implementation does NOT merely return the exact optimum/oracle correction. Native fixed directions must be used once and unchanged. Accepting equal rounded Phi is insufficient evidence; strict interval slope/margin certification plus distinct state is mandatory. No criterion change is presently necessary for the failing control, but full-size/other-case attainment remains unproved.

## Prospective source/state evidence and truthful handoff

After implementation, new runtime/policy/source digests must refer to actual reviewed bytes. Keep cpu-3/failures immutable. Compare original public solve keys, None semantics, traces, candidate eligibility, prediction/residual signs and native terminal replay. Record actual test commands/counts/failures/skips/timing, environment loaded versions and source pins; no inherited historical PASS for changed code. Record guard results AFTER staging all new tracked paths and inspect the scoped diff before commit/push.

For this research packet, guards/whitespace/source protection are checked separately from numerical acceptance. No frontend/browser/API/native-platform/host/full-method gates are run or claimed. No production mechanism, epoch, criterion, calibration eligibility or deployment is changed. PR132 remains draft and requires MAIN full pinned read before code.

## Actual scoped self-review and staged guards

Final research harness exit0,6.4141135s for this tiny cached development diagnostic ONLY. AST parsing, strict receipt assertions, both certificate count, seven invariant families, source-hash binding, explicit noop inadmissibility and five primary200receipts checks PASS. These are diagnostic/integrity checks, not SP-T01..16 or full resource/scientific acceptance.

After staging precisely the six NEW paths in this packet: `python scripts/check_content_standards.py` PASS; `python scripts/check_template_residue.py` PASS,891tracked paths; `python scripts/check_ci_budget.py` PASS; `git diff --cached --check` PASS. Scoped staged diff contains no product/test/old-document modification. Self-review corrected diagnostic None handling on native failure, explicitly labelled full unprojected gradient normalization in the research receipt, and separated bare Armijo equality from strict admissibility for the research noop. No criterion or source fix was smuggled into those documentation corrections.

Actual SHA audit matches frozen gravity_l2/test_gravity_l2, planner/selection tests, accepted forward, approved binding amendment and installed SimPEG optimization/data_misfit/regularization base sources. Four original private receipts were rehashed read-only and match their prior published pins: red ef3d80e11d2ff1777d7c96deb0f0a893e9b4eff04e45db1dde15c77ea535dcd0; first-green9effb23730710aaa3c041fcd37687e914785946605f1c3a9478901d565db2bb3; full-focused0071094df543bc358727cd0617520316f27cf70845129f2f30c5198b3dc208e6; six-cell replay6cbbe5d00e48b40e70ec3d24a33c97a2fc99d7cc9951d7084de9d5cd46ff06d3. Their original FAIL/PASS/skips meanings are not replaced. Protected `.validation/` remains untracked; only the new research cache subdirectory was used, no receipt copied to public/canonical assets.
