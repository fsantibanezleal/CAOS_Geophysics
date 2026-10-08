# Source-bound owned Joseph construction

Frozen BEFORE code. New exports live in `physical_conditioned_optimizer`, not
in either historical optimizer. Epochs:
`physical-gncg-linear-joseph-candidate-2` and
`physical-gncg-nonlinear-joseph-candidate-3`; policy
`closed-firstorder-joseph-native-true-residual-terminal-1`.

The adapter supplies original physical DTOs, not a metric/operator callback.
`MetricOperands` contains original beta-weighted regularization CSR A and the
actual whitened physical Jacobian K at the requested exact q and the literal
original likelihood normalization c (1 or1/2, never a tuning knob). It binds actual
q, objective/source/allocation hashes, full source COMPONENT count, fit COMPONENT
count, parameter count and literal covariance kind. No caller-supplied factor,
P, F, SPD assertion, perturbation or user-upload native callback is accepted.
Factory checks exact native storage/metadata before scans, copies or native
entry; principal indices come from the public optimizer's actual active set.
The adapter's source admission remains separate from this typed numerical ABI.

For free face J, use A_J with the examined fixed-natural IC0 numeric kernel:
stored unit-lower L and positive D; no shift/permutation/floor/retry. B=sqrt(2c)K_J,
T=(LDL^T)^-1 B^T, S=I+BT, symmetrize METRIC S only, Cholesky without jitter,
F=T S^-1 in64-row chunks. P=(I-FB)(LDL^T)^-1(I-FB)^T+FF^T. Stored-real SPD:
both square terms vanishing would give F^T v=0 and (I-FB)^T v=v, impossible for
nonzero v through nonsingular L/D. This argument is not floating symmetry;
actual native actions require finite intermediates and positive v dot Pv.
Registered `gravity_l2_metric` is a numeric factor/action dependency only, not
a gravity survey/driver, source admission or alternative CG. The new API owns
construction, free face, replacement and close; no adapter factor lifetime.

Resource dictionary uses the EXACT existing dependency allocation equations:
g0=8*n*a, g=8*m*a, c=8*m*m for covariance else0, s=8*m*m;
native=8*g0+12*c+576MiB; interval=4096*(44*a+12*m);
lower=12*(4*a)+4*(a+1);
setup=native+8*g+12*s+8MiB;
action=native+2*g+4*lower+128*(a+m)+8MiB;
line_search=action+interval. maximum=max(setup,line_search).
DTO wrapper/native scalar headers/temporary identity hashes consume the existing
8MiB reserve, not an uncharged second matrix. No second live face factor;
source DTO borrows immutable adapter operands until construction, no retained
source/problem/parent closure after close. All old/new vector and bounded factor
scratch is charged; unknown graph/native tuple refuses. On original M04
n864,m432,a528,diagonal noise: setup674078720/action645446928/
line_search761838864 <805306368. This source dictionary is NOT measured RSS or
host upper-bound proof. Native tuple remains examined Windows Python3.12.10,
exact loaded SciPy triangular/BLAS binary hashes, single-thread controls.

Each actual CG uses the ORIGINAL vendor search H/g. Public API applies its owned
metric, never replaces H with A+B^TB. PG bound release uses the original full
initial diagonal BEFORE CG; failed factor/CG/LS cannot enter that branch as a
rescue. Native CG limits: linear200/rtol1e-6/atol0, nonlinear512/same tolerance.
Check actual free(-g-Hp) norm<=1e-6*initial_free_rhs norm before vendor deletes H.
Record true residual, actual counts/setup/actions/timing/source/model/face hashes
including failed attempts. Nonlinear K refreshes EVERY actual q; previous factor
is disposed BEFORE new setup. Exact-H audit remains distinct from GN search H.

Linear native200 accepted/20LS/120s remains; nonlinear250/30LS/1800s remains,
with lower caller remaining/deadline applied (M04 actual200/120s). Same native
minimize/history; no terminal restart. Preserve nested linear certificate and
nonlinear actual chord Armijo plus any original adapter certificate.

`TerminalPolicy` declares normalized exact-bound KKT no larger than original
1e-5; public computation uses native original gradient and initial norm. When
quadratic model/objective/prediction bounds are requested, a closed
`QuadraticOperands` supplies ORIGINAL G,W,d,reference,beta,alpha and sparse
W_j,D_j terms; positive diagonal smallness is identified structurally, not a
caller mu. Directed nested-factor evaluation encloses physical gradient, mu,
row norms and residual norm, then upper bounds model=r/mu, gap=r^2/(2mu),
prediction=max physical row-norm*r/mu. Exact-bound normal cone signs are used;
no near-bound clipping. Public API computes pass/fail against declared ORIGINAL
absolute limits; no terminal boolean callback. These are conservative sufficient
conditions, not a replacement for independent physical scientific tests.
Optional relative thresholds must first be converted to declared absolute
original units by independently reviewed source adapters, not hidden score data.
The physical prediction-row set may be a declared bounded subset of the original
source geometry (at least1 and no more than charged source COMPONENT count).
The receipt records its actual row count; a fit-row bound is NOT a heldout/full-
geometry bound. Do not duplicate or synthesize rows to fill the source allocation
shape. Full source component accounting stays unchanged even for a subset audit.
No quadratic bounds are used for nonlinear total-norm or quartic cross-gradient
without a separate exact global curvature proof. Stronger nonlinear KKT alone
is NOT model/prediction/objective accuracy acceptance.

Old sources and receipts stay immutable. Failures store last accepted native
state and failed direction/terminal diagnostics, no archive upgrade. M04 owns
only the original physical DTO adapter/full matrix; M11 non-firstorder factor
graph remains unadmitted. Full M02 correction/workflow/UI/course is separate.
