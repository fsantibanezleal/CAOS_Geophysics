# Canonical scaled IRLS: native free-face guards

This source defines prospective guards, not an enabled fit policy. Existing
INTERIOR-only branches and their original failures are unchanged. A guarded
derivative is not evidence of fixed-point convergence or native fit accuracy.

At the current epsilon, evaluate the actual original canonical gradient first.
The installed SimPEG `ProjectedGNCG.bindingSet` determines the binding face:
lower-bound coordinates with nonnegative gradient, upper-bound coordinates
with nonpositive gradient. A literal bound with inward negative-gradient
motion is free. Bound equality alone cannot freeze it.

Let `F` be the native free coordinates, `x=q-reference`, and
`S=sqrt(max(abs(x))^2+epsilon^2)`. The canonical root Jacobian has

    J = M + u e_j^T,
    M = H0 + diag(v S epsilon^2 / (x^2+epsilon^2)^(3/2)).

If the unique maximizing coordinate is free, retain the rank-one term on the
literal free principal face. If every maximizing coordinate is binding and
there is a strict gap to every free coordinate, `S` is locally constant on
that fixed face, even if multiple binding coordinates tie. Then `J_FF=M_FF`
exactly; this does not differentiate a nonsmooth free maximum or perturb a tie.
Null models, empty free faces and any free maximum tie disable construction.

An auxiliary trial must remain feasible and nonzero, hold every binding
coordinate bitwise fixed, preserve the actual native binding signs, preserve
the maximizing identity/plateau and retain the strict gap. The guard never
projects a proposed point into another derivative branch. A later coupled
physical source proof and the unchanged original inner solve remain required.

These guards do not expose an upload objective, metric, mask, inverse or
certificate callback. They are private arithmetic within a prospective closed
physical constructor. Independent sign/release/feasibility/plateau/source
negative controls are separate from derivative, actual native CG, strict
merit Armijo, replay, complete 21-stage and original24/noise/refit qualification.
No nonconservative canonical root is presented as a new physical potential.

## Closed original source derivative and lifetime

The private derivative owner accepts only the exact original physical
partition constructor, actual normalized model, original policy and stage.
It computes actual native canonical gradient and binding signs itself. It
accepts no caller gradient, Hessian, mask, sparse factor or metric callback.
Unsupported faces disable before derivative or metric construction. Literal
free-vector embedding, native physical likelihood/directional actions and
positive smallness derivative form `M_FF`. A binding max removes the rank-one
action exactly; a unique free max retains it. The principal Joseph metric is
constructed from these source-owned operands and never replaces the derivative
action used by a future auxiliary CG residual check.

Its prospective resource dictionary sums the complete original retained
partition, a complete additional native factory phase, two fit-by-active
binary64 source matrices, bounded parameter/likelihood vector workspace,
sparse factors and metadata under the unchanged 2 GiB limit. No unexplained
extra blanket scratch ceiling or subtraction of coexisting phases is used.
Literal full48 SD/covariance dictionary controls are distinct from measured
RSS and actual full-fit acceptance. Owners dispose on source/clock/lifetime
failure. Native stage source checks and source-loaded/on-disk derivative
checks precede each action and factory construction.

Independent source-row and 80/120-digit finite-difference controls establish
the mathematical fixed-face derivative. They do not establish agreement of
every rounded native gradient with an ideal real expression under a universal
absolute `1e-12` test. Near cancellation, the actual native reduction and
weight-construction error must be independently explained and bounded. A
failed retained-state gradient prerequisite remains failed. This source does
not enable recurrence, adopt a proposal, execute auxiliary CG or accept a fit.

## Independent nested-gradient research

The test-only `gravity_face_gradient_oracle.py` computes a rational exact
gradient of the literal frozen stored-weight quadratic. It retains the
native nesting `G -> W -> W.T -> G.T` and, for each regularizer,
`D -> W -> W.T -> 2D.T`, then the actual alpha sum and beta product. It
does not replace those actions with rounded `WG` or `WD` matrices. Every
intermediate binary64 result is checked against an independently propagated
componentwise bound: `abs(A)*input_error + gamma_(2n)*sum(abs(A*x_float))`
plus an absolute subnormal term; scalar products and additions have their
own one-operation bounds. Source, model, reference/mapping and deadline
guards apply throughout. This arithmetic is not imported by product code.

Separately, 80/120-digit evaluation compares the exact stored smallness
weight with the ideal real canonical law. This distinguishes native nested
reduction error from rounded LP-weight/square-root construction error.
Near a cancelling gradient, neither term is controlled by a universal
absolute `1e-12` comparison alone. The retained fold1/stage20 comparison
is still FAIL; it is not relabeled by this decomposition or by passing
small-original controls. A retained-state forward bound and the unchanged
original scientific accuracy/stopping assertions remain required before
the proposed recurrence is enabled.

## Prospective actual native direction and strict trial replay

