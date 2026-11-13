# Local first-arrival data flow and algorithms

Explicit local JSON bytes -> bounded stdlib validation -> original identity ->
cell-length ray operator -> weighted classical inverse and optional frozen CNN
-> physical arrays/diagnostics -> independently reopened local JSON generation.
No provider or server connection occurs. The caller separately opts into a
checkpoint path and its SHA-256. No external executable is selected by JSON.

Version1 deliberately matches the existing checkpoint's 800 m square,16x16
cells, z-positive-down frame. Arbitrary supplied straight segments within this
domain are accepted (8..2048); the physical approximation is straight-ray
tomography, not bent-ray first arrivals, elastic imaging or FWI. Geometries
other than the exact training A/B layouts and noise other than1 ms are reported
as outside the trained acquisition/noise domain. Even A/B inference retains the
failed family/acquisition benchmark. The bounded CNN has a600 m/s perturbation
range around2000+0.35z; high-contrast models outside this range are not supported.
The separate M09 field solver is not replaced by this tool.

Closed request keys: schema,id,source,frame,units,ray_ids,rays_m,times_s,sigma_s,
lambda. Source keys: citation,rights,scope (owner-provided or synthetic-control).
Rights must be owner-permitted or CC0 or CC-BY; citation is nonempty. Frame is
local-x-z-down, units exactly distance=m,time=s,velocity=m/s. IDs are unique ASCII
letters/digits/underscore/hyphen,1..64 characters. All coordinates lie in[0,800]
m; endpoints differ by at least1 mm. Time and standard deviations are finite
positive seconds (time<=100,sigma<=10). Lambda is explicit finite[1e-6,1e6], not
selected on user truth. Raw JSON<=512 KiB, depth<=12 and nodes<=40000, scanned
before scientific imports; only exact native numeric types, not booleans.

For q=1000(s-s0), s0=1/v0, C=A/1000, and W=diag(1/sigma), the weighted
objective is

    min_q ||W(Cq-(t-As0))||^2 + lambda||Dq||^2 + 0.01||q||^2

subject to the cellwise velocity bounds represented in slowness coordinates:

    1000(1/4000-s0) <= q <= 1000(1/1400-s0).

The positive ridge makes the quadratic Hessian positive definite. The current
implementation solves this box-constrained quadratic with a deterministic
primal active-set method: it solves on the current free face, advances only to
the first blocking bound, and releases a bound when its multiplier violates
the KKT sign condition. It does not solve an unconstrained system and clip the
result afterward. The solver stops only when the projected KKT residual is at
most 1e-9 relative to the declared scale. The producer reconstructs q from the
serialized velocity grid and independently recomputes that residual before an
export can be reopened as a successful v2 generation. D uses the existing
dimensionless neighbour differences. Sigma is supplied by the user and is
never estimated from residuals.

An independent SciPy bounded least-squares solve is used as a numerical
optimizer control on the same Hessian, right-hand side and physical box. The
control compares model values; it shares the declared ray matrix, so it cannot
validate the ray geometry or establish independent geophysical accuracy. A
small KKT residual proves optimality only for this finite straight-ray
quadratic and its supplied data, not that the straight paths represent bent
first arrivals in an unknown earth.

CNN input uses only observed times and supplied A through the existing fixed
backprojection/coverage transform. Load and evaluate the real checkpoint with
no training or fallback. Predictions from A are data fits; alternate bilinear Q
predictions expose discretization sensitivity, not independent measured truth.
Both quantities are labelled and retained. Every residual is observed-predicted.
Coverage is ray path length per cell in metres, not posterior uncertainty.

Output is one bounded canonical UTF8 result.json (<=4 MiB) plus manifest.json,
written exclusively in a new output directory, flushed and independently
reopened/hash/shape checked before a manifest marks completeness. Manifest binds
exact original SHA-256/bytes, request, source modules, checkpoint if used and
result SHA-256/bytes. No raw mirror, pickle/ZIP, canonical rebake, frontend/API
mutation or implicit installation. The original request is retained in the
result; original file remains read-only. CLI exceptions produce fixed public
errors/nonzero exit. Tests use fresh scratch and preserve failed generations.
