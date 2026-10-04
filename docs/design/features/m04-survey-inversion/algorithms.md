# Exact magnetic workflow algorithms and dimensional semantics

All policies below are proposed frozen definitions, not performed experiments.
No threshold is a field-data noise estimate or an override of accepted M02
convergence. Read the [closed types](contracts.md) before applying these rules.

## 1. Geometry-only seal

Use usable original rows, declared source groups and local horizontal ENU.
Block index=(floor(E/block_width_E),floor(N/block_width_N)), anchored at physical
zero, never a data-dependent origin. Union any two rows sharing a source group
OR block. Connected components are indivisible units, including transitive
edges; tie/source groups can merge blocks, never break a flight at a boundary.
A component ID is SHA256 of sorted original row IDs joined by LF; acquisition
IDs cannot contain LF. Sort units by SHA256 of ASCII
"magnetic-geometry-seal-1|104729|"+component_id, with ID as tie break.
Require>=12 nonempty units. Outer is first ceil(U/5) units. Remaining units in
that sorted order are assigned validation fold position modulo3. Source/tie
identity stays indivisible; do not rotate the seed to get an attractive split.

For each fold, fitting rows are development rows outside that validation fold,
excluding every row at horizontal Euclidean distance<=buffer_m from ANY
validation or outer row. Geometry comparisons use squared distances in m^2;
no dimensionless reuse of a coordinate tolerance. Equality is excluded.
Final development refit excludes rows within buffer of outer rows too.
Only declared usable rows participate; outer memberships never change.
Each fold requires fit>=40, validation>=10 rows, at least2 distinct E and N
coordinates and matrix rank3 of centered [1,E,N] (SVD relative cutoff1e-12).
Center E and N only; retain the constant column1. Reject exact duplicate usable
ENU coordinates before union. No tolerance merges physically distinct stations.
Outer requires>=10 rows and same geometric rank; final development>=50.
Failure preserves all row inventories and says insufficient_partition_geometry.
No buffer relaxation, amplitude-based QC, silent decimation or group thinning.
Truth/noise/observations cannot enter seal or minima tests.

Frozen independent acquisition S2:12 flights l=0..11,24 samples s=0..23;
row ID=S2-L{l:02d}-S{s:02d}, group=S2-L{l:02d};
E=-200+80*s m, N=600*l m, U=120+10*(s modulo3) m.
Block widths=(250,500)m, buffer=200m, seed104729.
Exactly12 indivisible units, outer3 flights/72 rows, development9/216;
each of3 folds validation3/72, fit6/144, buffered0; final refit216.
These counts follow spacing before choosing a truth body or observation.
The geometry-only fixture must assert counts, IDs and unit/partition hashes
before magnetic generation. Alternative tie-overlap fixtures intentionally
merge too many units and must fail, not silently reassign lines.

## 2. Physical operator and quantity-specific Jacobian

Keep P04 unchanged. The inverse constructs the same public vendor
Simulation3DIntegral scalar, components bx/by/bz, IdentityMap(A), actual active
cells, Geoana RAM float64, n_processes=1, is_amplitude_data=False.
Validate TensorMesh ordering/representability/exterior receivers and native
field vectors through the P04 scientific definitions; no local prism formula.
Obtain actual G shape(3M,A), receiver-major ENU, nT per unit SI chi.
The public vendor getJ at chi with IdentityMap must agree with G.
Use q=chi/.01 and q_ref=reference_si/.01. J_b,q=.01*G.

Let b=reshape(G chi,(M,3)), t=B0+b, T=norm(t).
Secondary ENU: H=b in original receiver/component order.
Linear TMI: H=f dot b and J_q=.01*f dot G.
Exact scalar anomaly: H=(2 B0 dot b+b dot b)/(T+F);
J_q=.01*(t/T) dot G for each receiver.
Reject if T/F<=1e-8 (undefined/ill-conditioned direction) or any derived
value becomes nonfinite, rather than choosing f or jittering t.
This guard is a declared numerical domain restriction, not geological knowledge.
The zero-secondary model has T=F and derivative f, so zero starts are legal.
The forward-only P04 magnitude domain is not narrowed by this inverse-only guard.
No exact lane using vendor secondary-amplitude mode, no constant linear
projection Jacobian inside a nonlinear fit, no substitution of |b|.

## 3. Errors, residuals, sensitivity and units

