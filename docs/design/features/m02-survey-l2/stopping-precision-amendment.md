# M02 stopping precision amendment for full review

Status2026-10-03: RESEARCHED PROPOSAL, implementation NOT_APPROVED. The latest user explicitly authorized this investigation/design BEFORE code, without threshold changes or acceptance. MAIN must fully read the pinned packet before any product numerical decision change. Baseline45ff14ce retains frozen cpu-3 source c297294b and its stopping FAIL. [Research](../../../research/m02-l2-precision-2026-10-03.md), [actual receipt](evidence/precision-investigation-20261003.json), [prospective tests](stopping-precision-validation.md) and the linked research-side harness constitute the review unit. This does not rewrite the approved [binding amendment](binding-set-amendment.md), historical approvals or old failure receipts.

## Requirements and preferred decision

SP-R01: retain the exact fixed physical model, coefficients, submitted background/observations and their identities, W, regularization, beta grid/engine factor, bounds, starts, source admission, masks/partitions, units and scientific comparison thresholds.

SP-R02: retain native ProjectedGNCG directions on the reduced face, binding-release choice BEFORE CG, fixed diagonal, CG200/rtol1e-6/atol0, shortening .5, Armijo1e-4, LS20, accepted200, trace201, cooperative120s/1800s and failure precedence. No independent optimum/BVLS/rational dense solve enters production, no post-failure optimizer retry or artificially scaled accepted steps.

SP-R03: retain the existing convergence rule EXACTLY for the preferred proposal: absolute projected native gradient<=1e-12 OR normalized native KKT<=1e-5 AND last THREE genuine accepted relative objective changes<=1e-6. Rejected trials, repeated evaluation, interval precision escalations and rounded noops do not count as accepted changes. The current terminal state cannot be relabelled converged.

SP-R04: investigate/propose source-preserving reliable Armijo evaluation of ACTUAL projected chords, without subtraction of two rounded absolute Phi values. Strictly reject zero displacement, certify negative slope and sufficient decrease; no inequality widening, empirical epsilon floor, tolerant acceptance or noise-based shortcut.

SP-R05: distinguish arithmetic/source-model uncertainty, exact fixed-coefficient proofs, native rounded values and independent assembly. Unknown proof/arithmetic support stays unavailable or nonconverged. Neither finite fit nor low WRMS constitutes science/field/full-method acceptance.

SP-R06: measure full bounded tests/resources before any approval to use the new evaluator in selection/refit. Default current public/private solve semantics and source epoch stay unchanged until implementation is reviewed and pinned. New product/test digests remain absent, not fictitious.

Preferred review decision: approve, after full read, a precision-only line-search decision mechanism, NOT a new stopping tolerance. This specimen has a natural existing native chord reaching native gradient8.867906409193438e-15; the unchanged absolute exception then suffices, without inventing three small steps. This is a diagnostic observation, not an executed amended solve or a proof for all28 controls/sealed cases. Criterion weakening is NOT justified by this evidence.

## Exact mathematical domain and source fidelity

q is g/cc, rho=1000q kg/m3. For immutable native binary64 operands, define the real extension:

`E(q)=||W(Gq-dobs)||^2 + sum_j beta_engine*alpha_j*||Wj Dj(q-qref)||^2`.

dobs is the stored native binary64 `fl64(observed-background)`, NOT a new extended-precision subtraction of the original values. qref/alpha/W/D are the admitted native operands. IdentityMap and linear first-order terms are mandatory; positive-beta smallness makes this admitted quadratic SPD. Zero-multiplier second-order terms are not introduced. E is mathematically the frozen quadratic with its actual operands; it need not equal every rounded native scalar. No replacement of G by independent J, W by another whitening, R by an oracle matrix, or alpha*beta by an accidentally pre-rounded combined coefficient.

For native trial qt=projection(q+t*p), use exact real difference between the ACTUAL two binary64 model vectors, `dq=qt-q`. Do not substitute t*p before rounding/projection. With B0=WG,c0=W*dobs,w0=1 and Bj=Wj Dj,cj=Bj*qref,wj=beta*alpha_j:

`D=E(qt)-E(q)=sum_j wj*(2 rj(q).T Bj*dq + ||Bj*dq||^2)`.

Armijo uses the frozen accepted-state NATIVE gradient vector gn, not a newly substituted gradient: `s=gn.T dq`, `M=D-fl64(1e-4)*s`. Certify `s<0` and `M<=0`. The directed implementation below deliberately requires the sufficient strict certificate M_upper<0; exact-boundary equality remains unresolved/refused, not rounded into a pass. The actual frozen scalar1e-4 is preserved exactly, not ideal decimal1/10000. Reporting an exact-quadratic gradient in research does NOT authorize substituting it in the direction or stopping check.

## Proposed bounded precision decision, no native-package patch

