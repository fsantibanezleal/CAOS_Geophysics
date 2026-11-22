# Exact initial native planner and later data channels

`plan_joint_survey(request: dict) -> dict` is no-I/O and does NOT solve. Unknown
keys, custom scalar/container/array subclasses, conversion hooks, nonnative
endian/dtypes and implicit defaults are rejected before equality/array operations.
Numbers described as float are exact builtin finite float; integers are exact
builtin int (not bool). Strings are builtin, nonempty, at most4096 UTF-8 bytes.
Array shapes/dtypes/counts for the ENTIRE request precede finite scans, copies,
hashes or engines. All supplied arrays count logically, including aliases.

## Seven planner keys

`schema`, `frame`, `mesh`, `gravity`, `magnetic`, `prior`, `policy`.
schema=`joint-survey-plan-request-1`.

frame has exactly `kind=local_cartesian`, `axes=('east','north','up')` (builtin
tuple), `length_unit=m`, `vertical_positive=up`, `reference_id`,
`horizontal_datum`, `vertical_datum`. The last three are explicit nonempty strings,
not inferred EPSG/datum transformations. Both surveys declare the identical
reference_id. Projected/geographic coordinates must be transformed by a separate
attributed stage; this callable does not implement a CRS projection.

mesh exactly `origin_m` float64(3,), `hx_m`, `hy_m`, `hz_m` float64(axis,),
`active` bool(full,). Each axis2..64; product<=4096; nonempty activity.
Widths1e-3..1e5 m, span<=1e5 m; coordinates/edges within[-1e7,1e7] m.
Declared edges, interior centres, node-derived and declared volumes must be
representable at accepted local geometry fidelity1e-10 (NOT prediction tolerance).
Ordering is x-fast (Fortran xyz) and ascending active full-cell index.
All receivers lie strictly outside the CLOSED full rectangular source volume,
including inactive portions. No automatic topography or inactive zero extension.

gravity exactly `source`, `reference_id`, `component=gz_up`, `unit=mGal`,
`receivers_m` float64(N,3), `mask` bool(N,), `missing_reasons` tuple(N strings),
`groups` int64(N,), `partition` int64(N,), `noise`.
magnetic has these same keys except `component=linear_tmi`, `unit=nT`, plus
`inducing_field` exactly amplitude_nt builtin float[1,1e6], inclination_deg
float[-90,90] positive down, declination_deg float[-180,180) clockwise from north.
ENU direction=(cos(I)sin(D),cos(I)cos(D),-sin(I)); no IGRF inference.

N3..2048 each; exact receiver duplicates within a modality reject, rather than
merge/average. A shared receiver across modalities is valid. Groups are nonnegative
acquisition-block IDs; partition0=train,1=validation,2=sealed-test. Each unmasked
partition must contain at least one row in each modality. Each global group has
one partition across BOTH surveys, including masked rows. Splits are supplied,
not randomly rebuilt on each call. Every masked row has a nonempty reason;
every unmasked reason is the empty string (the only allowed empty text).

source exactly `source_id`, `citation`, `raw_sha256` (64 lowercase hex),
`raw_bytes` int1..1073741824, `rights`, `correction_sha256` (same hex grammar).
The two source IDs must differ; equal original bytes are allowed and reported
(a common multi-modality raw source is not made scientifically independent by
different IDs). rights=`private_use`|`provider_link_only`|`redistributable`.
This is a caller rights declaration, NOT independently verified permission.
Forbidden/unknown rights reject modelling. Only redistributable permits raw bytes
in a public export; private bundles remain access controlled. Citation is text,
not an instruction to fetch a URL or import Python code.

noise exactly `kind=diagonal_sd|full_covariance`, `unit=mGal|mGal^2` for gravity,
`nT|nT^2` for magnetic, `basis=measured_gaussian|propagated_gaussian|conditional_gaussian`,
`cross_partition=declared_absent|possible_not_removed`, `citation`.
No noise array belongs in the planner. Observations/errors arrive in separate
development and sealed channels below; this prevents a planner from fitting on
the sealed values. Cross-modality covariance is NOT supported in this epoch.

prior exactly `density`, `susceptibility`, `lengths_m` float64(3,),
`coupling_length_m` positive builtin float, `basis` nonempty string.
Each property dict exactly `lower`, `upper`, `start`, `reference` float64(active,),
`scale` positive builtin float. Density bounds within[-5000,5000] kg/m³;
susceptibility bounds within[0,0.1] SI; strict lower<upper elementwise.
Start/reference within supplied bounds, no clipping. Lengths and coupling length
1e-3..1e5 m. Scale density1e-3..5000 kg/m³, susceptibility1e-8..0.1 SI.
These prior scales are fixed physical parameters, not trained normalization.

