# Ordinary induced-prism forward operator

## Physical meaning and limits

`forward_magnetic(request)` in `data-pipeline/magnetic_forward.py` evaluates actual
SimPEG0.25.2 scalar induction with Geoana0.8.1 integral kernels. Geometry is a
nonuniform discretize0.12.0 TensorMesh, with an explicit active-cell mask and
dimensionless SI susceptibility chi in[0,0.1]. A positive susceptibility can
produce either sign of projected magnetic anomaly. No self-demagnetization,
remanence, variable background field or terrain geometry is inferred.

The background amplitude F is in nT. Inclination I is positive downward;
declination D is clockwise from geographic north. With angles in radians,
the east,north,up unit vector is

```text
f = (cos(I) sin(D), cos(I) cos(D), -sin(I))
B0 = F f                         [nT]
M = chi B0 * 1e-9 / mu0          [A/m]
```

The [versioned SimPEG source](https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/simpeg/potential_fields/magnetics/sources.py)
and [coordinate implementation](https://raw.githubusercontent.com/simpeg/simpeg/v0.25.2/simpeg/utils/mat_utils.py)
define these conventions. The operator checks its explicit ENU direction against
the actual engine source vector. It does not query IGRF or choose a survey epoch,
field datum, acquisition height, reference field or correction state for a user.
Those physical inputs must be authenticated separately.

![Bounded input, actual induced engine, distinct quantities and separate oracles](induced-prism.svg)

For the secondary vector b at each receiver, three different outputs matter:

```text
field_components_nt = (b_east, b_north, b_up)           [nT]
linear_tmi_nt = f dot b                               [nT]
exact_magnitude_anomaly_nt = |B0+b| - F                [nT]
```

Linear TMI is a projection, not the east component, vertical component or exact
change in field magnitude. The operator also returns the linear-TMI derivative
J with respect to each active chi in nT per unit SI susceptibility. J is not the
derivative of the exact-magnitude output.

To preserve tiny nonzero anomalies, the scalar computation is rationalized:

```text
delta_F = (2 B0 dot b + b dot b) / (|B0+b| + F)
```

The positive F bound protects the denominator. Secondary/background ratios and
exact-minus-linear differences are diagnostics, not automatic field eligibility
thresholds. There is no default field, inferred uncertainty or geologic truth.

## Closed native-array contract and preflight

The [complete request/result contract](../../design/features/m04-induced-prism/contracts.md)
is normative. The seven request keys are schema,engine,frame,mesh,receivers_m,
susceptibility_si,inducing_field. Nested dictionaries have exact native string
keys; every enum is explicit. Numeric arrays are native float64 ndarrays, except
the native boolean full-cell active mask. No subclass conversion, list coercion,
float32 promotion, extra key, angle wrapping or backend fallback occurs.

All array metadata and count caps are checked before array finite scans or copies.
The native scalar field is validated independently. Only after metadata passes
are bounded arrays scanned and privately copied. The caller must keep inputs
private during snapshot; this is not a concurrent mutation protocol.

| Quantity | Bound and ordering |
| --- | --- |
| Widths | 1..64 per axis; each1e-3..1e5 m; axis span<=1e5 m |
| Geometry | Origin and edges within[-1e7,1e7] m; finite increasing faithful edges |
| Full mesh | At most65536 cells; x-fast full-cell order |
| Active mesh | 1..8192 cells; chi follows ascending active full-cell indices |
| Receivers | 1..2048 rows; metre ENU; original row order; coordinates within[-1e7,1e7] |
| Projected entries | N*n_active<=4194304 before kernel construction |
| Background | Native finite floats; F in[1,1e6] nT, I in[-90,90], D in[-180,180) degrees |

Actual component sensitivity storage has3*N*n_active float64 entries. At the
declared maximum that is12582912 entries,100663296 raw bytes. This is the matrix
alone, not peak RSS or a guarantee of admission under a host memory limit.
Normal local tests exercise small physical cases. The exact-cap test stops after
metadata preflight, before mesh/kernel construction; it is not an upper-memory
benchmark. Native resource containment and cold/warm upper allocations are
separate unaccepted gates.

Independently constructed declared bounds are compared against actual public
TensorMesh nodes, widths, cell bounds, ordered corners, strict interior centres
and volumes at the frozen1e-10 local relative geometry tolerance. A small width
at a large origin can fail representability; it is not silently shifted.
Every receiver must lie strictly outside the closed full rectangular mesh.
Interior, face, edge and corner locations are rejected even in an inactive cell
or when chi is zero. The exterior restriction is stronger than individual active
prism singularity handling and is part of this ABI.

## Actual engine, ordering and snapshots

The operator explicitly constructs `UniformBackgroundField`, a receiver with
components `["bx","by","bz"]`, an active IdentityMap, and
`Simulation3DIntegral(model_type="scalar", engine="geoana",
store_sensitivities="ram", sensitivity_dtype=np.float64, n_processes=1)`.
It is not a hand-written substitute for SimPEG. Kernel rows are receiver-major,
component-second. The native G@chi versus native dpred identity is checked at
atol1e-10 nT,rtol1e-12. Projection gives J without changing the component kernel.
Unexpected kernel/prediction dtype, shape or nonfinite values are errors.

Output arrays are independently owned C-order snapshots, with OWNDATA=true,
base=None and WRITEABLE=false at return. They share no storage with inputs or
each other, and input bytes/write flags are unchanged. Ordinary indexed writes
fail initially, but an owner can reenable its own array's WRITEABLE flag. That
reversible flag is not tamperproof immutability. Dictionaries are ordinary
mutable dictionaries. The operator retains no returned storage as trusted state.
Persisted-byte hashes can detect changes; durable storage contracts remain a
separate capability.

Every result explicitly retains `field_source_verified=false`,
`full_method_accepted=false` and `host_approved=false`. Errors are local native
exceptions with private causes, not a safe HTTP response contract. The ordinary
function performs no file/network/cache/CLI/optimizer workflow. Python/vendor
imports themselves are not claimed to require no file access.

## Independent acceptance controls

The [frozen validation specification](../../design/features/m04-induced-prism/validation.md)
separates three independent checks:

1. The actual [Choclo0.3.2 prism function](https://www.fatiando.org/choclo/v0.3.2/api/generated/choclo.prism.magnetic_field.html)
   uses independently enumerated six prism bounds and ENU magnetization in A/m.
   Its returned tesla is converted once to nT. Components and projected TMI
   use atol1e-7 nT,rtol2e-8. J columns use mathematical chi=1 in one prism,
   M=B0(T)/the actual Choclo mu0, and atol1e-7 nT per SI,rtol2e-8. This derivative
   oracle never submits chi=1 to the production0.1-limited request and does not
   imply physical neglect of self-demagnetization at chi=1.
2. Independently integrated physical dipoles use tensor-product16/24/32-point
   Gauss-Legendre volume quadrature on frozen distant exterior controls. The24/32
   convergence gate is atol1e-8 nT,rtol2e-8 before analytic comparison at
   atol1e-7 nT,rtol2e-8. A separate far-field dipole control requires distance
   >=20 largest cell dimension and vector relative error<=0.003. Choclo and
   quadrature do not reuse candidate G, geometry helpers or predictions.
3. Portable stdlib Decimal uses80 digits,ROUND_HALF_EVEN and Decimal.from_float
   on every binary64 component before a direct square root and subtraction.
   This independently checks tiny scalar algebra, not physical components.
   F=50000 nT,B0=(0,50000,0) nT with transverse b=(+/-1e-4,0,0) nT gives
   positive anomalies near1e-13 nT; parallel b=(0,+/-1e-10,0) retains sign.
   Each nonzero value must be nonzero, sign-correct and within2e-8 relative
   error with no absolute floor. The null is exactly zero. There is no Windows
   longdouble dependency, skipped oracle or platform fallback.

Cardinal and oblique fields, off-origin asymmetric/nonuniform active geometry,
receiver ordering, null chi, scaling and signed lobes are physical controls.
Authored remanent M=(8,-5.5,2.3) A/m and a changed field orientation demonstrate
different modeled data. They are synthetic counterexamples, not a field
remanence classifier or evidence of recovered geology. Contract negatives trap
preflight ordering, all native types/keys, count and physical bounds, runtime
epochs, malformed engine state, derived overflow and deterministic MemoryError.

## Reproduce locally without changing an environment

This source epoch is CPython3.12.10 Windows64, not a portable Linux deployment.
Use an already provisioned isolated environment whose actual installed sources
match the [research hashes](../../design/features/m04-induced-prism/research.md)
and relevant shared M02 source/native pins. The numerical suite verifies those
targeted files externally; the forward function does not verify file hashes.
Required observed versions are SimPEG0.25.2,Geoana0.8.1,discretize0.12.0,
NumPy2.2.6,SciPy1.15.2,Choclo0.3.2,Numba0.67.0,llvmlite0.49.0.
Generic dependency installation alone does not establish those source identities.

From the repository root, PowerShell:

```powershell
$m04Python = (Resolve-Path .venv-pipeline/Scripts/python.exe).Path
$m04Run = Join-Path ([IO.Path]::GetTempPath()) ('m04-forward-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $m04Run | Out-Null
$env:PYTHONPATH = (Resolve-Path data-pipeline).Path
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
$env:NUMBA_NUM_THREADS = '1'
$env:NUMBA_CACHE_DIR = Join-Path $m04Run 'jit'
& $m04Python -B -m pytest --noconftest -p no:cacheprovider -o addopts= -q `
  tests/numerics/test_magnetic_forward.py --junitxml="$m04Run/results.xml"
if ($LASTEXITCODE -ne 0) { throw 'M04 local tests failed; preserve the receipt' }
```

Equivalent Git Bash on Windows, using the same approved Windows interpreter:

```bash
m04_run=$(mktemp -d)
export PYTHONPATH="$(cygpath -m "$PWD/data-pipeline")"
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1 NUMBA_NUM_THREADS=1
export NUMBA_CACHE_DIR="$(cygpath -m "$m04_run")/jit"
./.venv-pipeline/Scripts/python.exe -B -m pytest --noconftest -p no:cacheprovider \
  -o addopts= -q tests/numerics/test_magnetic_forward.py \
  --junitxml="$(cygpath -m "$m04_run")/results.xml"
```

These commands create fresh private outputs, do not install packages and bypass
the repository conftest only because PYTHONPATH is explicitly set. Preserve the
first expected missing-module RED separately from subsequent execution; never
replace a failed scientific receipt with a successful one. A local replay is
not an online worker, physical data admission or independent full-method review.

For an ordinary Python call after setting that path, this fully authored example
uses metre ENU geometry, three exterior receivers and explicit field values:

```python
import numpy as np
from magnetic_forward import ENGINE, forward_magnetic

request = {
    "schema": "magnetic-prism-forward-request-1", "engine": ENGINE,
    "frame": {"kind": "local_cartesian", "axes": ("east", "north", "up"),
              "length_unit": "m", "vertical_positive": "up"},
    "mesh": {"origin_m": np.array([-50., -40., -120.]),
             "hx_m": np.array([100.]), "hy_m": np.array([80.]),
             "hz_m": np.array([120.]), "active": np.array([True])},
    "receivers_m": np.array([[0., 0., 100.], [170., 30., 120.], [-100., 160., 240.]]),
    "susceptibility_si": np.array([.03]),
    "inducing_field": {"amplitude_nt": 50000., "inclination_deg": 60.,
                       "declination_deg": 12.},
}
result = forward_magnetic(request)
print(result["field_components_nt"])
print(result["linear_tmi_nt"], result["exact_magnitude_anomaly_nt"])
```

The numbers are an original synthetic control, not a recorded acquisition,
field licence, height/datum assertion or accepted survey. There is no inverse
fit, IRLS model, uncertainty estimate or held-out prediction in this function.
Those and the strict user-data/resource/storage/API/UI vertical remain required
next, using an independently accepted optimizer dependency and a reviewed survey
extension rather than rebranding this forward calculation as full M04.
