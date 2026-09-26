# MT recovery, strict EDI ingestion and conditional uncertainty

Implemented for R-S04, R-S05 and the MT part of R-S07 on 2026-09-24. Files are
plain scripts, not an internal Python package. All inversion tensors use CPU
float64, including the per-sounding neural model. No canonical v2 arrays are
changed by this work unit.

## Physical target and forward problem

The target is electrical resistivity in Ω m for isotropic, horizontally infinite
layers. Finite-layer thicknesses in metres are **fixed inputs**, not estimated.
The bottom layer is an infinite half-space. The experiment assumes a quasi-static
plane-wave source, permeability μ₀ = 4π×10⁻⁷ H/m, and exp(+iωt).

With xⱼ = ln ρⱼ, kⱼ = √(iωμ₀/ρⱼ), wⱼ = √(iωμ₀ρⱼ), and tⱼ = tanh(kⱼhⱼ),

    Z_bottom = sqrt(i omega mu0 rho_bottom)
    Z_j = w_j (Z_(j+1) + w_j t_j) / (w_j + Z_(j+1) t_j)

Z is E/H in Ω, not E/B in native MT units. Apparent resistivity is
|Z|²/(μ₀ω) and phase is atan2(Im Z, Re Z). The complete 1D tensor is
[[0, Z], [-Z, 0]]. An off-diagonal component is not a subsurface property.

Known-model independent tests use the explicit half-space formula
(1+i)√(πfμ₀ρ) and a two-layer reflection-coefficient expression, not a second
call to the implementation's tanh recursion. These tests do not validate 2D/3D
geology, static shift, unknown thickness, permeability variation or anisotropy.

## One objective and one physical domain

For active frequency set A of size N and L layers:

    J(x) = sum_(i in A) [(Re ΔZ_i / σ_i)^2 + (Im ΔZ_i / σ_i)^2] / (2N)
           + β sum_(j=1 to L-1) (x_(j+1)-x_j)^2 / (L-1)

The prior is zero for a one-layer half-space. σ is the standard deviation of each
real/imaginary part, not complex RMS error. All three algorithms receive the same
observations, mask, σ, β, layer thickness, initial model and physical bounds
**1–6000 Ω m**. No algorithm receives synthetic truth.

The normal synthetic β is 0.001; the regularization experiment uses 0.3. This is
a declared fixed tradeoff, not a claimed optimal L-curve/discrepancy selection.
The adjacent-layer penalty uses index differences; it is not a depth derivative.

- **mt-lm (legacy array key): bounded SciPy TRF.** The residual vector contains
  real and imaginary errors divided by √(2N), and adjacent differences multiplied
  by √(β/(L−1)). Its squared norm is J. SciPy's reported cost is J/2. Budget:
  400 function evaluations; ftol, xtol and gtol = 10⁻¹⁰. It is not LM.
- **mt-adam: projected Adam.** Direct log-resistivity parameters, clipped to the
  same log bounds after every update. 1,200 updates; initial learning rate 0.06.
- **mt-neural: per-sounding neural parameterization.** A CPU double
  1→24→24→1 tanh network perturbs the logit of the common initial model. A sigmoid
  maps to the same physical bounds. The final layer starts at zero, so all
  algorithms start at exactly the same resistivity. 1,800 Adam updates; initial
  learning rate 0.015. This network is not a pretrained geological prior.

Both Adam schedules halve the rate after 50% and quarter it after 75% of the
fixed budget. The selected Adam state minimizes **complete J**, not model error.
Finite budget is explicitly distinguished from optimizer convergence.

The [SciPy least-squares definition](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html)
supports the cost and bound interpretation. The installed SciPy is 1.15.2, which
does not provide the newer TRF callback API; recorded TRF residual evaluations
can include rejected trials and are labelled accordingly.

## Saved state identity

