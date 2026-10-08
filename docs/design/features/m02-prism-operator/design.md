# M02 pure prism operator design amendment

Status: narrowed implementation approved, 2026-10-03; acceptance pending. Main's
full-read and exact authority are recorded in [tasks](tasks.md). New branch
`task/geophysics-m02-forward-sdd`, aligned base develop
`bc0c573daa511ba897dd0b21e315b8c1eef67413`. PR120 head
`395459bb82cf221be132479358725ce76268ca93` is frozen/merged, its six files unchanged.
This separate folder does not amend the merged plan or close its open contracts.

## Boundary and callable

Proposed new callable `forward_gravity(request: dict) -> dict`, in only
`data-pipeline/gravity_forward.py`; new paired tests only
`tests/numerics/test_gravity_forward.py`. No integration into old potential,
spatial inverse, ingest, station adapter, API, CLI, job runner or UI. No inverse,
uncertainty fit, regularization, holdout selector, learned training or field
admission. A source-bound ordinary linear forward operator is the whole unit.

Input/output are bounded in-memory arrays, not upload assets or wire bundles.
No file/network reads/writes in the callable, serialization, disk sensitivity
cache, engine injection/callbacks, configurable plugins, environment mutations,
canonical interaction, GPU selection, subprocesses or GUI. Normal dependency
loading by the interpreter is not a survey/file workflow. The external read-only
review harness checks dependency file hashes and records commands/tool versions;
the pure operator never pretends it made that filesystem check. Import/cache
behavior is controlled by the harness, not a hidden environment edit in the unit.

## Exact request: six mandatory keys

`dict` means a built-in dict, not an arbitrary Mapping with user hooks. Reject
additional/missing keys; accept no defaults, aliases, strings as numbers or lists
as numeric arrays. Float arrays are exact `numpy.ndarray`, native float64,
finite, dimensionality/shape as below; bool arrays exact ndarray/bool. No subclass,
object, complex, float32 or implicit dtype conversion. C/F contiguous layouts
are both accepted and copied to private C arrays without changing caller values.
Copy before engine construction; caller must not concurrently mutate inputs.

| Key | Exact type and admitted values |
| --- | --- |
| `schema` | str, exactly `gravity-prism-forward-request-1` |
| `frame` | Built-in dict with exactly `kind`, `axes`, `length_unit`, `vertical_positive`; respectively str `local_cartesian`, tuple of str `('east','north','up')`, str `m`, str `up` |
| `mesh` | Built-in dict with exactly `origin_m`, `hx_m`, `hy_m`, `hz_m`, `active`; arrays as specified below |
| `receivers_m` | float64 array `(n,3)` columns east,north,up; integer n in 1..2048 |
| `density_kg_m3` | float64 array `(a,)` of signed physical density contrast, in active-cell order; zeros valid |
| `engine` | str, exactly `simpeg-0.25.2-geoana-0.8.1-f64-ram` |

`origin_m` is float64 `(3,)`, lower west/south/bottom corner. `hx_m`, `hy_m`,
`hz_m` are float64 one-dimensional arrays with nx,ny,nz lengths >=1 and strictly
positive entries. Define `N=nx*ny*nz`; require **N<=4096**, no automatic coarsening.
`active` is bool `(N,)`, with `a=count_nonzero(active)` in 1..N. No whole-volume
density array where an active vector is expected. There are no survey IDs, SD,
observed gravity, CRS transformations, terrain interpolation or corrections in
this operator; such inputs are unknown keys and reject. The mathematical local
frame declaration is not evidence of a field CRS or vertical datum.

Edges in each axis are `origin_axis + concatenate([0], cumsum(widths_axis))`
in float64. Check finite, strictly increasing edges; positive widths that collapse
under floating-point addition reject. Bounds/centres/volumes derived from these
edges must be finite, ordered and volumes >0; overflow/underflow rejects.
No arbitrary geological density clipping. Extremely large finite density whose
conversion/prediction overflows yields a numerical error, not saturation to bounds.

Full source box is the closed rectangle
`[x0,x1] x [y0,y1] x [z0,z1]`. EVERY receiver must satisfy
`x<x0 or x>x1 or y<y0 or y>y1 or z<z0 or z>z1`.
Thus interior, face, edge and corner receivers reject when on/in the closed box.
An inactive air cell or zero-density model does not exempt this check. This is
intentionally stricter than testing only active cells; topographic receivers
inside the tensor envelope are outside this first supported ordinary domain.
No boundary epsilon silently shifts receivers. Distinct observations may have
identical positions: pure forward predictions do not interpret measurement
independence or covariance; future survey admission handles ambiguous repeats.

