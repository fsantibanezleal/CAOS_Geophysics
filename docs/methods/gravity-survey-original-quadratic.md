# Original-noise reduced quadratic and corrected IRLS ownership

This is the closed numerical source contract for supplied gravity, not a source
rights decision, hosted API grant, nonlinear model or field-density claim.
The [practitioner workflow](gravity-survey-workflow.md) specifies original byte
custody, physical corrections, leakage-safe geometry, frozen evaluation and
external-only commands. The [original-noise bridge](../design/features/physical-owned-spd/gravity-original-noise.md)
defines the literal numerical ABI. Historical ordinary L2, plain IRLS and cpu2
archives keep their own source inventory, recipe and actual failed verdicts.

## Original physics, scaling and noise

Let \(q=\rho/1000\) in g/cc, with physical density contrast \(\rho\) in
kg/m3. For fixed fitting rows, the actual native problem is

\[
 \Phi(q)=\|W(Gq-d_{engine})\|_2^2+
 n_f\beta_c\sum_j\alpha_j\|W_jD_j(q-q_{ref})\|_2^2,
 \qquad \ell\le q\le u.
\]

Original background is subtracted once into \(d_{engine}\). The data misfit
is unhalved; the original mean-data candidate normalization is
\(\beta_{engine}=n_f\beta_c\). No coupling, weight, beta, noise scale or
scientific threshold is adjusted to help convergence. See the pinned
[SimPEG misfit source](https://github.com/simpeg/simpeg/blob/v0.25.2/simpeg/data_misfit.py)
and [Sparse regularization source](https://github.com/simpeg/simpeg/blob/v0.25.2/simpeg/regularization/sparse.py).

Diagonal noise uses original positive SD division. Covariance uses the exact
original fitting principal block and stored symmetric inverse precision root
from the frozen eigendecomposition recipe. It is not substituted by a differently
rounded Cholesky inverse, materialized whitened-H approximation, symmetrized
covariance, eigenvalue clipping or jitter. Source interval actions preserve the
original factor nesting and stored binary64 entries. Exported station residuals
are observed minus predicted; upward mGal and kg/m3 conversion remain explicit.

## Working face and actual physical CG

The actual installed native optimizer derives its working mask from the current
physical gradient and original bounds. On the inactive/free principal block,

\[
 H_{FF}p_F=-g_F,\quad p_A=0,\qquad
 \|H_{FF}p_F+g_F\|_2/\|g_F\|_2\le10^{-6}.
\]

The closed owner builds a Joseph SPD preconditioner from the original source
operands for that face. This changes neither \(H\), \(g\), \(\Phi\), nor the
native true-residual test. An unconstrained inverse direction followed by
projection need not preserve descent, which is why the physical free block is
solved before first feasible contact. The actual physical Armijo inequality
is then evaluated with source-bound original operands. Different phase counts
are summed against the same original 200 CG iterations per direction, not a
fresh 200 for each phase. Actual library CG, failed states, rejected trials and
best available trial remain in the audit; no private CG or BVLS rescue occurs.

This algorithm-family distinction is supported by the official
[PETSc GPCG documentation](https://petsc.org/release/manualpages/Tao/TAOGPCG/)
and [BNK inactive principal-Hessian extraction](https://petsc.org/main/src/tao/bound/impls/bnk/bnk.c.html).
These are primary context, not imported perturbation/fallback permissions or a
proof of this product's scientific precision.

## Source-original terminal certificate

The terminal face is determined by exact original bound equalities, not a
supplied mask or proximity threshold. Positive original scientific smallness
provides \(H\succeq\mu I\), \(\mu>0\). Pure outward-rounded source actions
bound the original gradient/Hessian and the owned stored factor action \(P\).
If

\[
 \kappa=\|I-PH_{FF}\|_\infty<1,\qquad
 \eta=\|Pg_F\|_\infty,\qquad e=\eta/(1-\kappa),
\]

the Neumann bound gives free-coordinate error at most \(e\). Every interval
\([q_i-e,q_i+e]\), \(i\in F\), must lie strictly inside its original bounds.
For each active lower coordinate, the original gradient lower endpoint minus
the upper bound on \(|H_{iF}|\mathbf 1\,e\) must be nonnegative; at an upper
coordinate use the negated upper gradient endpoint. These coupling guards
prove that the same active face solves the original box problem, not just a
free unconstrained quadratic. No inaccurate gradient sign is silently clipped
into a terminal success.

The same source actions produce

\[
 \|q-q^*\|_2\le\sqrt{|F|}\,e,\qquad
 \Phi(q)-\Phi(q^*)\le\|g_{feas}\|_2^2/(2\mu),
\]
\[
 \|p(q)-p(q^*)\|_\infty\le
 \max_i\|G_{physical,i}\|_2\sqrt{|F|}\,e.
\]

The physical prediction sensitivity is unwhitened. Native and source canonical
normalized KKT must both satisfy the declared stronger 1e-7 gate; gravity also
requires q-error2<=1e-8, objective-gap<=1e-8 and physical prediction sup<=1e-6.
These gates supplement, not replace, original independent physical model,
mapping, prediction and objective assertions. This is a strongly convex fixed
quadratic argument, not a global nonlinear Gauss-Newton theorem.

If the outward ORIGINAL feasible gradient is exactly zero, original positive
mu proves the unique optimum directly: for every feasible z, gradient dot(z-q)
is nonnegative and Phi(z)>=Phi(q)+mu/2||z-q||2^2. This exact source predicate is
not a floating nearzero tolerance. The record names `exact_source_feasible_kkt`,
with kappa/eta unavailable rather than a fictitious zero contraction. Native KKT,
source validation, free intervals, active signs, original caps and disposal still
apply. The nonzero branch remains `free_face_neumann`; it does not receive this
proof by analogy or because a CG/line search failed.

## Corrected original-noise IRLS source composition

`gravity_irls_original.GravityIRLSPartition` takes only the original physical
request, observed values, declared noise, prior, fit rows, beta and absolute
deadline. It constructs one native base, owns original-noise initialization,
then owns every actual frozen Sparse stage. Callers cannot supply a simulation,
objective, derivative, preconditioner, factor, mask, jitter or approval callback.
Operand/source drift and post-disposal actions reject.

The explicit epoch is `m02-survey-irls-cpu-3`; policy is
`safeguarded-irls-interior-threepair-original-noise-reduced-1`. Its public
`solve_partition` and `validate_partition` use the same reviewed
[interior three-pair fixed-point correction](../design/features/m02-irls-corrected/design.md).
The native q is retained exactly instead of reconstructing it by a potentially
lossy kg/m3 round trip. Derivative proposals remain disabled before construction
for any bound face, tied maximum or null model. Failed auxiliary CG/merit/native
solve has no fallback. Original scientific weights and scheduled epsilon remain.

Initialization, adopted anchors and native moves share 200 accepted moves,
201 actual states and 120 seconds. All 21 native inners, 20 weight updates,
17 logarithmic transitions and three floor observations remain required.
Final three model/weight changes<=1e-6 and final canonical weight mismatch<=1e-6
remain literal; canonical KKT is absolute1e-12 or normalized1e-5. At most three
pairs per stage, 126 actual auxiliary CG calls and 63 anchors are admitted.
The original per-direction CG200/rtol1e-6/atol0 and 20 line-search trials are
unchanged. Complete calibration and a separate conditional-noise job each keep
their own original 1800-second absolute deadline.

## Public workflow, replay and resource separation

Public `calibrate`, `validate`, `evaluate` use these distinct exact schemas:

- `gravity-survey-irls-original-calibration-request-1`
- `gravity-survey-irls-original-calibration-result-1`
- `gravity-survey-irls-original-evaluation-request-1`
- `gravity-survey-irls-original-evaluation-result-1`

All eight original betas, three original folds and at most one selected
development refit are retained. Eligibility requires complete converged folds
and finite original marginal scores. An unstarted/failed fit is unavailable,
not a zero-score/null-model success. Outer data cannot enter selection. Native
transport and CLI commands remain shared; schema dispatch never upgrades an old
archive to this epoch. Conditional noise uses the same frozen selected recipe,
original starts, 32 real targets and PCG64 seed20261008, never field truth.

Lossless initialization and each native phase book are separately encoded under
the original native guards; the complete partition/calibration wrappers are
also charged. Original 256MiB native arrays, 256KiB metadata, 32768 scalars,
depth8 and ZIP member bounds remain. Whole-IRLS construction preflights the
native source/factor/endpoints, retained initialization plus 21 inner books,
63 possible auxiliary proposals and stage records against original2GiB before
native construction. Phase checks include original backing allocation, source
snapshots, sparse transposes, free factors and retained terminal audits.

CPU3 workflow partitions use a distinct `gravity-irls-typed-pool-2` envelope:
the exact UTF8 string table is stored in bounded int64 byte and offset banks,
not repeatedly charged Python textual metadata. Original raw book and v1 pool
guards run before encoding; read expansion re-applies the unchanged logical v1
guard and every original node/span/string/hash check. Every byte, padding and
offset is checked, text is strict UTF8, no decimal is rounded or field omitted,
and byte-bank storage is charged at its actual eight bytes per integer. Old
cpu2/history keep v1; no archive is upgraded by schema dispatch.

Replay reconstructs actual original source objectives, true native H residuals,
native masks, physical Armijo source proofs, stored-factor/active-free terminal
guards, epsilon/weights, canonical KKT and all scored predictions without any
optimizer or fresh CG call. Source/runtime hashes bind defining installed code;
content hashes alone do not establish scientific replay or execution custody.
The original solve clock is never reset to finish a fit. A separately bounded
read replay has no authority to append states or promote its historical result.

Resource dictionary admission, actual RSS, operating-system process containment,
Linux binary qualification, original source rights and online admission are
distinct. There is no M11 compiled identity-W, property-scale/c=.5, quartic,
cross-gradient or nonlinear grant here. Full original24/noise/refit, independent
accuracy, API/UI and deployment criteria remain separate executable gates.