Each frame has its own copied physical resistivity vector and a freshly
evaluated complete objective, data term and regularization term. Evaluation
occurs after Adam's update; no mutable Parameter alias is reused with an earlier
loss. The selected model is explicitly appended as the **last frame**, including
when an earlier iterate was selected. Predictions and residuals are recomputed
from that identical model.

The states array labels initial, post-update, TRF residual evaluation and
selected-final records. The state_identity.final_frame_index points to the last
frame. The selected_iteration is an Adam step or a TRF residual-call index
(as specified by its state kind), not a fabricated accepted-iteration count.
The history array is J at the corresponding frames entry.

Tests check every frame's objective, not only the last loss. Direct export
retains full JSON floating-point precision. The integration owner must retain
that precision for exact re-evaluation; a shared seven-significant-digit export
requires explicitly documented numerical tolerance instead. The optional
state.model_sha256 describes the pre-rounding little-endian float64 vector.

## Recovery and identifiability are separate questions

Reported data metrics distinguish:

- active_component_wrms: square root of the mean of 2N real-component squared
  standardized residuals; expected near 1 under the supplied independent error law.
- withheld_component_wrms: same quantity at frequencies excluded from fitting,
  or null when none are excluded.
- Legacy wrms: complex magnitude convention over **all** frequencies, expected
  near √2 at the known truth. It is retained for v2 compatibility.
- Initial component WRMS, complete objective and both objective components.
- For synthetic cases only: natural-log model RMSE, initial log-model RMSE,
  and their ratio. These are evaluation quantities, never solver inputs.

Identifiability uses a finite-difference, noise-whitened **data-only** Jacobian at
the selected model. It exports singular values, effective rank, condition number,
linearized log-resistivity deviations, bound contacts and unresolved layers.
A direction is weak below max(1, 0.001×largest singular value); a layer is flagged
if its weak-subspace participation exceeds 0.1, local log standard deviation
exceeds ln 2, or it lies within 0.01 log units of a bound. These are declared
diagnostic thresholds, not a posterior interval or global uniqueness proof.

The evaluation status is recovered, unresolved or failed, with reason_codes.
The generic inverse, which has no geological truth, stays unresolved unless
it fails. For synthetic evaluation, recovery requires improvement over the
independent 100 Ω m starting model, active component WRMS ≤1.5, finite solver
execution and no local identifiability flag. Poor data fit or no improvement is
failed. A good fit with unresolved parameters stays unresolved. A recovered
label does not assert an exact model, unique solution or field performance.

## Strict EDI ingestion

