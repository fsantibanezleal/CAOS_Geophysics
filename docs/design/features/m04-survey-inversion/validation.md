# Independent validation and complete acceptance matrix

## 2026-11-11 sparse first-fold phase-limit sensitivity (diagnostic only)

The exact S2-A `linear_tmi_nT`, fold-0, beta-`0.0001` request was run once with
the production 120-second per-fit wall clock and byte cap unchanged. A
process-local diagnostic override raised only
`physical_reduced_optimizer.PHASE_LIMIT` from 512 to 1024; no source file,
stopping tolerance, epsilon, beta, model bound, or scientific acceptance rule
was changed. This is a sensitivity diagnostic, not an accepted production
configuration or an M04 pass.

The run returned `failed / wall_cap` at 120.016 seconds. Epsilons `0.1`, `0.05`,
and `0.025` converged after 3, 1, and 1 outer updates. At `0.0125`, the final
inner call reached the wall cap after three solver iterations; the remaining
four epsilon stages did not run, and no candidate selection or outer evaluation
occurred. The first epsilon's 528-parameter solve used 127 accepted iterations
and 635 conditioning phases. Its prospective memory peak was 762,623,424 bytes
against the unchanged 805,306,368-byte limit. The later stages each needed
three conditioning phases in their completed inner calls. The full eight-stage
schedule therefore remains incomplete.

Evidence identity: checkout `d975d0456db350a5b80f25fa1064e0ac454db1f0`;
request SHA-256
`e8ada27dc7e2a9d911c8bf3c2f684a36753041ddb14e989f70ea1acafbba2afa`;
`magnetic_calibration.py` SHA-256
`58e33b05bdd796bf62535fa6b9068b9d41b5f28020d57487e04162d7305e5ded`;
`physical_reduced_optimizer.py` SHA-256
`22bf04a7e260b5f93c2e54430f54c3d3464150b3ce78d861c8236bc3d6b21aad`;
`magnetic_optimizer_adapter.py` SHA-256
`9655f02dcd1becc3a994cf1956dfa130899cd06e01a5f7d0d6c58a1bcA544f4f`;
Python 3.12.10, NumPy 2.2.6, SciPy 1.15.2, SimPEG 0.25.2, discretize 0.12.0,
single-thread BLAS. The four LaTeX build intermediates in the manuscript
directory were present before this diagnostic and were not touched.

The phase-cap sensitivity shows that the 512-phase refusal is not the only
cause: continuing past it reaches the unchanged wall limit before completing
the frozen schedule. Do not raise the cap or wall limit to call this accepted.
The next solver change must reduce work per accepted model step while retaining
the original noise objective, active-bound policy, byte budget, wall budget,
epsilon schedule, terminal certificates, and outer-data seal. Re-run only this
first failing fold after a source change; do not launch the candidate matrix
until it passes all eight stages and its full independent certificate.

## 2026-11-11 selective likelihood decoding

The fold assembler and calibration path previously materialized the complete
observation vector and noise array before slicing fit rows. They now revalidate
the bounded survey bytes, recompute and compare the geometry seal, then scan
the original scalar tokens while copying only the authorized fit observations
and the corresponding principal covariance block. Held-out likelihood values
are not placed into NumPy arrays. A stale-seal regression refuses before that
selection step; focused tests also verify diagonal fit dimensions and exact
full-covariance principal-block reconstruction.

The focused assembly suite passed six tests; the current calibration suite
passed four tests with the reviewed `OPENBLAS_NUM_THREADS=1`,
`OMP_NUM_THREADS=1`, and `MKL_NUM_THREADS=1` environment. The current-source
528-parameter synthetic S2-A linear-TMI fold converged in 113 iterations in
57.938 seconds. Its normalized projected KKT infinity norm was
`1.420804898067916e-16`, and its original-accuracy terminal certificate passed.
The 144 fit scalars were materialized; the separate 72 validation and 72 outer
scalars remained sealed. The source-bound receipt is
[`m04-current-source-selective-reader-2026-11-11.json`](../../../validation/m04-current-source-selective-reader-2026-11-11.json).

The development-fold scorer now uses the same post-seal selective reader for
only the chosen validation rows and their diagonal errors or covariance
principal block. Its public result remains aggregate-only. Four scorer tests,
including a nonzero physical prediction and an analytic linear-TMI check of
the engine's ENU vertical sign, pass; the combined
assembly/scorer run passes ten tests. Ruff and `git diff --check` pass for the
scoped changes. This does not add candidate selection or expose validation
vectors to an optimizer.

This fixes the likelihood materialization boundary for the tested fit-fold
path. It does not qualify candidate selection, held-out scoring, field data,
nonlinear exact-magnitude inversion, sparse IRLS, API admission, full product
acceptance, or a release.

