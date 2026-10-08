# Exact induced forward contract

Status: proposed, not an API/upload/serialized survey contract.
Public local function: forward_magnetic(request: dict) -> dict.
Only NEW data-pipeline/magnetic_forward.py and its NEW tests are prospective.

## Request

Exactly seven keys: schema, engine, frame, mesh, receivers_m,
susceptibility_si, inducing_field. Native built-in dicts only, exact string keys,
no unknown keys/subclass coercion/implicit defaults.

schema=`magnetic-prism-forward-request-1`;
engine=`simpeg-0.25.2-geoana-0.8.1-f64-induced-ram`.
frame has exactly kind=`local_cartesian`, axes=('east','north','up'),
length_unit=`m`, vertical_positive=`up`; axes is a native tuple of three strings.

mesh exactly origin_m, hx_m, hy_m, hz_m, active. origin_m is float64 ndarray(3,).
Widths are native float64 one-dimensional ndarrays,1..64 entries per axis;
product<=65536 cells, each finite1e-3..1e5 m, each total span<=1e5 m.
Origin and every resulting edge lie within[-1e7,1e7] m. Edges must be finite,
strictly increasing and representable at the declared local-width fidelity.
active is native bool ndarray(n_full,), at least1 and at most8192 true cells;
flattening is x-fast/Fortran(mesh x,y,z). No inferred terrain or cell centre bounds.

receivers_m is native float64 ndarray(N,3),1..2048 rows, finite coordinates in
[-1e7,1e7] m. N*n_active<=4194304 before any kernel is created. All receivers
strictly outside the closed full rectangular mesh, not only active cells.
susceptibility_si is float64 ndarray(n_active,), finite0..0.1 inclusive, in
ascending active full-cell order. Signed magnetic anomalies remain possible;
negative magnetic permeability contrasts are outside this initial induced lane.
Zero susceptibility is valid; null fields must not trigger an inversion.

inducing_field exactly amplitude_nt, inclination_deg, declination_deg. Each is
a built-in finite float, not bool/int/NumPy scalar. Amplitude1..1e6 nT,
inclination[-90,90] degrees positive down, declination[-180,180) degrees clockwise
from north. No wrap, IGRF lookup, regional removal, field-direction estimation,
magnetization conversion submitted by a caller or remanence declaration is inferred.

The caller must keep every input private during snapshot. Negative-stride or
read-only native arrays are allowed; outputs never alias them. Metadata for ALL
arrays/counts precedes scans/copies. Snapshot finite values only after bounds.

## Result

Exactly ten keys: schema, engine, source_epoch, inducing_field, geometry,
field_components_nt, linear_tmi_nt, linear_jacobian_nt_per_si,
exact_magnitude_anomaly_nt, linearization.
schema=`magnetic-prism-forward-result-1`, source_epoch=`m04-induced-prism-cpu-1`.
Engine literal identical to request. inducing_field adds to its original three
keys direction_enu (owned write-protected float64(3,)) and background_enu_nt(3,).

geometry exactly receivers_m(N,3), active_indices(n_active,) native int64,
active_bounds_m(n_active,6) ordered west,east,south,north,bottom,top,
active_centres_m(n_active,3), active_volumes_m3(n_active,), cell_order=`x-fast`.
All numeric result arrays are finite native ndarrays with independently owned
C-order storage: OWNDATA=true, base=None, C_CONTIGUOUS=true, WRITEABLE=false
at return. Each array is a snapshot, with no shared memory with any caller input
or another numeric result array. The caller's arrays and write flags are unchanged.
Ordinary indexed assignment to a returned array fails while its flag is false.
This is write protection, NOT tamperproof in-memory immutability: an owner can
reenable WRITEABLE and modify its own snapshot. Dicts are ordinary mutable dicts.
The operator never retains or reuses returned storage as trusted future state.

Durable immutability and identity belong to the external persisted-byte contracts
and verified content hashes of immutable stored objects, not to NumPy flags or
this no-I/O function. A hash detects byte changes; it alone does not prevent them.
Persisted storage, export and hash verification are separate later gates, not
implemented or accepted by a forward result.

field_components_nt(N,3) is east,north,up; linear_tmi_nt(N,);
linear_jacobian_nt_per_si(N,n_active); exact_magnitude_anomaly_nt(N,).
The Jacobian is ONLY for projected linear TMI, not exact scalar magnitude.
Its unit is nT per unit dimensionless SI susceptibility. Independent oracle
columns mathematically set chi=1 for one prism at a time, using Choclo
magnetization M=B0(T)/mu0 in A/m and its actual pinned mu0. This linear derivative
oracle is outside the production request domain and never submits chi=1 to the
operator. Production susceptibility remains in[0,0.1].

linearization exactly secondary_to_background_ratio(N,),
exact_minus_linear_nt(N,), maximum_abs_difference_nt(float),
interpretation=`uniform-induced-no-self-demagnetization`,
field_source_verified=false, full_method_accepted=false, host_approved=false.
Ratios/errors are diagnostics, not an automatic physical eligibility threshold.
No pass/fit/truth/uncertainty or inverse-model fields exist in this result.

## Error and runtime boundary

Native TypeError/ValueError/RuntimeError use literal field-specific diagnostics,
not a safe HTTP contract; caller exception causes are private. Invalid protocol,
metadata limits, geometry, field, chi, runtime or engine output must never yield
a successful result. No silent float32 cast, NaN masking, interpolation or backend
fallback. No CLI, file/network/cache/environment/app worker/optimizer behavior.

Runtime fixed to observed CPython3.12.10 Windows64 and observed five engine
versions from research. External harness verifies targeted actual source bytes;
the ordinary operator does not perform or falsely claim filesystem verification.
Linux/other builds need a separately measured source epoch; no portability claim.
