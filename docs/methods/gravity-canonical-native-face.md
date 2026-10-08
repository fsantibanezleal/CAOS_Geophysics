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
