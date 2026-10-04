# Global streamed Ridge: numerical and lifetime specification

Revision1, prospective, frozen before new survey value access. The scalar
physics is the approved [global1/r proposal](full-survey-operator-proposal.md),
not gradient-boosted tiling. The [closed contract](full-survey-contracts.md)
and [gates](full-survey-validation.md) are normative. No old result or cap is
changed. New ordinary module namespace is magnetic_line_survey, distinct from
the separate magnetic_survey inversion-acquisition module.

## Objective, units and engine

For training XYZ x_i and explicit training-only sources p_j,
G_ij=1/||x_i-p_j|| in m^-1. Stable two-pass unweighted population variance
defines s_j=std(G_:j,ddof=0), without centering G in the fit. First pass sums
in canonical row order with compensated accumulation; second sums squared
deviations from the fixed first-pass means. Reject s_j nonfinite or
s_j<=1024*float64_epsilon*max_i(G_ij), the unchanged dimensional guard.
N>=2, positive distances, finite representable coordinates/weights/scales.
No StandardScaler constant-column fallback or invented field sigma.

A_ij=sqrt(w_i)G_ij/s_j; b_i=sqrt(w_i)y_i. Solve
F(c)=||Ac-b||_2^2+lambda||c||_2^2. c is nT; q_j=c_j/s_j is nT*m.
Unweighted w=1 has F in nT^2 and dimensionless numerical lambda.
Independent one-sigma w=1/sigma_nT^2 has dimensionless F and lambda nT^-2.
No weight normalization, mean subtraction, intercept, fit thinning or extra
baseline. The candidate arrays and tie rule are unchanged; new user choices
must be fixed before values, not inherited from opened synthetic failures.
The operator returns complete global contributions, not a windowed objective.

