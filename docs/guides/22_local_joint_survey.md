# Local supplied gravity and magnetic inversion

This is a private local scientific workflow, separate from the browser's cached
joint example. It uses physical SimPEG/Geoana prism kernels, signed density in
kg/m3, nonnegative SI susceptibility and the actual SimPEG face-averaged
CrossGradient. It neither deploys a service nor uploads observations.

## Prepare external immutable inputs

Set `GEOPHYSICS_LOCAL_DATA_ROOT` or pass `--data-root` to an existing external
directory. Explicit development, sealed, frozen-input and output directories
must lie beneath it and be mutually disjoint. Scratch is a separate explicit
external ordinary directory. Repository ancestors, links/junctions, implicit
cwd roots, existing outputs and input/output nesting reject. Inputs are never
overwritten, deleted or extracted from arbitrary uploaded archives.

The development channel contains request.json and exactly28 fixed NPY arrays;
see [original-byte intake](../design/features/joint-survey-inversion/intake-unit.md)
and [exclusive writer](../design/features/joint-survey-inversion/serialization-unit.md).
Supply a common declared ENU frame, exact physical mesh/bounds/units, inducing
field, globally consistent acquisition groups and preassigned train/validation/
sealed partitions. Source hashes are integrity commitments, not correction
science, verified rights or field eligibility. Missing physical metadata is
not repaired from a catalogue label. Inactive cells do not become zero-valued
regularization neighbors. Receiver rows remain global immutable IDs.

Create the separate sealed channel before calibration using
`write_joint_sealed(directory, plan, data)`, then bind its returned file digests
in `write_joint_development`'s sealed_manifest. Sealed has six exact NPY arrays
and sealed.json; it is not an argument to the calibration callable. Values are
opened only after actual selection and durable frozen.json. Covariance values
are marginal physical-unit-squared SPD matrices, not correlations or conditional
errors. There is no pseudoinverse, jitter, SD floor or covariance repair.

## Execute and inspect the complete method

Use the pinned pipeline interpreter, not an arbitrary system interpreter:

```powershell
python scripts/run_joint_survey.py solve --data-root $JointDataRoot `
  --development "$JointDataRoot/development" --sealed "$JointDataRoot/sealed" `
  --output "$JointDataRoot/solution" --scratch-root $JointScratchRoot
python scripts/run_joint_survey.py validate --data-root $JointDataRoot `
  --development "$JointDataRoot/development" --sealed "$JointDataRoot/sealed" `
  --output "$JointDataRoot/solution" --scratch-root $JointScratchRoot
```

The solve performs eight beta fits for each independent modality, then five
positive coupling strengths from two starts. Every actual failure remains in
calibration.json and its trace arrays. Selection uses validation only; there is
no validation/test refit. The lambda0 comparison concatenates the two separately
optimized baseline models; it is not a fictional additional fit. Each positive
candidate must stay within1.05 of EACH baseline validation WRMS. No eligible
positive candidate gives `no_validated_coupling_benefit` and the uncoupled model.
The shared nonlinear export is a reviewed candidate source, not by itself a
parent-accepted science certificate. Original precision failures remain visible.

Output directories contain the actual26-fit calibration ledger (or16 attempts
when no stationary separate baseline exists), frozen model, partition result,
physical-unit models/geometry directory and workflow.json. NPY arrays are loaded only with allow_pickle=False after exact
file inventories, dtype/shape/header/cap/hash checks. Physical traces retain
density then susceptibility in their distinct units. Normalized q in the frozen
record uses the fixed supplied prior scales; do not call it a physical property.
Result residuals are prediction minus observation; each modality and partition
has its own physical RMSE, WRMS and chi-square. No combined accuracy score hides
a failed modality. See [calibration protocol](../design/features/joint-survey-inversion/calibration-unit.md)
and [evaluation protocol](../design/features/joint-survey-inversion/evaluation-unit.md).

Validation rebuilds the actual physical kernels, replays original F/KKT and
projected Armijo states, baseline/coupling selection and each partition result.
It rejects stale inputs, weights, source inventories, fabricated terminal or
summary values and changed exported predictions. This is not a signature or
proof that another person's file was executed; no authenticity is inferred
from an origin label. Resource receipts contain measured elapsed time, sampled
process RSS and bytes in the explicit scratch directory, plus actual private
export bytes. Sampling is not an OS reservation or hard realtime guarantee.

If the workflow expires or scientific replay fails, failure.json and the aborted
directory retain genuine accepted-state evidence. They explicitly deny completed
inversion/evaluation and record whether a freeze exists or a sealed read started.
The completed-workflow validator rejects such partial outputs. Keep those files
for inspection; reruns require a different new output directory. No automatic
retry, deadline reset, cleanup deletion or successful coupling claim follows.

## Evaluate a supplied model without claiming a solve

`freeze_joint_model` and `write_frozen_model` create a strict physically bounded
model commitment. `evaluate` accepts its external directory and exports genuine
physical predictions and marginal statistics without optimizer claims:

```powershell
python scripts/run_joint_survey.py evaluate --data-root $JointDataRoot `
  --development "$JointDataRoot/development" --sealed "$JointDataRoot/sealed" `
  --frozen "$JointDataRoot/supplied-model" --output "$JointDataRoot/evaluation" `
  --scratch-root $JointScratchRoot
```

Evaluation has inverse_completed=false even if an imported origin/digest says
optimized_selection. A solve receipt requires the separate actual calibration
ledger and its scientific replay. Field eligibility, verified rights/correction
science, geological recovery and global optimum are never established by fitting.
These exports include supplied observations and are private, not public bundles.

## Reproduce the adverse and resource matrices

`scripts/validate_joint_matrix.py` runs all24 fixed refined-source Choclo cases,
strict solve/export/replay, each original beta control against the independent
test-only raw BVLS return and post-freeze truth discrepancies. Raw BVLS exact-KKT
failures, production nonconvergence, precision failures and ineligible positive
coupling remain cell records; a completed CLI is not scientific precision PASS.
`scripts/validate_joint_resources.py` runs maximum simultaneous admitted mesh/
receiver/export counts with full marginal covariance and analytical zero-property
data. Its actual large kernels and26 fits measure resources; it is explicitly not
a recovery benchmark. The nonzero nominal gate is the separate24-case matrix.
All generated arrays, receipts, caches and plots belong in configured external
device storage, never in the product checkout or system temporary directory.
