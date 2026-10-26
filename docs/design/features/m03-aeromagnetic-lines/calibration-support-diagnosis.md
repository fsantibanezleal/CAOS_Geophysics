# Calibration support under the original geometry seal

This intrinsic diagnosis retains the original
[geometry/candidate definition](algorithms.md#2-geometry-only-sealed-evaluation).
No buffer, validation line, source map, tolerance or candidate is changed.
Geometric prediction support and crossover-calibration support are different
conditions. The former does not establish the latter.

For original S2, all heights are80m, and the scalar plane is
10+.002e-.003n nT with independently authored flight offsets2*(i-3)nT
and tie offsets0. The original outer training partition has enough admitted
crossovers for its relative-gauge offset check. Independent offsets can
calibrate a line held out of that graph without using its magnetic values.
These are explicit supplied constants, not a field uncertainty or fitted truth.

Original inner fold A contains five training flights and just three tie
records:363 originals become168 training records after complete-line holdout
and the union of closed outer/inner tie buffers. Inventorying the original
adjacencies within that training identity admits **zero crossover constraints**.
No QR solver can infer line offsets from an empty constraint graph. Retaining
three tie rows or geometric hull/distance coverage1 does not create crossings.
The independently supplied heldout offsets do not silently replace the
requested training-crossover estimator with another operation.

Accordingly, the current combined training-leveling request is physically
ineligible in this fold before any candidate fit. An initial integration-test
expectation of successful full leveling/CV failed; that evidence is retained,
not promoted as a successful run. The separate exact S2 graph/offset diagnostic,
independently calibrated outer correction and S3 instrument-correction/CV replay
remain different controls. The original S1 predictive5% gate remains failed;
this calibration diagnosis neither explains away nor alters that result.

A future amended processing-validation definition must independently provide
enough training-only crossings in every fold, or explicitly define and review
a distinct independently calibrated-offset operation and its applicability.
It needs prospectively sealed new geometry/control identities and untouched
validation observations. Reusing the already opened S1/S2 outer data to select
new buffers, source resolution or correction options cannot create a new
untouched test. No such amendment or positive test is silently substituted here.

This distinction follows rank identifiability of
min||W^(1/2)(Co-d)||^2 with an explicit tie gauge. Missing graph edges are
not recovered by the harmonic grid. See the
[crossover/offset equations](algorithms.md#4-crossovers-and-offsets) and
[scientific nullspace/scaling description](https://www.fatiando.org/verde/v1.9.0/api/generated/verde.base.least_squares.html).
