# Binding-set L2 direction research, docs-only proposal

Date2026-10-03. Frozen implementation6331bee9cf289e59647566ac01efc178d51a8e6c.
MAIN requested this investigation after reading the new ordinary near-zero
negative; this is NOT approval to implement another search policy. No code,
tests, installed files, original documents or execution receipts are changed.
The [new full amendment](../design/features/m02-survey-l2/binding-set-amendment.md),
[prospective gates](../design/features/m02-survey-l2/binding-set-validation.md)
and [source/frozen-path receipt](m02-l2-binding-set-evidence-2026-10-03.json)
form one complete review packet. Proposed numerical executions:0.

## Primary references: verified material versus unavailable claims

P-BS-01, Benson/McInnes/More, September2000,
[Argonne ANL/MCS-P768-0799](https://ftp.mcs.anl.gov/pub/tech_reports/reports/P768.pdf).
VERIFIED relevant full-text sections2/3, pages with zero-based
indices4..7. It distinguishes active and binding constraints, combines gradient
projection with reduced-face CG, and uses projected sufficient-decrease searches.
Its GPCG has additional phase/progress rules and CG accuracy changes. Those are
NOT automatically our hybrid or our frozen residual-based CG stopping rule.
No finite-termination theorem from GPCG is asserted for the proposed policy.

P-BS-02, Dimitri Bertsekas,
[MIT6.252 nonlinear programming lecture slides](https://web.mit.edu/6.252/www/LectureNotes/NLP_Slides.pdf).
VERIFIED relevant full-text pages74..76 (zero-based): feasible-direction gradient
projection, Armijo on its chord, and scaled positive-definite quadratic direction
subproblems. Pages79/80 warn that arbitrary nondiagonal two-metric scaling needs
additional care. Our D is fixed POSITIVE DIAGONAL and the box projection is also
its metric projection. Scalar-gradient and scaled derivations are distinguished;
the proof below is own mathematics, not copied wording or a hybrid theorem.

P-BS-03,
[versioned official PETSc3.12 GPCG source](https://www.mcs.anl.gov/petsc/petsc-3.12/src/tao/quadratic/impls/gpcg/gpcg.c.html).
VERIFIED source routines TaoSolve_GPCG and GPCGGradProjections (lines130..291)
read through their complete bodies. This reference has a projection phase,
reduced-system CG and its own progress/iteration defaults. It is comparative
source evidence, NOT a dependency, runtime switch or installed implementation.
No PETSc package/download/staging/parallel execution is proposed.

P-BS-04,
[official SimPEGv0.25.2 optimization.py](https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/simpeg/optimization.py).
VERIFIED remote and trusted installed source; pinned installed SHA256
0ac858cc310b32bb9aa59c78aaaa9c79b5f28438db52fb06ec73d976b63196a4.
Read installed exact activeSet/bindingSet, findSearchDirection, stoppersLS and
modifySearchDirection: inward active terms scale with free-step size, projected
trial slopes enter Armijo, and its loop evaluates at most20 trials for maxIterLS20.
No vendor source or environment edits are proposed. All28 existing pins remain.

P-BS-05, More/Toraldo1991,
[SIAM DOI10.1137/0801008](https://epubs.siam.org/doi/10.1137/0801008).
Original bibliographic verification is retained; new open returns an internal
access error. Full paper remains UNAVAILABLE here; no full-text/theorem audit
claim. No paywall bypass, third-party mirror or textbook download is used.

PDF screenshot requests for MIT74/75/76 and Argonne5/6 returned references, not
inspectable pixels in this tool result; Argonne7 timed out. Text/formula checks
above are actual; successful rendered-page review is NOT claimed. Exact in-memory
retrieval hashes/statuses are separately recorded, including any fetch failures.
No PDF/source is staged in the repository or used as a callable import path.

## Actual retained evidence and why the rule must change openly

Read the frozen [complete producer negative](../design/features/m02-survey-l2/evidence/additional-wide-start-negative-20261003.json)
and [chronology](../design/features/m02-survey-l2/evidence/approved-release-execution-20261003.json).
The six-start/two-bound/two-noise gate is23 PASS/1 FAIL, not the separate locked
24-family/condition matrix. Current complete regression is347 PASS/1 FAIL/14
attributed legacy skips; focused subset240 PASS/1 FAIL/zero skips. This is not a
whole-unit pass. Original d7 failures and MAIN's distinct16-start baseline remain.

For wide diagonal lower_reference, independent cell0 gradient is-0.08871593992245919
at its lower bound while free gradients are nonzero around1e-11. Thus A contains
a nonbinding coordinate even though the free problem is nearly stationary.
The accepted51-direction diagnostic remains entirely native CG, hitting wall_cap
and failing model/objective/prediction comparison. AS-B's exact-zero condition
correctly does NOT fire; that is a policy limitation, not a faulty zero comparison.

Proposed inference from P-BS-01 and the actual KKT violation: select a projected
feasible gradient direction whenever A minus B is nonempty, independent of free
residual magnitude. Only use current native face CG when A=B. This is an OWN
binding-set hybrid using standard published ingredients, not a literal complete
GPCG implementation or an unchanged-native-direction promise. The proposal
deliberately changes that promise, including nonzero/large/underflow free residuals.

## Own exact-arithmetic descent derivation

Let Phi be the SAME fixed unhalved quadratic, g its gradient and H its Hessian.
The positive volume-weighted smallness term makes H positive definite in exact arithmetic; finite
computed systems may still fail and are never repaired. Let h=diag(H)>0 and
D=diag(1/h), fixed for this partition; B_box is the unchanged finite Cartesian box.
The proposed projection candidate is z=P_box(q-Dg), d=z-q. This z uniquely solves
the diagonal strictly convex model over the box,

```text
min_z g^T(z-q) + 0.5 (z-q)^T D^-1 (z-q),  z in B_box.
(g+D^-1 d)^T(y-z) >= 0 for each y in B_box.
y=q gives g^T d <= -d^T D^-1 d < 0 if d != 0.
```

This holds because componentwise clipping equals projection in that diagonal
metric. It is not true for an arbitrary dense D with ordinary Euclidean clipping.
The finite box is convex: q+t*d remains feasible for0<=t<=1. With a strictly
inward gradient on an exactly active coordinate, its projected candidate moves
inward in exact arithmetic; a rounded float64 zero still fails, not converges.

On an A=B face, native CG has no inward active contribution. In exact arithmetic
with its fixed positive diagonal, zero initial step and positive-definite reduced
H_FF, each nonzero Galerkin CG approximation p_F has residual orthogonal to its
CG subspace. Hence g_F^T p_F=-p_F^T H_FF p_F<0. Its active components are zero.
Projection of q+t*p is unchanged for sufficiently small positive t because free
coordinates are strictly inside bounds. Therefore native face CG also has a
local feasible descent path. This proof does NOT exempt computed directions
from strict finite/descent checks or promise residual convergence in200 CG steps.

For either direction, smoothness and strict slope ensure an eventual Armijo
step in ideal arithmetic if unbounded shortening is allowed. Our LS20/iteration200/
wall120 limits and floating arithmetic may terminate first. No global convergence,
finite termination, optimal face discovery or operational-cap theorem for this
simplified hybrid is claimed. KKT and independent bounded optimum gates stay
required; small free-CG residual, rounded objective or good data fit is insufficient.

## Alternatives and review decision

Keeping cpu-2 truthfully reports its known failure but does not pass bounded
quality. A heuristic near-zero epsilon or rounded-step trigger treats a symptom;
this proposal instead uses the exact violated binding condition for any scale.
Literal published GPCG/PETSc would add phase loops/progress constants/CG accuracy
schedules and change more existing mapping. Pure scaled gradient projection is
a standard alternative with simpler global theory, but its200-step envelope has
not been tested; this task does not select it after looking at sealed scores.
No alternative solver, dense BVLS production fallback, jitter, start shift, cap
increase or vendor upgrade is offered. New policy/epoch requires FULL MAIN read
of the complete packet and explicit approval BEFORE tests or implementation.
