# Objective and nonlinear algorithm proposal

The planner contract is independent of nonlinear optimization. The latter is an
explicit proposal requiring applicability review before implementation, not a
claim of native GNCG convergence or an authorized private M02 import.

## Physical and statistical chain

Let rho=s_r q_r and chi=s_c q_c, with scales fixed in the supplied prior.
Real forward Jacobians J_r (mGal per kg/m³) and J_c (nT per SI) give
A_r=s_r J_r, A_c=s_c J_c. Gravity's physical chain includes exactly0.001
kg/m³-to-g/cm³; magnetic J is linear projected TMI, NOT scalar-magnitude anomaly.
Signed residual is prediction minus observation in each physical unit.
For an admitted partition I, W=diag(1/sigma_I), or solve L z=r with
L L^T=C[I,I]. Never use C inverse, or a full-data conditional prediction that
reads held-out observations. f_d,k=0.5||W_k(A_k q_k-d_k)||².
Report chi-square=2f_d and WRMS=sqrt(2f_d/N) separately for each modality.
No combined score is advertised as a scientific accuracy metric.

Let v_i be active volumes, V=sum(v_i). Quadratic model penalty is
R_k=0.5 sum_i(v_i/V)(q_i-qref_i)² +
0.5 sum_{axis,active-neighbor pairs ij}(area_ij*distance_ij/V)
*[length_axis*(delta_q_j-delta_q_i)/distance_ij]².
Pairs include only two active cells; no inactive/boundary zero extension.
delta_q=q-qref. No depth/sensitivity weights are inferred. They would be a
separate explicit science-policy amendment, not a hidden numerical repair.

## Actual SimPEG coupling, not the plotted diagnostic

Use the genuine pinned SimPEG CrossGradient (two active Wires, no custom weights).
G is the regularization mesh's cell-centre-to-active-face gradient and A its
face-to-cell average. B=diag(sqrt(v))*A. Let a=G q_r, b=G q_c, p=B(a²),
t=B(b²), h=B(a*b). The **actual optimized** scalar is

    C(q) = (L_c^4/V) * sum_i [p_i*t_i - h_i²].

Squared/product quantities are averaged BEFORE the Gram determinant; this is
not sum_i v_i |(A_vec a)_i cross (A_vec b)_i|². The latter cell-centre diagnostic
is exported under a different name and never substituted in the objective.
L_c is the supplied positive coupling length; L_c^4/V renders C dimensionless.
No initial-cross/truth/data-fit normalization or small-value epsilon is inserted.
Public actual regmesh operators must be independently assembled/audited for
nonuniform meshes and active holes. Only volume weighting is used: the pinned
implementation constructs B directly; generic custom-weight API documentation
does not establish that arbitrary user weights affect this implementation.

Gradient (c=L_c^4/V):

    g_r = 2c G^T [a*(B^T t) - b*(B^T h)]
    g_c = 2c G^T [b*(B^T p) - a*(B^T h)].

Compare with actual CrossGradient.deriv plus independent Torch autograd and three
central finite-difference steps. Exact Hessian finite differences use
approx_hessian=False. The positive-semidefinite approximation used for search is

    H_C = 2c diag(G,G)^T [[diag(B^T t),-diag(B^T h)],
                         [-diag(B^T h),diag(B^T p)]] diag(G,G).

Each face's2x2 block is PSD by nonnegative averaging/Cauchy-Schwarz. This is a
search approximation, NOT the exact Hessian of a nonconvex quartic objective;
do not test approximate Hv against exact gradient finite differences. Verify
symmetry/PSD and its agreement with official approx_hessian=True separately.
Near-zero negative scalar from floating-point cancellation is a numerical
diagnostic/failure to investigate, not silently clipped objective values.

Full candidate objective:

    F=f_d,r + f_d,c + beta_r R_r + beta_c R_c + lambda C.

Physical gradient transforms back by1/s_r,1/s_c; physical Hessian sandwiches
the scale-inverse diagonal. Independent directional tests exercise this chain.

## Two real baselines and leakage-safe selection

For EACH modality independently optimize the eight beta candidates
(0.0001,0.001,0.01,0.1,1,10,100,1000), using only that modality's train rows,
original submitted bounds/reference/start and its regularizer. Candidate failures
remain records, never omitted. Select lowest validation WRMS among stationary
finite feasible candidates, exact ties to larger beta then declared order.
Freeze baseline hashes and selected betas. No model-truth or sealed arrays enter.
The lambda=0 comparison consists of those TWO actual independently optimized
models/traces; it is not a copied historical model or jointly labelled refit.

For fixed selected beta_r/beta_c, solve lambda candidates(0.001,0.01,0.1,1,10)
from both submitted start and baseline concatenation; include the exact baseline
pair as lambda=0 without a fabricated solve. Record every attempted candidate.
Select by mean of the two validation squared WRMS values, provided EACH
validation WRMS<=1.05 times its own baseline; ties prefer smaller lambda then
baseline start. This is a selection rule, not a combined science score. If no
positive-lambda candidate is eligible, retain the uncoupled result and explicitly
report `no_validated_coupling_benefit`. Refit is NOT performed on validation/test;
selection freezes train-only models, preserving strict predictive comparisons.
Report each modality's sealed predictions only after frozen selection is bound.

## Proposed bounded search and exact stopping

Public reusable optimizer applicability is unresolved, including its precision
predicate for a nonquadratic objective. Proposed M11 policy is projected
Gauss-Newton with a binding-aware projected-gradient chord, NOT unmodified
SimPEG native GNCG. Exact active/binding signs use the CURRENT total gradient.
At each state evaluate finite F,g and constrained KKT infinity norm: lower-bound
components min(g,0), upper-bound max(g,0), interior g. Stationary iff
||g_KKT||inf/max(1,||g_initial||inf)<=1e-5 with exact feasible bounds.
No small CG residual, fit, step or objective-change alone declares convergence.

If any exactly active entry is nonbinding, use
p=clip(q-D^-1 g,lower,upper)-q with fixed positive D equal the initial diagonal
data+beta-regularization+lambda approximate Hessian, rejecting invalid D. The
projection inequality gives g^T p<=-p^T D p in exact arithmetic. Otherwise use
the native face-restricted CG direction for the PSD approximate total Hessian.
CG failure does NOT invoke an oracle/BVLS, jitter, new beta or different solver.
Both branches require finite candidate displacement and strictly negative
actual g^T(q_trial-q), not merely negative unprojected direction slope.
Projected Armijo uses F_trial<=F+1e-4*g^T(q_trial-q), starting alpha1 and halving,
at most30 trials. Reject no-op/overflow/non-descent; no rounded-zero trigger.
For nonlinear objective comparisons a quadratic-certified-delta implementation
is not reusable without a mathematically applicable tested extension.

Limits:250 accepted iterations per solve,512 CG steps, relative CG residual1e-6,
30 LS trials, total pipeline deadline1800 s. Exhaustion is `nonconverged`, never
success; all candidates remain attributable. Exact test controls must determine
whether these limits suffice; no tuning on failed sealed/oracle models.
Trace every state: physical models, five objective terms, feasible KKT,
branch/binding counts, CG actual residual or null when unused, LS trials, alpha,
actual slope and model hashes. Seal selection by hashes. Local minima remain
possible; two starts do not prove a global optimum or geological identifiability.
