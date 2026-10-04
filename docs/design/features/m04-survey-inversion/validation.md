# Independent validation and complete acceptance matrix

This is the complete acceptance matrix. Ordinary input/geometry gates verify
their implemented foundation only; numerical/full-generation/integration gates
remain required and are not satisfied by geometry roundtrip. P04 frozen scientific tolerances
remain unchanged. A parser, physical operator or figure pass cannot satisfy
inverse, field, durability, online or product acceptance.

## Actual operators and independent physics

Retain intrinsic component/sign/order/Choclo/16-24-32 quadrature/tiny scalar gates.
The independent physical oracle uses actual Choclo component functions and
physical magnetization M=chi*B0(T)/mu0. Mathematical unit-chi=1 is allowed ONLY
in that oracle to define nT/SI Jacobian columns; production accepts chi<=.1.
Decimal80 from_float direct sqrt-F remains the independent tiny scalar norm
oracle, not Windows longdouble or the candidate rationalized expression.

New exact inverse Jacobian controls: cardinal+oblique directions, asymmetric
off-origin nonuniform mesh, mixed active holes and nonzero chi. Independent
Choclo total norm differentiated with centered steps chi=1e-6,5e-7,2.5e-7,
using only interior production bounds. Require consecutive derivative estimates
converge at rtol2e-6/atol1e-6 nT/SI, then analytic candidate agrees at the same
fixed tolerance. At chi=0 use a permitted one-sided three-point derivative and
confirm its limit uses native B0/norm(B0); do not assume a rounded B0 norm equals
the separately retained F or reset its tiny baseline. Check adjoint
u dot (J v)=v dot (J^T u) with relative error<=1e-12 or absolute1e-10 nT/SI;
freeze vectors independently of the candidate. Zero-norm/guard-domain negatives
must fail without fallback. These proposed derivative tolerances do not weaken
the stricter P04 component or ordinary magnitude comparisons.

## Objective, covariance and optimizer oracles

Tiny well-conditioned linear controls A<=8, D>=24, explicit regularizer;
independent physical G_chi from Choclo, stencils from pairwise center distances
and active faces, exact SD/full SPD covariance. Compare vendor objective/gradient/
GN at rtol1e-10, atol1e-10 dimensionless (objective),1e-8 (gradient),1e-8
(Hessian actions). Validate q=.01 scaling separately and factors of two.
Cholesky oracle independently checks ||W r||^2=r^T C^-1 r and weighted
column norms including off-diagonal covariance; at rtol1e-12/atol1e-10.
No covariance correction or user-uncertainty estimator in this test.

Independent SciPy1.15.2 lsq_linear(method="bvls",tol=1e-12,max_iter=10000)
on stacked [W J_q; sqrt(beta)*R], RHS [W d;sqrt(beta)*R*q_ref],
matching production bounds, not a production fallback.
Compare model infinity error<=1e-6 q, relative objective gap<=1e-8,
prediction RMS discrepancy<=1e-6 nT and independent bound/KKT residual
<=1e-7*max(1,||g_initial||inf).
Use interior, lower/upper binding, mixed release, exact null, tiny nonzero
gradient and different legal starts. Preserve any M02 known failures; no
ordinary-zero special case passing may hide near-zero failure.
For ill-conditioned controls, agreement/model tolerance alone is insufficient:
also compare accepted native-operand stopping certificate against an independent
Decimal80 quadratic calculation. No accepted M02 certificate is invented here.

For nonlinear exact-magnitude small controls, centered derivative/adjoint and
GN-direction checks are independent; compare a separate SciPy bounded
least_squares using Choclo physical predictions with at least3 frozen starts.
Report all objective/local-KKT/prediction differences; no global-minimum theorem.
If alternative starts give distinct acceptable models, show ambiguity rather
than choose truth. The accepted nonlinear core boundary is still a prerequisite.

Sparse independent oracle directly evaluates psi_epsilon and its analytic
gradient. Test all8 epsilons, actual vendor unscaled weights, true-surrogate
gradient equality at weight refresh, positive null behavior, reference notzero,
nonuniform volume and lengths. Each fixed-epsilon descent/certificate must pass;
final-epsilon independent projected gradient <=1e-7 scaled initial criterion.
A stall, cap or nonzero final KKT is FAIL, never an IRLS success badge.
Tiny true-smallness control delta=+/-1e-10,epsilon=.1 requires a strictly
positive value matching independent Decimal80 direct sqrt difference at
relative error<=2e-8 without an absolute floor; delta=0 is exactly zero.