Fit error r=H(q)-d in nT, flattened original receiver-major. SD whitening
W=diag(1/sigma) nT^-1. Covariance C=L L^T in nT^2, whiten via solves L^-1
without forming an inverse or extracting diag(W). Each fold/evaluation obtains
the principal covariance for its own rows/components and its own Cholesky.
Correlation across a split remains explicitly declared; no independence claim.

phi_d=||W r||^2 (dimensionless), g_d=2 J_q^T W^T W r,
GN H_d=2 J_q^T W^T W J_q. Exact total-magnitude uses GN, not an assertion
that its ignored second derivatives vanish. Export residual is d-H, opposite
to optimizer r. Component count D, not station count N, divides whitened RMS.

Preconditioner uses diagonal of the complete GN+regularizer quadratic:
2*column_norms(W J_q)^2+2*beta*diag(R^T R), with the accepted M02 policy for
zero/scale handling. No UpdateSensitivityWeights/getJtJdiag diagonal shortcut
on full covariance. Sensitivity displayed in nT/SI uses unscaled physical
J_chi; whitened sensitivity is labelled 1/SI; q never becomes a displayed
susceptibility unit.

## 4. Physical regularizer and beta

Use actual SimPEG WeightedLeastSquares, IdentityMap(A), explicit q_ref,
reference_model_in_smooth=True, alpha_s=1, alpha_j=ell_j^2 m^2,
alpha_xx=alpha_yy=alpha_zz=0. Add constant cell weights 1/V with
V=sum(active cell volumes) m^3, not per-cell inverse volumes.
Do not use vendor length_scale_* as literal metre lengths.
For delta=q-q_ref:

phi_2=sum(v_i/V*delta_i^2)
       +sum_j ell_j^2 * sum_faces(avg_j(v)/V*(D_j delta)^2).

D_j is the actual active-face physical difference per metre, checked against
independent nonuniform cell-center distances. Only faces admitted by actual
RegularizationMesh active-face convention participate; compare its sparse
projection/averaging explicitly with the independent topology oracle.
For the explicitly supplied active mask, retain only interior faces with both
adjacent cells active. Exclude exterior and active/inactive interfaces. Each
retained difference is (q_right-q_left)/(0.5*(h_left+h_right)) along that axis;
its averaged volume is0.5*(v_left+v_right). No derivative bridges an inactive
hole. Match actual RegularizationMesh projections/averaging to this independent
definition; mismatch stops rather than alters the oracle.

phi=phi_d+beta*phi_2, beta dimensionless because data are whitened and the
q/volume/length normalization makes phi_2 dimensionless. Numerical beta is
not portable to chi-unscaled, different SD, different q scale or a gravity
objective. The model scale is fixed, recorded and never tuned from observed
amplitude. Bounds in q are supplied SI bounds divided by .01.

## 5. Accepted M02 mathematical composition boundary

Required adapter input is a trusted internal problem, never user callbacks:
q lower/upper/start, value(q), gradient(q), GN_hessian_action(q,v),
preconditioner(q), immutable operand/source identity, checked budgets.
Required result: owned q, terminal reason, real histories, projected-gradient/
bound/KKT certificate and counts. The accepted core must support arbitrary
physical model scaling, frozen full-covariance quadratic operands, near-zero
binding-set release and precision-certified stopping without gravity construction.

There is currently NO accepted magnetic-compatible export/source pin.
The gravity-specific private _build_problem path cannot serve this protocol.
Before source implementation, M02 owner/reviewer must name the actual accepted
export/pin and map EVERY input, output, stop, precision and budget to this
boundary in a normative amendment. No placeholder function, copied solver,
SciPy production replacement, vendor-default shortcut or guessed export name.

For linear fits, certification must preserve the accepted fixed native-operand
quadratic and bound semantics. For exact-magnitude fits, accepted nonlinear GN
and projected actual-displacement line-search handling are additionally
required; acceptance of the linear core alone does not prove this.
Magnetic independent oracles remain mandatory even after accepted-core binding.
An unavailable binding returns dependency error before engine construction.

## 6. L2 and sparse policies

L2: same explicit start/reference/bounds for each fold and beta, no mesh/field
search. Use accepted optimizer stops and certification, never manufacture
convergence from cap/time termination or small objective change.

Sparse: actual SimPEG Sparse with norms=[1,2,2,2], gradient_type="components",
irls_scaled=False, explicit alpha and volume normalization as above.
Call actual Sparse.update_weights at the recorded current model. Application
outer policy, NOT default UpdateIRLS/BetaSchedule, uses epsilon_q sequence
[.1,.05,.025,.0125,.00625,.003125,.0015625,.001].
Smoothness epsilon_j=epsilon_q/ell_j in m^-1, positive even though p=2 weights
are1. Smallness weights r_i=1/sqrt(delta_i^2+epsilon_q^2);
smoothness weights exactly1. At null delta, r_i=1/epsilon_q finite.
Beta stays fixed at that candidate's value, no hidden lambda/max rescaling.