Dependency: **mt-metadata==1.0.10**. The official EDI class is used, with a raw
preflight that checks data before that reader can replace invalid/missing tokens
with zeros. Official arrays must agree with the validated raw tensor and errors.
See the [official transfer-function interface](https://mtgeophysics.github.io/tf-example/)
and [reader source](https://github.com/MTgeophysics/mt_metadata/blob/main/mt_metadata/transfer_functions/io/edi/edi.py).

Supported subset:

- One ASCII/UTF-8 station; HEAD, INFO, DEFINEMEAS, four EX/EY/HX/HY measurements,
  MTSECT, FREQ, all real/imag/variance blocks for xx/xy/yx/yy, and END.
- 2–512 unique positive frequencies in Hz. Every block has its declared count.
  Frequencies are sorted together with all tensor/error/angle arrays.
- Finite values, positive variances, unique matching channel IDs, an orthogonal
  co-oriented electric/magnetic layout and a common declared tensor frame.
- Explicit native (mV/km)/nT or SI Ω impedance units. Missing conventions may be
  supplied as CLI arguments with provenance; conflicting declarations are rejected.
- Explicit time-sign and variance conventions. Negative time sign is conjugated
  to positive. Complex variance becomes per-real-component σ = √(VAR/2);
  an explicitly declared per-real-component variance uses √VAR.
- Input σ assumes equal real/imaginary variances and zero real–imag covariance.
  No covariance between tensor components is invented.

Native MT conversion is derived dimensionally:

    (1 mV/km)/(1 nT) = 1000 (V/m)/T
    Z_E/H = mu0 * 1000 * Z_native
    VAR_E/H = (mu0 * 1000)^2 * VAR_native

The reciprocal is approximately 795.77471546. This agrees with the
[MTpy unit definitions](https://mtpy-v2.readthedocs.io/en/latest/mtpy.core.html).
It is not a conversion from resistivity Ω m.

The [USGS EMTF-FCU source notes](https://github.com/magnetotellurics/EMTF-FCU)
document the factor-of-two distinction between complex and real-component
variance and the missing-covariance problem for EDI rotations. Therefore an
arbitrary angle is **preserved**, not silently rotated with guessed errors.
An isotropic 1D tensor is invariant under common horizontal rotation, so direct
fitting in the supplied frame is valid. Geographic conversion is supported only
for exact multiples of 90°, which are signed permutations and do not mix errors.
Other requested re-rotations fail closed.

Before inversion, diagonal component WRMS and conservative antisymmetry WRMS
must each be ≤3. The latter uses σ_xy+σ_yx, an upper bound on the standard
deviation of a sum without assuming cross-component independence. This is a
necessary 1D compatibility screen, **not** proof of one dimensionality.

One selected component, xy or sign-corrected yx, is fitted. The other off-diagonal
is evaluated separately as other_component_wrms; the components are not
averaged with invented covariance. Diagonal-component inversion is rejected.

Unsupported input is rejected: spectra, tipper/additional channels, incomplete
tensors, missing errors, zero/negative errors, duplicate frequencies or blocks,
sentinels, malformed tokens, unexplained units/signs, nonorthogonal layouts,
mixed component frames and arbitrary covariance-free re-rotation. This strict
subset is **not a general EDI field-processing package**.

## Original fixtures and provenance

[data/fixtures/edi/manifest.json](../../data/fixtures/edi/manifest.json) lists three
original CC0-1.0 fixtures, SHA-256 and byte counts, generating formula, noise seeds,
units, rotation, known synthetic model and reproduction commands. Actual EDI files:

| Fixture | Independent target | Purpose |
|---|---|---|
| halfspace-100-native.edi | 100 Ω m | E/B → E/H and complex-variance conversion |
| halfspace-500-ohm-negative.edi | 500 Ω m | SI input, negative sign, exact 90° orientation |
| two-layer-noisy-rotated.edi | 120 / 12 Ω m; 350 m cover | Noisy inversion, 27° frame preservation |

Coordinates are explicitly unspecified synthetic placeholders, not claimed
field acquisition locations. The generator imports no inversion forward operator.
Fixture truth is used only by tests/evaluation; invert_edi never reads the fixture
manifest and returns truth=null, clean=null for supplied data.

Ingestion preserves original metadata, source hash, source size, parser version,
declared/supplied interpretation, frequency permutation and rotations. Source
tensor components and their real-part SDs remain available alongside 1D output.

## Conditional parametric bootstrap

Implemented for the bounded TRF estimator only. Hold selected model, thickness,
σ, frequencies/mask, initial model, bounds and β fixed. Generate independent
Gaussian real and imaginary errors with the supplied σ around its forward
response. Re-invert every resample with the same objective. No test truth or
resample-specific uncertainty is used. All child seeds and failures are retained.

The exported interval is pointwise percentile, ordinarily 128 members and
2.5%/97.5% quantiles. It is a **conditional repeatability interval**, not a
geological posterior or simultaneous model band. Bias, incorrect structure,
unknown thickness, correlated errors and model discrepancy are excluded.
Failed solves are counted; an ensemble with failures is marked incomplete.
No coverage value is inferred from a nominal quantile span.

Independent calibration experiments use separate SeedSequence branches for
each observation and its bootstrap, and different synthetic models from the
EDI fixtures: a 230 Ω m half-space and a 180/20 Ω m two-layer model with 450 m
thickness, 24 frequencies, 4% per-real-component noise. Coverage, bias, width,
Monte Carlo standard error and Wilson 95% coverage intervals are exported.
Failed calibration intervals count as noncoverage; no interval calibration
parameter is fitted to these outcomes.

The [SciPy bootstrap documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html)
describes percentile bounds and their limitations. Our sampling is parametric
complex-Gaussian inversion resampling, **not** a call to SciPy's nonparametric
resampling function and not claimed BCa inference.

## Commands and frontend contract

Run from the repository root:

    .venv-pipeline/Scripts/python -m pip install mt-metadata==1.0.10
    .venv-pipeline/Scripts/python data/fixtures/edi/generate_fixtures.py
    .venv-pipeline/Scripts/python data-pipeline/edi.py data/fixtures/edi/two-layer-noisy-rotated.edi --thickness 350 --bootstrap-samples 128 --output data/experiments/edi/two-layer-noisy-rotated.json
    .venv-pipeline/Scripts/python data-pipeline/edi.py --fixture-bundle --bootstrap-samples 128 --calibration-realizations 48 --output data/experiments/edi
    .venv-pipeline/Scripts/python -m pytest tests/test_mt_recovery.py tests/test_edi.py

The bundle manifest uses schema inverse-earth/edi-bundle/v1.
Its fixtures array contains id, label, synthetic=true, target, truth_ohm_m,
thickness, relative source/artifact filenames, SHA-256, noise details, selected
component and metrics. The calibration array references separate empirical
calibration records. Copy the **entire bundle** together when publishing; relative
paths then work under either host base. The integration owner chooses the public
data/edi/ destination. This work unit only writes review artifacts under
data/experiments/edi/, never data/derived/v2.

EDI artifacts use inverse-earth/edi-1d/v1; they are not silently cast to canonical
v2 runs with non-null truth. They carry the same MT frequencies, thickness,
observed curves, σ, methods, frames, predictions and residuals. Known fixture
truth belongs to the labelled manifest/evaluation context, not generic ingestion.

Each method adds:

    target: {quantity, units, dimensionality, provenance}
    evaluation: {status, reason_codes, ...}
    state_identity: {
      final_frame_index, selected_iteration,
      frame_quantity: "layer resistivity in ohm m",
      predictions: "final-model"
    }
    uncertainty (TRF only): {
      kind: "conditional-parametric-bootstrap",
      conditioning, members, seed, quantiles,
      lower: number[L], upper: number[L], mean: number[L], std: number[L],
      ... complete sampling settings, samples, child seeds, failures ...
    }

Absent uncertainty on Adam/neural is deliberate: a TRF ensemble must not be
mislabelled as uncertainty for a different estimator. Calibration coverage is in
its own evidence record, never copied to arbitrary sounding intervals.

The existing solve_case(case, variant) signature remains unchanged. The common
bake coordinator currently replaces root provenance and rounds exported arrays;
integration should preserve the added scientific provenance and account for
rounding in any exact-value gate. Catalogue method summaries must copy evaluation
as well as names/metrics so the frontend does not lose the verdict.

## Dependency receipt

Installed only into .venv-pipeline; no shared requirement files were edited.
Requested direct pin: mt-metadata==1.0.10. Newly resolved dependencies:

    annotated-types==0.8.0
    certifi==2026.7.22
    dnspython==2.8.0
    email-validator==2.3.0
    idna==3.20
    loguru==0.7.3
    pydantic==2.13.5
    pydantic-core==2.46.5
    pyproj==3.8.0
    typing-inspection==0.4.4
    win32-setctime==1.2.0
    xarray==2026.7.0

Existing NumPy 2.2.6, SciPy 1.15.2 and Torch 2.14.0+cu126 were not upgraded.
Torch's CUDA build is installed but **this vertical uses CPU only**.
Pip check reported no broken requirements. The integration owner must add the
direct pin (and lock transitive dependencies according to repository policy).