## Frozen acquisition and six scientific regimes

Use original S2 geometry defined in algorithms BEFORE any source values.
Inversion mesh origin=(-400,-300,-1800)m, hx=11*[200],hy=12*[600],
hz=[150,250,400,1000], all528 cells active. Prior lower0, upper.1,
start0, reference0, scale.01, lengths=(400,1200,600)m.
No truth cell-centers are reused by inversion. Truth consists of independent
off-grid rectangular Choclo bodies specified by six bounds and magnetization;
physical χ ranges in ordinary induced cases [.002,.025]. All heights, times,
noise and sources here are AUTHORED SYNTHETIC, never field acquisition metadata.

| Regime | Frozen independent construction | Scientific question |
| --- | --- | --- |
| S2-A offset heterogeneous induced | body1 E[310,770],N[1700,2570],U[-510,-130],chi .012; body2 E[960,1430],N[3980,4830],U[-980,-420],chi .021; F50000,I37,D-73 | Prediction on disjoint flights and regularization ambiguity |
| S2-B compact susceptibility contrast | same body1 chi .025, body2 chi .003 | Does sparse smallness change heldout fit/compactness versus L2? |
| S2-C depth/extent ambiguity | body1 U[-1050,-470],chi .021, body2 unchanged | Distinguish predictive fit from unique depth recovery |
| S2-D remanent negative | A induced plus body1 remanent M=(8,-5.5,2.3) A/m | Induced-only residual/systematic mismatch, no classifier |
| S2-E wrong-field negative | A observations generated I37,D-73; inverse declared I-35,D-100 | Field direction cannot be silently estimated or cured |
| S2-F null/coverage negative | zero bodies; separate fixture with flights0..3 only | Null starts valid; deficient partitions reject before values |

For A-E use deterministic authored conditional Gaussian SD.5nT every component,
noise generated NumPy PCG64 seed20261004, raw generator/seed/source version
recorded; vectors and scalar modes are separate measurements with respective
noise, not identical likelihoods. F null uses zero observations with SD.5,
an explicitly zero-observation control with a declared conditional test covariance.
In the exact scalar lane retain the separate native-vector clean baseline
norm(B0)-F, which may be nonzero; this zero-observation test does not assert
exact identity between rounded-vector norm and F and does not change P04.
Physical truth fields from Choclo, scalar exact values from Decimal80 direct
norm, no SimPEG inverse-crime generator. Timestamps use unavailable_declared
rather than fake collection dates. No generated anomaly amplitude determines SD.
Also test covariance correlations on a separate D<=512 tiny control, not a
silently subset full survey labelled complete.

For A/B/C, record outer/component metrics for all declared lanes and both
penalties, reference/fit/heldout scores, rank/resolution, legal start and mesh
sensitivity. No unmeasured universal field thresholds are declared.
A controlled nontrivial predictive success requires outer normalized RMS<=2,
raw RMS improvement>=20% over the explicit zero-model baseline, all numerical/
KKT gates, and no outer tuning. These are synthetic release targets only.
Sparse is not required to beat L2 in every regime; worse sparse results persist.
Model error compares susceptibility mass/centroid on original authored bodies
only after independently integrating truth to evaluation mesh; never score a
field survey against an invented volume. No requirement for an attractive image.
D/E publish degradation per fixed incorrect hypothesis, even if nonunique
susceptibility happens to fit it. The demonstration gate needs >=20% greater
heldout raw RMS than correctly specified A OR a recorded unable-to-discriminate
verdict; the latter is unresolved negative discrimination, not PASS.
F exact-null model/prediction at numerical zero and deficient geometry failures
are separate gates. No subtraction of means to make a null model pass.

## Input and leakage attack matrix