After future explicit approval, implement only a private source-bound evaluator called by the owned recorder's trial acceptance observation. No caller-selected precision/runtime/engine hook. Installed SimPEG files and public request/result keys remain unchanged. This proposal changes delegation of the Armijo predicate previously evaluated by native absolute-Phi arithmetic; all non-Armijo native trial mechanics, accounting and error gates remain. It is NOT advertised as unchanged native line-search arithmetic.

1. Original native evaluation must return finite Phi/data/model values and coherent state. Original nonfinite/engine/state failures have precedence and are never rescued by interval arithmetic. An actual rounded noop fails immediately, BEFORE any inequality check.
2. Preserve the existing chosen native/PG direction and projected trial. No alternative/refinement direction, new beta/start or second solve. Each trial is still one of0..19 at the original shortening factors; precision escalations evaluate the SAME pair of models.
3. Construct outward intervals from the EXACT binary64 operands (`as_integer_ratio`/exact float conversion), including actual dq. Do not parse shortest decimal strings as exact input. Preserve separate matrix/operator factors through evaluation; do not flatten and round WG or WjDj, nor allocate a dense normal matrix. Evaluate nested residuals/operators and the direct D identity with interval products/sums.
4. Proposed fixed decimal precision ladder34,50,80 significant digits. Use explicit ROUND_FLOOR/ROUND_CEILING contexts, restoring caller context on exit. Every addition, subtraction, multiply, coefficient conversion and sum is enclosed. Test subnormal handling/exponent range; if assumptions/range cannot be certified, mark unavailable, no silent float64/longdouble fallback. This is a stdlib candidate; no new dependency/install or automatic runtime capability claim.
5. At each precision compute intervals [sL,sU],[ML,MU]. If sU<0 and MU<0, certificate permits acceptance of THIS trial. If sL>=0, it is non-descent; shorten as the original finite-slope rejection policy. If ML>0, reject/shorten. Otherwise escalate precision for the same trial, without registering an accepted state. At80digits unresolved means reject/shorten with diagnostic `precision_unresolved`; after LS20 retain line_search_failed. No invented tolerance around zero, midpoint-sign acceptance, or "tiny means safe" branch.
6. On certified acceptance, original state recording reevaluates genuine native data/model/objective/gradient at qt. Model predictions and residuals stay native. Keep actual native Phi in the public trace; it may differ by a few ULP from the real-extension descent. Private interval evidence must show the difference. Do NOT overwrite native Phi with a monotone surrogate. Existing native relative-change/absolute-gradient stopping rules stay unchanged. Finite raw Phi alone never justifies acceptance, and small changes cannot manufacture the missing third change.
7. Check the existing cooperative deadline between operator blocks and precision escalations, and on return before publication. No hard native preemption promise. Limits remain n<=2048, a<=4096, G<=64MiB, covariance<=32MiB, existing projected workspace<=2GiB. Stream residual/transpose row terms, bound retained interval operands/workspace before allocation, do not materialize Python-object copies of the entire G or80-digit dense H. At most one certificate record per actual trial, not one per arithmetic operation/precision pass. If the streamed implementation cannot fit the existing resource/120s limits it remains unsupported/nonconverged, NOT admitted by increasing caps.

The research harness rationally flattens ONLY the tiny15x6 control for exact external proof. It is not the proposed full-size evaluator and establishes no full-cap memory/time admission. This production streaming/interval implementation and its error enclosure are NOT written or tested yet.

## Precision improvements considered but not authorized as fallback

Compensating only sums of already-rounded products fails at the current model because its true gradient exceeds1e-12. An error-free product/sum expansion, accurate residual formation and transpose accumulation could tighten error bounds, but must preserve actual operator factors, handle overflow/underflow and prove enclosure. Python/NumPy longdouble on this actual Windows runtime remains53bits/8bytes; it offers no precision gain.

The research external correction solves `H dq=-g_exact` once, rounds q+dq naturally and proves a real decrease. It demonstrates attainable accuracy, but production dense factorization, QR replacement and post-CG retry are outside the approved hybrid. Since the original native CG chord already suffices here, adding refinement/search policy is unnecessary for this fix. If future controls show actual CG residual arithmetic needs refinement, it requires a separate source/algorithm/conditioning/resource review BEFORE implementation; no blind rounded normal-equation correction or vendor error estimate relabelled as rigorous.

## Exact private diagnostic contract proposed

Future owned optimizer evidence may add ONE `precision_trials` tuple (max4000), without replacing the existing10keys/history. Each record has EXACT14keys:

| key | type/bound |
| --- | --- |
| iteration | int0..199 actual accepted-state index |
| trial | int0..19 original trial index |
| native_phi_current | finite float64 or None on native failure |
| native_phi_trial | finite float64 or None on native failure |
| displacement_inf_q | finite float64>=0, g/cc, or None when no coherent chord |
| precision_digits | int34,50,80, or None when evaluator not run |
| slope_interval | tuple2 ASCII decimal strings, each<=192chars, or None |
| delta_interval | tuple2 ASCII decimal strings, each<=192chars, or None |
| armijo_margin_interval | tuple2 ASCII decimal strings, each<=192chars, or None |
| arithmetic_domain | literal fixed_native_operand_quadratic |
| slope_domain | literal recorded_native_gradient |
| decision | certified_accept, certified_reject, unresolved, not_run |
| cause | armijo, non_descent, zero_displacement, precision_limit, range_unsupported, wall_cap, native_failure |
| passes | int0..3 actual precision passes, not accepted count |