## 2026-11-11 current-source 528-cell linear L2 fold

The current-source fold test passed after extending its source inventory to
include the calibration module, the likelihood decoder, the quantity
composition module and the actual SimPEG regularization implementation. The
source inventory digest is recorded in
[`m04-current-source-l2-fold-2026-11-11.json`](../../../validation/m04-current-source-l2-fold-2026-11-11.json).

On the authored S2-A linear-TMI request, fold 0 used 144 fit rows and kept its
72 validation rows and 72 outer rows sealed. The 528-parameter bounded L2
solve converged in 113 iterations in 63.515 seconds. Its normalized projected
KKT infinity norm was `1.420804898067916e-16`; the original-accuracy terminal
certificate passed with a source-normalized KKT upper bound of
`1.119698199062626295969625968149742E-16`.

The four focused tests passed with no failures or skips. This is one authored
synthetic development fold. It does not establish an independent full-fit
oracle, truth recovery, candidate selection, sealed outer evaluation, sparse
or exact-magnitude inversion, field eligibility, API admission or M04 method
acceptance.

## 2026-11-06 source-bound linear inverse increment

`magnetic_inverse.build_operator` now parses the sealed survey, checks local
processing eligibility and original-lineage status, preserves the selected
usable receiver-row order, and constructs the actual SimPEG component kernel.
`MagneticQuantity` evaluates secondary ENU, linear TMI, and exact total-field
anomaly with their quantity-specific predictions and Jacobians.

`MagneticRegularizer.terms()` exports the existing volume-normalized L2
objective as sparse, weighted smallness and active-face operators. The cell
term uses `sqrt(v_i/V)` and each axis face uses
`ell_j * sqrt(V_face/V) / distance`; inactive-cell and exterior faces remain
absent. The reconstructed Hessian, objective value, and gradient match the
independent active-face quadratic on the nonuniform mesh with two inactive
cells. `MagneticObjective` composes this with diagonal or full-covariance
Gaussian whitening and binds only affine secondary-ENU and linear-TMI fits to
the M02 original-noise solver. The exact total-field lane and sparse IRLS lane
are refused by the optimizer adapter until their separate bindings exist.

The focused local run passed 26 tests with zero failures, errors, or skips.
It covered sealed-survey row preservation, quantity guards, physical L2
reconstruction, and four actual 30-receiver solves (secondary ENU and linear
TMI, each with diagonal and full covariance) against an independent SciPy
BVLS oracle. Ruff and `git diff --check` passed. JUnit receipt:
`E:\_Datos\CAOS_Geophysics\validation\m04-linear-adapter-20261106-r3.xml`.

This closes a local synthetic linear-inverse increment only. The frozen
528-parameter first-fold request was not available, and there is no accepted
full-survey calibration, sparse reweight-and-solve sequence, nonlinear exact
total-field solver, nested beta/fold selection, sealed outer evaluation,
field-data qualification, full result generation/export, full product
integration, host admission, or M04/release acceptance.

## 2026-11-02 positive-down background correction

The fold assembler had used the wrong vertical sign for its inducing-field
background. It now consumes the ENU vector validated and returned by the
actual SimPEG forward engine. The exact-total-anomaly regression compares the
assembled prediction to that engine on the same fit rows; see the
[field-sign validation](../../../validation/m04-positive-down-background-2026-11-02.md).
The exact R-405 and R-406 gates now independently check all quantity Jacobians
against Choclo observations and full-covariance principal whitening against
explicit solves; see the [gate evidence](../../../validation/m04-quantity-covariance-gates-2026-11-02.md).
The current focused M04 regression passes 456 tests with no skips. Inverse,
optimizer, and product acceptance remain open.

## 2026-11-02 independent synthetic acquisition matrix

The geometry-first six-regime, three-quantity Choclo generator and its
manifest-bound request/truth files are documented in the
[current R-412 validation report](../../../validation/m04-synthetic-acquisition-2026-11-02.md).
The exact `test_independent_case_matrix` gate passes for all 18 cases, and the
current focused M04 foundation/regression run passed 453 tests with no skips.
This closes synthetic generation controls only; the full inverse and M04
acceptance matrix remain open.

## 2026-10-28 bounded likelihood-composition increment

`data-pipeline/magnetic_objective.py` now composes the frozen Gaussian data
term with secondary ENU, linear TMI, and exact total-field anomaly quantities.
It returns the dimensionless whitened L2 value, physical `observed - predicted`
residual, gradient, and matrix-free Gauss-Newton action for normalized
`q=chi_si/0.01`. Selected original rows are matched exactly to the whitener;
principal full-covariance whitening is retained. Kernel receiver/cell/product
caps are checked before copying or scanning numeric values.

