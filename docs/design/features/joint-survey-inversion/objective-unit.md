# Development-only physical objective unit

This additive contract refines JS08 before implementation. It evaluates the
already defined objective/derivatives; it never optimizes, selects candidates,
refits on validation, consumes sealed observations or integrates an optimizer.
The nonlinear algorithm proposal at the earlier pin remains unchanged.

## Exact native request

`evaluate_joint_objective(request: dict) -> dict`, no I/O, callbacks, injected
Jacobians/regularizers/simulation objects, private M02 imports or JSON execution.
Exactly six keys: `schema=joint-survey-objective-request-1`, `survey_request`
(native seven-key planner contract), `development`, `models`,
`direction_physical`, `weights`.

development exactly `plan_sha256` (64 lowercase hex), `gravity`, `magnetic`.
Each modality exactly `rows` int64(M,), `observed` float64(M,), `noise_values`,
`observations_sha256`, `noise_sha256` (same hex grammar). M2..2048 and MUST match
concatenation of that modality's admitted training rows then validation rows,
not all original/held-out rows. Every row occurs once. No separate test/truth
key is accepted. Diagonal_sd noise_values is float64(M,), positive SD in the
planner's physical units; full_covariance is float64(M,M), exact symmetric SPD
in squared units. No jitter/floor/pseudoinverse. Cholesky check the whole declared
development covariance; for objective whitening use ONLY its principal training
block. If cross_partition=declared_absent, the training/validation cross block
must be exactly zero. possible_not_removed retains dependence warning.

observations_sha256 is the normative native descriptor digest of
{rows, observed, unit, plan_sha256}; noise_sha256 of
{rows, noise_values, unit, kind, plan_sha256}. Arrays have dtype/shape/C-byte
SHA descriptors as in contracts.md. These bind row identity and declared units,
not only a bare value vector. Integrity is not source authenticity.

models exactly `density_kg_m3` and `susceptibility_si`, native float64(active,)
within supplied property bounds. direction_physical is native float64(2*active,)
density then susceptibility, same unit semantics as the structural unit.
weights exactly builtin finite floats `beta_gravity`, `beta_magnetic`, `coupling`.
Each beta belongs to the frozen eight candidates, coupling belongs to
(0,0.001,0.01,0.1,1,10). This unit cannot choose/tune these values or alter limits.

ALL request types/shapes/dimensions, planner/array/descriptor and projected-kernel
limits precede finite scans, snapshot/hash/mesh/forward calls. The full objective
request counts96MiB logical arrays including covariance, aliases, models and
direction;256KiB descriptors. No additional resource/field/GPU admission is
inferred. This unit shares the actual pinned CPU/Windows engine epoch.

## Calculation and exact result

Use actual accepted public gravity/magnetic forward functions to create real
physical J; no user-supplied kernel. Marginal training Cholesky whitening and
separate data terms, fixed physical scales, active-neighbor quadratic model
penalties and actual SimPEG coupling are exactly algorithms.md. Both exact
and approximate Hessian-vector actions are returned; the latter is never tested
as an exact Hessian. No dense combined Hessian is required. Volume/area/distance
pair enumeration uses only two active neighbors and actual validated geometry.

Result exactly `schema=joint-survey-objective-1`, `plan_sha256`, `objective`,
`terms`, `gradient_physical`, `exact_hessian_vector_physical`,
`approx_hessian_vector_physical`, `predictions`, `diagnostics`.
terms exactly data_gravity, data_magnetic, regularization_gravity,
regularization_magnetic, coupling (unweighted scalar terms, finite builtin floats).
objective is their exact weighted sum by the declared weights. Gradient and both
Hv arrays are owned/read-only float64(2*active,), physical chain1/scale.
predictions exactly gravity/magnetic dicts, each rows int64(M,), observed,
predicted, signed_residual float64(M,), and unit. These include validation
predictions for inspection, but validation observations NEVER enter F/g/Hv.
diagnostics exactly inverse_completed=false, field_eligible=false,
sealed_consumed=false, cross_partition_dependence (bool),
training_rows_gravity(int), training_rows_magnetic(int).
Source hashes and raw access are externally verified, not claimed by this unit.

## Predeclared controls

Use signed/nonuniform3x2x2 mesh, six active cells0/1/4/6/9/11, six irregular
outside receivers per modality. Independent Choclo supplies physical kernels and
controlled observations; its matrices and explicit pairwise R plus separate
triangular whitening are the oracle, never producer G/R/W. Fixed correlations
0.35 ones+0.65 I, physical SD0.005 mGal/1 nT; both diagonal and covariance modes.
Compare full weighted objective and normalized-coordinate gradient/exact Hv
at atol1e-10,rtol1e-9 and all three directional steps from validation.md.
This is a mathematical derivative control, NOT inverse recovery.

The earlier validation protocol's five-receiver control is additionally exercised
in both noise modes, not replaced by the six-receiver control. The training and
validation counts stay two each; the fifth receiver is the single sealed geometry
row whose observations are absent. Independently compose the full PSD search-Hv
from the data/quadratic-model Hessian and explicit Gram coupling approximation;
do not compare that approximation to an exact quartic Hessian. Check that every
returned array is owned/C-contiguous/read-only and that inputs remain unchanged.

Negative tests: row duplicates/order/sealed IDs, nonnative arrays, metadata caps
before scans/copies/hash/engine; negative SD, asymmetric/semidefinite covariance,
false absent-dependence declaration; stale plan/value/noise hashes; model/weight
types and bounds, injected callback/kernel/test/truth fields. Mutating validation
observations while recomputing integrity hashes MUST leave F/g/Hv identical;
altering training observations MUST alter actual data terms/gradients.
No change to frozen caps, physical tolerances, seed or baseline/search policy.
