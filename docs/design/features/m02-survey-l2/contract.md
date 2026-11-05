# Exact ordinary submitted-survey L2 protocol

Status: planned. No code/test authority; MAIN must read the complete sub-SDD.
Base `1b112bb258520a5679a865335cec30b6a97a1a0d`. Numerical gates NOT RUN.
[Design](design.md), [requirements](requirements.md), [controls](validation.md).
This is a native in-memory scientific contract, NOT JSON/upload/API admission.

## Common strict types, caps and identity

Every dictionary/key/string/tuple/int/float/bool is EXACT builtin type, checked
before equality, hashing, conversion or other user hooks. Numeric arrays are
EXACT numpy.ndarray, native float64 (F64), int64 (I64) or bool (B), no subclasses,
object/complex/float32/byte-swapped arrays or coercion. C/F layouts allowed;
private copied arrays returned readonly. Caller must not mutate during snapshot.
No unknown keys/defaults/aliases. A float scalar is builtin float, finite; an int
is builtin int, never bool. All identifier strings use ASCII `[A-Za-z0-9_.:-]`,
length 1..128; explanatory text is builtin Unicode str, <=1024 code points.
SHA is lowercase `[0-9a-f]{64}`. Units/enums below are literal str constants.

Before ANY array traversal/copy/equality/digest/population/factorization/engine:
validate every supplied array's exact type/dtype/ndim/shape and all counts.
At most n=2048 full known receiver rows, N=4096 full tensor cells, a=1..N active
cells; axis lengths 1..4096. Caps include excluded and sealed geometry. Aggregate
input array storage <=96 MiB, native metadata <=256 KiB UTF-8, <=32768 scalar
nodes, <=8 container levels. Reject cap violations before scans; modest oversized
arrays suffice for negative tests. After metadata, bounded masks/populations and
array finiteness/alignment checks precede copying. No pickle, objects, import
paths, callbacks, URLs to fetch, destination, engine selector or RNG arguments.

Canonical native digest v1: ndarray -> dict exactly {dtype, shape, sha256}, where
dtype is `<f8`, `<i8` or `|b1`, shape is a list of builtin ints, SHA hashes logical
C-order little-endian bytes; scalar negative zero becomes 0.0; tuples become
lists. Builtin metadata dictionaries serialize with sorted keys, UTF-8,
ensure_ascii=False, allow_nan=False, compact separators, no trailing newline.
Content digest hashes those bytes. Dtypes are checked before this bounded encoding;
no user-provided digest replaces computing identity of supplied normalized arrays.
Original raw SHA/size and third-party processing receipts remain externally
verified declarations, not claims that this no-I/O unit fetched their bytes.

## 1. Geometry-only planning request

Proposed `plan_gravity_l2(request: dict) -> dict` has EXACT eight root keys:

| Key | Required content |
| --- | --- |
| schema | `gravity-survey-l2-plan-request-1` |
| source | Source dictionary below |
| frame | Existing forward four-key local_cartesian/east,north,up/m/up frame, unchanged |
| mesh | Existing forward five-key origin_m/hx_m/hy_m/hz_m/active contract, unchanged |
| stations | Station dictionary below |
| background_mgal | F64 `(n,)`, fixed upward mGal; zeros require source anomaly/background citation |
| split | Exact fixed-policy split dictionary below |
| engine | Existing `simpeg-0.25.2-geoana-0.8.1-f64-ram` |

Source EXACT keys: `source_id` identifier; `source_kind` enum `synthetic_control`,
`user_upload` or `field`; `raw_sha256` SHA; `raw_bytes` int 1..1073741824;
`citation` nonempty text; `rights` enum `private_only`, `derivative_only` or
`redistributable_declared`; `processing_sha256` SHA; `processing_kind` enum
`synthetic_anomaly`, `m01_declared_derivative` or `provider_declared_derivative`;
`quantity` exactly `processed_gravity_anomaly`; `reference_description` nonempty
text; `original_acceleration_unit` enum `mGal`, `microGal` or `m/s2`;
`original_vertical_positive` enum `up` or `down`; `normalization_sha256` SHA;
`horizontal_reference` nonempty text; `vertical_reference` nonempty text;
`transform_sha256` SHA or None; `geometry_uncertainty` exactly
`conditional_fixed_geometry`. None transform means source supplied the declared
metric local coordinates, not that a CRS conversion was verified. Missing/unknown
reference description, vertical datum or correction meaning rejects; listing a
name does not certify its external accuracy. Synthetic processing kind requires
source_kind=synthetic_control; field/user require a declared derivative kind.
There is no boolean to assert source/field/full-method approval. Absolute/raw
gravity, opaque FAA/CBA labels, unspecified corrections and equivalent-source
coefficients are not the declared quantity and reject. This unit neither corrects
gravity nor converts a provider height/datum or resolves source rights itself.