The focused local run passed 33 tests across `test_magnetic_likelihood.py`,
`test_magnetic_quantity.py`, and `test_magnetic_objective.py`; Ruff, Python
compilation, and `git diff --check` passed for the new objective/test files.
An additional actual-Choclo integration control passed for an exact-magnitude
Gaussian gradient with correlated principal covariance and a directional
finite-difference oracle on independent Choclo predictions.
An initial test exposed that the exported residual used `observed - (predicted
- observed)`; the return path was corrected and regression-tested against
`observed - predicted`. This increment does not create SimPEG kernels, solve
for a model, bind an accepted optimizer, run a user survey, create artifacts,
or satisfy R-405..R-420. The optimizer and all nonlinear precision gates remain
open; this is objective-component evidence only.

## 2026-10-28 optimizer-binding review

The repository's public `physical_nonlinear_optimizer.solve_bounded_nonlinear`
is a candidate, not an accepted M02 binding. Its M11 source hash matches the
current file, but the M11 precision receipt leaves scientific precision and
full release acceptance false. An independent source review found it is a
plausible candidate for a narrowly scoped scalar exact-magnitude M04 lane after
a normative binding amendment and independent M04 replay. It rejects three
component observations, so that review does not qualify secondary ENU. The
review also confirmed its existing tests exercise a quartic joint objective,
not the new M04 likelihood, and that runtime resource containment is external
to the optimizer. Consequently R-407 stays open: no M04 adapter may claim this
candidate is accepted, and the magnetic inverse remains unimplemented until the
M02 accepted export/source, semantics, and M04-specific precision and resource
evidence are bound. The open draft M02 survey-L2 PR is not acceptance evidence.

## 2026-10-30 focused source rerun

On the current direct checkout, the dedicated `.venv-gravity` lane passed three
focused controls: the actual SimPEG component-kernel export is available to the
M04 objective; the exact-total-field Gaussian gradient agrees with independent
Choclo observations; and the nonzero SimPEG fit assembly has the declared
physical objective derivative. Command:

```powershell
.\.venv-gravity\Scripts\python.exe -m pytest `
  tests/numerics/test_magnetic_forward.py::test_actual_simpeg_component_kernel_is_available_for_m04_objective `
  tests/numerics/test_magnetic_forward.py::test_m04_exact_magnitude_gaussian_gradient_against_choclo_observations `
  tests/data/test_magnetic_fit_assembly.py::test_actual_nonzero_simpeg_fit_assembly_has_physical_objective_derivative -q
