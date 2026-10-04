# Additional independent active-face reference, not a solver amendment

The first actual refined matrix reference run retained32PASS/24FAIL. Every
failed control stopped at an independently computed exact-bound KKT requirement;
SciPy success is deliberately insufficient. This does not establish24 optimizer
failures in M11: production M11 optimization has not run.

Actual case0,beta0.0001 gravity: BVLS status1/nit14/reported optimality
5.824108624302889e-13, but one coordinate is1.9999999999999998, upper2.0,
reported active_mask=+1 with true gradient-0.1285353542511816. Its returned point
is one representable float inside the face, so exact-bound projected KKT treats
that derivative as free. The original independently normalized KKT is
0.0018707088358199072, FAIL against the unchanged1e-5 gate. No raw returned-point
success is inferred. Full pinned installed bvls.py was inspected: LoopB updates
x by a convex combination, records on_bound separately, and its reported KKT
uses on_bound rather than an exact-coordinate comparison.

Before supplementary test implementation, define a DIFFERENT test-only reference:
use the reported active_mask merely as a proposed face, set those coordinates
to the EXACT submitted normalized lower/upper values, then solve the free-face
dense linear least squares once with explicit augmented A/b. Independently check
all feasible bounds, total gradient and exact-bound projected KKT against the
ORIGINAL1e-5 threshold. Wrong faces, infeasible free solutions, nonfinite states
or failed KKT reject; no mask iteration, tolerance radius, jitter or alternate
production fallback. Positive smallness makes the augmented convex problem
strictly convex, so feasible KKT provides the reference's mathematical check.

Keep BOTH raw vendor point/KKT/status/nit and separate face-reference point/KKT/
cost/delta. Do not rewrite first24 failures or call the new reference the raw
SciPy returned optimum. Compare production physical OBJECTIVE evaluation with
the independent face reference using the unchanged F/g/prediction tolerances.
This is additional mathematical/oracle evidence, not a production optimizer,
native stop/direction change, reference mask imported into production, source
prism change, threshold relaxation or whole inverse/selection acceptance.