Stations EXACT keys: `station_ids` tuple of n distinct identifiers in original
row order; `partition_group_ids` tuple of n identifiers, with repeated acquisition
members given SAME group; `receivers_m` F64 `(n,3)` in the declared metric frame;
`excluded` B `(n,)`, true means excluded from fit/score; `exclusion_reasons` tuple
of n text strings, empty iff not excluded, nonempty iff excluded. Exact duplicate
receiver XYZ rejects even across excluded rows; repeated-measurement covariance
admission is unsupported. Every geometry row must be finite and satisfy the
accepted forward closed-box rule, even excluded rows. Unknown coordinates cannot
be inserted as zero/NaN; preserve such raw rows upstream, outside this ordinary
contract. Geometry-only excluded rows can receive predictions, NEVER scores.

Background is fixed independently of fit/validation/outer values. No hidden
demean, intercept, regional fit or derivative correction. Known background error
belongs to declared observation covariance or to separate unaccepted alternatives.

Split EXACT keys: `policy` exactly `blocked-hash-3fold-sealed-1`;
`block_origin_m` F64 `(2,)`; `block_size_m` F64 `(2,)` positive;
`buffer_m` float >0; `seed` int exactly 104729. Values freeze before observation
delivery. Coordinate block IDs use floor((east/north-origin)/size), require
representable finite int64 indices. Union SAME block or SAME partition group,
transitively, before assigning units. Identity of a unit is its sorted station
ID tuple, independent of row order. Sort units by SHA256 of canonical
{seed, station_ids}, lexical tuple as collision tie-break. At least 12 eligible
occupied blocks and 12 resulting units required; no silent random-point fallback.
Excluded rows do not form eligible units; an excluded row sharing a group does
not free the included members of that group's allocation constraint.

Reserve first ceil(unit_count/5) units as sealed outer. Remaining units ordered
as above cycle fold index 0,1,2 for validation. Remove development rows within
horizontal Euclidean distance <=buffer of ANY sealed receiver permanently
(embargo); each inner fit removes rows within <=buffer of its validation
receivers. Buffer distance uses coordinates only; never observations/errors/truth.
No group/block can straddle fit/validation/outer roles. Outer and each validation
set need >=10 rows; each buffered fit >=40; final development >=50, and at least
six development units survive outer embargo. Every fit/final set needs horizontal
coordinate rank 2 and nonzero extent in both axes under design's numerical rank
rule. Infeasible buffers/groups/masks reject, not thinner buffers or more seeds.
No uncertainty/candidate fitting occurs during planning.

Plan result EXACT keys: `schema`=`gravity-survey-l2-plan-1`, `request` (private
snapshot of the eight-key planning request), `plan_sha256`, `development_rows`
I64 `(m,)` ascending, `outer_rows` I64 `(h,)` ascending, `embargo_rows` I64
ascending, `folds` tuple of three EXACT dicts {`fold`: int0/1/2, `fit_rows`: I64,
`validation_rows`: I64, `buffer_rows`: I64}, `geometry` (the unchanged forward
geometry dictionary), `scope` exactly `ordinary_local_conditional_not_field`.
Plan SHA hashes result contents excluding its own SHA. Accepted-forward geometry
is checked using an explicit zero-density request; its nonzero J is not a fit.
Planning returns no data values or scores and owns no sealed-observation storage.

## 2. Development-only calibration request

Proposed `calibrate_gravity_l2(request: dict) -> dict` EXACT seven root keys:
`schema`=`gravity-survey-l2-calibration-request-1`, `plan`, `observations`,
`noise`, `prior`, `policy`, `runtime_epoch`=`m02-survey-l2-cpu-1`.
Plan is the complete exact result above, rehashed/recomputed for consistency;
arbitrary prepared engine objects are forbidden.