Wrong/extra/missing nested keys, string/bool/float integer confusion, subclass
native callbacks, wrong descriptor hashes, shape overflow, NPY header bombs,
invalid encoding, over-depth/token/byte caps, covariance D versus N confusion.
Before heavy import, spy on imports/allocation and assert every cap fails.
Original order/permutation/reimport retains IDs, component order, units and
partition; units hash is determined by IDs+geometry rather than current order.
Duplicate station identity or identical usable coordinates reject, not average.
Corrupted frames/datums/uniform field references/lineage and provider rights
cannot become eligible by selecting an attractive UI case.

Geometry fixture assertions precede truth generation:12 units,72 outer,
216 development, fold144 fit/72 validation/0 buffered,216 refit.
Test exact buffer equality, transitive group/block unions/tie bridges,
negative ENU block indices and all insufficient counts without relaxation.
Changing observations/noise/truth keeps seal/partition unchanged.
Instrument/mask conversion has to occur upstream and be hash-bound.

A trap raises on outer observations at EVERY fitting/selection callback.
Hash candidate+final model before unsealing, then mutate outer values and prove
physical configuration/model unchanged and only evaluation changes; likelihood
and source-record identity hashes necessarily change with changed raw values.
An ordinary re-import with a stale hash must reject, not pretend it is the same
survey. This counterfactual is a leakage test, not a hash-validation waiver.
Covariance basis/
correlation changes cannot silently alter partition but do change likelihood
identity. Failed folds/cap termination forbid aggregate score or best fallback.

## Resource, durability, tools, field and integration

Local ordinary proposed whole-calibration cap7200s wall/3600s CPU, per-inner
solve120s wall, accepted-core iteration/evaluation caps unchanged. No direct
large native run until actual accepted containment authority/profile exists.
One threaded context explicitly pinned; monitor complete child CPU, peak RSS/
private memory, scratch and orphan cleanup, not launcher/null metrics.
Cold/warm null, nominal and upper count cases measured independently with
fresh scratch/cache; upper-cap metadata rejection is not upper execution.
Proposed online60s/30CPU/768MiB RSS/1GiB private/512MiB scratch must pass actual
admitted contained execution. Admission additionally measures actual byte
capacity for the candidate release, current plus two rollback releases, retained
project bytes and configured scratch, and configured worker-memory capacity.
There is no whole-host percentage threshold for the owner-tested stage.
Historical failed headroom/restore receipts are not revised into passes.
Timeout/cancel survive restart,
no orphan processes, no success partial outputs. Native activation is not
authorized by writing this design.

Local CLI: hash original user file, validate geometry, calibrate/evaluate,
export, reimport, reproduce actual model/prediction hashes under pinned runtime.
Change beta/field/geometry in a new configuration and prove actual computation/
hash difference. No saved-case replay as local solve. A rights-blocked source
may be inventoried but cannot be fitted/published.

Crash/disk-full/hash corruption/truncated arrays/member traversal/object NPY/
cross-volume pointer tests must preserve old successful generation and reject
partial new generation; Windows guarantees measured, not assumed. Hosted owner
cross-read/write, job quota, durable cancel/restart and user deletion tests belong
existing integration, not a second persistence system. Off-host backup/restore
and provider SMTP are not prerequisites for the owner-tested stage under current
product SDD section8; local atomic export/reimport remains required.

Field gate requires actually available original bytes with permitted processing,
explicit quantity/error/geometry/field/corrections and grouped heldout results.
Charleston full-coverage/offline processing and Bartlett grid-only distinction
remain parent obligations. No acquisition/rights/source gate closes from S2,
provider links, a400-row subset or P04 numerical success.

Linked browser matrix EN/ES x light/dark x desktop/phone/reduced motion:
pointer-reachable method/result, same-ID map/line highlights, honest absent
predictions for excluded rows, actual residual sign/units, chi3D/slice coordinates,
physical sensitivity, resolution qualification, iteration-history replay labelled,
uniform-line spectral applicability, reactive scientific parameters/readouts,
bundle export/reimport. Shared shell route/font/tokens, no standalone SVG parent
inheritance assumption, no view-domain masking becoming model QC. Course/wiki
needs source-linked theory, all equations/symbols, two worked user-data modes,
six-regime interpretation, exercises and failures; an EN-only forward wiki is
not a completed bilingual inverse course.