Cell index `c=i+nx*(j+ny*k)` is x-fast; corresponding displayed volume would be
`[z,y,x]`. Active indices ascend in that full ordering. Derived active bounds have
six columns exactly `[west,east,south,north,bottom,top]`, shape `(a,6)`. Centres
are `(a,3)` east/north/up; volumes `(a,)` in m3. Receiver order is never sorted.

## Genuine engine and unit/Jacobian contract

Use the pinned, already installed SimPEG 0.25.2 / Geoana 0.8.1 /
discretize 0.12.0 stack, no package/environment changes. TensorMesh uses supplied
widths/origin and active mask; gravity Point receivers use component `gz`, a
SourceField and Survey. Simulation3DIntegral explicitly receives
`engine='geoana'`, `store_sensitivities='ram'`, `sensitivity_dtype=np.float64`,
`n_processes=1`, active mask and an `IdentityMap(nP=a)` for active density.
No disk path option, `forward_only`, alternate engine or reconstructed custom G.
Call the official `simulation.fields(q)` with `q=density_kg_m3/1000`.

Pinned engine G has shape `(n,a)`, float64 and mGal/(g/cc). Return
`J=G/1000`, shape `(n,a)`, mGal/(kg/m3), and engine prediction `p`, shape `(n,)`,
upward mGal. Check finite dtype/shape and `p` versus `J @ density_kg_m3` under
rtol 1e-10/atol 1e-12 mGal; never cast a float32 G to conceal precision loss.
Density sign is not flipped: a positive body below receivers gives negative
upward gz. Down-positive or SI inputs are not aliases; upstream must explicitly
convert before constructing this exact protocol. No residual/objective is returned.

Zero density yields zero predicted signal but **nonzero physical J** where
geometry is sensitive. Doubling signed density doubles p, leaves J unchanged.
Reusing a cached kernel keyed only by shape is prohibited; first implementation
constructs its private simulation per call. No caches or hooks added to public API.