policy exactly `name=joint-survey-l2-cross-gradient-1`, `seed=42`,
`cell_order=x-fast`, `training=not_applicable_classical`,
`group_scope=global_acquisition`, `modal_covariance=independent`.
No additional keyword changes a weight, candidate, optimizer or limit.

## Bounded descriptor and planner result

Compact ensure_ascii=False UTF-8 JSON, separators(',',':'), preserves tuple/list
order, sorts builtin dictionary keys; arrays become exact dict descriptors
`dtype`, `shape`, `sha256`, with a fixed64-character digest slot. Descriptor
metadata<=262144 bytes, depth<=8, scalar leaves<=32768; array bytes<=100663296.
Charge container punctuation/key/escaped-string bytes before child traversal,
including empty containers; no full-tree allocation/hash/value scan in preflight.
Closed expected-schema shape rejection can occur earlier. A size check after
serialization/hash is NOT admission. Scalar counting does not count containers.
Final digests bind C-order array bytes plus dtype/shape descriptors; the plan
identity excludes its own plan_sha256 slot. A digest is integrity, not signature.

Result exactly `schema=joint-survey-plan-1`, `frame`, `mesh`, `gravity`, `magnetic`,
`prior`, `policy`, `resources`, `diagnostics`, `plan_sha256`. Survey snapshots add
`training_rows`, `validation_rows`, `sealed_rows` int64; remove no original rows.
All numeric output arrays are independently owned C-order native arrays,
WRITEABLE=false on return, not tamperproof. Caller storage is never retained.
resources exactly `logical_input_bytes`, `projected_kernel_bytes`,
`projected_export_bytes`, `descriptor_bytes`. Diagnostics distinguish declarations
from verified facts and must include `rights_verified=false`,
`source_bytes_verified=false`, `field_eligible=false`, `inverse_completed=false`.
The native planner cannot assert receipt/source-file verification it did not do.
The exact diagnostics also include active_cells (int), shared_raw_bytes (bool),
common_frame_declared=true, rank_not_assessed=true. Equal raw hashes are visible;
different source IDs alone are not proof of independent geological sources.
Projected export-array bytes conservatively include input arrays, kernels,
36 property traces x251 states xactive_count x8 bytes (16 independent solves,
10 two-property solves), plus54 residual/prediction vectors per survey row.
Calibration must additionally budget its real observation/covariance arrays and
metadata; this planner estimate is not total RSS or complete export acceptance.

`evaluate_joint_structure(request)` is an initial no-I/O objective/derivative
unit, not optimization. Exact keys: schema=`joint-survey-structure-request-1`,
survey_request (the seven-key native planner request), density_kg_m3 float64(active,),
susceptibility_si float64(active,), direction_physical float64(2*active,).
Models must be within declared prior bounds. Direction contains density then
susceptibility components in their respective physical units, not a unitless
velocity or an injected kernel. Total logical array bytes, including these
vectors, obey96MiB before any planner finite scan/hash/mesh construction.
Result exactly schema=`joint-survey-structure-1`, plan_sha256, objective (float),
gradient_physical float64(2*active,), exact_hessian_vector_physical float64(2*active,),
approx_hessian_vector_physical float64(2*active,),
cell_centre_cross_gradient float64(active,) in1/m² for normalized properties,
optimizer_completed=false. Arrays are independently owned C-order/read-only.
The dimensionless objective and the unscaled cell-centre diagnostic remain
explicitly different. No custom weights or kernel/optimizer injection exists.

## Prospective calibration/evaluation and serialized CLI contract

Development channel: per modality exact global row indices equal concatenated
training then validation rows, finite float64 observations of that length, noise
SD vector or symmetric positive-definite covariance of matching dimension,
observation/noise SHA-256 and the bound plan identity. Covariance is in squared
physical units, not a correlation matrix. No floor/jitter/pseudoinverse fallback.
Principal partition submatrices are separately Cholesky-whitened; the planner's
cross-partition dependence declaration remains visible. Sealed channel cannot
be passed to calibration; it binds a frozen selection hash and sealed row indices.
No refit on sealed rows. Masked values are excluded by exact row IDs, never zeroed.

CLI archive is proposed as a bounded directory: `request.json`, independently
hashed `.npy` arrays loaded with allow_pickle=False, raw-access receipts and no
executable objects/paths/URLs. Exact filename allowlist, confinement, symlink,
size, header/shape and hash checks precede array loading; exclusive new output
directory, no overwrite/delete of inputs or canonical directories. This document
freezes native planner types; serialized calibration/export key grammar must be
completed and reviewed before a CLI claims complete import/solve/export support.
That outstanding serialized seam is not silently implemented with loose JSON.
