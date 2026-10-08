# Source-action interior three-pair IRLS design

New explicit runtime `m02-survey-irls-cpu-2`, policy
`safeguarded-irls-interior-threepair-log17-stage-1`; implementation
`gravity_irls_corrected.solve_partition`. Original gravity_irls.py and its
assertions/archives remain unchanged. Actual native fixed-inner solver remains
the original public source-bound linear export,CG200/20trials/certified physical
quadratic Armijo. Low-beta initialization failure is not relabelled accepted.

Let x=q-qref,A=WG,H0=A^T A plus the original quadratic directional prior,
v=beta*alpha_s*diag(W_s)^2 and epsilon>0. For a unique nonzero maximum j,
S=sqrt(x_j^2+epsilon^2),d_i=sqrt(x_i^2+epsilon^2),native scaled w_i=S/d_i.
Canonical R is HALF the actual native frozen-at-q gradient. Its Jacobian is
J=M+u e_j^T, M=H0+diag(v*S*epsilon^2/d_i^3),u_i=v_i*x_i*x_j/(d_i*S).
Construct M by native likelihood/directional actions directly, NOT by
subtracting nearly equal smallness Hessians. M is SPD for the admitted positive
smallness and epsilon; finite positive diagonal is required without a floor.
Solve Ma=-R,Mc=u with real pinned SciPyCG; p=a-c*a_j/(1+c_j). At max j the
smallness diagonal cancels correctly to v_j. Nonconservative R is an auxiliary
fixed-point residual, NOT a new globally minimized physical sparse potential.

Derivative branch guard precedes M/p construction: strict interior allcoordinates,
unique nonzero max. Record boundface active/free maximum,tie/null disabling.
No projected-merit derivative is claimed. Absolute canonical native1e-12 stops
proposal generation; no tiny anchors manufactured. At most3pairs perstage.
Denominator delta>0 and delta/(1+||c||inf)>=sqrt(eps64). Every actual CG true
residual<=1e-6||rhs||,actual callinfo/count/action/timing retained. Actual Jp
linear residual is recorded. Require R dot Jp<0. For strictly interior nonzero
q_trial=q+2^-trial*p, .5||Rtrial||^2-.5||R||^2-1e-4*alpha*(R dot Jp)<0.
At most20actual trial observations; rejected out-of-box trials record unavailable
merit,notzero. Failed CG/guard/LS/native solve ends the fit; no fallback.

After predictors, ONE official weight adoption and ONE actual native fixed
inner per scheduledstage. All21 must converge, original final3 terminalmodel
and adoptedweightchanges<=1e-6,plus finalcanonicalweightmismatch<=1e-6 and
original canonicalKKT absolute1e-12/normalized1e-5. One shared120s deadline
includes all actual work; caller whole1800s remains. Auxiliary/nonzero native
moves together<=200 and combined actualmodels<=201; atmost126CG/63anchors.

Ledger distinguishes initialization/auxiliary/native moves,scheduled weight
adoption,rejected trials and zero-step scheduled stationary observations.
Typed top-level pools use index references to avoid deeply nested calibration
records; no metadata/scalar/depth8/256MiB limits are increased. Retain solutions,
actual models/stage identities and sufficient original factors for deterministic
action/merit/canonical/physical replay WITHOUT calling any solver on import.
Original physical-E certificates must not be inferred from auxiliary merit.
Immutable result hash and source tuple supplement numerical replay,not replace it.

Independent tiny oracle assembles likelihood/prior and scaled-weight derivatives
from original admitted factors, compares analytic J/M actions and finite
differences on signed/nonzero-reference branches. Dense eigensolvers/LU occur
only in tests,never production. Original IR-C06 same fixture/assertions determines
positive correction; retained plain test stillfails. Full24/noise/refits/cap
resources and additive actual API/UI/course remain completion obligations.
