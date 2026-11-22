# Supplied acoustic shot gathers: actual local CPU/GPU inversion

This is M10's supplied-data calculation, not selecting an already baked model.
The CLI reads your original observations and an independently chosen initial
velocity, runs the actual differentiable scalar-acoustic inverse and writes a
complete verified generation for local browser inspection. Nothing is uploaded
or run on the ML VPS by this workflow. The scientific operator is the same
reviewed `data-pipeline/seismic.py`; its canonical synthetic artifacts remain
unchanged. [Input contract and limits](../design/features/fwi-user-data/design.md).

## Applicability before file preparation

Version1 supports the declared constant-density 2D acoustic experiment on a
128-distance by96-depth grid,12.5m spacing,0.0005s internal sampling, three
Ricker point sources at x=300,800,1275m and z=75m. Receivers are20 or40 at the
exact integer-cell coordinates in the input contract, also z=75m. Observations
have512..3200 original samples per trace. This is not an automatic SEG-Y import,
elastic inversion, arbitrary marine acquisition or an unknown-wavelet fit. A
different source signature, physics or geometry must be prepared and validated
with its own operator, not relabelled as this acquisition.

Amplitudes use the declared Deepwave scalar point-source convention; they are
not silently called calibrated pressure in pascals. All initial velocities are
strictly between1400 and4400m/s. Missing units/rights, incorrect geometry,
nonfinite values, zero-energy fitting/holdout groups and mismatched counts/hashes
are rejected before propagation. No true model enters the inverse.

## Prepare immutable local originals

Use the repository's ignored `.venv-pipeline` with the pinned installed NumPy,
PyTorch/Deepwave and psutil environment. The separate ERT environment is not an
acoustic environment. Run from the product checkout, with original and output
paths outside repositories. The existing data directory must already exist.
Input/output generations must not exist before creation. Source files are never
overwritten. Do not use untrusted pickle/serialized Torch tensors as input.

The observation binary is little-endian float32 in C order `[shot,receiver,time]`.
The initial binary is little-endian float32 in C order `[depth,distance]`.
For an already prepared numeric array, `array.astype('<f4').tobytes(order='C')`
produces these bytes; the convention does not perform calibration or conversion
of an unknown field dataset. Source rights and acquisition declarations remain
your explicit responsibility.

```powershell
$py = '.venv-pipeline/Scripts/python.exe'
& $py -B scripts/prepare_fwi_input.py `
  --observed E:/_Datos/my-acoustic/observed.f32 `
  --initial E:/_Datos/my-acoustic/initial.f32 `
  --output E:/_Datos/my-acoustic/input-01 `
  --id my-acoustic-01 --citation 'My calibrated source/acquisition record' `
  --rights owner-permitted --scope owner-provided `
  --receivers 20 --samples 3200 --frequency-hz 8 `
  --beta 0.001 --iterations-per-stage 28
& $py -B scripts/process_fwi.py `
  --input E:/_Datos/my-acoustic/input-01 `
  --output E:/_Datos/my-acoustic/result-01 --device cuda
```

On Linux the same arguments use `./.venv-pipeline/bin/python` and absolute
external Linux paths. Use `--device cpu` explicitly for CPU execution. Requesting
CUDA without a usable CUDA device fails; there is no silent CPU substitution,
engine install, download or retraining. A failure returns nonzero; an interrupted
partial output is retained, not accepted or overwritten by a later run.

## What the two methods optimize

Both methods fit identical observations using only receiver indices whose index
modulo5 is not2. The remaining receivers are withheld. Both start from the same
submitted velocity and shared data-only3Hz one-dimensional background. They
then use the same9x12,17x24 and33x48 control grids, bounds, roughness coefficient
and number of optimizer calls. Full-band uses unfiltered data after the shared
background; continuation uses5,8 and14Hz filtering at successive spatial stages.
The order6 zero-phase FFT amplitude filter is zero-padded to at least twice the
record length. It is not a causal IIR or a squared filtfilt response.

The objective is relative mean-square waveform error plus beta times squared
physical velocity roughness. A sigmoid maps interpolated control parameters to
1400..4400m/s. Each L-BFGS call has strong-Wolfe search and at most25 closure
evaluations. With28 calls per stage, each method reports112 calls, while the
shared background is calculated once. Every terminal update is actually
evaluated. The stop is a finite iteration budget, not KKT convergence or a
global optimum. Holdout values are diagnostics, never a stopping/selection input.

## Export, reopen and inspect

The result directory contains13 files: a bounded manifest and12 uncompressed
float32 members. All original time samples are retained. Models/frames use
`[depth,distance]`; gathers use `[shot,receiver,time]`. Each member declares
shape, exact bytes, units and SHA-256. The manifest preserves the exact bounded
original request UTF8, its original digest, input-array identities, source code
hashes, actual environment, recorded states, solver settings and resources.
An independent reopen verifies each member, terminal model/frame equality and
the exact float32 observed-minus-predicted residual before completion is marked.

In App choose **Open local acoustic FWI result**, select all13 files from that
one generation, then open it. No account is required. File parsing checks every
member and the request/source/axis/state bindings. A rejected import preserves
the previous admitted view. The browser does not independently replay acoustic
physics, and a manifest is not a digital signature.

Select either schedule, actual source/receiver/time sample and a native velocity
cell. Views include native velocity states at equal metre scales, full observed/
predicted/signed-residual gathers on a shared zero-centred scale, linked complete
traces with zoom/keyboard inspection, and the evaluated objective/holdout history.
Playback advances only recorded velocity states, with pause and scrub controls;
waveform predictions remain explicitly tied to the evaluated terminal model.
Inspection export records exact linked numeric values and manifest identity,
not an invented recomputation or replacement original.

## Validation and limits

The serialized original-input CUDA gate is distinct from array-storage tests.
The initial full-budget heterogeneous control passed fresh terminal forward
replay for both112-call methods at rtol/atol2e-5/2e-5, and signed residual replay
at2e-4/2e-5. It used the RTX4070 Laptop GPU,2.073GB peak CUDA allocation and
20ms-sampled peak RSS1.435GB,144.68s measured inverse wall time. These are one
local controlled experiment, not VPS admission, percentiles or a guarantee for
every input. The control improved waveform error much more than whole-model
velocity error. That distinction is part of the result, not hidden by visuals.
Final source-pin, adversarial and rendered receipts are recorded in the feature
[validation record](../design/features/fwi-user-data/validation.md); this early
receipt is not final release acceptance. The final full-budget run measured
177.02s inverse wall,1.414GB sampled RSS and the same2.073GB CUDA peak.

The original analytic propagation, refinement, adjoint, leakage and cycle-skip
controls remain unchanged. Known synthetic truth is inspected only externally
after both fits and exports are fixed. User/field outputs always retain truth=null
and no model-recovery score. Neither small waveform error nor attractive layers
establishes unique geology, calibrated uncertainty or field suitability.

Primary method references: [Deepwave scalar/gradient API](https://ausargeo.com/deepwave/usage),
[Deepwave FWI discussion](https://ausargeo.com/deepwave/example_fwi), and
[official implementation](https://github.com/ar4/deepwave). The web pages describe
their current0.0.26 documentation; actual local execution records0.0.27 rather
than silently pretending the versions coincide.
