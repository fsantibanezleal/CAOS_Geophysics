# M11 supplied-survey structural inversion

This feature refines parent SDD section 4 M11 and R-008. It is a local scientific
pipeline, not a replacement of the cached synthetic `joint.py`, an API endpoint,
browser solve, field-validity certificate or deployed service. Numerical gates
below are prospective until their individual execution receipts exist.

## Boundary

The pipeline accepts two independently sourced, explicitly co-registered surveys:
upward gravity anomalies and induced **linear** total-magnetic-intensity anomalies.
Receiver sets need not coincide. Both model properties occupy one declared 3D
tensor mesh and common active-cell mask. Density contrast is kg/m³ (signed);
susceptibility is dimensionless SI in [0,0.1]. No remanence inversion, terrain
construction, CRS conversion, correction, interpolation, unit guessing, PGI,
learned training or IRLS is performed implicitly.

Separate source records, observation uncertainties and correction histories are
mandatory. A common frame identifier is an assertion to be independently checked,
not proof of co-registration. Existing public `forward_gravity` and
`forward_magnetic` are the physical-engine seams. Their accepted source epochs,
runtime restrictions, unit conventions and geometry checks remain unchanged.
No private M02 symbols are imported. A reusable `physical_optimizer` seam is a
dependency only after it exists, is tested and has a reviewed applicable public
contract; a quadratic-only precision certificate cannot certify a quartic joint
objective. Missing that seam does not prevent planner/derivative/oracle gates,
but prevents claiming a completed shared-optimizer integration.

## Named stages

1. **Ingest:** bounded local bytes and immutable raw source receipts, rights and
   format declarations; never fetch a supplied URL. CLI ingestion is separate
   from no-I/O native functions.
2. **Preprocess:** validate already corrected quantities, units, datum, sign,
   component, geometry, masks and uncertainty basis. Reject ambiguity. Preserve
   originals; no replacement of masked/nonfinite data with zero.
3. **Dataset/split:** explicit acquisition-group partitions, fixed before fitting;
   common global group identities across both modalities prevent cross-modal
   leakage. Produce development rows and separate sealed rows.
4. **Feature extraction:** real physical Jacobians and mesh-based regularizers;
   explicit rank/sensitivity/coverage diagnostics, not geological resolution.
5. **Train:** `not_applicable_classical` with reason, not fake fitting/training.
6. **Infer:** two independent bounded weighted-L2 baseline solves; then separately
   recorded nonconvex coupled candidates. Exact proposal in algorithms.md.
7. **Evaluate:** per-modality development/validation/sealed prediction and residual,
   actual objective/KKT/stopping, cross-gradient diagnostics, start/regularization
   sensitivity. Synthetic truth is only an external post-selection evaluator.
8. **Export:** newly created immutable local bundle with input/engine/file hashes,
   original-access metadata, allowed bytes, arrays, traces and methods card.
9. **Validate:** strict re-import, hash/source/shape/unit/identity checks and
   independent physical replay; no canonical bake or training in CI.

## Resources and implementation seams

Only new `data-pipeline/joint_survey*.py`, paired
`tests/numerics/test_joint_survey*.py`, `scripts/process_joint_survey.py` and this
feature/method documentation are implementation paths. Existing sources are
read-only dependencies. Native functions accept exact builtin containers and
native arrays, run no file/network/environment I/O, and expose private caller
errors, not safe HTTP responses. Caller inputs must be private during snapshot.

Initial scientific epoch: CPython3.12.10 Windows64; NumPy2.2.6, SciPy1.15.2,
SimPEG0.25.2, Geoana0.8.1, discretize0.12.0. Independent test oracles use
Choclo0.3.2 and Torch2.14.0+cu126. Actual loaded versions and externally verified
installed-source bytes are required, never inferred from distribution metadata.
No runtime installation or source modification belongs to this feature.

The first executable lane is CPU float64, one process. Prospective admission:
4096 full/active cells, 2..64 cells per axis, 3..2048 rows per modality,
96 MiB logical input arrays, 256 KiB compact descriptor metadata, 128 MiB
projected gravity plus magnetic **three-component** kernels, and 256 MiB
projected export arrays. Total solve budget1800 s, measured peak RSS<=2 GiB,
scratch<=256 MiB are local acceptance gates, not host qualification. Test both
boundary and +1 negatives before scans/copies/hash/engine allocation.
Counts are not a measurement of RSS. Large cases outside these bounds are
ineligible for this epoch, not silently downsampled. CUDA is not a default or
fallback: any later GPU path requires available-resource checks, real measured
compute and numerical/source parity; a Torch oracle alone is not GPU acceptance.

## Interpretation

Cross-gradient penalizes certain misaligned changes, not a petrophysical relation
or proof of shared geology. Parallel, antiparallel or flat gradients can all have
zero penalty; active holes leave unconstrained interfaces. An induced linear
magnetic model can be inappropriate for remanence or strong secondary fields.
Undercoverage/rank deficiency is reported, not repaired by stronger coupling.
Two source records and a small residual never establish field eligibility.
No Bayesian/posterior or unique-geology claim follows from deterministic sweeps.