Newtonian reference in SI: `g_up(r)=G_N integral rho(r')*(z'-z)/|r'-r|^3 dV`.
Use direct Choclo 0.3.2 `prism.gravity_u` for each active cell in kg/m3/metres,
sum SI contributions and multiply by 1e5 for mGal. The production engine stays
Geoana. Separate quadrature, sphere and point-mass tests check amplitude/sign
without either prism code. Required sources are the [versioned engine API](https://docs.simpeg.xyz/v0.25.2/content/api/generated/simpeg.potential_fields.gravity.Simulation3DIntegral.html),
[pinned source](https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/simpeg/potential_fields/gravity/simulation.py)
and [separate Choclo evaluator](https://www.fatiando.org/choclo/latest/api/generated/choclo.prism.gravity_u.html).
Research verification limits/unavailable reads remain in the [merged dossier](../../../research/m02-survey-inversion-2026-10-03.md).

## Exact result: six keys, no implicit statuses

| Key | Exact type/content |
| --- | --- |
| `schema` | str `gravity-prism-forward-result-1` |
| `frame` | Exact copied four-key frame dict from request |
| `gz_up_mgal` | finite private C float64 ndarray `(n,)` |
| `jacobian_mgal_per_kg_m3` | finite private C float64 ndarray `(n,a)` |
| `geometry` | Dict with exactly the keys below; copied/read-only arrays |
| `provenance` | Dict with exactly the keys below; no fake measured file hashes |

`geometry` keys: `shape_xyz` tuple `(nx,ny,nz)` of builtin ints; `flattening` str
`x-fast`; `active_cell_indices` ascending int64 `(a,)`; `active_cell_bounds_m`
float64 `(a,6)`; `active_cell_centres_m` float64 `(a,3)`;
`active_cell_volumes_m3` float64 `(a,)`; `receivers_m` float64 `(n,3)`;
`density_kg_m3` float64 `(a,)`. Numeric output arrays are private/read-only and
share no memory with caller inputs or a mutable simulation. Exact key checks
are tested for nested outputs as well as requests.

`provenance` keys: `engine` fixed request engine string; `required_source_epoch`
str `m02-prism-cpu-1`; `runtime_versions` dict of observed loaded NumPy, SciPy,
SimPEG, Geoana, discretize version strings; `python_version` str; `precision`
str `float64`; `sensitivity_storage` str `ram`; `n_processes` builtin int 1;
`source_verification` str `external_required_not_performed_by_operator`.
Reject mismatched loaded required package versions before engine construction.
No false claim of measured source hash or successful field validation. This is
not a portable result bundle: external review receipts bind the actual new
operator/test/tool revision, request-case specification and runtime/source hashes.

The [runtime pin manifest](runtime-pins.json) records observed versions and
targeted source/binary digests acquired by read-only metadata/file inspection,
not a new computation. The current proposed source epoch is Windows AMD64 /
CPython 3.12.10. Unsupported runtime or missing/changed external source pins
cannot pass the reviewed harness. A separately reviewed equivalent Linux/runtime
epoch is not authorized by relabelling these Windows hashes. Targeted pins are
not a full transitive supply-chain hash. The original docs-only manifest retains
its planned null operator hash; do not retroactively rewrite that provenance.
Actual implementation/test hashes are bound in the new execution receipts in
[validation](validation.md), never copied from old potential.py provenance.

## Failures, memory and acceptance boundaries

Reject with `TypeError` for wrong protocol/types and `ValueError` for keys/enums,
counts/shapes/nonfinite/geometry. Messages identify field/reason without dumping
private arrays. Engine failures/nonfinite/wrong-shape/dtype/state mismatch raise
`RuntimeError`, preserving the cause; no partial result, fallback, nan_to_num,
silent clip or successful status. Catch ordinary engine exceptions, not system
exit/interrupt/memory exhaustion; callers retain these literal failures externally.
Exception context/cause is private caller diagnostic information, NOT a safe HTTP
response contract; no web exception rendering is part of this operator.

At capped geometry G has <=2048*4096*8 = 64 MiB. G/J/copies and engine internals
need more memory; this cap is not a measured RSS, latency, host or GPU guarantee.
Estimate projected G/J allocation before engine; do not create an inverse Hessian,
uncertainty refits, output files or full-workflow resource benchmark in this unit.
Separate local/host envelopes remain pending under the broader M02 plan.

Only new operator plus paired tests could be authorized after main reads this
amendment. Existing physics, fixtures/canonical/source guards, API/UI, dependency
files and environment stay unchanged. A passing ordinary forward gate would
not accept user-survey semantics, a full inverse, terrain, errors, field geometry,
holdouts, M02 product or deployment. Those remain separately unapproved/unresolved.

## Additive representability investigation and geometry policy

2026-10-03, within main's approved invalid-geometry protection scope. The
original 66/104/164-run receipt and original code/test hashes remain historical,
not reassigned to a new source. Official pinned SimPEG builds Geoana prism
coordinates from actual TensorMesh **nodes**, not centre +/- half-width.
At origin 1e16 and width 2, centre coordinates collapse to a face, but actual
node bounds remain ordered and engine acceleration agrees with Choclo. A
prediction-collapse hypothesis was NOT reproduced. At origin 1e16 and width 3,
node width rounds to 4: actual prism volume is 64 m3 versus framework volume
27 m3 from the supplied widths. Returning consistent shape alone misses this
physical density/volume discrepancy.

Ordinary decimal widths can instead produce harmless one-ULP differences from
sequential node accumulation. An exact-equality nominal-edge admission rule
would reject those grids and is NOT the final policy. Add a separate geometric
fidelity budget **1e-10 relative to local cell widths/volumes**, never relative
to a large absolute origin and never a changed prediction/oracle tolerance.
It requires declared and actual edge/bound differences <=1e-10 of adjacent
local widths, actual node interval widths within that relative budget of
supplied widths, and node-derived volumes within that relative budget of
TensorMesh cell_volumes. This conservative metadata fidelity target permits
the investigated ordinary 1000 m / 0.1 m roundoff (~1e-12 relative width),
but rejects width 3 rounding to 4 and gross density-volume inconsistency.
It is not a guarantee of field-coordinate accuracy or forward relative error
near a cancellation; independent physics tolerances remain separate and unchanged.

All nominal and actual centres must be finite and strictly inside their full
cells, including inactive cells. Verify actual TensorMesh node arrays, actual
bounds, all eight ordered corner coordinates (bounding boxes alone miss a
duplicate corner), actual centres and node-derived volumes. Return actual
verified engine bounds/centres/volumes, not nominal coordinates falsely labelled
engine geometry. Recheck receivers strictly outside the actual full node box,
with no shifts. Verify actual SimPEG active prism corners exactly match the
ordered actual TensorMesh corners before evaluating fields. Structural equality
between views of the SAME actual nodes is exact; nominal floating-point geometry
agreement uses the distinct cell-scale rule above, not exact bit equality.

This fail-closed geometry tightening and its full source diff require main's
independent final review. Counts, required engine, units, shape contract, Windows
epoch, no-I/O scope and every frozen prediction tolerance remain unchanged.