`gravity_irls_face_direction.py` implements a separate research epoch. It is
not selected by the original cpu1/cpu2/cpu3 calibration or archive reader.
Only a literal `GravityIRLSPartition` and its uninterrupted original budget
may construct the direction. A binding maximum uses one actual library CG
on `M_FF`; a unique free maximum uses two CG calls and the restricted
Sherman--Morrison update. Each actual CG has `maxiter=200`, `rtol=1e-6`,
`atol=0`, and its true original source-action residual is checked before use.
The rank-one denominator remains positive, with the original conditioning
ratio at least `sqrt(eps64)`. No dense production solve or fallback is used.

Merit is `0.5*||r_F||^2`, with its actual derivative `r_F.T J_FF p_F`.
Binding coordinates are embedded as exact zero direction entries. All
trials must preserve the actual native binding signs, literal box and
maximizing branch. The initial alpha is the exact stored-real first box
contact, bounded by one and rounded downward only if nearest binary64 would
exceed that rational contact. No projection or tolerance fudge is applied.
A zero outward contact refuses the proposal. At most the original 20
halvings are permitted and strict native free-merit Armijo descent is
required. All actual trial models, gradients, binding signs, canonical stage
seals, epsilon values and margins are retained, including rejected trials.
Each temporary canonical objective is released in a `finally` block.

The same budget counts at most three proposals per stage, 126 actual
auxiliary CG calls and 63 anchors, inside the original combined 200 accepted
moves/201 states/120-second partition and 1800-second calibration limits.
A direction or candidate is not an accepted move: production adoption must
be recorded within that same combined budget. A failed constructed CG or
line search remains failed, not a disabled branch or permission to fall back.

Independent replay rebuilds the source-owned metric operand, native free
face, true residual, denominator and direction without another CG. It then
recomputes every trial's actual source gradient, sign/branch and strict merit
margin. Altered hashes, supplied masks, truncated or added trials, modified
gradients, candidates, epsilon, stage seals or disposal claims cannot approve
a candidate. Actual retained-state proof and direction/trial positives are
prerequisites to enabling a new outer epoch, followed by unchanged complete
21-stage fixed-point assertions and original24/noise/refits. The historical
plain/interior-only failures remain unchanged.

The source-owned Joseph metric has a **full native parameter-vector ABI** even
when its factor is a free principal face. The free CG preconditioner therefore
zero-embeds into native space, applies that same owned metric, and restricts
back to `F`. An `F`-sized argument is an ABI error, not permission to replace
the physical action. Natural IC0/Joseph is an SPD metric, not an exact inverse
of `M_FF`; exact-inverse equality is not its contract. Each actual CG must
still independently satisfy the unchanged true `M_FF` residual threshold.
The research tests can retain complete failed and successful direction/trial
records under explicitly configured external temporary custody, before any
assertion, using exclusive files and exact float/array bits. This transport
does not approve a candidate or upgrade an earlier failed receipt.

## Separate complete source-prior direction epoch

The prospective complete-prior epoch preserves the literal source derivative,
native free face and all preceding scientific tests. It replaces only the
incomplete natural prior factor with complete natural sparse unit-lower LDLT.
Every computed nonzero fill entry is retained, with no dropping threshold,
permutation, pivot shift, retry or failed-CG fallback. It factors the actual
positive first-order regularization prior, not a dense physical Hessian.
The public default IC0 constructor and its historical epochs are unchanged.

In exact arithmetic, let `R=L D L.T` be that prior, `B` the literal original
whitened sensitivity at its existing likelihood scale, and
`F=R^-1 B.T (I+B R^-1 B.T)^-1`. The stored Joseph action is

    P = (I-F B) R^-1 (I-B.T F.T) + F F.T.

For any finite stored `F`, positive stored pivots and nonsingular stored
unit-lower `L`, this is positive definite in real arithmetic: if both terms
vanish for a nonzero `v`, `F.T v=0` and `(I-B.T F.T)v=0` imply `v=0`, a
contradiction. With exact `F` it equals `(R+B.T B)^-1`. Neither theorem promises
rounded forward direction accuracy. Every actual native CG must still pass
the true original action residual and the unchanged independent direction
assertion. A passing residual alone cannot qualify a direction under poor
physical conditioning.

The added worst-fill dictionary is `128*a*a+128*a+65536` bytes, in addition to
all original simultaneous source/factory/action/retained-book reserves. It
charges Python row entries, fill/reach sets and lists, factor and transpose
copies. Construction checks loaded Python object sizes and the unchanged
original limit before any complete factor allocation; the public owned class
checks its own literal limit too. Full48 SD/covariance sums are respectively
2140343720 and 2147421608 bytes, both below the original 2147483648-byte cap.
Larger closed requests can refuse; no claimed unused memory is deducted.
Allocation proof, actual native action, independent accuracy, strict trials,
complete 21-stage convergence and whole original24/noise/refits remain distinct.
This epoch is not a compiled nonlinear, quartic or global GN theorem.