```

This confirms those operator/likelihood pieces on the present checkout only.
It does not satisfy R-407: the M02 optimizer remains a gravity-bound private
class, and no accepted generic source/export/epoch exists. Consequently no
magnetic model was optimized, no held-out survey was evaluated, and no M04
artifact or resource profile is accepted by this rerun.

## 2026-10-28 SimPEG regularization cross-check

`data-pipeline/magnetic_regularization.py` now constructs the pinned SimPEG
0.25.2 `WeightedLeastSquares` objective with identity mapping, explicit
reference-in-smoothness, dimensionless beta-ready q units, zero second-order
coefficients and volume fractions `v_i/V`. A separate explicit sparse quadratic
uses only physical center-to-center faces whose two cells are active. On a
nonuniform 3D mesh with two inactive cells, SimPEG objective, gradient and
Hessian action match that oracle at the test tolerances; the test observes 6,
4 and 5 valid faces along x, y and z. Three focused regularization tests passed,
including inactive/exterior face exclusion and shape-before-finite-scan.

This test resolved a genuine API mismatch in the written recipe: a constant
`1/V` passed as SimPEG `weights["volume"]` yields an unweighted-per-cell
smallness term, not `sum(v_i/V * delta_i^2)`. The algorithm note now records the
actual pinned API use that matches its frozen equation. This is local
regularization evidence only; no magnetic inverse, accepted optimizer, field
case, complete method gate or release acceptance is implied.

The module also evaluates one frozen sparse weight refresh through actual
SimPEG `Sparse.update_weights`. It fixes norms `[1,2,2,2]`, component gradients,
`irls_scaled=False`, the prescribed eight `epsilon_q` values and
`epsilon_j=epsilon_q/ell_j` thresholds. SimPEG smallness weights match
`1/sqrt(delta_q^2+epsilon_q^2)`; first-order weights remain one. For every
epsilon, the refreshed surrogate gradient agrees with the derivative of the
true fixed-epsilon penalty and a directional finite-difference oracle.
Decimal80 controls at delta `+/-1e-10` and zero confirm positive tiny penalties
and exact zero. Outer reweight-and-solve convergence, fixed-objective
monotonicity and terminal stationarity remain unimplemented and unaccepted.

## 2026-10-28 SimPEG sensitivity handoff

`magnetic_forward.forward_magnetic_with_kernel` now exposes the actual
receiver-major E,N,U SimPEG/Geoana sensitivity matrix in nT per SI
susceptibility through a distinct `magnetic-prism-forward-kernel-result-1`
schema. The ordinary forward function retains its previous exact key set and
result schema. On the multi-cell, sparse-active control the new matrix matches
independent Choclo unit-SI component columns and its product with the supplied
susceptibility reproduces the returned physical field components. The focused
kernel test and the existing closed legacy-result-schema test both passed.
This creates a real kernel-to-objective input path, but does not yet parse a
full survey into the forward request, run calibration or satisfy M04 acceptance.

## 2026-10-28 fold-scoped objective assembly

`magnetic_fit_assembly.assemble_magnetic_fit_objective` now joins the closed
survey byte protocol to a freshly planned geometry partition, actual
SimPEG/Geoana fit-receiver kernel, frozen Gaussian likelihood, and actual
SimPEG WLS regularizer. It selects only the requested development fold's fit
rows, preserves original receiver/component flattening, extracts the matching
principal covariance for full-covariance noise, and returns the geometry seal
and source flat indices. Before materializing observations/noise it reparses
and revalidates the original bounded bytes; geometry planning continues to
exclude those values.

Four focused tests pass for diagonal-SD selection, full-covariance principal
subsetting, invalid fold rejection and a nonzero actual SimPEG assembly. The
nonzero test uses 144 fit receivers with chi=0.002 SI and zero protocol-control
observations; the assembled objective is positive and its directional
finite-difference derivative matches the analytic gradient at relative
tolerance 2e-5. An earlier zero-start control produced zero objectives and is
retained only as the exact zero baseline. These authored protocol controls do
not establish inversion recovery or scientific accuracy. No optimizer,
candidate selection, outer evaluation, final refit, durable result bundle,
native admission, user-data CLI or online path is implemented or accepted by
this increment.

## 2026-10-28 frozen development-fold scoring

`magnetic_fold_score.score_magnetic_validation_fold` accepts only a hash-matched
normalized model, replans the sealed geometry, builds the real kernel on one
fold's validation rows, applies the declared quantity and Gaussian noise model,
and returns aggregate phi-d/RMS metrics without observation, prediction or
residual vectors. It records the geometry seal, model hash, noise dependence
declaration and explicit development-only role; it neither calls a fit callback
nor selects a candidate nor evaluates outer rows. A changed model hash is
rejected before planning or forward computation.

Three focused tests pass, including a nonzero actual SimPEG validation score
from the authored protocol fixture. That score is a synthetic plumbing check,
not validation accuracy or a selected-model result. The final sealed outer
evaluator, candidate workflow, and any method acceptance remain open.

The new English/Spanish lesson pair
`notebooks/{en,es}/03-magnetics/04-m04-fit-objective-validation.ipynb` was
executed in fresh kernels and passed a second `run_notebooks.py --check` replay.
Both render the same computed values: 144 fit, 72 validation and 72 outer rows
with zero overlaps; 528 active cells; `chi_start=0.002 SI`; `phi_d=564455.5774`,
`phi_m=0.04`; and a directional gradient finite-difference discrepancy of
`1.98e-6`. The validation fold reports `phi_d=263336.3622` for that fixed model.
These high residual values are properties of the deliberately zero-observation,
authored protocol fixture; they are not an accuracy score or geological result.
The figures map the computed east-component fit prediction and residual at the
fixture's ENU coordinates. The static notebook checker passes across both
language trees, 60 notebooks total.

The complete focused M04 regression selection before the scorer addition
(survey JSON/geometry/bundle/CLI, fit assembly, forward, likelihood, quantity,
objective and regularization) collected 421 tests and exited successfully with
all tests passing on the pinned Windows runtime. Three additional fold-score
tests also pass. Ruff, Python compilation and `git diff --check` passed for the
added M04 files.

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
confirm its limit is linear projection. Check adjoint
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
an explicitly noiseless realization of a declared conditional test covariance.
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

The bounded NPY member and history codecs plus generation-envelope pointer
controls have a focused 48-test replay recorded in
`docs/validation/m04-bounded-array-member-codec-2026-11-02.md`. This is container
integrity evidence using a structural failure fixture. Request semantics and
request-array unit binding are now checked by reconstruction and reparsing; full
Result semantics, Result-array field-to-unit binding, fitted-result replay, Windows
crash durability, optimizer binding, and R-415 acceptance remain open.

## 2026-11-06 current-checkout foundation replay

At source revision `721f7fcad4b53307087f710c5222e8b50d153882`, the focused
M04 foundation selection collected 421 tests and exited successfully on the
repository `.venv-pipeline` runtime. It covered the bounded survey reader,
geometry planner, survey bundle, SimPEG/Geoana forward operator, fit assembly,
likelihood, quantities, objective, and regularization. Ruff passed for the
foundation modules. The command selection did not exercise a completed M04
inverse or user-survey calibration: `magnetic_inverse.py`, the accepted M02
optimizer binding, and the calibration CLI are absent. This replay refreshes
only the foundation evidence; M04 remains planned and unaccepted.

## 2026-11-06 declared-gate inventory

At source revision `6711efd`, `scripts/check_magnetic_method_matrix.py` parses
the twenty R-401..R-420 requirements, checks named Python test symbols and
gate files, and reports whether declared implementation files exist. It fails
closed by default when references are missing; `--report-only` is used to
inspect an in-progress matrix. Four checker tests passed, Ruff passed, and the
JSON inventory reported 7/20 declared source/gate pairs present and 13
incomplete. The exact command was
`.venv-pipeline/Scripts/python.exe scripts/check_magnetic_method_matrix.py
--report-only --json`.

This is a structural inventory. Existing gate symbols are not evidence that
their tests passed, and source/test presence does not establish numerical,
field, API, UI, durability, or host acceptance. In particular the checker
reports the missing `magnetic_inverse.py`, `magnetic_optimizer_adapter.py`,
calibration CLI, hosted adapter, linked views, bilingual docs gate, and field
eligibility gate. Scientific and field acceptance remain false; the M04
requirements status remains planned.


## 2026-11-11 active-face preflight reuse performance diagnostic

The reduced active-face optimizer now passes the exact metric operands and
allocation proof that it has just validated into the registered conditioned
optimizer. The prior path built and validated the same source-bound operands
again immediately before constructing the native metric. Reuse is scoped to one
synchronous direction: the model must remain byte-equal to the admitted model,
the operand object must be identical, identity is rechecked, and the cached
objects are cleared on every exit. The native M02 loop, accepted stopping and
terminal policy, active-face sequence, 200-CG cumulative limit, 512 production
phase limit, byte ceiling, and 120-second inner wall limit are unchanged.

The focused source-bound regression verifies one `metric_operands` construction
per active-face phase and exactly two allocations validations per phase: the
pre-native reservation plus `OwnedMetric`'s own validation. This removes the
intermediate duplicate construction and validation while preserving the
allocator's independent final check.

The exact S2-A `linear_tmi_nT`, fold 0, beta `0.0001` request was run with the
production 512-phase cap. It stopped honestly at `resource_cap` after 87 accepted
steps and 513 recorded attempts (the last is the refusal), in 9.594 seconds.
No candidate scoring or held-out evaluation ran. A separate, process-local
sensitivity run set only `physical_reduced_optimizer.PHASE_LIMIT = 1024`, with
the 120-second wall limit and all numerical rules unchanged. It returned
`wall_cap` at 120.015 seconds: the epsilon `0.1` stage completed three outer
updates, `0.05`, `0.025`, and `0.0125` completed one each, and the `0.00625`
stage then timed out during its first inner solve. The remaining stages and
selection were not run. The larger phase limit is diagnostic only and is not a
production policy change.

Evidence identity: input SHA-256
`e8ada27dc7e2a9d911c8bf3c2f684a36753041ddb14e989f70ea1acafbba2afa`;
`physical_conditioned_optimizer.py` SHA-256
`cc2eb86c657a09f406d91cdc11c4ae30418ff76e1b2b2649233fe80917d338f5`;
`physical_reduced_optimizer.py` SHA-256
`e0fd50057c73a450159cf66ade51cb23a000b1e2090a559e4a7097e261ef68ae`;
regression SHA-256
`a150c605cdd2bfeeeccd528d6f11f4d7cd0180352828f16d687f8b0ae8736831`;
Python 3.12.10, NumPy 2.2.6, SciPy 1.15.2, SimPEG 0.25.2, discretize 0.12.0,
with `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`, and `MKL_NUM_THREADS=1`.
The reduced-optimizer, physical-optimizer, owned-SPD, and current-source M04
calibration suites passed together (89 tests); Ruff and `git diff --check` also
passed. The calibration suite includes the current 528-cell L2 fold and a
mocked sparse refusal control; it does not turn the production-cap sparse
failure or the 1024-phase diagnostic into a successful sparse fold. A separate
34-test M02 original-optimizer selection passed; it excluded the retained long
low-beta initialization and locked full-fold runs, which were not needed to
verify the default allocator hooks.

This is an optimization increment with a reproducible negative sparse result.
The all-eight-epsilon sparse fold, 16-candidate/three-fold selection, refit,
sealed evaluation, field validation, complete M04 workflow, and product
acceptance remain open.

## 2026-11-11 exact ray-screen optimization

`physical_reduced_optimizer.initial_ray` now computes outward-rounded lower
and upper intervals for each nonzero direction coordinate. It retains the
exact `Fraction` comparison for every coordinate whose interval can contain
the first contact. The interval screen cannot select the contact or change
the returned step; the exact rational minimum still defines both. Zero
direction coordinates are excluded before screening, including a zero
coordinate that is already on a bound. The deterministic rational-oracle tests
cover random 96-coordinate inputs, ties, subnormal motion, very large
components, and bound-resident zero coordinates.

The preserved scalar implementation and optimized implementation were
measured with `python scripts/benchmark_physical_ray.py` on a seeded 528-cell
vector, 120 repetitions. Both returned exactly `(0.09004450897719632, 98)`.
The scalar scan took 0.2600024 s and the screened version took 0.0085985 s,
30.24x for this isolated operation. This is a local microbenchmark, not an
end-to-end fit speed claim.

The exact S2-A `linear_tmi_nT`, fold 0, beta `0.0001` sparse request was then
replayed once with the production limits unchanged. It stopped at the same
phase resource cap after 87 accepted updates and 513 conditioning attempts
(512 admitted, then one refusal), in 20.297 s. The refusal recorded 7,158,016
retained audit bytes, 760,776,464 prospective bytes, an 805,306,368-byte
admission ceiling, and a 512-phase ceiling. Only epsilon `0.1` ran; no candidate
selection or evaluation ran. This optimization is retained as a bounded
cost reduction but does not resolve the sparse solver bottleneck or change any
method/product acceptance claim.

The run used request SHA-256
`e8ada27dc7e2a9d911c8bf3c2f684a36753041ddb14e989f70ea1acafbba2afa` and
optimizer SHA-256
`3d026d44b32f644ded036e5f309e3fe1eb1b3bbb627798647cd5ee43fe2e6887`.
`tests/numerics/test_physical_reduced_optimizer.py` has SHA-256
`ee7fbfb3627d22da4f7115c1400eaa9fc21fe20692e952503978daadd4796a9d`.
The focused module passed 19 tests; Ruff passed on the optimizer, test module,
and benchmark script; `git diff --check` passed.

## 2026-11-11 sparse active-face phase profile

To locate the remaining cap without changing the solve, a one-fold profile
wrapper records each native direction's conditioning phases, CG work, frozen
cell counts and existing timers. It requires the reviewed single-thread
environment and keeps the 512-phase, 120-second and 805,306,368-byte limits
unchanged. The exact S2-A fold completed its diagnostic run in 15.969 s and
again stopped at `resource_cap`: 87 accepted updates, 88 direction calls, 513
conditioning attempts, with only epsilon `0.1` reached.

The direction-phase count distribution was 3:4, 4:11, 5:24, 6:16, 7:23 and
8:10. Of 513 phases, 306 used one CG iteration, 145 used two and 61 used
three; one was the refusal. The first accepted direction froze 100 new
coordinates after its initial solve, then the subsequent restricted solves
identified further outward bound coordinates in groups of 41, 24, 11, 6 and
4. The record locates the budget pressure in repeated active-face updates, not
CG exhaustion or the isolated bound-ray arithmetic. It does not establish
that these updates can be combined without changing the accepted constrained
solution; a new active-set rule requires its own source-bound proof and
adversarial validation under the same limits.

Profile runner SHA-256:
`60bfae2af11c3cc833e9c335d037218b806adcf2ad0aa32281b55e9a0c94de89`.
External diagnostic receipt SHA-256:
`e18c59e2f5029faefe81cc95d0dc8914d4fc190c5befa2dd38a74a38f8d17fda3`.
The focused optimizer module remains 19 passing tests; Ruff passes on the
profile runner. This is diagnostic evidence only. Sparse acceptance, M04,
the method ladder and product release remain open.

## 2026-11-11 prior-start sparse IRLS diagnostic (not a candidate fold)

This run used the authored S2-A `linear_tmi_nT` request, fold 0, beta `0.0001`,
and the frozen eight-value epsilon schedule, objective, bounds, stopping rules,
and 805,306,368-byte allocation ceiling. It initialized from the request's
declared prior. The candidate protocol requires a converged same-beta, same-fold
L2 result, so this successful prior-start run is a solver diagnostic, not a
valid sparse candidate fold. The locally configured conditioning
phase ceiling was 1024 and this run explicitly used a 600-second per-fit wall
allowance. It completed in 190.829 seconds with 154 direction calls and 662
conditioning phases. The largest recorded prospective allocation was
762,623,424 bytes, 42,682,944 bytes below the byte ceiling.

All eight epsilon stages returned `converged`. The stage outer-update counts
were 3, 1, 1, 1, 1, 1, 1, 1. Each of the ten stored M02 terminal audits passed
its original-noise free-face certificate; the maximum certified free error
upper bound was `1.15522e-13`, and the maximum normalized exact bound-KKT value
was `8.24701e-15`. All ten accepted outer states passed the fixed-epsilon true
objective monotonicity check. The final normalized projected-gradient infinity
norm was `3.60736e-15`, against the stage's `1.25134e-4` limit. The final
fixed-epsilon objective components were `phi_d=374.04002134` and
`phi_m=12.47076958`, with beta `0.0001` and total `374.04126842`. The 144
observed-minus-predicted residuals had an unweighted RMS of `0.805838 nT`.
These quantities are solver diagnostics on one synthetic development fold;
they do not measure held-out performance or geological accuracy.

The full diagnostic artifact, including the 528-component normalized model, 144
predictions, 144 signed residuals, stage history, terminal-certificate digests
and per-phase resource profile, is stored outside Git at the relative path
`CAOS_Geophysics/research-runs/2026-11-11/s2a-sparse-fold0-beta-1e-4-prior-start-diagnostic.json`
under the configured device data root. Its SHA-256 is
`b21d4ee3e554076e408f32f9bed1c9f0dce6cd6138a1df71147b667702211ad4`. The
request SHA-256 is
`e8ada27dc7e2a9d911c8bf3c2f684a36753041ddb14e989f70ea1acafbba2afa`, the
calibration source SHA-256 is
`eafd2c41e9c8adf8075e4633755245e4f8f2334ab362b155fa0badf72805783b`, and the
reduced-optimizer source SHA-256 is
`74ca5273cfe885f0d77ee117119a4d4221929e097383e4843130db912d6b16d2`. The
compact machine-readable summary is
[`evidence/s2a-sparse-fold0-beta-1e-4.json`](evidence/s2a-sparse-fold0-beta-1e-4.json).

The sparse API and profile runner have since been changed to require and
persist a certified same-fold, same-beta L2 starting model. That candidate-path
replay remains to be run. The prior-start result claims remain false for candidate selection, field-geology
validation, outer evaluation, method acceptance and online admission. It closes
only the standalone IRLS convergence diagnostic. The 16-candidate/three-fold matrix,
fold scoring, nested selection, final development refit, model freeze, sealed
evaluation, independent-acquisition controls, field eligibility, user-data
bundle and full M04 integration remain open. Earlier failures remain retained
above as historical evidence.

## 2026-11-11 same-beta L2-start sparse replay at production limits

The profile runner executed the authored S2-A `linear_tmi_nT` fold 0 at beta
`0.0001`. Unlike the prior-start and over-budget diagnostics above, this run
started from a converged, independently certified L2 model for the same fold,
beta, source inventory, geometry seal and fitting rows. The L2 fit converged
with normalized KKT `8.9567e-17` in 41.828 s. The sparse fit used the unchanged
120-second deadline, 512-phase limit and 805,306,368-byte allocation ceiling.
It ran for 120.328 s and stopped at `wall_cap` while processing epsilon
`0.0125`; epsilon `0.1`, `0.05` and `0.025` converged. The 12 recorded
conditioning phases were all within one CG iteration, and the prospective
allocation remained within the byte ceiling. The full eight-stage schedule did
not finish, so the fold failed and no candidate score or selection was
produced.

This replay validates the same-beta L2 start binding and provides a compliant
resource-failure receipt. It does not satisfy T43 or justify extending either
M02 solver limit. Its full receipt is stored outside Git at
`CAOS_Geophysics/research-runs/2026-11-11/s2a-sparse-fold0-beta-1e-4-same-beta-l2-start-120s.json`
under the configured device data root. Receipt SHA-256:
`b9817de18852980422e1a573181259be914adcfe6d233ad00a23a59003220411`.
The receipt records the exact product commit, runner and solver source hashes,
runtime, initial L2 model hash, every completed epsilon stage and the failure
state. Its compact summary is
[`evidence/s2a-sparse-fold0-beta-1e-4-l2-start-120s.json`](evidence/s2a-sparse-fold0-beta-1e-4-l2-start-120s.json).

The remaining bottleneck is the time required by repeated certified inner
solves across the continuation schedule. The run does not authorize weakening
the original-noise terminal certificate, objective monotonicity, frozen
epsilon schedule, source binding or resource limits. Any optimization must
preserve those conditions and pass the existing adversarial controls before
the candidate matrix runs.

## 2026-11-12 source-exact same-beta sparse fold

The M04 fold-0 failure above was traced to a native line-search trial whose
rounded model equalled the current model. SimPEG's in-line-search
`zero_free_direction` guard fires before the ordinary stopping-criteria
terminal check. Commit `89453682c1bb41724b4f6f6f7d1d8e5c116f78a7` adds a narrow
catch for that exact failure, plus the corresponding zero native-direction
case. Neither path accepts a trial or changes the model. A successful stop
requires the existing original-source residual/strong-convexity certificate;
the native solve wrapper then verifies exact equality to the last recorded
state and reevaluates the objective. If certification is withheld, the result
remains `nonconverged / zero_free_direction`.

The regression control exercises both outcomes. It passes with the actual
certificate and the unchanged model, and fails closed when the certificate is
withheld. `tests/numerics/test_magnetic_inverse.py` and the applicable tests in
`tests/numerics/test_physical_original_optimizer.py` pass: 11 passed, 1 skipped.
The one external-control test was excluded because
`GEOPHYSICS_M02_MAGNETIC_SOURCE` is not set to its retained control snapshot;
the unfiltered invocation fails at that required environment precondition.
Ruff, Python compilation, `git diff --check`, and the independent
`joint_survey_compiled_baseline.source_inventory()` closure also pass.

The exact-commit profile reran S2-A `linear_tmi_nT`, fold 0, beta `0.0001`,
starting from the converged same-fold/same-beta L2 model and retaining the
original schedule, 120-second per-fit wall cap, 512-phase cap and
805,306,368-byte allocation ceiling. All eight epsilon values
`[0.1, 0.05, 0.025, 0.0125, 0.00625, 0.003125, 0.0015625, 0.001]` converged.
The sparse fit used 112.297 seconds and 24 direction calls / 24 conditioning
phases; all eight stored terminal audits passed. Final normalized projected
gradient infinity norm was `4.921145520829682e-15`. At epsilon `0.001`, the
fixed-epsilon true objective was `374.0412684186038` (`phi_d` `374.0400213416462`,
true `phi_m` `12.470769576338325`). The full profile took 141.109 seconds
because it includes the preceding L2 fit; the sparse fit itself stayed under
its unchanged 120-second limit.

The source-exact receipt, including the 528-cell model, 144 fit predictions,
signed residuals, stage history, terminal proofs and resource profile, is
stored outside Git at
`CAOS_Geophysics/research-runs/2026-11-12/s2a-sparse-fold0-beta-1e-4-8945368-120s.json`
under the configured device data root. Receipt SHA-256:
`f7ce714bc5c5e9eb399649caec8890cf70f5735a3d9a5791569e838f524c1734`.
Request SHA-256 remains
`e8ada27dc7e2a9d911c8bf3c2f684a36753041ddb14e989f70ea1acafbba2afa`.
The receipt still marks candidate selection, field validation, outer evaluation,
method acceptance and online admission false. This closes one compliant
synthetic development fold only. The candidate/fold matrix, nested selection,
final refit, freeze, sealed evaluation and independent acquisitions remain
required; T43, M04 and product release remain open.

## Resumable candidate-matrix and final-refit plumbing

The current source adds `data-pipeline/magnetic_candidate_matrix.py` and
`scripts/run_m04_candidate_matrix.py`. The runner fixes the eight beta values,
L2-before-sparse ordering and three development folds from the approved
contract. It uses the same-beta converged L2 fit as the sparse starting model,
scores each frozen model only on that fold's validation rows, and writes a
hash-bound receipt per beta/fold under `GEOPHYSICS_LOCAL_DATA_ROOT`. Resume
requires exact request, partition, product-commit and solver-source identity;
partial or source-stale receipts are rejected. Candidate aggregation uses
pooled `sum(phi_d)/sum(n_components)` and requires all three fold metrics.
Score ties use the contract's floating tolerance, L2 preference, larger beta
and fixed candidate ID.

The same change adds explicit ordinary-L2 and sparse final-refit entry points.
Partition index `-1` resolves only to `plan.final_refit_rows`, which is a
subset of development rows and disjoint from the outer partition. A focused
current-source test proves this row selection and both wrapper calls; candidate
order, pooled scoring, failed-fold rejection and tie resolution pass three
deterministic unit tests. Ruff and `git diff --check` pass.

No full candidate matrix was run by this plumbing check. No selected model,
final refit, model freeze, sealed outer score, independent acquisition,
resource-upper proof or scientific acceptance is claimed. T43 and R-008 remain
open. The reproduction command after commit is:

```powershell
python scripts/run_m04_candidate_matrix.py `
  --request tests/fixtures/magnetic_survey/generated/requests/S2-A-linear_tmi_nT.json `
  --output-dir "$env:GEOPHYSICS_LOCAL_DATA_ROOT/research-runs/<run-id>/m04-candidate-matrix"
```

The unchanged per-fit wall limit is 120 seconds. Matrix completion means the
declared outcomes were recorded, including failures; it does not itself pass
the candidate, field, method, host or product gates.
