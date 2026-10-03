# Independent ordinary gravity-L2 candidate review

Date: 2026-10-03. This is a partial local candidate review, not accepted full L2,
submitted-data API, field modelling, GPU/host or product capability. Source
candidate is `8acab62e46cb6cd4707adcd90c18a95343d3b48c`, against the fully read
and narrowly approved seven-document sub-SDD
`48245d1a947870758553e612be1a0a2e3e823afb`. Later source/tests need their own
exact-diff review and execution; no receipt transfers silently.

MAIN fully read355-line native planner,119-line private objective constructor,
the complete three new test files and their frozen contract. The constructor
uses real SimPEG3D integral gravity and official L2DataMisfit/WeightedLeastSquares;
it does not accept a supplied engine or kernel. This milestone has no public
calibration/evaluation, recorded optimizer or complete24-case acceptance yet.

Planner source SHA-256:
`4bc6788f7c46bc2a36bcd871989becf535c03d9702bb1034949ecc37ed040c01`.
Objective source SHA-256:
`0f37fcafa440dafdd899a24d636be9d0557a7fb5a08e7004c84db31e086c19e4`.

## Actual independent focused execution

MAIN created a detached candidate review tree and fresh external private scratch,
using the existing pipeline interpreter read-only with bytecode disabled, one
numerical thread and separate private Numba cache. No installation, provider
acquisition, environment/dependency file, accepted forward/scientific source,
canonical artifact, tolerance or historical receipt changed.

```text
<READ_ONLY_PIPELINE_PYTHON> -B -m pytest
  tests/data/test_gravity_survey_l2.py
  tests/numerics/test_gravity_l2.py
  tests/numerics/test_gravity_l2_selection.py
  tests/numerics/test_gravity_forward.py
  -o addopts= -q -rs -p no:cacheprovider
  --basetemp <FRESH_PRIVATE_ROOT>
  --junitxml <FRESH_PRIVATE_RECEIPT>
```

Result:134 passed, zero skips/deselections,1.89 s:54 new planner/objective
controls and80 unchanged accepted forward controls. Actual JUnit SHA-256:
`bd261f2ac5d0edefd611680caddd40fe12bcddc5f0856f4ffa0c9b8a953d52e1`.
The source-pin test read and compared28 actual installed source/native files:
the earlier20 forward pins plus eight additional exact SimPEG objective/
regularization/optimization sources. Loaded versions were NumPy2.2.6,
SciPy1.15.2,SimPEG0.25.2,Geoana0.8.1. The review checkout stayed tracked-clean.
This actual local numerical run is distinct from inexpensive CI guards.

## Additional independently authored physical/objective control

MAIN authored a new private helper, not the producer's tiny fixture. Mesh origin
is(-320,-140,-510) m; widths east(70,110,90), north(80,140), up(120,60) m,
with x-fast active indices(0,1,4,6,9,11). Five outside receivers are
(-100,50,140),(500,-450,80),(-450,300,-900),(20,-200,350),(100,200,220) m.
Declared signed contrasts are(250,-450,600,-800,300,1000) kg/m3 and independently
fixed backgrounds(.002,-.003,.001,.004,-.002) mGal. These are authored physical
control inputs, not measured geology or an inverse fit.

Choclo gravity_u on independently enumerated prism bounds supplies the physical
Jacobian and observations. Full covariance is0.005^2*(0.65 I+0.35 ones) mGal^2;
prior scale750 kg/m3, lengths(60,110,75) m and reference(10,-15,25,-40,5,0)
kg/m3. Candidate beta1 gives engine beta5. Private evaluation q is
(.12,-.3,.8,-.2,.5,.7) g/cm3, direction(.4,-.2,.1,.3,-.1,.2).

The independent model stencil uses each explicit prism volume divided by total
active volume and scale^2, plus pairwise BOTH-active shared faces weighted by
mean neighbour volume, physical centre separation and the declared directional
length. There are(1,2,1) shared east/north/up faces. It does not import the
engine's stencil or bridge inactive cells. The independent data quadratic uses
the original covariance solve, not the whitening helper under review.

All frozen objective/physical-J/gradient/Hessian/whitening/directional gates
passed. Maximum actual absolute discrepancies:

| Quantity | Absolute discrepancy |
| --- | ---: |
| J, mGal/(kg/m3) | 7.587721141504022e-18 |
| Unhalved data objective | 9.537259870739945e-12 |
| Model objective | 4.440892098500626e-16 |
| Physical-density gradient | 4.228561945041065e-14 |
| Physical-density Hessian direction | 1.3782920117721975e-17 |
| W C W transpose versus I | 6.661338147750939e-16 |

Normalized directional errors at steps1e-2/1e-3/1e-4 were respectively
1.0127523313826117e-14,1.0708918170730949e-13,6.020249969885526e-14.
Both adjacent-step conditions pass without changing tolerances. The private
authored helper SHA-256 is
`99e731b0629a52a5541bbe7e8287c021d20bcd93dcd83dc1e71e8e01f7f049de`.
This checks local physics/objective units, not a bounded optimum, identifiability,
posterior covariance, sealed-selection accuracy or field truth.

## Independently confirmed pre-admission resource gap

The actual source's native metadata walker counts scalar nodes/text/arrays,
but empty dict/tuple containers add neither metadata bytes nor scalar count.
Per-container length32768 and depth8 do not alone bound total structural work.
The walker precedes semantic root/field shape rejection. Therefore malformed
shared nested containers can require much more work than the declared metadata
budget before the public planner finally rejects them.

MAIN ran a bounded, non-giant counterexample in the same actual interpreter:
`x=(((),)*32768,)*5`. Its compact native JSON representation is491531 bytes,
above the262144-byte metadata cap, yet `_native_metadata(x)` returns None.
The root is not an admissible planning request; this is a preflight/resource
negative, not a science/field acceptance. A wrong known field can similarly
contain empty nested structures. No enormous allocation, copy, engine or provider
run was needed. The initial command's shell-quoting SyntaxError is a retained
harness failure; corrected quoting executed the same stated counterexample.

MAIN notified the producer for a test-first bounded correction, preserving the
frozen32768 SCALAR-node semantics, valid native inputs and no caller-hook
execution. Any necessary exact byte-accounting clarification requires review;
silently loosening caps or merely claiming the later semantic rejection fixes
pre-admission work is not acceptance. The134 physics/shape controls above remain
their genuine candidate result, but this resource gap BLOCKS full-unit promotion.

## Remaining acceptance

Required next gates: independently review/replay the metadata fix; exact native
public observations/noise/prior/configuration validation; recorded projected-GNCG
stop/terminal/bound behavior; independent bounded BVLS optimum; all24 frozen
candidate/fold fits, separate sealed evaluation; complete predeclared24-case
and actual operational resource matrix; final complete source/tests/evidence and
independent peer review. No API/storage/UI/worker/browser/host/field/GPU or main
activation follows from this private constructor/planner milestone. All larger
product unresolved/failed verdicts and protected earlier evidence remain.
