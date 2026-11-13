# Original-noise accuracy termination

`physical_original_optimizer.solve_bounded_linear` is a separate prospective
linear epoch. It preserves installed SimPEG ProjectedGNCG, the native physical
objective, gradient and Hessian actions, and the original reduced first-contact
direction policy. No dense optimization oracle, private CG, inverse supplied by
a caller, jitter, scientific coefficient change or failed-solve fallback exists.
The original 200 summed CG iterations per direction, true relative residual
`1e-6`, 200 accepted steps, 201 retained states, 20 line-search trials and one
uninterrupted 120-second deadline remain binding. A stronger terminal consumes
that same deadline; it never finishes and restarts a fit.

## Literal source arithmetic

The fixed objective is

\[
 \Phi(q)=c\|W(Gq-d)\|_2^2+
 \beta\sum_j\alpha_j\|W_jD_j(q-q_{ref})\|_2^2,
 \qquad l\le q\le u.
\]

`OriginalQuadraticOperands` binds the original stored sensitivity, observations,
reference, box, coefficients and canonical sparse physical factors. For diagonal
noise, each action divides by the original positive standard deviation, not a
rounded reciprocal. Covariance uses the actual stored native lower Cholesky
factor, forward substitution and its adjoint. Linear TMI keeps the nested
three-component sensitivity followed by the original unit direction, rather
than substituting a rounded projected matrix. Native H/g remain the optimizer's
authority; source-real outward arithmetic is an independent accuracy predicate.

The additive `magnetic_original_optimizer.solve_magnetic_original` bridge takes
the actual native MagneticObjective, not a caller-made objective subclass or
certificate decision. Only secondary-vector and linear-TMI likelihoods are
supported. The full original source component count is an explicit workflow
allocation input; the bridge does not infer it from fitted scalar rows.
Acquisition, sealing, source/native-host authority and execution custody remain
independent workflow obligations. The bridge grants no exact-norm, quartic or
compiler-stencil admission.

## Owned free-face certificate

`OwnedOriginalTerminal` derives the free coordinates from exact bound equalities,
snapshots the closed original source operands, and constructs its own principal
Joseph metric. It accepts neither an external metric nor a free-mask approval.
Let F be this face, H the original real quadratic Hessian and M the exact real
interpretation of the factory's stored factors. Stream one source column at a
time and use pure directed 34-digit arithmetic to bound

\[
 \kappa=\|I-MH_{FF}\|_\infty<1,\qquad
 \eta=\|Mg_F\|_\infty,\qquad
 e=\frac{\eta}{1-\kappa}.
\]

No dense physical H, inverse or retained interval column matrix is formed.
The Neumann series gives the unique free stationary point inside the box
`q_F +/- e`. Every free interval must lie strictly inside the original bounds.
Every active full gradient sign must hold throughout that interval. Its drift
is bounded with original whitened-column Cauchy norms and sparse
`|D|^T |W|^T |W|` actions. Incorrect signs, crossing bounds, or `kappa >= 1`
produce a retained failed sufficient check, never a relaxed assertion.

Positive original diagonal scientific smallness establishes a real lower
curvature mu. Once the entire face's KKT signs are certified, this stationary
point is the unique full-box optimum. The sufficient model error is
`sqrt(|F|)*e`; original physical prediction row norms give a sup-norm bound.
The objective-gap bound is the original projected-gradient squared norm divided
by `2*mu`. Both canonical native KKT and outward original-source KKT must satisfy
the declared original normalization and threshold. Empty free faces require
the full original sign proof and create no synthetic CG calls.

Each Decimal operation uses an explicit directed context. Endpoint absolute
values and sign reversals use exact `copy_abs` and `copy_negate`; ambient-context
rounding must not shrink upper bounds. Native-row intervals are deliberately
not used for this ill-conditioned contraction proof.

## Physical domain, resource and lifetime

Both endpoints of every actual magnetic Armijo chord retain the original
strict `||B0 + Gq|| / F > 1e-8` real affine direction predicate. A zero norm or
uncertified ratio cannot be accepted merely because the linear objective is
finite. Original objective displacement and the actual native-gradient slope
are certified separately with the original strict Armijo rule.

The source owner admits dimensions, ultimate backing storage, scalar metadata,
canonical sparse structure and the source/model binding before snapshots and
factor construction. The simultaneous phase dictionary adds original source
copies/arithmetic, free endpoint buffers, factory factors and sparse transpose,
native workspace, retained actual native audit buffers and bounded metadata.
It must fit both the original admitted bytes and resource limit. This dictionary
is not an RSS or native allocator/host-headroom proof. Construction, expiration,
failed sufficient proofs and successful proofs all dispose the factory and
snapshots. Use after close refuses; source/model/face refresh constructs a new
owner and never reuses an old inverse.

## Verification and interpretation

`test_physical_original_terminal.py` interprets original source and stored
factory factors independently with Fraction arithmetic. It checks exact optima,
model/gap/prediction enclosures, SD and stored-L noise, nested projections,
normalizations, ambient contexts, incorrect active signs, crossing bounds,
one-byte resource deficit, source drift, invalid pivots, contraction failure,
expiry and disposal. Native original-noise tests preserve independent BVLS
comparisons solely in the test process, never production.

`test_actual_original_full528_firstfold_strong_accuracy` is one frozen original
first-fold prerequisite, not a full matrix or field-validity claim. The bounded
validation DAG must stop dependent matrices on any failed unchanged prerequisite.
Retained historical diagnostic or independent-oracle evidence cannot upgrade
an earlier fit's terminal flag, source epoch or clock.
