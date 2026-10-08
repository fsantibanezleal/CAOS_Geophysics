# Acoustic inputs, optimization and exact storage

## Physical applicability

The current reviewed inverse is a constant-density 2D scalar acoustic engine on
a 128 x 96 [distance,depth] velocity grid, 12.5 m spacing, 0.0005 s internal
sampling, one Ricker point source at each of x={300,800,1275} m and z=75 m.
Receivers have the same 75 m depth and the existing canonical 20- or 40-receiver
integer-cell acquisition. Version1 rejects other geometries instead of pretending
this engine models arbitrary SEG-Y. Source-frequency calibration and matching
the stated Deepwave point-source amplitude convention are the user's declared
responsibility. Raw field pressure units or an unknown source signature are not
silently normalized or assigned synthetic truth. SEG-Y remains a separate bounded
intake/offline preparation question.

The primary [Deepwave scalar contract](https://ausargeo.com/deepwave/usage)
specifies differentiable velocity, physical grid/time steps, integer acquisition
cells, PML and gradient sampling. Its [FWI discussion](https://ausargeo.com/deepwave/example_fwi)
explains source/acquisition sensitivity, bounded parameterization, frequency
continuation and the limits of simplified examples. Neither page establishes
field validation of this product.

## Original input directory

Exactly `request.json`, `observed.f32`, `initial.f32`. No paths from JSON.
Closed request: schema=`geophysics.fwi-user-data/v1`, id, source, acquisition,
observed, initial, parameters. Source has citation, rights=owner-permitted|CC0|
CC-BY, scope=owner-provided|synthetic-control. Acquisition has frame=local-x-z-down,
spacing_m=12.5, dt_s=0.0005, sources_m=[[300,75],[800,75],[1275,75]],
receivers_m=[[x,75],...], wavelet=Ricker-peak-at-1.5-over-f,
amplitude_convention=Deepwave-scalar-point-source. Observed shape is
[3,20|40,512..3200], units=point-source-amplitude; initial shape=[96,128],
units=m/s. Each array declares dtype=float32-le, exact SHA-256 and byte count.
Parameters: frequency_hz=[4,12], beta=[0.0001,0.1], iterations_per_stage=[1,100].
IDs bounded64; citation2048; request<=16KiB. Integer bounds reject booleans.
All source bytes are read once, bounded regular files, no symlink or repository
ancestor. Byte count/hash/shape/scalar finiteness checked before scientific
imports. Initial velocities are strictly inside [1400,4400] m/s. Observations
must have nonzero energy in fitted and withheld sets.

## Calculation

Reuse `seismic.invert_observations`, never `solve_case` and never a generated
truth model. Explicit cpu|cuda operator option; unavailable cuda fails rather
than silently choosing CPU. Deterministic Torch flags restored after execution.
Receiver index modulo5 equals2 is held out. One shared 3Hz 1D background then
three equal spatial stages, terminal evaluated models retained. Full-band and
multiscale share observations, initial state, beta and call budgets. Record full
samples; no stride8 display-decimation is introduced into this user workflow.
Record finite-budget status and holdout improvement separately, without calling
either known geology or a global optimum. Source/environment hashes and measured
wall time, RSS and CUDA memory bind the generation. Original input is read-only.

## Result and export

External fresh directory contains `manifest.json` and named uncompressed
float32-le members: observed, initial, each method's model, prediction, signed
observed-minus-predicted residual, background and saved iteration frames. Model
arrays are [depth,distance], gather arrays [shot,receiver,time], frames
[iteration,depth,distance]. Complete member inventory with no unknown names;
every array carries dimensions, units, bytes, SHA-256. Manifest retains request,
raw hashes, actual receiver mask, history/solver/state identities, environment,
source hashes and truth=null. Reopening validates all bytes, shapes, values,
state linkage and residual identity before a completed marker is written. No
pickle, external executable, archive decompression or overwrite. Public import
uses selected local files only; it cannot submit an authenticated server job.
