# M05/M06: source-valid EDI and conditional layered recovery

The bilingual course is reached from App by selecting Methodology or Implementation, Fields, Magnetotellurics, then M05 or M06. It preserves the published synthetic TRF/Adam/per-sounding-neural material under Replay comparators. The current Introduction distinguishes immutable observations, derived processing and inverse models. This chapter concerns the reviewed [PR100 scientific baseline](https://github.com/fsantibanezleal/CAOS_Geophysics/tree/7b6940487c5ed67833fa2624f91ef8e68c147e5d), not public API activation, a completed M01-M13 matrix or an eligible Clear Lake inverse. [Course SDD](../design/features/online-mt-course/requirements.md).

## 1. What is measured and what is assumed

EDI stores estimated complex transfer functions, not raw E/H time series. The tensor maps horizontal H (A/m) to E (V/m), with frequency/electric/magnetic axis order. Its E/H impedance has units ohm, distinct from resistivity in ohm m. For exp(+i omega t), negative-time source values must be conjugated. Native (mV/km)/nT converts by c=1000 mu0, because B=mu0 H and native E/B is1000(V/m)/T. Variance scales by c squared. No unit, orientation, sign or covariance is guessed.

For equal real/imaginary marginal variances, complex VAR gives sigma=c sqrt(VAR/2); explicitly per-real-component VAR gives c sqrt(VAR). Sigma is SD of each impedance part, not complex RMS or apparent-resistivity error. Changing that interpretation changes residual weighting and prior balance. Equal real/imaginary variance and zero covariance between those parts are stated assumptions. Cross-component covariance remains unknown. [EMTF-FCU conventions](https://github.com/magnetotellurics/EMTF-FCU), [actual parser](../../data-pipeline/edi.py).

The strict raw-block preflight checks complete xx/xy/yx/yy real/imaginary/variance blocks, declared counts, finite values, positive variances, positive unique frequencies, channel polarity/geometry and common frames before calling mt-metadata1.0.10's official EDI reader. Official full arrays must agree with validated raw arrays. Source bytes/hash, supplied assumptions, original frequency permutation and frame action remain in provenance. Optional complete tipper with common missing masks is ancillary and unused by M06; its native variance is not silently assigned an uncertainty convention. [Official reader](https://github.com/MTgeophysics/mt_metadata/blob/main/mt_metadata/transfer_functions/io/edi/edi.py).

## 2. Common frame, full tensor and eligibility

For a common proper horizontal rotation R, Z'=RZR^T. The assumed isotropic tensor [[0,z],[-z,0]] is invariant. That permits preservation in the supplied co-oriented frame, not an inferred north reference or independent electric/magnetic rerotation. A general covariance transformation is Sigma'=(R tensor R)Sigma(R tensor R)^T. Marginal EDI variances cannot reconstruct Sigma. Only exact90-degree signed permutations to a documented north frame are supported; arbitrary rerotation rejects. The xy comparison curve uses Zxy, the yx curve -Zyx, while the full tensor retains original signs. One off-diagonal is fitted; no covariance-free averaging.

With N original frequencies, each diagonal score is

```text
Q_aa = sqrt(sum_n |Z_aa,n / sigma_aa,n|^2 / (2N))
Q_anti = sqrt(sum_n |(Z_xy,n + Z_yx,n) / (sigma_xy,n + sigma_yx,n)|^2 / (2N))
```

All three must be<=3 across the entire original tensor. The antisymmetry denominator is the conservative SD-sum bound, not quadrature assuming independence. A later training mask cannot rescue failed QC. Necessary compatibility does not prove 1D geology, absence of static shift or field error calibration. A favorable phase-tensor label is not this full-complex-tensor admission. [EMTF-FCU](https://github.com/magnetotellurics/EMTF-FCU), [Caldwell et al.2004](https://doi.org/10.1111/j.1365-246X.2004.02281.x), [implemented screen](../../data-pipeline/edi.py).

## 3. Literal forward model and independent oracle

Assume quasi-static plane-wave induction, horizontal infinite isotropic layers, mu0=4pi×1e-7 H/m, conductivity1/rho and negligible displacement current. With exp(+i omega t): curl E=-i omega mu0 H and curl H=E/rho. The positive decaying branch gives

```text
omega = 2 pi f
k_j = sqrt(i omega mu0/rho_j) = (1+i)/delta_j, inverse metres
w_j = sqrt(i omega mu0 rho_j), ohm
delta_j = sqrt(2rho_j/(mu0 omega)), metres
Z_(L-1) = w_(L-1)                       infinite basement
t_j = tanh(k_j h_j)                    h fixed, not optimized
Z_j = w_j (Z_(j+1) + w_j t_j)/(w_j + Z_(j+1) t_j), j=L-2..0
rho_a = |Z_0|^2/(mu0 omega), ohm m
phase = atan2(Im Z_0, Re Z_0), exported degrees
```

An independent halfspace oracle is (1+i)sqrt(pi f mu0 rho), with constant apparent resistivity and45-degree phase. Independent two-layer reflection algebra uses q=((w1-w0)/(w1+w0))exp(-2k0h0), Z0=w0(1+q)/(1-q), not a second tanh call. Tests cover both contrasts, exact halfspaces and boundary rho/h values. Skin depth is attenuation in a homogeneous layer, not a resolution certificate or a unique period-to-depth map. The hand-authored bilingual physics SVG depicts an imposed x-z section: +x/Ex right, +y/Hy out of the page toward the viewer (dot-circle), +z/depth down. The fields are horizontal and orthogonal; glyph sizes/arrows encode no amplitudes. The imposed cover/infinite basement is not recovered field geometry. [Heagy et al.2017](https://doi.org/10.1016/j.cageo.2017.06.018), [actual forward](../../data-pipeline/electromagnetics.py), [independent course oracles](../../tests/test_online_mt_course.py).

## 4. Objective, finite differences and training-only protocol

Optimize x=ln(rho), not log apparent-resistivity data. For active A with N_A samples and L layers,

```text
deltaZ = F(exp(x); g,h) - d
J_data = sum_A[(Re(deltaZ)/sigma)^2 + (Im(deltaZ)/sigma)^2]/(2N_A)
J_prior = beta sum_j (x_(j+1)-x_j)^2/(L-1); zero if L=1
r = concatenate(Re(deltaZ_A)/(sigma_A sqrt(2N_A)),
                Im(deltaZ_A)/(sigma_A sqrt(2N_A)),
                sqrt(beta/(L-1)) diff(x))
J = r dot r = 2 SciPy cost
```

The first-difference prior is adjacent layer-index contrast, not a physical depth derivative. `objective_residual` feeds bounded SciPy TRF through `invert_mt`. Bounds are1..6000ohm m; main max_nfev400; ftol/xtol/gtol1e-10; default linear loss and 2-point finite-difference Jacobian. The automatic step adjusts for bounds; no analytic optimizer Jacobian is implemented. Residual calls include differentiation/rejected trials and are not accepted iterations. A copied selected-final physical model is appended with reevaluated predictions, residual and objective. [Pinned SciPy1.15.2](https://docs.scipy.org/doc/scipy-1.15.2/reference/generated/scipy.optimize.least_squares.html), [implemented objective](../../data-pipeline/electromagnetics.py).

The reviewed online wrapper withholds sorted zero-based indices4,9,14,19,... before any fit. User start, uniform30 and uniform1000 compete only among successful trials by minimum complete training objective. Holdout cannot choose starts, beta or h. Controls reuse the winning main start: h×0.8/1.2; beta'=0.01 if zero, otherwise beta×10 when<=0.1 or beta/10 when larger. The same-input halfspace baseline starts100. These controls are sensitivities, not posterior samples. Source geometry g includes layer count, common frame, plane-wave assumption and frequencies; d, g, beta and h remain explicit conditioning. [Actual online selection](https://github.com/fsantibanezleal/CAOS_Geophysics/blob/7b69404/app/mt_compute.py).

## 5. Identifiability and conditional bootstrap

`identifiability` uses a different Jacobian: central data-only differences at epsilon1e-5 in log rho, stacked real/imaginary and whitened by sigma, without prior or sqrt(2N_A). SVD effective threshold is max(1,0.001s0). Flags include weak-direction participation>0.1, local log SD>ln2, log-bound distance<0.01 and rank deficiency. The numerical pseudoinverse threshold max(s0×1e-10,1e-12) is distinct from the effective threshold; a small pseudoinverse SD does not erase a null-space flag. This is local linear data sensitivity conditional on h, not global uniqueness or posterior geology.

`bootstrap_mt` generates d*=F(rho_selected)+sigma(xi+i eta) with independent standard Gaussian parts and recorded SeedSequence children, then actually refits every draw. Thickness, sigma, acquisition/frame, mask, initial model, beta and bounds stay fixed. `invert_edi` passes seed+1; `_trf_only` uses max_nfev300 and1e-10 tolerances. Online20..40 members produce pointwise2.5/97.5percentiles only when at least20 fits complete; failures are retained and mark incomplete. Unknown h/structure, correlated noise, static shift and model discrepancy are excluded. Nominal percentiles do not establish field coverage; independent calibration is a separate study. [Source implementation](../../data-pipeline/electromagnetics.py), [prior calibration](mt-recovery-validation.md).

## 6. Worked source and the retained wrong-h result

The [course record](../../frontend/src/data/online-mt-worked.json) pins8987original bytes/SHA`0d6b0fab71efe69d183445070aba1181604333f00fb6781bf6d2c9d9d2ee5e95`, actual executed source and scientific-function hashes, NumPy2.2.6/SciPy1.15.2/mt-metadata1.0.10, observations, sigma and mask. It actually solves the original synthetic noisy27-degree fixture with target120/12ohm m and h350m, noise seed67201. Target is evaluation metadata only; no truth reaches the inverse. Twenty frequencies train and four are withheld. All displayed models/predictions/objectives are independently replayed.

Fixed350m gives about123.95/11.87ohm m, training WRMS0.891 and holdout1.750. Wrong280m gives about198.32/12.67, training1.354 and holdout1.567. The wrong-h holdout is smaller: retain this negative result, do not claim280m true or tune h on four noisy held-out samples. Wrong420m and beta0.01 plus a halfspace control remain inspectable. Exact numbers are in the record, not duplicated as a public benchmark. Controls change recorded actual-solve results and curve readouts; they do not submit a user job or optimize in-browser. [Numerical reproduction](../../tests/test_online_mt_course.py), [exercise UI](../../frontend/src/components/OnlineMTExercise.tsx).

## 7. Measured source that must not be inverted

Original cl061 has16411bytes/SHA`90c5c96cd69d6d29c866a768097cb3b38bc20e8b9c143e24bf10b2d253261e83`,42frequencies, positive time sign, supplied native-unit/complex-variance assumptions and preserved frame. Scores320.233260669,109.507875314,267.600037116 all exceed3. `test_cl061_source_exclusion` actually reads the ignored original, checks count/hash, reruns screen and verifies inversion rejection. If absent, it explicitly skips rather than manufactures field evidence. The actual course run must record whether that original gate executed.

Field truth stays null; methods empty; no inverse. The release is Peacock, Mitchell and Burgess2025, CC0 with required source attribution. This finding does not identify a true2D/3D model. C15 is also QC-only, not a substituted field inverse. [USGS DOI10.5066/P14KAQ3M](https://doi.org/10.5066/P14KAQ3M), [EarthScope DOI10.17611/DP/EMTF/GMEG/Clearlake](https://doi.org/10.17611/DP/EMTF/GMEG/Clearlake), [existing measured record](mt-recovery.md).

## 8. Array identity and separate operational gates

| Actual array | Shape | Meaning/function |
| --- | --- | --- |
| frequency_hz | N | Sorted Hz, read_edi |
| screen.tensor.real/imag/sigma | N×2×2 | Electric/magnetic E/H Ω and marginal SD, screen_edi |
| inverse.thickness/active | L-1 / N | Imposed m / Boolean training mask, _inverse |
| inverse.methods.mt-lm.model | L | Selected-final Ω m, invert_mt |
| predicted.real/imag; residual.real/imag | N | Ω; exported residual observed minus serialized prediction |
| frames/history | K×L / K | Copied physical states and their own complete objectives |
| uncertainty.samples/lower/upper | B×L / L | Actual conditional refits and percentiles, bootstrap_mt |

A recipient checks independent forward prediction against the physical model, then checks serialized residual identity against serialized prediction. Near-zero cancellation can amplify a one-ULP cross-platform forward difference; this is not permission to relax all response/error gates. Original/model/serialized-state identity each needs its own check. Compact ZIP has exactly manifest/dataset/result with hashes and no raw bytes; rights do not expand on export. [Reviewed contract](https://github.com/fsantibanezleal/CAOS_Geophysics/blob/0970a09/docs/data-contract/02_online-edi-mt.md).

M05:5MiB original,2..512frequencies,768MiB/8MiB/90s. M06:12..64frequencies,1or2layers,h2..4000m,initial strictly1..6000,beta0..1,20..40members,1GiB/32MiB/300s reduced by host ceilings. Same owned source/dataset M05 is mandatory; host flag defaults closed. Actual-host acceptance, full canonical FWI+MT assembly and integrated App validation are independent. No course test asserts host activation, deploys or completes those gates. [Use guide](../guides/09_online-mt-course.md).
