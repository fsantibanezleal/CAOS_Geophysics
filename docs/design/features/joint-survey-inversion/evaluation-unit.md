# Frozen evaluation and private result directory protocol

This unit implements the already specified development/sealed separation, not
an alternative inversion policy. `freeze_joint_model` binds the normalized
two-property model, fixed weights, physical engine epochs, plan and development
hashes before any sealed value is opened. A supplied-model origin is explicitly
`inverse_completed=false`. Calibration origin is produced by the real bounded
optimizer driver only; stationarity alone is not evidence of an executed solve.
The freeze hash is an integrity commitment, not a signature or permission proof.

All directories are explicit absolute external paths. Existing ancestors must
be ordinary directories, not links, junctions or repositories. New destinations
are exclusive; files use exclusive creation and the JSON manifest is last. No
overwrite, cleanup deletion, URL fetch, archive extraction or executable hook.
Readers require the exact file inventory, NPY v1.0 native float64/int64 arrays,
bounded literal headers, exact descriptor shapes and hashes. Every metadata and
header guard precedes array loading or hashing values. Directory cap is256MiB,
logical arrays96MiB, JSON256KiB/depth8. A concurrent snapshot is not promised.

The sealed directory has `sealed.json` and six fixed arrays named
`gravity_rows`, `gravity_observed`, `gravity_noise`, and the magnetic equivalents.
Envelope keys are exactly schema=`joint-survey-sealed-input-1`, payload, arrays.
Payload has exactly plan_sha256. Descriptor keys are dtype, shape, file_bytes,
file_sha256, data_sha256, as in development intake. Sealed observation/noise
FILE digests must match the development manifest committed before calibration.
Rows exactly equal frozen sealed rows; noise has the declared marginal partition
shape, positive SD or exactly symmetric SPD covariance. No jitter or conditional
use of other partitions. No sealed object can be passed to the fitting driver.

Frozen directory envelope schema=`joint-survey-frozen-model-file-1`, manifest
`frozen.json`, only array `q`. Payload is the frozen native record without q.
Record keys: schema=`joint-survey-frozen-model-1`, plan_sha256,
development_sha256, physical_epochs, weights, origin, selection_sha256, q,
frozen_sha256.
Origin is `supplied_model` or `optimized_selection`; an optimized record also
binds the actual separate calibration ledger through selection_sha256. The
frozen SHA-256 binds every other key, including q. The reader recomputes it.

Evaluation preserves signed residual=prediction-observation and reports each
modality and partition separately: count, physical RMSE, dimensionless WRMS,
chi-square, physical unit. W is diagonal reciprocal SD or a triangular solve
using Cholesky of the PRINCIPAL marginal covariance, not an inverse matrix.
Train-only objective terms and normalized exact-bound projected KKT are recorded
separately. No metric threshold implies recovery, global optimality or coupling
benefit. Truth and field eligibility remain unverified. The explicit warnings
include cross-partition covariance and unverified source rights/corrections.

Result envelope schema=`joint-survey-result-file-1`, `result.json`, fixed model
q and per-modality/partition rows, observed, predicted, signed_residual and
whitened_residual arrays. Result payload binds the frozen hash and sealed file
digests, objective five terms, partition metrics and claim flags. Validation
recompiles the actual physical kernels, verifies the freeze BEFORE sealed reads,
recomputes every prediction/residual/metric/objective and compares the resulting
native record digest. Embedded summary numbers are never trusted as evidence.
The evaluation record always says inverse_completed=false: an optimized origin
and calibration digest are declarations until the separate real calibration
ledger is verified. The solve workflow supplies the execution receipt only after
actual replay; importing an origin label cannot manufacture a completed inverse.
The result is private, includes observations and is not a public redistribution
bundle. It contains no device path. A rights declaration is not a verified grant.

Resource control measures monotonic elapsed time, actual process RSS and actual
exclusive scratch directory bytes; a background sampler plus synchronous
checkpoints enforces1800s/2GiB/256MiB. Sampling is not an operating-system memory
reservation or hard realtime interruption. Over-budget evidence is a failure,
never a completed-workflow resource pass. Maximum-shape projected admission and
complete scientific runtime measurements are separate gates.

Executed regression:46 frozen-evaluation/resource tests pass in both diagonal
and covariance modes. The original-inclusive epoch2 nonlinear/evaluation/resource
suite passes71 tests. These are actual model evaluation and adverse I/O/resource
controls, not acceptance of all26 fits,24 scientific cases or maximum resources.