Decimal endpoints must be finite ordered exact decimal values, strict bounded grammar, no NaN/Infinity/locale, no truncation, context exponent bound checked. None means unavailable, never zero. Unknown enum/key/type rejects. `certified_accept` requires both finite native Phi values, displacement>0, complete source-bound computation, slope upper<0 and margin upper<0; unavailable/range/native failure cannot certify. Total retained diagnostics must stay within the existing256MiB trace allowance and projected-workspace admission, including native histories and other solves; the full-cap measurements are NOT_RUN. No public API/export change is implied by this private contract.

Proposed NEW runtime epoch `m02-survey-l2-cpu-4`, optimizer policy `projected-gncg-binding-release-certified-delta-1`, are RESERVED design names only. cpu-3 and its hashes are never relabelled. Exact future implementation/source/stdlib evidence must be pinned after actual reviewed code exists; no fabricated future hashes. These names require MAIN approval along with the changed private contract.

## CLOSED contingency: scale-aware KKT plus stagnation verdict

NOT NEEDED/ACTIVATED by this control. The existing1e-12 exception is attained by its natural full native chord. No additional convergence reason or eligibility is added in the preferred proposal.

If separately frozen broader controls prove that the fixed1e-12 is unattainable at their nearest representable solution, propose a separate DESIGN-ONLY verdict `finite_precision_stagnation`, distinct from convergence. This would require full review of a new contract/source epoch. It would retain `status=nonconverged`, be INELIGIBLE for selection/frozen evaluation by default, and carry no scientific acceptance. MAIN would have to explicitly approve any later status/eligibility criterion amendment; historical CPU3 failures remain failures.

Define a certified gradient enclosure gi in [li,ui] using the actual nested operators. Remove a component from a STRICT KKT certificate only at a literal feasible lower bound with li>=0 or literal upper bound with ui<=0. Ambiguous-sign/near-bound-but-interior components retain maximum magnitude. Also record the unchanged32eps projected native KKT separately; never shift bounds. Let vi be the strict projected enclosure maximum magnitude; denominator lower bound `d0L=max(1,lower_bound(||g_initial||inf))`. Require `max_i vi/d0L<=1e-5`, the EXISTING normalized numerical target, not midpoint-based K.

For componentwise scale, define `Si=2 sum_j wj*sum_rows |Bji|*(sum_k |Bjk|*|qk|+|cj|)` with certified upper/lower bounds on exact fixed operands; report `eta_i=vi/max(1,Si_lower)` (q units fixed g/cc). There is no newly fitted empirical eta threshold. Compute the algebraic representational allowance `Qi=sum_j |Hij|*ulp(qj)/2` using bounded streamed Hessian entries/enclosures without a dense H, and actual accumulation-error bound Ei. Both are labelled conservative UPPER allowances, not a theorem of a universal lower achievable error or physical uncertainty. The additional prospective roundoff-level check `vi<=Ei+Qi` cannot, by itself, certify an optimum or justify convergence.

A stagnation verdict would additionally require completion of the full existing admissible-direction/LS trial budget or an actual rounded-zero chord, retained trial evidence, no certified useful nonzero descent, verified arithmetic assumptions/enclosures, and failure precedence. It means only "this authorized finite-precision search could not certify further progress while its KKT bound meets the declared target". It does NOT mean no representable vector anywhere descends; such a global claim needs an independent bounded proof. Above-target KKT, weak/unknown bounds, available corrective chord, incomplete budget or resource/engine failure stays its original nonconverged/failed cause, not this verdict.

Difference from the current rule, if later approved: a NEW descriptive scale-aware roundoff/stagnation record instead of silently calling small-KKT/noop convergence; any proposal to make it converged/eligible would explicitly replace the absolute-or-three-change rule and needs new frozen acceptance review. Current terminal true gradient~4.99e-12 is above its conservative error+representation allowance~7.42e-13 and has certified useful native chords, so cannot meet this contingency. No manufactured tiny accepted steps, tolerance change, test masking or theorem of impossible progress.

## Review and implementation boundary

No product/source/test/native changes in this packet. Six NEW documentation/research/evidence paths only. Existing staged/dirty unrelated work and all original receipts remain protected. MAIN reviews the COMPLETE amendment, research, raw numerical receipt and validation BEFORE deciding implementation scope. Future preferred code scope, IF approved, would be the owned inverse recorder/evaluator and paired tests, not source geometry/operator/vendor files. No code authorization follows merely from publishing this proposal.

Full M02, source mapping/M01, IRLS, real calibration/refit/evaluation, sealed24family/condition matrix, API/bundle/UI/field/host/deployment remain incomplete. PR132 stays draft; this packet neither makes it ready nor deploys anything.
