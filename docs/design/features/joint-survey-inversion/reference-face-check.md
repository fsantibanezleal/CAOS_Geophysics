# Additional independent active-face reference, not a solver amendment

The first actual refined matrix reference run retained32PASS/24FAIL. Every
failed control stopped at an independently computed exact-bound KKT requirement;
SciPy success is deliberately insufficient. This historical reproduction alone
does not establish24 optimizer failures in M11: production M11 optimization had
not run at that reference epoch.

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

## Supplementary execution and retained precision negative

The Oct8 raw reproduction again produced32PASS/24FAIL. After implementation of
the independent exact-face reference, all192 case/beta pairs were evaluated
without stopping at the first raw vendor failure. Raw vendor face landing varies
at individual coordinates with floating-point evaluation; retain each actual
model/status/KKT verdict rather than asserting an immutable vendor failure count.
Case0 remains a separate reproducible exact-KKT adverse witness.

The supplementary probe measured maximum objective disagreement4.7273e-11,
magnetic prediction disagreement2.6178e-10nT and normalized-coordinate gradient
disagreement1.1136e-9. Nineteen of192 near-optimum gradient comparisons fail
the unchanged atol1e-10/rtol1e-9 predicate. These remain failed PRECISION verdicts,
not JS08 acceptance. The tiny original derivative controls still exercise their
original gates. A new separate case14/beta0.0001 test requires the precision
negative to remain observable. No producer kernel, weighting or tolerance changes
were made to conceal it. This near-stationary cross-library gradient comparison
cannot substitute for the full inverse gate's model/prediction/objective/KKT tests
or be called complete M11 acceptance. Original and supplementary red receipts
remain separate; neither is rewritten as a passing historical execution.

## Actual fitted-baseline supplementary control

`scripts/validate_joint_precision.py` consumes the completed frozen24-case matrix
and strict source-bound actual calibration ledgers. It leaves every raw-BVLS
record and original precision failure unchanged. For each actual baseline it
also compares the production return with the already specified independent
exact-face reference. The reference independently verifies feasible bounds and
the ORIGINAL exact-bound normalized KKT1e-5 before comparison; no production
optimizer or fitted model is changed. Relative F1e-8, normalized model1e-5,
physical prediction1e-8 and production exact-KKT1e-5 remain separate predicates.
References that fail their independent KKT are unresolved, not usable optima.
The separate external receipt binds original matrix/calibration manifest hashes
and actual candidate statuses. Its failures remain failures, not a new tolerance,
parent acceptance, field proof or a rewrite of raw-return scientific verdicts.

The frozen actual24-case workflow matrix now supplies all384 baseline fits
(24cases x2modalities x8betas). Every independent exact-face reference passes its
own feasible-bound/originalKKT qualification. Comparing the unchanged actual
production returns fails51relative-objective,63normalized-model,70physical-
prediction and37normalized-exact-KKT predicates at the original thresholds.
These counts overlap; they are not summed. All actual fitted q arrays, raw-BVLS
records and original comparisons remain unchanged. The supplement exits1 and
reports `all_scientific_predicates_pass=false`, even though every native workflow
completed its actual CLI/export/replay sequence. Its immutable receipt SHA256 is
2239ee86eaddf7a362452f85000261983725adf737907661f7fc5613f4384aae.
This is a failed full-baseline precision qualification, not inverse acceptance.
