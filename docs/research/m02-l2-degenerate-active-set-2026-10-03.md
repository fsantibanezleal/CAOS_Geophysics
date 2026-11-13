# Local L2 degenerate active-set research

Date: 2026-10-03. Scope: read-only source/algebra investigation and a proposed
[additive design amendment](../design/features/m02-survey-l2/active-set-amendment.md).
No changed optimizer has been implemented or accepted. The original seven-file
SDD, metadata approval and dated execution receipts remain unchanged.

## Verified primary evidence and access limits

P-AS-01. [SimPEG 0.25.2 optimizer source](https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/simpeg/optimization.py)
and [versioned ProjectedGNCG API](https://docs.simpeg.xyz/v0.25.2/content/api/generated/simpeg.optimization.ProjectedGNCG.html)
are VERIFIED. Installed optimization.py SHA256 is
`0ac858cc310b32bb9aa59c78aaaa9c79b5f28438db52fb06ec73d976b63196a4`,
the original reviewed source pin. The source computes CG on free coordinates,
then scales an inward active contribution by the maximum free CG step. A zero
free residual gives zero CG step and a zero divisor in the relative diagnostic.
An all-active state is therefore not automatically a bound-constrained optimum.
Installed lines1630..1705 were read, not inferred from a different release.

P-AS-02. [Pinned line-search source](https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/simpeg/optimization.py)
is VERIFIED: projected trials, sufficient decrease using the actual trial
displacement, geometric shortening and a finite trial cap. Removing only the
producer stop cannot supply a missing search direction. No vendor patch or new
runtime was attempted.

P-AS-03. Benson, McInnes and More, [Argonne report ANL/MCS-P768-0799](https://ftp.mcs.anl.gov/pub/tech_reports/reports/P768.pdf),
September2000, is VERIFIED through the full author/institution PDF text.
Sections2/3 distinguish active from binding constraints and
use gradient projection to find a face, then CG to search it. A projected
sufficient-decrease search globalizes those steps. This motivates a release
direction; it does NOT prove our proposed limited hybrid equals GPCG or inherits
its global convergence. [Author arXiv record](https://arxiv.org/abs/cs/0101018)
is a separate January2001 submission, not a new runtime or performance result.
Earlier PDF screenshots on pages2/3 failed. Page5 requests returned a reference,
but pixels were not inspected here; a later URL-based retry failed content-type
resolution. No successful visual rendering/review is claimed.

P-AS-04. More and Toraldo,1991, SIAM Journal on Optimization1(1),93-113,
[DOI10.1137/0801008](https://epubs.siam.org/doi/10.1137/0801008): publisher
title/bibliographic landing was available, but full text and subsequent browser
find/open access were unavailable. Full-paper verification and its theorem
application to this hybrid are NOT claimed. Argonne's accessible account is
the primary source actually read for the active/binding distinction.

P-AS-05. The installed code_utils.py, SHA256
`5f69a2cddfc8cbafa6b723466c7a46e20936efb8c37c3797591b2c262322e03b`,
was read at print_line: None prints blank, without passing to the formatter.
Thus not-performed CG diagnostics need not be invented as zero residuals or
require a numerical/printer vendor patch. All28 original source pins remain
required at any later acceptance; these two reads are not a transitive audit.

## Evidence boundary

MAIN owns the separate full report
`docs/validation/gravity-l2-bounded-independent-review-2026-10-03.md` on its
bounded-evidence branch. It is not copied, overwritten or authored here.
Its four new controls at d7c6670 contain two genuine tight-bound failures,
separate from MAIN's168-test and12-metadata passes. The actual failed private
record SHA256 is
`f118d046a6be3929d9432a921c728cc5a6295bd265cfc444dfecaf8e56f774da`;
its trusted independently authored fixture SHA256 is
`dc4a6da238d84d9fe65592cd818961ac57ddad6f78471ecdf1e16080d35de070`.
Those bytes were inspected read-only; this dossier does not republish MAIN's
report or change its attribution or verdict.

The [new producer algebraic diagnostic](../design/features/m02-survey-l2/evidence/degenerate-direction-diagnostic-20261003.json)
uses that explicitly pinned trusted geometry/algebra to examine ONE prospective
direction at each failed accepted state. The old native solve still returns
nonconverged/zero_free_direction. Only the proposed endpoint and an independent
quadratic sufficient-decrease calculation are evaluated outside the solver.
Accepted optimizer release steps: ZERO. No amended optimizer, final optimum,
sealed selection,24-case/resource or field acceptance is claimed.

## Own derivation: feasible diagonal projected direction

Let Phi(q) be the existing unhalved fixed quadratic in g/cc, with genuine
gradient g. Let h be its finite strictly positive Hessian diagonal, D=diag(1/h),
and B the unchanged supplied box. Set z=P_B(q-Dg), d=z-q. Since D is positive
diagonal and B is a Cartesian box, componentwise clipping is also the projection
in the D^-1 metric. Its variational inequality is

```text
(D^-1(z-q) + g)^T (y-z) >= 0  for every y in B.
Set y=q:  g^T d <= -d^T D^-1 d < 0 whenever d != 0.
```

This is an own local descent derivation, not a quoted theorem about our code.
q+t*d is feasible for0<=t<=1. For a smooth fixed quadratic, a sufficiently
small positive t meets Armijo in exact arithmetic; this does NOT promise that
twenty float64 trials or200 accepted steps suffice. Finite arithmetic can
overflow, round away a step or fail strict descent and must remain a failure.
No altered bound, seed, initial model, beta, background or data is needed.

At the two failed vertices the diagnostic computed slopes
-25.284140086043962 and-31.662344944176827, versus certificate right sides
-1.749103193941614 and-2.1824705557838384. Both proposed endpoints are feasible
and the full algebraic trial meets the original Armijo inequality. These are
one-direction certificates, NOT optimizer success; they justify review of the
narrow exception rather than changing a gate to make the old failure disappear.

## Alternatives and decision still requiring approval

Retaining truthful nonconvergence preserves the original policy but does not
complete the bounded unit. Merely bypassing its zero-free guard is insufficient
by P-AS-01. Dense BVLS is an independent tiny oracle, not a production substitute.
A vendor upgrade, broad switch to projected gradient/GPCG, jittered start or
new scaling parameter would change more than the proposed exception and is not
authorized. The amendment instead specifies a strict zero-free-residual release
with the already-declared Hessian diagonal and official line search. It remains
PROPOSED until MAIN reads the entire amendment and explicitly approves it.
