# Bounded reference and nonlinear applicability

Primary audit2026-10-04. This supplements the initial research without changing
the implemented native objective, its caps/weights/tolerances or the frozen
nonlinear proposal. Source inspection is not optimizer execution or acceptance.

## Independent tiny linear reference

[SciPy1.15.2 lsq_linear](https://docs.scipy.org/doc/scipy-1.15.2/reference/generated/scipy.optimize.lsq_linear.html)
supports a dense active-set BVLS reference for bounded linear least squares.
Use method=bvls and lsq_solver=exact explicitly, not a default-method or LSMR
switch. The public wrapper reports success for positive status, including a
relative-cost stop. Thus success alone cannot certify the required projected
KKT or numerical comparator gates. The public wrapper's feasible unconstrained
solution shortcut and the bounded branch must both retain their actual statuses.

The full [versioned BVLS source](https://github.com/scipy/scipy/blob/v1.15.2/scipy/optimize/_lsq/bvls.py)
and [public wrapper source](https://github.com/scipy/scipy/blob/v1.15.2/scipy/optimize/_lsq/lsq_linear.py)
were checked against the actually loaded installed functions. BVLS initializes
from the unconstrained solution, moves violating variables to bounds and releases
active variables by gradient signs. It can stop on relative cost before its next
KKT test. Initialization iterations are added to its nominal max_iter allowance;
that parameter is not an absolute whole-pipeline work/deadline bound.

Actual trusted loaded defining-file SHA256:

- BVLS87d6d88776acb4846f32d306821b441a91b97c3b21ef848c45b9a01771cdf183.
- lsq_linear866a691914b304f8788214ff34441d325ed3294c15367fbd2cd45ad60944fa15.

These are external installed-source reads, not imports from caller-provided
paths or permission to change/install a runtime. They are additional reference
pins; the earlier structural/forward receipts are not relabelled with them.

For modality k independently construct the tiny oracle from Choclo J, explicitly
enumerated physical R, and separate triangular whitening. In normalized units,

    Aaug = [ W * (s_k J_k) ; sqrt(beta_k) R_k ]
    baug = [ W * d_k       ; sqrt(beta_k) R_k qref_k ].

Here R_k^T R_k is exactly the smallness/face penalty Hessian in algorithms.md;
the objective is0.5||Aaug q-baug||². Bounds are physical lower/upper divided by
the same fixed positive scale. Positive beta and positive volume smallness make
this tiny augmented problem strictly convex even if the data matrix is rank
deficient; this does not resolve geological nonuniqueness of the measurements.

Prospective comparator calls use tol1e-12,max_iter250 and report actual nit,
status/cost/optimality/model/bounds plus an independently recomputed projected
gradient. Oracle initialization semantics remain explicit. Compare production
baseline against the frozen objective/model/prediction/KKT gates in validation.md,
not just SciPy's success. This dense oracle is test-only, never a production
fallback, candidate kernel, exported result or substitute for two real baseline
solves. No reference optimum or whole inverse acceptance has been executed here.

## Published face release does not prove this quartic solve

[Benson, McInnes and More, ANL/MCS-P768](https://ftp.mcs.anl.gov/pub/tech_reports/reports/P768.pdf)
sections2/3 were read. They distinguish active from binding coordinates and use
projected-gradient identification plus reduced-face CG and projected decrease.
Their problem and convergence statements concern convex quadratic objectives.
Their initial search-length choice and CG progress termination differ from this
feature's fixed initial diagonal and native CG residual criterion. This proposal
is not a reproduction of their GPCG method or a transferred global theorem.
The initially attempted P157 PDF URL was unavailable; P768 is the accessible
source actually inspected, not a relabelled retrieval.

Own local reasoning:for a feasible q, fixed positive diagonal D and
p=clip(q-D^-1 g,l,u)-q, projection optimality with comparison point q gives

    (D p + g)^T (-p) >= 0,
    hence g^T p <= -p^T D p.

A nonzero chord is therefore a descent direction in exact arithmetic. Smooth F
on finite bounds admits a sufficiently small decrease step in exact arithmetic;
this does not guarantee the frozen30 finite-precision trials succeed. Both chord
and CG branches must check their actual projected displacement, strict finite
negative slope and actual F, rejecting rounded no-ops/non-descent/overflow. No
ordinary CG or line-search failure enables a different solver or weight.

The structural Gram term is generally quartic and jointly nonconvex despite
being quadratic in either fixed property. A PSD approximate search Hessian is
not the exact Hessian or a global-optimum certificate. The M02 quadratic-delta
precision predicate cannot be applied to this quartic term without an applicable
new proof and tests. Independent nonlinear applicability review and all frozen
baseline/start/sealed/resource/adverse controls remain necessary before candidate
integration. No code, pipeline gate, convergence or field claim follows from
this primary-source supplement.