Harmonica0.7.0's explicit-source float64 Jacobian is used for bounded blocks;
forward and adjoint use the same ordered training/source map. Do not substitute
its GB residual/window algorithm. Verde1.9.0's
[tagged source](https://raw.githubusercontent.com/fatiando/verde/v1.9.0/verde/base/least_squares.py)
defines the scaled Ridge convention; physical q is unscaled after the solve.
Only already installed pinned engines are used; no internal package.

[SciPy1.15.2 LSMR](https://docs.scipy.org/doc/scipy-1.15.2/reference/generated/scipy.sparse.linalg.lsmr.html)
is called with LinearOperator, damp=sqrt(lambda), atol=btol=1e-12,
conlim=1e8, maxiter=2000, show=False, x0=None. Fixed one native thread and
zero initial guess; never continue a failed candidate with outer-based tuning.
Codes1,2,4,5 are necessary but insufficient success. Codes3,6,7 refuse.
Code0 requires independently verified zero gradient; nonzero b orthogonal to
A is a legitimate algebraic zero optimum, but is explicitly a zero-solution
control and is not nonzero-signal predictive evidence. Nonfinite estimates,
conda>=1e8 or exceeded actual limits refuse regardless of stop code.

## Independent stationarity and numerical tolerances

After releasing solver temporaries, recompute independent direct1/r blocks
from the original admitted training geometry, not the Harmonica Jacobian,
LSMR recurrence normar, cached prediction or library adjoint. Use original
weights, frozen scales and returned c. Reconstruct r=Ac-b and
g=A^T r+lambda*c. Observed-minus-predicted public residual is y-Gq, the
opposite of r before weighting. Accumulate gradient and objective in fixed
source/row order with compensated sums; independent action blocks are bounded.

D=max(||A^T b||_inf,||A^T Ac||_inf,lambda||c||_inf).
Require ||g||_inf/D<=1e-9 when D>0; when D=0 require g exactly zero.
No absolute floor in physical nT units that could admit an arbitrarily small
bad solution. Compute/check each term for finite representability; zero caused
by underflow refuses. Also report ||g||_2/lambda in nT, an a posteriori
coefficient numerical-error bound from Hessian A^T A+lambda I, NOT geological
or measurement uncertainty. Large bound alone cannot upgrade predictive
acceptance. Record raw data and penalty terms and their finite sum; do not
call an LSMR estimate the independently reconstructed objective.

These thresholds are frozen before new predictive observations. Independent
operator controls require adjoint relative dot error<=1e-12, using denominator
max(|<Av,u>|,|<v,A^Tu>|,||Av||_2||u||_2,||v||_2||A^Tu||_2) and exact-zero
branch. Chunk geometry/scales relative agreement<=1e-12; actions absolute
error<=1e-11*max(1,max absolute dense action) in that action's stated units.
Dense augmented QR/SVD oracle prediction max error<=1e-7*max(1,RMS dense
prediction) nT; objective relative difference<=1e-8 with exact-zero branch.
These NEW solver controls do not weaken any unchanged ordinary formula,
source/geometry, old S1 or100/50 predictive tolerance. No outer retuning if a
new solver gate fails; diagnose or retain nonconverged evidence.

## Geometry, calibration and full workflow

First hash/count original raw and auxiliaries in bounded reads. Geometry-only
stream builds exact dictionaries, external ordinal/unique-ID indexes, admitted
adjacencies and unjoined masked gaps. Stable external sort (key, original
ordinal) retains every row and ID. Dictionaries/indexes use a bounded disk
store, no million-row Python object inventory. Decode admitted actual lag
navigation before geometry seal, retaining masks and original geometry.
Sources use the original half-open block arithmetic and sorted-row-ID fsum
representatives; do not alter block width because source count exceeds cap.

Spatial index only prunes geometrically disjoint segment bounding boxes.
Enumerate ALL remaining flight/tie pairs with the original intersection,
height/time/channel policies, shared-endpoint representatives and rejected
reasons. Count candidate pairs before materializing records; over-cap refuses,
never truncate. A full graph component gets one original lexicographic tie
gauge, no tile-specific zero. Sparse incidence graph solve uses explicit
independent rank/gauge and residual controls, not a dense millions-column
allocation. An empty fold calibration remains ineligible. This graph solve is
distinct from the scalar1/r Ridge operator and must not share its lambda.

Whole-line outer and three inner partitions, anchors, buffered tie endpoint
exclusions, acquisition-gap and support masks are sealed from geometry before
values. Candidate corrections/crossovers/scales/source maps are reconstructed
inside each training fold. Fixed independently provided lag/diurnal/heading/
old-new reference evidence stays explicit; no full-survey fitted provider
calibration passes as independent test correction. Original reference/data
rights and datum remain gating, never guessed. Fit exactly24 inner candidates,
select only from inner validation, fit final once, evaluate outer once. Optional
geometric comparator adds at most one fit; failures retain per-candidate causes.

Prediction streams global source contributions in source-order rows and
northing-major/easting-minor grid cells. Higher planes require compatible known
datum and positive source-free height increments; no downward continuation.
Complete-rectangle spectrum/FFT has its own preallocated phase budget and
ordinary normalization/window/mask tests. No hole fill. Export grid tiling is
storage only, not separate geological or regression fits. Residual/source/
reference/correction identities are independently replayed from permitted
originals; no old-source receipt becomes a current-origin claim.

## Prospective offline profile: capacities, not measurements

Profile m03-offline-stream/1 is local-only and PROVISIONAL until actual cold
whole-request checks pass. Limits:8,000,000 original rows,65,536 lines,
4 sensors,65,536 sources per fold,16,000,000 auxiliary records combined,
8,000,000 candidate crossover pairs,26 fits,128 arrays,192 logical members,
1,048,576 total exported cells,4,194,304 internal FFT cells. Raw CSV<=4GiB;
all auxiliary originals<=4GiB combined. Original ordinary400/256/512MiB/60s
and local400/320 profiles do not inherit these larger limits.

R=4096 and C=128 are maximum operator rows/sources per block; last blocks
may be smaller. No entire N*M or M*M array is allowed. Chunk working-set
ceilings are checked before actual NumPy/native calls and include temporary
products. LinearOperator dtype is explicit float64 so no speculative type
probe opens data. Actual runtime/source/native pins are verified before imports
and measurements, not assumed from names. Matrix-free is O(N+M), NOT O(R*C).
The [tagged SciPy source](https://raw.githubusercontent.com/scipy/scipy/v1.15.2/scipy/sparse/linalg/_isolve/lsmr.py)
retains N-vector b/u and M-vector x/v/h/hbar with action/ufunc temporaries.

| Phase | Conservative simultaneous controlled byte allowance |
| --- | --- |
| Ingest/seal/crossover | 128MiB parser/index/cache allowance +32MiB fixed records +32*R*8 +16*C*8 +1GiB import/native/allocator reserve. Disk indexes/page cache are within128MiB, not extra uncounted mapped pages. |
| One fit/operator/stationarity | 8*(32*N+64*M+8*R*C+48*R+24*C) +128MiB cache/decoder +1GiB import/native/allocator reserve. Counts b,u, all returned actions, residual/gradient checks, weights, index/mapped-page exposure and temporary live buffers; no parallel fits. |
| Grid prediction/export | 8*(16*R+64*M+8*R*C+24*C)+128MiB cache/decoder+1GiB reserve. N-vector solver buffers released before phase; grid output stays chunked on disk. |
| Spectrum/FFT | 16*16*Q+8*16*P+128MiB cache/decoder+1GiB reserve. Q internal FFT complex cells, P total exported cells; no simultaneous N-vector fit buffers. |

Independent code allocation planner must enumerate actual owned arrays and
native entry shapes, not just echo these formulae. These conservative formulas
are rejection allowances, not proofs of native workspace or page residency.
At the row/source ceilings fit allowance is3,324,665,856bytes; FFT ceiling
is2,415,919,104bytes. Compute the integer formula from actual P/Q and reject
if over4GiB. Actual peak RSS and committed
memory each<=4,294,967,296bytes independently. A claimed native reserve cannot
hide a measured excess. Device lacking available headroom refuses before
allocating, without lowering scientific resolution.

Scratch bound is 2*(raw_bytes+auxiliary_bytes)+512*N+256*M+
256*crossover_candidates+256*P+128*Q+268435456bytes. It counts original
copies, typed geometry/channels/masks/indexes, partition/candidate summaries,
staged+final artifacts and custody; no simultaneous26 prediction caches or
unaccounted file-backed RAM. Before every stage count actual owned scratch and
remaining estimate; refuse if>34,359,738,368bytes or available free space.
Dense control oracles have separate small-N/M bounds; never execute dense SVD
under the full-survey profile.
At all declared maxima the scratch formula is24,414,388,224bytes, before
independent actual free-space/owned-byte checks; it is not measured usage.

Geometry seal also records a kernel-pair upper bound, sum over all25 mandatory
fits of N_f*M_f*(4+2*2000), plus actual grid/query/operator-check pairs; it must
be<=10^15. Two scaling passes, forward/adjoint iterations and independent
verification are counted. This is an arithmetic cap, NOT timing evidence.
Record actual iterations/call/pair counts without replaying fits just to count.
Large source geometry may fail this cap; no hidden GB/coarsening/thinning fix.

Cold process-tree CPU<=21600s, wall<=43200s, scratch<=32GiB, one active
child/no descendants, threads1. Stop at21540CPU or43140wall, reserving60s
CPU and60s wall to drain/retain terminal custody. Explicit cancellation must
stop within10CPU and10wall seconds. Parent controller CPU<=300s through
child drain, final own receipt write timed separately and reported explicitly.
Sampling<=100ms, lifetime RSS/committed/CPU/exit counters queried after death;
unavailable counters refuse. Start before interpreter/import/decoding, finish
after export/hash/fsync/terminal counter queries, not just inside lsmr.
Fit-local timings are descriptive subdivisions of that cold lifetime, not
replacement ceilings. Budget expiry cannot produce a successful partial solve.

Before any new full-study values, geometry/max-source/preallocation and real
zero-target/native-workload cancellation profiles must pass at the actually
proposed geometry. Thirty cold useful-shape runs and tail/headroom/native host
checks remain admission gates; this provisional local profile is not VPS
admission. No measured full-survey success is asserted by this document.
