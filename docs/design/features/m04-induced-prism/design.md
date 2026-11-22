# Induced magnetic forward design and staged dependencies

Status: proposed. Every numerical/ABI/host/field gate NOT_RUN.

## Local flow

Validate exact keys/types and every array's metadata/counts; bounded finite
snapshot; independently construct declared mesh edges/cell bounds; construct
actual TensorMesh; verify its nodes, bounds, corners, centres and volumes against
the declared nonuniform x-fast geometry at1e-10 relative local width/volume.
Reject collapsed edges or nonrepresentable interior centres. Reject receivers
in/on full closed volume before SimPEG. No M02 private helper import/refactor.
Preserve that accepted operator/source/tests untouched.

Construct one magnetics receiver object with components=['bx','by','bz']; one
explicit UniformBackgroundField; scalar Simulation3DIntegral with active_cells,
IdentityMap(nP=n_active), engine='geoana', store_sensitivities='ram',
sensitivity_dtype=np.float64, n_processes=1. No M override or disk caching.
Check actual G is float64 finite(3*N,n_active); reshape receiver-first
component-second to(N,3,n_active), verified by asymmetric independent controls.
Calculate vectors and projected Jacobian; verify actual native dpred components
agree with G@chi to frozen float64 numerical tolerance. Return the exact contract
and independently owned C-order snapshots with WRITEABLE=false at return and
no pairwise/input memory aliasing. Owners can reenable writes; neither arrays
nor result dicts are tamperproof. No returned storage is retained as trusted
future state. Durable identity/immutability requires external persisted-byte
contracts, immutable storage and verified hashes; the forward function performs
none of that I/O. No source field/residual is synthesized from case labels,
and no output is an inverse.

The tiny scalar-magnitude algebraic gate uses portable stdlib Decimal80 direct
sqrt of independently converted binary64 input components, not Windows
longdouble or the candidate's rationalized expression. It is distinct from the
independent Choclo physical component gate. Mathematical unit-susceptibility
Jacobian controls use chi=1 only in the independent oracle, with physical
M=B0(T)/mu0; they do not expand the production chi range. Exact controls and
unchanged component/ordinary-magnitude tolerances are specified in validation.

## Resource boundary

3*N*n_active<=12582912 float64 matrix entries (100663296 raw bytes).
Copies/engine temporary nodes and projected Jacobian make process memory larger;
this is an allocation count, NOT an RSS measurement or online profile. Reject
limits before engine allocation; never downsample, substitute a coarser mesh or
select a cheaper kernel. Cold/warm nominal/upper controls and memory receipts
must later measure actual whole-process CPU/wall/peak, no browser/VPS inference.
One-process means native BLAS/thread context is externally pinned and measured,
not assumed from n_processes. No GPU is asserted for this CPU integral engine.

## Remaining complete M04 vertical

Separate next packet must define immutable survey/processing lineage, units,
background and component meaning, diagonal/full-covariance whitening, masks,
geometric train/validation/sealed holdout, mesh and beta selection, reference/
start/bounds, L2 and sparse/IRLS algorithm/stops, mathematical versus geological
uncertainty, six physically meaningful case regimes, inverse-crime controls,
field rights/metadata and interpretation. Corrected M02 optimizer is a dependency,
not copied while its bounded convergence is still failing. M03 processed output
is eligible only when its exact physical component/correction contract matches.
Neither a gridded RGB image nor harmonic equivalent-source coefficients become
susceptibility observations or known subsurface truth.

Online native admission, storage/API/export re-import, actual linked 3D views,
course/algorithm diagrams/EN-ES UI, whole case matrix and final deployment remain
unimplemented by this forward unit. Author these with their genuine data path;
do not render saved-array replay as an online inverse calculation.
