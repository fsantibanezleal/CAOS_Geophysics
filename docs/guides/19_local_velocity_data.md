# Local first-arrival survey processing

The executable `scripts/process_velocity.py` accepts supplied source-receiver
segments, arrival times and uncertainties. It computes a velocity estimate,
coverage and signed residuals, and writes a verified local generation. Files
remain on the workstation: this command neither uploads them nor trains a model.
It is separate from the field bent-ray M09 solver and acoustic FWI.

## Physical input

The800 by800 m section has16 by16 cells of50 m, horizontal x and positive-down
depth z. Coordinates must already be in this explicit local frame. The tool
never guesses a CRS, converts a geodetic longitude to metres or extrapolates a
ray outside the domain. Supply8..2048 rays with unique IDs; every original row
and its declared standard deviation remains in the output.

The closed JSON schema is `geophysics.velocity-user-data/v1`. Keys are `id`,
`source`, `frame`, `units`, `ray_ids`, `rays_m`, `times_s`, `sigma_s`, `lambda`,
plus `schema`. Source declares nonempty citation, rights (`owner-permitted`,
`CC0` or `CC-BY`) and scope (`owner-provided` or `synthetic-control`). Frame is
`local-x-z-down`; units are `distance: m`, `time: s`, `velocity: m/s`.
Each ray is `[source_x, source_z, receiver_x, receiver_z]` in metres. Arrival
times and positive standard deviations are seconds, not samples or milliseconds.
An absolute origin time must be removed by a documented upstream operation.
No hypocentre, source delay or response correction is inferred here.

## Actual estimate and parameter semantics

For fixed straight paths, ray-cell length matrix A has units of metres and
slowness s has units of seconds per metre. Predicted time is As. With reference
v0(z)=2000+0.35z m/s, q=1000(s-s0), supplied uncertainties sigma and neighbour
difference matrix D, the tool minimizes

\[
\left\|\operatorname{diag}(\sigma^{-1})
\left(\frac{Aq}{1000}-(t-As_0)\right)\right\|_2^2
+\lambda\|Dq\|_2^2+0.01\|q\|_2^2.
\]

Cholesky solves this positive-definite normal equation. `lambda` is an explicit
dimensionless smoothness weight, not a noise estimate or an automatically tuned
regularization. Increasing it changes the solution toward spatial smoothness;
changing a ray's sigma changes its actual likelihood weight. The estimate is
then explicitly clipped in slowness to1400..4000 m/s. The clipped-cell count and
post-clipping objective are recorded; this is not a certified box-constrained
optimum. Residual is observed minus predicted, in seconds. WRMS divides by the
supplied uncertainties; it is not a known-truth error.

Coverage is accumulated path length per cell in metres. Zero coverage means no
ray traverses that cell, not zero velocity or a probability of absence. A second
bilinear-slowness quadrature reforward exposes discretization sensitivity. It
is not independent field observation or proof of the true ray trajectory.
Strong heterogeneity requires bent rays or a wave equation; this linearized
tool does not silently label them as equivalent.

## Run and independently reopen

Use the repository's ignored environment with NumPy/SciPy; Torch is required
only for optional real checkpoint inference. Paths passed to the command must
be absolute. The output directory must not already exist.

```powershell
.\.venv-pipeline\Scripts\python.exe scripts/process_velocity.py `
  --input D:\Surveys\first-arrivals.json --output D:\Results\arrival-run-01
```

For the retained experimental CNN, additionally supply `--checkpoint` with the
absolute path to `models/experimental/m12-velocity-cpu-20260928/m12-velocity.npz`
and `--checkpoint-sha256 a06a29fc9b64e1797d9b96db10053097816256fa32b578ceb19c301b19b5a99d`.
This is actual inference on the same supplied times/geometry, never substitution
of the classical model. Its matched held-out benchmark failed. The output
retains that warning, the600 m/s perturbation bound and any mismatch from its
training geometry or1 ms noise. Do not interpret `computed` as learned advantage.

The generation has `result.json` and `manifest.json`; the manifest is published
only after an independent reopen checks physical shapes, axes, ray reforward,
residuals, WRMS, objective and exact bytes/hashes. `verify_generation` in
`data-pipeline/velocity_user_data.py` repeats these checks. Rehashed incorrect
physical arrays still fail. The input is never overwritten and failed partial
generations never acquire a successful manifest.

## Reproducible controls and interpretation

`tests/data/test_velocity_user_data.py` contains the complete128-ray background
control, variable-error nonuniform residual case,2,048-ray upper input, actual
checkpoint inference, supplied-parameter changes, malformed contracts and
corrupt/interrupted generations. Run it locally, never in deployment:

```powershell
.\.venv-pipeline\Scripts\python.exe -m pytest -p no:cacheprovider tests/data/test_velocity_user_data.py
```

Exercise: increase one ray's sigma tenfold and lambda from1 to100. Compare the
computed velocity and standardized residual, not just colour scales. Identify
which cells have low coverage and why smoothness can fill them without creating
new observations. Repeat with a delayed pick; do not call a small fit residual
an independent geological validation.

## Resumen en español

La herramienta procesa tiempos de llegada y geometría aportados por el usuario,
con unidades y errores explícitos. Calcula inversión lineal de lentitud,
cobertura, predicción y residuales; no carga los archivos a un servidor ni
inventa verdad geológica. La aproximación usa rayos rectos, no refracción ni FWI.
El CNN opcional ejecuta sus pesos reales, pero conserva el resultado negativo
del ensayo y advierte adquisiciones fuera del dominio de entrenamiento.

References: [ray-cell intersection, Siddon](https://doi.org/10.1118/1.595715),
[original learned benchmark and limits](../problem-types/04_learned-velocity-validation.md),
[closed user-data design](../design/features/velocity-user-data/design.md).