For each epsilon, maximum20 reweight-and-solve outer iterations. Each inner
surrogate must converge under the accepted core. After solving, recompute true
fixed-epsilon objective

psi_epsilon=2 sum_i(v_i/V*(sqrt(delta_i^2+epsilon^2)-epsilon))
            +sum_j ell_j^2 sum_faces(avg_j(v)/V*(D_j delta)^2).

The factor2 makes its smallness gradient 2*(v/V)*delta/sqrt(delta^2+epsilon^2),
equal to the surrogate gradient when weights are refreshed at that same model.
The surrogate quadratic omits a model-independent touching constant; its raw
value is NOT the true sparse objective. Persist both separately labelled.
Evaluate sqrt(delta^2+epsilon^2)-epsilon through the cancellation-resistant
equivalent delta^2/(sqrt(delta^2+epsilon^2)+epsilon). An independently converted
Decimal80 direct square-root difference verifies tiny nonzero values; do not
drop small positive regularization terms or rely on Windows longdouble.
Require nonincrease of true fixed-epsilon phi_d+beta*psi within
64*eps_float64*max(1,abs(previous),abs(current)); precision uncertainty beyond
that bound triggers failure/certification, not relaxed thresholds.
No monotonicity claim across changing epsilons.

Advance epsilon only after relative model change
||q_new-q_old||inf/max(1,||q_new||inf)<=1e-5 AND independent projected-gradient
criterion <=1e-7*max(1,||g_initial_at_this_epsilon||inf), plus accepted core
certificate. Core stopping may be stricter; these tests cannot waive it.
Always reach final epsilon .001. Exhaust20 at any stage -> failed candidate.
The final-epsilon gradient is recalculated with refreshed weights; stale
surrogate KKT or changing-beta plateau cannot certify it. No p=0 unsupported
claims, no posterior interval or global nonlinear minimum assertion.

## 7. Selection, refit and sealed evaluation

Each of16 beta/penalty candidates gets3 fits. Score each fold by phi_d/D on
validation-only principal noise; aggregate as sum(phi_d)/sum(D), not average
row RMS. A missing/nonconverged fold makes the entire candidate failed.
Select lowest score; values within64eps*max(1,abs(score_a),abs(score_b))
tie by l2 before sparse, then larger beta, then fixed candidate ID.
No field-direction or remanence fitting in this candidate list.

Refit selected candidate on buffered final development rows. Retain the L2
baseline at selected beta on identical development rows. Any refit failure
fails the workflow, no second-best fallback. Freeze model/config hash BEFORE
revealing outer observations. Predict all usable original rows using the same
operator/quantity; evaluation selects only its declared rows and principal noise.
Development and outer phi_d, raw per-component RMS and normalized RMS retained.
No outer-dependent mask, threshold, refit or model selection.
A previously seen outer survey is labelled reused evaluation, not a new holdout.

## 8. Deterministic diagnostics, not statistical certainty

For tiny linear controls form local fixed-objective
A=W J_q and R. Model-resolution matrix
(A^T A+beta R^T R)^-1 A^T A is dimensionless local regularized resolution.
Use linear solves, not inverse. Report singular values, diagonal, selected
point-spread columns and regularization dependence. At active bounds/nonlinear
or sparse fits, the local free-set/GN/final-frozen-weight qualification is
mandatory; it is not posterior covariance or calibrated confidence.

Large ordinary jobs compute at most8 explicitly selected active columns,
selected by evenly spaced active index floor(k*(A-1)/7), unique when A<8.
No stochastic trace/rank claim, no dense resolution above A=64.
Signed residual spectrum only for actual uniformly spaced contiguous line
samples: demean residual percomponent for VIEW ONLY, Hann window, rfft,
periodogram |FFT(w*r)|^2/(fs*sum(w^2)), fs=1/delta_s in cycles/m;
units nT^2*m, one-sided interior bins multiplied2, DC/Nyquist not.
Irregular spacing/gaps -> unavailable with reason, not hidden resampling.
Primary S2 z varies but E spacing80 and fixedN admits projected horizontal
along-line spectrum; clearly label horizontal distance, not 3D arc length.