Observations EXACT keys: `rows` I64 `(m,)` exactly plan.development_rows;
`gz_up_mgal` finite F64 `(m,)`; `values_sha256` SHA recomputed for this compact
row/value record; `acceleration_unit`=`mGal`; `vertical_positive`=`up`.
NO outer/excluded/embargo values, truth array or nullable data array enters
calibration. Original values remain in owner storage; no imputed-zero missingness.
For normalized values the upstream conversion is explicit: down flips once;
microGal -> mGal factor .001, SI -> mGal factor 100000; density -> q factor .001.
This exact callable accepts ONLY normalized metre/upward-mGal/physical-kg/m3.
No geographic degrees, feet, tilted vertical, unit guessing or conversion inside.

Noise EXACT keys: `kind` enum `diagonal_sd` or `full_covariance`; `values` F64,
`unit`=`mGal` for SD or `mGal^2` for covariance; `basis` enum `measured_gaussian`,
`propagated_independent_gaussian` or `explicit_conditional_gaussian`;
`citation` nonempty text; `values_sha256` SHA of kind/unit/rows/values;
`cross_partition_dependence` enum `declared_absent` or `possible_not_removed`.
SD shape `(m,)`, all >0. Covariance shape `(m,m)`, exactly symmetric in supplied
float64 values, finite SPD, numerical condition <=1e8; no silent symmetrization,
nugget/eigenvalue clipping, diagonal approximation or 3% floor. Exact symmetry
is a declared covariance representation rule, NOT an exact nominal mesh rule.
Tests must distinguish measured SD from conditional assumptions/conservative
bounds. Unknown error scale, conservative_bounds or None rejects weighted fit.
Mask/row alignment is compact development order. Principal submatrices are
formed independently for fit/validation; no whitening full data before splitting.

Prior EXACT keys: `lower_kg_m3`, `upper_kg_m3`, `start_kg_m3`, `reference_kg_m3`
F64 `(a,)`; `density_scale_kg_m3` float >0; `lengths_m` F64 `(3,)` >0;
`basis` nonempty text; `reference_in_smooth` bool exactly True;
`spatial_weights` exactly `none`; `geometry_sha256` SHA of plan.geometry.
Every lower<upper, start/reference within closed bounds, all finite. Scalar
broadcasts/infinite bounds/positivity default/zero-density jitter reject. Bounds
and reference have independent scientific rationale, not holdout/truth tuning.
Signed contrast valid; density scale is a declared normalization, not clipping.
No depth/sensitivity weighting, changed mesh, beta schedule, learned checkpoint,
IRLS/epsilon or nuisance fit in this unit.

Policy EXACT keys: `name`=`ordinary-l2-beta-grid-1`; `beta_candidates` tuple of
EXACT floats `(0.0001,0.001,0.01,0.1,1.0,10.0,100.0,1000.0)`;
`optimizer`=`projected-gncg-recorded-1`; `training`=`not_applicable_classical`.
No caller-supplied tolerances/stops/candidate arrays/seeds; all are frozen in design.

## 3. Separate sealed evaluation request

Proposed `evaluate_gravity_l2(request: dict) -> dict` EXACT keys: `schema`=
`gravity-survey-l2-evaluation-request-1`, `frozen_calibration`, `observations`,
`noise`. Frozen calibration is the exact result defined in [design](design.md),
with verified result SHA and terminal model/source/config/plan identity. Its
success must predate disclosure; in-memory hashes alone cannot certify owner
storage timing/access control, which remains main's external responsibility.
Observations have the same five keys as development observations but rows exactly
plan.outer_rows and values `(h,)`. Noise has the same exact seven keys defined
above, with h-order SD/covariance; hash uses outer rows. No optimization,
candidate selection, early-stop choice, background/mesh correction or all-data
refit is permitted here. Cross-partition correlation is disclosed; score is the
outer MARGINAL, never conditioned on development residuals. Metadata/contracts
fail before any numerical work; unverifiable source/plan or nonconverged frozen
model cannot become an accepted heldout result.

Evaluation result exact schemas and unavailable metrics are in design. It does
not write/re-import a portable bundle or assert measured field eligibility. A
later all-data refit, upload decoder, M01/provider mapper or full covariance
cross-group statistical analysis is a separate unapproved unit.
