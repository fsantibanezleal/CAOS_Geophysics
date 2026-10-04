# Full-survey offline operator seam

This prospective intrinsic extension is needed because the unchanged ordinary
400-row/256-source Result and distinct local320 study cannot represent a
complete provider survey. It does not change either contract, rewrite their
failed controls, or admit a server profile. It specifies the scientific choice
for review before a new executor/schema is implemented.

## Source-backed choice, not a renamed subset

Retain a single global1/r scalar representation, the exact training-only
half-open source blocks, min(training upward)-candidate depth, population
column scales without centering, raw numerical weights, and Ridge objective.
Every eligible training row participates in that global objective. Chunks are
storage/operator evaluation units only: they do not create independent tiled
fits, change sources, average measurements or thin the survey. Each full
request still carries its own complete line/sensor/spatial seal and heldout
denominator. One sensor/request, not a hidden multiplication of candidate fits.

[SciPy1.15.2 LSMR](https://docs.scipy.org/doc/scipy-1.15.2/reference/generated/scipy.sparse.linalg.lsmr.html)
accepts a LinearOperator with forward/transpose actions. For A=W^(1/2)G/s,
b=W^(1/2)y, its damp parameter must be sqrt(lambda), not the Verde lambda:
the solved objective is ||Ac-b||^2+damp^2||c||^2. The reported physical
coefficients remain q=c/s with nT*m, not susceptibility. Fixed nT units and
the unweighted versus inverse-variance lambda distinction remain unchanged.
Published [LSMR author documentation](https://web.stanford.edu/group/SOL/software/lsmr/)
provides the algorithm reference; a small residual is not a geological bound.

Do not silently substitute
[Harmonica0.7.0 EquivalentSourcesGB](https://www.fatiando.org/harmonica/v0.7.0/api/generated/harmonica.EquivalentSourcesGB.html).
Its [tagged implementation](https://raw.githubusercontent.com/fatiando/harmonica/v0.7.0/harmonica/_equivalent_sources/gradient_boosted.py)
fits successive overlapping-window residuals and adds coefficients; each
window uses its own least-squares scaling. It retains full input/predicted/
residual arrays, and its memory estimator counts the largest Jacobian rather
than whole-process RSS. It is a valuable separate large-survey algorithm,
but not an algebraically identical execution of the frozen global Ridge
objective. Window size/order/seed and predictive validation would require
their own presealed contract, not a backwards-compatible engine swap.

## Prospective streamed custody and geometry

Original acquisition bytes are immutable and streamed/hash-counted through
MAX+1 limits. Record length, UTF-8/numeric token length, exact14-column header,
IDs, strict ordinals, finite values and line/sensor dictionary coverage remain
typed. Do not buffer an entire2.58GB CSV or load an archive then check its
expanded size. Public provider files require an explicit reviewed adapter to
this contract after actual dictionary/report/attachment verification; guessed
column aliases and latitude-to-projected-coordinate defaults are prohibited.

Store all decoded rows and masks in source-order fixed-dtype disk arrays with
explicit shape/dtype/units/hash and closed chunk manifests. No object dtype,
pickle, arbitrary loader, ZIP member execution or caller callback. Secondary
line/ordinal indexes refer to original row IDs, never replace original order.
Auxiliary/reference arrays likewise need bounded per-chunk typed identities;
they cannot evade the ordinary2MiB metadata ceiling by silently lifting it.
The future survey contract must name those distinct external-array shapes and
rights, not claim ordinary inline auxiliary arrays can hold a full survey.

Pass1: count bytes/rows/lines/sensors and validate identities/geometry without
reading magnetic values for model choices. Persist the full geometry seal,
whole-line outer/inner IDs, tie-segment buffer exclusions, physical support,
all source blocks/member counts/minimum upward and prospective memory/disk
costs. Pass2: inspect admitted channel/correction metadata and produce explicit
source-order derivatives. Actual supplied navigation alignment precedes the
seal; value-dependent calibration remains independent or fold-local.
No missing datum/time/error/reference/rights is synthesized to enable either
pass. An empty calibration fold refuses unchanged.

Global crossover discovery uses a geometry-only spatial index and exhaustively
enumerates actual flight/tie segment intersections. No pair truncation or
joining across masked gaps. Save rejected candidates/reasons too. Components,
gauges and rank remain full-survey objects; window-by-window leveling with
independent artificial zero datums is not equivalent. Held-out offsets require
independent calibration, never leakage from full-survey provider corrections.

## Matrix-free objective and independent acceptance

Accumulate unweighted column population variance in deterministic source/row
order with a stable centered two-pass or mergeable variance algorithm; refuse
nearconstant columns under the original dimensional threshold. Fold means,
source positions and scales never use validation/outer values. No row-count or
weight-sum objective normalization is introduced.

Evaluate bounded Harmonica float64 Jacobian blocks for explicit existing
source coordinates; apply row weights and column scales only as specified.
Forward action accumulates each row's complete source contribution; transpose
action accumulates every eligible row into the same global coefficient vector.
Require an independent adjoint dot-product oracle, chunk-order perturbation
tests and comparison with dense augmented QR/SVD and the unchanged Verde fit.
No solve of G^T G by normal equations. Every matrix/vector/block allocation has
an independently counted byte budget before native calls.

Solver convergence is not inferred from finiteness or reaching maxiter. Check
the actual LSMR stop reason, independent reconstructed residual/objective and
regularized stationarity A^T(Ac-b)+lambda*c. Condition-limit and iteration-limit
stops remain nonconverged; a trivial zero solution is a distinct control, not
evidence of nonzero-signal performance. Exact tolerances/iteration ceilings
must be frozen by dense/operator tests and resource proof BEFORE new survey
values or heldout evaluation. This proposal supplies no invented successful
tolerance/profile and does not relax the original frozen controls.

Selection uses only full inner-fold validation. One final fit and one complete
outer evaluation preserve the full scored/excluded/support denominators and
per-line metrics. Stream grid predictions on the requested source-free plane
and higher planes; exported tiling does not change global sources or introduce
new resolution. Spectrum/FFT continuation require a declared complete support
rectangle and independent memory proof; no inpainting of holes. Preserve
directions, reference lineage, observed-minus-predicted residual signs and
denied raw members. Full survey data do not become independent field truth.

## Necessary implementation gates and ownership boundary

Proposed ordinary new executor: data-pipeline/magnetic_survey.py; new tests
tests/data/test_magnetic_survey.py and tests/numerics/test_magnetic_survey.py;
paired wrappers gain an explicit reviewed survey tag after its exact schema
exists. Old contracts/Results remain immutable and continue to refuse >400
ordinary rows or >256 sources. A survey result has a distinct schema and
chunk-custody manifest, not a falsely relabeled magnetic-result/1.

Required gates: streamed cap/depth/native-type/duplicate/ordinal negatives;
exhaustive source-order/chunk identities; geometry sealed before values;
training-only source/scales/crossover graph; adjoint/dense/operator/oracle
parity; whole-line leakage perturbations; actual heterogeneous-height dipoles;
full support/gap/alias/no-downward tests; deterministic chunked export/replay;
rights-restricted external arrays; decoder-to-fsync whole-process CPU/RSS/
scratch/cancel proof at actual useful shape; genuine eligible provider/user
files with quantitative metrics and an independently reviewed reference.

No survey row/source/CPU/RSS/disk ceiling is advertised as measured here.
Geometry-only counts and owned-device availability determine a prospective
local profile whose whole-process measurements must pass or refuse before
field science. Larger offline budgets do not change the512MiB/60s bounded
profile or imply VPS admission. Actual field byte access/dictionary, original
correction dependencies, altitude datum, sigma and numeric comparison remain
unresolved. Provider-product prediction and independently sealed end-to-end
correction validation are separate outcomes. Existing S1 and both opened
refinement failures remain immutable. No API/auth/storage/frontend/deployment
change or full-method acceptance is part of this executor seam.
