# Frozen refined-source authored matrix

This is an additive exact realization of the prospective24 controls, not inverse
acceptance. No acquired field data, training, source authentication or geological
truth claim. `joint_survey_cases.py::make_joint_control(index)` is an explicitly
authored synthetic/oracle data constructor, NOT a production forward, fitter or
replacement of either supplied survey. Input is exact builtin int0..23.

Case order: family=index//6, regime=(index//2)%3, noise=index%2. Seeds1101+index.
No post-fit filtering/reseeding. Families: co_structural, disjoint,
flat_null, wrong_field. Regimes: dense, sparse_blocked, shifted_geometry.
Noise0=diagonal_sd,1=full_covariance. All24 records remain, including unresolved
or failed fits. This file freezes constants before generator/test implementation.

## Geometry and conditional source targets

Inverse mesh origin[-140,-180,-260]m, hx[40,70,90],hy[30,50],hz[60,110],
12 full/active cells, x-fast ordering. Refined source divides EACH width in two,
6x4x4=96 ordinary rectangular prisms; no inverse kernel produces observations.
Source centres/bounds come from explicit cumulative edges, not the production
geometry helpers. Coarse evaluation target is the volume average of its eight
refined constant properties, NOT recovered fine geometry or geological truth.

For a source centre x, blob(c,a)=exp(-0.5*sum(((x-c)/a)^2)). Fixed centres and
lengths (m): A=(-90,-150,-180),(30,22,35); B=(15,-125,-125),(24,18,24);
C=(-20,-160,-215),(20,15,20); D=(25,-165,-230),(18,13,18).

- co_structural:rho=600A-350B kg/m³; chi=0.012A+0.008B SI.
- disjoint:rho=600A-350B+400C; chi=0.015D. Do not claim equal source structure.
- flat_null:rho=0;chi=0.005 everywhere, nonzero induced magnetic response but
  constant model gradient. Coupling with a flat property is not resolution.
- wrong_field:rho and chi as co_structural, but source magnetization direction
  I=25deg,D=-35deg differs from DECLARED inverse I=60deg,D=12deg. The anomaly is
  projected onto the declared field direction, retaining genuine misspecification.

Declared field amplitude50000nT. ENU direction=(cosI sinD,cosI cosD,-sinI).
Induced M=chi*B0(T)/mu0 in A/m, actual Choclo magnetic_field produces T, projected
then multiplied1e9 ONCE. Gravity uses Choclo gravity_u*1e5 ONCE (upward mGal),
signed density; no fixed-G substitution. Both receivers are strictly above the
full source box. Native source/receiver/uncertainty/prior admission still applies.

Dense and shifted geometry:6 lines y[-210,-130,-50,30,110,190],8 points per line
x=linspace(-230,230,8);z=120+10*sin(point_index). Sparse blocked:3 lines
y[-150,-60,90],3 points per line x=linspace(-230,230,8)[0,3,7]; same height rule.
Magnetic measured receiver x has an additional5m offset. Each line is one GLOBAL
group; partition=line_index%3, including both modalities. Dense rows48 (16 per
partition), sparse9 (3 per partition). Shifted geometry uses dense measurements
but DECLARED receiver offset(+20,-15,+12)m; original measured receivers remain
external provenance, not used to repair submitted coordinates during a solve.
No mask is artificially inserted; every missing reason is empty.

Physical density bounds[-1500,1500],start/reference0,scale750 kg/m³;
chi bounds[0,0.1],start/reference0.005,scale0.03SI. Lengths[60,110,75]m,
coupling length100m. Explicit local ENU reference and conditional authored datum;
rights redistributable for these authored controls only, NOT provider datasets.

## Noise, custody and development/sealed split

Physical SD gravity0.005mGal,magnetic1nT. Diagonal draws seeded normal with the
fixed NumPy default_rng; covariance each modality separately is sigma² times
(0.65I+0.35ones), actual Cholesky correlated Gaussian draw. Correlation spans
partitions:full covariance declares possible_not_removed; diagonal declares
declared_absent. Marginal blocks, NOT conditional noise/leaked values, enter
training/validation/sealed scoring. Draw gravity then magnetic; seed/state/order
fixed before fitting. No same-engine-only observations or threshold retuning.

Original source identity binds explicit measured receivers, all observed values,
error covariance and original inducing vector through the normative C-byte native
descriptor digest. This is a synthetic source integrity declaration, NOT a
download/field/source-rights certificate. Byte serialization/export must later
bind actual serialized originals separately; a native digest is not file SHA.
Corrections receipt explicitly says authored/no field corrections. No raw field
file or fabricated provider acquisition is advertised.

Return exactly schema,case_id,family,regime,seed,survey_request,development,
sealed,truth,provenance,diagnostics. Development receives only exact training then
validation rows and marginal covariance/SD; sealed receives separate row IDs,
observations,noise_values and units. Truth/refined sources/original geometry stay
external to candidate/calibration input. Original source identities may be
referenced by development, but sealed observations do not enter development.
All returned arrays owned/C/read-only. Diagnostics synthetic=true,
inverse_completed=false,field_eligible=false. Full solver selection must accept
only survey_request/development, NEVER the whole oracle constructor result.

## Predeclared paired controls and applicability

`test_joint_survey_cases.py`: all24 exact identities/seeds/dimensions/types,
deterministic bytes, disjoint-source/constant/wrong-field/shifted-geometry
negatives; real Choclo source96 differs from inverse12; no producer forward calls
in construction; development/sealed masks/units/marginal covariance and digest
admission. Independent test-only Choclo COARSE kernels plus explicit pairwise R
and triangular whitening supply tiny BVLS/exact/tol1e-12/max_iter250 optima.
Record actual status/nit and independently projected KKT, per-modality residuals.
Compare weighted objective values/derivatives to actual native evaluation at the
frozen tolerances, not to an injected production kernel. These reference optima
are NOT production independently optimized baselines or a nonlinear fallback.
No24 inverse/selection/resource PASS follows until those actual gates run.

Verified primary units: [Choclo0.3.2 magnetic_field](https://www.fatiando.org/choclo/v0.3.2/api/generated/choclo.prism.magnetic_field.html)
accepts metric bounds and magnetization A/m, returns ENU tesla; singular source
interior/edge points yield NaN. [SimPEG0.25.2 CrossGradient](https://docs.simpeg.xyz/v0.25.2/content/api/generated/simpeg.regularization.CrossGradient.html)
penalizes structural variation, not data-source independence or petrophysics.
Published quadratic GPCG convergence is not transferred to quartic coupling.
